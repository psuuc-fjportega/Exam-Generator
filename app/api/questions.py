from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_teacher, get_current_user
from app.core.database import get_db
from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.models.question import Question, QuestionStatus
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.schemas.question import QuestionResponse, QuestionValidateResponse, ValidationResultResponse
from app.services.question_service import serialize_question, validate_question_record

router = APIRouter()


def _get_accessible_question(db: Session, question_id: int, current_user: User) -> Question:
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    subject = db.query(Subject).filter(Subject.id == question.subject_id).first()
    if current_user.role == UserRole.admin:
        return question
    if current_user.role == UserRole.teacher:
        if not subject or subject.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return question
    raise HTTPException(status_code=403, detail="Not enough permissions")


@router.get("", response_model=List[QuestionResponse])
def list_questions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_teacher),
    subject_id: Optional[int] = None,
    question_type: Optional[QuestionType] = None,
    difficulty: Optional[QuestionDifficulty] = None,
    status: Optional[QuestionStatus] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=200),
) -> Any:
    query = db.query(Question)
    if current_user.role == UserRole.teacher:
        subject_ids = [
            row.id for row in db.query(Subject).filter(Subject.teacher_id == current_user.id).all()
        ]
        query = query.filter(Question.subject_id.in_(subject_ids or [0]))
    if subject_id is not None:
        query = query.filter(Question.subject_id == subject_id)
    if question_type is not None:
        query = query.filter(Question.question_type == question_type)
    if difficulty is not None:
        query = query.filter(Question.difficulty == difficulty)
    if status is not None:
        query = query.filter(Question.status == status)

    questions = query.order_by(Question.id.asc()).offset(skip).limit(limit).all()
    return [serialize_question(question) for question in questions]


@router.get("/{id}", response_model=QuestionResponse)
def get_question(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    question = _get_accessible_question(db, id, current_user)
    return serialize_question(question)


@router.post("/{id}/validate", response_model=QuestionValidateResponse)
def validate_question(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
    use_ai: bool = False,
) -> Any:
    question = _get_accessible_question(db, id, current_user)
    try:
        result = validate_question_record(db, question, use_ai=use_ai)
    except Exception:
        raise HTTPException(status_code=500, detail="Question validation failed")
    return QuestionValidateResponse(
        question=serialize_question(question),
        validation=ValidationResultResponse(**result.model_dump()),
    )
