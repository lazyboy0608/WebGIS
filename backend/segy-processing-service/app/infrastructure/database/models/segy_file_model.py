from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from geoalchemy2 import Geometry

from app.infrastructure.database.base import Base
from app.infrastructure.database.models.user_model import UserModel  # noqa: F401


class SegyFileModel(Base):
    __tablename__ = "segy_files"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    source_crs: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    trace_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    line_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    geometry = mapped_column(
        Geometry(
            geometry_type="MULTILINESTRING",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
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