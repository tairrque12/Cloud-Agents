"""Repair Miguel instagram_handle on production

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-24

Landing page reads instagram_handle from Neon; some databases still have a
legacy handle. Force canonical miguel_tattoos for Miguel's row.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE artists
        SET instagram_handle = 'miguel_tattoos'
        WHERE slug = 'miguel'
           OR LOWER(TRIM(name)) = 'miguel'
        """
    )


def downgrade() -> None:
    pass
