from pyproj import CRS
from pyproj.transformer import Transformer, TransformerGroup

from app.domain.models.coordinate import Coordinate
from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)


class CRSTransformer:
    """
    Transforms coordinates between coordinate reference systems.

    The transformer uses PROJ's best available transformation
    between the source CRS and WGS84.
    """

    WGS84_EPSG = 4326

    def __init__(
        self,
        source_crs: CoordinateReferenceSystem | str,
    ) -> None:

        if isinstance(source_crs, str):
            source_crs = CoordinateReferenceSystem(name=source_crs)

        self.source_crs_definition = source_crs

        self.source_crs = CRS.from_user_input(
            source_crs.name
        )

        self.target_crs = CRS.from_epsg(
            self.WGS84_EPSG
        )

        transformer_group = TransformerGroup(
            self.source_crs,
            self.target_crs,
            always_xy=True,
        )

        if not transformer_group.best_available:
            raise RuntimeError(
                "Best available CRS transformation "
                "is not available."
            )

        if not transformer_group.transformers:
            raise RuntimeError(
                "No CRS transformation is available "
                "for the specified source CRS."
            )

        self.transformer: Transformer = (
            transformer_group.transformers[0]
        )

        self.accuracy = self.transformer.accuracy

        self.description = (
            self.transformer.description
        )

    def transform_to_wgs84(
        self,
        coordinate: Coordinate,
    ) -> Coordinate:

        x, y = self.transformer.transform(
            coordinate.x,
            coordinate.y,
        )

        return Coordinate(
            x=x,
            y=y,
        )