from unittest.mock import Mock

import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.infrastructure.database.repositories.seismic_trace_repository import (
    SQLAlchemySeismicTraceRepository,
)
from app.infrastructure.database.models.seismic_trace_model import (
    SeismicTraceModel,
)


def create_trace() -> ProcessedTrace:
    return ProcessedTrace(
        trace_index=10,
        source_point=SourcePoint(
            number=100,
        ),
        coordinate=Coordinate(
            x=149.25,
            y=61.75,
        ),
        samples=None,
    )


def test_repository_stores_session():
    session = Mock()

    repository = (
        SQLAlchemySeismicTraceRepository(
            session
        )
    )

    assert repository.session is session


def test_save_trace_adds_model_to_session():
    session = Mock()

    repository = (
        SQLAlchemySeismicTraceRepository(
            session
        )
    )

    trace = create_trace()

    repository.save_trace(
        trace=trace,
        segy_file_id=1,
    )

    session.add.assert_called_once()

    model = session.add.call_args.args[0]

    assert isinstance(
        model,
        SeismicTraceModel,
    )


def test_save_trace_maps_basic_fields():
    session = Mock()

    repository = (
        SQLAlchemySeismicTraceRepository(
            session
        )
    )

    trace = create_trace()

    repository.save_trace(
        trace=trace,
        segy_file_id=5,
        seismic_line_id=10,
        shot_point_id=20,
    )

    model = session.add.call_args.args[0]

    assert model.trace_index == 10
    assert model.segy_file_id == 5
    assert model.seismic_line_id == 10
    assert model.shot_point_id == 20


def test_save_trace_maps_geometry():
    session = Mock()

    repository = (
        SQLAlchemySeismicTraceRepository(
            session
        )
    )

    trace = create_trace()

    repository.save_trace(
        trace=trace,
        segy_file_id=1,
    )

    model = session.add.call_args.args[0]

    assert str(model.geometry) == (
        "POINT(149.25 61.75)"
    )

    assert model.geometry.srid == 4326


def test_save_trace_rejects_missing_coordinate():
    session = Mock()

    repository = (
        SQLAlchemySeismicTraceRepository(
            session
        )
    )

    trace = ProcessedTrace(
        trace_index=10,
        source_point=SourcePoint(
            number=100,
        ),
        coordinate=None,
        samples=None,
    )

    with pytest.raises(
        ValueError,
        match="coordinate is required",
    ):
        repository.save_trace(
            trace=trace,
            segy_file_id=1,
        )