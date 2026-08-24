from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from geoalchemy2 import Geometry

from app.infrastructure.database.base import Base


class SeismicTraceModel(Base):
    __tablename__ = "seismic_traces"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    trace_index: Mapped[int] = mapped_column(
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

    shot_point_id: Mapped[int] = mapped_column(
        ForeignKey(
            "seismic_shot_points.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )