"""Policy phân quyền tập trung (T-108; SRS-ACC-01, 02, 03, 09; ADR-007; Architecture §6).

- **Quyền hiệu lực (SRS-ACC-01):** quyền nền (`BASE`) của các role ∪ assignment còn hiệu lực (`valid_from ≤ now <
  valid_to`, chưa thu hồi). `load_actor` đọc một lần cho mỗi request; `authorize(actor, permission, resource)` **mặc
  định từ chối** (không có quyền, ngoài phạm vi).
- **Phạm vi (SRS-ACC-03, Architecture §6 cột "Phạm vi" của `data.read`):** quyền nền áp phạm vi dữ liệu theo role — CEO
  toàn công ty; CFO dữ liệu tài chính toàn công ty + của mình; MANAGER đơn vị mình quản lý và cấp dưới; EMPLOYEE của
  mình. Assignment áp phạm vi riêng: `COMPANY`, `ORG_UNIT` (đơn vị và cấp dưới), `DOCUMENT_TYPE`, `REVIEW_QUEUE`.
  Tài nguyên quản trị (`Resource(business=False)`, vd. tài khoản) không thuộc phạm vi dữ liệu nghiệp vụ — chỉ xét
  permission.
- **Chưa làm (`[CẦN XÁC NHẬN]`, Implementation_Plan §27):** "team" của EMPLOYEE (SRS-ACC-04 PROPOSED, mục 0
  OPEN_DECISIONS) và "mục tiêu cha" (cần module `goals`) → hiện từ chối (mặc định deny).
- **Cây tổ chức:** `access` không đọc bảng `org.*` (T-201, phụ thuộc T-108). `OrgScope` cung cấp đơn vị do người dùng
  quản lý và cây con; trước khi có T-201 dùng `NO_ORG` (không quản lý đơn vị nào; cây con = chính đơn vị) — MANAGER
  chỉ thấy dữ liệu của mình cho tới khi T-201 cài `OrgScope`.
- **Đối tượng (SRS-ACC-02):** `require(..., hide=True)` → `404 NOT_FOUND` khi không được biết đối tượng tồn tại;
  `hide=False` → `403 FORBIDDEN`. Danh sách lọc trong SQL bằng `scope_filter` (không lọc sau khi đọc).
- **Route (SRS-ACC-09):** `PermissionGuard.route(permission)` vừa khai báo quyền cho route (`platform.declare`) vừa
  kiểm tra; từ chối → `403 FORBIDDEN` + audit `SECURITY` `DENIED` (ADR-007).
"""

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from fastapi import Depends, Request
from sqlalchemy import ColumnElement, false, or_, text, true
from sqlalchemy.orm import Session, sessionmaker

from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record_separately
from aieos.platform.api import ApiError, declare, transaction

FINANCE = "finance"
_ACTOR_STATE = "aieos_actor"


class Source(StrEnum):
    BASE = "BASE"
    ASSIGNMENT = "ASSIGNMENT"


@dataclass(frozen=True)
class Grant:
    source: Source
    scope_type: str | None = None  # chỉ với ASSIGNMENT
    scope_id: str | None = None
    units: frozenset[uuid.UUID] = frozenset()  # ORG_UNIT: đơn vị và cấp dưới


@dataclass(frozen=True)
class Actor:
    user_id: uuid.UUID
    roles: frozenset[str]
    grants: dict[str, tuple[Grant, ...]]
    managed_units: frozenset[uuid.UUID] = frozenset()  # đơn vị MANAGER quản lý và cấp dưới

    def has(self, permission: str) -> bool:
        return bool(self.grants.get(permission))


@dataclass(frozen=True)
class Resource:
    """Thuộc tính đối tượng dùng để xét phạm vi. `org_units` = đơn vị của đối tượng và mọi đơn vị cấp trên."""

    owner_id: uuid.UUID | None = None
    org_units: frozenset[uuid.UUID] = frozenset()
    domain: str | None = None
    document_type: str | None = None
    review_queue: str | None = None
    business: bool = True


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str = ""


ALLOW = Decision(True)


class OrgScope(Protocol):
    def managed_units(self, session: Session, user_id: uuid.UUID) -> frozenset[uuid.UUID]: ...

    def subtree(self, session: Session, unit_ids: Iterable[uuid.UUID]) -> frozenset[uuid.UUID]: ...


@dataclass(frozen=True)
class _NoOrg:
    """Chưa có `org.*` (T-201): không ai quản lý đơn vị; cây con chỉ gồm chính đơn vị."""

    def managed_units(self, session: Session, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
        return frozenset()

    def subtree(self, session: Session, unit_ids: Iterable[uuid.UUID]) -> frozenset[uuid.UUID]:
        return frozenset(unit_ids)


NO_ORG: OrgScope = _NoOrg()


def load_actor(session: Session, user_id: uuid.UUID, org: OrgScope = NO_ORG) -> Actor:
    roles = frozenset(
        session.scalars(text("SELECT role_code FROM access.user_role WHERE user_id = :u"), {"u": user_id})
    )
    grants: dict[str, list[Grant]] = {}
    base = session.execute(
        text(
            "SELECT DISTINCT rp.permission_code FROM access.user_role ur JOIN access.role_permission rp "
            "ON rp.role_code = ur.role_code AND rp.kind = 'BASE' WHERE ur.user_id = :u"
        ),
        {"u": user_id},
    )
    for (permission,) in base:
        grants.setdefault(permission, []).append(Grant(Source.BASE))
    assignments = session.execute(
        text(
            "SELECT permission_code, scope_type, scope_id FROM access.assignment WHERE user_id = :u "
            "AND revoked_at IS NULL AND valid_from <= now() AND (valid_to IS NULL OR valid_to > now())"
        ),
        {"u": user_id},
    )
    for permission, scope_type, scope_id in assignments:
        units: frozenset[uuid.UUID] = frozenset()
        if scope_type == "ORG_UNIT" and scope_id:
            units = org.subtree(session, [uuid.UUID(scope_id)])
        grants.setdefault(permission, []).append(Grant(Source.ASSIGNMENT, scope_type, scope_id, units))
    managed = org.managed_units(session, user_id) if "MANAGER" in roles else frozenset()
    return Actor(user_id, roles, {k: tuple(v) for k, v in grants.items()}, managed)


def _in_data_scope(actor: Actor, resource: Resource) -> bool:
    """Phạm vi theo role của quyền nền (Architecture §6, `data.read`). Team/mục tiêu cha: chưa làm → False."""
    if "CEO" in actor.roles:
        return True
    if "CFO" in actor.roles and resource.domain == FINANCE:
        return True
    if resource.owner_id is not None and resource.owner_id == actor.user_id:
        return True
    return "MANAGER" in actor.roles and bool(resource.org_units & actor.managed_units)


def _assignment_covers(grant: Grant, resource: Resource) -> bool:
    match grant.scope_type:
        case "COMPANY":
            return True
        case "ORG_UNIT":
            return bool(resource.org_units & grant.units)
        case "DOCUMENT_TYPE":
            return resource.document_type is not None and resource.document_type == grant.scope_id
        case "REVIEW_QUEUE":
            return resource.review_queue is not None and resource.review_queue == grant.scope_id
    return False


def authorize(actor: Actor, permission: str, resource: Resource | None = None) -> Decision:
    """Allow | Deny(reason); mặc định từ chối. `resource=None` → chỉ xét có permission (kiểm tra ở mức route)."""
    grants = actor.grants.get(permission, ())
    if not grants:
        return Decision(False, "NO_PERMISSION")
    if resource is None:
        return ALLOW
    for grant in grants:
        if grant.source is Source.BASE:
            if not resource.business or _in_data_scope(actor, resource):
                return ALLOW
        elif _assignment_covers(grant, resource):
            return ALLOW
    return Decision(False, "OUT_OF_SCOPE")


def require(actor: Actor, permission: str, resource: Resource | None = None, *, hide: bool = True) -> None:
    """Như `authorize` nhưng ném lỗi: ngoài phạm vi với `hide` → `404 NOT_FOUND` (không lộ sự tồn tại), còn lại 403."""
    decision = authorize(actor, permission, resource)
    if decision.allowed:
        return
    if hide and resource is not None:
        raise ApiError("NOT_FOUND")
    raise ApiError("FORBIDDEN")


def scope_filter(
    actor: Actor,
    permission: str,
    *,
    owner: ColumnElement[Any],
    org_unit: ColumnElement[Any] | None = None,
    domain: str | None = None,
) -> ColumnElement[bool]:
    """Điều kiện SQL cho danh sách: chỉ bản ghi `authorize(actor, permission, …)` cho phép (SRS-ACC-02, ADR-007)."""
    grants = actor.grants.get(permission, ())
    if not grants:
        return false()
    conditions: list[ColumnElement[bool]] = []
    for grant in grants:
        if grant.source is Source.BASE:
            if "CEO" in actor.roles or ("CFO" in actor.roles and domain == FINANCE):
                return true()
            conditions.append(owner == actor.user_id)
            if "MANAGER" in actor.roles and org_unit is not None and actor.managed_units:
                conditions.append(org_unit.in_(actor.managed_units))
        elif grant.scope_type == "COMPANY":
            return true()
        elif grant.scope_type == "ORG_UNIT" and org_unit is not None and grant.units:
            conditions.append(org_unit.in_(grant.units))
    return or_(false(), *conditions)


class Principal(Protocol):
    @property
    def user_id(self) -> uuid.UUID: ...


@dataclass
class PermissionGuard:
    """Gắn kiểm tra quyền vào route (composition root tạo một lần, truyền cho router của module)."""

    factory: sessionmaker[Session]
    require_session: Callable[..., Principal]
    org: OrgScope = NO_ORG
    require_step_up: Callable[..., Principal] | None = None  # T-104: `Authenticator.require_step_up`
    _checks: dict[tuple[str, bool], Callable[..., Actor]] = field(default_factory=dict)

    def route(self, permission: str, *, step_up: bool = False) -> dict[str, Any]:
        """`@router.get(path, **guard.route("data.read"))`: khai báo + kiểm tra; handler lấy `Actor` qua `actor`.

        `step_up=True` (thao tác `STEP-UP`, SRS-IAM-08): session phải xác thực lại gần đây → nếu không `401
        REAUTH_REQUIRED`. Kiểm tra permission chạy trước step-up: người không có quyền nhận `403`, không bị mời reauth.
        """
        return {**declare(permission), "dependencies": [Depends(self._check(permission, step_up))]}

    def _check(self, permission: str, step_up: bool) -> Callable[..., Actor]:
        key = (permission, step_up)
        if key not in self._checks:
            guard = self
            if step_up and self.require_step_up is None:
                raise ValueError("PermissionGuard thiếu require_step_up cho route STEP-UP")

            def check(request: Request, principal: Principal = Depends(self.require_session)) -> Actor:  # noqa: B008
                with transaction(guard.factory) as session:
                    actor = load_actor(session, principal.user_id, guard.org)
                decision = authorize(actor, permission)
                if not decision.allowed:
                    guard._audit_denied(actor.user_id, permission, decision.reason)
                    raise ApiError("FORBIDDEN")
                if step_up and guard.require_step_up is not None:
                    guard.require_step_up(request)
                setattr(request.state, _ACTOR_STATE, actor)
                return actor

            self._checks[key] = check
        return self._checks[key]

    @staticmethod
    def actor(request: Request) -> Actor:
        """Dependency cho handler: `Actor` đã được `route(...)` nạp và kiểm tra."""
        actor = getattr(request.state, _ACTOR_STATE, None)
        if not isinstance(actor, Actor):
            raise ApiError("FORBIDDEN")
        return actor

    def _audit_denied(self, user_id: uuid.UUID, permission: str, reason: str) -> None:
        record_separately(
            self.factory,
            AuditEvent(
                category=Category.SECURITY,
                actor_type=ActorType.USER,
                actor_user_id=user_id,
                action="access.denied",
                outcome=Outcome.DENIED,
                reason=reason,
                changes={"permission": permission},
            ),
        )
