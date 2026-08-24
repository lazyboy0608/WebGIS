"""create seismic persistence tables

Revision ID: b9725ecf6d0c
Revises: a053a35c11a5
Create Date: 2026-08-18 11:24:26.726473

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = 'b9725ecf6d0c'
down_revision: Union[str, Sequence[str], None] = 'a053a35c11a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create seismic persistence tables."""

    op.create_table(
        "seismic_lines",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "line_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "segy_file_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="LINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=False,
        ),
        sa.Column(
            "point_count",
            sa.Integer(),
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
            ["segy_file_id"],
            ["segy_files.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "seismic_shot_points",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "shot_point_number",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "segy_file_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "seismic_line_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column(
            "trace_count",
            sa.Integer(),
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
            ["segy_file_id"],
            ["segy_files.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["seismic_line_id"],
            ["seismic_lines.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "seismic_traces",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "trace_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "segy_file_id",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "seismic_line_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "shot_point_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "geometry",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
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
        sa.ForeignKeyConstraint(
            ["segy_file_id"],
            ["segy_files.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["seismic_line_id"],
            ["seismic_lines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["shot_point_id"],
            ["seismic_shot_points.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

def downgrade() -> None:
    """Drop seismic persistence tables."""

    op.drop_table("seismic_traces")

    op.drop_table("seismic_shot_points")

    op.drop_table("seismic_lines")
