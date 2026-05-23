"""add_selected_date_to_intakes

Revision ID: 0001
Revises:
Create Date: 2026-05-23

Adds a dedicated selected_date column to intakes.
Migrates existing data out of the emotional_tone_note hack
(rows where emotional_tone_note starts with "selected_date:").
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the dedicated column
    op.add_column(
        'intakes',
        sa.Column('selected_date', sa.String(200), nullable=True)
    )

    # Migrate data: extract "Saturday · June 6" from "selected_date:Saturday · June 6"
    op.execute("""
        UPDATE intakes
        SET selected_date = SUBSTRING(emotional_tone_note FROM 'selected_date:(.+)$')
        WHERE emotional_tone_note LIKE 'selected_date:%'
    """)

    # Clear the hack from emotional_tone_note so the field is free for its
    # original purpose (emotional tone notes from the classifier)
    op.execute("""
        UPDATE intakes
        SET emotional_tone_note = NULL
        WHERE emotional_tone_note LIKE 'selected_date:%'
    """)


def downgrade() -> None:
    # Restore the hack before dropping the column so no data is lost
    op.execute("""
        UPDATE intakes
        SET emotional_tone_note = 'selected_date:' || selected_date
        WHERE selected_date IS NOT NULL
    """)

    op.drop_column('intakes', 'selected_date')
