from unittest.mock import MagicMock

import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.seismic_line import SeismicLine
from app.infrastructure.database.repositories.seismic_line_repository import (
    SQLAlchemyLineRepository,
)


def create_repository():
    session = MagicMock()
    repository = SQLAlchemyLineRepository(session)

    return repository, session


def test_repository_stores_session():
    repository, session = create_repository()

    assert repository.session is session


def test_save_line_adds_model_to_session():
    repository, session = create_repository()

    line = SeismicLine(
        line_id="LINE-001",
        coordinates=[
            Coordinate(x=100.0, y=200.0),
            Coordinate(x=110.0, y=210.0),
        ],
    )

    repository.save_line(
        line=line,
        segy_file_id=1,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()


def test_save_line_maps_basic_fields():
    repository, session = create_repository()

    line = SeismicLine(
        line_id="LINE-001",
        coordinates=[
            Coordinate(x=100.0, y=200.0),
            Coordinate(x=110.0, y=210.0),
            Coordinate(x=120.0, y=220.0),
        ],
    )

    repository.save_line(
        line=line,
        segy_file_id=5,
    )

    model = session.add.call_args.args[0]

    assert model.line_id == "LINE-001"
    assert model.segy_file_id == 5
    assert model.point_count == 3


def test_save_line_rejects_empty_coordinates():
    repository, session = create_repository()

    line = SeismicLine(
        line_id="LINE-001",
        coordinates=[],
    )

    with pytest.raises(ValueError):
        repository.save_line(
            line=line,
            segy_file_id=1,
        )

    session.add.assert_not_called()


def test_save_line_supports_single_coordinate():
    repository, session = create_repository()

    line = SeismicLine(
        line_id="LINE-001",
        coordinates=[
            Coordinate(x=100.0, y=200.0),
        ],
    )

    repository.save_line(
        line=line,
        segy_file_id=1,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()