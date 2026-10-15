"""Interface công khai của `finance` (Architecture §3 quy tắc 1).

T-401: bảng `finance.*` + bất biến INV-01…07 ở CSDL (migration 0012). Kỳ báo cáo: T-402; giao dịch: T-403…T-406.
"""

import aieos.finance.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)

__all__: list[str] = []
