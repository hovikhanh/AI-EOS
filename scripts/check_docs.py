#!/usr/bin/env python3
"""Kiểm tra nhất quán tài liệu AI-EOS (docs/).

Chạy: python3 scripts/check_docs.py [--mermaid-modules <thư mục chứa node_modules có mermaid, jsdom>]
Thoát mã 1 nếu có lỗi (ERROR); cảnh báo (WARN) không làm thất bại.
Không đọc/ghi gì ngoài docs/ và không chạy code ứng dụng.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")

# md5 của hai file nguồn tại thời điểm Giai đoạn 1; không được thay đổi.
SOURCE_HASHES = {
    "00-source/BRD_Review.md": "f4158782f8a92bb57d940c8360199721",
    "00-source/UI_UX_Proposal.md": "f3ccd38977829a34a27ae2d4d4d26c93",
}
EXPECTED_REQ_COUNT = 217
STATUSES = {"CONFIRMED", "PROPOSED", "NEEDS_CONFIRMATION", "DEFERRED"}
REQ_PFX = r"(?:BR|FR-DCS|FR-DC|SEC-DC|FR-LRN|FR-DF|FR-AUT|FR-HM|FR-AIQ|CMP|FR-EXT|NFR|MET|UX|US-DC|UC|SC|CHG)"
V1_EXTERNAL = {"UC-01", "UC-02", "UC-03"}  # BRD v1.0, liệt kê ở Requirements_Traceability §6

errors: list[str] = []
warns: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warns.append(msg)


def load() -> dict[str, str]:
    files = {}
    for path in glob.glob(os.path.join(DOCS, "**", "*.md"), recursive=True):
        files[os.path.relpath(path, DOCS)] = open(path, encoding="utf-8").read()
    claude = os.path.join(ROOT, "CLAUDE.md")
    if os.path.exists(claude):
        files["../CLAUDE.md"] = open(claude, encoding="utf-8").read()
    return files


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("| ") or set(line.replace("|", "").strip()) <= set("-: "):
            continue
        rows.append([c.strip() for c in line.strip().strip("|").split("|")])
    return rows


def headings(text: str) -> set[str]:
    return set(re.findall(r"^#{2,3} (\d+(?:\.\d+)?)\.", text, re.M))


def check_sources(T: dict[str, str]) -> None:
    for rel, md5 in SOURCE_HASHES.items():
        data = open(os.path.join(DOCS, rel), "rb").read()
        if hashlib.md5(data).hexdigest() != md5:
            err(f"File nguồn đã bị thay đổi: {rel}")


def check_links(T: dict[str, str]) -> int:
    n = 0
    for rel, text in T.items():
        for link in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            n += 1
            target = os.path.normpath(os.path.join(DOCS, os.path.dirname(rel), link))
            if not os.path.exists(target):
                err(f"Link hỏng: {rel} -> {link}")
    return n


def matrix(T: dict[str, str]) -> list[list[str]]:
    rt = T["00-source/Requirements_Traceability.md"]
    sec = rt.split("## 3. Ma trận yêu cầu")[1].split("## 4. Bảng chéo")[0]
    return [r for r in table_rows(sec) if r[0] != "ID"]


def check_matrix(T: dict[str, str]) -> set[str]:
    rows = matrix(T)
    ids = [r[0] for r in rows]
    if len(ids) != EXPECTED_REQ_COUNT:
        err(f"Số requirement trong ma trận = {len(ids)}, mong đợi {EXPECTED_REQ_COUNT}")
    dup = [k for k, v in Counter(ids).items() if v > 1]
    if dup:
        err(f"Requirement ID trùng: {dup}")
    for r in rows:
        if re.match(r"^U\d$", r[0]):
            continue  # bảng nguyên tắc U1–U8 không có cột trạng thái
        st = [c for c in r if c in STATUSES]
        if not st:
            err(f"Dòng {r[0]} không có trạng thái hợp lệ")
        if any(c in ("IMPLEMENTED", "VERIFIED") for c in r):
            err(f"Dòng {r[0]} ở IMPLEMENTED/VERIFIED khi chưa có code")
    return set(ids)


def defined_ids(T: dict[str, str]) -> dict[str, set[str]]:
    sa, dl = T["00-source/Source_Analysis.md"], T["00-source/Decision_Log.md"]
    srs, prd, ux = T["02-requirements/SRS.md"], T["02-requirements/PRD.md"], T["02-requirements/UX_Flows.md"]
    api = T["03-architecture/API_Specification.md"]
    return {
        "D": set(re.findall(r"^\| (D-\d+) \|", dl, re.M)),
        "CGQA": set(re.findall(r"(?:^### |^\| )((?:CON|GAP|Q|ASM)-\d+)", sa + dl, re.M)),
        "SRS": set(re.findall(r"^\| (SRS-[A-Z]+-\d+) \|", srs, re.M)),
        "US": set(re.findall(r"^\*\*(US-[A-Z]+-\d+)\*\*", prd, re.M)),
        "FL": set(re.findall(r"^## (FL-\d+) ", ux, re.M)),
        "API": set(re.findall(r"^\| (API-[A-Z]+-\d+) \|", api, re.M)),
        "ADR": {re.match(r"(ADR-\d+)", os.path.basename(p)).group(1)
                for p in glob.glob(os.path.join(DOCS, "03-architecture/decisions/ADR-*.md"))},
    }


def check_refs(T: dict[str, str], req_ids: set[str]) -> None:
    D = defined_ids(T)
    api_rows = re.findall(r"^\| (API-[A-Z]+-\d+) \|", T["03-architecture/API_Specification.md"], re.M)
    for k, v in Counter(api_rows).items():
        if v > 1:
            err(f"API ID trùng: {k}")
    srs_rows = re.findall(r"^\| (SRS-[A-Z]+-\d+) \|", T["02-requirements/SRS.md"], re.M)
    for k, v in Counter(srs_rows).items():
        if v > 1:
            err(f"SRS ID trùng: {k}")
    sources = set(SOURCE_HASHES)
    for rel, text in T.items():
        if rel in sources:
            continue
        for x in set(re.findall(r"\bD-\d{2}\b", text)) - D["D"]:
            err(f"{rel}: {x} chưa định nghĩa")
        for x in set(re.findall(r"\b(?:CON|GAP|Q|ASM)-\d{2}\b", text)) - D["CGQA"]:
            err(f"{rel}: {x} chưa định nghĩa")
        for x in set(re.findall(r"\bADR-\d{3}\b", text)) - D["ADR"]:
            err(f"{rel}: {x} không tồn tại")
        for x in set(re.findall(r"\bAPI-[A-Z]+-\d+\b", text)) - D["API"]:
            err(f"{rel}: {x} không có trong API_Specification")
        for x in set(re.findall(r"\bSRS-[A-Z]+-\d+\b", text)) - D["SRS"]:
            err(f"{rel}: {x} không có trong SRS")
        for x in set(re.findall(r"\bFL-\d{2}\b", text)) - D["FL"]:
            err(f"{rel}: {x} không có trong UX_Flows")
        new_us = r"\bUS-(?:IAM|GOAL|WRK|BRF|FNL|SLS|AIC|PRV)-\d+\b"
        for x in set(re.findall(new_us, text)) - D["US"]:
            err(f"{rel}: {x} không có trong PRD")
        if rel.startswith(("01-", "02-", "03-")):
            for x in set(re.findall(r"(?<![\w-])(" + REQ_PFX + r"-\d+)\b", text)) - req_ids - V1_EXTERNAL:
                err(f"{rel}: requirement {x} không có trong ma trận")


def check_section_refs(T: dict[str, str]) -> int:
    targets = {
        "Architecture": "03-architecture/Architecture.md",
        "Database_Design": "03-architecture/Database_Design.md",
        "API_Specification": "03-architecture/API_Specification.md",
        "SRS": "02-requirements/SRS.md",
        "PRD": "02-requirements/PRD.md",
        "Decision_Log": "00-source/Decision_Log.md",
    }
    n = 0
    for name, rel in targets.items():
        H = headings(T[rel])
        for src, text in T.items():
            if src in SOURCE_HASHES:
                continue
            for s in re.findall(name + r" §(\d+(?:\.\d+)?)", text):
                n += 1
                if s not in H:
                    err(f"{src}: {name} §{s} không tồn tại")
    return n


def expand(text: str, pfx: str) -> set[str]:
    """Lấy ID dạng PFX-NN, kể cả khoảng 'PFX-01…05' và 'PFX-01…PFX-05'."""
    out = set()
    for m in re.finditer(r"\b(" + pfx + r")-(\d+)(?:\s*…\s*(?:\1-)?(\d+))?", text):
        a, b = int(m.group(2)), int(m.group(3) or m.group(2))
        w = len(m.group(2))
        out.update(f"{m.group(1)}-{k:0{w}d}" for k in range(a, b + 1))
    return out


def check_delivery(T: dict[str, str]) -> None:
    ip = T.get("04-delivery/Implementation_Plan.md")
    tp = T.get("04-delivery/TEST_Plan.md")
    if not ip or not tp:
        err("Thiếu Implementation_Plan.md hoặc TEST_Plan.md")
        return
    tasks = re.findall(r"^\| (T-\d+) \|", ip, re.M)
    tcs = re.findall(r"^\| (TC-[A-Z0-9]+-\d+) \|", tp, re.M)
    for k, v in Counter(tasks).items():
        if v > 1:
            err(f"Task ID trùng: {k}")
    for k, v in Counter(tcs).items():
        if v > 1:
            err(f"Test case ID trùng: {k}")
    tset, cset = set(tasks), set(tcs)
    srs_ids = set(re.findall(r"^\| (SRS-[A-Z]+-\d+) \|", T["02-requirements/SRS.md"], re.M))
    for rel, text in T.items():
        for x in expand(text, r"T") - tset:
            if re.match(r"^T-\d{3}$", x):
                err(f"{rel}: {x} không có trong Implementation_Plan")
        for x in expand(text, r"TC-[A-Z0-9]+") - cset:
            err(f"{rel}: {x} không có trong TEST_Plan")
    # Trạng thái TC (D-44): chỉ `NOT RUN` hoặc `PASSED`; `PASSED` phải kèm run CI trên cùng dòng
    if re.search(r"\b(FAILED_RUN|VERIFIED)\b", tp):
        err("TEST_Plan chứa trạng thái FAILED_RUN/VERIFIED")
    for line in tp.splitlines():
        if re.search(r"\bPASSED\b", line) and re.match(r"^\| `?TC-", line) and not re.search(r"run `\d+`", line):
            err(f"TEST_Plan: PASSED không kèm run CI: {line[:60]}")
    # SRS chưa có test (trừ mục bị chặn/DEFERRED/không có nguồn mục tiêu)
    srs_text = T["02-requirements/SRS.md"]
    covered = set(re.findall(r"SRS-[A-Z]+-\d+", tp))
    for sid in sorted(srs_ids - covered):
        row = re.search(r"^\| " + sid + r" \|.*$", srs_text, re.M).group(0)
        if not re.search(r"DEFERRED|NEEDS_CONFIRMATION|D-40|nguồn không có chỉ tiêu", row):
            warn(f"{sid} chưa có test case")


def check_rules(T: dict[str, str]) -> None:
    arch = T["03-architecture/Architecture.md"]
    for r in table_rows(arch):
        if r and r[0] in ("`finance.approve`", "`data.read`", "`hr.profile.read`", "`pii.unmask`"):
            admin, ceo = r[2], r[3]
            if admin != "—":
                err(f"Architecture §6: ADMIN có {r[0]}")
            if r[0] == "`finance.approve`" and ceo != "—":
                err("Architecture §6: CEO có finance.approve mặc định")
    # Cột Req của API tài chính phải dùng CDA-F, tránh trùng luồng UX F1–F5
    for line in T["03-architecture/API_Specification.md"].splitlines():
        if re.match(r"^\| API-FIN-\d+ \|", line):
            last = line.rstrip().rstrip("|").split("|")[-1]
            if re.search(r"(?<![\w-])F[1-7](?![\w-])", last):
                err(f"API tài chính dùng mã F không tiền tố: {line[:40]}")
    # Phạm vi MVP: cảnh báo dòng nhắc L4 / hóa đơn / email forwarding mà không có dấu hiệu ngoài MVP
    guard = re.compile(r"\bL4\b|email forwarding|hóa đơn", re.I)
    ok = re.compile(r"DEFERRED|Phase 2|ngoài MVP|không|D-11|D-17|D-18|P1|L0.?L4|L3/L4|trần|Ngoài MVP|chưa hỗ trợ|BR-19|L4 Autonomous", re.I)
    for rel, text in T.items():
        if not rel.startswith(("01-", "02-", "03-")):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if guard.search(line) and not ok.search(line):
                warn(f"{rel}:{i} nhắc phạm vi ngoài MVP, cần kiểm tra: {line.strip()[:90]}")


def check_mermaid(T: dict[str, str], modules: str | None) -> str:
    blocks = [(rel, b) for rel, text in T.items() for b in re.findall(r"```mermaid\n([\s\S]*?)```", text)]
    if not modules:
        return f"bỏ qua ({len(blocks)} sơ đồ; truyền --mermaid-modules để kiểm tra)"
    script = r"""
import { JSDOM } from 'jsdom'; import fs from 'fs';
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window; globalThis.document = dom.window.document;
globalThis.DOMParser = dom.window.DOMParser; globalThis.Element = dom.window.Element;
Object.defineProperty(globalThis,'navigator',{value:dom.window.navigator,configurable:true});
const mermaid = (await import('mermaid')).default; mermaid.initialize({startOnLoad:false});
const items = JSON.parse(fs.readFileSync(process.argv[2],'utf8')); const res=[];
for (const [f,b] of items) { try { await mermaid.parse(b); res.push([f,'OK']); } catch(e) { res.push([f,String(e.message||e).split('\n')[0]]); } }
console.log(JSON.stringify(res));
"""
    with tempfile.TemporaryDirectory() as tmp:
        js = os.path.join(modules, "_aieos_check.mjs")
        open(js, "w").write(script)
        data = os.path.join(tmp, "blocks.json")
        json.dump(blocks, open(data, "w"))
        try:
            out = subprocess.run(["node", js, data], cwd=modules, capture_output=True, text=True, timeout=180)
            res = json.loads(out.stdout.strip().splitlines()[-1])
        finally:
            os.remove(js)
    bad = [(f, m) for f, m in res if m != "OK"]
    for f, m in bad:
        err(f"Mermaid lỗi trong {f}: {m}")
    return f"{len(res) - len(bad)}/{len(res)} sơ đồ hợp lệ"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mermaid-modules")
    args = ap.parse_args()
    T = load()
    check_sources(T)
    n_links = check_links(T)
    req_ids = check_matrix(T)
    check_refs(T, req_ids)
    n_sec = check_section_refs(T)
    check_rules(T)
    check_delivery(T)
    mm = check_mermaid(T, args.mermaid_modules)
    print(f"Tài liệu: {len(T)} file · link: {n_links} · tham chiếu mục: {n_sec} · requirement: {len(req_ids)} · Mermaid: {mm}")
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"Kết quả: {len(errors)} lỗi, {len(warns)} cảnh báo")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
