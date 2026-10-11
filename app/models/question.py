import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, Float, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.examination_blueprint import QuestionType, QuestionDifficulty


class QuestionStatus(str, enum.Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"


class GenerationMethod(str, enum.Enum):
    ai = "ai"
    manual = "manual"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False, index=True)
    difficulty = Column(Enum(QuestionDifficulty), nullable=False, index=True)
    explanation = Column(Text, nullable=True)
    status = Column(Enum(QuestionStatus), default=QuestionStatus.draft, nullable=False, index=True)
    generation_method = Column(Enum(GenerationMethod), default=GenerationMethod.manual, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String, nullable=True)

    validation_confidence = Column(Float, nullable=True)
    source_supported = Column(Boolean, nullable=True)
    validation_issues = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subject = relationship("Subject")
    creator = relationship("User")
    choices = relationship(
        "QuestionChoice",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionChoice.choice_order",
    )
    sources = relationship(
        "QuestionSource",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    exam_links = relationship(
        "ExaminationQuestion",
        back_populates="question",
        cascade="all, delete-orphan",
    )
