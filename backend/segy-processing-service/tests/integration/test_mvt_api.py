def test_get_vector_tile_endpoint(client):
    response = client.get("/api/segy-files/mvt/10/500/300.pbf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-protobuf"


def test_get_file_vector_tile_endpoint(client):
    response = client.get("/api/segy-files/1/mvt/10/500/300.pbf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/x-protobuf"
