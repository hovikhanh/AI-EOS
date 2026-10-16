"""Cấu hình autonomy trong trần (T-305, SRS-AIC-15, R8): đọc Tool Registry, đọc/sửa `ai.autonomy_policy`.

- Tool Registry chỉ đọc (API-AI-03): seed qua migration, không sửa trần qua API.
- Chỉ sửa `level` (và `reason`) của policy đã có (API-AI-05 là `PUT` theo id) — không tạo/xóa policy, không đổi
  `tool_name`, `role_code`, `value_threshold` (ngưỡng tiền chưa có giá trị — D-16).
- Trần (INV-12, SRS-AIC-02): `level ≤ tool.max_autonomy_level`, `level ≤ 3` (không có L4 — D-11), tool tài chính
  `level ≤ 2` (D-12) → vượt trần `422 AUTONOMY_CAP_EXCEEDED`. CSDL kiểm lại (trigger `AE030`, CHECK) — lỗi CSDL cùng
  loại cũng trả mã này.
- Thành công: audit ADMIN trong cùng transaction (mức cũ → mới, lý do); lỗi nghiệp vụ: audit `FAILED` riêng.
- Dữ liệu trả về chỉ là cấu hình (tên tool, mức, người/thời điểm đổi) — không có dữ liệu nghiệp vụ (D-21).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from aieos.ai.models import AutonomyPolicyRow, ToolRow
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record, record_separately
from aieos.platform.api import ApiError, check_version, transaction

MAX_LEVEL = 3  # L4 không tồn tại trong MVP (D-11)
FINANCIAL_MAX_LEVEL = 2  # ghi tài chính luôn L2 (D-12)
CAP_SQLSTATES = frozenset({"AE030", "23514"})  # trigger trần (INV-12), CHECK `level BETWEEN 0 AND 3`
AUDIT_ACTION = "ai.autonomy_policy.update"
RESOURCE_TYPE = "ai.autonomy_policy"


@dataclass(frozen=True)
class Tool:
    name: str
    module: str
    operation_type: str
    risk_level: str | None
    financial: bool
    max_autonomy_level: int
    approval_required: bool
    params_schema: dict[str, Any] | None
    enabled: bool


@dataclass(frozen=True)
class Policy:
    id: uuid.UUID
    tool_name: str
    role_code: str | None
    value_threshold: Decimal | None
    level: int
    max_autonomy_level: int
    financial: bool
    updated_by: uuid.UUID | None
    updated_at: datetime
    reason: str | None
    version: int


def effective_cap(max_autonomy_level: int, financial: bool) -> int:
    """Trần cho policy của một tool: min(trần tool, L3, L2 nếu tài chính) (SRS-AIC-02)."""
    cap = min(max_autonomy_level, MAX_LEVEL)
    return min(cap, FINANCIAL_MAX_LEVEL) if financial else cap


def check_within_cap(level: int, *, max_autonomy_level: int, financial: bool) -> None:
    """`422 AUTONOMY_CAP_EXCEEDED` nếu `level` vượt trần (R8); mức âm do validate đầu vào chặn (`VALIDATION_ERROR`)."""
    cap = effective_cap(max_autonomy_level, financial)
    if level > cap:
        raise ApiError("AUTONOMY_CAP_EXCEEDED", f"Mức L{level} vượt trần L{cap} của tool")


def _tool(row: ToolRow) -> Tool:
    return Tool(
        name=row.name,
        module=row.module,
        operation_type=row.operation_type,
        risk_level=row.risk_level,
        financial=row.financial,
        max_autonomy_level=row.max_autonomy_level,
        approval_required=row.approval_required,
        params_schema=row.params_schema,
        enabled=row.enabled,
    )


def _policy(row: AutonomyPolicyRow, tool: ToolRow) -> Policy:
    return Policy(
        id=row.id,
        tool_name=row.tool_name,
        role_code=row.role_code,
        value_threshold=row.value_threshold,
        level=row.level,
        max_autonomy_level=effective_cap(tool.max_autonomy_level, tool.financial),
        financial=tool.financial,
        updated_by=row.updated_by,
        updated_at=row.updated_at,
        reason=row.reason,
        version=row.version,
    )


def list_tools(session: Session) -> list[Tool]:
    return [_tool(row) for row in session.scalars(select(ToolRow).order_by(ToolRow.name))]


def list_policies(session: Session) -> list[Policy]:
    query = (
        select(AutonomyPolicyRow, ToolRow)
        .join(ToolRow, ToolRow.name == AutonomyPolicyRow.tool_name)
        .order_by(
            AutonomyPolicyRow.tool_name,
            AutonomyPolicyRow.role_code.asc().nulls_first(),
            AutonomyPolicyRow.value_threshold.asc().nulls_first(),
            AutonomyPolicyRow.id,
        )
    )
    return [_policy(policy, tool) for policy, tool in session.execute(query)]


def _failed(factory: sessionmaker[Session], actor: uuid.UUID, policy_id: uuid.UUID, error: ApiError) -> None:
    record_separately(
        factory,
        AuditEvent(
            category=Category.ADMIN,
            actor_type=ActorType.USER,
            actor_user_id=actor,
            action=AUDIT_ACTION,
            outcome=Outcome.FAILED,
            resource_type=RESOURCE_TYPE,
            resource_id=str(policy_id),
            reason=error.code,
        ),
    )


def set_level(
    factory: sessionmaker[Session],
    *,
    actor: uuid.UUID,
    policy_id: uuid.UUID,
    level: int,
    reason: str,
    expected_version: int,
) -> Policy:
    """API-AI-05: đặt mức của policy `policy_id` trong trần; `If-Match` = `version`."""
    try:
        with transaction(factory) as session:
            row = session.scalars(
                select(AutonomyPolicyRow).where(AutonomyPolicyRow.id == policy_id).with_for_update()
            ).one_or_none()
            if row is None:
                raise ApiError("NOT_FOUND")
            tool = session.scalars(
                select(ToolRow).where(ToolRow.name == row.tool_name).with_for_update(read=True)
            ).one()
            check_version(row.version, expected_version)
            check_within_cap(level, max_autonomy_level=tool.max_autonomy_level, financial=tool.financial)
            old = row.level
            row.level = level
            row.reason = reason
            row.updated_by = actor
            row.updated_at = func.now()
            row.version = row.version + 1
            try:
                session.flush()
            except DBAPIError as error:  # CSDL kiểm lại trần (INV-12)
                if getattr(error.orig, "sqlstate", None) in CAP_SQLSTATES:
                    raise ApiError("AUTONOMY_CAP_EXCEEDED", "Mức vượt trần của tool") from None
                raise
            record(
                session,
                AuditEvent(
                    category=Category.ADMIN,
                    actor_type=ActorType.USER,
                    actor_user_id=actor,
                    action=AUDIT_ACTION,
                    outcome=Outcome.SUCCESS,
                    resource_type=RESOURCE_TYPE,
                    resource_id=str(policy_id),
                    reason=reason,
                    changes={
                        "tool_name": row.tool_name,
                        "role_code": row.role_code,
                        "level": {"old": old, "new": level},
                    },
                ),
            )
            session.refresh(row)  # `updated_at` mới
            return _policy(row, tool)
    except ApiError as error:
        if error.code != "NOT_FOUND":
            _failed(factory, actor, policy_id, error)
        raise
