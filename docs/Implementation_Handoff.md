# AI-EOS — Implementation Handoff (checkpoint trước triển khai)

> Ngày: 12/10/2026, cập nhật 14/10/2026 (mục 11–14) · Loại: checkpoint bàn giao, **không** phải tài liệu yêu cầu. Nguồn sự thật vẫn là các tài liệu được liên kết; nếu checkpoint này lệch với chúng, tài liệu gốc thắng.
> Trạng thái: tài liệu Stage 2A–2D đã hoàn thành (baseline commit `683f847`); T-001 (khung repo) `DONE` (commit `318689c`, GitHub Actions run `38257197546`); T-002 (toolchain + CI) `DONE` (branch protection `main`: required check `ci`, PR bắt buộc, `enforce_admins`; PR đỏ #2 bị chặn merge — HTTP 405); T-012 (nền tảng frontend) `IN_REVIEW` (14/10/2026, mục 11); T-004 (cấu hình/secret) `DONE` (14/10/2026, mục 13); T-005, T-006, T-011 `IN_REVIEW` (14/10/2026, mục 14, Q-51); xem Implementation_Plan §10; chưa có test nào trong TEST_Plan được chạy.

## 1. Đọc trước

| Thứ tự | File | Vai trò |
| --- | --- | --- |
| 1 | [CLAUDE.md](../CLAUDE.md) | Quy tắc cho coding agent |
| 2 | [Implementation_Plan.md](04-delivery/Implementation_Plan.md) (1.0) | Task, dependency, DoD |
| 3 | [TEST_Plan.md](04-delivery/TEST_Plan.md) (1.0) | Test case, benchmark, AC-ARCH |
| 4 | [SRS.md](02-requirements/SRS.md) (1.1) | Yêu cầu phần mềm |
| 5 | [Architecture.md](03-architecture/Architecture.md) (1.2), [Database_Design.md](03-architecture/Database_Design.md) (1.2), [API_Specification.md](03-architecture/API_Specification.md) (1.2), [ADR](03-architecture/decisions/) | Thiết kế |
| 6 | [Decision_Log.md](00-source/Decision_Log.md) (0.7) | Quyết định, câu hỏi mở |
| 7 | [Requirements_Traceability.md](00-source/Requirements_Traceability.md) (0.6) | Truy vết requirement → PRD → SRS → API → Task → Test |
| 8 | [Documentation_Review.md](04-delivery/Documentation_Review.md) | Tổng kết tài liệu |

## 2. Trạng thái các Stage

| Stage | Trạng thái | Ghi chú |
| --- | --- | --- |
| 1 / 2A | Hoàn thành | AI-EOS độc lập, A-EMS ngoài phạm vi (D-04, D-05) |
| 2B | Hoàn thành, CDA duyệt có điều kiện | PRD, SRS, UX_Flows 1.1; Personas, User_Journeys, Product_Vision, Business_OKRs 1.0. M3/M4/M5 đặc tả một phần; Sales Lite chưa đặc tả |
| 2C | Hoàn thành | 13 ADR (ADR-005, ADR-008, ADR-009 có Amendment 1); API ở `DESIGNED`, Sales `SKELETON` |
| 2D | Hoàn thành tài liệu, **chờ CDA duyệt** | Implementation_Plan, TEST_Plan, CLAUDE.md, Documentation_Review |
| Triển khai | Bắt đầu | T-001 `DONE`, T-002 `DONE` (Implementation_Plan §10); task khác `TODO`; mọi TC trong TEST_Plan `NOT RUN`; không requirement nào `IMPLEMENTED`/`VERIFIED` |

## 3. Kiến trúc và tech stack (đã chốt)

| ADR | Quyết định | Trạng thái |
| --- | --- | --- |
| ADR-001 | Modular monolith + worker, một PostgreSQL | CONFIRMED · Amendment 1 (D-42: thêm `platform`, `app`; danh sách module = Architecture §3) |
| ADR-002 | Python, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 | CONFIRMED · Amendment 1 (D-42) |
| ADR-003 | React + Vite + TypeScript strict + PWA; Tailwind + shadcn/ui | CONFIRMED |
| ADR-004 | PostgreSQL; storage adapter (volume cục bộ); backup ngoài máy | CONFIRMED |
| ADR-005 | Job queue trên PostgreSQL (claim `SKIP LOCKED`, lease, retry, outbox) | CONFIRMED · Amendment 1 |
| ADR-006 | Session phía server, Argon2id, CSRF, MFA bắt buộc cho ADMIN; lời mời một lần; bootstrap/recovery qua CLI | CONFIRMED |
| ADR-007 | Role → permission → assignment, policy tập trung, mặc định deny | CONFIRMED |
| ADR-008 | AI write gateway: quyền → autonomy → kill switch → idempotency → audit | CONFIRMED · Amendment 1 |
| ADR-009 | Giao dịch tài chính: state machine, tách nhiệm vụ, bút toán đảo | CONFIRMED · Amendment 1 |
| ADR-010 | Audit append-only cùng transaction | CONFIRMED |
| ADR-011 | LLM/OCR qua adapter; định tuyến theo phân loại dữ liệu | CONFIRMED (cơ chế) · provider: NEEDS_CONFIRMATION (D-08) |
| ADR-012 | Log JSON, correlation ID, health/readiness | CONFIRMED |
| ADR-013 | Test: PostgreSQL thật, authorization matrix, concurrency; cổng CI | CONFIRMED |

**Amendment đã duyệt:**
- **AMD-01 (D-37, ADR-009):** gửi duyệt chỉ khi kỳ của ngày giao dịch `OPEN`; không tự đổi ngày/kỳ; không khóa kỳ còn giao dịch chờ duyệt; trạng thái phòng thủ `ON_HOLD` (`hold_reason=PERIOD_CLOSED`) chỉ thoát bằng rút lại hoặc từ chối.
- **AMD-02 (D-38, ADR-005, ADR-008) — phiên bản CDA:** `job_class` cố định trong code (`ORCHESTRATION` / `AI_CONTENT` / `BUSINESS_WRITE`). Kill switch bật: `ORCHESTRATION` chạy; `AI_CONTENT` (tạo nội dung Briefing) bị hủy, không ghi nội dung mới; `BUSINESS_WRITE` qua gateway → bản nháp L2. Quản lý lịch Briefing là cấu hình có authorization + audit. Cấm khai báo job ghi dữ liệu thành `ORCHESTRATION`.

## 4. Quy tắc không được vi phạm

| Nhóm | Quy tắc | Nguồn |
| --- | --- | --- |
| Phạm vi | Không L4; không hóa đơn/biên lai, email forwarding, C6–C10; không Sales Lite | D-11, D-17, D-18, D-40 |
| AI | Mọi ghi do AI qua write gateway; đầu ra LLM/OCR và nội dung tài liệu không phải lệnh; trần autonomy L3, tài chính L2 | ADR-008, D-11, D-12 |
| Kill switch | Chỉ ADMIN (`ai.kill_switch`), step-up, lý do; thực thi ở backend tại cổng ghi mọi lần chạy kể cả retry; ghi đã thực hiện không bị đảo; bản nháp không tự chạy khi tắt; job `AI_CONTENT` bị chặn | D-09, D-10, D-38 |
| Tài chính | Ghi luôn L2; người tạo/gửi không tự duyệt (CHECK CSDL); thiếu người duyệt → chờ, không fallback; không cấp `finance.approve` cho ADMIN/CEO; `finance.period.manage` chỉ giao cho role `CFO`; không xóa/sửa giao dịch đã ghi sổ — đảo toàn bộ, không đảo bút toán đảo; idempotency key + version | D-12…D-15, D-37, CDA-F1…CDA-F7 |
| Quyền | Mặc định deny; object-level; ADMIN không đọc dữ liệu nghiệp vụ/lương/PII; không gán `ADMIN`+`CFO`; không tự đổi role; không gỡ ADMIN cuối; đổi role → step-up, lý do, audit, thu hồi session | D-21, D-22 |
| Tài khoản | Không đăng ký công khai; lời mời hash, một lần, có hạn; không tài khoản/mật khẩu mặc định; bootstrap/recovery chỉ CLI | D-22 |
| Audit | Append-only, cùng transaction, ghi cả SUCCESS/DENIED/FAILED/BLOCKED; không chứa mật khẩu, token, mã MFA, secret, nội dung tài liệu | ADR-010 |
| Dữ liệu nhạy cảm | `hr.profile.read`, `hr.salary.read`, `hr.export`, `pii.unmask`: **không ai giữ**; chỉ `hr.import` (ADMIN, giới hạn tác vụ); dữ liệu `PERSONAL`/`SENSITIVE` không gửi provider ngoài | R6, ADR-011 |
| Chỉ số | Không tính % đạt; 4 ô chỉ số có nhãn "chưa chính thức", không cảnh báo; không tuyên bố đạt MET/NFR khi chưa đo | D-39 |
| Secret | Không commit; không giá trị mặc định; thiếu → dừng tiến trình | Implementation_Plan §7 |

## 5. Task

Tổng **81 task**: **55 READY** (gồm T-605 "READY — công cụ cụ thể chọn khi triển khai" và T-012 thêm ngày 12/10/2026), **13 PARTIAL**, **13 BLOCKED** (cập nhật 14/10/2026 theo D-43: T-003 chuyển `BLOCKED`, thêm T-013 `BLOCKED`). Thực thi: T-001 `DONE` (run `38257197546`), T-002 `DONE` (branch protection + PR #2 bị chặn), các task khác `TODO` (Implementation_Plan §10). `READY` chỉ nghĩa là đủ căn cứ; task chỉ được bắt đầu khi mọi dependency `DONE`. Ngoại lệ duy nhất: T-002 được bắt đầu khi T-001 `IN_REVIEW` (CDA 12/10/2026; Implementation_Plan §1, "Điều kiện bắt đầu"). Test case: **199**, tất cả `NOT RUN`.
Tiêu chí nghiệm thu mỗi task = DoD chung (Implementation_Plan §2) + DoD riêng của task + các test case dưới đây xanh. Cột "Test case" gồm TC ghi trong DoD của task và TC phủ các SRS của task (TEST_Plan).

| ID | Giai đoạn | Sẵn sàng | Phụ thuộc | Requirement (SRS) | Test case | Ghi chú |
| --- | --- | --- | --- | --- | --- | --- |
| T-001 | P0 | READY | — | ADR-001, ADR-002, ADR-003 | — |  |
| T-002 | P0 | READY | T-001 | ADR-013, ADR-001 | — |  |
| T-003 | P0 | BLOCKED | T-001 | SRS-NFR-04 | — | Compose — cấu hình (D-43); công cụ chờ CDA duyệt; Q-50 |
| T-004 | P0 | READY | T-001 | ADR-006, ADR-011 | — |  |
| T-005 | P0 | READY | T-002, T-004 | SRS-NFR-03 | TC-DR-01…02, TC-MIG-01…02 |  |
| T-006 | P0 | READY | T-001 | SRS-GEN-05 | TC-GEN-05, TC-SEC-05 |  |
| T-007 | P0 | READY | T-005 | SRS-GEN-01, SRS-GEN-02, SRS-GEN-03, SRS-GEN-04, SRS-GEN-05 | TC-GEN-01…06, TC-SEC-05 |  |
| T-008 | P0 | READY | T-005 | SRS-AUD-01, SRS-AUD-02, SRS-AUD-03 | TC-AUD-01…03 |  |
| T-009 | P0 | READY | T-005, T-008 | SRS-JOB-01, SRS-JOB-02, SRS-JOB-03, SRS-AIC-06 | TC-JOB-01…06, TC-KS-07…09 |  |
| T-010 | P0 | READY | T-005 | SRS-NTF-01, SRS-NTF-02 | TC-NTF-01 |  |
| T-011 | P0 | READY | T-004 | SRS-CAP-03 | TC-FILE-03 |  |
| T-012 | P0 | READY | T-001, T-002 | ADR-003 | — (TC dự kiến: Implementation_Plan §12) | Nền tảng frontend: Tailwind + shadcn/ui, React Router, TanStack Query, manifest + service worker PWA (chỉ cache tài nguyên tĩnh). Dependency T-001, T-002 đã `DONE`; `IN_REVIEW` 14/10/2026 (mục 11). Q-45, D-41 |
| T-013 | P0 | BLOCKED | T-003, T-004, T-005, T-006, T-009 | SRS-NFR-04 | TC-NFR-01 | Compose — tích hợp (D-43); công cụ chờ CDA duyệt; Q-50 |
| T-101 | P1 | READY | T-005 | SRS-IAM-06 | TC-IAM-02, TC-IAM-05 |  |
| T-102 | P1 | READY | T-101, T-007 | SRS-IAM-04, SRS-IAM-06, SRS-IAM-07, SRS-GEN-01 | TC-GEN-06, TC-IAM-01…05 |  |
| T-103 | P1 | READY | T-102 | SRS-IAM-05 | TC-IAM-06…07 |  |
| T-104 | P1 | READY | T-102 | SRS-IAM-08, SRS-IAM-11 | TC-ACC-08, TC-IAM-08 |  |
| T-105 | P1 | READY | T-102, T-108 | SRS-IAM-01, SRS-IAM-02, SRS-IAM-03 | TC-IAM-09…10, TC-IAM-13 |  |
| T-106 | P1 | READY | T-101, T-107 | SRS-IAM-09, SRS-IAM-10 | TC-IAM-11…12 |  |
| T-107 | P1 | READY | T-101 | SRS-ACC-05, SRS-ACC-06, SRS-ACC-07, SRS-ACC-08 | TC-ACC-04…07 |  |
| T-108 | P1 | PARTIAL | T-107 | SRS-ACC-01, SRS-ACC-02, SRS-ACC-03, SRS-ACC-09, SRS-ACC-11 | TC-ACC-01…03, TC-ACC-09 | SRS-ACC-04 (định nghĩa "team") dùng mặc định PROPOSED |
| T-109 | P1 | READY | T-108, T-104 | SRS-ACC-05, SRS-ACC-06, SRS-ACC-07, SRS-ACC-08, SRS-IAM-11 | TC-ACC-04…08, TC-IAM-08 |  |
| T-110 | P1 | READY | T-109, T-009 | SRS-AUD-04, SRS-FIN-12 | TC-AUD-04, TC-FIN-12…15 |  |
| T-111 | P1 | READY | T-102…T-109, T-012 | SRS-ACC-09, SRS-GEN-06 | TC-ACC-02, TC-E2E-01, TC-GEN-07 |  |
| T-112 | P1 | PARTIAL | T-108 | SRS-ACC-10, SRS-PRV-02 | TC-PRV-01…04, TC-SEC-06 | người giữ `hr.profile.read`, `hr.salary.read`, `hr.export`, `pii.unmask` chờ R6; không ai giữ |
| T-201 | P2 | READY | T-108 | SRS-ACC-11 | TC-ACC-09 |  |
| T-202 | P2 | READY | T-005, T-201 | SRS-CAP-13, SRS-REV-07, SRS-REV-09 | TC-CAP-02, TC-REV-04 |  |
| T-203 | P2 | READY | T-202, T-011, T-009 | SRS-CAP-01, SRS-CAP-02, SRS-CAP-03, SRS-CAP-04, SRS-CAP-05, SRS-CAP-06, SRS-CAP-07 | TC-FILE-01…08 |  |
| T-204 | P2 | READY | T-004, T-009 | SRS-PRV-01, SRS-PRV-02, SRS-PRV-03, SRS-PRV-04, SRS-NFR-07 | TC-NFR-04, TC-PRV-04…07, TC-SEC-06 |  |
| T-205 | P2 | BLOCKED | T-204, T-606 | SRS-PRV-01 | TC-PRV-07 | D-08 |
| T-206 | P2 | PARTIAL | T-203, T-204, T-302 | SRS-CAP-08, SRS-CAP-10, SRS-CAP-11, SRS-CAP-12, SRS-CAP-14, SRS-CAP-15, SRS-CAP-16, SRS-CAP-17, SRS-CAP-18, SRS-CAP-20, SRS-CAP-21, SRS-CAP-22 | TC-CAP-01…08, TC-CAP-14…16 | danh mục đơn vị hành chính (GAP-13), danh sách trường trọng yếu (D-16), ngưỡng (D-29) dùng mặc định an toàn |
| T-207 | P2 | PARTIAL | T-206, T-108, T-012 | SRS-REV-01, SRS-REV-02, SRS-REV-03, SRS-REV-04, SRS-REV-05, SRS-REV-06, SRS-REV-07, SRS-REV-08, SRS-REV-09, SRS-NFR-10 | TC-NFR-07, TC-REV-01…07 | SLA (GAP-18) là cấu hình trống |
| T-208 | P2 | READY | T-206 | SRS-CAP-15, SRS-CAP-16, SRS-CAP-17 | TC-CAP-04…06, TC-CAP-15 |  |
| T-209 | P2 | READY | T-206, T-204 | SRS-CAP-30, SRS-CAP-31, SRS-CAP-32, SRS-CAP-33, SRS-CAP-34 | TC-CAP-09…11 |  |
| T-210 | P2 | READY | T-206, T-302 | SRS-IMP-01, SRS-IMP-02, SRS-IMP-03 | TC-IMP-01…04 |  |
| T-211 | P2 | READY | T-206 | SRS-CAP-19, SRS-BRF-04 | TC-CAP-12 |  |
| T-212 | P2 | READY | T-203, T-210, T-012 | SRS-CAP-09 | TC-CAP-17, TC-E2E-02 |  |
| T-301 | P3 | READY | T-005, T-107 | SRS-AIC-02, SRS-AIC-03 | TC-AIC-02…03 |  |
| T-302 | P3 | READY | T-301, T-108, T-008 | SRS-AIC-01, SRS-AIC-02, SRS-AIC-05, SRS-AIC-09, SRS-CAP-18 | TC-AIC-01…06, TC-CAP-08, TC-KS-03…06, TC-KS-10 |  |
| T-303 | P3 | READY | T-302, T-009 | SRS-AIC-04, SRS-AIC-05, SRS-AIC-06 | TC-JOB-06, TC-KS-01…10 |  |
| T-304 | P3 | READY | T-302, T-010 | SRS-AIC-07, SRS-AIC-08, SRS-AIC-10, SRS-AIC-11 | TC-AIC-07…11, TC-AIC-17 |  |
| T-305 | P3 | READY | T-301 | SRS-AIC-15 | TC-AIC-12 |  |
| T-306 | P3 | PARTIAL | T-204, T-108 | SRS-AIC-12, SRS-AIC-13 | TC-AIC-13…15 | chất lượng trả lời chờ provider thật (D-08) |
| T-307 | P3 | READY | T-306 | SRS-AIC-14, SRS-AIC-16 | TC-AIC-16 |  |
| T-401 | P4 | READY | T-005, T-107 | SRS-FIN-13, SRS-FIN-17 | TC-FIN-01…04, TC-FIN-19…20 |  |
| T-402 | P4 | PARTIAL | T-401, T-104 | SRS-FIN-12 | TC-FIN-12…15 | độ dài kỳ mặc định tháng (Q-31); người giữ `finance.period.manage` do CDA giao vận hành |
| T-403 | P4 | PARTIAL | T-401, T-402, T-010 | SRS-FIN-01, SRS-FIN-02, SRS-FIN-04, SRS-FIN-05, SRS-FIN-06, SRS-FIN-07, SRS-FIN-16 | TC-FIN-05…11 | danh mục (Q-42) là văn bản tự do |
| T-404 | P4 | READY | T-403 | SRS-FIN-08, SRS-FIN-09, SRS-FIN-17 | TC-FIN-03…04, TC-FIN-16…22 |  |
| T-405 | P4 | READY | T-404 | SRS-FIN-10, SRS-FIN-11 | TC-FIN-23…28 |  |
| T-406 | P4 | READY | T-404 | SRS-FIN-14 | TC-FIN-29 |  |
| T-407 | P4 | BLOCKED | T-406 | SRS-FIN-15 | TC-FIN-31 | Q-39 (định nghĩa burn ròng) |
| T-408 | P4 | READY | T-302, T-403 | SRS-FIN-03, SRS-REV-08 | TC-FIN-30, TC-REV-05 |  |
| T-409 | P4 | READY | T-403…T-406, T-012 | SRS-FIN-12 | TC-E2E-03, TC-FIN-12…15 |  |
| T-501 | P5 | PARTIAL | T-108, T-201 | SRS-GOAL-01, SRS-GOAL-02, SRS-GOAL-05, SRS-GOAL-06, SRS-GOAL-07, SRS-GOAL-09, SRS-GOAL-11 | TC-GOAL-01…06 | thang độ tự tin (Q-30) là cấu hình PROPOSED |
| T-502 | P5 | PARTIAL | T-501, T-109 | SRS-GOAL-03, SRS-GOAL-04 | TC-GOAL-07…09 | ai được giao: Q-28 |
| T-503 | P5 | READY | T-206, T-302, T-501 | SRS-GOAL-03, SRS-GOAL-06, SRS-GOAL-10 | TC-GOAL-03, TC-GOAL-08…09 |  |
| T-504 | P5 | PARTIAL | T-501, T-502, T-012 | SRS-GOAL-08 | TC-E2E-04, TC-GOAL-10 | điền sẵn check-in = giá trị đo gần nhất (PROPOSED); điền từ task bị chặn (Q-29) |
| T-505 | P5 | PARTIAL | T-108, T-201 | SRS-WRK-01, SRS-WRK-02, SRS-WRK-03, SRS-WRK-04, SRS-WRK-10 | TC-WRK-01…05 | mở lại bởi người giao, EMPLOYEE tự giao (PROPOSED); trạng thái mở rộng chờ Q-33 |
| T-506 | P5 | READY | T-206, T-302, T-505 | SRS-WRK-05, SRS-WRK-06, SRS-WRK-07, SRS-WRK-11 | TC-WRK-06…08 |  |
| T-507 | P5 | READY | T-009, T-505 | SRS-WRK-09 | TC-WRK-09 |  |
| T-508 | P5 | READY | T-304, T-505 | SRS-WRK-08 | TC-WRK-10 |  |
| T-509 | P5 | READY | T-505, T-506, T-012 | SRS-WRK-10 | TC-E2E-05, TC-WRK-05 |  |
| T-510 | P5 | PARTIAL | T-406, T-501, T-505, T-304 | SRS-BRF-01, SRS-BRF-02, SRS-BRF-03, SRS-BRF-04, SRS-BRF-05, SRS-BRF-06, SRS-BRF-07, SRS-BRF-08, SRS-BRF-09, SRS-BRF-12, SRS-SLS-03 | TC-BRF-01…07, TC-CAP-12, TC-SLS-01 | công thức ô PROPOSED (Q-37, D-39); ngưỡng "dữ liệu cũ" là cấu hình trống |
| T-511 | P5 | PARTIAL | T-510, T-303, T-204 | SRS-BRF-10, SRS-BRF-11, SRS-BRF-13 | TC-BRF-08…11, TC-KS-08…09 | giờ/tần suất PROPOSED (Q-36); chất lượng tóm tắt chờ D-08 |
| T-512 | P5 | READY | T-206, T-302 | FR-DCS-02 | TC-CAP-13 |  |
| T-601 | P6 | READY | T-107, các API | SRS-ACC-01, SRS-ACC-02, SRS-NFR-11 | TC-ACC-01…02, TC-SEC-01…04 |  |
| T-602 | P6 | READY | T-111, T-203, T-306 | SRS-NFR-11 | TC-SEC-01…04 |  |
| T-603 | P6 | READY | T-404, T-405, T-009 | SRS-GEN-03, SRS-GEN-04 | TC-GEN-03…05 |  |
| T-604 | P6 | BLOCKED | T-206, T-205 | SRS-NFR-01, SRS-NFR-02 | TC-PERF-01…02 | cần provider thật (D-08) để đo đại diện; có thể đo pipeline với adapter giả lập |
| T-605 | P6 | READY | T-005, T-013 | SRS-NFR-03 | TC-DR-01…02, TC-MIG-01…02 | READY (công cụ cụ thể chọn khi triển khai) |
| T-606 | P6 | READY | T-204 | SRS-NFR-09 | TC-NFR-06 |  |
| T-607 | P6 | READY | T-111 | SRS-NFR-05, SRS-NFR-08 | TC-NFR-02, TC-NFR-05 |  |
| T-608 | P6 | READY | Các task frontend, T-013 | SRS-NFR-06 | TC-E2E-01…06, TC-NFR-03 |  |
| T-901 | Bị | BLOCKED | — | SRS-SLS-01, SRS-SLS-02, FR-HM-04 | — | D-40, Q-38; điều kiện mở: CDA cung cấp đặc tả |
| T-902 | Bị | BLOCKED | — | SRS-WRK-12, F5, FR-HM-06 | — | Q-34; điều kiện mở: Mô hình workload |
| T-903 | Bị | BLOCKED | — | SRS-WRK-12 | — | Q-35, D-31; điều kiện mở: Quyết định lịch nội bộ/ngoài |
| T-904 | Bị | BLOCKED | — | SRS-GOAL-09 | — | Q-29, D-39; điều kiện mở: Công thức được duyệt |
| T-905 | Bị | BLOCKED | — | SRS-WRK-11 | — | Q-41; điều kiện mở: Quyết định phạm vi |
| T-906 | Bị | BLOCKED | — | SRS-GOAL-07 | — | Q-30; điều kiện mở: Nhịp check-in |
| T-907 | Bị | BLOCKED | — | SRS-ACC-10 | — | R6; điều kiện mở: CDA chỉ định người giữ |
| T-908 | Bị | BLOCKED | — | SRS-NTF-03 | — | D-11, D-17, D-18; điều kiện mở: Phase 2 |

## 6. Task BLOCKED và lý do

| Task | Lý do | Điều kiện mở |
| --- | --- | --- |
| T-003, T-013 | Công cụ `proxy`, `scanner` chưa được duyệt (D-43 `PROPOSED`); cập nhật chữ ký scanner vs TC-NFR-01 (Q-50) | CDA duyệt công cụ (Decision_Log mục 3.6.2) và trả lời Q-50 |
| T-205 | Provider LLM/OCR chưa chọn | D-08: benchmark (T-606) + CDA chọn |
| T-407 | Định nghĩa burn ròng | Q-39 |
| T-604 | Đo hiệu năng đại diện cần provider thật | D-08 (có thể đo pipeline với adapter giả lập) |
| T-901 | Sales Pipeline Lite | D-40, Q-38 |
| T-902 | Workload/quá tải | Q-34 |
| T-903 | Lịch | Q-35, D-31 |
| T-904 | % đạt, cảnh báo lệch | Q-29 |
| T-905 | Decision Log 30/60/90 | Q-41 |
| T-906 | Nhắc check-in | Q-30 |
| T-907 | Quyền xem dữ liệu nhân sự nhạy cảm | R6 |
| T-908 | Hạng mục Phase 2 | D-11, D-17, D-18 |

## 7. Quyết định nghiệp vụ còn mở và hành vi mặc định an toàn

| ID | Còn mở | Hành vi mặc định trong kế hoạch |
| --- | --- | --- |
| D-08 | Provider LLM/OCR | Adapter giả lập; benchmark dữ liệu tổng hợp không PII trước; dữ liệu thật chỉ khi được phê duyệt và xử lý; không gửi dữ liệu nhạy cảm ra ngoài |
| D-14 (phần) | Người giữ `finance.period.manage` | Chưa giao → không mở kỳ, không gửi/ghi sổ; Admin thấy cảnh báo |
| D-16, D-29 | Trường trọng yếu, ngưỡng | Mọi trường tiền trọng yếu; tự ghi tắt |
| D-21 (R6) | Người giữ quyền nhân sự nhạy cảm | Không ai giữ; dữ liệu che |
| D-20, D-23, D-28, D-31, D-33 | Chỉ số review, danh sách domain, bộ chỉ số, lịch, màn mobile | Như Decision_Log |
| D-27 (phần), D-30 (phần), D-32 (phần) | Sinh trắc học/offline; SSO; kênh ngoài | Không cam kết / DEFERRED |
| D-34, D-36 | Sửa tham chiếu CON-10/11; vị trí tài liệu | PROPOSED |
| Q-28 | Ai kích hoạt mục tiêu | `goals.activate` chỉ qua assignment, không quyền nền (D-39) |
| Q-29 | % đạt | Không tính (D-39) |
| Q-30…Q-35, Q-39, Q-41, Q-42 | Chi tiết M3–M6 | Xem Decision_Log §7 |
| Q-36 | Nội dung Briefing | Chỉ mục có nguồn truy vết; ẩn khối chưa đủ căn cứ (D-39) |
| Q-37 | Công thức ô chỉ số | PROPOSED, nhãn "chưa chính thức", không cảnh báo (D-39) |
| Q-38 | Sales Lite | Không triển khai (D-40) |
| ADR-008 Amendment 1 | Chat AI chỉ đọc khi kill switch bật | Hoạt động — **cần CDA xác nhận diễn giải** |

Q-40 đã được trả lời qua D-37.

## 8. Kiểm tra đã chạy và giới hạn

| Kiểm tra | Lệnh / cách | Kết quả thực tế |
| --- | --- | --- |
| Nhất quán tài liệu | `python3 scripts/check_docs.py --mermaid-modules <dir có mermaid, jsdom>` (chạy lại khi tạo checkpoint này) | 0 lỗi, 0 cảnh báo; 34 file (gồm checkpoint này), 69 link, 173 tham chiếu mục, 217 requirement, 18/18 sơ đồ Mermaid parse được |
| Kiểm tra âm script | Bản sao có lỗi cố ý (link, ID, quyền, trạng thái, phạm vi, task/test, file nguồn, D-xx) | Script phát hiện đủ các lỗi đã tiêm |
| File nguồn | md5 trong script | Không đổi |
| ID/trạng thái | So với bản chụp trước 2D | 217 requirement và 36 quyết định cũ giữ nguyên ID/trạng thái; thêm D-37…D-40 |

**Chưa xác minh:** không có code, không chạy test ứng dụng, Docker, migration; Mermaid chỉ kiểm cú pháp; field accuracy, thông lượng, latency, RPO/RTO chưa đo; persona chưa kiểm chứng; script không đánh giá đúng sai nghiệp vụ. Module `mermaid`/`jsdom` dùng cho kiểm tra nằm ngoài repo (scratchpad phiên làm việc); lần sau cần cài lại vào thư mục tạm.

## 9. Task đầu tiên đề xuất

**T-001 — Khung repo** (P0, READY, không phụ thuộc): `backend/` (package theo module ADR-001), `frontend/` (React + Vite + TS strict), `infra/` (Compose), giữ `docs/`.

Thứ tự tiếp theo (suy ra từ cột "Phụ thuộc" ở mục 5 / Implementation_Plan mục 4; `{…}` = cần tất cả, chạy song song được):
- **P0** (cập nhật 14/10/2026, D-43: xem Implementation_Plan §3): T-001 → {T-002, T-004} → T-005 → T-008 → T-009; T-003 chỉ cần T-001; T-013 cần T-003, T-004, T-005, T-006, T-009. Bản cũ: T-001 → {T-002, T-003} → T-005 → T-008 → T-009. Nhánh song song: T-004 và T-006 chỉ cần T-001; T-007 và T-010 cần T-005; T-011 cần T-004; T-012 (nền tảng frontend) cần T-001 và T-002 — là dependency của T-111, T-207, T-212, T-409, T-504, T-509. T-012 không thuộc ngoại lệ bắt đầu; dependency T-001, T-002 nay đã `DONE`.
- **Chuỗi dài nhất tính theo số task** (khớp Implementation_Plan dòng "Đường găng"): T-001 → {T-002, T-003} → T-005 → T-101 → T-102 → T-104 → T-402 → T-403 → T-404 → T-406 → T-510 → T-511. Đây **chưa phải** critical path theo thời lượng vì kế hoạch chưa có ước lượng.

**Điều kiện để bắt đầu T-001:**
1. CDA duyệt Implementation_Plan, TEST_Plan và CLAUDE.md (Documentation_Review §9).
2. **Quyết định quản lý mã nguồn:** `AI-EOS/` hiện là thư mục **untracked** trong git repo `CyEyes` (branch `feature/hr-service-lab`, đang có hàng nghìn file `A-EMS/` bị xóa chưa stage — không liên quan AI-EOS). Cần CDA chọn: repo git riêng cho AI-EOS, hoặc branch riêng trong `CyEyes`; không commit lẫn với thay đổi A-EMS (liên quan D-36).
3. Không cần provider AI, assignment tài chính hay câu trả lời Q-xx để làm T-001…T-011.

**Điều kiện bắt đầu T-002:** đáp ứng theo ngoại lệ duy nhất ở Implementation_Plan §1 — T-002 được bắt đầu khi T-001 `IN_REVIEW` (CDA 12/10/2026). T-001 vẫn `IN_REVIEW` đến khi đủ DoD.

**Điều kiện cho các giai đoạn sau** (không chặn T-001): assignment vận hành (`finance.period.manage`, ≥ 2 người `finance.approve`, `goals.activate`, hàng chờ review) trước nghiệm thu P4/P5; duyệt dataset benchmark trước T-606; xác nhận diễn giải chat khi kill switch bật trước T-303.

## 10. Nhật ký phiên 12/10/2026 và điểm bắt đầu phiên tiếp theo

Số liệu dưới đây đã được kiểm tra lại lúc ghi checkpoint (12/10/2026): HEAD = `origin/main` = `b7ba32d552982e2ec362c2cc8e95c0562f132fbe`, working tree sạch, run `38262327635` `completed`/`success` trên `b7ba32d`.

### 10.1. Đã hoàn thành

| Hạng mục | Kết quả | Bằng chứng |
| --- | --- | --- |
| T-001 — khung repo | `DONE` | Kiểm tra cấu trúc module chạy trong GitHub Actions run `38257197546` (commit `318689c`); trạng thái đồng bộ ở Plan §10, Handoff, Traceability §12 (commit `d1f7f26`, `2f30196`) |
| T-002 — toolchain + CI | `DONE` | Branch protection `main` đọc lại từ GitHub: required check `ci` (GitHub Actions app 15368), `enforce_admins: true`, bắt buộc PR (0 approval), cấm force-push và xóa `main`. PR #2 (CI đỏ) bị chặn: HTTP 405 `Required status check "ci" is failing.`. PR #3 merge sau khi CI xanh → commit `b7ba32d`, run `38262327635` `success` |
| Traceability | Đồng bộ | T-001, T-002 `DONE` ở §12; không trạng thái requirement nào thay đổi |
| Decision_Log D-41 | Đóng (0.10) | Ba điều kiện thực thi đã có bằng chứng (Decision_Log D-41, cột "Điều kiện đóng") |

### 10.2. Quy tắc Git bắt buộc từ nay

- Mọi thay đổi vào `main` đi qua Pull Request; required check `ci` phải xanh trước khi merge. Áp dụng cả cho thay đổi chỉ có tài liệu: branch → PR → CI xanh → merge.
- Không push trực tiếp vào `main` (branch protection sẽ từ chối); không force-push; không bypass branch protection (kể cả bằng quyền admin).
- Chỉ làm việc trong repository AI-EOS (`git@github.com:hovikhanh/AI-EOS.git`). Không sửa, stage hay commit repository cha `/home/vika/CyEyes` (HEAD `0a1a629`, 0 file staged lúc ghi checkpoint).

### 10.3. Trạng thái lúc kết thúc phiên

- T-001 `DONE`; T-002 `DONE`; T-012 `READY`, chưa bắt đầu; mọi task khác `TODO`.
- 80 task: 56 `READY`, 13 `PARTIAL`, 11 `BLOCKED` (cột "Sẵn sàng" — đủ căn cứ, không phải đã được giao).
- Mọi test case trong TEST_Plan vẫn `NOT RUN`; không requirement nào `IMPLEMENTED`/`VERIFIED`.
- Mở, không được tự đóng: Q-44 (amendment ADR-001), giả định C1 `[CẦN XÁC NHẬN]` (Implementation_Plan §11.4), câu hỏi frontend chưa có chủ cho chat AI và Trang chủ CEO (Implementation_Plan §12), các mục ở mục 7.

### 10.4. Hướng tiếp tục phiên sau

1. Đọc lại Handoff này; kiểm tra `git status --short --branch`, HEAD, `origin/main` và CI gần nhất của `main` trước khi làm việc.
2. Xem task graph ở Implementation_Plan §3, §4, §12. Chiều phụ thuộc của T-012: T-012 phụ thuộc **T-001, T-002** — cả hai đã `DONE`, nên dependency của T-012 đã đáp ứng. T-111, T-207, T-212, T-409, T-504, T-509 là các task **phụ thuộc vào T-012** (chúng chờ T-012), không phải điều kiện của T-012.
3. T-012 `READY` **không** có nghĩa được bắt đầu ngay: chỉ bắt đầu khi CDA giao task tiếp theo.
4. Trước khi làm bất kỳ task nào: đọc DoD (Implementation_Plan §2 và hàng của task), TEST_Plan, quyết định liên quan và câu hỏi còn mở; không tự đóng quyết định đang mở.
5. Phạm vi T-012 (không mở rộng): Tailwind + shadcn/ui với token trung tính (D-35); React Router; TanStack Query dùng cookie session, không lưu token ở `localStorage`/`sessionStorage`; manifest PWA + service worker chỉ cache tài nguyên tĩnh, không cache `/api`. Không gồm đăng nhập, app shell nghiệp vụ (T-111), i18n (T-607), màn hình nghiệp vụ. Test case dự kiến ở Implementation_Plan §12 (chưa có trong TEST_Plan, cần CDA duyệt khi bổ sung).
6. Môi trường local: Node 22 và Python 3.12 không phải mặc định của máy (mặc định Node 24, Python 3.10); xem README "Yêu cầu môi trường". Test PostgreSQL chỉ chạy trên GitHub Actions (máy không có Docker/PostgreSQL).

## 11. Nhật ký phiên 14/10/2026

Kiểm tra đầu phiên: HEAD = `origin/main` = `45b36f8` (PR #4 — checkpoint của mục 10 — merge sau khi mục 10 ghi `b7ba32d`; không có lệch khác), working tree sạch, run `38263752291` `success` trên `45b36f8`; branch protection `main` đọc lại: required check `ci`, `enforce_admins: true`, bắt buộc PR, cấm force-push/xóa.

| Hạng mục | Kết quả |
| --- | --- |
| Chọn task | T-012. Task có mọi dependency `DONE`: T-003, T-004, T-006, T-012. T-004, T-006 chưa có module sở hữu trong Architecture §3 → Q-48 (mới, Cao). T-003 cần chọn công cụ chưa chốt và không chạy được Docker local. Chi tiết: Implementation_Plan §12.1 |
| Lưu ý chiều dependency | T-111, T-207, T-212, T-409, T-504, T-509 phụ thuộc **vào** T-012, không phải dependency của T-012 (mục 10.4) |
| T-012 | `IN_REVIEW`: PR #5 (branch `feat/t012-frontend-foundation`); `scripts/ci.sh` local 18/18 (bước mới `build-check`); GitHub Actions run `38536047844` `success` trên `16c1e9e`. Giữ `IN_REVIEW` đến khi CDA duyệt đăng ký TC trong TEST_Plan; bằng chứng và giới hạn ở Implementation_Plan §10 |
| Decision_Log | 0.11: thêm Q-48 |

**Còn mở sau phiên:** Q-48 chặn bắt đầu T-004, T-006 (và phần mã dùng chung của T-005, T-007); 7 test của T-012 chưa đăng ký TC trong TEST_Plan (cần CDA duyệt); các mục ở 10.3 không đổi.

**Hướng tiếp tục:** khi CDA trả lời Q-48 → T-004, T-006; T-003 sau khi chốt công cụ proxy/scanner (hoặc CDA cho phép chọn khi triển khai) và có môi trường Docker để kiểm tra; T-005 cần T-003.

## 12. Nhật ký phiên 14/10/2026 (lần 2)

Kiểm tra đầu phiên: HEAD = `origin/main` = `da716ce` (PR #5 merge 14/10/2026), working tree sạch; run `38536405383` `success` trên `da716ce`; branch protection không đổi. Không có quyết định CDA mới về Q-48 hay TC của T-012: T-012 giữ `IN_REVIEW`.

| Hạng mục | Kết quả |
| --- | --- |
| Chọn task | Không task nào đủ điều kiện viết code. Task có mọi dependency `DONE`: T-003, T-004, T-006 (T-012 đã làm). T-004, T-006 chờ Q-48; T-003 chờ Q-49 (công cụ + phụ thuộc `api`/`worker` vào T-006, T-009). T-005 cần T-003; T-007 cần T-005; T-011 cần T-004; các task khác cần T-005 trở đi |
| Decision_Log 0.12 | Mục 3.5: hồ sơ phương án Q-48 (4 phương án, ưu/nhược, tác động T-004…T-007, điểm CDA cần quyết định). Mục 3.6 + Q-49 mới cho T-003 |
| T-012 | Đề xuất 7 test case (`PROPOSED`, nhãn `ĐX-12-1…7`, chưa đăng ký TEST_Plan): Implementation_Plan §12.2 |

**Cần CDA quyết định để mở khóa:** Q-48 (→ T-004, T-006, rồi T-007, T-011); Q-49 (→ T-003, rồi T-005 và gần như toàn bộ P0/P1); duyệt đề xuất TC ở Implementation_Plan §12.2 (→ T-012 `DONE`).

## 13. Nhật ký phiên 14/10/2026 (lần 3) — áp dụng chỉ đạo CDA cho Q-48, Q-49

Kiểm tra đầu phiên: HEAD = `origin/main` = `2073075`, working tree sạch, run `38538619882` `success`; branch protection không đổi.

| Hạng mục | Kết quả |
| --- | --- |
| Q-48 → D-42 (CONFIRMED) | Thêm module `platform` (hạ tầng dùng chung) và `app` (composition root, dạng package) vào Architecture §3 (1.3), quy tắc 8–10; ADR-001, ADR-002 Amendment 1; Q-44 trả lời cùng. Contract mới C5, C6 (import-linter), C7 (test AST); C1 cho phép `providers` → `platform`. Kiểm tra âm N20–N22 |
| Q-49 → D-43 | Tách T-003 (Compose — cấu hình) và T-013 mới (Compose — tích hợp); T-005 phụ thuộc T-002, T-004; T-605, T-608 thêm T-013. Công cụ `proxy` = Caddy, `scanner` = ClamAV là `PROPOSED` → T-003, T-013 `BLOCKED` tới khi CDA duyệt. Q-50 mới: cập nhật chữ ký scanner vs TC-NFR-01 |
| T-012 | Không có phê duyệt mới cho `ĐX-12-1…7` (Implementation_Plan §12.2) → giữ `IN_REVIEW`; bằng chứng kỹ thuật (run `38536047844`) giữ nguyên. Còn thiếu: CDA duyệt và đăng ký TC trong TEST_Plan |

| PR #7 | `194e40e` trên `main`, run `38540541945` (PR) và `38540690372` (`main`) `success` |
| T-004 | `DONE` — PR #8, run `38541183244` `success`; bằng chứng: Implementation_Plan §10, ghi chú §13 |

**Task đủ điều kiện tiếp theo:** T-006 (chỉ cần T-001); T-005 sau khi T-004 `DONE` (cần T-002, T-004); T-011 sau T-004.

## 14. Nhật ký phiên 14/10/2026 (lần 4)

Kiểm tra đầu phiên: HEAD = `origin/main` = `d9617a8`, working tree sạch, run `38541532132` `success`; branch protection không đổi; T-001, T-002, T-004 `DONE`, T-012 `IN_REVIEW`. D-43: tách DoD/dependency `CONFIRMED`, công cụ `PROPOSED`; Q-50 mở.

| Hạng mục | Kết quả |
| --- | --- |
| T-005 | Triển khai, merge PR #9 (`2cb5fc1`, run `38543440774` PR, `38543791513` `main`): engine/session, Alembic + revision M-01, script role, lệnh `migrate`; 9 test PostgreSQL chạy trong CI. `IN_REVIEW` — Q-51 (phạm vi TC nghiệm thu). Chi tiết: Implementation_Plan §10, §14 |
| T-011 | Triển khai, merge PR #10 (`875c2b7`, run `38544080219`) (module `storage`): `LocalStorage` khóa UUID, ghi nguyên tử, SHA-256, `delete_unreferenced` có tuổi tối thiểu bắt buộc, `is_ready`. `IN_REVIEW` — Q-51 (TC-FILE-03 phần chuẩn hóa tên thuộc T-203). Chi tiết: Implementation_Plan §10, §15 |
| T-006 | Triển khai, merge PR #11 (`aa405fc`, run `38544809935`) (`platform/logs.py`, `platform/web.py`, `app/asgi.py`): log JSON + che dữ liệu, correlation ID, `/api/v1/health/live`, `/api/v1/health/ready` (CSDL + migration + storage). `IN_REVIEW` — Q-51 (TC-GEN-05, TC-SEC-05). Chi tiết: Implementation_Plan §10, §16 |
| Q-51 (mới, Cao) | TC-DR-01/02, TC-MIG-02 gán cho T-005 phụ thuộc task sau T-005 → đề xuất nghiệm thu T-005 bằng DoD riêng + TC-MIG-01 |

**Tác động:** T-005, T-006, T-011 đều `IN_REVIEW` chờ Q-51. T-007, T-008, T-010, T-101 (và chuỗi sau) cần T-005 `DONE`; T-203, T-204 cần T-011/T-004 và chuỗi P2. Không còn task nào đủ điều kiện bắt đầu cho tới khi CDA trả lời Q-51 (hoặc D-43/Q-50 cho T-003).

**Cần CDA quyết định (cuối phiên lần 4):**
1. **Q-51** — phạm vi TC nghiệm thu của task nền (T-005, T-006, T-011): chấp nhận đề xuất thì ba task chuyển `DONE` dựa trên bằng chứng CI đã có; mở khóa T-007, T-008, T-010, T-101 và chuỗi P1.
2. **D-43** — duyệt công cụ (Caddy, ClamAV, không profile `observability`, hoãn `llm`) và **Q-50** (ranh giới TC-NFR-01, phương án A–D, Decision_Log mục 3.6.3) → mở khóa T-003, rồi T-013.
3. **T-012** — duyệt `ĐX-12-1…7` (Implementation_Plan §12.2) để đăng ký TC.
