from pathlib import Path

import pytest

from app.infrastructure.storage.local_file_storage import (
    LocalFileStorage,
)


def test_storage_creates_base_directory(
    tmp_path: Path,
):
    storage_path = tmp_path / "segy"

    LocalFileStorage(storage_path)

    assert storage_path.exists()
    assert storage_path.is_dir()


def test_save_file(
    tmp_path: Path,
):
    storage = LocalFileStorage(tmp_path)

    content = b"SEG-Y test content"

    file_path = storage.save(
        "test.sgy",
        content,
    )

    assert file_path.exists()
    assert file_path.read_bytes() == content


def test_save_returns_path_inside_storage(
    tmp_path: Path,
):
    storage = LocalFileStorage(tmp_path)

    file_path = storage.save(
        "test.sgy",
        b"test",
    )

    assert file_path.parent == tmp_path.resolve()


def test_delete_file(
    tmp_path: Path,
):
    storage = LocalFileStorage(tmp_path)

    file_path = storage.save(
        "test.sgy",
        b"test",
    )

    assert file_path.exists()

    storage.delete(file_path)

    assert not file_path.exists()


def test_delete_non_existing_file(
    tmp_path: Path,
):
    storage = LocalFileStorage(tmp_path)

    file_path = tmp_path / "does-not-exist.sgy"

    storage.delete(file_path)

    assert not file_path.exists()


def test_rejects_path_traversal(
    tmp_path: Path,
):
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.save(
            "../../outside.sgy",
            b"malicious content",
        )

def test_get_path_returns_existing_storage_path(
    tmp_path,
):
    storage = LocalFileStorage(tmp_path)

    path = storage.get_path("slb1.sgy")

    assert path == (
        tmp_path / "slb1.sgy"
    ).resolve()

def test_get_path_rejects_path_traversal(
    tmp_path,
):
    storage = LocalFileStorage(tmp_path)

    with pytest.raises(ValueError):
        storage.get_path("../outside.sgy")


    def test_save_uses_unique_path_when_filename_already_exists(tmp_path) -> None:
        storage = LocalFileStorage(tmp_path)

        first_path = storage.save("survey.sgy", b"first")
        second_path = storage.save("survey.sgy", b"second")

        assert first_path == tmp_path / "survey.sgy"
        assert second_path != first_path
        assert second_path.name.startswith("survey-")
        assert first_path.read_bytes() == b"first"
        assert second_path.read_bytes() == b"second"
