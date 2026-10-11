from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_teacher
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.examination import Examination, ExamStatus
from app.models.examination_blueprint import ExaminationBlueprint
from app.schemas.examination import ExaminationCreate, ExaminationUpdate, ExaminationResponse

router = APIRouter()

@router.post("", response_model=ExaminationResponse)
def create_examination(
    *,
    db: Session = Depends(get_db),
    exam_in: ExaminationCreate,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    subject = db.query(Subject).filter(Subject.id == exam_in.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role != UserRole.admin and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to create exam for this subject")

    exam_data = exam_in.model_dump(exclude={"blueprints"})
    exam = Examination(**exam_data, created_by=current_user.id)
    db.add(exam)
    db.commit()
    db.refresh(exam)
    
    for bp in exam_in.blueprints:
        blueprint = ExaminationBlueprint(
            examination_id=exam.id,
            **bp.model_dump()
        )
        db.add(blueprint)
    
    db.commit()
    db.refresh(exam)
    return exam

@router.get("", response_model=List[ExaminationResponse])
def read_examinations(
    db: Session = Depends(get_db),
    subject_id: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    query = db.query(Examination)
    if current_user.role == UserRole.teacher:
        query = query.filter(Examination.created_by == current_user.id)
    elif current_user.role == UserRole.student:
        query = query.filter(Examination.status == ExamStatus.published)
        
    if subject_id:
        query = query.filter(Examination.subject_id == subject_id)
        
    return query.offset(skip).limit(limit).all()

@router.get("/{id}", response_model=ExaminationResponse)
def read_examination(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    exam = db.query(Examination).filter(Examination.id == id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
        
    if current_user.role == UserRole.teacher and exam.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    elif current_user.role == UserRole.student and exam.status != ExamStatus.published:
        raise HTTPException(status_code=403, detail="Examination is not available")
        
    return exam

from app.services.question_service import generate_questions_for_exam, validate_exam_questions

@router.post("/{id}/generate")
def generate_examination_questions(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    exam = db.query(Examination).filter(Examination.id == id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
        
    if current_user.role != UserRole.admin and exam.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    try:
        generation_result = generate_questions_for_exam(db, exam.id)
        return {"status": "success", **generation_result}
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


@router.post("/{id}/validate")
def validate_examination_questions(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
    use_ai: bool = False,
) -> Any:
    exam = db.query(Examination).filter(Examination.id == id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    if current_user.role != UserRole.admin and exam.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    try:
        return {"status": "success", **validate_exam_questions(db, exam.id, use_ai=use_ai)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Question validation failed")


from app.schemas.examination import GenerateFromMaterialRequest
from app.models.material import Material
from app.models.examination_blueprint import QuestionDifficulty
from app.api.materials import _resolve_question_types, _build_blueprints_from_types
from app.services.analysis_service import analyze_material_record


@router.post("/generate-from-material")
def generate_exam_from_material(
    *,
    db: Session = Depends(get_db),
    request_data: GenerateFromMaterialRequest,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    """Create an exam and generate questions directly from an already uploaded & analyzed material."""
    material = db.query(Material).filter(Material.id == request_data.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if current_user.role != UserRole.admin and material.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to access this material")

    try:
        difficulty_enum = QuestionDifficulty(request_data.difficulty.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid difficulty '{request_data.difficulty}'. Choose from: easy, medium, hard",
        )

    try:
        question_types = _resolve_question_types(request_data.exam_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    analysis = analyze_material_record(db, material.id)

    effective_title = (
        request_data.exam_title.strip()
        if (request_data.exam_title and request_data.exam_title.strip())
        else analysis.title_suggestion
    )
    effective_description = (
        request_data.exam_description.strip()
        if (request_data.exam_description and request_data.exam_description.strip())
        else analysis.summary
    )

    blueprints_data = _build_blueprints_from_types(
        question_types, request_data.total_questions, difficulty_enum
    )

    exam = Examination(
        subject_id=material.subject_id,
        created_by=current_user.id,
        material_id=material.id,
        title=effective_title,
        description=effective_description,
        total_questions=request_data.total_questions,
        time_limit_minutes=request_data.time_limit_minutes,
        passing_score=request_data.passing_score,
        status=ExamStatus.draft,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    for bp in blueprints_data:
        db.add(ExaminationBlueprint(examination_id=exam.id, **bp))
    db.commit()
    db.refresh(exam)

    try:
        generation_result = generate_questions_for_exam(db, exam.id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(exc)}")

    db.refresh(exam)

    return {
        "status": "success",
        "material": {
            "id": material.id,
            "original_file_name": material.original_file_name,
            "summary": material.summary,
        },
        "analysis": analysis.model_dump(),
        "examination": ExaminationResponse.model_validate(exam).model_dump(),
        "generation": {
            "questions_generated": len(generation_result.get("questions", [])),
            "questions": generation_result.get("questions", []),
            "validation": generation_result.get("validation", []),
        },
    }

