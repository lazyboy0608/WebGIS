from dataclasses import replace
from pathlib import Path

from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.domain.models.processed_line import ProcessedLine
from app.domain.models.processed_segy_data import ProcessedSegyData
from app.domain.services.file_storage import FileStorage
from app.services.line_builder import LineBuilder
from app.services.line_topology_analyzer import LineTopologyAnalyzer
from app.services.segy_reader import SegyReaderService
from app.services.shot_point_analyzer import ShotPointAnalyzer
from app.services.trace_processor import TraceProcessor
from app.services.wgs84_line_geometry_builder import WGS84LineGeometryBuilder


class SegyProcessingService:
    """Orchestrate SEG-Y reading, analysis, and geometry construction."""

    def __init__(
        self,
        segy_reader: SegyReaderService,
        trace_processor: TraceProcessor,
        shot_point_analyzer: ShotPointAnalyzer,
        line_builder: LineBuilder,
        topology_analyzer: LineTopologyAnalyzer,
        wgs84_geometry_builder: WGS84LineGeometryBuilder,
        file_storage: FileStorage | None = None,
    ) -> None:
        self._segy_reader = segy_reader
        self._trace_processor = trace_processor
        self._shot_point_analyzer = shot_point_analyzer
        self._line_builder = line_builder
        self._topology_analyzer = topology_analyzer
        self._wgs84_geometry_builder = wgs84_geometry_builder
        self._file_storage = file_storage

    def process(
        self,
        file_path: Path,
        source_crs: str | None = None,
    ) -> ProcessedSegyData:
        metadata = self._segy_reader.read_metadata(file_path)
        raw_traces = list(
            self._segy_reader.iter_traces(
                file_path,
                include_samples=False,
            )
        )
        shot_point_analysis = self._shot_point_analyzer.analyze(raw_traces)
        processed_traces = list(self._trace_processor.process_many(raw_traces))
        line_keys = {
            trace.line_group_key or "default"
            for trace in processed_traces
        }
        if len(line_keys) == 1:
            line_key = next(iter(line_keys))
            line = self._line_builder.build(processed_traces)
            topology_analysis = self._topology_analyzer.analyze(processed_traces)
            wgs84_geometry = self._build_wgs84_geometry(line, source_crs)
            grouped_lines = [
                ProcessedLine(
                    line_key=line_key,
                    line=line,
                    wgs84_geometry=wgs84_geometry,
                    topology_analysis=topology_analysis,
                )
            ]
            processed_traces = self._attach_wgs84_coordinates(
                processed_traces,
                wgs84_geometry.coordinates,
            )
        else:
            grouped = self._line_builder.build_grouped(processed_traces)
            grouped_lines = []
            processed_by_index = {
                trace.trace_index: trace for trace in processed_traces
            }
            for line_key, grouped_line in grouped.items():
                grouped_traces = [
                    processed_by_index[index]
                    for index in grouped_line.trace_indices
                ]
                topology = self._topology_analyzer.analyze(grouped_traces)
                geometry = self._build_wgs84_geometry(
                    grouped_line,
                    source_crs,
                )
                for index, coordinate in zip(
                    grouped_line.trace_indices,
                    geometry.coordinates,
                ):
                    processed_by_index[index] = replace(
                        processed_by_index[index],
                        wgs84_coordinate=coordinate,
                    )
                grouped_lines.append(
                    ProcessedLine(
                        line_key=line_key,
                        line=grouped_line,
                        wgs84_geometry=geometry,
                        topology_analysis=topology,
                    )
                )
            processed_traces = [
                processed_by_index[trace.trace_index]
                for trace in processed_traces
            ]
            line = grouped_lines[0].line
            topology_analysis = grouped_lines[0].topology_analysis
            wgs84_geometry = grouped_lines[0].wgs84_geometry

        traces_by_index = {
            trace.trace_index: trace for trace in processed_traces
        }
        if shot_point_analysis is not None:
            for shot_point in shot_point_analysis.shot_points:
                shot_point.wgs84_coordinates = [
                    traces_by_index[trace_index].wgs84_coordinate
                    for trace_index in shot_point.trace_indices
                    if trace_index in traces_by_index
                    and traces_by_index[trace_index].wgs84_coordinate is not None
                ]

        return ProcessedSegyData(
            metadata=metadata,
            processed_traces=processed_traces,
            shot_point_analysis=shot_point_analysis,
            line=line,
            topology_analysis=topology_analysis,
            wgs84_geometry=wgs84_geometry,
            lines=grouped_lines,
        )

    def _build_wgs84_geometry(self, line, source_crs):
        if source_crs is None:
            return self._wgs84_geometry_builder.build(line)
        return self._wgs84_geometry_builder.build(
            line,
            source_crs=CoordinateReferenceSystem(name=source_crs),
        )

    @staticmethod
    def _attach_wgs84_coordinates(traces, coordinates):
        return [
            replace(trace, wgs84_coordinate=coordinates[index])
            for index, trace in enumerate(traces)
        ]

    def process_file(
        self,
        filename: str,
        source_crs: str | None = None,
    ) -> ProcessedSegyData:
        if self._file_storage is None:
            raise RuntimeError("File storage is not configured.")

        file_path = self._file_storage.get_path(filename)
        if not file_path.exists():
            raise FileNotFoundError(f"SEG-Y file not found: {filename}")

        if source_crs is None:
            return self.process(file_path)

        return self.process(file_path, source_crs=source_crs)
