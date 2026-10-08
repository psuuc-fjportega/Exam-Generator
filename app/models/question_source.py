from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuestionSource(Base):
    __tablename__ = "question_sources"
    __table_args__ = (
        UniqueConstraint("question_id", "chunk_id", name="uq_question_source_chunk"),
    )

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    relevance_score = Column(Float, nullable=True)

    question = relationship("Question", back_populates="sources")
    chunk = relationship("DocumentChunk")
