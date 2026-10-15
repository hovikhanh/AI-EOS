"""Interface công khai của `capture` (Architecture §3 quy tắc 1).

T-202: bảng `capture.*` (migration 0014). Upload + quét mã độc: T-203; trích xuất: T-206; review: T-208/T-209;
import: T-210.
"""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from aieos.capture.models import SourceDocumentRow


def document_exists(session: Session, document_id: uuid.UUID) -> bool:
    """Tài liệu nguồn có tồn tại (module ghi `source_document_id` kiểm trước để trả 422 thay vì lỗi khóa ngoại)."""
    return bool(session.scalar(select(exists().where(SourceDocumentRow.id == document_id))))


__all__ = ["document_exists"]
