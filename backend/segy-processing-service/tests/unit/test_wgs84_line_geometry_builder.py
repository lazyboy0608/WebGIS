from app.domain.models.coordinate import Coordinate
from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.domain.models.line import Line
from app.services.crs_transformer import CRSTransformer
from app.services.wgs84_line_geometry_builder import (
    WGS84LineGeometryBuilder,
)


def test_build_wgs84_line_string() -> None:
    source_crs = CoordinateReferenceSystem(
        name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    transformer = CRSTransformer(
        source_crs=source_crs
    )

    builder = WGS84LineGeometryBuilder(
        crs_transformer=transformer
    )

    line = Line(
        coordinates=[
            Coordinate(
                x=1610154.0,
                y=-191584.0,
            ),
            Coordinate(
                x=1610134.0,
                y=-156966.0,
            ),
        ],
        trace_indices=[0, 1],
        shot_points=[1, 2],
    )

    geometry = builder.build(line)

    assert geometry.srid == 4326
    assert len(geometry.coordinates) == 2


def test_build_preserves_coordinate_order() -> None:
    source_crs = CoordinateReferenceSystem(
        name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    transformer = CRSTransformer(
        source_crs=source_crs
    )

    builder = WGS84LineGeometryBuilder(
        crs_transformer=transformer
    )

    line = Line(
        coordinates=[
            Coordinate(
                x=1610154.0,
                y=-191584.0,
            ),
            Coordinate(
                x=1610134.0,
                y=-156966.0,
            ),
        ]
    )

    geometry = builder.build(line)

    assert geometry.coordinates[0].x != line.coordinates[0].x
    assert geometry.coordinates[0].y != line.coordinates[0].y

    assert geometry.coordinates[1].x != line.coordinates[1].x
    assert geometry.coordinates[1].y != line.coordinates[1].y


def test_build_empty_line() -> None:
    source_crs = CoordinateReferenceSystem(
        name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    transformer = CRSTransformer(
        source_crs=source_crs
    )

    builder = WGS84LineGeometryBuilder(
        crs_transformer=transformer
    )

    line = Line()

    geometry = builder.build(line)

    assert geometry.srid == 4326
    assert geometry.coordinates == []

def test_coordinates_are_wgs84() -> None:
    source_crs = CoordinateReferenceSystem(
        name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    transformer = CRSTransformer(
        source_crs=source_crs
    )

    builder = WGS84LineGeometryBuilder(
        crs_transformer=transformer
    )

    line = Line(
        coordinates=[
            Coordinate(
                x=1610154.0,
                y=-191584.0,
            )
        ]
    )

    geometry = builder.build(line)

    coordinate = geometry.coordinates[0]

    assert -180 <= coordinate.x <= 180
    assert -90 <= coordinate.y <= 90