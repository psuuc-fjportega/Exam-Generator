import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class ExamStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    published = "published"
    archived = "archived"

class Examination(Base):
    __tablename__ = "examinations"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    total_questions = Column(Integer, nullable=False)
    time_limit_minutes = Column(Integer, nullable=False)
    passing_score = Column(Integer, nullable=False)
    
    status = Column(Enum(ExamStatus), default=ExamStatus.draft, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    subject = relationship("Subject")
    creator = relationship("User")
    blueprints = relationship("ExaminationBlueprint", back_populates="examination", cascade="all, delete-orphan")
