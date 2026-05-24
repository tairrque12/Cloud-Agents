"""artist application fields and pending status

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE artists DROP CONSTRAINT IF EXISTS artists_status_check")
    op.execute(
        "ALTER TABLE artists ADD CONSTRAINT artists_status_check "
        "CHECK (status IN ('active', 'inactive', 'suspended', 'pending'))"
    )
    op.add_column("artists", sa.Column("profile_photo_url", sa.Text(), nullable=True))
    op.add_column(
        "artists", sa.Column("scheduling_tool", sa.String(length=100), nullable=True)
    )
    op.add_column(
        "artists", sa.Column("scheduling_tool_other", sa.Text(), nullable=True)
    )
    op.add_column(
        "artists", sa.Column("application_notes", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("artists", "application_notes")
    op.drop_column("artists", "scheduling_tool_other")
    op.drop_column("artists", "scheduling_tool")
    op.drop_column("artists", "profile_photo_url")
    op.execute("ALTER TABLE artists DROP CONSTRAINT IF EXISTS artists_status_check")
    op.execute(
        "ALTER TABLE artists ADD CONSTRAINT artists_status_check "
        "CHECK (status IN ('active', 'inactive', 'suspended'))"
    )
