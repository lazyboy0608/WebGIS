from __future__ import annotations

from typing import Any

from shapely.geometry.base import BaseGeometry


def geometry_to_geojson(geom: BaseGeometry | None) -> dict[str, Any] | None:
    if geom is None:
        return None

    if hasattr(geom, "geom_type") and hasattr(geom, "coords"):
        if geom.geom_type == "Point":
            x, y = geom.coords[0]
            return {"type": "Point", "coordinates": [x, y]}

        if geom.geom_type in {"LineString", "MultiLineString"}:
            return {
                "type": geom.geom_type,
                "coordinates": list(geom.coords) if geom.geom_type == "LineString" else list(geom.geoms[0].coords) if len(geom.geoms) == 1 else [list(g.coords) for g in geom.geoms],
            }

        return {
            "type": geom.geom_type,
            "coordinates": list(geom.coords),
        }

    return None


def feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": features,
    }
