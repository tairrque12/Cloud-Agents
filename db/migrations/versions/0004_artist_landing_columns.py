"""artist landing page columns and Miguel slug

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-24

Adds optional artist profile columns if missing (does not alter existing columns).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS slug TEXT")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS artists_slug_unique_idx ON artists (slug)"
    )
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS bio TEXT")
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS specialties JSONB")
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS pricing_tiers JSONB")
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS notes TEXT")
    op.execute("ALTER TABLE artists ADD COLUMN IF NOT EXISTS scheduling_tool TEXT")
    op.execute(
        "ALTER TABLE artists ADD COLUMN IF NOT EXISTS scheduling_tool_other TEXT"
    )
    op.execute(
        "ALTER TABLE artists ADD COLUMN IF NOT EXISTS profile_photo_url TEXT"
    )
    op.execute("UPDATE artists SET slug = 'miguel' WHERE name = 'Miguel'")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS artists_slug_unique_idx")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS profile_photo_url")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS scheduling_tool_other")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS scheduling_tool")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS notes")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS pricing_tiers")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS specialties")
    op.execute("ALTER TABLE artists DROP COLUMN IF EXISTS bio")
    # Do not drop slug — it existed before this migration on most databases.
