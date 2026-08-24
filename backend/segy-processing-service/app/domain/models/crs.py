from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)


SOURCE_CRS = CoordinateReferenceSystem(
    name="NAD_1927_StatePlane_Louisiana_South_FIPS_1702",
    authority="EPSG",
    code=26782,
    units="US survey foot",
)


WGS84_CRS = CoordinateReferenceSystem(
    name="WGS 84",
    authority="EPSG",
    code=4326,
    units="degree",
)