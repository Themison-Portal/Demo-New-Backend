"""add organization_id to chunks

Revision ID: 910b22c6437f
Revises: b7d1e4f9a2c5
Create Date: 2026-07-23 08:53:57.095621+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '910b22c6437f'
down_revision: Union[str, None] = 'b7d1e4f9a2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunks_docling",
        sa.Column("organization_id", UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE document_chunks_docling AS c
        SET organization_id = t.organization_id
        FROM trial_documents AS d
        JOIN trials AS t ON t.id = d.trial_id
        WHERE c.document_id = d.id
          AND c.organization_id IS NULL
        """
    )

    conn = op.get_bind()
    orphaned = conn.execute(
        sa.text(
            "SELECT count(*) FROM document_chunks_docling WHERE organization_id IS NULL"
        )
    ).scalar()
    if orphaned:
        raise RuntimeError(
            f"{orphaned} chunk(s) could not be backfilled — investigate before re-running."
        )

    op.alter_column(
        "document_chunks_docling",
        "organization_id",
        nullable=False,
    )

    op.create_index(
        "idx_chunks_organization_id",
        "document_chunks_docling",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_organization_id", table_name="document_chunks_docling")
    op.drop_column("document_chunks_docling", "organization_id")
