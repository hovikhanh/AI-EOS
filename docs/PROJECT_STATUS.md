# PROJECT STATUS – AI-EOS

> Nguồn sự thật duy nhất về hiện trạng dự án.
> Mọi nơi khác chỉ được liên kết tới file này, không được ghi lại trạng thái.

**Cập nhật lần cuối:** 15/10/2026 (T-008 đang review; D-55)
**Commit tham chiếu:** `99e477c` (`main`, PR #15); T-008 trên branch `feat/T-008-audit-append-only`
**Giai đoạn hiện tại:** Triển khai giai đoạn P0 (Nền tảng): 7/13 task `DONE`. Kế hoạch đã được duyệt (D-46). T-008 đang review. **4 task đủ điều kiện bắt đầu:** T-003, T-007, T-010, T-101.

Căn cứ: [Implementation_Plan](04-delivery/Implementation_Plan.md) §4 (cột "Sẵn sàng", "Phụ thuộc"), §10 (bằng chứng CI), §17 (áp dụng quyết định 15/10/2026); [TEST_Plan](04-delivery/TEST_Plan.md) §12 (task chủ và trạng thái từng TC); [Decision_Log](00-source/Decision_Log.md) 0.19. Quy ước: task chỉ được bắt đầu khi mọi task ở cột "Phụ thuộc" đã `DONE` (Implementation_Plan §1).

## 1. Tóm tắt nhanh

- Tổng task: **83** (thêm T-308, T-513 theo D-49)
- DONE: **7** — T-001, T-002, T-004, T-005, T-006, T-011, T-012 (T-005, T-006, T-011 theo D-44; T-012 theo D-47; ngày 15/10/2026, dựa trên run CI đã có)
- IN_REVIEW: **1** — T-008
- BLOCKED: **10** — T-407, T-604, T-901…T-908
- TODO: **65** (`READY` 57, `PARTIAL` 8; chưa bắt đầu)
- Task đủ điều kiện bắt đầu ngay: **4** — T-003, T-007, T-010, T-101
- Chức năng nghiệp vụ đã có: **Không.** Đã có hạ tầng nền: khung repo + CI; cấu hình/secret; CSDL + Alembic revision `0001`; log JSON, correlation ID, `/api/v1/health/live`, `/api/v1/health/ready` (API-SYS-01/02 `IMPLEMENTED`, D-52); storage cục bộ; nền tảng frontend
- Test case: **206** (199 + TC-FE-01…07); **8 `PASSED`** (TC-MIG-01; TC-FE-01…07), 198 `NOT RUN`; 1 TC chưa có task chủ (TC-ACC-10)
- Requirement `IMPLEMENTED` / `VERIFIED`: **0 / 217**
- CI: `scripts/ci.sh` 18 bước; branch protection `main` (required check `ci`, bắt buộc PR, `enforce_admins`, 0 approval — D-54 chưa áp dụng)

## 2. Việc đang bị block (Blockers)

Không còn blocker chặn toàn dự án. Các điểm chặn cục bộ:

| # | Bị chặn | Chặn bởi | Hệ quả |
| --- | --- | --- | --- |
| 1 | T-407 (runway) | Q-39 còn thiếu định nghĩa burn ròng, cửa sổ tính | [OPEN_DECISIONS](OPEN_DECISIONS.md) 0.6 |
| 2 | T-904 (% đạt, cảnh báo lệch) | Q-29: công thức (agent đã đề xuất) và cách hiểu ngưỡng "dưới 20%" chờ CDA | OPEN_DECISIONS 0.4 |
| 3 | T-604 (hiệu năng đại diện) | Provider: demo đã chọn (D-50); provider production chưa | Có thể đo khi có adapter T-205 |
| 4 | T-205 (adapter provider) | `PARTIAL`; dependency T-606 (benchmark) — CDA chưa nói phần demo có cần chờ không | OPEN_DECISIONS 0.1 |
| 5 | Nghiệm thu P4/P5 (không chặn code) | Người giữ `finance.period.manage`, `finance.approve` (≥ 2), `goals.activate` chưa giao | OPEN_DECISIONS 0.7 |
| 6 | T-901…T-903, T-905…T-908 | Ngoài phạm vi MVP theo quyết định (D-51, D-21) | Không làm trong MVP |
| 7 | Môi trường | Node mặc định 24 — Node 22.23.3 phải cài lại mỗi phiên (`N_PREFIX=<scratchpad> n install 22.23.3`) | Máy nay có Docker 29.8: test PostgreSQL chạy local bằng container `postgres:18` tạm |

## 3. Trạng thái theo Priority

Nhóm theo giai đoạn P0–P6 của Implementation_Plan §3 (khác mức ưu tiên ở [OPEN_DECISIONS.md](OPEN_DECISIONS.md)). "Chờ …" = task phụ thuộc chưa `DONE`.

### P0 – Nền tảng

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-001 | DONE | Khung repo; run `38257197546` (12/10/2026) |
| T-002 | DONE | Toolchain + CI; branch protection (12/10/2026) |
| T-003 | TODO | READY · **đủ điều kiện bắt đầu** · Compose cấu hình: Caddy, ClamAV + service cập nhật chữ ký (D-43, D-45) |
| T-004 | DONE | Cấu hình/secret; PR #8, run `38541183244` (14/10/2026) |
| T-005 | DONE | Nền CSDL; run `38543440774`; TC-MIG-01 `PASSED` (D-44, 15/10/2026) |
| T-006 | DONE | Log, correlation ID, health; run `38544809935` (D-44, 15/10/2026) |
| T-007 | TODO | READY · **đủ điều kiện bắt đầu** · HTTP: CSRF, problem+json, idempotency, ETag, rate limit |
| T-008 | IN_REVIEW | Audit append-only: migration `0002`, trigger INV-14, `audit.api.record`/`record_separately`; chờ CI của PR; chủ TC-AUD-03 (D-55) |
| T-009 | TODO | READY · Job queue; chờ T-008 |
| T-010 | TODO | READY · **đủ điều kiện bắt đầu** · Thông báo in-app |
| T-011 | DONE | Storage adapter; run `38544080219` (D-44, 15/10/2026) |
| T-012 | DONE | Nền tảng frontend; run `38536047844`; TC-FE-01…07 `PASSED` (D-47, 15/10/2026) |
| T-013 | TODO | READY · Compose tích hợp; chờ T-003, T-009 |

### P1 – Identity và Access

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-101 | TODO | READY · **đủ điều kiện bắt đầu** · Bảng `identity.*` |
| T-102 | TODO | READY · Đăng nhập, session; chờ T-101, T-007 |
| T-103 | TODO | READY · MFA TOTP; chờ T-102 |
| T-104 | TODO | READY · Step-up, đổi mật khẩu; chờ T-102 |
| T-105 | TODO | READY · Lời mời; chờ T-102, T-108 |
| T-106 | TODO | READY · CLI bootstrap/recover admin; chờ T-101, T-107 |
| T-107 | TODO | READY · Bảng `access.*`, seed; chờ T-101 |
| T-108 | TODO | PARTIAL (định nghĩa "team" PROPOSED) · `authorize()`; chờ T-107 |
| T-109 | TODO | READY · API quản trị; chờ T-108, T-104 |
| T-110 | TODO | READY · Audit, trang tình trạng; chờ T-109, T-009; TC-FIN-14 cần thêm T-401 hoặc T-402 (OPEN_DECISIONS 0.2) |
| T-111 | TODO | READY · Frontend app shell; chờ T-102…T-109 |
| T-112 | TODO | READY (R6 đã quyết) · Che dữ liệu cá nhân; chờ T-108 |

### P2 – Org và Data Capture

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-201 | TODO | READY · `org.*`; chờ T-108 |
| T-202 | TODO | READY · Bảng `capture.*`; chờ T-201 |
| T-203 | TODO | READY · Upload, quét mã độc; chờ T-202, T-009 |
| T-204 | TODO | READY · Provider adapter + giả lập; chờ T-009 |
| T-205 | TODO | PARTIAL (D-50: DeepSeek qua OpenRouter cho demo) · chờ T-204, T-606 |
| T-206 | TODO | READY · Pipeline; chờ T-203, T-204, T-302, T-112 |
| T-207 | TODO | READY · Hàng chờ review + UI; chờ T-206, T-108, T-408 |
| T-208 | TODO | READY · Cấu hình loại tài liệu; chờ T-206 |
| T-209 | TODO | READY · Form từ schema; chờ T-206, T-204 |
| T-210 | TODO | READY · Import; chờ T-206, T-302 |
| T-211 | TODO | READY · Lineage; chờ T-206 |
| T-212 | TODO | READY · Frontend capture; chờ T-203, T-210 |

### P3 – AI control

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-301 | TODO | READY · Bảng `ai.*`; chờ T-107 |
| T-302 | TODO | READY · Write gateway; chờ T-301, T-108, T-008 |
| T-303 | TODO | READY · Kill switch; chờ T-302, T-009 |
| T-304 | TODO | READY · Bản nháp, hoàn tác; chờ T-302, T-010 |
| T-305 | TODO | READY · Cấu hình autonomy; chờ T-301 |
| T-306 | TODO | PARTIAL · Chat AI SSE (chat chỉ đọc vẫn chạy khi kill switch bật — D-48); chờ T-204, T-108 |
| T-307 | TODO | READY · Phản hồi, harness đánh giá; chờ T-306 |
| T-308 | TODO | READY · **Mới (D-49)** Frontend panel chat AI; chờ T-306, T-111 |

### P4 – Finance Lite

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-401 | TODO | READY · Bảng `finance.*`; chờ T-107 |
| T-402 | TODO | PARTIAL (người giữ `finance.period.manage` chưa giao) · Kỳ báo cáo; chờ T-401, T-104 |
| T-403 | TODO | READY · Giao dịch; chờ T-401, T-402 |
| T-404 | TODO | READY · Duyệt; chờ T-403 |
| T-405 | TODO | READY · Bút toán đảo; chờ T-404 |
| T-406 | TODO | READY · Tổng hợp; chờ T-404 |
| T-407 | BLOCKED | Runway; Q-39 còn thiếu định nghĩa burn ròng |
| T-408 | TODO | READY · Tool AI `create_finance_draft`; chờ T-302, T-403 |
| T-409 | TODO | READY · Frontend tài chính; chờ T-403…T-406 |

### P5 – Goals, Work, Briefing

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-501 | TODO | READY · `goals.*`; chờ T-108, T-201 |
| T-502 | TODO | PARTIAL (vòng đời Q-28) · Kích hoạt: CEO cấp công ty, MANAGER cấp đơn vị; chờ T-501, T-109 |
| T-503 | TODO | READY · Mục tiêu từ tài liệu; chờ T-206, T-302, T-501 |
| T-504 | TODO | PARTIAL (quy tắc điền check-in từ task — Q-29) · chờ T-501, T-502 |
| T-505 | TODO | READY · `work.task`; chờ T-108, T-201 |
| T-506 | TODO | READY · Biên bản → việc; chờ T-206, T-302, T-505 |
| T-507 | TODO | READY · Job task quá hạn; chờ T-009, T-505 |
| T-508 | TODO | READY · Action card F1; chờ T-304, T-505 |
| T-509 | TODO | READY · Frontend công việc; chờ T-505, T-506 |
| T-510 | TODO | PARTIAL (ngưỡng "dữ liệu cũ" trống) · Trang chủ CEO (API), công thức ô chính thức (Q-37); chờ T-406, T-501, T-505, T-304, T-211 |
| T-511 | TODO | READY · Nội dung Briefing; chờ T-510, T-303, T-204 |
| T-512 | TODO | READY · SOP → knowledge; chờ T-206, T-302 |
| T-513 | TODO | PARTIAL · **Mới (D-49)** Frontend Trang chủ CEO; chờ T-510, T-111 |

### P6 – Hardening, benchmark, phục hồi

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-601 | TODO | READY · Ma trận authorization; chờ T-107 và 33 task API (Implementation_Plan §17) |
| T-602 | TODO | READY · Test bảo mật; chờ T-111, T-203, T-306, T-013 |
| T-603 | TODO | READY · Đồng thời, idempotency; chờ T-404, T-405, T-009 |
| T-604 | BLOCKED | Hiệu năng; cần provider thật (T-205) |
| T-605 | TODO | READY · Backup/restore, chủ TC-DR-01/02, TC-MIG-02; chờ T-013, T-203, T-008, T-101, T-107, T-301, T-302, T-401, T-403 |
| T-606 | TODO | READY · Benchmark (dataset giai đoạn 1 đã duyệt, D-08); chờ T-204 |
| T-607 | TODO | READY · WCAG, i18n; chờ T-111 |
| T-608 | TODO | READY · E2E, chủ TC-E2E-01…06; chờ T-013 và 9 task frontend (Implementation_Plan §17) |

### Ngoài phạm vi triển khai MVP

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-901 | BLOCKED | Sales Pipeline Lite — giữ ngoài MVP (D-51) |
| T-902 | BLOCKED | Workload — không có trong MVP (D-51) |
| T-903 | BLOCKED | Lịch — không có trong MVP (D-51) |
| T-904 | BLOCKED | % đạt, cảnh báo lệch — chờ duyệt công thức (Q-29) |
| T-905 | BLOCKED | Theo dõi quyết định 30/60/90 — chỉ ghi quyết định (D-51) |
| T-906 | BLOCKED | Nhắc check-in — không nhắc tự động (D-51) |
| T-907 | BLOCKED | Quyền dữ liệu nhân sự nhạy cảm — không ai giữ trong MVP (D-21) |
| T-908 | BLOCKED | Phase 2 |

## 4. Quyết định đang chờ (link sang OPEN_DECISIONS.md)

Chi tiết và phiếu điền: [OPEN_DECISIONS.md](OPEN_DECISIONS.md) mục 0 (12 mục). Không mục nào chặn 5 task đang đủ điều kiện bắt đầu.

- Cần trước T-204/T-205: D-50 — demo dùng dữ liệu tổng hợp hay thật; định tuyến dữ liệu nhạy cảm ở production; DeepSeek trong benchmark; T-205 có chờ T-606
- Cần trước T-110: dependency TC-FIN-14 (T-401 hay T-402)
- Cần trước T-108: task chủ TC-ACC-10, định nghĩa "team"
- Cần trước T-502/T-504/T-904/T-407: Q-28 vòng đời; Q-29 công thức + ngưỡng + quy tắc check-in từ task; Q-39 burn ròng
- Vận hành: người giữ quyền tài chính và `goals.activate`; tài khoản approve cho D-54

## 5. Việc nên làm tiếp theo (sau khi có quyết định)

1. Hoàn tất PR T-008 (CI xanh → TC-AUD-03 `PASSED` kèm run → T-008 `DONE` → merge).
2. Tiếp theo đường găng: **T-009** (sau T-008), **T-007** (HTTP — cần cho T-102) → **T-101** → **T-010**; **T-003** song song.
3. Sau T-008: T-009 → T-013 (khi T-003 xong) → T-605 về sau.
4. CDA điền OPEN_DECISIONS mục 0 trước khi tới T-204 (D-50) và T-108 (TC-ACC-10).

## 6. Ghi chú phiên gần nhất

**Phiên 15/10/2026 (lần 3) — T-008:**
- PR #15 (tài liệu D-44…D-54) merge → `99e477c`, CI `main` run `38676541858` xanh.
- D-55 (CDA): TC-AUD-01 chủ T-109; TC-AUD-02 tách phần, tổng ở T-105 (thêm T-103, T-104 vào dependency T-105); T-008 chỉ làm chủ TC-AUD-03.
- T-008: code + test; `scripts/ci.sh` local rc 0 với PostgreSQL 18.6 (container tạm); đột biến → test đỏ. Chi tiết: Implementation_Plan §10, §18.

**Phiên 15/10/2026 (lần 2) — áp dụng quyết định CDA:**
- Đọc phiếu OPEN_DECISIONS (người quyết định: "admin"). Hỏi lại 4 điểm mâu thuẫn; CDA trả lời: giữ D-21/D-14 (không giao quyền tài chính cho ADMIN); provider demo DeepSeek qua OpenRouter cho mọi dữ liệu; Q-50 đổi A → B; TC-MIG-02 chủ T-605.
- Cập nhật: Decision_Log 0.19 (D-44…D-54), Implementation_Plan (§2, §3, §4, §8, §10, §12, §17), TEST_Plan 1.1 (§8a, §12, TC-BRF-02, TC-NFR-01), Requirements_Traceability 0.7 (§13), SRS 1.2, API_Specification 1.3, Architecture §9.1/§12, ADR-008, ADR-011 Amendment 1, CLAUDE.md §1/§6, Implementation_Handoff (ghi chú), `scripts/check_docs.py` (cho phép `PASSED` kèm run CI), OPEN_DECISIONS, file này.
- Kiểm tra: `python3 scripts/check_docs.py` → 0 lỗi, 0 cảnh báo; kiểm tra âm luật `PASSED` trên bản sao tạm (thiếu run CI → lỗi; `VERIFIED` → lỗi). Không đổi code ứng dụng; chưa chạy `scripts/ci.sh`.
- Chưa commit.

**Phiên 15/10/2026 (lần 1):** review tài liệu; tạo PROJECT_STATUS và OPEN_DECISIONS.

**Phiên 14/10/2026 (lần 6):** PR #14 (`04f41bb`, dự thảo Q-51). Bài học: không nối kiểm tra bằng `;` sau `&&`; không pipe lệnh kiểm tra qua `tail` khi cần exit code; `gh` 2.4 cũ → dùng `gh api` REST.

## 7. Tài liệu khác đang ghi trạng thái lỗi thời (chưa sửa)

| File | Nội dung lỗi thời |
| --- | --- |
| [README.md](../README.md) | "Chưa có chức năng, API, CSDL, migration hay Docker" |
| [SRS](02-requirements/SRS.md), [Architecture](03-architecture/Architecture.md), [Database_Design](03-architecture/Database_Design.md) — header | "chưa có code" / "chưa có migration" |
| [Implementation_Handoff](Implementation_Handoff.md) §2, §8, §9, §10.3 | Trạng thái 12/10/2026 (đã có ghi chú ở đầu file trỏ về đây) |
| [Requirements_Traceability](00-source/Requirements_Traceability.md) §5 | "AI-EOS chưa có code" |
| [Documentation_Review](04-delivery/Documentation_Review.md) | Snapshot cuối Stage 2D |
| `04-delivery/SESSION_CHECKPOINT.md` | Untracked; trùng nội dung file này |

Đã sửa trong phiên này: CLAUDE.md §1, Decision_Log §1.1, header Implementation_Plan, TEST_Plan, API_Specification.
