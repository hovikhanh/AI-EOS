# PROJECT STATUS – AI-EOS

> Nguồn sự thật duy nhất về hiện trạng dự án.
> Mọi nơi khác chỉ được liên kết tới file này, không được ghi lại trạng thái.

**Cập nhật lần cuối:** 15/10/2026 (T-501 `DONE`)
**Commit tham chiếu:** `110e561` (`main`, PR #36 — T-202); T-501: PR #37 (CI run `38764880704` xanh)
**Giai đoạn hiện tại:** Triển khai giai đoạn P0 (Nền tảng): 13/13 task `DONE`; P1: T-101…T-109, T-111 `DONE`; P2: T-201, T-202 `DONE`; P3: T-301 `DONE`; P4: T-401 `DONE`; P5: T-501, T-505 `DONE`. Kế hoạch đã được duyệt (D-46). **9 task đủ điều kiện bắt đầu:** T-112, T-203, T-204, T-302, T-305, T-402, T-502, T-507, T-607.

Căn cứ: [Implementation_Plan](04-delivery/Implementation_Plan.md) §4 (cột "Sẵn sàng", "Phụ thuộc"), §10 (bằng chứng CI), §17 (áp dụng quyết định 15/10/2026); [TEST_Plan](04-delivery/TEST_Plan.md) §12 (task chủ và trạng thái từng TC); [Decision_Log](00-source/Decision_Log.md) 0.19. Quy ước: task chỉ được bắt đầu khi mọi task ở cột "Phụ thuộc" đã `DONE` (Implementation_Plan §1).

## 1. Tóm tắt nhanh

- Tổng task: **83** (thêm T-308, T-513 theo D-49)
- DONE: **29** — T-001…T-013, T-101…T-109, T-111, T-201, T-202, T-301, T-401, T-501, T-505 (T-501 run `38764880704`; T-202 run `38760592674`; T-301 run `38757933594`; T-401 run `38755214148`; T-505 run `38752643215`; T-201 run `38737949724`; T-013 run `38722522003`; T-111 run `38719094857`; T-003 run `38712655012`; T-105 run `38710976904`; T-109 run `38708289449`; T-104 run `38705903816`; T-108 run `38703355287`, phần có căn cứ — team/mục tiêu cha chưa làm; T-103 run `38700993783`; T-106 run `38697852135`; T-010 run `38696839691`; T-102 run `38686690047`; T-107 run `38684667496`; T-101 run `38683463269`; T-007 run `38681777001`; T-005, T-006, T-011 theo D-44; T-012 theo D-47; T-008 run `38678659141`; T-009 run `38680383606`; ngày 15/10/2026)
- IN_REVIEW: **0**
- BLOCKED: **10** — T-407, T-604, T-901…T-908
- TODO: **44** (`READY` 37, `PARTIAL` 7; chưa bắt đầu)
- Task đủ điều kiện bắt đầu ngay: **9** — T-112, T-203, T-204, T-302, T-305, T-402, T-502, T-507, T-607
- Chức năng nghiệp vụ đã có: **Không.** Đã có hạ tầng nền: khung repo + CI; cấu hình/secret; CSDL + Alembic revision `0001`; log JSON, correlation ID, `/api/v1/health/live`, `/api/v1/health/ready` (API-SYS-01/02 `IMPLEMENTED`, D-52); storage cục bộ; nền tảng frontend; đăng nhập/session (T-102); MFA TOTP API-AUTH-02/03/04 (T-103); policy `authorize()` + bắt buộc khai báo quyền cho route (T-108); step-up + đổi mật khẩu API-AUTH-05/09 (T-104); API quản trị tài khoản/role/assignment API-ADM-01, 04…09 (T-109); tạo tài khoản + lời mời API-ADM-02/03, API-AUTH-08 (T-105); Docker Compose chạy được qua HTTPS, demo đầu-cuối tự động trong CI (T-003, T-013); frontend: đăng nhập, MFA, lời mời, quản trị người dùng/quyền (T-111); danh bạ + cây đơn vị API-ORG-01/02, phạm vi MANAGER (T-201); task API-WORK-01/03/04/05 (T-505, chưa có giao diện); bảng tài chính + bất biến CSDL (T-401); bảng AI + Tool Registry (T-301); bảng tài liệu/trích xuất (T-202); thông báo in-app API-NOT-01/02 (T-010); CLI `bootstrap-admin`/`recover-admin` (T-106)
- Test case: **206** (199 + TC-FE-01…07); **52 `PASSED`** (TC-MIG-01; TC-FE-01…07; TC-AUD-03; TC-JOB-01…04, TC-JOB-06; TC-GEN-01…06; TC-IAM-01…08, TC-IAM-11, TC-IAM-12; TC-IAM-09, TC-IAM-10; TC-ACC-01, TC-ACC-02, TC-ACC-04…09; TC-AUD-01, TC-AUD-02; TC-NFR-01; TC-WRK-01…05; TC-FIN-01…04), 154 `NOT RUN`; 1 TC chưa có task chủ (TC-ACC-10)
- Requirement `IMPLEMENTED` / `VERIFIED`: **0 / 217**
- CI: `scripts/ci.sh` 20 bước (thêm `compose` T-003, `compose-smoke` T-013); PostgreSQL CI `18.6`; branch protection `main` (required check `ci`, bắt buộc PR, `enforce_admins`, 0 approval — D-54 chưa áp dụng)

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
| T-003 | DONE | Compose cấu hình (Caddy 2.11.4, PostgreSQL 18.6, ClamAV 1.5.4 + `scanner-updater`), `scripts/check_compose.py` (bước `compose`); run `38712655012` |
| T-004 | DONE | Cấu hình/secret; PR #8, run `38541183244` (14/10/2026) |
| T-005 | DONE | Nền CSDL; run `38543440774`; TC-MIG-01 `PASSED` (D-44, 15/10/2026) |
| T-006 | DONE | Log, correlation ID, health; run `38544809935` (D-44, 15/10/2026) |
| T-007 | DONE | HTTP: problem+json, CSRF + Origin, idempotency, ETag/If-Match, rate limit; run `38681777001`; TC-GEN-01…05 `PASSED` |
| T-008 | DONE | Audit append-only: migration `0002`, trigger INV-14, `audit.api.record`/`record_separately`; run `38678659141`; TC-AUD-03 `PASSED` (15/10/2026) |
| T-009 | DONE | Job queue: migration `0003`, claim `SKIP LOCKED`, lease, reaper, backoff, scheduler, registry `job_class`, lệnh `worker`; run `38680383606`; TC-JOB-01…04, 06 `PASSED` (TC-JOB-05 → T-203, D-56) |
| T-010 | DONE | Thông báo in-app: `notify.notification` (revision `0006`), `notify.api.notify`, API-NOT-01/02; run `38696839691`; bằng chứng thành phần TC-NTF-01 (chủ T-510) |
| T-011 | DONE | Storage adapter; run `38544080219` (D-44, 15/10/2026) |
| T-012 | DONE | Nền tảng frontend; run `38536047844`; TC-FE-01…07 `PASSED` (D-47, 15/10/2026) |
| T-013 | DONE | Dockerfile backend/proxy, `uvicorn`, init CSDL + secret, mọi service healthy, demo đầu-cuối qua HTTPS (`compose-smoke`); run `38722522003`; TC-NFR-01 `PASSED` |

### P1 – Identity và Access

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-101 | DONE | Bảng `identity.*` (migration `0004`), token chỉ lưu hash (INV-16); run `38683463269` |
| T-102 | DONE | Đăng nhập Argon2id, session, khóa tạm, rate limit, `/auth/me`, logout, dependency session; run `38686690047`; TC-IAM-01…05, TC-GEN-06 `PASSED` |
| T-103 | DONE | MFA TOTP: đăng ký, xác minh, mã khôi phục, xoay session; migration `0007`; run `38700993783`; TC-IAM-06, TC-IAM-07 `PASSED` |
| T-104 | DONE | Reauth (step-up) gắn session, `require_step_up`, đổi mật khẩu + thu hồi session khác; run `38705903816`; TC-IAM-08 `PASSED` |
| T-105 | DONE | Tạo tài khoản `INVITED` + lời mời (link một lần), cấp lại, chấp nhận lời mời; migration `0009`; run `38710976904`; TC-IAM-09, TC-IAM-10, TC-AUD-02 (tổng) `PASSED` |
| T-106 | DONE | CLI `bootstrap-admin`/`recover-admin` (tiến trình `admin-cli`, `AIEOS_PASSWORD_MIN_LENGTH`); run `38697852135`; TC-IAM-11, TC-IAM-12 `PASSED` |
| T-107 | DONE | Bảng `access.*` (migration `0005`), seed theo Architecture §6, INV-09/10/11, điều kiện assignment, service role/assignment; run `38684667496` |
| T-108 | DONE | Phần có căn cứ: `authorize()`, phạm vi theo role/assignment, `scope_filter`, `PermissionGuard`, route không khai báo quyền → 403; run `38703355287`; TC-ACC-01, TC-ACC-02 `PASSED`. Chưa làm: "team" (SRS-ACC-04), mục tiêu cha. TC-ACC-03 → chủ T-505 (D-59) |
| T-109 | DONE | API-ADM-01, 04…09; thu hồi session khi đổi role/assignment/khóa; idempotency assignment (migration `0008`); run `38708289449`; TC-ACC-04…08, TC-AUD-01 `PASSED` |
| T-110 | TODO | READY · Audit, trang tình trạng; chờ T-109; TC-FIN-14 cần thêm T-401 hoặc T-402 (OPEN_DECISIONS 0.2) |
| T-111 | DONE | App shell, đăng nhập, MFA, lời mời, quản trị người dùng/quyền, ẩn mục không có quyền, trạng thái chung; run `38719094857`; bằng chứng thành phần TC-E2E-01 |
| T-112 | TODO | READY (R6 đã quyết) · **đủ điều kiện bắt đầu** · Che dữ liệu cá nhân |

### P2 – Org và Data Capture

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-201 | DONE | `org.*` (migration `0010`), API-ORG-01/02, `OrgDirectoryScope` (MANAGER = đơn vị làm trưởng + cấp dưới); run `38737949724`; TC-ACC-09 `PASSED` |
| T-202 | DONE | `capture.*` (migration `0014`); run `38760592674` |
| T-203 | TODO | READY · **đủ điều kiện bắt đầu** · Upload, quét mã độc; chủ TC-JOB-05 (D-56) |
| T-204 | TODO | READY · **đủ điều kiện bắt đầu** · Provider adapter + giả lập (cần làm rõ D-50 trước — OPEN_DECISIONS 0.1) |
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
| T-301 | DONE | `ai.*` (migration `0013`), Tool Registry, trần autonomy, kill switch singleton; run `38757933594`; Q-53 |
| T-302 | TODO | READY · **đủ điều kiện bắt đầu** · Write gateway |
| T-303 | TODO | READY · Kill switch; chờ T-302 |
| T-304 | TODO | READY · Bản nháp, hoàn tác; chờ T-302, T-010 |
| T-305 | TODO | READY · **đủ điều kiện bắt đầu** · Cấu hình autonomy |
| T-306 | TODO | PARTIAL · Chat AI SSE (chat chỉ đọc vẫn chạy khi kill switch bật — D-48); chờ T-204, T-108 |
| T-307 | TODO | READY · Phản hồi, harness đánh giá; chờ T-306 |
| T-308 | TODO | READY · **Mới (D-49)** Frontend panel chat AI; chờ T-306, T-111 |

### P4 – Finance Lite

| Task | Trạng thái | Ghi chú ngắn |
|------|------------|--------------|
| T-401 | DONE | `finance.*` (migration `0012`), INV-01…07 ở CSDL; run `38755214148`; TC-FIN-01…04 `PASSED` |
| T-402 | TODO | PARTIAL (người giữ `finance.period.manage` chưa giao) · **đủ điều kiện bắt đầu** · Kỳ báo cáo |
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
| T-501 | DONE | `goals.*` (migration `0015`), API-GOAL-01/02/03/05/06; run `38764880704` |
| T-502 | TODO | PARTIAL (vòng đời Q-28) · **đủ điều kiện bắt đầu** · Kích hoạt: CEO cấp công ty, MANAGER cấp đơn vị; chờ T-501, T-109 |
| T-503 | TODO | READY · Mục tiêu từ tài liệu; chờ T-206, T-302, T-501 |
| T-504 | TODO | PARTIAL (quy tắc điền check-in từ task — Q-29) · chờ T-501, T-502 |
| T-505 | DONE | `work.task` (migration `0011`), tạo/sửa/hoàn thành/mở lại, danh sách theo phạm vi; run `38752643215`; TC-WRK-01…05 `PASSED`; TC-ACC-03 phần task (chờ T-502) |
| T-506 | TODO | READY · Biên bản → việc; chờ T-206, T-302, T-505 |
| T-507 | TODO | READY · **đủ điều kiện bắt đầu** · Job task quá hạn |
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
| T-603 | TODO | READY · Đồng thời, idempotency; chờ T-404, T-405 |
| T-604 | BLOCKED | Hiệu năng; cần provider thật (T-205) |
| T-605 | TODO | READY · Backup/restore, chủ TC-DR-01/02, TC-MIG-02; chờ T-013, T-203, T-008, T-101, T-107, T-301, T-302, T-401, T-403 |
| T-606 | TODO | READY · Benchmark (dataset giai đoạn 1 đã duyệt, D-08); chờ T-204 |
| T-607 | TODO | READY · **đủ điều kiện bắt đầu** · WCAG, i18n |
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

1. Merge PR #32 (T-201) khi CDA đồng ý. Demo đăng nhập đầu-cuối: `infra/README.md`.
   Ứng viên tiếp theo (không cần mục 0): T-505 (task, chủ TC-ACC-03), T-202 (bảng capture), T-501 (mục tiêu — Q-28/Q-29 đã điền ở mục 0, chưa ghi Decision_Log), T-401 (finance). T-204/T-205 chờ D-50.
2. **T-003** song song (reverse proxy HTTPS — cookie `Secure` cần HTTPS để demo trên trình duyệt).
3. T-013 khi T-003 xong → T-605 về sau.
4. CDA điền OPEN_DECISIONS mục 0 trước khi tới T-204 (D-50) và T-108 (TC-ACC-10).

## 6. Ghi chú phiên gần nhất

**Phiên 15/10/2026 (lần 19) — "hoàn thành tất cả task đã sẵn sàng" (T-505, …):**
- CDA: hoàn thành 8 task đủ điều kiện (T-505, T-401, T-301, T-202, T-501, T-204, T-112, T-607); agent merge từng PR khi CI xanh để tránh xung đột tài liệu. PR #32 (T-201) merge → `42518d2`.
- T-505: PR #33, CI run `38752643215` xanh → `DONE`; TC-WRK-01…05 `PASSED`. Chi tiết: Implementation_Plan §10, §35.
- T-401: PR #34, CI run `38755214148` xanh → `DONE`; TC-FIN-01…04 `PASSED`. Chi tiết: Implementation_Plan §10, §36. PR #33 (T-505) merge → `6ba9bcf`.
- T-301: PR #35, CI run `38757933594` xanh → `DONE`. Q-53 mới (CHECK `call_log` vs ngoại lệ demo D-50). PR #34 (T-401) merge → `3286674`. Chi tiết: Implementation_Plan §10, §37.
- T-202: PR #36, CI run `38760592674` xanh → `DONE`. PR #35 (T-301) merge → `3ee8730`. Chi tiết: Implementation_Plan §10, §38.
- T-501: PR #37, CI run `38764880704` xanh → `DONE`; TC-GOAL-01, 03…06 `PASSED`, TC-GOAL-02 `NOT RUN` (bề mặt chưa có). Sửa hồi quy T-202 (composition root nạp mọi model). T-502 vừa đủ điều kiện (PARTIAL — không làm trong đợt này). PR #36 (T-202) merge → `110e561`. Chi tiết: Implementation_Plan §10, §39.

**Phiên 15/10/2026 (lần 18) — T-201:**
- PR #31 (T-013) merge → `dd22085`, CI `main` xanh. CDA chạy demo trên máy (chờ phản hồi); CDA yêu cầu "tiếp tục triển khai" → agent chọn T-201 (không phụ thuộc mục 0).
- T-201: migration `0010`, module `org`, API-ORG-01/02, `OrgDirectoryScope`; 7 đột biến → test đỏ. Local: `compose-smoke` không chạy được vì stack demo của CDA đang giữ cổng 443 (lỗi môi trường). PR #32, CI run `38737949724` xanh (pytest 312, vitest 62, compose-smoke 0 lỗi) → T-201 `DONE`; TC-ACC-09 `PASSED`. Chi tiết: Implementation_Plan §10, §34.

**Phiên 15/10/2026 (lần 17) — T-013:**
- PR #30 (T-111) merge → `2457914`, CI `main` xanh.
- T-013: Dockerfile backend (thêm `uvicorn` còn thiếu) và proxy (đóng gói frontend), init CSDL + secret, healthcheck worker/scanner-updater, `scripts/compose_smoke.py` (demo đầu-cuối qua HTTPS + TC-NFR-01) trong `ci.sh`; CI `postgres:18.6`. Smoke local 1 phút 44 giây; kiểm âm `api` có đường ra → lỗi. PR #31, CI run `38722522003` xanh (pytest 307, vitest 62, compose-smoke 0 lỗi) → T-013 `DONE`; TC-NFR-01 `PASSED`. Chi tiết: Implementation_Plan §10, §33.

**Phiên 15/10/2026 (lần 16) — T-111:**
- PR #29 (T-003) merge → `57eb61d`, CI `main` xanh. CDA: DeepSeek/đường ra internet xử lý ở T-204/T-205; đồng ý ghim CI `postgres:18.6` (làm cùng T-013).
- T-111: frontend (API client `/api/v1`, phiên, đăng nhập, MFA, lời mời, app shell ẩn mục không quyền, quản trị người dùng/quyền, reauth, trạng thái chung); 15 test mới, TC-FE-01/02 chỉnh tối thiểu; 9 đột biến → test đỏ. PR #30, CI run `38719094857` xanh (vitest 62, pytest 305) → T-111 `DONE`. Chi tiết: Implementation_Plan §10, §32.

**Phiên 15/10/2026 (lần 15) — T-003:**
- PR #28 (T-105) merge → `feaaf5a`, CI `main` xanh. CDA: endpoint hủy lời mời — tạm giữ hành vi hiện tại (thu hồi khi cấp lại), ghi `[CẦN XÁC NHẬN]`.
- T-003: `infra/compose.yaml`, `infra/caddy/Caddyfile`, `scripts/check_compose.py` (bước `compose`, CI `AIEOS_REQUIRE_DOCKER=1`); 12 vi phạm tiêm + Caddyfile sai → đều bị bắt. PR #29, CI run `38712655012` xanh (bước `compose` chạy thật, 0 lỗi) → T-003 `DONE`. Chi tiết: Implementation_Plan §10, §31.

**Phiên 15/10/2026 (lần 14) — T-105:**
- PR #27 (T-109) merge → `b978db5`, CI `main` xanh.
- T-105: `identity/invitations.py`, API-ADM-02/03, API-AUTH-08, migration `0009`; `scripts/ci.sh` local rc 0 (305 passed); 10 đột biến → 9 test đỏ, 1 lớp "một lần dùng" trùng lặp có chủ đích (bỏ cả hai lớp → đỏ). PR #28, CI run `38710976904` xanh (305 passed, 0 skipped) → T-105 `DONE`; TC-AUD-02 đạt tổng. Chi tiết: Implementation_Plan §10, §30.

**Phiên 15/10/2026 (lần 13) — T-109:**
- PR #26 (T-104) merge → `671d57c`, CI `main` xanh.
- T-109: `identity/users.py`, `access/router.py`, `set_roles`, migration `0008`; `scripts/ci.sh` local rc 0 (297 passed); 9 đột biến → test đỏ (đột biến "không thu hồi session khi khóa" ban đầu lọt → thêm kiểm "mở khóa không làm session cũ sống lại"). Test TC-ACC-06 bắt deadlock thật (thứ tự khóa) → đã sửa. PR #27, CI run `38708289449` xanh (297 passed, 0 skipped) → T-109 `DONE`. Chi tiết: Implementation_Plan §10, §29.

**Phiên 15/10/2026 (lần 12) — T-104:**
- PR #25 (T-108) merge → `c62a0ed`, CI `main` xanh.
- D-59 (CDA): TC-ACC-03 → chủ T-505, phần mục tiêu T-502 (đóng Q-52).
- T-104: `identity/stepup.py`, `require_step_up`, `revoke_sessions`, API-AUTH-05/09; `scripts/ci.sh` local rc 0 (286 passed); 9 đột biến → test đỏ. PR #26, CI run `38705903816` xanh (286 passed, 0 skipped) → T-104 `DONE`. Chi tiết: Implementation_Plan §10, §28.

**Phiên 15/10/2026 (lần 11) — T-108:**
- PR #24 (T-103) merge → `6590c6d`, CI `main` xanh.
- T-108 (phần có căn cứ, CDA cho bỏ qua "team"): `access/policy.py` + khai báo quyền bắt buộc ở `platform/web.py`; mọi route hiện có đã khai báo. `scripts/ci.sh` local rc 0 (280 passed); 10 đột biến → test đỏ. PR #25, CI run `38703355287` xanh (280 passed, 0 skipped) → T-108 `DONE`. Q-52 mới: task chủ TC-ACC-03 (không chạy đủ ở T-108). Chi tiết: Implementation_Plan §10, §27.

**Phiên 15/10/2026 (lần 10) — T-103:**
- PR #23 (T-106) merge → `86d5a32` (đồng bộ `main` vào nhánh, không force-push), CI `main` xanh.
- T-103: `identity/mfa.py` (TOTP RFC 6238, AES-256-GCM, mã khôi phục), API-AUTH-02/03/04, `rotate_session`, migration `0007` (`mfa_last_step`), `cryptography` 50.0.2; response đăng nhập thêm `mfa_enrolled`, `csrf_token` (API_Specification cập nhật trước). `scripts/ci.sh` local rc 0 (271 passed); 9 đột biến → test đỏ (đột biến "không thu hồi session cũ" ban đầu lọt → sửa test). PR #24, CI run `38700993783` xanh (271 passed, 0 skipped) → T-103 `DONE`. Chi tiết: Implementation_Plan §10, §26.

**Phiên 15/10/2026 (lần 9) — T-010, T-106:**
- PR #21 (T-102) merge → `f1ce538`, CI `main` xanh.
- T-010: migration `0006` + module `notify` (service, API-NOT-01/02, phân trang cursor ở `platform`); `scripts/ci.sh` local rc 0 (248 passed); 4 đột biến → test đỏ. PR #22, CI run `38696839691` xanh (248 passed, 0 skipped) → T-010 `DONE`. Chi tiết: Implementation_Plan §10, §24.
- T-106: `identity/admin.py` + `app/admin_cli.py`, `access.api.active_admins`, tiến trình loader `admin-cli`, `AIEOS_PASSWORD_MIN_LENGTH`; `scripts/ci.sh` local rc 0 (259 passed); 8 đột biến → test đỏ (đột biến bỏ advisory lock ban đầu không bị bắt → viết lại test tranh chấp có barrier). PR #23 (base `feat/T-010-notifications`), CI run `38697852135` xanh (259 passed, 0 skipped) → T-106 `DONE`. Chi tiết: Implementation_Plan §10, §25.
- PR #22 (T-010) merge → `aa1061b`. CDA đã điền OPEN_DECISIONS mục 0 trong working tree (chưa commit) — CDA quyết định sau trong PR tài liệu riêng; không xử lý trong PR task. CDA chấp nhận các lựa chọn kỹ thuật của T-010/T-106; `recover-admin` giữ chỉ khôi phục ADMIN `ACTIVE` (`[CẦN XÁC NHẬN]`, Implementation_Plan §25).

**Phiên 15/10/2026 (lần 8) — T-102:**
- PR #20 (T-107) merge → `7429117`, CI `main` run `38685297396` xanh.
- D-58 (CDA): T-106 ← T-010 ← T-102 (thứ tự demo T-102 → T-010 → T-106 → T-103); TC-NTF-01 chủ T-510; `AIEOS_PASSWORD_MIN_LENGTH`.
- T-102: đăng nhập/session/logout/me; `scripts/ci.sh` local rc 0 (242 passed); 7 đột biến → test đỏ; sửa lỗi lộ thời gian (email không tồn tại) do test TC-IAM-03 bắt. PR #21, CI run `38686690047` xanh (242 passed, 0 skipped) → T-102 `DONE`. Chi tiết: Implementation_Plan §10, §23.

**Phiên 15/10/2026 (lần 7) — T-107:**
- PR #19 (T-101) merge → `60c55e4`, CI `main` run `38683918733` xanh.
- T-107: migration `0005` + module `access` (seed theo Architecture §6, INV-09/10/11, assignment, service); `scripts/ci.sh` local rc 0; 5 đột biến → test đỏ. PR #20, CI run `38684667496` xanh (231 passed, 0 skipped) → T-107 `DONE`. Chi tiết: Implementation_Plan §10, §22.

**Phiên 15/10/2026 (lần 6) — T-101:**
- PR #18 (T-007) merge → `46fa612`, CI `main` run `38682923035` xanh.
- D-57 (CDA): rate limit là biến cấu hình bắt buộc, không mặc định — tên biến ở Implementation_Plan §7.
- T-101: migration `0004` + module `identity` (bảng, hàm băm token); `scripts/ci.sh` local rc 0; 4 đột biến → test đỏ. PR #19, CI run `38683463269` xanh (221 passed, 0 skipped) → T-101 `DONE`. Chi tiết: Implementation_Plan §10, §21.

**Phiên 15/10/2026 (lần 5) — T-007:**
- PR #17 (T-009) merge → `f012775`, CI `main` run `38680968482` xanh.
- T-007: code + test; `scripts/ci.sh` local rc 0 (PostgreSQL 18.6, 213 passed); 6 đột biến → test đỏ. PR #18, CI run `38681777001` xanh (213 passed, 0 skipped) → T-007 `DONE`, TC-GEN-01…05 `PASSED`. Idempotency theo INV-08 (không bảng trung tâm); rate limit không có giá trị mặc định. Chi tiết: Implementation_Plan §10, §20.

**Phiên 15/10/2026 (lần 4) — T-009:**
- PR #16 (T-008) merge → `1101438`, CI `main` run `38679074230` xanh.
- D-56 (CDA): TC-JOB-05 chủ T-203; tham số kỹ thuật queue `PROPOSED` (lease 300 s, backoff, poll 1 s, reaper/scheduler 30 s); lịch chỉ `interval`, không chạy bù; tách M-05.
- T-009: code + test; `scripts/ci.sh` local rc 0 (PostgreSQL 18.6, 177 passed); 9 đột biến → test đỏ. PR #17, CI run `38680383606` xanh (177 passed, 0 skipped) → T-009 `DONE`, TC-JOB-01…04, 06 `PASSED`. Chi tiết: Implementation_Plan §10, §19.

**Phiên 15/10/2026 (lần 3) — T-008:**
- PR #15 (tài liệu D-44…D-54) merge → `99e477c`, CI `main` run `38676541858` xanh.
- D-55 (CDA): TC-AUD-01 chủ T-109; TC-AUD-02 tách phần, tổng ở T-105 (thêm T-103, T-104 vào dependency T-105); T-008 chỉ làm chủ TC-AUD-03.
- T-008: code + test; `scripts/ci.sh` local rc 0 với PostgreSQL 18.6 (container tạm); đột biến → test đỏ. PR #16, CI run `38678659141` xanh (144 passed, 0 skipped) → T-008 `DONE`, TC-AUD-03 `PASSED`. Chi tiết: Implementation_Plan §10, §18.

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
