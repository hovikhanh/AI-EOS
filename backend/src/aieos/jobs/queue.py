"""Queue trên PostgreSQL (ADR-005, SRS-JOB-01, SRS-JOB-02, Architecture §8.4).

- `enqueue`: xếp job trong transaction của nơi gọi (transactional outbox); trùng `idempotency_key` → trả job cũ.
- `claim`: `SELECT … FOR UPDATE SKIP LOCKED`, đặt `RUNNING`, lease, `attempts + 1` trong một câu lệnh.
- `mark_succeeded`: gọi trong transaction lưu kết quả; chỉ thành công khi worker còn giữ job (chưa bị reaper lấy lại).
- `mark_failed`: lỗi tạm thời → `QUEUED` + backoff (còn lượt) hoặc `DEAD`; lỗi không thể retry → `FAILED`.
- `reap`: job `RUNNING` hết lease → `QUEUED` (còn lượt) hoặc `DEAD`.
Mọi thời điểm lấy từ đồng hồ CSDL (`now()`). `last_error` chỉ chứa tên loại lỗi, không chứa thông điệp (có thể chứa dữ
liệu hoặc secret).
"""

import random
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Row, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from aieos.jobs.models import JobRow
from aieos.jobs.registry import BACKOFF_BASE, BACKOFF_CAP, BACKOFF_JITTER, DEFAULT_LEASE, JobRegistry
from aieos.platform.api import CORRELATION_ID

MAX_PAYLOAD_VALUE_LENGTH = 200  # payload chỉ chứa ID/tham chiếu ngắn (ADR-005 Security Considerations)
_PAYLOAD_SCALARS = (str, int, bool, uuid.UUID, type(None))


class JobError(ValueError):
    """Yêu cầu xếp job không hợp lệ."""


@dataclass(frozen=True)
class ClaimedJob:
    id: uuid.UUID
    kind: str
    job_class: str
    payload: Mapping[str, Any]
    attempts: int
    max_attempts: int
    initiated_by: uuid.UUID | None
    correlation_id: str | None
    locked_by: str
    lease_expires_at: datetime


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Payload phẳng, chỉ giá trị đơn và ngắn (ID, số, cờ); UUID chuyển thành chuỗi."""
    if not isinstance(payload, Mapping):
        raise JobError("payload phải là mapping")
    clean: dict[str, Any] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not key:
            raise JobError("khóa payload phải là chuỗi không rỗng")
        if isinstance(value, float) or not isinstance(value, _PAYLOAD_SCALARS):
            raise JobError(f"payload[{key!r}]: chỉ nhận ID, số nguyên, chuỗi ngắn, bool hoặc null")
        if isinstance(value, uuid.UUID):
            value = str(value)
        if isinstance(value, str) and len(value) > MAX_PAYLOAD_VALUE_LENGTH:
            raise JobError(f"payload[{key!r}]: chuỗi quá dài — payload chỉ chứa tham chiếu")
        clean[key] = value
    return clean


def enqueue(
    session: Session,
    registry: JobRegistry,
    kind: str,
    *,
    idempotency_key: str,
    payload: Mapping[str, Any] | None = None,
    initiated_by: uuid.UUID | None = None,
    run_after: datetime | None = None,
) -> uuid.UUID:
    """Xếp job trong transaction hiện hành; `job_class`, `max_attempts` lấy từ registry. Trùng khóa → id job cũ."""
    entry = registry.get(kind)
    if not idempotency_key:
        raise JobError("idempotency_key không được rỗng")
    if entry.permission is not None and initiated_by is None:
        raise JobError(f"{kind}: loại job cần quyền người khởi tạo nên phải có initiated_by")
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "kind": kind,
        "job_class": entry.job_class.value,
        "payload": validate_payload(payload or {}),
        "max_attempts": entry.max_attempts,
        "idempotency_key": idempotency_key,
        "initiated_by": initiated_by,
        "correlation_id": CORRELATION_ID.get(),
    }
    if run_after is not None:
        values["run_after"] = run_after
    statement = (
        insert(JobRow).values(**values).on_conflict_do_nothing(index_elements=["idempotency_key"]).returning(JobRow.id)
    )
    inserted = session.execute(statement).scalar_one_or_none()
    if inserted is not None:
        return inserted
    existing = session.execute(
        text("SELECT id, kind FROM jobs.job WHERE idempotency_key = :key"), {"key": idempotency_key}
    ).one()
    if existing.kind != kind:
        raise JobError("idempotency_key đã dùng cho loại job khác")
    return uuid.UUID(str(existing.id))


_CLAIM = text(
    """
    UPDATE jobs.job
       SET status = 'RUNNING', attempts = attempts + 1, locked_by = :worker,
           lease_expires_at = now() + make_interval(secs => :lease)
     WHERE status = 'QUEUED' AND id = (
           SELECT id FROM jobs.job
            WHERE status = 'QUEUED' AND run_after <= now() AND kind = ANY(:kinds)
            ORDER BY run_after, id
            FOR UPDATE SKIP LOCKED
            LIMIT 1)
    RETURNING id, kind, job_class, payload, attempts, max_attempts, initiated_by, correlation_id, locked_by,
              lease_expires_at
    """
)


def claim(session: Session, kinds: list[str], worker_id: str, lease: timedelta = DEFAULT_LEASE) -> ClaimedJob | None:
    """Nhận một job đến hạn thuộc `kinds`; nơi gọi commit ngay để giải phóng khóa dòng."""
    if not kinds:
        return None
    row = session.execute(_CLAIM, {"worker": worker_id, "lease": lease.total_seconds(), "kinds": kinds}).one_or_none()
    return None if row is None else _claimed(row)


def _claimed(row: Row[Any]) -> ClaimedJob:
    return ClaimedJob(
        id=row.id,
        kind=row.kind,
        job_class=row.job_class,
        payload=dict(row.payload),
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        initiated_by=row.initiated_by,
        correlation_id=row.correlation_id,
        locked_by=row.locked_by,
        lease_expires_at=row.lease_expires_at,
    )


def extend_lease(session: Session, job_id: uuid.UUID, worker_id: str, lease: timedelta = DEFAULT_LEASE) -> bool:
    """Gia hạn lease khi job chạy lâu; False nếu worker không còn giữ job."""
    result = session.execute(
        text(
            "UPDATE jobs.job SET lease_expires_at = now() + make_interval(secs => :lease) "
            "WHERE id = :id AND locked_by = :worker AND status = 'RUNNING'"
        ),
        {"id": job_id, "worker": worker_id, "lease": lease.total_seconds()},
    )
    return _rowcount(result) == 1


def mark_succeeded(session: Session, job_id: uuid.UUID, worker_id: str) -> bool:
    """Đánh dấu `SUCCEEDED` trong transaction lưu kết quả (K2); False nếu worker đã mất job → nơi gọi rollback."""
    result = session.execute(
        text(
            "UPDATE jobs.job SET status = 'SUCCEEDED', finished_at = now(), lease_expires_at = NULL, "
            "last_error_code = NULL, last_error = NULL "
            "WHERE id = :id AND locked_by = :worker AND status = 'RUNNING'"
        ),
        {"id": job_id, "worker": worker_id},
    )
    return _rowcount(result) == 1


def backoff(attempts: int, rng: random.Random | None = None) -> timedelta:
    """min(30 s × 2^(attempts−1), 1 giờ) + jitter ngẫu nhiên tới 10% (D-56)."""
    exponent = max(attempts - 1, 0)
    base = BACKOFF_CAP if exponent >= 32 else min(BACKOFF_BASE * (2**exponent), BACKOFF_CAP)
    return base * (1 + (rng or random).uniform(0, BACKOFF_JITTER))


def mark_failed(
    session: Session, job: ClaimedJob, *, code: str, error_type: str, permanent: bool, rng: random.Random | None = None
) -> str | None:
    """Ghi lỗi; trả về trạng thái mới (`FAILED`/`QUEUED`/`DEAD`) hoặc None nếu worker đã mất job."""
    if permanent:
        status, delay = "FAILED", None
    elif job.attempts >= job.max_attempts:
        status, delay = "DEAD", None
    else:
        status, delay = "QUEUED", backoff(job.attempts, rng)
    result = session.execute(
        text(
            "UPDATE jobs.job SET status = :status, locked_by = NULL, lease_expires_at = NULL, "
            "last_error_code = :code, last_error = :error, "
            "run_after = CASE WHEN :status = 'QUEUED' THEN now() + make_interval(secs => :delay) ELSE run_after END, "
            "finished_at = CASE WHEN :status = 'QUEUED' THEN NULL ELSE now() END "
            "WHERE id = :id AND locked_by = :worker AND status = 'RUNNING'"
        ),
        {
            "status": status,
            "code": code,
            "error": error_type,
            "delay": delay.total_seconds() if delay else 0.0,
            "id": job.id,
            "worker": job.locked_by,
        },
    )
    return status if _rowcount(result) == 1 else None


_REAP = text(
    """
    UPDATE jobs.job
       SET status = CASE WHEN attempts >= max_attempts THEN 'DEAD' ELSE 'QUEUED' END,
           finished_at = CASE WHEN attempts >= max_attempts THEN now() END,
           locked_by = NULL, lease_expires_at = NULL, run_after = now(), last_error_code = 'LEASE_EXPIRED'
     WHERE id IN (
           SELECT id FROM jobs.job
            WHERE status = 'RUNNING' AND lease_expires_at < now()
            FOR UPDATE SKIP LOCKED)
    RETURNING id, status
    """
)


def reap(session: Session) -> dict[uuid.UUID, str]:
    """Trả job `RUNNING` hết lease về `QUEUED` (còn lượt) hoặc `DEAD`; trả về {id: trạng thái mới}."""
    return {row.id: row.status for row in session.execute(_REAP)}


def count_by_status(session: Session) -> dict[str, int]:
    """Số job theo trạng thái (cho trang tình trạng hệ thống — ADR-012, T-110)."""
    rows = session.execute(text("SELECT status, count(*) AS n FROM jobs.job GROUP BY status"))
    return {row.status: row.n for row in rows}


def _rowcount(result: Any) -> int:
    return int(result.rowcount)
