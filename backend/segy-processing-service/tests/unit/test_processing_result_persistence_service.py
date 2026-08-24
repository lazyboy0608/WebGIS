from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.line import Line
from app.domain.models.processed_segy_data import ProcessedSegyData
from app.domain.models.seismic_line import SeismicLine
from app.domain.models.seismic_shot_point import SeismicShotPoint
from app.domain.models.shot_point import ShotPoint
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.processing_result_persistence_service import (
    ProcessingResultPersistenceService,
)

def create_coordinate(
    x: float = 0.0,
    y: float = 0.0,
) -> Coordinate:
    return Coordinate(x=x, y=y)

def create_processed_data(
    *,
    line: Line | None = None,
    shot_points: list[ShotPoint] | None = None,
    processed_traces: list[ProcessedTrace] | None = None,
) -> ProcessedSegyData:

    return ProcessedSegyData(
        metadata=Mock(),
        processed_traces=(
            processed_traces
            if processed_traces is not None
            else []
        ),
        shot_point_analysis=(
            SimpleNamespace(
                shot_points=shot_points
                if shot_points is not None
                else []
            )
            if shot_points is not None
            else None
        ),
        line=line,
    )

def create_service():
    line_repository = Mock()
    shot_point_repository = Mock()
    trace_repository = Mock()

    service = ProcessingResultPersistenceService(
        line_repository=line_repository,
        shot_point_repository=shot_point_repository,
        trace_repository=trace_repository,
    )

    return (
        service,
        line_repository,
        shot_point_repository,
        trace_repository,
    )

def test_persist_saves_line_first():
    service, line_repository, shot_point_repository, trace_repository = (
        create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[100, 101],
    )

    # line_repository.save_line.assert_called_once()

    saved_line = SeismicLine(
        id=15,
        line_id="LINE-7-1",
        coordinates=line.coordinates,
    )

    line_repository.save_line.return_value = saved_line

    processed_data = create_processed_data(
        line=line,
    )

    service.persist(
        processed_data,
        segy_file_id=7,
    )

    line_repository.save_line.assert_called_once()

    saved_argument, saved_file_id = (
        line_repository.save_line.call_args.args
    )

    assert saved_argument.line_id == "LINE-7-1"
    assert saved_argument.coordinates == line.coordinates
    assert saved_file_id == 7

    shot_point_repository.save_shot_point.assert_not_called()
    trace_repository.save_trace.assert_not_called()

def test_persist_saves_shot_points_after_line():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[100, 101],
    )

    saved_line = SeismicLine(
        id=15,
        coordinates=line.coordinates,
    )

    line_repository.save_line.return_value = saved_line

    shot_point_100 = ShotPoint(
        number=100,
        trace_indices=[1],
        coordinates=[create_coordinate(10, 20)],
    )

    shot_point_101 = ShotPoint(
        number=101,
        trace_indices=[2],
        coordinates=[create_coordinate(20, 30)],
    )

    shot_point_repository.save_shot_point.side_effect = [
        SeismicShotPoint(
            id=21,
            number=100,
            trace_indices=[1],
            coordinates=shot_point_100.coordinates,
        ),
        SeismicShotPoint(
            id=22,
            number=101,
            trace_indices=[2],
            coordinates=shot_point_101.coordinates,
        ),
    ]

    processed_data = create_processed_data(
        line=line,
        shot_points=[
            shot_point_100,
            shot_point_101,
        ],
    )

    service.persist(
        processed_data,
        segy_file_id=7,
    )

    line_repository.save_line.assert_called_once()

    assert shot_point_repository.save_shot_point.call_count == 2

    first_call = (
        shot_point_repository.save_shot_point.call_args_list[0]
    )
    second_call = (
        shot_point_repository.save_shot_point.call_args_list[1]
    )

    assert first_call.args[1] == 7
    assert first_call.args[2] == 15

    assert second_call.args[1] == 7
    assert second_call.args[2] == 15

    trace_repository.save_trace.assert_not_called()

def test_persist_saves_traces_after_shot_points():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[100, 101],
    )

    saved_line = SeismicLine(
        id=15,
        coordinates=line.coordinates,
    )

    line_repository.save_line.return_value = saved_line

    shot_point = ShotPoint(
        number=100,
        trace_indices=[1, 2],
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
    )

    shot_point_repository.save_shot_point.return_value = (
        SeismicShotPoint(
            id=21,
            number=100,
            trace_indices=[1, 2],
            coordinates=shot_point.coordinates,
        )
    )

    trace_1 = ProcessedTrace(
        trace_index=1,
        source_point=SourcePoint(number=100),
        coordinate=create_coordinate(10, 20),
    )

    trace_2 = ProcessedTrace(
        trace_index=2,
        source_point=SourcePoint(number=100),
        coordinate=create_coordinate(20, 30),
    )

    processed_data = create_processed_data(
        line=line,
        shot_points=[shot_point],
        processed_traces=[
            trace_1,
            trace_2,
        ],
    )

    service.persist(
        processed_data,
        segy_file_id=7,       
    )

    assert trace_repository.save_trace.call_count == 2

    first_call = trace_repository.save_trace.call_args_list[0]
    second_call = trace_repository.save_trace.call_args_list[1]

    assert first_call.args == (
        trace_1,
        7,
        15,
        21,
    )

    assert second_call.args == (
        trace_2,
        7,
        15,
        21,
    )

def test_persist_maps_shot_point_ids_to_traces():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[100, 200],
    )

    line_repository.save_line.return_value = SeismicLine(
        id=15,
        coordinates=line.coordinates,
    )

    shot_point_100 = ShotPoint(
        number=100,
        trace_indices=[1],
        coordinates=[create_coordinate(10, 20)],
    )

    shot_point_200 = ShotPoint(
        number=200,
        trace_indices=[2],
        coordinates=[create_coordinate(20, 30)],
    )

    shot_point_repository.save_shot_point.side_effect = [
        SeismicShotPoint(
            id=101,
            number=100,
            trace_indices=[1],
            coordinates=shot_point_100.coordinates,
        ),
        SeismicShotPoint(
            id=202,
            number=200,
            trace_indices=[2],
            coordinates=shot_point_200.coordinates,
        ),
    ]

    trace_1 = ProcessedTrace(
        trace_index=1,
        source_point=SourcePoint(number=100),
        coordinate=create_coordinate(10, 20),
    )

    trace_2 = ProcessedTrace(
        trace_index=2,
        source_point=SourcePoint(number=200),
        coordinate=create_coordinate(20, 30),
    )

    processed_data = create_processed_data(
        line=line,
        shot_points=[
            shot_point_100,
            shot_point_200,
        ],
        processed_traces=[
            trace_1,
            trace_2,
        ],
    )

    service.persist(
        processed_data,
        segy_file_id=7,
    )

    first_call = trace_repository.save_trace.call_args_list[0]
    second_call = trace_repository.save_trace.call_args_list[1]

    assert first_call.args[3] == 101
    assert second_call.args[3] == 202

def test_persist_without_shot_point_analysis():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[],
    )

    line_repository.save_line.return_value = SeismicLine(
        id=15,        
        coordinates=line.coordinates,
    )

    trace = ProcessedTrace(
        trace_index=1,
        source_point=SourcePoint(number=100),
        coordinate=create_coordinate(10, 20),
    )

    processed_data = create_processed_data(
        line=line,
        processed_traces=[trace],
    )

    service.persist(
        processed_data,
        segy_file_id=7,
    )

    shot_point_repository.save_shot_point.assert_not_called()

    trace_repository.save_trace.assert_called_once_with(
        trace,
        7,
        15,
        None,
    )

def test_persist_requires_line():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    processed_data = create_processed_data(
        line=None,
    )

    with pytest.raises(
        ValueError,
        match="Processed SEG-Y data does not contain a line",
    ):
        service.persist(
            processed_data,
            segy_file_id=7,
        )

    line_repository.save_line.assert_not_called()
    shot_point_repository.save_shot_point.assert_not_called()
    trace_repository.save_trace.assert_not_called()

def test_persist_rejects_shot_point_without_database_id():
    service, line_repository, shot_point_repository, trace_repository = (
    create_service()
)

    line = Line(
        coordinates=[
            create_coordinate(10, 20),
            create_coordinate(20, 30),
        ],
        trace_indices=[1, 2],
        shot_points=[100],
    )

    line_repository.save_line.return_value = SeismicLine(
        id=15,
        coordinates=line.coordinates,
    )

    shot_point = ShotPoint(
        number=100,
        trace_indices=[1],
        coordinates=[create_coordinate(10, 20)],
    )

    shot_point_repository.save_shot_point.return_value = (
        SeismicShotPoint(
            id=None,
            number=100,
            trace_indices=[1],
            coordinates=shot_point.coordinates,
        )
    )

    processed_data = create_processed_data(
        line=line,
        shot_points=[shot_point],
    )

    with pytest.raises(
        ValueError,
        match="does not have a database ID",
    ):
        service.persist(
            processed_data,
            segy_file_id=7,
        )

    trace_repository.save_trace.assert_not_called()