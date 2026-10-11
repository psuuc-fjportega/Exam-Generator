from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.examination_blueprint import QuestionDifficulty, QuestionType
from app.models.question import GenerationMethod, QuestionStatus


class AIChoiceOutput(BaseModel):
    text: str
    is_correct: bool


class AIQuestionOutput(BaseModel):
    question_text: str
    question_type: QuestionType
    difficulty: QuestionDifficulty
    topic: str = ""
    choices: List[AIChoiceOutput] = Field(default_factory=list)
    explanation: str = ""
    source_chunk_ids: List[int] = Field(default_factory=list)


class AIGenerationOutput(BaseModel):
    questions: List[AIQuestionOutput]


class QuestionChoiceResponse(BaseModel):
    id: int
    choice_text: str
    choice_order: int
    is_correct: bool

    model_config = {"from_attributes": True}


class QuestionSourceResponse(BaseModel):
    id: int
    chunk_id: int
    relevance_score: Optional[float] = None
    page_number: Optional[str] = None
    section_title: Optional[str] = None
    excerpt: Optional[str] = None

    model_config = {"from_attributes": True}


class ValidationResultResponse(BaseModel):
    valid: bool
    confidence: float
    issues: List[str]
    source_supported: bool
    recommended_status: str
    recommended_action: str = "review"
    relevance_scores: dict[int, float] = Field(default_factory=dict)


class QuestionResponse(BaseModel):
    id: int
    subject_id: int
    question_text: str
    question_type: QuestionType
    difficulty: QuestionDifficulty
    topic: Optional[str] = None
    explanation: Optional[str] = None
    status: QuestionStatus
    generation_method: GenerationMethod
    created_by: int
    validation_confidence: Optional[float] = None
    source_supported: Optional[bool] = None
    validation_issues: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None
    choices: List[QuestionChoiceResponse] = Field(default_factory=list)
    sources: List[QuestionSourceResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class QuestionValidateResponse(BaseModel):
    question: QuestionResponse
    validation: ValidationResultResponse
