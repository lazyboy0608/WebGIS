from datetime import datetime

from app.api.schemas.segy_file import (
    SegyFileCreate,
    SegyFileResponse,
    SegyFileUpdate,
)


def test_create_schema_accepts_valid_data():
    schema = SegyFileCreate(
        filename="test.sgy",
        file_path="/data/test.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=2,
        geometry=None,
    )

    assert schema.filename == "test.sgy"
    assert schema.file_path == "/data/test.sgy"
    assert schema.file_size == 1024
    assert schema.source_crs == "EPSG:4326"
    assert schema.trace_count == 100
    assert schema.line_count == 2
    assert schema.geometry is None


def test_update_schema_accepts_valid_data():
    schema = SegyFileUpdate(
        filename="updated.sgy",
        file_path="/data/updated.sgy",
        file_size=2048,
        source_crs="EPSG:4326",
        trace_count=200,
        line_count=3,
        geometry=None,
    )

    assert schema.filename == "updated.sgy"
    assert schema.file_size == 2048
    assert schema.trace_count == 200
    assert schema.line_count == 3


def test_response_schema_accepts_complete_data():
    now = datetime.now()

    schema = SegyFileResponse(
        id=1,
        filename="test.sgy",
        file_path="/data/test.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=2,
        geometry=None,
        created_at=now,
        updated_at=now,
    )

    assert schema.id == 1
    assert schema.filename == "test.sgy"
    assert schema.created_at == now
    assert schema.updated_at == now