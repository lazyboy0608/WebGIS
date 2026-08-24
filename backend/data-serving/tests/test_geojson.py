from shapely.geometry import LineString, Point

from app.services.geojson import feature_collection, geometry_to_geojson


def test_geometry_to_geojson_point() -> None:
    result = geometry_to_geojson(Point(1, 2))
    assert result == {"type": "Point", "coordinates": [1.0, 2.0]}


def test_feature_collection_builds_frontend_geojson() -> None:
    features = [
        {
            "type": "Feature",
            "geometry": geometry_to_geojson(LineString([(0, 0), (1, 1)])),
            "properties": {"id": 1, "segy_file_id": 3},
        }
    ]

    result = feature_collection(features)
    assert result["type"] == "FeatureCollection"
    assert len(result["features"]) == 1
    assert result["features"][0]["properties"]["id"] == 1
