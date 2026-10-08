import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.models.question import GenerationMethod
from app.schemas.question import AIQuestionOutput
from app.services.ai_service import ai_service
from app.utils.text_utils import is_near_duplicate, overlap_ratio, significant_terms

logger = logging.getLogger(__name__)

TRUE_FALSE_VALUES = {"true", "false"}
INTERROGATIVES = ("what", "which", "who", "when", "where", "why", "how", "is", "are", "does", "do", "can")
HARD_MARKERS = ("analyze", "compare", "evaluate", "explain why", "differentiate", "justify")
EASY_MARKERS = ("what is", "which of the following", "true or false", "identify")
AMBIGUOUS_MARKERS = (
    "all of the above",
    "none of the above",
    "both a and b",
    "a and b only",
    "all except",
)
MIN_QUESTION_WORDS = 4
MIN_QUESTION_CHARS = 12
SOURCE_OVERLAP_THRESHOLD = 0.18
ANSWER_OVERLAP_THRESHOLD = 0.25
IRRELEVANT_OVERLAP_THRESHOLD = 0.08
DUPLICATE_THRESHOLD = 0.86
NON_BLOCKING_PREFIXES = ("difficulty is",)
NON_BLOCKING_KEYWORDS = ("ambiguous wording",)

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


class ValidationResult(BaseModel):
    valid: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    source_supported: bool
    recommended_status: str = "review"
    recommended_action: str = "review"
    relevance_scores: Dict[int, float] = Field(default_factory=dict)


class AIValidationOutput(BaseModel):
    valid: bool
    confidence: float
    issues: List[str] = Field(default_factory=list)
    source_supported: bool
    difficulty_appropriate: bool = True


def _load_prompt_template(filename: str) -> str:
    path = PROMPT_DIR / filename
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _word_count(text: str) -> int:
    return len([part for part in (text or "").split() if part])


def _correct_choices(question: AIQuestionOutput) -> List[str]:
    return [choice.text.strip() for choice in question.choices if choice.is_correct]


def _combined_source_text(chunks: Dict[int, str], chunk_ids: List[int]) -> str:
    return "\n".join(chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in chunks)


def _is_non_blocking_issue(issue: str) -> bool:
    lowered = issue.lower()
    if lowered.startswith(NON_BLOCKING_PREFIXES):
        return True
    return any(keyword in lowered for keyword in NON_BLOCKING_KEYWORDS)


def _blocking_issues(issues: List[str]) -> List[str]:
    return [issue for issue in issues if not _is_non_blocking_issue(issue)]


def parse_ai_validation_output(payload: Any) -> AIValidationOutput:
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("AI validation response is not valid JSON.") from exc
    if not isinstance(payload, dict):
        raise ValueError("AI validation response must be a JSON object.")
    try:
        parsed = AIValidationOutput.model_validate(payload)
    except ValidationError as exc:
        raise ValueError("AI validation response does not match the expected schema.") from exc
    parsed.confidence = max(0.0, min(1.0, parsed.confidence))
    return parsed


def validate_question_structure(question: AIQuestionOutput) -> List[str]:
    issues: List[str] = []
    text = (question.question_text or "").strip()

    if not text:
        issues.append("Question text is empty.")
    elif len(text) < MIN_QUESTION_CHARS or _word_count(text) < MIN_QUESTION_WORDS:
        issues.append("Question is too short to be understandable.")
    else:
        lowered = text.lower()
        looks_like_question = (
            "?" in text
            or lowered.startswith(INTERROGATIVES)
            or question.question_type in {QuestionType.identification, QuestionType.essay, QuestionType.matching}
        )
        if not looks_like_question:
            issues.append("Question wording is not clearly understandable as an exam item.")

    if question.question_type == QuestionType.multiple_choice:
        if len(question.choices) < 2:
            issues.append("Multiple-choice questions must have at least two choices.")
        correct_count = sum(1 for choice in question.choices if choice.is_correct)
        if correct_count != 1:
            issues.append("Multiple-choice questions must have exactly one correct answer.")
        choice_texts = [choice.text.strip().lower() for choice in question.choices]
        if any(not value for value in choice_texts):
            issues.append("Multiple-choice questions cannot have empty choices.")
        if len(choice_texts) != len(set(choice_texts)):
            issues.append("Multiple-choice questions cannot have duplicate choices.")

    elif question.question_type == QuestionType.true_false:
        if len(question.choices) != 2:
            issues.append("True/false questions must have exactly two choices.")
        labels = {choice.text.strip().lower() for choice in question.choices}
        if labels != TRUE_FALSE_VALUES:
            issues.append("True/false choices must be True and False.")
        if sum(1 for choice in question.choices if choice.is_correct) != 1:
            issues.append("True/false questions must have exactly one correct answer.")

    elif question.question_type == QuestionType.identification:
        if len(_correct_choices(question)) != 1:
            issues.append("Identification questions must include exactly one correct answer.")

    elif question.question_type == QuestionType.essay:
        if not text:
            issues.append("Essay questions must include a prompt.")

    elif question.question_type == QuestionType.matching:
        if len(question.choices) < 4:
            issues.append("Matching questions must have at least 4 items (2 pairs).")
        correct_count = sum(1 for choice in question.choices if choice.is_correct)
        if correct_count < 2:
            issues.append("Matching questions must have at least 2 correct matches marked.")

    return issues


def validate_ambiguous_wording(question: AIQuestionOutput) -> List[str]:
    combined = f"{question.question_text} {' '.join(choice.text for choice in question.choices)}".lower()
    if any(marker in combined for marker in AMBIGUOUS_MARKERS):
        return ["Question uses ambiguous wording that should be reviewed by a teacher."]
    return []


def validate_source_grounding(
    question: AIQuestionOutput,
    chunks: Dict[int, str],
    generation_method: GenerationMethod = GenerationMethod.ai,
) -> Tuple[bool, List[str], Dict[int, float]]:
    issues: List[str] = []
    relevance: Dict[int, float] = {}

    if generation_method != GenerationMethod.ai:
        if not question.source_chunk_ids:
            return True, [], {}

    if not question.source_chunk_ids:
        return False, ["AI-generated questions must cite at least one source chunk."], {}

    missing = [chunk_id for chunk_id in question.source_chunk_ids if chunk_id not in chunks]
    if missing:
        issues.append(f"Cited source chunk ids do not exist: {missing}.")

    valid_ids = [chunk_id for chunk_id in question.source_chunk_ids if chunk_id in chunks]
    source_text = _combined_source_text(chunks, valid_ids)
    if not source_text.strip():
        issues.append("Cited source material is empty.")
        return False, issues, relevance

    answer_text = " ".join(_correct_choices(question))
    question_overlap = overlap_ratio(f"{question.question_text} {question.explanation or ''}", source_text)
    answer_overlap = overlap_ratio(answer_text, source_text) if answer_text else 1.0
    answer_in_source = bool(answer_text) and answer_text.lower() in source_text.lower()

    for chunk_id in valid_ids:
        relevance[chunk_id] = round(
            max(
                overlap_ratio(question.question_text, chunks[chunk_id]),
                overlap_ratio(answer_text, chunks[chunk_id]) if answer_text else 0.0,
            ),
            4,
        )

    source_supported = True
    if question_overlap < SOURCE_OVERLAP_THRESHOLD:
        source_supported = False
        issues.append("Question does not match the cited source content closely enough.")

    if question_overlap < IRRELEVANT_OVERLAP_THRESHOLD:
        source_supported = False
        issues.append("Question contains irrelevant content that is not present in the source material.")

    if question.question_type not in {QuestionType.essay, QuestionType.true_false, QuestionType.matching}:
        if not answer_in_source and answer_overlap < ANSWER_OVERLAP_THRESHOLD:
            source_supported = False
            issues.append("Correct answer is not supported by the cited source material.")

    answer_terms = significant_terms(answer_text)
    source_terms = significant_terms(source_text)
    if answer_terms and not (answer_terms & source_terms) and not answer_in_source:
        source_supported = False
        if "Correct answer is not supported by the cited source material." not in issues:
            issues.append("Correct answer contains claims that are not present in the source material.")

    explanation_terms = significant_terms(question.explanation or "")
    if explanation_terms and question.explanation:
        explanation_overlap = overlap_ratio(question.explanation, source_text)
        if explanation_overlap < IRRELEVANT_OVERLAP_THRESHOLD and not (explanation_terms & source_terms):
            source_supported = False
            issues.append("Explanation contains unsupported claims that are not present in the source material.")

    return source_supported and not missing, issues, relevance


def validate_difficulty(question: AIQuestionOutput) -> List[str]:
    text = (question.question_text or "").lower()
    if question.difficulty == QuestionDifficulty.hard and any(marker in text for marker in EASY_MARKERS) and _word_count(text) < 12:
        return ["Difficulty is marked hard but the item reads like a simple recall question."]
    if question.difficulty == QuestionDifficulty.easy and any(marker in text for marker in HARD_MARKERS):
        return ["Difficulty is marked easy but the item requires analysis."]
    return []


def find_duplicate_issues(question: AIQuestionOutput, existing_texts: List[str]) -> List[str]:
    for existing in existing_texts:
        if is_near_duplicate(question.question_text, existing, DUPLICATE_THRESHOLD):
            return ["Question appears to be a duplicate of an existing question."]
    return []


def _confidence_from_issues(issues: List[str], source_supported: bool) -> float:
    confidence = 1.0
    confidence -= 0.18 * len(issues)
    if not source_supported:
        confidence -= 0.2
    return max(0.0, min(1.0, round(confidence, 2)))


def _recommended_action(valid: bool, issues: List[str]) -> str:
    if valid:
        return "review"
    regenerate_keywords = (
        "duplicate",
        "empty",
        "exactly one correct",
        "at least two choices",
        "too short",
        "not supported",
        "do not exist",
        "cite at least one",
        "unsupported",
        "irrelevant",
    )
    if any(any(keyword in issue.lower() for keyword in regenerate_keywords) for issue in issues):
        return "regenerate"
    return "review"


def _recommended_status(valid: bool, issues: List[str]) -> str:
    action = _recommended_action(valid, issues)
    if action == "regenerate":
        return "draft"
    return "review"


def _merge_results(deterministic: ValidationResult, ai_result: Optional[AIValidationOutput]) -> ValidationResult:
    if ai_result is None:
        return deterministic

    issues = list(dict.fromkeys(deterministic.issues + ai_result.issues))
    if not ai_result.difficulty_appropriate and "Difficulty is not appropriate for the requested level." not in issues:
        issues.append("Difficulty is not appropriate for the requested level.")

    source_supported = deterministic.source_supported and ai_result.source_supported
    valid = deterministic.valid and ai_result.valid and source_supported and not _blocking_issues(issues)
    confidence = round(min(deterministic.confidence, max(0.0, min(1.0, ai_result.confidence))), 2)
    return ValidationResult(
        valid=valid,
        confidence=confidence,
        issues=issues,
        source_supported=source_supported,
        recommended_status=_recommended_status(valid, issues),
        recommended_action=_recommended_action(valid, issues),
        relevance_scores=deterministic.relevance_scores,
    )


def _run_ai_validation(question: AIQuestionOutput, source_text: str) -> Optional[AIValidationOutput]:
    try:
        template = _load_prompt_template("question_validation.txt")
        prompt = template.format(
            question_payload=question.model_dump_json(),
            source_material=source_text or "No source material provided.",
        )
        raw = ai_service.generate_structured_json(prompt=prompt, response_schema=AIValidationOutput)
        return parse_ai_validation_output(raw)
    except Exception as exc:
        logger.error("AI question validation failed; using deterministic result only: %s", exc)
        return None


def validate_generated_question(
    question: AIQuestionOutput,
    chunks: Dict[int, str],
    existing_texts: Optional[List[str]] = None,
    generation_method: GenerationMethod = GenerationMethod.ai,
    use_ai: bool = False,
) -> ValidationResult:
    issues: List[str] = []
    issues.extend(validate_question_structure(question))
    source_supported, grounding_issues, relevance = validate_source_grounding(
        question, chunks, generation_method=generation_method
    )
    issues.extend(grounding_issues)
    issues.extend(validate_difficulty(question))
    issues.extend(validate_ambiguous_wording(question))
    issues.extend(find_duplicate_issues(question, existing_texts or []))

    valid = not _blocking_issues(issues) and source_supported
    result = ValidationResult(
        valid=valid,
        confidence=_confidence_from_issues(issues, source_supported),
        issues=issues,
        source_supported=source_supported,
        recommended_status=_recommended_status(valid, issues),
        recommended_action=_recommended_action(valid, issues),
        relevance_scores=relevance,
    )

    if use_ai:
        source_text = _combined_source_text(chunks, question.source_chunk_ids)
        ai_result = _run_ai_validation(question, source_text)
        result = _merge_results(result, ai_result)

    logger.info(
        "Validated question type=%s valid=%s confidence=%s source_supported=%s action=%s issues=%s",
        question.question_type.value,
        result.valid,
        result.confidence,
        result.source_supported,
        result.recommended_action,
        result.issues,
    )
    return result


def question_to_ai_output(question: Any) -> AIQuestionOutput:
    topic = ""
    if getattr(question, "sources", None):
        first_source = question.sources[0]
        if getattr(first_source, "chunk", None) and first_source.chunk.section_title:
            topic = first_source.chunk.section_title
    return AIQuestionOutput(
        question_text=question.question_text,
        question_type=question.question_type,
        difficulty=question.difficulty,
        topic=topic,
        choices=[
            {"text": choice.choice_text, "is_correct": choice.is_correct}
            for choice in question.choices
        ],
        explanation=question.explanation or "",
        source_chunk_ids=[source.chunk_id for source in question.sources],
    )
