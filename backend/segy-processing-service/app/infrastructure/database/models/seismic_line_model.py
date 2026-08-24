from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from geoalchemy2 import Geometry

from app.infrastructure.database.base import Base


class SeismicLineModel(Base):
    __tablename__ = "seismic_lines"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    line_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    segy_file_id: Mapped[int] = mapped_column(
        ForeignKey(
            "segy_files.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="LINESTRING",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    point_count: Mapped[int] = mapped_column(
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