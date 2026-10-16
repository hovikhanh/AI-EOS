"""Endpoint mục tiêu (T-501): API-GOAL-01 `GET /goals/objectives`, API-GOAL-02 `GET /goals/kpis`, API-GOAL-03
`POST/PATCH /goals/objectives|key-results|kpis`, API-GOAL-05 `POST /goals/key-results/{id}/check-ins`, API-GOAL-06
`POST /goals/{type}/{id}/measurements` (T-501); API-GOAL-04 `POST /goals/{type}/{id}/activate` (T-502).

Router mỏng (ADR-002). Số (baseline, target, giá trị) trả dạng chuỗi thập phân — không float (CLAUDE.md §5). Không có
trường % đạt hay cảnh báo (SRS-GOAL-09).
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, ConfigDict, Field

from aieos.access.api import Actor, PermissionGuard
from aieos.goals import service
from aieos.platform.api import (
    IDEMPOTENCY_HEADER,
    etag,
    request_fingerprint,
    require_idempotency_key,
    require_if_match,
    run_idempotent,
    transaction,
)

Number = Annotated[Decimal, Field(max_digits=30, decimal_places=6)]
Text200 = Annotated[str, Field(min_length=1, max_length=200)]


class MeasurementOut(BaseModel):
    value: Decimal
    report_period_label: str
    source_document_id: uuid.UUID | None
    recorded_by: uuid.UUID
    created_at: datetime


class CheckInOut(BaseModel):
    value: Decimal
    confidence: int
    blocker: str | None
    submitted_by: uuid.UUID
    created_at: datetime


class KeyResultOut(BaseModel):
    id: uuid.UUID
    objective_id: uuid.UUID
    metric: str
    baseline: Decimal | None
    target: Decimal
    unit: str | None
    owner_user_id: uuid.UUID
    period_label: str
    status: str
    version: int
    latest_measurement: MeasurementOut | None
    latest_check_in: CheckInOut | None


class ObjectiveOut(BaseModel):
    id: uuid.UUID
    title: str
    owner_user_id: uuid.UUID
    period_label: str
    org_unit_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    status: str
    version: int
    key_results: list[KeyResultOut]


class KpiOut(BaseModel):
    id: uuid.UUID
    metric: str
    baseline: Decimal | None
    target: Decimal
    unit: str | None
    owner_user_id: uuid.UUID
    period_label: str
    org_unit_id: uuid.UUID | None
    status: str
    version: int
    latest_measurement: MeasurementOut | None


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ObjectiveIn(_In):
    title: Annotated[str, Field(min_length=1, max_length=500)]
    owner_user_id: uuid.UUID
    period_label: Text200
    org_unit_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None


class ObjectivePatch(_In):
    title: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    owner_user_id: uuid.UUID | None = None
    period_label: Text200 | None = None
    org_unit_id: uuid.UUID | None = None
    parent_id: uuid.UUID | None = None


class KeyResultIn(_In):
    objective_id: uuid.UUID
    metric: Annotated[str, Field(min_length=1, max_length=500)]
    baseline: Number | None = None
    target: Number
    unit: Annotated[str, Field(max_length=50)] | None = None
    owner_user_id: uuid.UUID
    period_label: Text200


class MetricPatch(_In):
    metric: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    baseline: Number | None = None
    target: Number | None = None
    unit: Annotated[str, Field(max_length=50)] | None = None
    owner_user_id: uuid.UUID | None = None
    period_label: Text200 | None = None


class KpiIn(_In):
    metric: Annotated[str, Field(min_length=1, max_length=500)]
    baseline: Number | None = None
    target: Number
    unit: Annotated[str, Field(max_length=50)] | None = None
    owner_user_id: uuid.UUID
    period_label: Text200
    org_unit_id: uuid.UUID | None = None


class KpiPatch(MetricPatch):
    org_unit_id: uuid.UUID | None = None


class CheckInIn(_In):
    value: Number
    confidence: Annotated[int, Field(ge=0, le=10)]  # Q-30 → D-51
    blocker: Annotated[str, Field(max_length=2000)] | None = None


class MeasurementIn(_In):
    value: Number
    report_period_label: Text200
    source_document_id: uuid.UUID | None = None


def _dump(item: Any) -> dict[str, Any]:
    return {k: (_dump(v) if hasattr(v, "__dataclass_fields__") else [_dump(x) for x in v] if isinstance(v, list) else v)
            for k, v in item.__dict__.items()}  # fmt: skip


def build_goals_router(guard: PermissionGuard) -> APIRouter:
    router = APIRouter(tags=["goals"])
    actor_dep = Annotated[Actor, Depends(guard.actor)]
    key_header = Annotated[str | None, Header(alias=IDEMPOTENCY_HEADER)]
    if_match = Annotated[str | None, Header(alias="If-Match")]

    @router.get("/goals/objectives", response_model=list[ObjectiveOut], **guard.route("data.read"))
    def objectives(
        actor: actor_dep,
        status: Literal["DRAFT", "ACTIVE"] | None = None,
        org_unit_id: uuid.UUID | None = None,
        period_label: str | None = None,
    ) -> list[dict[str, Any]]:
        with transaction(guard.factory) as session:
            items = service.list_objectives(
                session, actor, status=status, org_unit_id=org_unit_id, period_label=period_label
            )
            return [_dump(o) for o in items]

    @router.get("/goals/kpis", response_model=list[KpiOut], **guard.route("data.read"))
    def kpis(actor: actor_dep, status: Literal["DRAFT", "ACTIVE"] | None = None) -> list[dict[str, Any]]:
        with transaction(guard.factory) as session:
            return [_dump(k) for k in service.list_kpis(session, actor, status=status)]

    def create(path: str, kind: str, body: BaseModel, actor: Actor, response: Response, key: str | None) -> Any:
        idempotency_key = require_idempotency_key(key)
        fingerprint = request_fingerprint("POST", path, body.model_dump_json().encode(), str(actor.user_id))
        creators: dict[str, Callable[..., Any]] = {
            "objective": service.create_objective,
            "key_result": service.create_key_result,
            "kpi": service.create_kpi,
        }
        with transaction(guard.factory) as session:
            item, _ = run_idempotent(
                session,
                fingerprint=fingerprint,
                find=lambda: service.find_by_key(session, actor, kind, idempotency_key),
                create=lambda: creators[kind](
                    session, actor, body.model_dump(), key=idempotency_key, request_hash=fingerprint
                ),
            )
            response.headers["ETag"] = etag(item.version)
            return _dump(item)

    def update(
        kind: str, item_id: uuid.UUID, body: BaseModel, actor: Actor, response: Response, version: str | None
    ) -> Any:
        expected = require_if_match(version)
        with transaction(guard.factory) as session:
            item = service.update_draft(
                session, actor, kind, item_id, body.model_dump(exclude_unset=True), expected_version=expected
            )
            response.headers["ETag"] = etag(item.version)
            return _dump(item)

    write = guard.route("record.submit")

    @router.post("/goals/objectives", status_code=201, response_model=ObjectiveOut, **write)
    def create_objective(body: ObjectiveIn, actor: actor_dep, response: Response, key: key_header = None) -> Any:
        return create("/goals/objectives", "objective", body, actor, response, key)

    @router.post("/goals/key-results", status_code=201, response_model=KeyResultOut, **write)
    def create_key_result(body: KeyResultIn, actor: actor_dep, response: Response, key: key_header = None) -> Any:
        return create("/goals/key-results", "key_result", body, actor, response, key)

    @router.post("/goals/kpis", status_code=201, response_model=KpiOut, **write)
    def create_kpi(body: KpiIn, actor: actor_dep, response: Response, key: key_header = None) -> Any:
        return create("/goals/kpis", "kpi", body, actor, response, key)

    @router.patch("/goals/objectives/{item_id}", response_model=ObjectiveOut, **write)
    def update_objective(
        item_id: uuid.UUID, body: ObjectivePatch, actor: actor_dep, response: Response, version: if_match = None
    ) -> Any:
        return update("objective", item_id, body, actor, response, version)

    @router.patch("/goals/key-results/{item_id}", response_model=KeyResultOut, **write)
    def update_key_result(
        item_id: uuid.UUID, body: MetricPatch, actor: actor_dep, response: Response, version: if_match = None
    ) -> Any:
        return update("key_result", item_id, body, actor, response, version)

    @router.patch("/goals/kpis/{item_id}", response_model=KpiOut, **write)
    def update_kpi(
        item_id: uuid.UUID, body: KpiPatch, actor: actor_dep, response: Response, version: if_match = None
    ) -> Any:
        return update("kpi", item_id, body, actor, response, version)

    @router.post(
        "/goals/key-results/{kr_id}/check-ins",
        status_code=201,
        response_model=CheckInOut,
        **guard.route("record.submit"),
    )
    def check_in(kr_id: uuid.UUID, body: CheckInIn, actor: actor_dep, key: key_header = None) -> Any:
        idempotency_key = require_idempotency_key(key)
        path = f"/goals/key-results/{kr_id}/check-ins"
        fingerprint = request_fingerprint("POST", path, body.model_dump_json().encode(), str(actor.user_id))
        with transaction(guard.factory) as session:
            item, _ = run_idempotent(
                session,
                fingerprint=fingerprint,
                find=lambda: service.find_check_in(session, actor, idempotency_key),
                create=lambda: service.check_in(
                    session, actor, kr_id, value=body.value, confidence=body.confidence, blocker=body.blocker,
                    key=idempotency_key, request_hash=fingerprint,
                ),
            )  # fmt: skip
            return _dump(item)

    @router.post(
        "/goals/{kind}/{target_id}/measurements",
        status_code=201,
        response_model=MeasurementOut,
        **guard.route("record.submit"),
    )
    def measurement(
        kind: Literal["key-results", "kpis"], target_id: uuid.UUID, body: MeasurementIn, actor: actor_dep,
        key: key_header = None,
    ) -> Any:  # fmt: skip
        idempotency_key = require_idempotency_key(key)
        path = f"/goals/{kind}/{target_id}/measurements"
        fingerprint = request_fingerprint("POST", path, body.model_dump_json().encode(), str(actor.user_id))
        with transaction(guard.factory) as session:
            item, _ = run_idempotent(
                session,
                fingerprint=fingerprint,
                find=lambda: service.find_measurement(session, actor, idempotency_key),
                create=lambda: service.record_measurement(
                    session, actor, "KR" if kind == "key-results" else "KPI", target_id, value=body.value,
                    report_period_label=body.report_period_label, source_document_id=body.source_document_id,
                    key=idempotency_key, request_hash=fingerprint,
                ),
            )  # fmt: skip
            return _dump(item)

    def activate(kind: str, item_id: uuid.UUID, actor: Actor, response: Response, version: str | None) -> Any:
        """API-GOAL-04: `DRAFT → ACTIVE`; `goals.activate` chỉ qua assignment (D-39, Q-28 → D-51); `If-Match`."""
        expected = require_if_match(version)
        with transaction(guard.factory) as session:
            item = service.activate(session, actor, kind, item_id, expected_version=expected)
            response.headers["ETag"] = etag(item.version)
            return _dump(item)

    activation = guard.route("goals.activate")

    @router.post("/goals/objectives/{item_id}/activate", response_model=ObjectiveOut, **activation)
    def activate_objective(item_id: uuid.UUID, actor: actor_dep, response: Response, version: if_match = None) -> Any:
        return activate("objective", item_id, actor, response, version)

    @router.post("/goals/key-results/{item_id}/activate", response_model=KeyResultOut, **activation)
    def activate_key_result(item_id: uuid.UUID, actor: actor_dep, response: Response, version: if_match = None) -> Any:
        return activate("key_result", item_id, actor, response, version)

    @router.post("/goals/kpis/{item_id}/activate", response_model=KpiOut, **activation)
    def activate_kpi(item_id: uuid.UUID, actor: actor_dep, response: Response, version: if_match = None) -> Any:
        return activate("kpi", item_id, actor, response, version)

    return router
