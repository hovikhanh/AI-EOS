"""Interface công khai của `audit` (ADR-010, Architecture §3 quy tắc 1, 4).

Module khác ghi audit qua `record(...)` trong transaction hiện hành, hoặc `record_separately(...)` cho thao tác bị
từ chối/thất bại. Không có hàm sửa hay xóa audit. Đọc audit (SRS-AUD-04) thuộc T-110.
"""

from aieos.audit.recorder import (
    ActorType,
    AuditEvent,
    AuditEventError,
    AutonomyLevel,
    Category,
    Outcome,
    audit_row_values,
    mask_changes,
    record,
    record_separately,
)

__all__ = [
    "ActorType",
    "AuditEvent",
    "AuditEventError",
    "AutonomyLevel",
    "Category",
    "Outcome",
    "audit_row_values",
    "mask_changes",
    "record",
    "record_separately",
]
