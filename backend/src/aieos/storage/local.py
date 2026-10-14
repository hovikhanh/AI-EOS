"""Storage adapter volume cục bộ (T-011, ADR-004, SRS-CAP-03).

- Khóa lưu trữ là UUID do adapter sinh; đường dẫn chỉ tạo từ `key.hex` — không tham số nào nhận tên file người dùng.
  Tên file (đã chuẩn hóa) chỉ là metadata do `capture` lưu trong CSDL (T-203).
- Ghi nguyên tử: file tạm trong cùng thư mục → fsync → `os.replace`; quyền 0o600.
- SHA-256 và kích thước trả về khi `put` để `capture` lưu cùng metadata (ADR-004).
- `delete_unreferenced`: xóa file không còn được tham chiếu và đủ cũ; tuổi tối thiểu do nơi gọi truyền (chống xóa file
  vừa ghi mà CSDL chưa commit) — không đặt mặc định.
"""

import hashlib
import os
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import BinaryIO

CHUNK_SIZE = 1024 * 1024
FILE_MODE = 0o600
_TEMP_PREFIX = ".tmp-"


class StorageError(Exception):
    """Lỗi storage; thông điệp không chứa nội dung file."""


class ObjectNotFound(StorageError):
    pass


@dataclass(frozen=True)
class StoredObject:
    key: uuid.UUID
    sha256: str
    size: int


class LocalStorage:
    """Triển khai mặc định của storage adapter: thư mục trên volume cục bộ."""

    def __init__(self, root: Path) -> None:
        resolved = root.resolve()
        if not resolved.is_dir():
            raise StorageError("Thư mục storage không tồn tại hoặc không phải thư mục")
        self._root = resolved

    def _path(self, key: uuid.UUID) -> Path:
        if not isinstance(key, uuid.UUID):
            raise TypeError("Khóa storage phải là uuid.UUID")
        return self._root / key.hex[:2] / key.hex

    def put(self, stream: BinaryIO) -> StoredObject:
        key = uuid.uuid4()
        target = self._path(key)
        target.parent.mkdir(mode=0o700, exist_ok=True)
        digest = hashlib.sha256()
        size = 0
        fd, temp_name = tempfile.mkstemp(prefix=_TEMP_PREFIX, dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as temp:
                os.fchmod(temp.fileno(), FILE_MODE)
                while chunk := stream.read(CHUNK_SIZE):
                    digest.update(chunk)
                    size += len(chunk)
                    temp.write(chunk)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, target)
        except BaseException:
            Path(temp_name).unlink(missing_ok=True)
            raise
        return StoredObject(key=key, sha256=digest.hexdigest(), size=size)

    @contextmanager
    def get(self, key: uuid.UUID) -> Iterator[BinaryIO]:
        path = self._path(key)
        try:
            handle = path.open("rb")
        except FileNotFoundError:
            raise ObjectNotFound(f"Không có đối tượng {key}") from None
        with handle:
            yield handle

    def exists(self, key: uuid.UUID) -> bool:
        return self._path(key).is_file()

    def delete_unreferenced(self, is_referenced: Callable[[uuid.UUID], bool], older_than: timedelta) -> list[uuid.UUID]:
        """Xóa đối tượng mà `is_referenced` trả False và có tuổi ≥ `older_than`; trả về khóa đã xóa."""
        if older_than <= timedelta(0):
            raise ValueError("older_than phải dương")
        cutoff = time.time() - older_than.total_seconds()
        deleted: list[uuid.UUID] = []
        for path in sorted(self._root.glob("??/*")):
            if path.name.startswith(_TEMP_PREFIX) or not path.is_file():
                continue
            try:
                key = uuid.UUID(hex=path.name)
            except ValueError:
                continue
            if key.hex != path.name or path.parent.name != key.hex[:2]:
                continue
            if path.stat().st_mtime > cutoff or is_referenced(key):
                continue
            path.unlink(missing_ok=True)
            deleted.append(key)
        return deleted

    def is_ready(self) -> bool:
        """Kiểm tra cho `/health/ready` (ADR-012): thư mục gốc tồn tại, đọc/ghi được."""
        return self._root.is_dir() and os.access(self._root, os.R_OK | os.W_OK | os.X_OK)
