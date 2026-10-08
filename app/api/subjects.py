from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_active_teacher
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter()

@router.post("", response_model=SubjectResponse)
def create_subject(
    *,
    db: Session = Depends(get_db),
    subject_in: SubjectCreate,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    # Check if subject code exists
    existing = db.query(Subject).filter(Subject.code == subject_in.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Subject with this code already exists.",
        )
    subject = Subject(
        **subject_in.model_dump(),
        teacher_id=current_user.id
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

@router.get("", response_model=List[SubjectResponse])
def read_subjects(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
) -> Any:
    if current_user.role in [UserRole.student, UserRole.admin]:
        subjects = db.query(Subject).offset(skip).limit(limit).all()
    else:
        # Teacher sees their own subjects
        subjects = db.query(Subject).filter(Subject.teacher_id == current_user.id).offset(skip).limit(limit).all()
    return subjects

@router.get("/{id}", response_model=SubjectResponse)
def read_subject(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_user),
) -> Any:
    subject = db.query(Subject).filter(Subject.id == id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    # Access checks
    if current_user.role == UserRole.teacher and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return subject

@router.put("/{id}", response_model=SubjectResponse)
def update_subject(
    *,
    db: Session = Depends(get_db),
    id: int,
    subject_in: SubjectUpdate,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    subject = db.query(Subject).filter(Subject.id == id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role != UserRole.admin and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    update_data = subject_in.model_dump(exclude_unset=True)
    if "code" in update_data:
        existing = db.query(Subject).filter(Subject.code == update_data["code"], Subject.id != id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Subject code already exists")
            
    for field, value in update_data.items():
        setattr(subject, field, value)
        
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject

@router.delete("/{id}")
def delete_subject(
    *,
    db: Session = Depends(get_db),
    id: int,
    current_user: User = Depends(get_current_active_teacher),
) -> Any:
    subject = db.query(Subject).filter(Subject.id == id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role != UserRole.admin and subject.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
        
    db.delete(subject)
    db.commit()
    return {"status": "success", "detail": "Subject deleted"}
