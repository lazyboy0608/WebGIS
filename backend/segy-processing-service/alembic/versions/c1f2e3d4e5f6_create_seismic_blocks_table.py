"""create seismic blocks table

Revision ID: c1f2e3d4e5f6
Revises: b9725ecf6d0c
Create Date: 2026-09-04 14:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'c1f2e3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'b9725ecf6d0c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create seismic_blocks table and indexes."""
    op.create_table(
        "seismic_blocks",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "block_code",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "operator",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "area_km2",
            sa.Float(),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "source_file",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POLYGON",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["seismic_blocks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index on block_code
    op.create_index(
        "seismic_blocks_code_idx",
        "seismic_blocks",
        ["block_code"],
        unique=False,
    )

    # Index on status
    op.create_index(
        "seismic_blocks_status_idx",
        "seismic_blocks",
        ["status"],
        unique=False,
    )

    # Index on parent_id
    op.create_index(
        "seismic_blocks_parent_idx",
        "seismic_blocks",
        ["parent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop seismic_blocks table."""
    op.drop_index("seismic_blocks_parent_idx", table_name="seismic_blocks")
    op.drop_index("seismic_blocks_status_idx", table_name="seismic_blocks")
    op.drop_index("seismic_blocks_code_idx", table_name="seismic_blocks")
    op.drop_table("seismic_blocks")
