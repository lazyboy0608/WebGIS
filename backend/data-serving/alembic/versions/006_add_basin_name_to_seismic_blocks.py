"""Add basin_name to seismic_blocks

Revision ID: 006_basin_name_seismic_blocks
Revises: 005_add_avatar_url_to_users
Create Date: 2026-09-15 10:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_basin_name_seismic_blocks'
down_revision: Union[str, None] = '005_add_avatar_url_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE seismic_blocks ADD COLUMN IF NOT EXISTS basin_name VARCHAR(255)")


def downgrade() -> None:
    op.drop_column('seismic_blocks', 'basin_name')
