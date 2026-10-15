"""T-009: job queue trên PostgreSQL (ADR-005 + Amendment 1, SRS-JOB-01…03, SRS-AIC-06, Database_Design §5, D-56).

TC do T-009 làm chủ: TC-JOB-01 (`test_concurrent_claim_single_winner`), TC-JOB-02 (`test_reaper_requeues_then_dead`),
TC-JOB-03 (`test_crash_before_commit_yields_single_result`, `test_stale_worker_cannot_commit_after_reap`), TC-JOB-04
(`test_enqueue_rolled_back_with_business_change`), TC-JOB-06 (`test_orchestration_handlers_static_scan` + ca vi phạm).
TC-JOB-05 (chủ T-203, D-56): chỉ bằng chứng thành phần — authorizer giả lập (`test_permission_*`).
"""

import ast
import importlib.util
import inspect
import os
import random
import re
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from aieos.app.worker import build_registry
from aieos.jobs.api import (
    BACKOFF_CAP,
    ClaimedJob,
    JobClass,
    JobContext,
    JobError,
    JobRegistry,
    JobRegistryError,
    LostLease,
    PermanentJobError,
    Worker,
    backoff,
    count_by_status,
    create_schedule,
    enqueue,
    latest_slot,
    validate_payload,
)
from aieos.platform.api import create_db_engine, make_session_factory, transaction
from tests.conftest import ProvisionedDatabase, migrate_to_head

# Module cấm với handler ORCHESTRATION (ADR-005 Amendment 1): gateway, provider AI, module/bảng nghiệp vụ.
FORBIDDEN_FOR_ORCHESTRATION = (
    "aieos.gateway",
    "aieos.providers",
    "aieos.goals",
    "aieos.work",
    "aieos.org",
    "aieos.knowledge",
    "aieos.finance",
    "aieos.capture",
    "aieos.sales",
    "aieos.insights",
)
BUSINESS_TABLE = re.compile(r"\b(goals|work|org|knowledge|finance|capture|sales|insights)\.[a-z_]+\b")


def orchestration_violations(registry: JobRegistry) -> list[str]:
    """Quét tĩnh module chứa handler ORCHESTRATION: import bị cấm hoặc chuỗi SQL nhắc bảng nghiệp vụ.

    Giới hạn: không bắt được import động hay SQL dựng từ biến (ghi ở Implementation_Plan §19).
    """
    found: list[str] = []
    for entry in registry:
        if entry.job_class is not JobClass.ORCHESTRATION:
            continue
        source_file = inspect.getsourcefile(entry.handler)
        assert source_file, entry.kind
        tree = ast.parse(Path(source_file).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
            for name in names:
                if any(name == f or name.startswith(f + ".") for f in FORBIDDEN_FOR_ORCHESTRATION):
                    found.append(f"{entry.kind}: import {name}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and BUSINESS_TABLE.search(node.value):
                found.append(f"{entry.kind}: SQL bảng nghiệp vụ {BUSINESS_TABLE.search(node.value).group(0)}")  # type: ignore[union-attr]
    return found


def noop(ctx: JobContext) -> None:
    return None


# ---------- Không cần CSDL ----------


def test_registry_requires_job_class_and_max_attempts() -> None:
    registry = JobRegistry()
    registry.register("test.ok", JobClass.ORCHESTRATION, noop, max_attempts=1)
    with pytest.raises(JobRegistryError):
        registry.register("test.ok", JobClass.ORCHESTRATION, noop, max_attempts=1)
    with pytest.raises(JobRegistryError):
        registry.register("test.no_attempts", JobClass.AI_CONTENT, noop, max_attempts=0)
    with pytest.raises(JobRegistryError):
        registry.register("test.bad_class", "ORCHESTRATION", noop, max_attempts=1)  # type: ignore[arg-type]
    with pytest.raises(JobRegistryError):
        registry.get("test.unknown")


def test_app_registry_every_kind_has_job_class() -> None:
    """TC-JOB-06 (phần registry): mọi `kind` của ứng dụng có `job_class` hợp lệ."""
    registry = build_registry()
    assert all(isinstance(entry.job_class, JobClass) for entry in registry)


def test_orchestration_handlers_static_scan() -> None:
    """TC-JOB-06: handler ORCHESTRATION của ứng dụng không import gateway/provider/module nghiệp vụ."""
    assert orchestration_violations(build_registry()) == []


def test_orchestration_scan_detects_violation(tmp_path: Path) -> None:
    """TC-JOB-06: thêm vi phạm làm test đỏ (import gateway, provider, ghi bảng nghiệp vụ)."""
    bad = tmp_path / "bad_handlers.py"
    bad.write_text(
        "SQL = 'UPDATE work.task SET status = 1'\n"
        "def handler(ctx):\n"
        "    import aieos.gateway.api\n"
        "    from aieos.providers.api import LLMProvider\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location("bad_handlers", bad)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry = JobRegistry()
    registry.register("test.bad", JobClass.ORCHESTRATION, module.handler, max_attempts=1)
    registry.register("test.ai", JobClass.AI_CONTENT, module.handler, max_attempts=1)  # không quét lớp khác
    violations = orchestration_violations(registry)
    assert sorted(violations) == [
        "test.bad: SQL bảng nghiệp vụ work.task",
        "test.bad: import aieos.gateway.api",
        "test.bad: import aieos.providers.api",
        "test.bad: import aieos.providers.api.LLMProvider",
    ]


def test_payload_only_flat_references() -> None:
    ident = uuid.uuid4()
    assert validate_payload({"document_id": ident, "page": 3, "force": False, "x": None}) == {
        "document_id": str(ident),
        "page": 3,
        "force": False,
        "x": None,
    }
    for bad in ({"nested": {"a": 1}}, {"list": [1]}, {"amount": 1.5}, {"text": "x" * 201}, {"": 1}):
        with pytest.raises(JobError):
            validate_payload(bad)


def test_backoff_formula() -> None:
    rng = random.Random(1)
    first = backoff(1, rng)
    assert timedelta(seconds=30) <= first <= timedelta(seconds=33)
    assert timedelta(seconds=60) <= backoff(2, rng) <= timedelta(seconds=66)
    assert BACKOFF_CAP <= backoff(50, rng) <= BACKOFF_CAP * 1.1


def test_latest_slot_skips_missed_runs() -> None:
    start = datetime(2026, 10, 15, 7, tzinfo=UTC)
    slot, following = latest_slot(start, timedelta(hours=1), start + timedelta(hours=3, minutes=30))
    assert slot == start + timedelta(hours=3)
    assert following == start + timedelta(hours=4)
    assert latest_slot(start, timedelta(days=1), start) == (start, start + timedelta(days=1))


# ---------- PostgreSQL thật ----------


class SimulatedCrash(BaseException):
    """Mô phỏng tiến trình chết: không phải Exception nên worker không bắt."""


@pytest.fixture
def db(database: ProvisionedDatabase) -> Iterator[tuple[Engine, sessionmaker[Session], ProvisionedDatabase]]:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE identity.probe_result (job_id uuid NOT NULL, note text)")
    owner.dispose()
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    yield engine, make_session_factory(engine), database
    engine.dispose()


def write_result(ctx: JobContext) -> None:
    ctx.session.execute(text("INSERT INTO identity.probe_result (job_id) VALUES (:j)"), {"j": ctx.job_id})


def registry_with(
    handler: Callable[[JobContext], None],
    *,
    job_class: JobClass = JobClass.BUSINESS_WRITE,
    max_attempts: int = 3,
    permission: str | None = None,
) -> JobRegistry:
    registry = JobRegistry()
    registry.register("test.job", job_class, handler, max_attempts=max_attempts, permission=permission)
    return registry


def add_job(factory: sessionmaker[Session], registry: JobRegistry, key: str = "k1", **kwargs: object) -> uuid.UUID:
    with transaction(factory) as session:
        return enqueue(session, registry, "test.job", idempotency_key=key, **kwargs)  # type: ignore[arg-type]


def job_row(engine: Engine, job_id: uuid.UUID) -> dict[str, object]:
    with engine.connect() as conn:
        return dict(conn.execute(text("SELECT * FROM jobs.job WHERE id = :i"), {"i": job_id}).mappings().one())


def results(engine: Engine) -> list[uuid.UUID]:
    with engine.connect() as conn:
        return list(conn.execute(text("SELECT job_id FROM identity.probe_result")).scalars())


def expire_lease(engine: Engine, job_id: uuid.UUID) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE jobs.job SET lease_expires_at = now() - interval '1 second' WHERE id = :i"), {"i": job_id}
        )


def claim_as(factory: sessionmaker[Session], registry: JobRegistry, worker_id: str) -> ClaimedJob | None:
    from aieos.jobs.queue import claim

    with transaction(factory) as session:
        return claim(session, registry.kinds(), worker_id)


@pytest.mark.db
def test_concurrent_claim_single_winner(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    """TC-JOB-01: hai worker claim đồng thời một job → đúng một worker nhận (lặp 20 lần)."""
    engine, factory, _ = db
    registry = registry_with(noop)
    for i in range(20):
        add_job(factory, registry, key=f"k{i}")
        barrier = threading.Barrier(2)
        claimed: list[ClaimedJob | None] = [None, None]

        def worker(slot: int, barrier: threading.Barrier, claimed: list[ClaimedJob | None]) -> None:
            barrier.wait()
            claimed[slot] = claim_as(factory, registry, f"w{slot}")

        threads = [threading.Thread(target=worker, args=(n, barrier, claimed)) for n in (0, 1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        winners = [c for c in claimed if c is not None]
        assert len(winners) == 1, i
        assert winners[0].attempts == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM jobs.job WHERE status = 'RUNNING'")).scalar_one() == 20


@pytest.mark.db
def test_two_jobs_two_workers(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    _, factory, _ = db
    registry = registry_with(noop)
    add_job(factory, registry, key="a")
    add_job(factory, registry, key="b")
    first, second = claim_as(factory, registry, "w1"), claim_as(factory, registry, "w2")
    assert first and second and first.id != second.id
    assert claim_as(factory, registry, "w3") is None


@pytest.mark.db
def test_reaper_requeues_then_dead(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    """TC-JOB-02: worker dừng, lease hết hạn → reaper trả QUEUED, attempts tăng; hết lượt → DEAD."""
    engine, factory, _ = db
    registry = registry_with(noop, max_attempts=2)
    job_id = add_job(factory, registry)
    worker = Worker(factory, registry, worker_id="w")
    assert claim_as(factory, registry, "dead-worker")
    assert worker.reap() == {}  # lease còn hạn
    expire_lease(engine, job_id)
    assert worker.reap() == {job_id: "QUEUED"}
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"], row["locked_by"], row["last_error_code"]) == (
        "QUEUED",
        1,
        None,
        "LEASE_EXPIRED",
    )
    assert claim_as(factory, registry, "dead-worker-2")
    expire_lease(engine, job_id)
    assert worker.reap() == {job_id: "DEAD"}
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"]) == ("DEAD", 2) and row["finished_at"] is not None
    assert claim_as(factory, registry, "w") is None


@pytest.mark.db
def test_crash_before_commit_yields_single_result(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """TC-JOB-03: process chết sau xử lý, trước commit; job chạy lại → một kết quả duy nhất."""
    engine, factory, _ = db

    def crash_after_write(ctx: JobContext) -> None:
        write_result(ctx)
        raise SimulatedCrash

    job_id = add_job(factory, registry_with(crash_after_write))
    with pytest.raises(SimulatedCrash):
        Worker(factory, registry_with(crash_after_write), worker_id="crashing").run_once()
    assert results(engine) == []
    assert job_row(engine, job_id)["status"] == "RUNNING"
    expire_lease(engine, job_id)
    survivor = Worker(factory, registry_with(write_result), worker_id="survivor")
    assert survivor.reap() == {job_id: "QUEUED"}
    assert survivor.run_once() is not None
    assert results(engine) == [job_id]
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"]) == ("SUCCEEDED", 2)


@pytest.mark.db
def test_stale_worker_cannot_commit_after_reap(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    """TC-JOB-03: worker cũ hoàn tất muộn sau khi reaper đã giao job cho worker khác → kết quả bị hủy."""
    from aieos.jobs.queue import mark_succeeded

    engine, factory, _ = db
    registry = registry_with(write_result)
    job_id = add_job(factory, registry)
    stale = claim_as(factory, registry, "stale")
    assert stale
    expire_lease(engine, job_id)
    Worker(factory, registry, worker_id="fresh").reap()
    assert Worker(factory, registry, worker_id="fresh").run_once() is not None
    session = factory()
    try:
        session.execute(text("INSERT INTO identity.probe_result (job_id) VALUES (:j)"), {"j": job_id})
        assert mark_succeeded(session, job_id, "stale") is False
        session.rollback()
    finally:
        session.close()
    assert results(engine) == [job_id]


@pytest.mark.db
def test_enqueue_rolled_back_with_business_change(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """TC-JOB-04: thay đổi nghiệp vụ rollback → job tương ứng không tồn tại (outbox)."""
    engine, factory, _ = db
    registry = registry_with(noop)
    with pytest.raises(RuntimeError):
        with transaction(factory) as session:
            session.execute(text("INSERT INTO identity.probe_result (job_id, note) VALUES (gen_random_uuid(), 'x')"))
            enqueue(session, registry, "test.job", idempotency_key="outbox")
            raise RuntimeError("rollback nghiệp vụ")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM jobs.job")).scalar_one() == 0
    assert results(engine) == []
    add_job(factory, registry, key="outbox")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM jobs.job")).scalar_one() == 1


@pytest.mark.db
def test_idempotency_key_dedupes(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db
    registry = registry_with(noop)
    registry.register("test.other", JobClass.ORCHESTRATION, noop, max_attempts=1)
    first = add_job(factory, registry, key="same")
    assert add_job(factory, registry, key="same") == first
    with pytest.raises(JobError):
        with transaction(factory) as session:
            enqueue(session, registry, "test.other", idempotency_key="same")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM jobs.job")).scalar_one() == 1


@pytest.mark.db
def test_job_class_comes_from_registry(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db
    registry = registry_with(noop, job_class=JobClass.AI_CONTENT, max_attempts=4)
    job_id = add_job(factory, registry)
    row = job_row(engine, job_id)
    assert (row["job_class"], row["max_attempts"], row["status"], row["attempts"]) == ("AI_CONTENT", 4, "QUEUED", 0)
    with pytest.raises(JobRegistryError):
        with transaction(factory) as session:
            enqueue(session, registry, "test.unregistered", idempotency_key="x")


@pytest.mark.db
def test_transient_error_backoff_then_dead(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db

    def boom(ctx: JobContext) -> None:
        write_result(ctx)
        raise RuntimeError("thông điệp chứa bí mật sk-123 không được lưu")

    registry = registry_with(boom, max_attempts=2)
    job_id = add_job(factory, registry)
    worker = Worker(factory, registry, worker_id="w")
    worker.run_once()
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"], row["last_error_code"], row["last_error"]) == (
        "QUEUED",
        1,
        "TRANSIENT",
        "RuntimeError",
    )
    with engine.connect() as conn:
        delay = conn.execute(
            text("SELECT extract(epoch FROM run_after - now()) FROM jobs.job WHERE id = :i"), {"i": job_id}
        ).scalar_one()
    assert 25 <= float(delay) <= 34
    assert worker.run_once() is None  # chưa tới run_after
    with engine.begin() as conn:
        conn.execute(text("UPDATE jobs.job SET run_after = now() WHERE id = :i"), {"i": job_id})
    worker.run_once()
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"]) == ("DEAD", 2) and row["finished_at"] is not None
    assert results(engine) == []  # kết quả của lần lỗi bị rollback
    with engine.connect() as conn:
        assert "sk-123" not in str(conn.execute(text("SELECT row_to_json(j) FROM jobs.job j")).scalar_one())


@pytest.mark.db
def test_permanent_error_fails_without_retry(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db

    def invalid(ctx: JobContext) -> None:
        raise PermanentJobError("INVALID_REFERENCE")

    job_id = add_job(factory, registry_with(invalid, max_attempts=5))
    Worker(factory, registry_with(invalid, max_attempts=5), worker_id="w").run_once()
    row = job_row(engine, job_id)
    assert (row["status"], row["attempts"], row["last_error_code"]) == ("FAILED", 1, "INVALID_REFERENCE")


@pytest.mark.db
def test_success_commits_result_and_status_together(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """SRS-JOB-02: kết quả và SUCCEEDED trong cùng transaction."""
    engine, factory, _ = db
    registry = registry_with(write_result)
    job_id = add_job(factory, registry)
    Worker(factory, registry, worker_id="w").run_once()
    row = job_row(engine, job_id)
    assert row["status"] == "SUCCEEDED" and row["lease_expires_at"] is None and row["finished_at"] is not None
    assert results(engine) == [job_id]
    assert count_by_status(factory()) == {"SUCCEEDED": 1}


@pytest.mark.db
def test_extend_lease_and_lost_lease(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db
    seen: list[object] = []

    def long_running(ctx: JobContext) -> None:
        with engine.connect() as conn:
            before = conn.execute(text("SELECT lease_expires_at FROM jobs.job WHERE id = :i"), {"i": ctx.job_id})
            seen.append(before.scalar_one())
        ctx.extend_lease()
        with engine.connect() as conn:
            after = conn.execute(text("SELECT lease_expires_at FROM jobs.job WHERE id = :i"), {"i": ctx.job_id})
            seen.append(after.scalar_one())
        write_result(ctx)

    registry = registry_with(long_running)
    job_id = add_job(factory, registry)
    Worker(factory, registry, worker_id="w").run_once()
    assert job_row(engine, job_id)["status"] == "SUCCEEDED"
    assert len(seen) == 2 and seen[1] > seen[0]  # type: ignore[operator]

    def lose_then_extend(ctx: JobContext) -> None:
        write_result(ctx)
        expire_lease(engine, ctx.job_id)
        Worker(factory, registry_lost, worker_id="reaper").reap()
        ctx.extend_lease()

    registry_lost = registry_with(lose_then_extend)
    lost_id = add_job(factory, registry_lost, key="k2")
    Worker(factory, registry_lost, worker_id="w2").run_once()
    assert job_row(engine, lost_id)["status"] == "QUEUED"
    assert results(engine) == [job_id]  # kết quả của lần mất lease bị rollback
    assert issubclass(LostLease, Exception)


@pytest.mark.db
def test_permission_denied_fails_without_running(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """Bằng chứng thành phần TC-JOB-05 (chủ T-203): quyền bị thu hồi → FAILED, không ghi, có audit DENIED."""
    engine, factory, _ = db
    user = uuid.uuid4()
    granted = {"value": True}

    def authorizer(session: Session, user_id: uuid.UUID, permission: str) -> bool:
        assert (user_id, permission) == (user, "test.run")
        return granted["value"]

    registry = registry_with(write_result, permission="test.run")
    ok_id = add_job(factory, registry, key="ok", initiated_by=user)
    Worker(factory, registry, authorizer=authorizer, worker_id="w").run_once()
    assert job_row(engine, ok_id)["status"] == "SUCCEEDED"

    granted["value"] = False  # quyền bị thu hồi trước khi job chạy
    denied_id = add_job(factory, registry, key="denied", initiated_by=user)
    Worker(factory, registry, authorizer=authorizer, worker_id="w").run_once()
    row = job_row(engine, denied_id)
    assert (row["status"], row["last_error_code"]) == ("FAILED", "PERMISSION_DENIED")
    assert results(engine) == [ok_id]
    with engine.connect() as conn:
        audit = conn.execute(
            text("SELECT category, actor_type, outcome, on_behalf_of_user_id, resource_id FROM audit.event")
        ).one()
    assert tuple(audit) == ("SECURITY", "SYSTEM", "DENIED", user, str(denied_id))


@pytest.mark.db
def test_permission_default_deny_and_authorizer_error(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    engine, factory, _ = db
    registry = registry_with(write_result, permission="test.run")
    no_authorizer = add_job(factory, registry, key="a", initiated_by=uuid.uuid4())
    Worker(factory, registry, worker_id="w").run_once()  # authorizer mặc định: từ chối

    def broken(session: Session, user_id: uuid.UUID, permission: str) -> bool:
        raise RuntimeError("policy lỗi")

    broken_id = add_job(factory, registry, key="b", initiated_by=uuid.uuid4())
    Worker(factory, registry, authorizer=broken, worker_id="w").run_once()
    for job_id in (no_authorizer, broken_id):
        assert job_row(engine, job_id)["last_error_code"] == "PERMISSION_DENIED"
    assert results(engine) == []
    with pytest.raises(JobError):
        add_job(factory, registry, key="c")  # cần quyền mà không có người khởi tạo


@pytest.mark.db
@pytest.mark.parametrize(
    "assignment",
    [
        "job_class = 'OTHER'",
        "status = 'PAUSED'",
        "max_attempts = 0",
        "attempts = 9",
        "status = 'RUNNING'",
        "idempotency_key = ''",
    ],
)
def test_job_check_constraints(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase], assignment: str) -> None:
    engine, factory, _ = db
    job_id = add_job(factory, registry_with(noop))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(f"UPDATE jobs.job SET {assignment} WHERE id = :i"), {"i": job_id})


@pytest.mark.db
def test_app_cannot_delete_jobs(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    _, _, database = db
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        privileges = {
            (table, privilege)
            for table in ("jobs.job", "jobs.schedule")
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
            if conn.execute(
                text("SELECT has_table_privilege('aieos_app', :t, :p)"), {"t": table, "p": privilege}
            ).scalar_one()
        }
    owner.dispose()
    assert privileges == {(t, p) for t in ("jobs.job", "jobs.schedule") for p in ("SELECT", "INSERT", "UPDATE")}


# ---------- Scheduler ----------


def scheduled_registry() -> JobRegistry:
    registry = JobRegistry()
    registry.register("test.reminder", JobClass.ORCHESTRATION, noop, max_attempts=1)
    registry.register("test.briefing", JobClass.AI_CONTENT, noop, max_attempts=1)
    return registry


def db_now(engine: Engine) -> datetime:
    with engine.connect() as conn:
        value: datetime = conn.execute(text("SELECT now()")).scalar_one()
    return value


def schedule_row(engine: Engine, schedule_id: uuid.UUID) -> dict[str, object]:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM jobs.schedule WHERE id = :i"), {"i": schedule_id}).mappings().one()
    return dict(row)


def jobs_of(engine: Engine, kind: str) -> list[dict[str, object]]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM jobs.job WHERE kind = :k"), {"k": kind}).mappings().all()
    return [dict(r) for r in rows]


@pytest.mark.db
def test_schedule_no_backfill_single_job_for_latest_slot(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """D-56: lỡ nhiều slot → chỉ một job cho slot gần nhất; next_run_at nhảy sang tương lai."""
    engine, factory, _ = db
    registry = scheduled_registry()
    first = db_now(engine) - timedelta(hours=3, minutes=30)
    with transaction(factory) as session:
        schedule_id = create_schedule(
            session, registry, "test.reminder", interval=timedelta(hours=1), first_run_at=first
        )
    worker = Worker(factory, registry, worker_id="w")
    assert worker.tick_scheduler() == 1
    assert worker.tick_scheduler() == 0
    jobs = jobs_of(engine, "test.reminder")
    expected_slot = first + timedelta(hours=3)
    assert len(jobs) == 1
    assert jobs[0]["idempotency_key"] == f"{schedule_id}:{expected_slot.isoformat()}"
    assert jobs[0]["initiated_by"] is None
    row = schedule_row(engine, schedule_id)
    assert row["next_run_at"] == first + timedelta(hours=4) and row["may_write"] is False
    assert row["last_run_at"] is not None


@pytest.mark.db
def test_scheduler_single_instance_advisory_lock(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    from aieos.jobs.scheduler import SCHEDULER_LOCK_KEY

    engine, factory, _ = db
    registry = scheduled_registry()
    with transaction(factory) as session:
        create_schedule(session, registry, "test.reminder", interval=timedelta(minutes=5), first_run_at=db_now(engine))
    holder = factory()
    try:
        assert holder.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": SCHEDULER_LOCK_KEY}).scalar_one()
        assert Worker(factory, registry, worker_id="other").tick_scheduler() == 0
    finally:
        holder.rollback()
        holder.close()
    assert Worker(factory, registry, worker_id="other").tick_scheduler() == 1


@pytest.mark.db
def test_may_write_schedule_skipped_logged_audited_no_catch_up(
    db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase],
) -> None:
    """Bằng chứng thành phần TC-KS-07 (chủ T-303): lịch may_write bị bỏ qua, audit, nhảy chu kỳ, không chạy bù."""
    engine, factory, _ = db
    registry = scheduled_registry()
    now = db_now(engine)
    with transaction(factory) as session:
        briefing = create_schedule(session, registry, "test.briefing", interval=timedelta(days=1), first_run_at=now)
        reminder = create_schedule(session, registry, "test.reminder", interval=timedelta(days=1), first_run_at=now)

    def kill_switch_on(session: Session, schedule: object) -> str | None:
        return "KILL_SWITCH"

    assert Worker(factory, registry, should_skip=kill_switch_on, worker_id="w").tick_scheduler() == 1
    assert jobs_of(engine, "test.briefing") == []
    assert len(jobs_of(engine, "test.reminder")) == 1  # ORCHESTRATION không bị hỏi should_skip
    row = schedule_row(engine, briefing)
    assert row["may_write"] is True and row["last_skip_reason"] == "KILL_SWITCH"
    assert row["next_run_at"] == now + timedelta(days=1)
    with engine.connect() as conn:
        audit = conn.execute(text("SELECT action, outcome, resource_id, category FROM audit.event")).one()
    assert tuple(audit) == ("schedule.skipped", "BLOCKED", str(briefing), "AI")
    assert Worker(factory, registry, worker_id="w").tick_scheduler() == 0  # tắt kill switch: không chạy bù
    assert schedule_row(engine, reminder)["next_run_at"] == now + timedelta(days=1)


@pytest.mark.db
def test_schedule_constraints(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase]) -> None:
    engine, factory, _ = db
    registry = scheduled_registry()
    registry.register("test.user_job", JobClass.BUSINESS_WRITE, noop, max_attempts=1, permission="x")
    with pytest.raises(ValueError):
        with transaction(factory) as session:
            create_schedule(
                session, registry, "test.user_job", interval=timedelta(hours=1), first_run_at=db_now(engine)
            )
    with transaction(factory) as session:
        schedule_id = create_schedule(
            session, registry, "test.reminder", interval=timedelta(hours=1), first_run_at=db_now(engine)
        )
    for assignment in ("interval = interval '1 month'", "interval = interval '0'", "may_write = true"):
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(text(f"UPDATE jobs.schedule SET {assignment} WHERE id = :i"), {"i": schedule_id})


# ---------- Tiến trình worker ----------


@pytest.mark.db
def test_worker_command_once(db: tuple[Engine, sessionmaker[Session], ProvisionedDatabase], tmp_path: Path) -> None:
    _, _, database = db
    env = {k: v for k, v in os.environ.items() if not k.startswith("AIEOS_")}
    command = [sys.executable, "-m", "aieos.app", "worker", "--once"]
    missing = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert missing.returncode == 2
    url = database.urls["aieos_app"]
    env.update(
        {
            "AIEOS_DATABASE_URL": url.render_as_string(hide_password=False),
            "AIEOS_STORAGE_PATH": str(tmp_path),
            "AIEOS_SCANNER_HOST": "scanner:3310",
        }
    )
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-500:].replace(str(url.password), "***")
    assert str(url.password) not in result.stdout + result.stderr
