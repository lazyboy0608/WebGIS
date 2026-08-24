from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from app.application.services.segy_processing import SegyProcessingService
from app.domain.models.line_string import LineString
from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.trace import Trace
from app.services.coordinate_transformer import CoordinateTransformer
from app.services.line_builder import LineBuilder
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.shot_point_analyzer import ShotPointAnalyzer
from app.services.trace_processor import TraceProcessor


class FakeReader:
    def __init__(self, traces):
        self.traces = traces

    def read_metadata(self, file_path: Path) -> SegyMetadata:
        return Mock(trace_count=len(self.traces))

    def iter_traces(self, file_path: Path, include_samples: bool = False):
        yield from self.traces


class FakeGeometryBuilder:
    def build(self, line, source_crs=None):
        return LineString(coordinates=line.coordinates, srid=4326)


def make_trace(index: int, line_key: int, x: float) -> Trace:
    return Trace(
        index=index,
        header=SimpleNamespace(
            source_x=x,
            source_y=20.0,
            coordinate_scalar=1,
            coordinate_units=1,
            energy_source_point=100 + index,
            original_field_record_number=line_key,
        ),
    )


def test_process_groups_traces_by_line_key():
    traces = [
        make_trace(0, 10, 10.0),
        make_trace(1, 10, 11.0),
        make_trace(2, 20, 30.0),
        make_trace(3, 20, 31.0),
    ]
    service = SegyProcessingService(
        segy_reader=FakeReader(traces),
        trace_processor=TraceProcessor(CoordinateTransformer()),
        shot_point_analyzer=ShotPointAnalyzer(CoordinateTransformer()),
        line_builder=LineBuilder(),
        topology_analyzer=LineTopologyAnalyzer(),
        wgs84_geometry_builder=FakeGeometryBuilder(),
    )

    result = service.process(Path("multi-line.sgy"))

    assert [line.line_key for line in result.lines] == ["10", "20"]
    assert [len(line.line.coordinates) for line in result.lines] == [2, 2]
    assert [
        trace.line_group_key for trace in result.processed_traces
    ] == ["10", "10", "20", "20"]
