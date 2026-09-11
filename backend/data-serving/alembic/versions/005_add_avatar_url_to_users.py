"""Add avatar_url column to users table

Revision ID: 005_add_avatar_url_to_users
Revises: 004_add_user_id_to_seismic_blocks
Create Date: 2026-09-11 11:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_add_avatar_url_to_users'
down_revision: Union[str, None] = '004_add_user_id_to_seismic_blocks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('avatar_url', sa.Text(), nullable=True, default=None),
    )


def downgrade() -> None:
    op.drop_column('users', 'avatar_url')
