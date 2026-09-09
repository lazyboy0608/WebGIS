from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from geoalchemy2 import Geometry

from app.infrastructure.database.base import Base


class SeismicBlockModel(Base):
    __tablename__ = "seismic_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    block_code: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    operator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    basin_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    area_km2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seismic_blocks.id", ondelete="SET NULL"), nullable=True, index=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    geometry = mapped_column(Geometry(geometry_type="POLYGON", srid=4326, spatial_index=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

