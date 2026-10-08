import enum
from sqlalchemy import Column, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    true_false = "true_false"
    identification = "identification"
    essay = "essay"
    matching = "matching"

class QuestionDifficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class ExaminationBlueprint(Base):
    __tablename__ = "examination_blueprints"

    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(QuestionDifficulty), nullable=False)
    quantity = Column(Integer, nullable=False)
    points = Column(Integer, nullable=False)

    examination = relationship("Examination", back_populates="blueprints")
