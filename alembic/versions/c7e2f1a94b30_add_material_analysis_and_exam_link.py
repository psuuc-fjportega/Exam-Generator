"""add_material_analysis_and_exam_link

Revision ID: c7e2f1a94b30
Revises: f34b691c87f1
Create Date: 2026-10-09 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e2f1a94b30'
down_revision: Union[str, Sequence[str], None] = 'f34b691c87f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safely add columns if not already present
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    mat_cols = [c['name'] for c in inspector.get_columns('materials')]
    if 'summary' not in mat_cols:
        op.add_column('materials', sa.Column('summary', sa.Text(), nullable=True))
    if 'analysis_json' not in mat_cols:
        op.add_column('materials', sa.Column('analysis_json', sa.Text(), nullable=True))

    exam_cols = [c['name'] for c in inspector.get_columns('examinations')]
    if 'material_id' not in exam_cols:
        op.add_column('examinations', sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id', ondelete='SET NULL'), nullable=True))

    q_cols = [c['name'] for c in inspector.get_columns('questions')]
    if 'topic' not in q_cols:
        op.add_column('questions', sa.Column('topic', sa.String(), nullable=True))


def downgrade() -> None:
    pass
