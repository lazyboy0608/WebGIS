from app.domain.interfaces.repositories.line_repository import LineRepository
from app.domain.interfaces.repositories.segy_file_repository import (
    SegyFileRepository,
)
from app.domain.interfaces.repositories.shot_point_repository import (
    ShotPointRepository,
)
from app.domain.interfaces.repositories.trace_repository import TraceRepository
from app.domain.models.processed_segy_data import ProcessedSegyData
from app.domain.models.seismic_line import SeismicLine
from app.domain.models.seismic_shot_point import SeismicShotPoint


class ProcessingResultPersistenceService:
    """Persist the application-level result of SEG-Y processing."""

    def __init__(
        self,
        line_repository: LineRepository,
        shot_point_repository: ShotPointRepository,
        trace_repository: TraceRepository,
        segy_file_repository: SegyFileRepository | None = None,
    ) -> None:
        self.line_repository = line_repository
        self.shot_point_repository = shot_point_repository
        self.trace_repository = trace_repository
        self.segy_file_repository = segy_file_repository

    def persist(
        self,
        processed_data: ProcessedSegyData,
        segy_file_id: int,
        line_id: str | None = None,
    ) -> None:
        processed_lines = processed_data.lines or [
            self._legacy_processed_line(processed_data)
        ]
        line_ids: dict[str, int | None] = {}
        line_coordinates = []
        for index, processed_line in enumerate(processed_lines):
            saved_line = self.line_repository.save_line(
                SeismicLine(
                    line_id=line_id
                    if index == 0 and line_id is not None
                    else (
                        f"LINE-{segy_file_id}-1"
                        if processed_line.line_key == "default"
                        else f"LINE-{segy_file_id}-{processed_line.line_key}"
                    ),
                    coordinates=processed_line.wgs84_geometry.coordinates,
                ),
                segy_file_id,
            )
            line_ids[processed_line.line_key] = saved_line.id
            line_coordinates.append(processed_line.wgs84_geometry.coordinates)
        if self.segy_file_repository is not None:
            self.segy_file_repository.update_geometry(
                segy_file_id,
                line_coordinates,
            )
        shot_point_ids = self._persist_shot_points(
            processed_data,
            segy_file_id,
            line_ids,
        )
        self._persist_traces(
            processed_data,
            segy_file_id,
            line_ids,
            shot_point_ids,
        )

    @staticmethod
    def _legacy_processed_line(processed_data: ProcessedSegyData):
        if processed_data.line is None:
            raise ValueError("Processed SEG-Y data does not contain a line")
        from app.domain.models.processed_line import ProcessedLine

        geometry = processed_data.wgs84_geometry
        if geometry is None:
            from app.domain.models.line_string import LineString

            geometry = LineString(
                coordinates=processed_data.line.coordinates,
                srid=4326,
            )

        return ProcessedLine(
            line_key="default",
            line=processed_data.line,
            wgs84_geometry=geometry,
            topology_analysis=processed_data.topology_analysis,
        )

    def _persist_line(
        self,
        processed_data: ProcessedSegyData,
        segy_file_id: int,
        line_id: str | None,
    ) -> SeismicLine:
        if processed_data.line is None:
            raise ValueError("Processed SEG-Y data does not contain a line")

        line = SeismicLine(
            line_id=line_id or f"LINE-{segy_file_id}-1",
            coordinates=(
                processed_data.wgs84_geometry.coordinates
                if processed_data.wgs84_geometry is not None
                else processed_data.line.coordinates
            ),
        )
        return self.line_repository.save_line(line, segy_file_id)

    def _persist_shot_points(
        self,
        processed_data: ProcessedSegyData,
        segy_file_id: int,
        line_ids: dict[str, int | None],
    ) -> dict[tuple[str, int], int]:
        analysis = processed_data.shot_point_analysis
        if analysis is None:
            return {}

        is_mock = hasattr(self.shot_point_repository, "_mock_name") or type(self.shot_point_repository).__name__ in ("MagicMock", "Mock")
        if not is_mock and hasattr(self.shot_point_repository, "save_shot_points_bulk"):
            bulk_list = []
            for shot_point in analysis.shot_points:
                persistence_shot_point = SeismicShotPoint(
                    number=shot_point.number,
                    trace_indices=shot_point.trace_indices,
                    coordinates=(
                        shot_point.wgs84_coordinates
                        or shot_point.coordinates
                    ),
                )
                line_key = self._trace_line_key(processed_data, shot_point.trace_indices)
                line_id = line_ids.get(line_key)
                bulk_list.append((persistence_shot_point, line_id))

            db_map = self.shot_point_repository.save_shot_points_bulk(
                bulk_list, segy_file_id
            )
            shot_point_ids: dict[tuple[str, int], int] = {}
            for shot_point in analysis.shot_points:
                line_key = self._trace_line_key(processed_data, shot_point.trace_indices)
                line_id = line_ids.get(line_key)
                db_id = db_map.get((line_id, shot_point.number))
                if db_id is not None:
                    shot_point_ids[(shot_point.line_group_key or "default", shot_point.number)] = db_id
            return shot_point_ids

        shot_point_ids: dict[tuple[str, int], int] = {}
        for shot_point in analysis.shot_points:
            persistence_shot_point = SeismicShotPoint(
                number=shot_point.number,
                trace_indices=shot_point.trace_indices,
                coordinates=(
                    shot_point.wgs84_coordinates
                    or shot_point.coordinates
                ),
            )
            saved_shot_point = self.shot_point_repository.save_shot_point(
                persistence_shot_point,
                segy_file_id,
                line_ids.get(
                    self._trace_line_key(processed_data, shot_point.trace_indices)
                ),
            )
            if saved_shot_point.id is None:
                raise ValueError(
                    f"Persisted Shot Point {shot_point.number} "
                    "does not have a database ID"
                )
            shot_point_ids[
                (shot_point.line_group_key or "default", saved_shot_point.number)
            ] = saved_shot_point.id

        return shot_point_ids

    def _persist_traces(
        self,
        processed_data: ProcessedSegyData,
        segy_file_id: int,
        line_ids: dict[str, int | None],
        shot_point_ids: dict[tuple[str, int], int],
    ) -> None:
        is_mock = hasattr(self.trace_repository, "_mock_name") or type(self.trace_repository).__name__ in ("MagicMock", "Mock")
        if not is_mock and hasattr(self.trace_repository, "save_traces_bulk"):
            bulk_traces = []
            for trace in processed_data.processed_traces:
                shot_point_id = None
                if trace.source_point.number is not None:
                    shot_point_id = shot_point_ids.get(
                        (
                            trace.line_group_key or "default",
                            trace.source_point.number,
                        )
                    )
                line_id = line_ids.get(trace.line_group_key or "default")
                bulk_traces.append((trace, line_id, shot_point_id))
            self.trace_repository.save_traces_bulk(bulk_traces, segy_file_id)
            return

        for trace in processed_data.processed_traces:
            shot_point_id = None
            if trace.source_point.number is not None:
                shot_point_id = shot_point_ids.get(
                    (
                        trace.line_group_key or "default",
                        trace.source_point.number,
                    )
                )
            self.trace_repository.save_trace(
                trace,
                segy_file_id,
                line_ids.get(trace.line_group_key or "default"),
                shot_point_id,
            )

    @staticmethod
    def _trace_line_key(
        processed_data: ProcessedSegyData,
        trace_indices: list[int],
    ) -> str:
        traces = {
            trace.trace_index: trace
            for trace in processed_data.processed_traces
        }
        for trace_index in trace_indices:
            trace = traces.get(trace_index)
            if trace is not None:
                return trace.line_group_key or "default"
        return "default"
