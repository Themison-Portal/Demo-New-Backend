"""add FE-only document fields to trial_documents

Migrates the FE `protocols` table's document metadata onto the BE
`trial_documents` table so the BE can become the single source of truth for
trial documents. All columns are additive and nullable (backward compatible).

Revision ID: c7f3a9e21b48
Revises: 0b36ae7e7c90
Create Date: 2026-06-17 09:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7f3a9e21b48"
down_revision: Union[str, None] = "0b36ae7e7c90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Free-text category (e.g. "Protocol", "Amendments", "ICF") — intentionally
    # separate from the document_type enum; drives the FE Documents-hub tabs.
    op.add_column(
        "trial_documents", sa.Column("category", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "trial_documents",
        sa.Column("document_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "trial_documents",
        sa.Column("amendment_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "trial_documents",
        sa.Column("release_date", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "trial_documents",
        sa.Column(
            "is_current", sa.Boolean(), nullable=True, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "trial_documents",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "trial_documents",
        sa.Column("source_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "trial_documents",
        sa.Column("source_reference", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("trial_documents", "source_reference")
    op.drop_column("trial_documents", "source_type")
    op.drop_column("trial_documents", "archived_at")
    op.drop_column("trial_documents", "is_current")
    op.drop_column("trial_documents", "release_date")
    op.drop_column("trial_documents", "amendment_version")
    op.drop_column("trial_documents", "document_version")
    op.drop_column("trial_documents", "category")
