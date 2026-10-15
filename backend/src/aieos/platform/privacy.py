"""Phát hiện và che dữ liệu cá nhân trong văn bản bằng quy tắc (T-112, SEC-DC-02, SRS-ACC-10, SRS-PRV-02).

Hàm thuần, không nghiệp vụ, đặt cạnh `redact` (T-006): `redact` che theo **tên khóa**, module này che theo **nội dung**.
Quyết định ai được bỏ che (`pii.unmask` — hiện không ai giữ, D-21) thuộc `access`.

Quy tắc và nhãn là `PROPOSED` của agent (Q-55): định danh (CCCD/CMND, số điện thoại, email) → `PERSONAL`; số tài khoản
ngân hàng, lương → `SENSITIVE` (theo cách Nghị định 13/2023 xếp thông tin tài khoản ngân hàng là dữ liệu nhạy cảm).
Hai nhãn được định tuyến và che như nhau (chỉ provider local; luôn che) nên khác biệt chỉ để báo cáo.
Quy tắc ưu tiên bắt thừa hơn bỏ sót; số thường (tiền, mã) không có từ khóa đi kèm không bị che, trừ dạng CCCD 12 số.
"""

import re
from dataclasses import dataclass
from typing import Literal

Sensitivity = Literal["NORMAL", "PERSONAL", "SENSITIVE"]
MASK = "•••"  # FL-13: trường nhạy cảm hiển thị dạng che

_RANK: dict[Sensitivity, int] = {"NORMAL": 0, "PERSONAL": 1, "SENSITIVE": 2}
_EDGE_L = r"(?<![\w\-./])"
_EDGE_R = r"(?![\w\-/]|\.\d)"
_DIGITS = r"\d[\d .\-]{4,22}\d"  # số có thể có khoảng trắng, chấm, gạch
_KEY_SEP = r"[\s:.#=\-]*"


@dataclass(frozen=True)
class Rule:
    kind: str
    sensitivity: Sensitivity
    pattern: re.Pattern[str]


def _keyed(words: str, value: str) -> re.Pattern[str]:
    """Giá trị đi sau từ khóa; nhóm `v` là phần bị che (giữ nguyên từ khóa để người đọc biết trường gì)."""
    return re.compile(rf"(?<!\w)(?:{words}){_KEY_SEP}(?P<v>{value})", re.IGNORECASE)


RULES: tuple[Rule, ...] = (
    Rule(
        "BANK_ACCOUNT",
        "SENSITIVE",
        _keyed(
            r"số\s+tài\s+khoản|stk|tài\s+khoản\s+(?:số|ngân\s+hàng)|tk\s+ngân\s+hàng|account\s+(?:no|number)", _DIGITS
        ),
    ),
    Rule("SALARY", "SENSITIVE", _keyed(r"(?:mức\s+)?lương(?:\s+(?:cơ\s+bản|tháng|gross|net))?|salary", _DIGITS)),
    Rule(
        "NATIONAL_ID", "PERSONAL", _keyed(r"cccd|cmnd|căn\s+cước(?:\s+công\s+dân)?|chứng\s+minh\s+nhân\s+dân", _DIGITS)
    ),
    Rule("NATIONAL_ID", "PERSONAL", re.compile(rf"{_EDGE_L}(?P<v>0\d{{11}}){_EDGE_R}")),  # CCCD 12 số, mã tỉnh 0xx
    Rule(
        "PHONE",
        "PERSONAL",
        re.compile(rf"{_EDGE_L}(?P<v>(?:\+84|0)[ .\-]?[35789](?:[ .\-]?\d){{8}}){_EDGE_R}"),
    ),
    Rule("EMAIL", "PERSONAL", re.compile(r"(?<![\w.+-])(?P<v>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)", re.UNICODE)),
)


@dataclass(frozen=True)
class PiiMatch:
    kind: str
    sensitivity: Sensitivity
    start: int
    end: int


def find_pii(text: str) -> list[PiiMatch]:
    """Các đoạn dữ liệu cá nhân, không chồng nhau, theo thứ tự xuất hiện (quy tắc đứng trước thắng khi chồng)."""
    found: list[PiiMatch] = []
    for rule in RULES:
        for match in rule.pattern.finditer(text):
            start, end = match.span("v")
            if any(start < m.end and m.start < end for m in found):
                continue
            found.append(PiiMatch(rule.kind, rule.sensitivity, start, end))
    return sorted(found, key=lambda m: m.start)


def classify_text(text: str, floor: Sensitivity = "NORMAL") -> Sensitivity:
    """Nhãn `sensitivity` cao nhất trong văn bản, không thấp hơn `floor` (nhãn đã biết từ nguồn)."""
    level = floor
    for match in find_pii(text):
        if _RANK[match.sensitivity] > _RANK[level]:
            level = match.sensitivity
    return level


def mask_pii(text: str) -> str:
    """Thay mọi đoạn dữ liệu cá nhân bằng `•••`; phần còn lại giữ nguyên."""
    out: list[str] = []
    cursor = 0
    for match in find_pii(text):
        out.append(text[cursor : match.start])
        out.append(MASK)
        cursor = match.end
    out.append(text[cursor:])
    return "".join(out)
