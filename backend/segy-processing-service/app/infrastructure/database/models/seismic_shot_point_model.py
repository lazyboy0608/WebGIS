from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from geoalchemy2 import Geometry

from app.infrastructure.database.base import Base


class SeismicShotPointModel(Base):
    __tablename__ = "seismic_shot_points"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    shot_point_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    segy_file_id: Mapped[int] = mapped_column(
        ForeignKey(
            "segy_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    seismic_line_id: Mapped[int] = mapped_column(
        ForeignKey(
            "seismic_lines.id",
            ondelete="CASCADE",
        ),
        nullable=True,
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    trace_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )