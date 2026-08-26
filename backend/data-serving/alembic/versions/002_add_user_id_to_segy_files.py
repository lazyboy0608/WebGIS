"""Add user_id column to segy_files table

Revision ID: 002_add_user_id_to_segy_files
Revises: 001_create_users_table
Create Date: 2026-08-25 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_user_id_to_segy_files'
down_revision: Union[str, None] = '001_create_users_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('segy_files', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_segy_files_user_id_users',
        'segy_files',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    op.create_index(op.f('ix_segy_files_user_id'), 'segy_files', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_segy_files_user_id'), table_name='segy_files')
    op.drop_constraint('fk_segy_files_user_id_users', 'segy_files', type_='foreignkey')
    op.drop_column('segy_files', 'user_id')
