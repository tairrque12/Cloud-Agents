"""Set Miguel instagram_handle to miguel_tattoos

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE artists SET instagram_handle = 'miguel_tattoos' WHERE slug = 'miguel'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE artists SET instagram_handle = 'txsmichaell_' WHERE slug = 'miguel'"
    )
