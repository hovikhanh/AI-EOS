"""Interface công khai của `access` (ADR-007, Architecture §3 quy tắc 1).

T-107: bảng, seed role/permission, bất biến INV-09/10/11 ở CSDL và service ghi role/assignment. Policy
`authorize()` thuộc T-108; API quản trị thuộc T-109.
"""

from aieos.access.service import (
    ScopeType,
    create_assignment,
    effective_permissions,
    grant_role,
    known_roles,
    revoke_assignment,
    revoke_role,
    roles_of,
)

__all__ = [
    "ScopeType",
    "create_assignment",
    "effective_permissions",
    "grant_role",
    "known_roles",
    "revoke_assignment",
    "revoke_role",
    "roles_of",
]
