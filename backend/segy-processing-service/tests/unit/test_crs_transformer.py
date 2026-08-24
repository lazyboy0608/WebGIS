import pytest

from app.domain.models.coordinate import (
    Coordinate,
)

from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.services.crs_transformer import (
    CRSTransformer,
)


def create_transformer() -> CRSTransformer:
    source_crs = CoordinateReferenceSystem(
        name=(
            "NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
        )
    )

    return CRSTransformer(
        source_crs=source_crs
    )


def test_transform_to_wgs84() -> None:
    transformer = create_transformer()

    coordinate = Coordinate(
        x=1610154.0,
        y=-191584.0,
    )

    result = transformer.transform_to_wgs84(
        coordinate
    )

    assert result.x == pytest.approx(
        -92.5424554937869,
        abs=1e-9,
    )

    assert result.y == pytest.approx(
        28.134507344310485,
        abs=1e-9,
    )


def test_uses_best_available_transformation() -> None:
    transformer = create_transformer()

    assert transformer.accuracy == 5.0

    assert (
        "NAD27 to WGS 84 (79)"
        in transformer.description
    )