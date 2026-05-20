"""add is_active columns and missing fields

Revision ID: 9ae5a6ca2950
Revises: a8f126cb30cc
Create Date: 2026-05-20 08:54:32.361020+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9ae5a6ca2950"
down_revision: Union[str, None] = "a8f126cb30cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # members.is_active
    op.add_column(
        "members",
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
    )

    # organizations.is_active
    op.add_column("organizations", sa.Column("is_active", sa.Boolean(), nullable=True))

    # profiles.is_active
    op.add_column(
        "profiles",
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
    )

    # invitations.token
    op.add_column("invitations", sa.Column("token", sa.Text(), nullable=True))

    # chat_sessions.document_id and document_name
    op.add_column("chat_sessions", sa.Column("document_id", sa.UUID(), nullable=True))
    op.add_column(
        "chat_sessions",
        sa.Column("document_name", sa.String(length=255), nullable=True),
    )

    # trial_documents.ingestion_status
    op.add_column(
        "trial_documents", sa.Column("ingestion_status", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("trial_documents", "ingestion_status")
    op.drop_column("chat_sessions", "document_name")
    op.drop_column("chat_sessions", "document_id")
    op.drop_column("invitations", "token")
    op.drop_column("profiles", "is_active")
    op.drop_column("organizations", "is_active")
    op.drop_column("members", "is_active")
