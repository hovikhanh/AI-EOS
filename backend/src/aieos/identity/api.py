"""Interface công khai của `identity` (ADR-006, Architecture §3 quy tắc 1).

T-101 chỉ dựng bảng `identity.*` và hàm băm token (INV-16). Đăng nhập, session, MFA, lời mời: T-102…T-106.
"""

import aieos.identity.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.identity.tokens import TOKEN_BYTES, hash_email, hash_token, new_token, token_matches

__all__ = ["TOKEN_BYTES", "hash_email", "hash_token", "new_token", "token_matches"]
