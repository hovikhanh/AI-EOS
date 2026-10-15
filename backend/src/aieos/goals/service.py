"""Mục tiêu (T-501; SRS-GOAL-01…03, 05…07, 09, 11; API-GOAL-01, 02, 03, 05, 06; D-39, D-51).

- **Trạng thái:** tạo mới luôn `DRAFT`; chỉ sửa được khi `DRAFT`. Kích hoạt `DRAFT → ACTIVE` thuộc T-502
  (`goals.activate`).
- **Không tính % đạt hay cảnh báo** (SRS-GOAL-09): chỉ trả baseline, target, giá trị đo gần nhất (Q-29 chưa duyệt công
  thức).
- **Phạm vi (SRS-ACC-02/03, T-108):** Objective/KPI thấy được khi owner hoặc đơn vị (và cấp trên) thuộc phạm vi
  `data.read` của người xem, hoặc người xem là owner/người tạo, hoặc (Objective) người xem là owner một KR của nó. KR
  theo Objective cha + owner KR. Ngoài phạm vi → `404`. "Mục tiêu cha" cho EMPLOYEE chưa làm (T-108 — mặc định deny).
- **Tạo/sửa (API-GOAL-03):** `record.submit`; owner phải là chính mình hoặc trong phạm vi `data.read` của người tạo.
  `IDEMPOTENT` (tạo) / `IF-MATCH` (sửa); chỉ người tạo hoặc owner sửa.
- **Check-in (API-GOAL-05, SRS-GOAL-07):** chỉ owner KR (người khác thấy KR → `403`); độ tự tin 0–10 (Q-30 → D-51).
- **Đo lường (API-GOAL-06, SRS-GOAL-06):** `record.submit` trên KR/KPI (owner hoặc trong phạm vi); gắn kỳ báo cáo và
  nguồn (`source_document_id`, hoặc nhập tay = người ghi).
- Audit `BUSINESS` trong cùng transaction.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from aieos.access.api import Actor, Resource, authorize, scope_filter
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.capture.api import document_exists
from aieos.goals.models import CheckInRow, KeyResultRow, KpiRow, MeasurementRow, ObjectiveRow
from aieos.org.api import unit_path
from aieos.platform.api import ApiError, check_version

READ = "data.read"
WRITE = "record.submit"


@dataclass(frozen=True)
class Measurement:
    value: Decimal
    report_period_label: str
    source_document_id: uuid.UUID | None
    recorded_by: uuid.UUID
    created_at: datetime


@dataclass(frozen=True)
class CheckIn:
    value: Decimal
    confidence: int
    blocker: str | None
    submitted_by: uuid.UUID
    created_at: datetime


@dataclass(frozen=True)
class KeyResult:
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
    latest_measurement: Measurement | None = None
    latest_check_in: CheckIn | None = None


@dataclass(frozen=True)
class Objective:
    id: uuid.UUID
    title: str
    owner_user_id: uuid.UUID
    period_label: str
    org_unit_id: uuid.UUID | None
    parent_id: uuid.UUID | None
    status: str
    version: int
    key_results: list[KeyResult] = field(default_factory=list)


@dataclass(frozen=True)
class Kpi:
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
    latest_measurement: Measurement | None = None


def _audit(session: Session, actor: uuid.UUID, action: str, kind: str, target: uuid.UUID) -> None:
    record(
        session,
        AuditEvent(
            category=Category.BUSINESS,
            actor_type=ActorType.USER,
            actor_user_id=actor,
            action=action,
            outcome=Outcome.SUCCESS,
            resource_type=f"goals.{kind}",
            resource_id=str(target),
        ),
    )


def _allowed(session: Session, actor: Actor, permission: str, owner: uuid.UUID, unit: uuid.UUID | None) -> bool:
    return authorize(actor, permission, Resource(owner_id=owner, org_units=unit_path(session, unit))).allowed


def _check_owner(session: Session, actor: Actor, owner: uuid.UUID, unit: uuid.UUID | None) -> None:
    if owner != actor.user_id and not _allowed(session, actor, READ, owner, unit):
        raise ApiError("FORBIDDEN", "Owner ngoài phạm vi của bạn")


# ---------- Đọc ----------


def _objective_filter(actor: Actor) -> Any:
    return or_(
        scope_filter(
            actor, READ, owner=ObjectiveRow.owner_user_id.expression, org_unit=ObjectiveRow.org_unit_id.expression
        ),
        ObjectiveRow.created_by == actor.user_id,
        exists().where(KeyResultRow.objective_id == ObjectiveRow.id, KeyResultRow.owner_user_id == actor.user_id),
    )


def _latest_measurements(session: Session, kind: str, ids: list[uuid.UUID]) -> dict[uuid.UUID, Measurement]:
    if not ids:
        return {}
    rows = session.scalars(
        select(MeasurementRow)
        .where(MeasurementRow.target_type == kind, MeasurementRow.target_id.in_(ids))
        .order_by(MeasurementRow.target_id, MeasurementRow.created_at.desc(), MeasurementRow.id.desc())
        .ext(distinct_on(MeasurementRow.target_id))
    )
    return {
        r.target_id: Measurement(r.value, r.report_period_label, r.source_document_id, r.recorded_by, r.created_at)
        for r in rows
    }


def _latest_check_ins(session: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, CheckIn]:
    if not ids:
        return {}
    rows = session.scalars(
        select(CheckInRow)
        .where(CheckInRow.key_result_id.in_(ids))
        .order_by(CheckInRow.key_result_id, CheckInRow.created_at.desc(), CheckInRow.id.desc())
        .ext(distinct_on(CheckInRow.key_result_id))
    )
    return {r.key_result_id: CheckIn(r.value, r.confidence, r.blocker, r.submitted_by, r.created_at) for r in rows}


def _kr(row: KeyResultRow, m: dict[uuid.UUID, Measurement], c: dict[uuid.UUID, CheckIn]) -> KeyResult:
    return KeyResult(
        row.id, row.objective_id, row.metric, row.baseline, row.target, row.unit, row.owner_user_id,
        row.period_label, row.status, row.version, m.get(row.id), c.get(row.id),
    )  # fmt: skip


def list_objectives(
    session: Session,
    actor: Actor,
    *,
    status: str | None = None,
    org_unit_id: uuid.UUID | None = None,
    period_label: str | None = None,
) -> list[Objective]:
    """API-GOAL-01: Objective trong phạm vi kèm KR, giá trị đo gần nhất và check-in gần nhất (tổng hợp cho MANAGER —
    SRS-GOAL-11)."""
    conditions = [_objective_filter(actor)]
    if status is not None:
        conditions.append(ObjectiveRow.status == status)
    if org_unit_id is not None:
        conditions.append(ObjectiveRow.org_unit_id == org_unit_id)
    if period_label is not None:
        conditions.append(ObjectiveRow.period_label == period_label)
    objectives = list(session.scalars(select(ObjectiveRow).where(and_(*conditions)).order_by(ObjectiveRow.created_at)))
    krs = list(
        session.scalars(
            select(KeyResultRow)
            .where(KeyResultRow.objective_id.in_([o.id for o in objectives]))
            .order_by(KeyResultRow.created_at)
        )
    ) if objectives else []  # fmt: skip
    ids = [k.id for k in krs]
    measurements, check_ins = _latest_measurements(session, "KR", ids), _latest_check_ins(session, ids)
    by_objective: dict[uuid.UUID, list[KeyResult]] = {}
    for k in krs:
        by_objective.setdefault(k.objective_id, []).append(_kr(k, measurements, check_ins))
    return [
        Objective(o.id, o.title, o.owner_user_id, o.period_label, o.org_unit_id, o.parent_id, o.status, o.version,
                  by_objective.get(o.id, []))
        for o in objectives
    ]  # fmt: skip


def list_kpis(session: Session, actor: Actor, *, status: str | None = None) -> list[Kpi]:
    """API-GOAL-02: KPI trong phạm vi và giá trị đo gần nhất."""
    conditions = [
        or_(
            scope_filter(actor, READ, owner=KpiRow.owner_user_id.expression, org_unit=KpiRow.org_unit_id.expression),
            KpiRow.created_by == actor.user_id,
        )
    ]
    if status is not None:
        conditions.append(KpiRow.status == status)
    rows = list(session.scalars(select(KpiRow).where(and_(*conditions)).order_by(KpiRow.created_at)))
    measurements = _latest_measurements(session, "KPI", [r.id for r in rows])
    return [
        Kpi(r.id, r.metric, r.baseline, r.target, r.unit, r.owner_user_id, r.period_label, r.org_unit_id, r.status,
            r.version, measurements.get(r.id))
        for r in rows
    ]  # fmt: skip


# ---------- Tải một đối tượng (kiểm phạm vi) ----------


def _objective(session: Session, actor: Actor, objective_id: uuid.UUID, *, lock: bool = False) -> ObjectiveRow:
    query = select(ObjectiveRow).where(ObjectiveRow.id == objective_id, _objective_filter(actor))
    row = session.scalars(query.with_for_update(of=ObjectiveRow) if lock else query).one_or_none()
    if row is None:
        raise ApiError("NOT_FOUND")
    return row


def _key_result(session: Session, actor: Actor, kr_id: uuid.UUID, *, lock: bool = False) -> KeyResultRow:
    query = select(KeyResultRow).where(KeyResultRow.id == kr_id)
    row = session.scalars(query.with_for_update(of=KeyResultRow) if lock else query).one_or_none()
    if row is None:
        raise ApiError("NOT_FOUND")
    if row.owner_user_id != actor.user_id and row.created_by != actor.user_id:
        _objective(session, actor, row.objective_id)  # KR theo phạm vi Objective cha → 404 nếu ngoài phạm vi
    return row


def _kpi(session: Session, actor: Actor, kpi_id: uuid.UUID, *, lock: bool = False) -> KpiRow:
    query = select(KpiRow).where(KpiRow.id == kpi_id)
    row = session.scalars(query.with_for_update(of=KpiRow) if lock else query).one_or_none()
    if row is None:
        raise ApiError("NOT_FOUND")
    if actor.user_id not in (row.owner_user_id, row.created_by) and not _allowed(
        session, actor, READ, row.owner_user_id, row.org_unit_id
    ):
        raise ApiError("NOT_FOUND")
    return row


def get_objective(session: Session, actor: Actor, objective_id: uuid.UUID) -> Objective:
    _objective(session, actor, objective_id)
    found = [o for o in list_objectives(session, actor) if o.id == objective_id]
    return found[0]


def get_key_result(session: Session, actor: Actor, kr_id: uuid.UUID) -> KeyResult:
    row = _key_result(session, actor, kr_id)
    return _kr(row, _latest_measurements(session, "KR", [row.id]), _latest_check_ins(session, [row.id]))


def get_kpi(session: Session, actor: Actor, kpi_id: uuid.UUID) -> Kpi:
    r = _kpi(session, actor, kpi_id)
    m = _latest_measurements(session, "KPI", [r.id])
    return Kpi(r.id, r.metric, r.baseline, r.target, r.unit, r.owner_user_id, r.period_label, r.org_unit_id, r.status,
               r.version, m.get(r.id))  # fmt: skip


# ---------- Tạo / sửa bản nháp ----------


def find_by_key(session: Session, actor: Actor, kind: str, key: str) -> tuple[str, Any] | None:
    model: Any = {"objective": ObjectiveRow, "key_result": KeyResultRow, "kpi": KpiRow}[kind]
    row = session.execute(
        select(model.id, model.request_hash).where(model.created_by == actor.user_id, model.idempotency_key == key)
    ).one_or_none()
    if row is None or row.request_hash is None:
        return None
    loader = {"objective": get_objective, "key_result": get_key_result, "kpi": get_kpi}[kind]
    return row.request_hash, loader(session, actor, row.id)


def create_objective(session: Session, actor: Actor, data: dict[str, Any], *, key: str, request_hash: str) -> Objective:
    _check_owner(session, actor, data["owner_user_id"], data.get("org_unit_id"))
    if data.get("parent_id") is not None:
        _objective(session, actor, data["parent_id"])
    row = ObjectiveRow(
        id=uuid.uuid4(), created_by=actor.user_id, idempotency_key=key, request_hash=request_hash, **data
    )
    session.add(row)
    session.flush()
    _audit(session, actor.user_id, "goals.objective.create", "objective", row.id)
    return get_objective(session, actor, row.id)


def create_key_result(
    session: Session, actor: Actor, data: dict[str, Any], *, key: str, request_hash: str
) -> KeyResult:
    objective = _objective(session, actor, data["objective_id"])
    _check_owner(session, actor, data["owner_user_id"], objective.org_unit_id)
    row = KeyResultRow(
        id=uuid.uuid4(), created_by=actor.user_id, idempotency_key=key, request_hash=request_hash, **data
    )
    session.add(row)
    session.flush()
    _audit(session, actor.user_id, "goals.key_result.create", "key_result", row.id)
    return get_key_result(session, actor, row.id)


def create_kpi(session: Session, actor: Actor, data: dict[str, Any], *, key: str, request_hash: str) -> Kpi:
    _check_owner(session, actor, data["owner_user_id"], data.get("org_unit_id"))
    row = KpiRow(id=uuid.uuid4(), created_by=actor.user_id, idempotency_key=key, request_hash=request_hash, **data)
    session.add(row)
    session.flush()
    _audit(session, actor.user_id, "goals.kpi.create", "kpi", row.id)
    return get_kpi(session, actor, row.id)


def update_draft(
    session: Session, actor: Actor, kind: str, item_id: uuid.UUID, changes: dict[str, Any], *, expected_version: int
) -> Any:
    """API-GOAL-03 (PATCH): chỉ bản `DRAFT`; người tạo hoặc owner; `If-Match`."""
    loader: Any = {"objective": _objective, "key_result": _key_result, "kpi": _kpi}[kind]
    row = loader(session, actor, item_id, lock=True)
    if actor.user_id not in (row.created_by, row.owner_user_id):
        raise ApiError("FORBIDDEN")
    check_version(row.version, expected_version)
    if row.status != "DRAFT":
        raise ApiError("INVALID_STATE", "Chỉ sửa được bản nháp")
    if "owner_user_id" in changes:
        unit = changes.get("org_unit_id", getattr(row, "org_unit_id", None))
        if kind == "key_result":
            unit = _objective(session, actor, row.objective_id).org_unit_id
        _check_owner(session, actor, changes["owner_user_id"], unit)
    if kind == "objective" and changes.get("parent_id") is not None:
        _objective(session, actor, changes["parent_id"])
    model: Any = type(row)
    if changes:
        session.execute(
            update(model)
            .where(model.id == item_id)
            .values(**changes, version=model.version + 1, updated_at=func.now())
            .execution_options(synchronize_session="fetch")
        )
        _audit(session, actor.user_id, f"goals.{kind}.update", kind, item_id)
    session.expire_all()
    getter: Any = {"objective": get_objective, "key_result": get_key_result, "kpi": get_kpi}[kind]
    return getter(session, actor, item_id)


# ---------- Check-in, đo lường ----------


def find_check_in(session: Session, actor: Actor, key: str) -> tuple[str, Any] | None:
    row = session.scalars(
        select(CheckInRow).where(CheckInRow.submitted_by == actor.user_id, CheckInRow.idempotency_key == key)
    ).one_or_none()
    if row is None or row.request_hash is None:
        return None
    return row.request_hash, CheckIn(row.value, row.confidence, row.blocker, row.submitted_by, row.created_at)


def check_in(
    session: Session, actor: Actor, kr_id: uuid.UUID, *, value: Decimal, confidence: int, blocker: str | None,
    key: str, request_hash: str,
) -> CheckIn:  # fmt: skip
    kr = _key_result(session, actor, kr_id)
    if kr.owner_user_id != actor.user_id:
        raise ApiError("FORBIDDEN", "Chỉ owner KR check-in")
    row = CheckInRow(
        id=uuid.uuid4(), key_result_id=kr_id, value=value, confidence=confidence, blocker=blocker or None,
        submitted_by=actor.user_id, idempotency_key=key, request_hash=request_hash,
    )  # fmt: skip
    session.add(row)
    session.flush()
    _audit(session, actor.user_id, "goals.check_in.create", "key_result", kr_id)
    return CheckIn(row.value, row.confidence, row.blocker, row.submitted_by, row.created_at)


def find_measurement(session: Session, actor: Actor, key: str) -> tuple[str, Any] | None:
    row = session.scalars(
        select(MeasurementRow).where(MeasurementRow.recorded_by == actor.user_id, MeasurementRow.idempotency_key == key)
    ).one_or_none()
    if row is None or row.request_hash is None:
        return None
    return row.request_hash, Measurement(
        row.value, row.report_period_label, row.source_document_id, row.recorded_by, row.created_at
    )


def record_measurement(
    session: Session, actor: Actor, kind: str, target_id: uuid.UUID, *, value: Decimal, report_period_label: str,
    source_document_id: uuid.UUID | None, key: str, request_hash: str,
) -> Measurement:  # fmt: skip
    if kind == "KR":
        kr = _key_result(session, actor, target_id)
        unit = _objective(session, actor, kr.objective_id).org_unit_id
        owner = kr.owner_user_id
    else:
        kpi = _kpi(session, actor, target_id)
        unit, owner = kpi.org_unit_id, kpi.owner_user_id
    if owner != actor.user_id and not _allowed(session, actor, WRITE, owner, unit):
        raise ApiError("FORBIDDEN")
    if source_document_id is not None and not document_exists(session, source_document_id):
        raise ApiError(
            "VALIDATION_ERROR", errors=[{"field": "source_document_id", "message": "Tài liệu không tồn tại"}]
        )
    row = MeasurementRow(
        id=uuid.uuid4(), target_type=kind, target_id=target_id, value=value, report_period_label=report_period_label,
        recorded_by=actor.user_id, source_document_id=source_document_id, idempotency_key=key,
        request_hash=request_hash,
    )  # fmt: skip
    session.add(row)
    session.flush()
    _audit(session, actor.user_id, "goals.measurement.create", "key_result" if kind == "KR" else "kpi", target_id)
    return Measurement(row.value, row.report_period_label, row.source_document_id, row.recorded_by, row.created_at)
