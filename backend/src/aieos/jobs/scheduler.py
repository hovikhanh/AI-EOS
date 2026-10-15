"""Lịch định kỳ (ADR-005, SRS-AIC-06, D-56).

- Chỉ hỗ trợ `interval` (D-56). Một instance scheduler tại một thời điểm nhờ `pg_try_advisory_xact_lock`.
- Mỗi lần đến hạn tạo một job với `idempotency_key = <schedule_id>:<slot>` (Database_Design §5).
- Lỡ nhiều slot (worker tắt): chỉ tạo job cho slot gần nhất, nhảy `next_run_at` sang tương lai — không chạy bù (D-56).
- Lịch `may_write` (`job_class <> 'ORCHESTRATION'`): trước khi xếp job hỏi `should_skip(schedule)`; có lý do → ghi
  `last_skipped_at`, `last_skip_reason`, nhảy sang chu kỳ kế tiếp, log + audit `schedule.skipped`, không chạy bù (K3).
  Kiểm tra kill switch thật được gắn ở T-303; mặc định không bỏ qua.
"""

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.jobs.models import ScheduleRow
from aieos.jobs.queue import enqueue
from aieos.jobs.registry import JobClass, JobRegistry

logger = logging.getLogger(__name__)

# Khóa advisory của scheduler (hằng số tùy ý, cố định cho toàn ứng dụng).
SCHEDULER_LOCK_KEY = 0x41454F53_00000001  # "AEOS", 1


@dataclass(frozen=True)
class ScheduleInfo:
    id: uuid.UUID
    kind: str
    job_class: JobClass
    may_write: bool
    slot: datetime


SkipPolicy = Callable[[Session, ScheduleInfo], str | None]


def never_skip(session: Session, schedule: ScheduleInfo) -> str | None:
    return None


def create_schedule(
    session: Session, registry: JobRegistry, kind: str, *, interval: timedelta, first_run_at: datetime
) -> uuid.UUID:
    """Tạo lịch trong transaction hiện hành; `job_class`, `may_write` kế thừa từ registry (ADR-005 Amendment 1)."""
    entry = registry.get(kind)
    if entry.permission is not None:
        raise ValueError(f"{kind}: job cần quyền người khởi tạo không chạy theo lịch hệ thống")
    if interval <= timedelta(0):
        raise ValueError("interval phải dương")
    if first_run_at.tzinfo is None:
        raise ValueError("first_run_at phải có múi giờ")
    schedule = ScheduleRow(
        id=uuid.uuid4(),
        kind=kind,
        job_class=entry.job_class.value,
        interval=interval,
        next_run_at=first_run_at,
        may_write=entry.job_class is not JobClass.ORCHESTRATION,
    )
    session.add(schedule)
    session.flush()
    return schedule.id


def latest_slot(next_run_at: datetime, interval: timedelta, now: datetime) -> tuple[datetime, datetime]:
    """(slot gần nhất ≤ now, next_run_at mới > now) — không chạy bù các slot đã lỡ."""
    missed = (now - next_run_at) // interval
    slot = next_run_at + interval * missed
    return slot, slot + interval


def tick(session: Session, registry: JobRegistry, should_skip: SkipPolicy = never_skip) -> int:
    """Xử lý lịch đến hạn trong transaction hiện hành; trả về số job đã xếp. Trả 0 nếu instance khác đang giữ khóa."""
    locked = session.execute(text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": SCHEDULER_LOCK_KEY}).scalar_one()
    if not locked:
        return 0
    now: datetime = session.execute(text("SELECT now()")).scalar_one()
    due = session.execute(
        text(
            "SELECT id, kind, job_class, interval, next_run_at, may_write FROM jobs.schedule "
            "WHERE enabled AND next_run_at <= now() ORDER BY next_run_at FOR UPDATE"
        )
    ).all()
    enqueued = 0
    for row in due:
        if row.kind not in registry.kinds():
            logger.warning("Lịch có kind chưa đăng ký ở tiến trình này", extra={"schedule_id": str(row.id)})
            continue
        slot, following = latest_slot(row.next_run_at, row.interval, now)
        info = ScheduleInfo(row.id, row.kind, JobClass(row.job_class), row.may_write, slot)
        reason = should_skip(session, info) if row.may_write else None
        if reason is not None:
            session.execute(
                text(
                    "UPDATE jobs.schedule SET next_run_at = :next, last_skipped_at = now(), last_skip_reason = :reason "
                    "WHERE id = :id"
                ),
                {"next": following, "reason": reason, "id": row.id},
            )
            record(
                session,
                AuditEvent(
                    category=Category.AI,
                    actor_type=ActorType.SYSTEM,
                    action="schedule.skipped",
                    outcome=Outcome.BLOCKED,
                    resource_type="jobs.schedule",
                    resource_id=str(row.id),
                    reason=reason,
                    changes={"kind": row.kind, "slot": slot.isoformat()},
                ),
            )
            logger.info("Bỏ qua lịch", extra={"schedule_id": str(row.id), "kind": row.kind, "skip_reason": reason})
            continue
        key = f"{row.id}:{slot.isoformat()}"
        enqueue(session, registry, row.kind, idempotency_key=key, payload={"slot": slot.isoformat()})
        session.execute(
            text("UPDATE jobs.schedule SET next_run_at = :next, last_run_at = now() WHERE id = :id"),
            {"next": following, "id": row.id},
        )
        enqueued += 1
    return enqueued
