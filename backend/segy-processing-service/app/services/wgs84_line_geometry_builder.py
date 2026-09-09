from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)
from app.domain.models.line import Line
from app.domain.models.line_string import LineString
from app.services.crs_transformer import CRSTransformer


class WGS84LineGeometryBuilder:
    """
    Builds a WGS84 LineString from a source Line.
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
    ) -> LineString:

        transformer = self.crs_transformer
        if source_crs is not None:
            if isinstance(source_crs, str):
                source_crs = CoordinateReferenceSystem(name=source_crs)
            transformer = CRSTransformer(source_crs)

        transformed_coordinates = [
            transformer.transform_to_wgs84(
                coordinate
            )
            for coordinate in line.coordinates
        ]

        return LineString(
            coordinates=transformed_coordinates,
            srid=4326,
        )
