"""Phát hiện và che dữ liệu cá nhân trong văn bản bằng quy tắc (T-112, SEC-DC-02, SRS-ACC-10, SRS-PRV-02).

Hàm thuần, không nghiệp vụ, đặt cạnh `redact` (T-006): `redact` che theo **tên khóa**, module này che theo **nội dung**.
Quyết định ai được bỏ che (`pii.unmask` — hiện không ai giữ, D-21) thuộc `access`.

Danh mục ban đầu (quyết định CDA 16/10/2026 cho Q-55): CCCD/CMND, số điện thoại, email → `PERSONAL`; số tài khoản ngân
hàng, lương → `SENSITIVE`. Hai nhãn được định tuyến và che như nhau (chỉ provider local; luôn che). Thêm loại = thêm
`Rule`, không đổi interface.

Đây là heuristic theo quy tắc, **không** nhận diện được mọi dữ liệu cá nhân. Số thường (tiền, mã, ngày) không bị
che trừ khi có từ khóa/ngữ cảnh đi kèm hoặc có dạng riêng (CCCD 12 số bắt đầu bằng 0, số điện thoại Việt Nam). Chuỗi
số chấp nhận một dấu phân cách (khoảng trắng, chấm, gạch, xuống dòng) giữa hai chữ số để bắt giá trị bị tách hoặc
ngắt dòng.
"""

import re
from dataclasses import dataclass
from typing import Literal

Sensitivity = Literal["NORMAL", "PERSONAL", "SENSITIVE"]
MASK = "•••"  # FL-13: trường nhạy cảm hiển thị dạng che

_RANK: dict[Sensitivity, int] = {"NORMAL": 0, "PERSONAL": 1, "SENSITIVE": 2}
_EDGE_L = r"(?<![\w\-./])"
_EDGE_R = r"(?![\w\-/]|\.\d)"
_SEP = r"(?:[ .\-]|\r?\n)?"  # tối đa một dấu phân cách giữa hai chữ số


def _seq(low: int, high: int) -> str:
    """Dãy từ `low` tới `high` chữ số, mỗi chỗ nối có thể có một dấu phân cách; không dừng giữa một dãy số dài hơn."""
    return rf"\d(?:{_SEP}\d){{{low - 1},{high - 1}}}(?!{_SEP}\d)"


def _after_keyword(low: int) -> str:
    """Sau từ khóa: lấy tham lam tới 24 chữ số — che thừa số đứng liền sau hơn là để lộ phần đuôi."""
    return rf"\d(?:{_SEP}\d){{{low - 1},23}}"


_MONEY_UNIT = r"(?:triệu|tr|nghìn|ngàn|k|tỷ|đồng|đ|vnđ|vnd|usd)(?!\w)"
_BANKS = (
    r"vietcombank|vcb|techcombank|tcb|bidv|agribank|vietinbank|mb\s*bank|acb|sacombank|vpbank|tpbank|shb|hdbank|vib|"
    r"ocb|msb|seabank|eximbank|lpbank|lienvietpostbank|nam\s+a\s*bank|bac\s+a\s*bank|abbank|kienlongbank|scb|"
    r"pvcombank|baovietbank|vietbank|ngân\s+hàng|bank"
)
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
    # Có từ khóa đứng trước (thứ tự = ưu tiên khi chồng nhau).
    Rule(
        "BANK_ACCOUNT",
        "SENSITIVE",
        _keyed(
            r"số\s+tài\s+khoản|stk|tài\s+khoản(?:\s+(?:số|ngân\s+hàng))?|tk|account\s+(?:no|number)", _after_keyword(6)
        ),
    ),
    Rule(
        "SALARY",
        "SENSITIVE",
        _keyed(
            r"(?:mức\s+)?lương(?:\s+(?:cơ\s+bản|tháng|gross|net))?|salary",
            rf"\d{{1,4}}(?:[.,]\d{{1,3}})?\s*{_MONEY_UNIT}|{_after_keyword(6)}(?:\s*{_MONEY_UNIT})?",
        ),
    ),
    Rule(
        "NATIONAL_ID",
        "PERSONAL",
        _keyed(r"cccd|cmnd|căn\s+cước(?:\s+công\s+dân)?|chứng\s+minh\s+nhân\s+dân", _after_keyword(9)),
    ),
    # Ngữ cảnh ngân hàng trên cùng dòng (trước hoặc sau số), không cần từ khóa "số tài khoản".
    Rule(
        "BANK_ACCOUNT",
        "SENSITIVE",
        re.compile(rf"(?<!\w)(?:{_BANKS})(?!\w)[^\d\n]{{0,40}}?{_EDGE_L}(?P<v>{_seq(6, 19)}){_EDGE_R}", re.IGNORECASE),
    ),
    Rule(
        "BANK_ACCOUNT",
        "SENSITIVE",
        re.compile(rf"{_EDGE_L}(?P<v>{_seq(6, 19)}){_EDGE_R}[^\d\n]{{0,40}}?(?<!\w)(?:{_BANKS})(?!\w)", re.IGNORECASE),
    ),
    # Dạng riêng, không cần từ khóa.
    Rule("NATIONAL_ID", "PERSONAL", re.compile(rf"{_EDGE_L}(?P<v>0\d(?:{_SEP}\d){{10}}){_EDGE_R}")),  # CCCD 12 số
    Rule(  # di động: 0/+84 + 3|5|7|8|9 + 8 số
        "PHONE", "PERSONAL", re.compile(rf"{_EDGE_L}(?P<v>(?:\+84|0){_SEP}[35789](?:{_SEP}\d){{8}}){_EDGE_R}")
    ),
    Rule(  # cố định: 0/+84 + 2 + 9 số (mã vùng 2x/2xx)
        "PHONE", "PERSONAL", re.compile(rf"{_EDGE_L}(?P<v>(?:\+84|0){_SEP}2(?:{_SEP}\d){{9}}){_EDGE_R}")
    ),
    Rule(
        "EMAIL",
        "PERSONAL",
        re.compile(
            r"(?<![\w.+-])(?P<v>[\w.+-]+(?:@|\s*[\[({]\s*at\s*[\])}]\s*)[\w-]+"
            r"(?:(?:\.|\s*[\[({]\s*dot\s*[\])}]\s*)[\w-]+)+)",
            re.IGNORECASE,
        ),
    ),
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
