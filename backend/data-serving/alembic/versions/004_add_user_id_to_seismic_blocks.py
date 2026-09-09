"""Add user_id column to seismic_blocks table

Revision ID: 004_add_user_id_to_seismic_blocks
Revises: 003_add_refresh_token_hash
Create Date: 2026-09-09 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_user_id_to_seismic_blocks'
down_revision: Union[str, None] = '003_add_refresh_token_hash'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('seismic_blocks', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_seismic_blocks_user_id_users',
        'seismic_blocks',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(op.f('ix_seismic_blocks_user_id'), 'seismic_blocks', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_seismic_blocks_user_id'), table_name='seismic_blocks')
    op.drop_constraint('fk_seismic_blocks_user_id_users', 'seismic_blocks', type_='foreignkey')
    op.drop_column('seismic_blocks', 'user_id')
