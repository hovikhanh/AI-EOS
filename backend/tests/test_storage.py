"""T-011: storage adapter volume cục bộ (ADR-004, SRS-CAP-03; phần lưu trữ của TC-FILE-03)."""

import hashlib
import inspect
import io
import os
import stat
import uuid
from datetime import timedelta
from pathlib import Path

import pytest

from aieos.platform.api import Process, load_settings
from aieos.storage.api import LocalStorage, ObjectNotFound, StorageError, storage_from_settings


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    root = tmp_path / "files"
    root.mkdir()
    return LocalStorage(root)


def files_under(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


def test_put_get_roundtrip_with_hash_and_size(storage: LocalStorage) -> None:
    data = b"%PDF-1.7 noi dung" * 1000
    stored = storage.put(io.BytesIO(data))
    assert isinstance(stored.key, uuid.UUID)
    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert stored.size == len(data)
    with storage.get(stored.key) as handle:
        assert handle.read() == data
    assert storage.exists(stored.key)


def test_keys_are_unique_and_random(storage: LocalStorage) -> None:
    keys = {storage.put(io.BytesIO(b"x")).key for _ in range(20)}
    assert len(keys) == 20
    assert all(key.version == 4 for key in keys)


@pytest.mark.parametrize(
    "hostile_name",
    ["../../etc/passwd.pdf", "/etc/passwd", "a" * 5000 + ".pdf", "tên\x00\x07\nđiều khiển.pdf", "..\\..\\x.pdf"],
)
def test_user_file_name_never_reaches_the_filesystem(tmp_path: Path, hostile_name: str) -> None:
    # TC-FILE-03 (phần storage): adapter không nhận tên file; đường dẫn chỉ gồm khóa UUID dưới thư mục gốc.
    root = tmp_path / "files"
    root.mkdir()
    storage = LocalStorage(root)
    stored = storage.put(io.BytesIO(hostile_name.encode("utf-8", "surrogatepass")))
    [path] = files_under(root)
    assert path.relative_to(root.resolve()).parts == (stored.key.hex[:2], stored.key.hex)
    assert not list(tmp_path.glob("etc*"))


def test_api_has_no_file_name_parameter() -> None:
    for name in ("put", "get", "exists", "delete_unreferenced"):
        parameters = inspect.signature(getattr(LocalStorage, name)).parameters
        assert not any("name" in p or "path" in p for p in parameters), name


@pytest.mark.parametrize("bad_key", ["../../etc/passwd", "0" * 32, 42])
def test_only_uuid_keys_accepted(storage: LocalStorage, bad_key: object) -> None:
    with pytest.raises(TypeError):
        storage.exists(bad_key)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        with storage.get(bad_key):  # type: ignore[arg-type]
            pass


def test_missing_object(storage: LocalStorage) -> None:
    key = uuid.uuid4()
    assert not storage.exists(key)
    with pytest.raises(ObjectNotFound):
        with storage.get(key):
            pass


def test_files_are_private(storage: LocalStorage, tmp_path: Path) -> None:
    stored = storage.put(io.BytesIO(b"bi mat"))
    [path] = files_under(tmp_path / "files")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.name == stored.key.hex


class FailingStream(io.RawIOBase):
    def __init__(self) -> None:
        self.calls = 0

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        self.calls += 1
        if self.calls > 1:
            raise OSError("đứt kết nối")
        return b"phan dau"


def test_failed_write_leaves_no_file(storage: LocalStorage, tmp_path: Path) -> None:
    with pytest.raises(OSError):
        storage.put(FailingStream())  # type: ignore[arg-type]
    assert files_under(tmp_path / "files") == []


def age(storage_root: Path, key: uuid.UUID, seconds: int) -> None:
    path = storage_root.resolve() / key.hex[:2] / key.hex
    past = path.stat().st_mtime - seconds
    os.utime(path, (past, past))


def test_delete_unreferenced_respects_references_and_age(storage: LocalStorage, tmp_path: Path) -> None:
    root = tmp_path / "files"
    kept = storage.put(io.BytesIO(b"con tham chieu")).key
    orphan = storage.put(io.BytesIO(b"mo coi")).key
    fresh = storage.put(io.BytesIO(b"vua ghi")).key
    for key in (kept, orphan):
        age(root, key, 3600)
    deleted = storage.delete_unreferenced(lambda key: key == kept, older_than=timedelta(minutes=10))
    assert deleted == [orphan]
    assert storage.exists(kept) and storage.exists(fresh) and not storage.exists(orphan)


def test_delete_unreferenced_requires_positive_age(storage: LocalStorage) -> None:
    with pytest.raises(ValueError):
        storage.delete_unreferenced(lambda key: False, older_than=timedelta(0))


def test_delete_unreferenced_ignores_foreign_files(storage: LocalStorage, tmp_path: Path) -> None:
    root = tmp_path / "files"
    stray = root / "ab" / "khong-phai-uuid"
    stray.parent.mkdir()
    stray.write_bytes(b"x")
    past = stray.stat().st_mtime - 3600
    os.utime(stray, (past, past))
    assert storage.delete_unreferenced(lambda key: False, older_than=timedelta(minutes=1)) == []
    assert stray.exists()


def test_root_must_exist(tmp_path: Path) -> None:
    with pytest.raises(StorageError):
        LocalStorage(tmp_path / "khong-co")


def test_readiness(storage: LocalStorage, tmp_path: Path) -> None:
    root = tmp_path / "files"
    assert storage.is_ready()
    root.chmod(0o500)
    try:
        assert os.geteuid() == 0 or not storage.is_ready()
    finally:
        root.chmod(0o700)


def test_storage_from_settings(tmp_path: Path) -> None:
    env = {
        "AIEOS_DATABASE_URL": "x",
        "AIEOS_STORAGE_PATH": str(tmp_path),
        "AIEOS_SCANNER_HOST": "scanner",
    }
    storage = storage_from_settings(load_settings(Process.WORKER, env))
    assert storage.is_ready()
