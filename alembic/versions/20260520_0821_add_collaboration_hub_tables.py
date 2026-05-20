"""add collaboration hub tables

Revision ID: a8f126cb30cc
Revises: 001
Create Date: 2026-05-20 08:21:52.292484+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a8f126cb30cc"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─────────────────────────────────────────
    # NEW: collaboration_threads
    # ─────────────────────────────────────────
    op.create_table(
        "collaboration_threads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("trial_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("thread_type", sa.Text(), nullable=False),
        sa.Column("anchors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.UUID(), nullable=True),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("ai_draft_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["resolved_by"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trial_id"], ["trials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─────────────────────────────────────────
    # NEW: collaboration_thread_messages
    # ─────────────────────────────────────────
    op.create_table(
        "collaboration_thread_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("thread_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["sender_id"], ["profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["thread_id"], ["collaboration_threads.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─────────────────────────────────────────
    # NEW: inbox_messages
    # ─────────────────────────────────────────
    op.create_table(
        "inbox_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("trial_id", sa.UUID(), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("sender_name", sa.Text(), nullable=False),
        sa.Column("sender_email", sa.Text(), nullable=True),
        sa.Column("to_addresses", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("cc_addresses", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("labels", sa.ARRAY(sa.Text()), nullable=False),
        sa.Column("folder", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("is_starred", sa.Boolean(), nullable=False),
        sa.Column("related_thread_id", sa.UUID(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["related_thread_id"], ["collaboration_threads.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["trial_id"], ["trials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ─────────────────────────────────────────
    # NEW: direct_messages
    # ─────────────────────────────────────────
    op.create_table(
        "direct_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("trial_id", sa.UUID(), nullable=True),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("recipient_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trial_id"], ["trials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("direct_messages")
    op.drop_table("inbox_messages")
    op.drop_table("collaboration_thread_messages")
    op.drop_table("collaboration_threads")
