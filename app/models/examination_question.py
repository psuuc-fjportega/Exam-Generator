from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExaminationQuestion(Base):
    __tablename__ = "examination_questions"
    __table_args__ = (
        UniqueConstraint("examination_id", "question_id", name="uq_exam_question"),
    )

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_order = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False, default=1)

    examination = relationship("Examination")
    question = relationship("Question", back_populates="exam_links")
