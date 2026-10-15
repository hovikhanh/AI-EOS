"""Interface công khai của `capture` (Architecture §3 quy tắc 1).

T-202: bảng `capture.*` (migration 0014). Upload + quét mã độc: T-203; trích xuất: T-206; review: T-208/T-209;
import: T-210.
"""

import aieos.capture.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)

__all__: list[str] = []
