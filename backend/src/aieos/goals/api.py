"""Interface công khai của `goals` (Architecture §3 quy tắc 1).

T-501: bảng (migration 0015), Objective/KR/KPI bản nháp, đo lường, check-in, danh sách theo phạm vi (API-GOAL-01/02/03/
05/06). Kích hoạt (API-GOAL-04): T-502.
"""

import aieos.goals.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.goals.router import build_goals_router
from aieos.goals.service import list_kpis, list_objectives

__all__ = ["build_goals_router", "list_kpis", "list_objectives"]
