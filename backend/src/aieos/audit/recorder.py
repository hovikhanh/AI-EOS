"""Ghi audit append-only (T-008, ADR-010, SRS-AUD-01, SRS-AUD-02, Architecture §3 quy tắc 4).

- `record(session, event)`: ghi trong transaction hiện hành của nơi gọi — thao tác không commit thì audit cũng không
  tồn tại.
- `record_separately(factory, event)`: ghi trong transaction riêng, dùng cho thao tác bị từ chối/thất bại (`DENIED`,
  `FAILED`, `BLOCKED`) mà transaction chính bị rollback (ADR-010).
- `changes` (giá trị trước/sau) được che trước khi ghi: khóa có tên nhạy cảm (mật khẩu, token, secret, CSRF, khóa API,
  mã OTP/MFA, session, credential, tên biến secret — cùng quy tắc với log của T-006) và các trường nơi gọi khai báo
  trong `masked_fields` (trường nhạy cảm theo nghiệp vụ, SEC-DC-02) bị thay bằng `***`; trong chuỗi còn lại, đoạn dữ
  liệu cá nhân phát hiện theo quy tắc (CCCD, số tài khoản, điện thoại, email…) bị thay bằng `•••` (T-112).
- Trường văn bản tự do khác — `reason` (người dùng nhập), `user_agent` (client gửi), `resource_id` — cũng được che
  theo nội dung trước khi ghi (Q-55, quyết định CDA 16/10/2026). Mã hệ thống (`action`, `resource_type`, `ai_agent`),
  ID dạng UUID và `correlation_id` (đã kiểm định dạng ở `platform.web`) không bị đổi, nên truy vết nghiệp vụ giữ nguyên.
- Không có hàm sửa hay xóa audit; CSDL cũng chặn (INV-14, migration 0002).
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session, sessionmaker

from aieos.audit.models import AuditEventRow
from aieos.platform.api import CORRELATION_ID, REDACTED, mask_pii, redact, transaction


class Category(StrEnum):
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"
    BUSINESS = "BUSINESS"
    AI = "AI"


class ActorType(StrEnum):
    USER = "USER"
    AI = "AI"
    SYSTEM = "SYSTEM"
    BOOTSTRAP = "BOOTSTRAP"


class Outcome(StrEnum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AutonomyLevel(StrEnum):
    """Mức tự chủ của hành động AI; L4 không thuộc MVP (D-11)."""

    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class AuditEventError(ValueError):
    """Sự kiện audit không hợp lệ."""


@dataclass(frozen=True, kw_only=True)
class AuditEvent:
    """Một sự kiện audit (Database_Design §9). `changes` chưa che; `record` che trước khi ghi."""

    category: Category
    actor_type: ActorType
    action: str
    outcome: Outcome
    actor_user_id: uuid.UUID | None = None
    on_behalf_of_user_id: uuid.UUID | None = None
    ai_agent: str | None = None
    autonomy_level: AutonomyLevel | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    reason: str | None = None
    changes: Mapping[str, Any] | None = None
    masked_fields: frozenset[str] = field(default_factory=frozenset)
    correlation_id: str | None = None
    request_ip: str | None = None
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if not self.action.strip():
            raise AuditEventError("action không được rỗng")
        if self.actor_type is not ActorType.AI and (self.ai_agent is not None or self.autonomy_level is not None):
            raise AuditEventError("ai_agent, autonomy_level chỉ dùng cho actor_type AI")
        if self.changes is not None and not isinstance(self.changes, Mapping):
            raise AuditEventError("changes phải là mapping")


def mask_changes(changes: Mapping[str, Any] | None, masked_fields: frozenset[str] = frozenset()) -> Any:
    """Bản sao `changes` an toàn để lưu: che khóa nhạy cảm (quy tắc log T-006) và khóa trong `masked_fields`."""
    if changes is None:
        return None
    fields = {name.lower() for name in masked_fields}

    def walk(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(k): REDACTED if str(k).lower() in fields else walk(v) for k, v in value.items()}
        if isinstance(value, list | tuple | set | frozenset):
            return [walk(v) for v in value]
        return mask_pii(value) if isinstance(value, str) else value

    return redact(walk(changes))


def _masked(value: str | None) -> str | None:
    return mask_pii(value) if value is not None else None


def audit_row_values(event: AuditEvent) -> dict[str, Any]:
    """Giá trị cột sẽ ghi cho `event`, đã che (hàm thuần — `record` dùng, test kiểm không cần CSDL)."""
    return {
        "category": event.category.value,
        "actor_type": event.actor_type.value,
        "actor_user_id": event.actor_user_id,
        "on_behalf_of_user_id": event.on_behalf_of_user_id,
        "ai_agent": event.ai_agent,
        "autonomy_level": event.autonomy_level.value if event.autonomy_level else None,
        "action": event.action,
        "resource_type": event.resource_type,
        "resource_id": _masked(event.resource_id),
        "outcome": event.outcome.value,
        "reason": _masked(event.reason),
        "changes": mask_changes(event.changes, event.masked_fields),
        "correlation_id": event.correlation_id if event.correlation_id is not None else CORRELATION_ID.get(),
        "request_ip": event.request_ip,
        "user_agent": _masked(event.user_agent),
    }


def record(session: Session, event: AuditEvent) -> int:
    """Ghi sự kiện trong transaction hiện hành của `session`; trả về `id`. Không commit."""
    values = audit_row_values(event)
    return session.execute(insert(AuditEventRow).values(**values).returning(AuditEventRow.id)).scalar_one()


def record_separately(factory: sessionmaker[Session], event: AuditEvent) -> int:
    """Ghi sự kiện trong transaction riêng và commit ngay (thao tác chính bị từ chối/rollback — ADR-010)."""
    with transaction(factory) as session:
        return record(session, event)
