"""Endpoint cấu hình autonomy (T-305): API-AI-03 `GET /admin/ai/tools`, API-AI-04 `GET /admin/ai/autonomy-policies`,
API-AI-05 `PUT /admin/ai/autonomy-policies/{id}` (`STEP-UP`, `IF-MATCH`).

Router mỏng (ADR-002); quyền `config.autonomy` (ADMIN nền, Architecture §6) qua `PermissionGuard`. Logic ở
`ai.autonomy`. `value_threshold` trả dạng chuỗi thập phân (CLAUDE.md §5).
"""

import uuid
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from aieos.access.api import Actor, PermissionGuard
from aieos.ai import autonomy
from aieos.platform.api import etag, require_if_match, transaction

PERMISSION = "config.autonomy"


class ToolOut(BaseModel):
    name: str
    module: str
    operation_type: str
    risk_level: str | None
    financial: bool
    max_autonomy_level: int
    approval_required: bool
    params_schema: dict[str, Any] | None
    enabled: bool


class PolicyOut(BaseModel):
    id: uuid.UUID
    tool_name: str
    role_code: str | None
    value_threshold: Decimal | None
    level: int
    max_autonomy_level: int  # trần hiệu lực của policy (trần tool, L3, L2 nếu tài chính)
    financial: bool
    updated_by: uuid.UUID | None
    updated_at: datetime
    reason: str | None
    version: int


class PolicyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Chỉ chặn số âm ở đây; vượt trần (kể cả L4+) → `422 AUTONOMY_CAP_EXCEEDED` ở service (TC-AIC-12, TC-AIC-02).
    level: Annotated[StrictInt, Field(ge=0)]
    reason: str = Field(min_length=1, max_length=1000)


def build_ai_admin_router(guard: PermissionGuard) -> APIRouter:
    router = APIRouter(tags=["admin"])
    actor_dep = Annotated[Actor, Depends(guard.actor)]
    if_match = Annotated[str | None, Header(alias="If-Match")]

    @router.get("/admin/ai/tools", response_model=list[ToolOut], **guard.route(PERMISSION))
    def tools() -> list[dict[str, Any]]:
        with transaction(guard.factory) as session:
            return [asdict(t) for t in autonomy.list_tools(session)]

    @router.get("/admin/ai/autonomy-policies", response_model=list[PolicyOut], **guard.route(PERMISSION))
    def policies() -> list[dict[str, Any]]:
        with transaction(guard.factory) as session:
            return [asdict(p) for p in autonomy.list_policies(session)]

    @router.put(
        "/admin/ai/autonomy-policies/{policy_id}", response_model=PolicyOut, **guard.route(PERMISSION, step_up=True)
    )
    def set_policy(
        policy_id: uuid.UUID, body: PolicyIn, actor: actor_dep, response: Response, version: if_match = None
    ) -> dict[str, Any]:
        expected = require_if_match(version)
        policy = autonomy.set_level(
            guard.factory,
            actor=actor.user_id,
            policy_id=policy_id,
            level=body.level,
            reason=body.reason,
            expected_version=expected,
        )
        response.headers["ETag"] = etag(policy.version)
        return asdict(policy)

    return router
