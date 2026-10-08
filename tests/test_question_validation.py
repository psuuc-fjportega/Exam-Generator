import pytest

from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.schemas.question import AIChoiceOutput, AIQuestionOutput
from app.services.validation_service import (
    AIValidationOutput,
    parse_ai_validation_output,
    validate_difficulty,
    validate_generated_question,
    validate_question_structure,
    validate_source_grounding,
)


SOURCE_TEXT = (
    "The mitochondria is the powerhouse of the cell. "
    "It produces ATP through cellular respiration. "
    "Plant cells also contain chloroplasts for photosynthesis."
)


def _mc_question(**overrides) -> AIQuestionOutput:
    data = {
        "question_text": "Which organelle is the powerhouse of the cell?",
        "question_type": QuestionType.multiple_choice,
        "difficulty": QuestionDifficulty.easy,
        "topic": "Cell Structure",
        "choices": [
            AIChoiceOutput(text="Mitochondria", is_correct=True),
            AIChoiceOutput(text="Golgi apparatus", is_correct=False),
            AIChoiceOutput(text="Ribosome", is_correct=False),
            AIChoiceOutput(text="Lysosome", is_correct=False),
        ],
        "explanation": "The material states that the mitochondria is the powerhouse of the cell.",
        "source_chunk_ids": [1],
    }
    data.update(overrides)
    return AIQuestionOutput(**data)


def test_multiple_choice_requires_exactly_one_correct_answer():
    question = _mc_question(
        choices=[
            AIChoiceOutput(text="Mitochondria", is_correct=True),
            AIChoiceOutput(text="Chloroplast", is_correct=True),
            AIChoiceOutput(text="Ribosome", is_correct=False),
        ]
    )
    issues = validate_question_structure(question)
    assert any("exactly one correct answer" in issue for issue in issues)


def test_multiple_choice_rejects_missing_correct_answer():
    question = _mc_question(
        choices=[
            AIChoiceOutput(text="Mitochondria", is_correct=False),
            AIChoiceOutput(text="Ribosome", is_correct=False),
        ]
    )
    issues = validate_question_structure(question)
    assert any("exactly one correct answer" in issue for issue in issues)


def test_true_false_requires_true_and_false_labels():
    question = AIQuestionOutput(
        question_text="The mitochondria produces ATP.",
        question_type=QuestionType.true_false,
        difficulty=QuestionDifficulty.easy,
        choices=[
            AIChoiceOutput(text="Yes", is_correct=True),
            AIChoiceOutput(text="No", is_correct=False),
        ],
        explanation="Supported by the material.",
        source_chunk_ids=[1],
    )
    issues = validate_question_structure(question)
    assert any("True and False" in issue for issue in issues)


def test_identification_requires_exactly_one_correct_answer():
    question = AIQuestionOutput(
        question_text="Identify the organelle that produces ATP.",
        question_type=QuestionType.identification,
        difficulty=QuestionDifficulty.easy,
        choices=[],
        explanation="Mitochondria produce ATP.",
        source_chunk_ids=[1],
    )
    issues = validate_question_structure(question)
    assert any("exactly one correct answer" in issue for issue in issues)


def test_short_question_is_not_understandable():
    question = _mc_question(question_text="ATP?")
    issues = validate_question_structure(question)
    assert any("too short" in issue for issue in issues)


def test_source_grounding_accepts_supported_answer():
    question = _mc_question()
    supported, issues, relevance = validate_source_grounding(question, {1: SOURCE_TEXT})
    assert supported is True
    assert issues == []
    assert 1 in relevance


def test_source_grounding_rejects_unsupported_answer():
    question = _mc_question(
        question_text="What is the capital of France according to world geography?",
        choices=[
            AIChoiceOutput(text="Paris", is_correct=True),
            AIChoiceOutput(text="Lyon", is_correct=False),
        ],
        explanation="Paris is the capital of France.",
    )
    supported, issues, _ = validate_source_grounding(question, {1: SOURCE_TEXT})
    assert supported is False
    assert issues


def test_source_grounding_rejects_missing_chunk_ids():
    question = _mc_question(source_chunk_ids=[99])
    supported, issues, _ = validate_source_grounding(question, {1: SOURCE_TEXT})
    assert supported is False
    assert any("do not exist" in issue for issue in issues)


def test_source_grounding_requires_chunk_citation_for_ai_questions():
    question = _mc_question(source_chunk_ids=[])
    supported, issues, _ = validate_source_grounding(question, {1: SOURCE_TEXT})
    assert supported is False
    assert any("cite at least one source chunk" in issue for issue in issues)


def test_irrelevant_content_is_flagged_for_regeneration():
    question = _mc_question(
        question_text="What is the capital of France according to world geography?",
        choices=[
            AIChoiceOutput(text="Paris", is_correct=True),
            AIChoiceOutput(text="Lyon", is_correct=False),
        ],
        explanation="Paris is the capital of France.",
    )
    result = validate_generated_question(question, chunks={1: SOURCE_TEXT})
    assert result.valid is False
    assert result.source_supported is False
    assert result.recommended_action == "regenerate"
    assert any("irrelevant" in issue.lower() or "not supported" in issue.lower() for issue in result.issues)


def test_duplicate_detection():
    question = _mc_question()
    result = validate_generated_question(
        question,
        chunks={1: SOURCE_TEXT},
        existing_texts=["Which organelle is the powerhouse of the cell?"],
    )
    assert result.valid is False
    assert any("duplicate" in issue.lower() for issue in result.issues)
    assert result.recommended_action == "regenerate"


def test_ambiguous_wording_is_sent_to_teacher_review():
    question = _mc_question(
        question_text="Which of the following is the powerhouse of the cell?",
        choices=[
            AIChoiceOutput(text="Mitochondria", is_correct=True),
            AIChoiceOutput(text="All of the above", is_correct=False),
        ],
    )
    result = validate_generated_question(question, chunks={1: SOURCE_TEXT})
    assert result.valid is True
    assert result.recommended_action == "review"
    assert any("ambiguous" in issue.lower() for issue in result.issues)


def test_difficulty_warning_does_not_block_valid_grounded_question():
    question = _mc_question(
            question_text="Evaluate and compare why mitochondria produce ATP during cellular respiration?",
        difficulty=QuestionDifficulty.easy,
    )
    issues = validate_difficulty(question)
    assert issues
    result = validate_generated_question(question, chunks={1: SOURCE_TEXT})
    assert result.valid is True
    assert result.source_supported is True


def test_valid_grounded_question_is_marked_for_teacher_review():
    question = _mc_question()
    result = validate_generated_question(question, chunks={1: SOURCE_TEXT})
    assert result.valid is True
    assert result.source_supported is True
    assert result.issues == []
    assert result.recommended_status == "review"
    assert result.recommended_action == "review"
    assert 0.0 <= result.confidence <= 1.0


def test_ai_validation_output_schema_parses_expected_payload():
    parsed = parse_ai_validation_output(
        {
            "valid": True,
            "confidence": 0.92,
            "issues": [],
            "source_supported": True,
            "difficulty_appropriate": True,
        }
    )
    assert parsed.valid is True
    assert parsed.confidence == 0.92


def test_ai_validation_output_rejects_malformed_payload():
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_ai_validation_output("{not-json")
    with pytest.raises(ValueError, match="expected schema"):
        parse_ai_validation_output({"valid": True})


def test_ai_merge_can_invalidate_an_otherwise_valid_question(monkeypatch):
    monkeypatch.setattr(
        "app.services.validation_service._run_ai_validation",
        lambda question, source_text: AIValidationOutput(
            valid=False,
            confidence=0.41,
            issues=["Correct answer is not supported by the source material."],
            source_supported=False,
            difficulty_appropriate=True,
        ),
    )
    result = validate_generated_question(_mc_question(), chunks={1: SOURCE_TEXT}, use_ai=True)
    assert result.valid is False
    assert result.source_supported is False
    assert result.recommended_action == "regenerate"


def test_ai_validation_failure_falls_back_to_deterministic_result(monkeypatch):
    monkeypatch.setattr(
        "app.services.validation_service._run_ai_validation",
        lambda question, source_text: None,
    )
    result = validate_generated_question(_mc_question(), chunks={1: SOURCE_TEXT}, use_ai=True)
    assert result.valid is True
    assert result.source_supported is True
    assert result.recommended_action == "review"
