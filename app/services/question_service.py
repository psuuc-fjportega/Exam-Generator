import json
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.models.examination import Examination, ExamStatus
from app.models.examination_question import ExaminationQuestion
from app.models.material import Material
from app.models.question import GenerationMethod, Question, QuestionStatus
from app.models.question_choice import QuestionChoice
from app.models.question_source import QuestionSource
from app.schemas.question import AIGenerationOutput, AIQuestionOutput, QuestionResponse, QuestionSourceResponse
from app.services.ai_service import ai_service
from app.services.validation_service import (
    ValidationResult,
    question_to_ai_output,
    validate_generated_question,
)

logger = logging.getLogger(__name__)


def load_prompt_template(filename: str) -> str:
    path = os.path.join(os.getcwd(), "prompts", filename)
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def _chunks_for_subject(db: Session, subject_id: int) -> List[DocumentChunk]:
    materials = db.query(Material).filter(Material.subject_id == subject_id).all()
    material_ids = [material.id for material in materials]
    if not material_ids:
        return []
    return db.query(DocumentChunk).filter(DocumentChunk.material_id.in_(material_ids)).all()


def _chunk_map(chunks: List[DocumentChunk]) -> Dict[int, str]:
    return {chunk.id: chunk.content for chunk in chunks}


def _parse_issues(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        return [raw]
    return []


def serialize_question(question: Question) -> QuestionResponse:
    sources: List[QuestionSourceResponse] = []
    for source in question.sources:
        excerpt = source.chunk.content if source.chunk else None
        if excerpt and len(excerpt) > 400:
            excerpt = excerpt[:400] + "..."
        sources.append(
            QuestionSourceResponse(
                id=source.id,
                chunk_id=source.chunk_id,
                relevance_score=source.relevance_score,
                page_number=source.chunk.page_number if source.chunk else None,
                section_title=source.chunk.section_title if source.chunk else None,
                excerpt=excerpt,
            )
        )
    return QuestionResponse(
        id=question.id,
        subject_id=question.subject_id,
        question_text=question.question_text,
        question_type=question.question_type,
        difficulty=question.difficulty,
        explanation=question.explanation,
        status=question.status,
        generation_method=question.generation_method,
        created_by=question.created_by,
        validation_confidence=question.validation_confidence,
        source_supported=question.source_supported,
        validation_issues=_parse_issues(question.validation_issues),
        created_at=question.created_at,
        updated_at=question.updated_at,
        choices=question.choices,
        sources=sources,
    )


def apply_validation(question: Question, result: ValidationResult) -> None:
    question.validation_confidence = result.confidence
    question.source_supported = result.source_supported
    question.validation_issues = json.dumps(result.issues)
    if question.status not in {QuestionStatus.approved, QuestionStatus.rejected, QuestionStatus.archived}:
        question.status = QuestionStatus(result.recommended_status)


def persist_generated_question(
    db: Session,
    exam: Examination,
    generated: AIQuestionOutput,
    chunks: Dict[int, str],
    created_by: int,
    question_order: int,
    existing_texts: List[str],
) -> tuple[Question, ValidationResult]:
    question = Question(
        subject_id=exam.subject_id,
        question_text=generated.question_text.strip(),
        question_type=generated.question_type,
        difficulty=generated.difficulty,
        explanation=generated.explanation,
        status=QuestionStatus.draft,
        generation_method=GenerationMethod.ai,
        created_by=created_by,
    )
    db.add(question)
    db.flush()

    for index, choice in enumerate(generated.choices):
        db.add(
            QuestionChoice(
                question_id=question.id,
                choice_text=choice.text,
                choice_order=index,
                is_correct=choice.is_correct,
            )
        )

    result = validate_generated_question(
        generated,
        chunks=chunks,
        existing_texts=existing_texts,
        generation_method=GenerationMethod.ai,
        use_ai=False,
    )
    cited_ids = [chunk_id for chunk_id in generated.source_chunk_ids if chunk_id in chunks]
    for chunk_id in cited_ids:
        db.add(
            QuestionSource(
                question_id=question.id,
                chunk_id=chunk_id,
                relevance_score=result.relevance_scores.get(chunk_id),
            )
        )

    db.add(
        ExaminationQuestion(
            examination_id=exam.id,
            question_id=question.id,
            question_order=question_order,
            points=1,
        )
    )

    apply_validation(question, result)
    db.flush()
    return question, result


def generate_questions_for_exam(db: Session, exam_id: int) -> Dict[str, Any]:
    exam = db.query(Examination).filter(Examination.id == exam_id).first()
    if not exam:
        raise ValueError("Examination not found")

    chunks = _chunks_for_subject(db, exam.subject_id)
    if not chunks:
        raise ValueError("No source material found for the given subject")

    source_material_text = ""
    for chunk in chunks:
        source_material_text += f"[CHUNK ID: {chunk.id}]\n{chunk.content}\n\n"

    blueprint_instructions = ""
    for blueprint in exam.blueprints:
        blueprint_instructions += (
            f"- Generate {blueprint.quantity} questions of type "
            f"{blueprint.question_type.value} with {blueprint.difficulty.value} difficulty.\n"
        )

    template = load_prompt_template("question_generation.txt")
    prompt = template.format(
        blueprint_instructions=blueprint_instructions,
        source_material=source_material_text,
    )

    result_dict = ai_service.generate_structured_json(
        prompt=prompt,
        response_schema=AIGenerationOutput,
    )
    parsed = AIGenerationOutput.model_validate(result_dict)
    chunk_lookup = _chunk_map(chunks)

    existing_texts = [
        row.question_text
        for row in db.query(Question).filter(Question.subject_id == exam.subject_id).all()
    ]
    saved: List[Question] = []
    validations: List[ValidationResult] = []

    for index, generated in enumerate(parsed.questions, start=1):
        if not generated.source_chunk_ids:
            generated.source_chunk_ids = [chunks[0].id]
        question, validation = persist_generated_question(
            db=db,
            exam=exam,
            generated=generated,
            chunks=chunk_lookup,
            created_by=exam.created_by,
            question_order=index,
            existing_texts=existing_texts,
        )
        saved.append(question)
        validations.append(validation)
        existing_texts.append(generated.question_text)

    if exam.status == ExamStatus.draft:
        exam.status = ExamStatus.review

    db.commit()
    for question in saved:
        db.refresh(question)

    logger.info("Generated and validated %s questions for examination %s", len(saved), exam.id)
    return {
        "generated_data": parsed.model_dump(),
        "questions": [serialize_question(question).model_dump() for question in saved],
        "validation": [item.model_dump() for item in validations],
    }


def validate_question_record(db: Session, question: Question, use_ai: bool = False) -> ValidationResult:
    chunks = _chunks_for_subject(db, question.subject_id)
    chunk_lookup = _chunk_map(chunks)
    existing_texts = [
        row.question_text
        for row in db.query(Question)
        .filter(Question.subject_id == question.subject_id, Question.id != question.id)
        .all()
    ]
    payload = question_to_ai_output(question)
    result = validate_generated_question(
        payload,
        chunks=chunk_lookup,
        existing_texts=existing_texts,
        generation_method=question.generation_method,
        use_ai=use_ai,
    )
    apply_validation(question, result)
    for source in question.sources:
        if source.chunk_id in result.relevance_scores:
            source.relevance_score = result.relevance_scores[source.chunk_id]
    db.commit()
    db.refresh(question)
    logger.info(
        "Stored validation for question %s valid=%s action=%s",
        question.id,
        result.valid,
        result.recommended_action,
    )
    return result


def validate_exam_questions(db: Session, exam_id: int, use_ai: bool = False) -> Dict[str, Any]:
    exam = db.query(Examination).filter(Examination.id == exam_id).first()
    if not exam:
        raise ValueError("Examination not found")

    links = (
        db.query(ExaminationQuestion)
        .filter(ExaminationQuestion.examination_id == exam_id)
        .order_by(ExaminationQuestion.question_order.asc())
        .all()
    )
    validations: List[ValidationResult] = []
    questions: List[Question] = []
    for link in links:
        if not link.question:
            continue
        result = validate_question_record(db, link.question, use_ai=use_ai)
        validations.append(result)
        questions.append(link.question)

    logger.info("Validated %s questions for examination %s", len(questions), exam_id)
    return {
        "examination_id": exam_id,
        "questions": [serialize_question(question).model_dump() for question in questions],
        "validation": [item.model_dump() for item in validations],
        "invalid_count": sum(1 for item in validations if not item.valid),
        "needs_regeneration": sum(1 for item in validations if item.recommended_action == "regenerate"),
    }
