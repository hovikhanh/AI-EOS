"""Task (T-505; SRS-WRK-01…04, SRS-WRK-10; API-WORK-01, 03, 04, 05; D-51 Q-33).

- **Trạng thái:** `OPEN`/`DONE` (Q-33 → D-51). "Trễ" là suy ra: `OPEN` và hạn trước hôm nay; "hoàn thành đúng hạn":
  `DONE` và ngày hoàn thành ≤ hạn. Ngày tính theo múi giờ Việt Nam (SRS-GEN-06).
- **Tạo (SRS-WRK-01, 04):** cần `record.submit`; tiêu đề, owner, hạn bắt buộc (hạn khi tạo tay: mặc định `PROPOSED`
  "bắt buộc" của SRS-WRK-01); owner phải trong phạm vi đọc (`data.read`) của người giao; người chỉ có role EMPLOYEE
  chỉ tự giao cho mình (mặc định `PROPOSED` SRS-WRK-04). `IDEMPOTENT` theo `(assigned_by, idempotency_key)`.
  Owner khác người giao → thông báo in-app `TASK_ASSIGNED` (tiêu đề chung, không chép tiêu đề task — SRS-NTF-02).
- **Xem (SRS-WRK-10, SRS-ACC-02):** task thấy được khi owner thuộc phạm vi `data.read` của người xem (T-108: CEO toàn
  công ty, MANAGER đơn vị làm trưởng + cấp dưới — T-201, EMPLOYEE của mình) hoặc người xem là người giao. Ngoài phạm vi
  → `404`.
- **Sửa (API-WORK-04):** owner hoặc người giao sửa tiêu đề, hạn; chỉ người giao đổi owner (owner mới trong phạm vi).
- **Hoàn thành / mở lại (SRS-WRK-03, Q-33):** owner hoặc người giao hoàn thành; chỉ người giao mở lại. Không phải owner
  /người giao nhưng thấy task → `403`.
- Ghi dùng `If-Match` = `version`; audit `BUSINESS` trong cùng transaction.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ColumnElement,
    and_,
    case,
    cast,
    column,
    false,
    func,
    literal,
    or_,
    select,
    table,
    text,
    true,
    update,
)
from sqlalchemy import Date as SqlDate
from sqlalchemy.orm import Session

from aieos.access.api import Actor, Resource, authorize, scope_filter
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.notify.api import notify
from aieos.org.api import subtree, user_unit_path
from aieos.platform.api import ApiError, check_version
from aieos.work.models import TaskRow

TIMEZONE = "Asia/Ho_Chi_Minh"
READ = "data.read"
_ACCOUNT = table("user_account", column("id"), column("employee_id"), schema="identity")
_EMPLOYEE = table("employee", column("id"), column("org_unit_id"), schema="org")


@dataclass(frozen=True)
class Task:
    id: uuid.UUID
    title: str
    owner_user_id: uuid.UUID
    assigned_by: uuid.UUID
    due_date: date | None
    status: str
    completed_at: datetime | None
    completed_by: uuid.UUID | None
    objective_id: uuid.UUID | None
    created_via: str
    created_at: datetime
    version: int
    overdue: bool
    completed_on_time: bool | None


def _today() -> ColumnElement[Any]:
    return cast(func.timezone(TIMEZONE, func.now()), SqlDate)


def _overdue() -> ColumnElement[bool]:
    return and_(TaskRow.status == "OPEN", TaskRow.due_date.is_not(None), TaskRow.due_date < _today())


def _on_time() -> ColumnElement[Any]:
    done_day = cast(func.timezone(TIMEZONE, TaskRow.completed_at), SqlDate)
    return case(
        (and_(TaskRow.status == "DONE", TaskRow.due_date.is_not(None)), done_day <= TaskRow.due_date),
        else_=literal(None, Boolean),
    )


def _select() -> Any:
    # populate_existing: đọc lại sau câu UPDATE trong cùng session, không dùng bản cũ trong identity map.
    return select(TaskRow, _overdue().label("overdue"), _on_time().label("on_time")).execution_options(
        populate_existing=True
    )


def _task(row: Any) -> Task:
    t: TaskRow = row[0]
    return Task(
        t.id,
        t.title,
        t.owner_user_id,
        t.assigned_by,
        t.due_date,
        t.status,
        t.completed_at,
        t.completed_by,
        t.objective_id,
        t.created_via,
        t.created_at,
        t.version,
        bool(row.overdue),
        row.on_time,
    )


def _audit(session: Session, actor: uuid.UUID, action: str, task_id: uuid.UUID, changes: dict[str, str]) -> None:
    record(
        session,
        AuditEvent(
            category=Category.BUSINESS,
            actor_type=ActorType.USER,
            actor_user_id=actor,
            action=action,
            outcome=Outcome.SUCCESS,
            resource_type="work.task",
            resource_id=str(task_id),
            changes=changes,
        ),
    )


def _can_see(session: Session, actor: Actor, owner: uuid.UUID, assigned_by: uuid.UUID) -> bool:
    if actor.user_id in (owner, assigned_by):
        return True
    return authorize(actor, READ, Resource(owner_id=owner, org_units=user_unit_path(session, owner))).allowed


def _check_owner_in_scope(session: Session, actor: Actor, owner: uuid.UUID) -> None:
    if owner == actor.user_id:
        return
    if actor.roles <= {"EMPLOYEE"}:
        raise ApiError("FORBIDDEN", "Chỉ tự giao task cho mình (SRS-WRK-04)")
    resource = Resource(owner_id=owner, org_units=user_unit_path(session, owner))
    if not authorize(actor, READ, resource).allowed:
        raise ApiError("FORBIDDEN", "Người nhận ngoài phạm vi của bạn")


def _owner_exists(session: Session, owner: uuid.UUID) -> None:
    status = session.execute(
        text("SELECT status FROM identity.user_account WHERE id = :i"), {"i": owner}
    ).scalar_one_or_none()
    if status != "ACTIVE":
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "owner_user_id", "message": "Người nhận không hợp lệ"}])


def _load(session: Session, actor: Actor, task_id: uuid.UUID, *, lock: bool = False) -> Task:
    query = _select().where(TaskRow.id == task_id)
    if lock:
        query = query.with_for_update(of=TaskRow)
    row = session.execute(query).one_or_none()
    if row is None:
        raise ApiError("NOT_FOUND")
    task = _task(row)
    if not _can_see(session, actor, task.owner_user_id, task.assigned_by):
        raise ApiError("NOT_FOUND")
    return task


def get_task(session: Session, actor: Actor, task_id: uuid.UUID) -> Task:
    return _load(session, actor, task_id)


def create_task(
    session: Session,
    actor: Actor,
    *,
    title: str,
    owner_user_id: uuid.UUID,
    due_date: date,
    objective_id: uuid.UUID | None,
    idempotency_key: str,
    request_hash: str,
) -> Task:
    title = title.strip()
    if not title:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "title", "message": "Không được rỗng"}])
    _owner_exists(session, owner_user_id)
    _check_owner_in_scope(session, actor, owner_user_id)
    task_id = uuid.uuid4()
    session.add(
        TaskRow(
            id=task_id,
            title=title,
            owner_user_id=owner_user_id,
            assigned_by=actor.user_id,
            due_date=due_date,
            objective_id=objective_id,
            created_via="MANUAL",
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    )
    session.flush()
    _audit(session, actor.user_id, "work.task.create", task_id, {"owner_user_id": str(owner_user_id)})
    if owner_user_id != actor.user_id:
        notify(
            session,
            user_id=owner_user_id,
            type="TASK_ASSIGNED",
            title="Bạn được giao một task mới",
            link=f"/work/tasks/{task_id}",
        )
    return _load(session, actor, task_id)


def find_task_by_key(session: Session, actor: Actor, idempotency_key: str) -> tuple[str, Task] | None:
    row = session.execute(
        select(TaskRow.id, TaskRow.request_hash).where(
            TaskRow.assigned_by == actor.user_id, TaskRow.idempotency_key == idempotency_key
        )
    ).one_or_none()
    if row is None or row.request_hash is None:
        return None
    return row.request_hash, _load(session, actor, row.id)


def update_task(
    session: Session,
    actor: Actor,
    task_id: uuid.UUID,
    *,
    expected_version: int,
    title: str | None = None,
    due_date: date | None = None,
    owner_user_id: uuid.UUID | None = None,
) -> Task:
    task = _load(session, actor, task_id, lock=True)
    if actor.user_id not in (task.owner_user_id, task.assigned_by):
        raise ApiError("FORBIDDEN")
    check_version(task.version, expected_version)
    values: dict[str, Any] = {}
    if title is not None:
        if not title.strip():
            raise ApiError("VALIDATION_ERROR", errors=[{"field": "title", "message": "Không được rỗng"}])
        values["title"] = title.strip()
    if due_date is not None:
        values["due_date"] = due_date
    if owner_user_id is not None and owner_user_id != task.owner_user_id:
        if actor.user_id != task.assigned_by:
            raise ApiError("FORBIDDEN", "Chỉ người giao đổi owner")
        _owner_exists(session, owner_user_id)
        _check_owner_in_scope(session, actor, owner_user_id)
        values["owner_user_id"] = owner_user_id
    if values:
        session.execute(
            update(TaskRow)
            .where(TaskRow.id == task_id)
            .values(**values, version=TaskRow.version + 1, updated_at=func.now())
        )
        _audit(session, actor.user_id, "work.task.update", task_id, {k: str(v) for k, v in values.items()})
        if "owner_user_id" in values and values["owner_user_id"] != actor.user_id:
            notify(
                session,
                user_id=values["owner_user_id"],
                type="TASK_ASSIGNED",
                title="Bạn được giao một task mới",
                link=f"/work/tasks/{task_id}",
            )
    return _load(session, actor, task_id)


def set_status(session: Session, actor: Actor, task_id: uuid.UUID, *, done: bool, expected_version: int) -> Task:
    task = _load(session, actor, task_id, lock=True)
    allowed = (task.owner_user_id, task.assigned_by) if done else (task.assigned_by,)
    if actor.user_id not in allowed:
        raise ApiError("FORBIDDEN", None if done else "Chỉ người giao mở lại task (Q-33)")
    check_version(task.version, expected_version)
    if task.status == ("DONE" if done else "OPEN"):
        raise ApiError("INVALID_STATE")
    session.execute(
        update(TaskRow)
        .where(TaskRow.id == task_id)
        .values(
            status="DONE" if done else "OPEN",
            completed_at=func.now() if done else None,
            completed_by=actor.user_id if done else None,
            version=TaskRow.version + 1,
            updated_at=func.now(),
        )
    )
    _audit(session, actor.user_id, "work.task.complete" if done else "work.task.reopen", task_id, {})
    return _load(session, actor, task_id)


def list_tasks(
    session: Session,
    actor: Actor,
    *,
    limit: int,
    after: tuple[datetime, uuid.UUID] | None = None,
    owner_user_id: uuid.UUID | None = None,
    status: str | None = None,
    overdue: bool | None = None,
    org_unit_id: uuid.UUID | None = None,
) -> list[Task]:
    """API-WORK-01: task trong phạm vi (SQL), mới nhất trước; lọc owner, trạng thái, trễ, đơn vị (gồm cấp dưới)."""
    in_scope = or_(
        scope_filter(actor, READ, owner=TaskRow.owner_user_id.expression, org_unit=_EMPLOYEE.c.org_unit_id),
        TaskRow.assigned_by == actor.user_id,
        TaskRow.owner_user_id == actor.user_id,
    )
    conditions: list[ColumnElement[bool]] = [in_scope]
    if owner_user_id is not None:
        conditions.append(TaskRow.owner_user_id == owner_user_id)
    if status is not None:
        conditions.append(TaskRow.status == status)
    if overdue is not None:
        conditions.append(_overdue() if overdue else ~_overdue())
    if org_unit_id is not None:
        units = subtree(session, [org_unit_id])
        conditions.append(_EMPLOYEE.c.org_unit_id.in_(units) if units else false())
    if after is not None:
        conditions.append(
            or_(TaskRow.created_at < after[0], and_(TaskRow.created_at == after[0], TaskRow.id < after[1]))
        )
    query = (
        _select()
        .join(_ACCOUNT, _ACCOUNT.c.id == TaskRow.owner_user_id)
        .outerjoin(_EMPLOYEE, _EMPLOYEE.c.id == _ACCOUNT.c.employee_id)
        .where(and_(true(), *conditions))
        .order_by(TaskRow.created_at.desc(), TaskRow.id.desc())
        .limit(limit)
    )
    return [_task(row) for row in session.execute(query)]
