"""add content_hash to chunks

Revision ID: 4c6ccf7ca92c
Revises: 2d5892e787a9
Create Date: 2026-08-24 18:39:58.857395+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c6ccf7ca92c'
down_revision: Union[str, None] = '2d5892e787a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunks_docling",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "idx_chunks_content_hash",
        "document_chunks_docling",
        ["content_hash"],
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_content_hash", table_name="document_chunks_docling")
    op.drop_column("document_chunks_docling", "content_hash")
