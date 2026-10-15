"""Registry loại job (ADR-005 Amendment 1, SRS-AIC-06) và hằng số kỹ thuật của queue (D-56).

Mỗi `kind` có một `job_class` cố định khai báo trong code khi đăng ký; không cấu hình qua giao diện hay CSDL. Nơi xếp
job không truyền `job_class`: queue lấy từ registry.
"""

import uuid
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any, Protocol

from sqlalchemy.orm import Session

# --- Hằng số kỹ thuật — `PROPOSED`, CDA chấp nhận làm mặc định (D-56, 15/10/2026); không phải ngưỡng nghiệp vụ. ---
DEFAULT_LEASE = timedelta(seconds=300)  # PROPOSED (D-56): lease khi claim; handler gia hạn bằng `extend_lease()`
BACKOFF_BASE = timedelta(seconds=30)  # PROPOSED (D-56): min(30 s × 2^(attempts−1), 1 giờ)
BACKOFF_CAP = timedelta(hours=1)  # PROPOSED (D-56)
BACKOFF_JITTER = 0.10  # PROPOSED (D-56): jitter ngẫu nhiên tới 10%
POLL_INTERVAL = timedelta(seconds=1)  # PROPOSED (D-56): worker poll khi hàng đợi rỗng
MAINTENANCE_INTERVAL = timedelta(seconds=30)  # PROPOSED (D-56): chu kỳ reaper và scheduler


class JobClass(StrEnum):
    ORCHESTRATION = "ORCHESTRATION"  # điều phối: lên lịch, nhắc việc, đánh dấu quá hạn — không ghi bảng nghiệp vụ
    AI_CONTENT = "AI_CONTENT"  # AI tạo nội dung mới (vd. tóm tắt Briefing)
    BUSINESS_WRITE = "BUSINESS_WRITE"  # ghi dữ liệu nghiệp vụ, luôn qua gateway (ADR-008)


class JobContext(Protocol):
    """Ngữ cảnh truyền cho handler. `session` là transaction sẽ commit cùng trạng thái `SUCCEEDED` (SRS-JOB-02)."""

    @property
    def job_id(self) -> uuid.UUID: ...
    @property
    def kind(self) -> str: ...
    @property
    def payload(self) -> Mapping[str, Any]: ...
    @property
    def attempt(self) -> int: ...
    @property
    def initiated_by(self) -> uuid.UUID | None: ...
    @property
    def session(self) -> Session: ...
    def extend_lease(self) -> None: ...


Handler = Callable[[JobContext], None]


class JobRegistryError(ValueError):
    """Đăng ký hoặc tra cứu loại job không hợp lệ."""


@dataclass(frozen=True)
class JobKind:
    kind: str
    job_class: JobClass
    handler: Handler
    max_attempts: int
    permission: str | None = None  # permission người khởi tạo phải còn giữ khi job chạy (SRS-JOB-03)

    def __post_init__(self) -> None:
        if not self.kind or self.kind != self.kind.strip():
            raise JobRegistryError("kind không hợp lệ")
        if not isinstance(self.job_class, JobClass):
            raise JobRegistryError(f"{self.kind}: job_class phải là JobClass")
        if self.max_attempts < 1:
            raise JobRegistryError(f"{self.kind}: max_attempts phải ≥ 1 (mỗi loại job tự khai báo, D-56)")


class JobRegistry:
    """Danh sách loại job của tiến trình; composition root (`app`) gọi `register` của từng module."""

    def __init__(self) -> None:
        self._kinds: dict[str, JobKind] = {}

    def register(
        self, kind: str, job_class: JobClass, handler: Handler, *, max_attempts: int, permission: str | None = None
    ) -> JobKind:
        if kind in self._kinds:
            raise JobRegistryError(f"{kind}: đã đăng ký")
        entry = JobKind(kind, job_class, handler, max_attempts, permission)
        self._kinds[kind] = entry
        return entry

    def get(self, kind: str) -> JobKind:
        try:
            return self._kinds[kind]
        except KeyError:
            raise JobRegistryError(f"{kind}: chưa đăng ký") from None

    def kinds(self) -> list[str]:
        return sorted(self._kinds)

    def __iter__(self) -> Iterator[JobKind]:
        return iter(self._kinds.values())

    def __len__(self) -> int:
        return len(self._kinds)
