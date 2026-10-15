"""Interface công khai của `access` (ADR-007, Architecture §3 quy tắc 1).

T-107: bảng, seed role/permission, bất biến INV-09/10/11 ở CSDL và service ghi role/assignment. T-108: policy
`authorize()`, `require()`, `scope_filter()`, `PermissionGuard` (`policy.py`). API quản trị thuộc T-109.
"""

from aieos.access.policy import (
    ALLOW,
    FINANCE,
    NO_ORG,
    Actor,
    Decision,
    Grant,
    OrgScope,
    PermissionGuard,
    Resource,
    authorize,
    load_actor,
    require,
    scope_filter,
)
from aieos.access.service import (
    ScopeType,
    active_admins,
    create_assignment,
    effective_permissions,
    grant_role,
    known_roles,
    revoke_assignment,
    revoke_role,
    roles_of,
)

__all__ = [
    "ALLOW",
    "FINANCE",
    "NO_ORG",
    "Actor",
    "Decision",
    "Grant",
    "OrgScope",
    "PermissionGuard",
    "Resource",
    "authorize",
    "load_actor",
    "require",
    "scope_filter",
    "ScopeType",
    "active_admins",
    "create_assignment",
    "effective_permissions",
    "grant_role",
    "known_roles",
    "revoke_assignment",
    "revoke_role",
    "roles_of",
]
