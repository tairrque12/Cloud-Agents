"""Ensure artist ORM columns exist on production

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-24

Neon production was missing columns that the Artist model maps but earlier
Alembic revisions did not add with IF NOT EXISTS (pricing_config and
admin_secret were only in raw SQL). Idempotent adds for onboarding and
get_miguel full-row loads.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS pricing_config JSONB")
    op.execute(
        "ALTER TABLE artists ADD COLUMN IF NOT EXISTS availability_config JSONB"
    )
    op.execute(
        "ALTER TABLE artists ADD COLUMN IF NOT EXISTS admin_secret VARCHAR(64)"
    )
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS application_notes TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS application_notes")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS admin_secret")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS availability_config")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS pricing_config")
