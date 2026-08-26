"""Add refresh_token_hash column to users table

Revision ID: 003_add_refresh_token_hash
Revises: 002_add_user_id_to_segy_files
Create Date: 2026-08-26 09:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_refresh_token_hash'
down_revision: Union[str, None] = '002_add_user_id_to_segy_files'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('refresh_token_hash', sa.String(255), nullable=True, default=None),
    )


def downgrade() -> None:
    op.drop_column('users', 'refresh_token_hash')
