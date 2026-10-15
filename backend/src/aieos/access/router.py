"""API quản trị quyền (T-109): API-ADM-06 `GET /admin/assignments`, API-ADM-07 `POST /admin/assignments` (`STEP-UP`,
`IDEMPOTENT`), API-ADM-08 `DELETE /admin/assignments/{id}` (`STEP-UP`), API-ADM-09 `GET /admin/roles`.

Router mỏng (ADR-002); quyền qua `PermissionGuard` (T-108). Giao/thu hồi assignment → thu hồi mọi session của tài khoản
đích (SRS-IAM-11) qua `on_change` do composition root truyền (`identity` sở hữu session; `access` không import
`identity`). Lỗi nghiệp vụ được audit `FAILED` trong transaction riêng (SRS-AUD-01).
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from aieos.access.policy import Actor, PermissionGuard
from aieos.access.service import (
    Assignment,
    ScopeType,
    create_assignment,
    find_assignment_by_key,
    get_assignment,
    list_assignments,
    revoke_assignment,
    role_catalog,
)
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record_separately
from aieos.platform.api import (
    IDEMPOTENCY_HEADER,
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    ApiError,
    decode_cursor,
    encode_cursor,
    request_fingerprint,
    require_idempotency_key,
    run_idempotent,
    transaction,
)

SessionsChanged = Callable[[Session, uuid.UUID], object]


class AssignmentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    permission: str
    scope_type: str
    scope_id: str | None
    valid_from: datetime
    valid_to: datetime | None
    granted_by: uuid.UUID
    reason: str
    created_at: datetime
    revoked_at: datetime | None
    revoked_by: uuid.UUID | None


class AssignmentPage(BaseModel):
    items: list[AssignmentOut]
    next_cursor: str | None


class AssignmentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID
    permission: str = Field(min_length=1, max_length=100)
    scope_type: ScopeType
    scope_id: str | None = Field(default=None, min_length=1, max_length=200)
    valid_to: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)


class RoleOut(BaseModel):
    code: str
    base: list[str]
    eligible: list[str]


def _out(item: Assignment) -> AssignmentOut:
    return AssignmentOut(**item.__dict__)


def _after(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if cursor is None:
        return None
    created_at, item_id = decode_cursor(cursor, 2)
    try:
        return datetime.fromisoformat(created_at), uuid.UUID(item_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "cursor", "message": "cursor không hợp lệ"}]) from None


def build_access_admin_router(guard: PermissionGuard, on_change: SessionsChanged) -> APIRouter:
    router = APIRouter(tags=["admin"])
    actor_dep = Annotated[Actor, Depends(guard.actor)]

    def failed(actor: uuid.UUID, action: str, target: uuid.UUID | None, error: ApiError) -> None:
        record_separately(
            guard.factory,
            AuditEvent(
                category=Category.ADMIN,
                actor_type=ActorType.USER,
                actor_user_id=actor,
                action=action,
                outcome=Outcome.FAILED,
                resource_type="identity.user_account" if target else None,
                resource_id=str(target) if target else None,
                reason=error.code,
            ),
        )

    @router.get("/admin/assignments", response_model=AssignmentPage, **guard.route("assignment.manage"))
    def list_items(
        user_id: uuid.UUID | None = None,
        permission: Annotated[str | None, Query(max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
    ) -> AssignmentPage:
        after = _after(cursor)
        with transaction(guard.factory) as session:
            items = list_assignments(session, user_id=user_id, permission=permission, limit=limit + 1, after=after)
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor((items[-1].created_at.isoformat(), str(items[-1].id)))
        return AssignmentPage(items=[_out(i) for i in items], next_cursor=next_cursor)

    @router.post(
        "/admin/assignments",
        status_code=201,
        response_model=AssignmentOut,
        **guard.route("assignment.manage", step_up=True),
    )
    def create(
        body: AssignmentIn,
        actor: actor_dep,
        key: Annotated[str | None, Header(alias=IDEMPOTENCY_HEADER)] = None,
    ) -> AssignmentOut:
        idempotency_key = require_idempotency_key(key)
        fingerprint = request_fingerprint(
            "POST", "/admin/assignments", body.model_dump_json().encode(), str(actor.user_id)
        )
        try:
            with transaction(guard.factory) as session:

                def make() -> Assignment:
                    new_id = create_assignment(
                        session,
                        user_id=body.user_id,
                        permission=body.permission,
                        scope_type=body.scope_type,
                        scope_id=body.scope_id,
                        granted_by=actor.user_id,
                        reason=body.reason,
                        valid_to=body.valid_to,
                        idempotency_key=idempotency_key,
                        request_hash=fingerprint,
                    )
                    on_change(session, body.user_id)
                    created = get_assignment(session, new_id)
                    assert created is not None
                    return created

                result, _ = run_idempotent(
                    session,
                    fingerprint=fingerprint,
                    find=lambda: find_assignment_by_key(session, actor.user_id, idempotency_key),
                    create=make,
                )
                return _out(result)
        except ApiError as error:
            failed(actor.user_id, "access.assignment.create", body.user_id, error)
            raise

    @router.delete(
        "/admin/assignments/{assignment_id}", status_code=204, **guard.route("assignment.manage", step_up=True)
    )
    def revoke(assignment_id: uuid.UUID, actor: actor_dep) -> Response:
        try:
            with transaction(guard.factory) as session:
                current = get_assignment(session, assignment_id)
                if current is None:
                    raise ApiError("NOT_FOUND")
                revoke_assignment(session, assignment_id=assignment_id, revoked_by=actor.user_id)
                on_change(session, current.user_id)
        except ApiError as error:
            if error.code != "NOT_FOUND":
                failed(actor.user_id, "access.assignment.revoke", None, error)
            raise
        return Response(status_code=204)

    @router.get("/admin/roles", response_model=list[RoleOut], **guard.route("user.manage"))
    def roles() -> list[dict[str, Any]]:
        with transaction(guard.factory) as session:
            return role_catalog(session)

    return router
