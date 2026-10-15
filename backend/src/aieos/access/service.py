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
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import delete, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from aieos.access.models import AssignmentRow, RoleRow, UserRoleRow
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.platform.api import ApiError

# SQLSTATE do trigger migration 0005 phát; CHECK vi phạm là 23514 (kèm tên ràng buộc).
_SQLSTATE_CODES = {"AE001": "ROLE_COMBINATION_FORBIDDEN", "AE002": "LAST_ADMIN", "AE003": "ASSIGNMENT_NOT_ELIGIBLE"}
_SELF_CHECKS = ("ck_user_role_not_self_granted", "ck_assignment_not_self_granted", "ck_assignment_not_self_revoked")


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
    if state == "23514" and getattr(diag, "constraint_name", None) in _SELF_CHECKS:
        return ApiError("SELF_ROLE_CHANGE")
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
