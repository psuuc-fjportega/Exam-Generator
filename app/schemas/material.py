from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.material import ProcessingStatus

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
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
