"""Interface công khai của `org` (Architecture §3 quy tắc 1).

T-201: bảng `org.*` (migration 0010), danh bạ + cây đơn vị (API-ORG-01/02), `OrgDirectoryScope` cho phạm vi MANAGER
(`access.api.OrgScope`, T-108), hàm ghi cho import nhân sự (T-210).
"""

import aieos.org.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.org.router import build_org_router
from aieos.org.service import (
    DirectoryEntry,
    OrgDirectoryScope,
    Unit,
    create_employee,
    create_unit,
    list_directory,
    list_units,
    set_head,
    set_parent,
    subtree,
)

__all__ = [
    "DirectoryEntry",
    "OrgDirectoryScope",
    "Unit",
    "build_org_router",
    "create_employee",
    "create_unit",
    "list_directory",
    "list_units",
    "set_head",
    "set_parent",
    "subtree",
]
