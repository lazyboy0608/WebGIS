from unittest.mock import MagicMock

import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.shot_point import ShotPoint
from app.infrastructure.database.repositories.seismic_shot_point_repository import (
    SQLAlchemyShotPointRepository,
)


def create_repository():
    session = MagicMock()
    repository = SQLAlchemyShotPointRepository(session)

    return repository, session


def test_repository_stores_session():
    repository, session = create_repository()

    assert repository.session is session


def test_save_shot_point_adds_model_to_session():
    repository, session = create_repository()

    shot_point = ShotPoint(
        number=100,
        trace_indices=[1, 2],
        coordinates=[
            Coordinate(x=100.0, y=200.0),
            Coordinate(x=110.0, y=210.0),
        ],
    )

    repository.save_shot_point(
        shot_point=shot_point,
        segy_file_id=1,
    )

    session.add.assert_called_once()
    session.flush.assert_called_once()


def test_save_shot_point_maps_basic_fields():
    repository, session = create_repository()

    shot_point = ShotPoint(
        number=100,
        trace_indices=[1, 2, 3],
        coordinates=[
            Coordinate(x=100.0, y=200.0),
        ],
    )

    repository.save_shot_point(
        shot_point=shot_point,
        segy_file_id=5,
        seismic_line_id=10,
    )

    model = session.add.call_args.args[0]

    assert model.shot_point_number == 100
    assert model.segy_file_id == 5
    assert model.seismic_line_id == 10
    assert model.trace_count == 3


def test_save_shot_point_uses_first_coordinate():
    repository, session = create_repository()

    shot_point = ShotPoint(
        number=200,
        trace_indices=[1, 2],
        coordinates=[
            Coordinate(x=100.0, y=200.0),
            Coordinate(x=300.0, y=400.0),
        ],
    )

    repository.save_shot_point(
        shot_point=shot_point,
        segy_file_id=1,
    )

    model = session.add.call_args.args[0]

    assert model.geometry is not None


def test_save_shot_point_rejects_empty_coordinates():
    repository, session = create_repository()

    shot_point = ShotPoint(
        number=100,
        trace_indices=[],
        coordinates=[],
    )

    with pytest.raises(ValueError):
        repository.save_shot_point(
            shot_point=shot_point,
            segy_file_id=1,
        )

    session.add.assert_not_called()