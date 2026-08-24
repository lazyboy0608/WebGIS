from fastapi.testclient import TestClient

from app.domain.models.segy_file import SegyFile
from app.infrastructure.database.repositories.segy_file_repository import (
    SQLAlchemySegyFileRepository,
)
from app.infrastructure.database.session import SessionLocal
from app.main import app


client = TestClient(app)

def test_get_segy_file_not_found():
    response = client.get("/api/segy-files/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "SEG-Y file with id=999999 not found"
    )

def test_get_segy_file():
    with SessionLocal() as session:
        repository = SQLAlchemySegyFileRepository(session)

        created = repository.create(
            SegyFile(
                id=None,
                filename="api_test.sgy",
                file_path="/tmp/api_test.sgy",
                file_size=1024,
                source_crs="EPSG:4326",
                trace_count=100,
                line_count=2,
            )
        )

        session.commit()

        file_id = created.id

    response = client.get(f"/api/segy-files/{file_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == file_id
    assert data["filename"] == "api_test.sgy"
    assert data["file_path"] == "/tmp/api_test.sgy"
    assert data["file_size"] == 1024
    assert data["source_crs"] == "EPSG:4326"
    assert data["trace_count"] == 100
    assert data["line_count"] == 2

def test_create_segy_file(client):
    response = client.post(
        "/api/segy-files",
        json={
            "filename": "api_create_test.sgy",
            "file_path": "/tmp/api_create_test.sgy",
            "file_size": 1024,
            "source_crs": "EPSG:4326",
            "trace_count": 100,
            "line_count": 2,
            "geometry": None,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["filename"] == "api_create_test.sgy"
    assert data["file_path"] == "/tmp/api_create_test.sgy"
    assert data["file_size"] == 1024
    assert data["source_crs"] == "EPSG:4326"
    assert data["trace_count"] == 100
    assert data["line_count"] == 2

def test_list_segy_files(client):
    response = client.get("/api/segy-files")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

def test_get_segy_file_by_filename(client):
    create_response = client.post(
        "/api/segy-files",
        json={
            "filename": "slb1.sgy",
            "file_path": "/data/slb1.sgy",
            "file_size": 2676060,
            "source_crs": "EPSG:4326",
            "trace_count": 630,
            "line_count": 1,
            "geometry": None,
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/segy-files/filename/slb1.sgy"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "slb1.sgy"

def test_update_segy_file(client):
    create_response = client.post(
        "/api/segy-files",
        json={
            "filename": "original.sgy",
            "file_path": "/data/original.sgy",
            "file_size": 1000,
            "source_crs": "EPSG:4326",
            "trace_count": 10,
            "line_count": 1,
            "geometry": None,
        },
    )

    assert create_response.status_code == 201

    created = create_response.json()
    file_id = created["id"]

    response = client.put(
        f"/api/segy-files/{file_id}",
        json={
            "filename": "updated.sgy",
            "file_path": "/data/updated.sgy",
            "file_size": 2000,
            "source_crs": "EPSG:4326",
            "trace_count": 20,
            "line_count": 2,
            "geometry": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == file_id
    assert data["filename"] == "updated.sgy"
    assert data["file_size"] == 2000
    assert data["trace_count"] == 20
    assert data["line_count"] == 2

def test_update_segy_file_not_found(client):
    response = client.put(
        "/api/segy-files/999999",
        json={
            "filename": "updated.sgy",
            "file_path": "/data/updated.sgy",
            "file_size": 2000,
            "source_crs": "EPSG:4326",
            "trace_count": 20,
            "line_count": 2,
            "geometry": None,
        },
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "SEG-Y file with id=999999 not found"
    )

def test_delete_segy_file(client):
    create_response = client.post(
        "/api/segy-files",
        json={
            "filename": "delete-test.sgy",
            "file_path": "/data/delete-test.sgy",
            "file_size": 1000,
            "source_crs": "EPSG:4326",
            "trace_count": 10,
            "line_count": 1,
            "geometry": None,
        },
    )

    assert create_response.status_code == 201

    created = create_response.json()
    file_id = created["id"]

    response = client.delete(
        f"/api/segy-files/{file_id}"
    )

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(
        f"/api/segy-files/{file_id}"
    )

    assert get_response.status_code == 404

def test_delete_segy_file_not_found(client):
    response = client.delete(
        "/api/segy-files/999999"
    )

    assert response.status_code == 404

    assert response.json()["detail"] == (
        "SEG-Y file with id=999999 not found"
    )