"""Gom metadata model của mọi module (composition root, D-42) cho lệnh migration và so khớp model ↔ schema (TC-MIG-01).

`platform` không import module khác (C5) nên không tự biết model; nạp `<module>.api` ở đây để model đăng ký vào
`Base.metadata`. Thêm module mới có bảng vào `MODULE_APIS`. `app.asgi`, `app.worker` import module này: model có khóa
ngoại tới bảng của module khác (vd. `source_document_id` → `capture`) cần bảng đích đã đăng ký khi ghi (T-501).
"""

from types import ModuleType

from sqlalchemy import MetaData

import aieos.access.api
import aieos.ai.api
import aieos.audit.api
import aieos.capture.api
import aieos.finance.api
import aieos.goals.api
import aieos.identity.api
import aieos.jobs.api
import aieos.notify.api
import aieos.org.api
import aieos.work.api
from aieos.platform.api import Base

MODULE_APIS: tuple[ModuleType, ...] = (
    aieos.access.api,
    aieos.ai.api,
    aieos.audit.api,
    aieos.capture.api,
    aieos.finance.api,
    aieos.goals.api,
    aieos.identity.api,
    aieos.jobs.api,
    aieos.notify.api,
    aieos.org.api,
    aieos.work.api,
)


def metadata() -> MetaData:
    return Base.metadata
