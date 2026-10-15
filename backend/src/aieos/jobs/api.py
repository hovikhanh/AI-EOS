"""Interface công khai của `jobs` (ADR-005, Architecture §3 quy tắc 1).

Module khác: đăng ký loại job vào `JobRegistry` (kèm `job_class` cố định), xếp job bằng `enqueue(...)` trong transaction
nghiệp vụ hiện hành, tạo lịch bằng `create_schedule(...)`. Tiến trình worker do composition root (`app`) dựng.
"""

from aieos.jobs.queue import ClaimedJob, JobError, backoff, count_by_status, enqueue, validate_payload
from aieos.jobs.registry import (
    BACKOFF_BASE,
    BACKOFF_CAP,
    BACKOFF_JITTER,
    DEFAULT_LEASE,
    MAINTENANCE_INTERVAL,
    POLL_INTERVAL,
    Handler,
    JobClass,
    JobContext,
    JobKind,
    JobRegistry,
    JobRegistryError,
)
from aieos.jobs.scheduler import ScheduleInfo, SkipPolicy, create_schedule, latest_slot, never_skip
from aieos.jobs.worker import Authorizer, LostLease, PermanentJobError, Worker, deny_all

__all__ = [
    "BACKOFF_BASE",
    "BACKOFF_CAP",
    "BACKOFF_JITTER",
    "DEFAULT_LEASE",
    "MAINTENANCE_INTERVAL",
    "POLL_INTERVAL",
    "Authorizer",
    "ClaimedJob",
    "Handler",
    "JobClass",
    "JobContext",
    "JobError",
    "JobKind",
    "JobRegistry",
    "JobRegistryError",
    "LostLease",
    "PermanentJobError",
    "ScheduleInfo",
    "SkipPolicy",
    "Worker",
    "backoff",
    "count_by_status",
    "create_schedule",
    "deny_all",
    "enqueue",
    "latest_slot",
    "never_skip",
    "validate_payload",
]
