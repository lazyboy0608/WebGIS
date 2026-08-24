from geoalchemy2 import Geometry

from app.infrastructure.database.models.segy_file_model import (
    SegyFileModel,
)


def test_segy_file_model_table_name() -> None:
    assert SegyFileModel.__tablename__ == "segy_files"


def test_segy_file_model_columns() -> None:
    columns = SegyFileModel.__table__.columns

    assert "id" in columns
    assert "filename" in columns
    assert "file_path" in columns
    assert "file_size" in columns
    assert "source_crs" in columns
    assert "trace_count" in columns
    assert "line_count" in columns
    assert "geometry" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_segy_file_geometry() -> None:
    geometry = SegyFileModel.__table__.columns.geometry.type

    assert isinstance(geometry, Geometry)
    assert geometry.geometry_type == "MULTILINESTRING"
    assert geometry.srid == 4326