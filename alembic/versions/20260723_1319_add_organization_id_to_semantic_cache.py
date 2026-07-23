"""add organization_id to semantic cache

Revision ID: 2d5892e787a9
Revises: 910b22c6437f
Create Date: 2026-07-23 13:19:22.508856+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '2d5892e787a9'
down_revision: Union[str, None] = '910b22c6437f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "semantic_cache_responses",
        sa.Column("organization_id", UUID(as_uuid=True), nullable=True),
    )

    op.execute(
        """
        UPDATE semantic_cache_responses AS c
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
            "SELECT count(*) FROM semantic_cache_responses WHERE organization_id IS NULL"
        )
    ).scalar()
    if orphaned:
        # Unlike chunks, cache entries are disposable — safe to just delete
        # orphaned rows rather than blocking the migration, since they're
        # regenerated on the next query anyway.
        conn.execute(
            sa.text("DELETE FROM semantic_cache_responses WHERE organization_id IS NULL")
        )

    op.alter_column(
        "semantic_cache_responses",
        "organization_id",
        nullable=False,
    )

    op.create_index(
        "idx_semantic_cache_organization_id",
        "semantic_cache_responses",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_semantic_cache_organization_id", table_name="semantic_cache_responses")
    op.drop_column("semantic_cache_responses", "organization_id")
