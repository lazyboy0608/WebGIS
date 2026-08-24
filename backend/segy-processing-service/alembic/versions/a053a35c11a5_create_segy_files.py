
"""create segy_files

Revision ID: a053a35c11a5
Revises:
Create Date: 2026-08-14 14:41:37.649443

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision: str = "a053a35c11a5"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create segy_files table."""

    op.create_table(
        "segy_files",

        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "filename",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "file_path",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "file_size",
            sa.BigInteger(),
            nullable=False,
        ),

        sa.Column(
            "source_crs",
            sa.String(255),
            nullable=False,
        ),

        sa.Column(
            "trace_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "line_count",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "geometry",
            Geometry(
                geometry_type="MULTILINESTRING",
                srid=4326,
                spatial_index=True,
            ),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop segy_files table."""

    op.drop_table("segy_files")

