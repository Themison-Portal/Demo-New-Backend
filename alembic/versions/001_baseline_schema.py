"""baseline schema from existing platform

Revision ID: 001
Revises: 
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Schema already applied via schema_dump.sql
    # Intentionally empty — baseline marker only
    pass


def downgrade() -> None:
    pass
