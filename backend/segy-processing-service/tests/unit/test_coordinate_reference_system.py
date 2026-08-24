from app.domain.models.crs import (
    SOURCE_CRS,
    WGS84_CRS,
)


def test_source_crs() -> None:
    assert SOURCE_CRS.name == (
        "NAD_1927_StatePlane_Louisiana_South_FIPS_1702"
    )

    assert SOURCE_CRS.authority == "EPSG"

    assert SOURCE_CRS.code == 26782

    assert SOURCE_CRS.units == "US survey foot"


def test_wgs84_crs() -> None:
    assert WGS84_CRS.name == "WGS 84"

    assert WGS84_CRS.authority == "EPSG"

    assert WGS84_CRS.code == 4326

    assert WGS84_CRS.units == "degree"