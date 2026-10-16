"""Interface công khai của `ai` (Architecture §3 quy tắc 1).

T-301: bảng `ai.*`, seed Tool Registry, trần autonomy (INV-12), kill switch singleton (INV-13) — migration 0013. Write
gateway: T-302; kill switch API: T-303; bản nháp: T-304. T-204: `DbCallRecorder` (call log, chi phí trong kỳ ngân sách).
"""

import aieos.ai.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.ai.call_log import DbCallRecorder
from aieos.ai.router import build_ai_admin_router  # T-305: API-AI-03, API-AI-04, API-AI-05

__all__ = ["DbCallRecorder", "build_ai_admin_router"]
