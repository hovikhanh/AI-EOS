"""Adapter giả lập cho test và CI (ADR-011 Amendment 1: CI không gọi provider thật).

Mỗi lời gọi lấy phần tử kế tiếp của kịch bản: kết quả thì trả về, ngoại lệ thì ném ra; hết kịch bản → lặp phần tử cuối.
"""

from collections.abc import Sequence

from aieos.providers.base import ConvertedDocument, LLMRequest, LLMResult, OCRRequest, OCRResult


class _Script[T]:
    def __init__(self, script: Sequence[T | Exception]) -> None:
        if not script:
            raise ValueError("kịch bản rỗng")
        self._script = list(script)
        self.calls: list[float] = []  # timeout nhận được ở mỗi lời gọi

    def _next(self, timeout: float) -> T:
        item = self._script[min(len(self.calls), len(self._script) - 1)]
        self.calls.append(timeout)
        if isinstance(item, Exception):
            raise item
        return item


class FakeLLM(_Script[LLMResult]):
    def complete(self, request: LLMRequest, *, timeout: float) -> LLMResult:
        return self._next(timeout)


class FakeOCR(_Script[OCRResult]):
    def recognize(self, request: OCRRequest, *, timeout: float) -> OCRResult:
        return self._next(timeout)


class FakeConverter:
    """Trả nguyên nội dung với kiểu đích cố định."""

    def __init__(self, media_type: str = "application/pdf") -> None:
        self.media_type = media_type

    def convert(self, content: bytes, media_type: str) -> ConvertedDocument:
        return ConvertedDocument(content, self.media_type)
