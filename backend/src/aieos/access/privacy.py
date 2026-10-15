"""Che dữ liệu cá nhân theo quyền (T-112, SRS-ACC-10, R6, D-21, FL-13).

`pii.unmask` mặc định không ai giữ (migration 0005, D-21) → mọi người đọc đều thấy bản che. Nơi trả dữ liệu ra ngoài
(API, file xuất, câu trả lời AI) gọi `mask_for`/`mask_fields` trước khi trả; phát hiện theo quy tắc ở `platform.api`.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from aieos.access.policy import Actor, Resource, authorize
from aieos.platform.api import PII_MASK, mask_pii

UNMASK = "pii.unmask"


def can_unmask(actor: Actor, resource: Resource | None = None) -> bool:
    return authorize(actor, UNMASK, resource).allowed


def mask_for(actor: Actor, text: str, resource: Resource | None = None) -> str:
    """Văn bản tự do (trích dẫn tài liệu, câu trả lời AI…): che đoạn dữ liệu cá nhân phát hiện được."""
    return text if can_unmask(actor, resource) else mask_pii(text)


def mask_fields(
    actor: Actor,
    data: Mapping[str, Any],
    sensitive: Iterable[str] = (),
    resource: Resource | None = None,
) -> dict[str, Any]:
    """Bản ghi trả ra ngoài: trường khai báo nhạy cảm → `•••` cả giá trị; chuỗi khác → che đoạn phát hiện được."""
    if can_unmask(actor, resource):
        return dict(data)
    names = {name.lower() for name in sensitive}

    def walk(key: str | None, value: Any) -> Any:
        if key is not None and key.lower() in names and value is not None:
            return PII_MASK
        if isinstance(value, str):
            return mask_pii(value)
        if isinstance(value, Mapping):
            return {str(k): walk(str(k), v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [walk(None, v) for v in value]
        return value

    return {str(k): walk(str(k), v) for k, v in data.items()}
