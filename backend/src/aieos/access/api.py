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
from aieos.access.router import build_access_admin_router
from aieos.access.service import (
    Assignment,
    ScopeType,
    active_admins,
    create_assignment,
    effective_permissions,
    find_assignment_by_key,
    get_assignment,
    grant_role,
    known_roles,
    list_assignments,
    revoke_assignment,
    revoke_role,
    role_catalog,
    roles_of,
    set_roles,
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
    "build_access_admin_router",
    "load_actor",
    "require",
    "scope_filter",
    "Assignment",
    "ScopeType",
    "active_admins",
    "create_assignment",
    "effective_permissions",
    "find_assignment_by_key",
    "get_assignment",
    "list_assignments",
    "role_catalog",
    "set_roles",
    "grant_role",
    "known_roles",
    "revoke_assignment",
    "revoke_role",
    "roles_of",
]
