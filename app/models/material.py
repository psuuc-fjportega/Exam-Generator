import enum
from sqlalchemy import Column, Integer, String, Text, Enum, DateTime, ForeignKey, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ProcessingStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"

class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    file_name = Column(String, nullable=False)
    original_file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_path = Column(String, nullable=False)
    
    processing_status = Column(Enum(ProcessingStatus), default=ProcessingStatus.uploaded, nullable=False)
    processing_error = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    analysis_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subject = relationship("Subject", backref="materials")
    uploader = relationship("User", backref="uploaded_materials")
    chunks = relationship("DocumentChunk", back_populates="material", cascade="all, delete-orphan")
