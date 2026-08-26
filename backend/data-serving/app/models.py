from datetime import date, datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # 'user' | 'admin'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SegyFileModel(Base):
    __tablename__ = "segy_files"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    source_crs: Mapped[str] = mapped_column(String(255), nullable=False)
    trace_count: Mapped[int] = mapped_column(Integer, nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    geometry = mapped_column(Geometry(geometry_type="MULTILINESTRING", srid=4326, spatial_index=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SeismicLineModel(Base):
    __tablename__ = "seismic_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    line_id: Mapped[str] = mapped_column(String(255), nullable=False)
    segy_file_id: Mapped[int] = mapped_column(ForeignKey("segy_files.id", ondelete="CASCADE"), nullable=False)
    geometry = mapped_column(Geometry(geometry_type="LINESTRING", srid=4326, spatial_index=True), nullable=False)
    point_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SeismicShotPointModel(Base):
    __tablename__ = "seismic_shot_points"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shot_point_number: Mapped[int] = mapped_column(Integer, nullable=False)
    segy_file_id: Mapped[int] = mapped_column(ForeignKey("segy_files.id", ondelete="CASCADE"), nullable=False)
    seismic_line_id: Mapped[int] = mapped_column(ForeignKey("seismic_lines.id", ondelete="CASCADE"), nullable=True)
    geometry = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    trace_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class SeismicTraceModel(Base):
    __tablename__ = "seismic_traces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trace_index: Mapped[int] = mapped_column(Integer, nullable=False)
    segy_file_id: Mapped[int] = mapped_column(ForeignKey("segy_files.id", ondelete="CASCADE"), nullable=False)
    seismic_line_id: Mapped[int] = mapped_column(ForeignKey("seismic_lines.id", ondelete="CASCADE"), nullable=True)
    shot_point_id: Mapped[int] = mapped_column(ForeignKey("seismic_shot_points.id", ondelete="SET NULL"), nullable=True)
    geometry = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
