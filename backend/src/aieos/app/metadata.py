"""Gom metadata model của mọi module (composition root, D-42) cho lệnh migration và so khớp model ↔ schema (TC-MIG-01).

`platform` không import module khác (C5) nên không tự biết model; nạp `<module>.api` ở đây để model đăng ký vào
`Base.metadata`. Thêm module mới có bảng vào `MODULE_APIS`.
"""

from types import ModuleType

from sqlalchemy import MetaData

import aieos.access.api
import aieos.audit.api
import aieos.identity.api
import aieos.jobs.api
from aieos.platform.api import Base

MODULE_APIS: tuple[ModuleType, ...] = (aieos.access.api, aieos.audit.api, aieos.identity.api, aieos.jobs.api)


def metadata() -> MetaData:
    return Base.metadata
