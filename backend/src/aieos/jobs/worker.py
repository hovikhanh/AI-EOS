"""Worker chạy job (ADR-005, SRS-JOB-01…03, Architecture §8.4).

Một vòng `run_once`:
1. Claim (transaction riêng, commit ngay).
2. Kiểm tra lại quyền người khởi tạo nếu loại job khai báo `permission` (SRS-JOB-03). Không có authorizer → từ chối
   (mặc định deny). Bị từ chối → `FAILED` mã `PERMISSION_DENIED` + audit `SECURITY`/`DENIED`, handler không chạy.
3. Chạy handler trong một transaction; `SUCCEEDED` được ghi trong chính transaction đó (SRS-JOB-02, K2). Nếu reaper đã
   lấy lại job (lease hết hạn) thì rollback — kết quả không được ghi hai lần.
4. Handler ném `PermanentJobError` → `FAILED`; lỗi khác → `QUEUED` + backoff hoặc `DEAD` (transaction riêng).
Tiến trình chết giữa chừng: job ở `RUNNING`, lease hết hạn, reaper trả về hàng đợi (TC-JOB-02, TC-JOB-03).
Kill switch (`AI_CONTENT` → `CANCELLED`, `BUSINESS_WRITE` qua gateway) gắn ở T-303.
"""

import logging
import os
import socket
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.jobs import queue
from aieos.jobs.queue import ClaimedJob
from aieos.jobs.registry import DEFAULT_LEASE, MAINTENANCE_INTERVAL, POLL_INTERVAL, JobRegistry
from aieos.jobs.scheduler import SkipPolicy, never_skip, tick
from aieos.platform.api import CORRELATION_ID, transaction

logger = logging.getLogger(__name__)

# (session, user_id, permission) → còn quyền hay không. Do composition root cung cấp (access.policy, T-108).
Authorizer = Callable[[Session, uuid.UUID, str], bool]


class PermanentJobError(Exception):
    """Lỗi không thể retry (validation, dữ liệu không còn hợp lệ…) → `FAILED` ngay."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class LostLease(Exception):
    """Worker không còn giữ job (reaper đã lấy lại); kết quả của lần chạy này bị hủy."""


def deny_all(session: Session, user_id: uuid.UUID, permission: str) -> bool:
    return False


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


@dataclass
class _Context:
    job_id: uuid.UUID
    kind: str
    payload: Mapping[str, Any]
    attempt: int
    initiated_by: uuid.UUID | None
    session: Session
    _extend: Callable[[], bool]

    def extend_lease(self) -> None:
        if not self._extend():
            raise LostLease(str(self.job_id))


class Worker:
    def __init__(
        self,
        factory: sessionmaker[Session],
        registry: JobRegistry,
        *,
        authorizer: Authorizer = deny_all,
        should_skip: SkipPolicy = never_skip,
        worker_id: str | None = None,
    ) -> None:
        self.factory = factory
        self.registry = registry
        self.authorizer = authorizer
        self.should_skip = should_skip
        self.worker_id = worker_id or default_worker_id()

    # --- bảo trì ---
    def reap(self) -> dict[uuid.UUID, str]:
        with transaction(self.factory) as session:
            result = queue.reap(session)
        if result:
            logger.warning("Reaper trả job hết lease", extra={"jobs": {str(k): v for k, v in result.items()}})
        return result

    def tick_scheduler(self) -> int:
        with transaction(self.factory) as session:
            return tick(session, self.registry, self.should_skip)

    # --- chạy job ---
    def run_once(self) -> ClaimedJob | None:
        """Nhận và xử lý tối đa một job; trả về job đã nhận (None nếu hàng đợi rỗng)."""
        with transaction(self.factory) as session:
            job = queue.claim(session, self.registry.kinds(), self.worker_id)
        if job is None:
            return None
        token = CORRELATION_ID.set(job.correlation_id)
        try:
            self._execute(job)
        finally:
            CORRELATION_ID.reset(token)
        return job

    def _execute(self, job: ClaimedJob) -> None:
        entry = self.registry.get(job.kind)
        log = {"job_id": str(job.id), "kind": job.kind, "attempt": job.attempts}
        if entry.permission is not None and not self._permitted(job, entry.permission):
            self._deny(job)
            logger.warning("Job bị từ chối: người khởi tạo không còn quyền", extra=log)
            return
        try:
            with transaction(self.factory) as session:
                context = _Context(
                    job.id, job.kind, job.payload, job.attempts, job.initiated_by, session, lambda: self._extend(job)
                )
                entry.handler(context)
                if not queue.mark_succeeded(session, job.id, self.worker_id):
                    raise LostLease(str(job.id))
        except LostLease:
            logger.warning("Worker mất job (lease hết hạn); hủy kết quả lần chạy này", extra=log)
            return
        except PermanentJobError as error:
            self._fail(job, code=error.code, error=error, permanent=True)
            return
        except Exception as error:  # lỗi tạm thời: retry có giới hạn
            self._fail(job, code="TRANSIENT", error=error, permanent=False)
            return
        logger.info("Job xong", extra={**log, "status": "SUCCEEDED"})

    def _permitted(self, job: ClaimedJob, permission: str) -> bool:
        if job.initiated_by is None:  # enqueue đã chặn trường hợp này; phòng thủ: không có người khởi tạo → từ chối
            return False
        try:
            with transaction(self.factory) as session:
                return bool(self.authorizer(session, job.initiated_by, permission))
        except Exception:
            logger.exception("Authorizer lỗi; coi như từ chối", extra={"job_id": str(job.id)})
            return False

    def _deny(self, job: ClaimedJob) -> None:
        with transaction(self.factory) as session:
            status = queue.mark_failed(
                session, job, code="PERMISSION_DENIED", error_type="PermissionDenied", permanent=True
            )
            if status is None:
                return
            record(
                session,
                AuditEvent(
                    category=Category.SECURITY,
                    actor_type=ActorType.SYSTEM,
                    on_behalf_of_user_id=job.initiated_by,
                    action=f"job.{job.kind}",
                    outcome=Outcome.DENIED,
                    resource_type="jobs.job",
                    resource_id=str(job.id),
                    reason="PERMISSION_DENIED",
                ),
            )

    def _fail(self, job: ClaimedJob, *, code: str, error: BaseException, permanent: bool) -> None:
        with transaction(self.factory) as session:
            status = queue.mark_failed(session, job, code=code, error_type=type(error).__name__, permanent=permanent)
        logger.warning(
            "Job lỗi",
            extra={"job_id": str(job.id), "kind": job.kind, "status": status, "error_type": type(error).__name__},
        )

    def _extend(self, job: ClaimedJob) -> bool:
        with transaction(self.factory) as session:
            return queue.extend_lease(session, job.id, self.worker_id, DEFAULT_LEASE)

    # --- vòng lặp tiến trình ---
    def run_forever(self, stop: threading.Event) -> None:
        last_maintenance = float("-inf")
        while not stop.is_set():
            now = time.monotonic()
            if now - last_maintenance >= MAINTENANCE_INTERVAL.total_seconds():
                last_maintenance = now
                try:
                    self.reap()
                    self.tick_scheduler()
                except Exception:
                    logger.exception("Bảo trì queue lỗi")
            try:
                processed = self.run_once()
            except Exception:
                logger.exception("Vòng worker lỗi")
                processed = None
            if processed is None:
                stop.wait(POLL_INTERVAL.total_seconds())
