"""add superadmin/editor/viewer/reader to organization_member_type enum

The SQLAlchemy models declare the `organization_member_type` enum with
admin/staff/superadmin/editor/viewer (members.py) plus reader (invitations.py),
but the shipped DB type only had {admin, staff}. That drift caused inserts with
roles like "editor" to fail. This migration adds the missing values so the DB
matches the models.

Additive only. Postgres cannot drop enum values without recreating the type, so
`downgrade` is a deliberate no-op. `IF NOT EXISTS` makes `upgrade` idempotent —
safe on databases where these values were already added out-of-band.

Revision ID: b7d1e4f9a2c5
Revises: e2b8c4f6a1d9
Create Date: 2026-07-13 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "b7d1e4f9a2c5"
down_revision: Union[str, None] = "e2b8c4f6a1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_VALUES = ["superadmin", "editor", "viewer", "reader"]


def upgrade() -> None:
    # `ALTER TYPE ... ADD VALUE` cannot run inside a transaction block, so it
    # must execute in an autocommit block. IF NOT EXISTS (Postgres 12+) keeps
    # each statement idempotent.
    with op.get_context().autocommit_block():
        for value in _NEW_VALUES:
            op.execute(
                "ALTER TYPE organization_member_type "
                f"ADD VALUE IF NOT EXISTS '{value}'"
            )


def downgrade() -> None:
    # Enum values cannot be removed in Postgres without recreating the type and
    # rewriting every dependent column; this change is additive and safe to keep.
    pass
