"""add FE-owned trial fields + demo_mode/slug to trials

Migrates the FE MySQL `trials` table's metadata onto the BE `trials` table so the
BE can become the single source of truth for trials. `slug` + `demo_mode`
partition the FE's demo datasets and let the BFF resolve the client's bare slug.
All columns are additive and nullable (backward compatible).

Revision ID: e2b8c4f6a1d9
Revises: c7f3a9e21b48
Create Date: 2026-06-18 10:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e2b8c4f6a1d9"
down_revision: Union[str, None] = "c7f3a9e21b48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TEXT_COLS = [
    "slug",
    "demo_mode",
    "protocol_number",
    "investigational_product",
    "indication",
    "nct_number",
    "current_version",
    "amendment_version",
    "release_date",
    "sample_size",
    "number_of_sites",
    "study_duration",
    "study_design_type",
    "primary_objective",
    "primary_endpoint",
    "principal_investigator",
]
_INT_COLS = ["enrolled_patients", "target_patients", "completion_percentage"]


def upgrade() -> None:
    for col in _TEXT_COLS:
        op.add_column("trials", sa.Column(col, sa.Text(), nullable=True))
    for col in _INT_COLS:
        op.add_column("trials", sa.Column(col, sa.Integer(), nullable=True))
    op.create_index("ix_trials_slug", "trials", ["slug"])
    op.create_index("ix_trials_demo_mode", "trials", ["demo_mode"])
    # Logical identity for a demo trial: (slug, demo_mode) within an org. NULL
    # slugs (existing rows) are distinct in Postgres unique indexes, so this is
    # safe to add without backfilling.
    op.create_index(
        "uq_trials_slug_mode_org",
        "trials",
        ["slug", "demo_mode", "organization_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_trials_slug_mode_org", table_name="trials")
    op.drop_index("ix_trials_demo_mode", table_name="trials")
    op.drop_index("ix_trials_slug", table_name="trials")
    for col in reversed(_INT_COLS):
        op.drop_column("trials", col)
    for col in reversed(_TEXT_COLS):
        op.drop_column("trials", col)
