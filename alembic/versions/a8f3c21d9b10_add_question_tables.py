"""Add question bank and source traceability tables

Revision ID: a8f3c21d9b10
Revises: 37cb541f5e48
Create Date: 2026-08-21 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f3c21d9b10"
down_revision: Union[str, Sequence[str], None] = "37cb541f5e48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.Enum("multiple_choice", "true_false", "identification", "essay", name="questiontype"), nullable=False),
        sa.Column("difficulty", sa.Enum("easy", "medium", "hard", name="questiondifficulty"), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("draft", "review", "approved", "rejected", "archived", name="questionstatus"), nullable=False),
        sa.Column("generation_method", sa.Enum("ai", "manual", name="generationmethod"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("validation_confidence", sa.Float(), nullable=True),
        sa.Column("source_supported", sa.Boolean(), nullable=True),
        sa.Column("validation_issues", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_id"), "questions", ["id"], unique=False)
    op.create_index(op.f("ix_questions_subject_id"), "questions", ["subject_id"], unique=False)
    op.create_index(op.f("ix_questions_question_type"), "questions", ["question_type"], unique=False)
    op.create_index(op.f("ix_questions_difficulty"), "questions", ["difficulty"], unique=False)
    op.create_index(op.f("ix_questions_status"), "questions", ["status"], unique=False)

    op.create_table(
        "question_choices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("choice_text", sa.Text(), nullable=False),
        sa.Column("choice_order", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_question_choices_id"), "question_choices", ["id"], unique=False)
    op.create_index(op.f("ix_question_choices_question_id"), "question_choices", ["question_id"], unique=False)

    op.create_table(
        "question_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id", "chunk_id", name="uq_question_source_chunk"),
    )
    op.create_index(op.f("ix_question_sources_id"), "question_sources", ["id"], unique=False)
    op.create_index(op.f("ix_question_sources_question_id"), "question_sources", ["question_id"], unique=False)
    op.create_index(op.f("ix_question_sources_chunk_id"), "question_sources", ["chunk_id"], unique=False)

    op.create_table(
        "examination_questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("examination_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("question_order", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["examination_id"], ["examinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("examination_id", "question_id", name="uq_exam_question"),
    )
    op.create_index(op.f("ix_examination_questions_id"), "examination_questions", ["id"], unique=False)
    op.create_index(op.f("ix_examination_questions_examination_id"), "examination_questions", ["examination_id"], unique=False)
    op.create_index(op.f("ix_examination_questions_question_id"), "examination_questions", ["question_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_examination_questions_question_id"), table_name="examination_questions")
    op.drop_index(op.f("ix_examination_questions_examination_id"), table_name="examination_questions")
    op.drop_index(op.f("ix_examination_questions_id"), table_name="examination_questions")
    op.drop_table("examination_questions")
    op.drop_index(op.f("ix_question_sources_chunk_id"), table_name="question_sources")
    op.drop_index(op.f("ix_question_sources_question_id"), table_name="question_sources")
    op.drop_index(op.f("ix_question_sources_id"), table_name="question_sources")
    op.drop_table("question_sources")
    op.drop_index(op.f("ix_question_choices_question_id"), table_name="question_choices")
    op.drop_index(op.f("ix_question_choices_id"), table_name="question_choices")
    op.drop_table("question_choices")
    op.drop_index(op.f("ix_questions_status"), table_name="questions")
    op.drop_index(op.f("ix_questions_difficulty"), table_name="questions")
    op.drop_index(op.f("ix_questions_question_type"), table_name="questions")
    op.drop_index(op.f("ix_questions_subject_id"), table_name="questions")
    op.drop_index(op.f("ix_questions_id"), table_name="questions")
    op.drop_table("questions")
