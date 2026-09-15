"""add suggestion_feedback table

Revision ID: c685fd7f75d6
Revises: 4c6ccf7ca92c
Create Date: 2026-08-31 08:13:21.206371+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c685fd7f75d6'
down_revision: Union[str, None] = '4c6ccf7ca92c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suggestion_feedback',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('trial_id', sa.UUID(), nullable=True),
        sa.Column('target_type', sa.String(), nullable=False),
        sa.Column('target_id', sa.String(), nullable=True),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('answer', sa.Text(), nullable=True),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('good', 'needs_work', name='feedbackstatus'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['members.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('suggestion_feedback')
    op.execute('DROP TYPE IF EXISTS feedbackstatus')