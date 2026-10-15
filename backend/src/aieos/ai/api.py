"""Interface công khai của `ai` (Architecture §3 quy tắc 1).

T-301: bảng `ai.*`, seed Tool Registry, trần autonomy (INV-12), kill switch singleton (INV-13) — migration 0013. Write
gateway: T-302; kill switch API: T-303; bản nháp: T-304.
"""

import aieos.ai.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)

__all__: list[str] = []
