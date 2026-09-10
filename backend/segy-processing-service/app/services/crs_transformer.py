import re
from pyproj import CRS
from pyproj.transformer import Transformer, TransformerGroup

from app.domain.models.coordinate import Coordinate
from app.domain.models.coordinate_reference_system import (
    CoordinateReferenceSystem,
)


def normalize_crs_string(crs_input: str | None) -> str:
    """Normalize user or header CRS inputs into standard EPSG or PROJ strings."""
    if not crs_input:
        return "EPSG:4326"
    s = str(crs_input).strip()

    # 1. Search for explicit EPSG:XXXX pattern
    epsg_match = re.search(r"EPSG\s*[:=]\s*(\d+)", s, re.IGNORECASE)
    if epsg_match:
        return f"EPSG:{epsg_match.group(1)}"

    # 2. Pure digits (e.g. "3405", "4326")
    if s.isdigit():
        return f"EPSG:{s}"

    s_upper = s.upper()

    # 3. VN-2000 keywords
    if "VN-2000" in s_upper or "VN2000" in s_upper:
        if "48" in s_upper or "105" in s_upper:
            return "EPSG:3405"
        elif "49" in s_upper or "111" in s_upper:
            return "EPSG:3406"
        elif "GEO" in s_upper or "KINH" in s_upper or "DEG" in s_upper:
            return "EPSG:4756"
        elif "5899" in s_upper or "NAT" in s_upper or "3 DEG" in s_upper:
            return "EPSG:5899"
        return "EPSG:3405"

    # 4. Hanoi 1972 keywords
    if "HANOI" in s_upper or "HN-72" in s_upper or "HN72" in s_upper:
        if "49" in s_upper:
            return "EPSG:2049"
        return "EPSG:2048"

    # 5. Pseudo Mercator / Web Mercator
    if "3857" in s_upper or "MERCATOR" in s_upper:
        return "EPSG:3857"

    # 6. WGS84 / UTM keywords
    if "UTM" in s_upper:
        if "48" in s_upper:
            return "EPSG:32648"
        elif "49" in s_upper:
            return "EPSG:32649"
        elif "50" in s_upper:
            return "EPSG:32650"

    if "WGS" in s_upper or "GPS" in s_upper:
        return "EPSG:4326"

    return s


class CRSTransformer:
    """
    Transforms coordinates between coordinate reference systems.

    The transformer uses PROJ's best available transformation
    between the source CRS and target CRS (default WGS84 EPSG:4326).
    """

    WGS84_EPSG = 4326

    def __init__(
        self,
        source_crs: CoordinateReferenceSystem | str,
        target_crs: CoordinateReferenceSystem | str = "EPSG:4326",
    ) -> None:

        s_name = source_crs.name if isinstance(source_crs, CoordinateReferenceSystem) else str(source_crs)
        t_name = target_crs.name if isinstance(target_crs, CoordinateReferenceSystem) else str(target_crs)

        norm_source = normalize_crs_string(s_name)
        norm_target = normalize_crs_string(t_name)

        self.source_crs_definition = CoordinateReferenceSystem(name=norm_source)
        self.target_crs_definition = CoordinateReferenceSystem(name=norm_target)

        try:
            self.source_crs = CRS.from_user_input(norm_source)
        except Exception:
            self.source_crs = CRS.from_user_input("EPSG:4326")

        try:
            self.target_crs = CRS.from_user_input(norm_target)
        except Exception:
            self.target_crs = CRS.from_user_input("EPSG:4326")

        transformer_group = TransformerGroup(
            self.source_crs,
            self.target_crs,
            always_xy=True,
        )

        if not transformer_group.transformers:
            raise RuntimeError(
                f"No CRS transformation is available from {source_crs.name} to {target_crs.name}."
            )

        self.transformer: Transformer = (
            transformer_group.transformers[0]
        )

        self.accuracy = self.transformer.accuracy

        self.description = (
            self.transformer.description
        )

    def transform(
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

    def transform_to_wgs84(
        self,
        coordinate: Coordinate,
    ) -> Coordinate:
        return self.transform(coordinate)