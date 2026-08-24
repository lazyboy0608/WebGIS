from uuid import uuid4

from geoalchemy2.shape import from_shape
from shapely.geometry import MultiLineString
from sqlalchemy import func

from app.domain.models.segy_file import SegyFile
from app.infrastructure.database.models.segy_file_model import SegyFileModel
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)
from app.infrastructure.database.session import SessionLocal


def test_create_and_read_segy_file():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        segy_file = SegyFile(
            id=None,
            filename="repository_test.sgy",
            file_path="/tmp/repository_test.sgy",
            file_size=1024,
            source_crs="EPSG:4326",
            trace_count=100,
            line_count=2,
            geometry="MULTILINESTRING((-92.55 28.13,-92.54 28.14))",
        )

        created = repository.create(segy_file)

        assert created.id is not None
        assert created.filename == "repository_test.sgy"

        found = repository.get_by_id(created.id)

        assert found is not None
        assert found.filename == "repository_test.sgy"
        assert found.file_size == 1024


def test_get_by_filename():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        segy_file = SegyFile(
            id=None,
            filename="find_by_name.sgy",
            file_path="/tmp/find_by_name.sgy",
            file_size=2048,
            source_crs="EPSG:4326",
            trace_count=200,
            line_count=3,
        )

        repository.create(segy_file)

        found = repository.get_by_filename("find_by_name.sgy")

        assert found is not None
        assert found.filename == "find_by_name.sgy"
        assert found.file_size == 2048


def test_list_segy_files():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        first = repository.create(
            SegyFile(
                id=None,
                filename="list_1.sgy",
                file_path="/tmp/list_1.sgy",
                file_size=100,
                source_crs="EPSG:4326",
                trace_count=10,
                line_count=1,
            )
        )

        second = repository.create(
            SegyFile(
                id=None,
                filename="list_2.sgy",
                file_path="/tmp/list_2.sgy",
                file_size=200,
                source_crs="EPSG:4326",
                trace_count=20,
                line_count=2,
            )
        )

        files = repository.list_all()

        ids = {file.id for file in files}

        assert first.id in ids
        assert second.id in ids


def test_update_segy_file():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        segy_file = SegyFile(
            id=None,
            filename="before_update.sgy",
            file_path="/tmp/before_update.sgy",
            file_size=100,
            source_crs="EPSG:4326",
            trace_count=10,
            line_count=1,
        )

        created = repository.create(segy_file)

        session.commit()

        updated = SegyFile(
            id=created.id,
            filename="after_update.sgy",
            file_path="/tmp/after_update.sgy",
            file_size=999,
            source_crs="EPSG:3857",
            trace_count=99,
            line_count=9,
        )

        result = repository.update(updated)

        session.commit()

        assert result.id == created.id
        assert result.filename == "after_update.sgy"
        assert result.file_size == 999
        assert result.source_crs == "EPSG:3857"
        assert result.trace_count == 99
        assert result.line_count == 9

        repository.delete(result.id)
        session.commit()


def test_delete_segy_file():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        segy_file = SegyFile(
            id=None,
            filename="delete_test.sgy",
            file_path="/tmp/delete_test.sgy",
            file_size=100,
            source_crs="EPSG:4326",
            trace_count=10,
            line_count=1,
        )

        created = repository.create(segy_file)

        assert created.id is not None

        repository.delete(created.id)

        found = repository.get_by_id(created.id)

        assert found is None

def test_intersects_polygon():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        segy_file = SegyFile(
            id=None,
            filename="spatial_test.sgy",
            file_path="/tmp/spatial_test.sgy",
            file_size=1000,
            source_crs="NAD_1927_StatePlane_Louisiana_South_FIPS_1702",
            trace_count=100,
            line_count=1,
            geometry=(
                "MULTILINESTRING("
                "(-92.55 28.13,-92.54 28.14)"
                ")"
            ),
        )

        created = repository.create(segy_file)

        # giữ nguyên phần polygon/query của test hiện tại
        ...