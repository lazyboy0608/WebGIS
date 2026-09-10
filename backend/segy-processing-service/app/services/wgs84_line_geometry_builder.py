from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.domain.models.line import Line
from app.domain.models.line_string import LineString
from app.services.crs_transformer import CRSTransformer


class WGS84LineGeometryBuilder:
    """
    Builds a LineString in WGS84 (EPSG:4326) from a source Line
    to ensure all PostGIS spatial operations (MVT, bounding boxes,
    intersections, spatial filters, and WebGIS map views) work accurately.
    """

    def __init__(
        self,
        crs_transformer: CRSTransformer,
    ) -> None:
        self.crs_transformer = crs_transformer

    def build(
        self,
        line: Line,
        source_crs: CoordinateReferenceSystem | str | None = None,
        target_crs: CoordinateReferenceSystem | str | None = None,
    ) -> LineString:

        s_crs = source_crs if source_crs is not None else self.crs_transformer.source_crs_definition
        if isinstance(s_crs, str):
            s_crs = CoordinateReferenceSystem(name=s_crs)

        # The spatial geometry stored in PostGIS for map rendering must ALWAYS be in WGS84 (EPSG:4326)
        transformer = CRSTransformer(source_crs=s_crs, target_crs="EPSG:4326")

        transformed_coordinates = [
            transformer.transform(
                coordinate
            )
            for coordinate in line.coordinates
        ]

        return LineString(
            coordinates=transformed_coordinates,
            srid=4326,
        )
