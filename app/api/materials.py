from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from sqlalchemy.orm import Session
import json
import os

from app.core.database import get_db
from app.core.config import settings
from app.api.deps import get_current_user, get_current_active_teacher
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.material import Material, ProcessingStatus
from app.models.examination import Examination, ExamStatus
from app.models.examination_blueprint import ExaminationBlueprint, QuestionType, QuestionDifficulty
from app.schemas.material import MaterialResponse
from app.schemas.examination import ExaminationResponse
from app.utils.file_utils import validate_file, save_upload_file

router = APIRouter()

@router.post("/upload", response_model=MaterialResponse)
async def upload_material(
    background_tasks: BackgroundTasks,
    *,
    db: Session = Depends(get_db),
    subject_id: int = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    # Verify subject
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role != UserRole.admin and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to upload to this subject")

    ext, content_type = validate_file(file)
    unique_filename, file_path, file_size = await save_upload_file(file, settings.UPLOAD_DIR)
    
    material = Material(
        subject_id=subject_id,
        uploaded_by=current_user.id,
        file_name=unique_filename,
        original_file_name=file.filename,
        file_type=ext.lstrip('.'),
        file_size=file_size,
        file_path=file_path,
        processing_status=ProcessingStatus.uploaded
    )
    
    db.add(material)
    db.commit()
    db.refresh(material)
    
    from app.services.document_service import process_material_sync
    background_tasks.add_task(process_material_sync, material.id)
    
    return material

@router.get("", response_model=List[MaterialResponse])
def read_materials(
    db: Session = Depends(get_db),
    subject_id: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    query = db.query(Material)
    if current_user.role != UserRole.admin:
        query = query.filter(Material.uploaded_by == current_user.id)
    if subject_id:
        query = query.filter(Material.subject_id == subject_id)
        
    materials = query.offset(skip).limit(limit).all()
    return materials

@router.get("/{id}", response_model=MaterialResponse)
def read_material(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if current_user.role != UserRole.admin and material.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return material

@router.delete("/{id}")
def delete_material(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    material = db.query(Material).filter(Material.id == id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if current_user.role != UserRole.admin and material.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Remove file from disk
    if os.path.exists(material.file_path):
        try:
            os.remove(material.file_path)
        except OSError:
            pass # Handle gracefully if file is already gone or locked
            
    db.delete(material)
    db.commit()
    return {"status": "success", "detail": "Material deleted"}


# ---------------------------------------------------------------------------
# Upload + Instant Exam Generation
# ---------------------------------------------------------------------------

# Allowed preset shorthand values the client can pass as a single string
_PRESET_ALL_TYPES = "all"
_VALID_PRESETS = {_PRESET_ALL_TYPES} | {qt.value for qt in QuestionType}

def _resolve_question_types(exam_type: str) -> List[QuestionType]:
    """Return the list of QuestionType values for a given preset or single type string."""
    exam_type = exam_type.strip().lower()
    if exam_type == _PRESET_ALL_TYPES:
        return list(QuestionType)
    if exam_type in {qt.value for qt in QuestionType}:
        return [QuestionType(exam_type)]
    raise ValueError(
        f"Invalid exam_type '{exam_type}'. "
        f"Valid values: {sorted(_VALID_PRESETS)}"
    )


def _build_blueprints_from_types(
    types: List[QuestionType],
    total_questions: int,
    difficulty: QuestionDifficulty,
) -> List[dict]:
    """
    Distribute total_questions evenly across the requested question types.
    Any remainder is added to the first type.
    """
    n = len(types)
    base, remainder = divmod(total_questions, n)
    blueprints = []
    for i, qt in enumerate(types):
        qty = base + (1 if i < remainder else 0)
        if qty > 0:
            blueprints.append({"question_type": qt, "difficulty": difficulty, "quantity": qty, "points": 1})
    return blueprints


@router.post("/upload-and-generate")
async def upload_and_generate_exam(
    *,
    db: Session = Depends(get_db),
    subject_id: int = Form(..., description="ID of the subject this material belongs to"),
    file: UploadFile = File(..., description="Learning material file (PDF, DOCX, TXT, etc.)"),
    exam_title: str = Form(..., description="Title for the generated examination"),
    exam_type: str = Form(
        "all",
        description=(
            "Question type(s) to generate. "
            "Options: 'all', 'multiple_choice', 'true_false', 'identification', 'essay', 'matching'. "
            "Use 'all' to include a mixture of every type."
        ),
    ),
    total_questions: int = Form(10, ge=1, le=100, description="Total number of questions to generate"),
    difficulty: str = Form("medium", description="Difficulty level: 'easy', 'medium', or 'hard'"),
    time_limit_minutes: int = Form(60, ge=1, description="Exam time limit in minutes"),
    passing_score: int = Form(50, ge=0, le=100, description="Passing score percentage (0-100)"),
    exam_description: Optional[str] = Form(None, description="Optional description for the examination"),
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    """
    **Upload a learning material and immediately generate an examination from it.**

    This endpoint combines three steps into one request:
    1. Upload and process (extract + chunk) the file.
    2. Create an exam record with the chosen configuration.
    3. Call the AI to generate questions according to the blueprint.

    The `exam_type` field controls which question type(s) are generated:
    - `"all"` → mixture of multiple choice, true/false, identification, essay, and matching
    - `"multiple_choice"` → only multiple-choice questions
    - `"matching"` → only matching-type questions
    - (and so on for each individual type)
    """
    # -- 1. Validate subject & permissions -----------------------------------------
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role != UserRole.admin and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions to upload to this subject")

    # -- 2. Validate difficulty -------------------------------------------------------
    try:
        difficulty_enum = QuestionDifficulty(difficulty.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid difficulty '{difficulty}'. Choose from: easy, medium, hard",
        )

    # -- 3. Resolve exam_type to a list of QuestionType values ------------------------
    try:
        question_types = _resolve_question_types(exam_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # -- 4. Save & process the uploaded file ------------------------------------------
    ext, content_type = validate_file(file)
    unique_filename, file_path, file_size = await save_upload_file(file, settings.UPLOAD_DIR)

    material = Material(
        subject_id=subject_id,
        uploaded_by=current_user.id,
        file_name=unique_filename,
        original_file_name=file.filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        file_path=file_path,
        processing_status=ProcessingStatus.uploaded,
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    # Process the file synchronously so we can use the chunks immediately
    from app.services.document_service import process_material_sync
    process_material_sync(material.id)
    db.refresh(material)

    if material.processing_status == ProcessingStatus.failed:
        raise HTTPException(
            status_code=422,
            detail=f"File processing failed: {material.processing_error or 'unknown error'}",
        )

    # -- 5. Build blueprints & create Examination record ------------------------------
    blueprints_data = _build_blueprints_from_types(question_types, total_questions, difficulty_enum)

    exam = Examination(
        subject_id=subject_id,
        created_by=current_user.id,
        title=exam_title,
        description=exam_description,
        total_questions=total_questions,
        time_limit_minutes=time_limit_minutes,
        passing_score=passing_score,
        status=ExamStatus.draft,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    for bp in blueprints_data:
        db.add(ExaminationBlueprint(examination_id=exam.id, **bp))
    db.commit()
    db.refresh(exam)

    # -- 6. Generate questions via AI -------------------------------------------------
    from app.services.question_service import generate_questions_for_exam
    try:
        generation_result = generate_questions_for_exam(db, exam.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(exc)}")

    db.refresh(exam)

    return {
        "material": {
            "id": material.id,
            "original_file_name": material.original_file_name,
            "processing_status": material.processing_status,
        },
        "examination": {
            "id": exam.id,
            "title": exam.title,
            "subject_id": exam.subject_id,
            "status": exam.status,
            "total_questions": exam.total_questions,
            "time_limit_minutes": exam.time_limit_minutes,
            "passing_score": exam.passing_score,
            "blueprints": [
                {
                    "question_type": bp.question_type,
                    "difficulty": bp.difficulty,
                    "quantity": bp.quantity,
                    "points": bp.points,
                }
                for bp in exam.blueprints
            ],
        },
        "generation": {
            "questions_generated": len(generation_result.get("questions", [])),
            "questions": generation_result.get("questions", []),
            "validation": generation_result.get("validation", []),
        },
    }

