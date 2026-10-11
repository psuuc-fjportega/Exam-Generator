from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.material import ProcessingStatus
from app.models.examination_blueprint import QuestionDifficulty

class QuestionTypeDistribution(BaseModel):
    multiple_choice: int = 0
    true_false: int = 0
    identification: int = 0
    essay: int = 0
    matching: int = 0

class DocumentStats(BaseModel):
    chunk_count: int = 0
    total_tokens: int = 0
    total_characters: int = 0
    estimated_words: int = 0
    file_type: str = ""
    original_file_name: str = ""

class DocumentAnalysis(BaseModel):
    title_suggestion: str
    summary: str
    key_topics: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    learning_objectives: List[str] = Field(default_factory=list)
    estimated_difficulty: QuestionDifficulty = QuestionDifficulty.medium
    difficulty_reasoning: str = ""
    recommended_total_questions: int = 10
    recommended_time_minutes: int = 60
    recommended_distribution: QuestionTypeDistribution = Field(default_factory=QuestionTypeDistribution)
    document_stats: Optional[DocumentStats] = None

class MaterialBase(BaseModel):
    subject_id: int

class MaterialCreate(MaterialBase):
    file_name: str
    original_file_name: str
    file_type: str
    file_size: int
    file_path: str

class MaterialResponse(MaterialBase):
    id: int
    uploaded_by: int
    original_file_name: str
    file_type: str
    file_size: int
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    summary: Optional[str] = None
    analysis_json: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class MaterialAnalysisResponse(BaseModel):
    material: MaterialResponse
    analysis: DocumentAnalysis
