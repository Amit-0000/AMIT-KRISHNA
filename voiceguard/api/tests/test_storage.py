from __future__ import annotations

import pytest

from api.core.storage import LocalStorageBackend, StorageError

pytestmark = pytest.mark.asyncio


async def _chunks(*parts: bytes):
    for part in parts:
        yield part


async def test_save_and_read_round_trip(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    written = await backend.save_stream("a.wav", _chunks(b"hello ", b"world"))
    assert written == 11
    with backend.open_read("a.wav") as f:
        assert f.read() == b"hello world"


async def test_exists_and_delete(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    await backend.save_stream("b.wav", _chunks(b"data"))
    assert await backend.exists("b.wav") is True
    await backend.delete("b.wav")
    assert await backend.exists("b.wav") is False


async def test_delete_missing_key_does_not_raise(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    await backend.delete("never-existed.wav")  # must not raise


async def test_exists_false_for_missing_key(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    assert await backend.exists("missing.wav") is False


async def test_path_traversal_key_is_rejected(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(StorageError):
        await backend.save_stream("../../etc/passwd", _chunks(b"x"))


async def test_absolute_path_key_is_rejected(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(StorageError):
        await backend.save_stream("/etc/passwd", _chunks(b"x"))


async def test_creates_root_directory_if_missing(tmp_path):
    root = tmp_path / "nested" / "uploads"
    assert not root.exists()
    LocalStorageBackend(root)
    assert root.is_dir()
