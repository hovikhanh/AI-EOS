"""Ghi `ai.call_log` và tính chi phí đã dùng cho trần ngân sách (T-204, ADR-011, SRS-PRV-04).

Mỗi lời gọi ghi trong transaction riêng: call log còn lại kể cả khi nghiệp vụ gọi provider bị rollback (chi phí đã
phát sinh). Kỳ ngân sách: tháng dương lịch theo giờ Việt Nam — `[CẦN XÁC NHẬN]` (GAP-14 chỉ quyết giá trị là cấu hình).
"""

from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from aieos.ai.models import CallLogRow
from aieos.platform.api import transaction
from aieos.providers.api import CallRecord

_MONTH_START = text("date_trunc('month', now() AT TIME ZONE 'Asia/Ho_Chi_Minh') AT TIME ZONE 'Asia/Ho_Chi_Minh'")


class DbCallRecorder:
    """`providers.api.CallRecorder` lưu vào `ai.call_log`."""

    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    def record(self, call: CallRecord) -> None:
        with transaction(self._factory) as session:
            session.add(
                CallLogRow(
                    provider=call.provider,
                    model=call.model,
                    purpose=call.purpose,
                    data_classification=call.data_classification.value,
                    provider_is_local=call.provider_is_local,
                    tokens_in=call.tokens_in,
                    tokens_out=call.tokens_out,
                    pages=call.pages,
                    latency_ms=call.latency_ms,
                    cost_estimate=call.cost_estimate,
                    outcome=call.outcome,
                    job_id=call.job_id,
                    correlation_id=call.correlation_id,
                )
            )

    def spent(self) -> Decimal:
        with transaction(self._factory) as session:
            total = session.scalar(
                select(func.coalesce(func.sum(CallLogRow.cost_estimate), 0)).where(
                    CallLogRow.created_at >= _MONTH_START
                )
            )
        return total if total is not None else Decimal(0)
