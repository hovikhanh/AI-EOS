"""Endpoint task (T-505): API-WORK-01 `GET /work/tasks`, API-WORK-03 `POST /work/tasks` (`IDEMPOTENT`), API-WORK-04
`PATCH /work/tasks/{id}` (`IF-MATCH`), API-WORK-05 `POST /work/tasks/{id}/complete` · `/reopen` (`IF-MATCH`).

Router mỏng (ADR-002): quyền ở mức route qua `PermissionGuard` (`data.read`, `record.submit`), kiểm tra đối tượng ở
service (`work.service`).
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from aieos.access.api import Actor, PermissionGuard
from aieos.platform.api import (
    IDEMPOTENCY_HEADER,
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    ApiError,
    decode_cursor,
    encode_cursor,
    etag,
    request_fingerprint,
    require_idempotency_key,
    require_if_match,
    run_idempotent,
    transaction,
)
from aieos.work.service import (
    Task,
    create_task,
    find_task_by_key,
    list_tasks,
    set_status,
    update_task,
)


class TaskOut(BaseModel):
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


class TaskPage(BaseModel):
    items: list[TaskOut]
    next_cursor: str | None


class TaskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    owner_user_id: uuid.UUID
    due_date: date
    objective_id: uuid.UUID | None = None


class TaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=500)
    due_date: date | None = None
    owner_user_id: uuid.UUID | None = None


def _out(task: Task, response: Response | None = None) -> TaskOut:
    if response is not None:
        response.headers["ETag"] = etag(task.version)
    return TaskOut(**task.__dict__)


def _after(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if cursor is None:
        return None
    created_at, item_id = decode_cursor(cursor, 2)
    try:
        return datetime.fromisoformat(created_at), uuid.UUID(item_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "cursor", "message": "cursor không hợp lệ"}]) from None


def build_work_router(guard: PermissionGuard) -> APIRouter:
    router = APIRouter(tags=["work"])
    actor_dep = Annotated[Actor, Depends(guard.actor)]
    if_match = Annotated[str | None, Header(alias="If-Match")]

    @router.get("/work/tasks", response_model=TaskPage, **guard.route("data.read"))
    def list_items(
        actor: actor_dep,
        owner_user_id: uuid.UUID | None = None,
        status: Literal["OPEN", "DONE"] | None = None,
        overdue: bool | None = None,
        org_unit_id: uuid.UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
    ) -> TaskPage:
        after = _after(cursor)
        with transaction(guard.factory) as session:
            items = list_tasks(
                session,
                actor,
                limit=limit + 1,
                after=after,
                owner_user_id=owner_user_id,
                status=status,
                overdue=overdue,
                org_unit_id=org_unit_id,
            )
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor((items[-1].created_at.isoformat(), str(items[-1].id)))
        return TaskPage(items=[_out(t) for t in items], next_cursor=next_cursor)

    @router.post("/work/tasks", status_code=201, response_model=TaskOut, **guard.route("record.submit"))
    def create(
        body: TaskIn,
        actor: actor_dep,
        response: Response,
        key: Annotated[str | None, Header(alias=IDEMPOTENCY_HEADER)] = None,
    ) -> TaskOut:
        idempotency_key = require_idempotency_key(key)
        fingerprint = request_fingerprint("POST", "/work/tasks", body.model_dump_json().encode(), str(actor.user_id))
        with transaction(guard.factory) as session:
            task, _ = run_idempotent(
                session,
                fingerprint=fingerprint,
                find=lambda: find_task_by_key(session, actor, idempotency_key),
                create=lambda: create_task(
                    session,
                    actor,
                    title=body.title,
                    owner_user_id=body.owner_user_id,
                    due_date=body.due_date,
                    objective_id=body.objective_id,
                    idempotency_key=idempotency_key,
                    request_hash=fingerprint,
                ),
            )
            return _out(task, response)

    @router.patch("/work/tasks/{task_id}", response_model=TaskOut, **guard.route("data.read"))
    def patch(
        task_id: uuid.UUID, body: TaskPatch, actor: actor_dep, response: Response, version: if_match = None
    ) -> TaskOut:
        expected = require_if_match(version)
        with transaction(guard.factory) as session:
            task = update_task(
                session,
                actor,
                task_id,
                expected_version=expected,
                title=body.title,
                due_date=body.due_date,
                owner_user_id=body.owner_user_id,
            )
            return _out(task, response)

    def status_route(done: bool) -> None:
        name = "complete" if done else "reopen"

        @router.post(f"/work/tasks/{{task_id}}/{name}", response_model=TaskOut, name=name, **guard.route("data.read"))
        def change(task_id: uuid.UUID, actor: actor_dep, response: Response, version: if_match = None) -> TaskOut:
            expected = require_if_match(version)
            with transaction(guard.factory) as session:
                return _out(set_status(session, actor, task_id, done=done, expected_version=expected), response)

    status_route(True)
    status_route(False)
    return router
