from pydantic import BaseModel, model_validator
from typing import Optional, List
from datetime import datetime
from app.models.examination import ExamStatus
from app.models.examination_blueprint import QuestionType, QuestionDifficulty

class BlueprintBase(BaseModel):
    question_type: QuestionType
    difficulty: QuestionDifficulty
    quantity: int
    points: int

class BlueprintCreate(BlueprintBase):
    pass

class BlueprintResponse(BlueprintBase):
    id: int
    examination_id: int
    
    model_config = {"from_attributes": True}

class ExaminationBase(BaseModel):
    subject_id: int
    title: str
    description: Optional[str] = None
    total_questions: int
    time_limit_minutes: int
    passing_score: int

class ExaminationCreate(ExaminationBase):
    blueprints: List[BlueprintCreate]
    
    @model_validator(mode='after')
    def validate_totals(self) -> 'ExaminationCreate':
        if not self.blueprints:
            raise ValueError("At least one blueprint definition is required.")
        total_qty = sum(bp.quantity for bp in self.blueprints)
        if total_qty != self.total_questions:
            raise ValueError(f"Blueprint total quantity ({total_qty}) does not match examination total_questions ({self.total_questions}).")
        return self

class ExaminationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ExamStatus] = None

class ExaminationResponse(ExaminationBase):
    id: int
    created_by: int
    status: ExamStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    blueprints: List[BlueprintResponse] = []

    model_config = {"from_attributes": True}
