from pathlib import Path

from app.domain.models.line_string import LineString

from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.services.coordinate_transformer import (
    CoordinateTransformer,
)
from app.services.crs_transformer import (
    CRSTransformer,
)
from app.services.line_geometry_builder import (
    LineGeometryBuilder,
)
from app.services.segy_validator import SegyValidator
from app.infrastructure.segy.segyio_reader import (
    SegyIOReader,
)
from app.services.trace_processor import TraceProcessor
from app.services.wgs84_line_geometry_builder import (
    WGS84LineGeometryBuilder,
)


def test_build_slb1_wgs84_line_geometry() -> None:
    file_path = Path(
        "data/input/slb1.sgy"
    )

    # ---------------------------------------------------------
    # 1. Validate SEG-Y
    # ---------------------------------------------------------

    validator = SegyValidator()

    validator.validate(file_path)

    # ---------------------------------------------------------
    # 2. Read SEG-Y traces
    # ---------------------------------------------------------

    reader = SegyIOReader()

    traces = reader.iter_traces(
        file_path=file_path,
        include_samples=False,
    )

    # ---------------------------------------------------------
    # 3. Process traces
    # ---------------------------------------------------------

    coordinate_transformer = CoordinateTransformer()

    trace_processor = TraceProcessor(
        coordinate_transformer
    )

    processed_traces = (
        trace_processor.process(trace)
        for trace in traces
    )

    # ---------------------------------------------------------
    # 4. Build source Line
    # ---------------------------------------------------------

    line_geometry_builder = LineGeometryBuilder()

    line = line_geometry_builder.build(
        processed_traces
    )

    assert line is not None

    assert len(line.coordinates) == 630
    assert len(line.trace_indices) == 630
    assert len(line.shot_points) == 630

    # ---------------------------------------------------------
    # 5. Define source CRS
    # ---------------------------------------------------------

    source_crs = CoordinateReferenceSystem(
        name=(
            "NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
        )
    )

    # ---------------------------------------------------------
    # 6. Create CRS transformer
    # ---------------------------------------------------------

    crs_transformer = CRSTransformer(
        source_crs=source_crs
    )

    # ---------------------------------------------------------
    # 7. Build WGS84 LineString
    # ---------------------------------------------------------

    wgs84_geometry_builder = (
        WGS84LineGeometryBuilder(
            crs_transformer=crs_transformer
        )
    )

    geometry = wgs84_geometry_builder.build(
        line
    )

    # ---------------------------------------------------------
    # 8. Validate domain LineString
    # ---------------------------------------------------------

    assert isinstance(
        geometry,
        LineString,
    )

    assert geometry.srid == 4326

    assert len(geometry.coordinates) == 630

    assert len(geometry.coordinates) == (
        len(line.coordinates)
    )

    # ---------------------------------------------------------
    # 9. Validate WGS84 coordinate range
    # ---------------------------------------------------------

    for coordinate in geometry.coordinates:

        assert -180.0 <= coordinate.x <= 180.0

        assert -90.0 <= coordinate.y <= 90.0

    # ---------------------------------------------------------
    # 10. Validate first coordinate transformation
    # ---------------------------------------------------------

    first_coordinate = geometry.coordinates[0]

    assert first_coordinate.x != (
        line.coordinates[0].x
    )

    assert first_coordinate.y != (
        line.coordinates[0].y
    )

    # ---------------------------------------------------------
    # 11. Validate last coordinate transformation
    # ---------------------------------------------------------

    last_coordinate = geometry.coordinates[-1]

    assert last_coordinate.x != (
        line.coordinates[-1].x
    )

    assert last_coordinate.y != (
        line.coordinates[-1].y
    )