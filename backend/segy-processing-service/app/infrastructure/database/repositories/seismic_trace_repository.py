from geoalchemy2.elements import WKTElement
from sqlalchemy.orm import Session

from app.domain.interfaces.repositories.trace_repository import TraceRepository
from app.domain.models.trace import ProcessedTrace
from app.infrastructure.database.models.seismic_trace_model import (
    SeismicTraceModel,
)


class SQLAlchemySeismicTraceRepository(TraceRepository):
    """SQLAlchemy implementation of TraceRepository."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self.session = session

    def save_trace(
        self,
        trace: ProcessedTrace,
        segy_file_id: int,
        seismic_line_id: int | None = None,
        shot_point_id: int | None = None,
    ) -> None:

        coordinate = trace.wgs84_coordinate or trace.coordinate

        if coordinate is None:
            raise ValueError("Seismic trace coordinate is required.")

        geometry = WKTElement(
            f"POINT({coordinate.x} {coordinate.y})",
            srid=4326,
        )

        model = SeismicTraceModel(
            trace_index=trace.trace_index,
            segy_file_id=segy_file_id,
            seismic_line_id=seismic_line_id,
            shot_point_id=shot_point_id,
            geometry=geometry,
        )

        self.session.add(model)

    def save_traces_bulk(
        self,
        traces: list[tuple[ProcessedTrace, int | None, int | None]],
        segy_file_id: int,
        batch_size: int = 5000,
    ) -> None:
        """Bulk save seismic traces in memory-efficient batches."""
        if not traces:
            return

        models: list[SeismicTraceModel] = []
        for trace, seismic_line_id, shot_point_id in traces:
            coord = trace.wgs84_coordinate or trace.coordinate
            if coord is None:
                continue
            geom = WKTElement(f"POINT({coord.x} {coord.y})", srid=4326)
            models.append(
                SeismicTraceModel(
                    trace_index=trace.trace_index,
                    segy_file_id=segy_file_id,
                    seismic_line_id=seismic_line_id,
                    shot_point_id=shot_point_id,
                    geometry=geom,
                )
            )
            if len(models) >= batch_size:
                self.session.bulk_save_objects(models)
                models.clear()

        if models:
            self.session.bulk_save_objects(models)
        self.session.flush()
