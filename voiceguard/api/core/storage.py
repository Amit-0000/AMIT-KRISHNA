from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from api.core.config import get_settings


class StorageError(Exception):
    """Raised when a storage backend can't complete a save/read/delete."""


class StorageBackend(ABC):
    """Content-addressable-ish key/value file storage. `key` is an opaque,
    caller-generated identifier (e.g. f"{scan_id}{extension}") — callers are
    responsible for never deriving it from user-supplied input, so backends
    don't need to defend against path traversal from the caller's own code.
    This is the only contract business logic (api.scans.*) depends on, so a
    future S3/Azure Blob/GCS backend is a drop-in `get_storage_backend()`
    swap with no changes anywhere else."""

    @abstractmethod
    async def save_stream(self, key: str, chunks: AsyncIterator[bytes]) -> int:
        """Consumes `chunks` and persists them under `key`. Returns total bytes written."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Removes the object at `key`. Must not raise if it's already gone."""

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    def open_read(self, key: str) -> BinaryIO:
        """Returns a binary file-like object opened for reading. Caller owns closing it."""


class LocalStorageBackend(StorageBackend):
    """Local-disk implementation — the only backend implemented so far
    (STORAGE_BACKEND=local). Async method signatures match what a real
    network-backed implementation needs even though disk I/O itself is
    synchronous underneath."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Keys are always generated internally (see class docstring), but this
        # is a defense-in-depth guard against a key ever escaping the storage
        # root via ".." or an absolute path.
        candidate = (self._root / key).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            raise StorageError(f"Refusing to resolve key outside storage root: {key!r}")
        return candidate

    async def save_stream(self, key: str, chunks: AsyncIterator[bytes]) -> int:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        try:
            with open(path, "wb") as dest:
                async for chunk in chunks:
                    dest.write(chunk)
                    size += len(chunk)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return size

    async def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def open_read(self, key: str) -> BinaryIO:
        return open(self._resolve(key), "rb")

    def resolve_path(self, key: str) -> Path:
        """Local-backend-only escape hatch for code that genuinely needs a
        real filesystem path (e.g. stdlib `wave` for duration extraction).
        Not part of the StorageBackend contract — never call this from code
        that must stay storage-backend-agnostic."""
        return self._resolve(key)


@lru_cache
def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND == "local":
        return LocalStorageBackend(Path(settings.UPLOAD_STORAGE_ROOT))
    raise NotImplementedError(
        f"Storage backend {settings.STORAGE_BACKEND!r} is not implemented. Add an "
        "S3StorageBackend / AzureBlobStorageBackend / GCSStorageBackend implementing "
        "StorageBackend and branch on it here — that ABC is the only thing callers depend on."
    )


def reset_storage_backend_cache() -> None:
    """Test-only hook: forces get_storage_backend() to re-read settings
    (e.g. after monkeypatching UPLOAD_STORAGE_ROOT to a tmp_path)."""
    get_storage_backend.cache_clear()
