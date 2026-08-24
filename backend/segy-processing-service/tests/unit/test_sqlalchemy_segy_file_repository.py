import pytest
from datetime import datetime
from unittest.mock import MagicMock

from app.domain.models.segy_file import SegyFile
from app.infrastructure.database.models.segy_file_model import (
    SegyFileModel,
)
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)


def create_domain_segy_file(
    file_id: int | None = None,
) -> SegyFile:
    return SegyFile(
        id=file_id,
        filename="test.sgy",
        file_path="/data/test.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=2,
        geometry=None,
    )

def create_orm_segy_file(
    file_id: int = 1,
) -> SegyFileModel:
    model = SegyFileModel(
        id=file_id,
        filename="test.sgy",
        file_path="/data/test.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=2,
        geometry=None,
    )

    model.created_at = datetime.now()
    model.updated_at = datetime.now()

    return model

def test_repository_stores_session():
    session = MagicMock()

    repository = SQLAlchemySegyFileRepository(session)

    assert repository.session is session

def test_create_adds_model_to_session():
    session = MagicMock()

    repository = SQLAlchemySegyFileRepository(session)

    domain_file = create_domain_segy_file()

    result = repository.create(domain_file)

    session.add.assert_called_once()
    session.flush.assert_called_once()
    session.refresh.assert_called_once()

    added_model = session.add.call_args.args[0]

    assert isinstance(added_model, SegyFileModel)
    assert added_model.filename == domain_file.filename
    assert added_model.file_path == domain_file.file_path
    assert added_model.file_size == domain_file.file_size
    assert added_model.source_crs == domain_file.source_crs
    assert added_model.trace_count == domain_file.trace_count
    assert added_model.line_count == domain_file.line_count
    assert added_model.geometry == domain_file.geometry

    assert isinstance(result, SegyFile)
    assert result.filename == "test.sgy"
    assert result.file_path == "/data/test.sgy"
    assert result.file_size == 1024
    assert result.source_crs == "EPSG:4326"
    assert result.trace_count == 100
    assert result.line_count == 2

def test_create_maps_geometry():
    session = MagicMock()

    repository = SQLAlchemySegyFileRepository(session)

    geometry = MagicMock()

    domain_file = SegyFile(
        id=None,
        filename="geometry.sgy",
        file_path="/data/geometry.sgy",
        file_size=1024,
        source_crs="EPSG:4326",
        trace_count=100,
        line_count=2,
        geometry=geometry,
    )

    repository.create(domain_file)

    added_model = session.add.call_args.args[0]

    assert isinstance(added_model, SegyFileModel)
    assert added_model.geometry == geometry

def test_get_by_id_returns_domain_model():
    session = MagicMock()

    orm_model = create_orm_segy_file(10)

    session.get.return_value = orm_model

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.get_by_id(10)

    session.get.assert_called_once_with(
        SegyFileModel,
        10,
    )

    assert isinstance(result, SegyFile)
    assert result.id == 10
    assert result.filename == "test.sgy"

def test_get_by_id_returns_none_when_not_found():
    session = MagicMock()

    session.get.return_value = None

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.get_by_id(999)

    assert result is None

def test_get_by_filename_returns_domain_model():
    session = MagicMock()

    orm_model = create_orm_segy_file(20)

    session.scalar.return_value = orm_model

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.get_by_filename("test.sgy")

    session.scalar.assert_called_once()

    assert isinstance(result, SegyFile)
    assert result.id == 20
    assert result.filename == "test.sgy"

def test_get_by_filename_returns_none_when_not_found():
    session = MagicMock()

    session.scalar.return_value = None

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.get_by_filename(
        "missing.sgy"
    )

    assert result is None

def test_list_all_returns_domain_models():
    session = MagicMock()

    models = [
        create_orm_segy_file(1),
        create_orm_segy_file(2),
        create_orm_segy_file(3),
    ]

    session.scalars.return_value.all.return_value = models

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.list_all()

    assert len(result) == 3

    assert all(
        isinstance(item, SegyFile)
        for item in result
    )

    assert [item.id for item in result] == [
        1,
        2,
        3,
    ]

def test_list_all_returns_empty_list_when_no_files():
    session = MagicMock()

    session.scalars.return_value.all.return_value = []

    repository = SQLAlchemySegyFileRepository(session)

    result = repository.list_all()

    assert result == []

def test_update_modifies_existing_model():
    session = MagicMock()

    existing_model = create_orm_segy_file(30)

    session.get.return_value = existing_model

    repository = SQLAlchemySegyFileRepository(session)

    geometry = MagicMock()

    updated_file = SegyFile(
        id=30,
        filename="updated.sgy",
        file_path="/data/updated.sgy",
        file_size=9999,
        source_crs="EPSG:3857",
        trace_count=500,
        line_count=10,
        geometry=geometry,
    )

    result = repository.update(updated_file)

    session.get.assert_called_once_with(
        SegyFileModel,
        30,
    )

    assert existing_model.filename == "updated.sgy"
    assert existing_model.file_path == "/data/updated.sgy"
    assert existing_model.file_size == 9999
    assert existing_model.source_crs == "EPSG:3857"
    assert existing_model.trace_count == 500
    assert existing_model.line_count == 10
    assert existing_model.geometry == geometry

    session.flush.assert_called_once()
    session.refresh.assert_called_once_with(
        existing_model
    )

    assert isinstance(result, SegyFile)
    assert result.id == 30
    assert result.filename == "updated.sgy"
    assert result.geometry == geometry

def test_update_raises_error_when_not_found():
    session = MagicMock()

    session.get.return_value = None

    repository = SQLAlchemySegyFileRepository(session)

    updated_file = SegyFile(
        id=999,
        filename="missing.sgy",
        file_path="/data/missing.sgy",
        file_size=100,
        source_crs="EPSG:4326",
        trace_count=10,
        line_count=1,
    )

    with pytest.raises(
        ValueError,
        match="SEG-Y file with id=999 not found",
    ):
        repository.update(updated_file)

def test_delete_existing_file():
    session = MagicMock()

    model = create_orm_segy_file(40)

    session.get.return_value = model

    repository = SQLAlchemySegyFileRepository(session)

    repository.delete(40)

    session.get.assert_called_once_with(
        SegyFileModel,
        40,
    )

    session.delete.assert_called_once_with(model)

    session.flush.assert_called_once()

def test_delete_non_existing_file_does_nothing():
    session = MagicMock()

    session.get.return_value = None

    repository = SQLAlchemySegyFileRepository(session)

    repository.delete(999)

    session.delete.assert_not_called()
    session.flush.assert_not_called()

def test_intersects_polygon_returns_domain_models():
    session = MagicMock()

    models = [
        create_orm_segy_file(1),
        create_orm_segy_file(2),
    ]

    session.scalars.return_value.all.return_value = models

    repository = SQLAlchemySegyFileRepository(session)

    polygon = MagicMock()

    result = repository.intersects_polygon(polygon)

    session.scalars.assert_called_once()

    assert len(result) == 2

    assert all(
        isinstance(item, SegyFile)
        for item in result
    )

    assert [item.id for item in result] == [
        1,
        2,
    ]

def test_intersects_polygon_returns_empty_list():
    session = MagicMock()

    session.scalars.return_value.all.return_value = []

    repository = SQLAlchemySegyFileRepository(session)

    polygon = MagicMock()

    result = repository.intersects_polygon(polygon)

    assert result == []

def test_to_domain_maps_orm_model_correctly():
    model = create_orm_segy_file(50)

    result = SQLAlchemySegyFileRepository._to_domain(
        model
    )

    assert isinstance(result, SegyFile)

    assert result.id == model.id
    assert result.filename == model.filename
    assert result.file_path == model.file_path
    assert result.file_size == model.file_size
    assert result.source_crs == model.source_crs
    assert result.trace_count == model.trace_count
    assert result.line_count == model.line_count
    assert result.geometry == model.geometry
    assert result.created_at == model.created_at
    assert result.updated_at == model.updated_at