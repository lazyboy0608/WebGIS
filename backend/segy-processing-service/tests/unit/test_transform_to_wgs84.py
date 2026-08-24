import pytest

from app.domain.models.coordinate import Coordinate
from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.services.crs_transformer import CRSTransformer


def test_transform_to_wgs84() -> None:
    source_crs = CoordinateReferenceSystem(
        name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    transformer = CRSTransformer(
        source_crs=source_crs
    )

    coordinate = Coordinate(
        x=1610154.0,
        y=-191584.0,
    )

    result = transformer.transform_to_wgs84(
        coordinate
    )

    assert result is not None

    # WGS84 longitude/latitude
    assert -93.0 < result.x < -92.0
    assert 27.0 < result.y < 29.0

    # Kết quả phải khác coordinate nguồn
    assert result.x != coordinate.x
    assert result.y != coordinate.y