"""Ghi role và assignment (T-107; SRS-ACC-05…08, ADR-007, D-22 A3–A5).

Bất biến được thực thi ở CSDL (migration 0005); service ánh xạ lỗi CSDL sang mã lỗi API (API_Specification §10) và
ghi audit `ADMIN` trong cùng transaction (ADR-010). Kiểm tra quyền của người thao tác (`role.assign`,
`assignment.manage`, step-up) thuộc T-108/T-109 — service này không thay thế authorization.

- `grant_role` / `revoke_role`: không tự đổi role của mình (`SELF_ROLE_CHANGE`); `ADMIN` + `CFO` bị chặn
  (`ROLE_COMBINATION_FORBIDDEN`); không gỡ ADMIN hoạt động cuối (`LAST_ADMIN`). `granted_by=None` chỉ dùng cho
  bootstrap/recovery qua CLI (T-106).
- `create_assignment` / `revoke_assignment`: chỉ cho role đủ điều kiện (`ASSIGNMENT_NOT_ELIGIBLE`); thu hồi bằng
  `revoked_at`, không xóa.
Thu hồi session sau khi đổi role (A3) thuộc T-104/T-109.

T-109: `set_roles` (thay tập role: gỡ trước, cấp sau để đổi `ADMIN` → `CFO` không vướng INV-10), `list_assignments`,
`role_catalog`, idempotency cho `create_assignment` (`idempotency_key`, `request_hash` — migration 0008, INV-08).
Vi phạm CHECK/FK của assignment → `422 VALIDATION_ERROR` có tên trường.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sqlalchemy import ColumnElement, delete, insert, select, text, tuple_, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from aieos.access.models import AssignmentRow, RoleRow, UserRoleRow
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.platform.api import ApiError

# SQLSTATE do trigger migration 0005 phát; CHECK vi phạm là 23514 (kèm tên ràng buộc).
_SQLSTATE_CODES = {"AE001": "ROLE_COMBINATION_FORBIDDEN", "AE002": "LAST_ADMIN", "AE003": "ASSIGNMENT_NOT_ELIGIBLE"}
_SELF_CHECKS = ("ck_user_role_not_self_granted", "ck_assignment_not_self_granted", "ck_assignment_not_self_revoked")
_FIELD_CHECKS = {"ck_assignment_scope_id": "scope_id", "ck_assignment_validity": "valid_to"}
_FIELD_FKS = {"fk_assignment_user_id_user_account": "user_id", "fk_assignment_permission_code_permission": "permission"}


class ScopeType(StrEnum):
    COMPANY = "COMPANY"
    ORG_UNIT = "ORG_UNIT"
    DOCUMENT_TYPE = "DOCUMENT_TYPE"
    REVIEW_QUEUE = "REVIEW_QUEUE"


def _translate(error: DBAPIError) -> ApiError | None:
    state = getattr(error.orig, "sqlstate", None)
    if state in _SQLSTATE_CODES:
        return ApiError(_SQLSTATE_CODES[state])
    diag = getattr(error.orig, "diag", None)
    constraint = getattr(diag, "constraint_name", None)
    if state == "23514" and constraint in _SELF_CHECKS:
        return ApiError("SELF_ROLE_CHANGE")
    field = _FIELD_CHECKS.get(constraint or "") if state == "23514" else _FIELD_FKS.get(constraint or "")
    if state in ("23514", "23503") and field:
        return ApiError("VALIDATION_ERROR", errors=[{"field": field, "message": "Giá trị không hợp lệ"}])
    return None


def _run(session: Session, statement: object) -> int:
    try:
        with session.begin_nested():
            result = session.execute(statement)  # type: ignore[call-overload]
    except DBAPIError as error:
        translated = _translate(error)
        if translated is None:
            raise
        raise translated from None
    return int(getattr(result, "rowcount", 0) or 0)


def _audit(session: Session, actor: uuid.UUID | None, action: str, target: uuid.UUID, changes: dict[str, str]) -> None:
    record(
        session,
        AuditEvent(
            category=Category.ADMIN,
            actor_type=ActorType.USER if actor else ActorType.BOOTSTRAP,
            actor_user_id=actor,
            action=action,
            outcome=Outcome.SUCCESS,
            resource_type="identity.user_account",
            resource_id=str(target),
            changes=changes,
        ),
    )


def roles_of(session: Session, user_id: uuid.UUID) -> set[str]:
    return set(session.scalars(select(UserRoleRow.role_code).where(UserRoleRow.user_id == user_id)))


def active_admins(session: Session) -> list[uuid.UUID]:
    """Tài khoản có role `ADMIN` và `status = 'ACTIVE'` (SRS-IAM-09, SRS-IAM-10; cùng định nghĩa với INV-11)."""
    rows = session.execute(
        text(
            "SELECT ur.user_id FROM access.user_role ur JOIN identity.user_account u ON u.id = ur.user_id "
            "WHERE ur.role_code = 'ADMIN' AND u.status = 'ACTIVE' ORDER BY ur.user_id"
        )
    )
    return [row.user_id for row in rows]


def effective_permissions(session: Session, user_id: uuid.UUID) -> set[str]:
    """Permission hiệu lực (chưa xét phạm vi): quyền nền của role + assignment còn hiệu lực. Phạm vi: T-108."""
    rows = session.execute(
        text(
            "SELECT rp.permission_code FROM access.user_role ur "
            "JOIN access.role_permission rp ON rp.role_code = ur.role_code AND rp.kind = 'BASE' "
            "WHERE ur.user_id = :u "
            "UNION SELECT permission_code FROM access.assignment WHERE user_id = :u AND revoked_at IS NULL "
            "AND valid_from <= now() AND (valid_to IS NULL OR valid_to > now())"
        ),
        {"u": user_id},
    )
    return set(rows.scalars())


def known_roles(session: Session) -> set[str]:
    return set(session.scalars(select(RoleRow.code)))


def grant_role(
    session: Session, *, user_id: uuid.UUID, role: str, granted_by: uuid.UUID | None, reason: str | None
) -> None:
    """Cấp role trong transaction hiện hành; đã có role → không đổi gì."""
    if granted_by is not None and granted_by == user_id:
        raise ApiError("SELF_ROLE_CHANGE")
    if role not in known_roles(session):
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "role", "message": "Role không tồn tại"}])
    if role in roles_of(session, user_id):
        return
    _run(session, insert(UserRoleRow).values(user_id=user_id, role_code=role, granted_by=granted_by, reason=reason))
    _audit(session, granted_by, "access.role.grant", user_id, {"role": role, "reason": reason or ""})


def revoke_role(session: Session, *, user_id: uuid.UUID, role: str, revoked_by: uuid.UUID, reason: str) -> None:
    if revoked_by == user_id:
        raise ApiError("SELF_ROLE_CHANGE")
    removed = _run(session, delete(UserRoleRow).where(UserRoleRow.user_id == user_id, UserRoleRow.role_code == role))
    if removed:
        _audit(session, revoked_by, "access.role.revoke", user_id, {"role": role, "reason": reason})


def create_assignment(
    session: Session,
    *,
    user_id: uuid.UUID,
    permission: str,
    scope_type: ScopeType,
    scope_id: str | None,
    granted_by: uuid.UUID,
    reason: str,
    valid_to: datetime | None = None,
    idempotency_key: str | None = None,
    request_hash: str | None = None,
) -> uuid.UUID:
    if granted_by == user_id:
        raise ApiError("SELF_ROLE_CHANGE")
    assignment_id = uuid.uuid4()
    _run(
        session,
        insert(AssignmentRow).values(
            id=assignment_id,
            user_id=user_id,
            permission_code=permission,
            scope_type=scope_type.value,
            scope_id=scope_id,
            granted_by=granted_by,
            reason=reason,
            valid_to=valid_to,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        ),
    )
    _audit(
        session,
        granted_by,
        "access.assignment.create",
        user_id,
        {"permission": permission, "scope_type": scope_type.value, "scope_id": scope_id or "", "reason": reason},
    )
    return assignment_id


def revoke_assignment(session: Session, *, assignment_id: uuid.UUID, revoked_by: uuid.UUID) -> None:
    target = session.scalar(select(AssignmentRow.user_id).where(AssignmentRow.id == assignment_id))
    if target is None:
        raise ApiError("NOT_FOUND")
    if target == revoked_by:
        raise ApiError("SELF_ROLE_CHANGE")
    changed = _run(
        session,
        update(AssignmentRow)
        .where(AssignmentRow.id == assignment_id, AssignmentRow.revoked_at.is_(None))
        .values(revoked_at=text("now()"), revoked_by=revoked_by),
    )
    if changed:
        _audit(session, revoked_by, "access.assignment.revoke", target, {"assignment_id": str(assignment_id)})


def set_roles(
    session: Session, *, user_id: uuid.UUID, roles: set[str], changed_by: uuid.UUID, reason: str
) -> tuple[set[str], set[str]]:
    """Thay tập role của `user_id` (API-ADM-05); trả (thêm, gỡ). Gỡ trước rồi cấp (đổi ADMIN → CFO hợp lệ)."""
    if changed_by == user_id:
        raise ApiError("SELF_ROLE_CHANGE")
    unknown = roles - known_roles(session)
    if unknown:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "roles", "message": "Role không tồn tại"}])
    current = roles_of(session, user_id)
    removed, added = current - roles, roles - current
    for role in sorted(removed):
        revoke_role(session, user_id=user_id, role=role, revoked_by=changed_by, reason=reason)
    for role in sorted(added):
        grant_role(session, user_id=user_id, role=role, granted_by=changed_by, reason=reason)
    return added, removed


@dataclass(frozen=True)
class Assignment:
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


def _assignment(row: AssignmentRow) -> Assignment:
    return Assignment(
        row.id,
        row.user_id,
        row.permission_code,
        row.scope_type,
        row.scope_id,
        row.valid_from,
        row.valid_to,
        row.granted_by,
        row.reason,
        row.created_at,
        row.revoked_at,
        row.revoked_by,
    )


def get_assignment(session: Session, assignment_id: uuid.UUID) -> Assignment | None:
    row = session.get(AssignmentRow, assignment_id)
    return None if row is None else _assignment(row)


def find_assignment_by_key(
    session: Session, granted_by: uuid.UUID, idempotency_key: str
) -> tuple[str, Assignment] | None:
    row = session.scalar(
        select(AssignmentRow).where(
            AssignmentRow.granted_by == granted_by, AssignmentRow.idempotency_key == idempotency_key
        )
    )
    if row is None or row.request_hash is None:
        return None
    return row.request_hash, _assignment(row)


def list_assignments(
    session: Session,
    *,
    user_id: uuid.UUID | None = None,
    permission: str | None = None,
    limit: int,
    after: tuple[datetime, uuid.UUID] | None = None,
) -> list[Assignment]:
    """API-ADM-06: mới nhất trước (`created_at`, `id` giảm dần); gồm cả assignment đã thu hồi/hết hạn."""
    conditions: list[ColumnElement[bool]] = []
    if user_id is not None:
        conditions.append(AssignmentRow.user_id == user_id)
    if permission is not None:
        conditions.append(AssignmentRow.permission_code == permission)
    if after is not None:
        conditions.append(tuple_(AssignmentRow.created_at, AssignmentRow.id) < tuple_(*after))
    query = (
        select(AssignmentRow)
        .where(*conditions)
        .order_by(AssignmentRow.created_at.desc(), AssignmentRow.id.desc())
        .limit(limit)
    )
    return [_assignment(row) for row in session.scalars(query)]


def role_catalog(session: Session) -> list[dict[str, object]]:
    """API-ADM-09: mỗi role kèm permission nền (`BASE`) và permission đủ điều kiện nhận assignment (`ELIGIBLE`)."""
    rows = session.execute(
        text("SELECT role_code, permission_code, kind FROM access.role_permission ORDER BY role_code, permission_code")
    ).all()
    catalog: dict[str, dict[str, list[str]]] = {
        code: {"base": [], "eligible": []} for code in sorted(known_roles(session))
    }
    for role, permission, kind in rows:
        catalog[role]["base" if kind == "BASE" else "eligible"].append(permission)
    return [{"code": code, **lists} for code, lists in catalog.items()]
