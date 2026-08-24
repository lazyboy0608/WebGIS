from pathlib import Path
from unittest.mock import Mock

import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.line import Line
from app.domain.models.line_string import LineString
from app.domain.models.line_topology import (
    LineTopologyAnalysis,
)
from app.domain.models.processed_segy_data import (
    ProcessedSegyData,
)
from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.shot_point_analysis import (
    ShotPointAnalysis,
)
from app.domain.models.trace import (
    ProcessedTrace,
    SourcePoint,
)
from app.services.segy_processing_service import (
    SegyProcessingService,
)


class FakeSegyReaderService:
    def __init__(
        self,
        metadata: SegyMetadata,
        traces,
        calls=None,
    ):
        self.metadata = metadata
        self.traces = traces
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def read_metadata(
        self,
        file_path: Path,
    ):
        self.calls.append(
            "read_metadata"
        )

        return self.metadata

    def iter_traces(
        self,
        file_path: Path,
        include_samples: bool = False,
    ):
        self.calls.append(
            "iter_traces"
        )

        assert include_samples is False

        yield from self.traces


class FakeTraceProcessor:
    def __init__(
        self,
        processed_traces,
        calls=None,
    ):
        self.processed_traces = (
            processed_traces
        )
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def process_many(
        self,
        traces,
    ):
        self.calls.append(
            "trace_processor"
        )

        yield from self.processed_traces


class FakeShotPointAnalyzer:
    def __init__(
        self,
        analysis: ShotPointAnalysis,
        calls=None,
    ):
        self.analysis = analysis
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def analyze(
        self,
        traces,
    ):
        self.calls.append(
            "shot_point_analyzer"
        )

        return self.analysis


class FakeLineBuilder:
    def __init__(
        self,
        line: Line,
        calls=None,
    ):
        self.line = line
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def build(
        self,
        traces,
    ):
        self.calls.append(
            "line_builder"
        )

        return self.line


class FakeLineTopologyAnalyzer:
    def __init__(
        self,
        analysis: LineTopologyAnalysis,
        calls=None,
    ):
        self.analysis = analysis
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def analyze(
        self,
        traces,
    ):
        self.calls.append(
            "line_topology_analyzer"
        )

        return self.analysis


class FakeWGS84LineGeometryBuilder:
    def __init__(
        self,
        geometry: LineString,
        calls=None,
    ):
        self.geometry = geometry
        self.calls = (
            calls
            if calls is not None
            else []
        )

    def build(
        self,
        line,
    ):
        self.calls.append(
            "wgs84_geometry_builder"
        )

        return self.geometry


def create_metadata() -> SegyMetadata:
    return SegyMetadata(
        file_name="test.sgy",
        file_size_bytes=1000,
        trace_count=2,
        textual_header=None,
        binary_header=None,
    )


def create_processed_traces() -> list[ProcessedTrace]:
    return [
        ProcessedTrace(
            trace_index=0,
            source_point=SourcePoint(
                number=100,
            ),
            coordinate=Coordinate(
                x=10,
                y=20,
            ),
            samples=None,
        ),
        ProcessedTrace(
            trace_index=1,
            source_point=SourcePoint(
                number=101,
            ),
            coordinate=Coordinate(
                x=20,
                y=20,
            ),
            samples=None,
        ),
    ]


def create_line() -> Line:
    return Line(
        coordinates=[
            Coordinate(
                x=10,
                y=20,
            ),
            Coordinate(
                x=20,
                y=20,
            ),
        ],
        trace_indices=[
            0,
            1,
        ],
        shot_points=[
            100,
            101,
        ],
    )


def create_geometry() -> LineString:
    return LineString(
        coordinates=[
            Coordinate(
                x=105.0,
                y=20.0,
            ),
            Coordinate(
                x=106.0,
                y=20.0,
            ),
        ],
        srid=4326,
    )


def create_topology_analysis() -> LineTopologyAnalysis:
    return LineTopologyAnalysis(
        trace_count=2,
        coordinate_count=2,
        distance_count=1,
        minimum_distance=10.0,
        maximum_distance=10.0,
        average_distance=10.0,
        median_distance=10.0,
        maximum_gap=None,
        gap_count=0,
        reversed_segment_count=0,
        monotonic_shot_point=True,
        continuous=True,
        start_coordinate=Coordinate(
            x=10,
            y=20,
        ),
        end_coordinate=Coordinate(
            x=20,
            y=20,
        ),
    )


def create_shot_point_analysis() -> ShotPointAnalysis:
    return ShotPointAnalysis(
        total_trace_count=2,
        unique_shot_point_count=2,
        shot_points=[],
        missing_shot_point_count=0,
    )


def create_service():
    calls = []

    processed_traces = (
        create_processed_traces()
    )

    service = SegyProcessingService(
        segy_reader=FakeSegyReaderService(
            metadata=create_metadata(),
            traces=[
                object(),
                object(),
            ],
            calls=calls,
        ),
        trace_processor=FakeTraceProcessor(
            processed_traces,
            calls=calls,
        ),
        shot_point_analyzer=FakeShotPointAnalyzer(
            create_shot_point_analysis(),
            calls=calls,
        ),
        line_builder=FakeLineBuilder(
            create_line(),
            calls=calls,
        ),
        topology_analyzer=FakeLineTopologyAnalyzer(
            create_topology_analysis(),
            calls=calls,
        ),
        wgs84_geometry_builder=(
            FakeWGS84LineGeometryBuilder(
                create_geometry(),
                calls=calls,
            )
        ),
    )

    return service, calls


def test_process_returns_processed_segy_data(
    tmp_path,
):
    service, calls = create_service()

    file_path = (
        tmp_path / "test.sgy"
    )

    result = service.process(
        file_path
    )

    assert isinstance(
        result,
        ProcessedSegyData,
    )

    assert (
        result.metadata.file_name
        == "test.sgy"
    )

    assert len(
        result.processed_traces
    ) == 2

    assert (
        result.shot_point_analysis
        is not None
    )

    assert result.line is not None

    assert (
        result.topology_analysis
        is not None
    )

    assert (
        result.wgs84_geometry
        is not None
    )

    assert calls == [
        "read_metadata",
        "iter_traces",
        "shot_point_analyzer",
        "trace_processor",
        "line_builder",
        "line_topology_analyzer",
        "wgs84_geometry_builder",
    ]


def test_process_preserves_processing_results(
    tmp_path,
):
    service, _ = create_service()

    file_path = (
        tmp_path / "test.sgy"
    )

    result = service.process(
        file_path
    )

    assert result.line.trace_indices == [
        0,
        1,
    ]

    assert result.line.shot_points == [
        100,
        101,
    ]

    assert (
        result.topology_analysis.continuous
        is True
    )

    assert (
        result.wgs84_geometry.srid
        == 4326
    )


def test_process_file_resolves_file_from_storage(
    tmp_path,
):
    file_storage = Mock()

    file_path = (
        tmp_path / "slb1.sgy"
    )

    file_path.write_bytes(
        b"fake-segy-data"
    )

    file_storage.get_path.return_value = (
        file_path
    )

    service = SegyProcessingService(
        segy_reader=Mock(),
        trace_processor=Mock(),
        shot_point_analyzer=Mock(),
        line_builder=Mock(),
        topology_analyzer=Mock(),
        wgs84_geometry_builder=Mock(),
        file_storage=file_storage,
    )

    expected = Mock()

    service.process = Mock(
        return_value=expected
    )

    result = service.process_file(
        "slb1.sgy"
    )

    file_storage.get_path.assert_called_once_with(
        "slb1.sgy"
    )

    service.process.assert_called_once_with(
        file_path
    )

    assert result is expected


def test_process_file_raises_when_file_does_not_exist(
    tmp_path,
):
    file_storage = Mock()

    file_path = (
        tmp_path / "missing.sgy"
    )

    file_storage.get_path.return_value = (
        file_path
    )

    service = SegyProcessingService(
        segy_reader=Mock(),
        trace_processor=Mock(),
        shot_point_analyzer=Mock(),
        line_builder=Mock(),
        topology_analyzer=Mock(),
        wgs84_geometry_builder=Mock(),
        file_storage=file_storage,
    )

    with pytest.raises(
        FileNotFoundError,
        match="SEG-Y file not found",
    ):
        service.process_file(
            "missing.sgy"
        )


def test_process_file_raises_when_file_storage_is_not_configured():
    service = SegyProcessingService(
        segy_reader=Mock(),
        trace_processor=Mock(),
        shot_point_analyzer=Mock(),
        line_builder=Mock(),
        topology_analyzer=Mock(),
        wgs84_geometry_builder=Mock(),
        file_storage=None,
    )

    with pytest.raises(
        RuntimeError,
        match="File storage is not configured",
    ):
        service.process_file(
            "test.sgy"
        )