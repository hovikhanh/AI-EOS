"""Interface công khai của `storage` (ADR-004, Architecture §3 quy tắc 1)."""

from pathlib import Path

from aieos.platform.api import Settings
from aieos.storage.local import CHUNK_SIZE, LocalStorage, ObjectNotFound, StorageError, StoredObject

__all__ = ["CHUNK_SIZE", "LocalStorage", "ObjectNotFound", "StorageError", "StoredObject", "storage_from_settings"]


def storage_from_settings(settings: Settings) -> LocalStorage:
    """Storage của tiến trình api/worker theo `AIEOS_STORAGE_PATH` (T-004)."""
    return LocalStorage(Path(settings.config("AIEOS_STORAGE_PATH")))
