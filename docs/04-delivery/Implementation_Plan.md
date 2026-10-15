# AI-EOS — Implementation Plan (Stage 2D)

> Phiên bản: 1.0 (cập nhật 14/10/2026: D-42, D-43) · Ngày: 12/10/2026 · Trạng thái: **Đã duyệt — D-46 (CDA, 15/10/2026)**; cập nhật 15/10/2026 theo D-44, D-47, D-49, D-51
> Hiện trạng thực thi từng task: mục 10 (bằng chứng) và [PROJECT_STATUS](../PROJECT_STATUS.md) (tổng hợp).
> Nguồn: [SRS](../02-requirements/SRS.md) 1.1, [Architecture](../03-architecture/Architecture.md) 1.2, [Database_Design](../03-architecture/Database_Design.md) 1.2, [API_Specification](../03-architecture/API_Specification.md) 1.2, ADR-001…013 (ADR-005/008/009 có Amendment 1), [Decision_Log](../00-source/Decision_Log.md) 0.7. Kiểm thử: [TEST_Plan](TEST_Plan.md).

## 1. Quy ước

| Trường | Ý nghĩa |
| --- | --- |
| ID | `T-xxx`, ổn định, không tái sử dụng |
| Sẵn sàng | `READY` (đủ căn cứ để làm) · `PARTIAL` (làm được phần có căn cứ; phần còn lại ghi rõ) · `BLOCKED` (chờ quyết định, không làm) |
| Thực thi | `TODO` (chưa làm) · `IN_REVIEW` (đã có code, kiểm tra cục bộ đã chạy, chờ CDA review; chưa đủ DoD vì DoD cần CI) · `DONE` (đủ DoD chung + DoD riêng, có bằng chứng CI). Ghi ở mục 10 |
| Điều kiện bắt đầu | Tách khỏi "Sẵn sàng": `READY` chỉ nói task **đủ căn cứ**, không nói dependency đã đáp ứng. Task chỉ được bắt đầu khi mọi task ở cột "Phụ thuộc" đã `DONE`. **Ngoại lệ duy nhất** (CDA, 12/10/2026): T-002 được bắt đầu khi T-001 đang `IN_REVIEW`, vì DoD chung 1 của T-001 cần CI do T-002 tạo. Ngoại lệ không áp dụng cho task khác và không đổi trạng thái T-001 |
| DoD chung | Áp dụng cho mọi task, xem mục 2 |

Không task nào được triển khai nghiệp vụ không có trong SRS. Giá trị `PROPOSED` (vd. 07:00 cho Briefing, thang độ tự tin 0–10) được cài dưới dạng **cấu hình**, có nhãn "đề xuất" trong mã và tài liệu, để đổi được mà không sửa code.

## 2. Definition of Done chung

1. Code theo ranh giới module ADR-001; lint, type check, test pass trong CI (ADR-013).
2. Test tương ứng trong TEST_Plan được viết và chạy xanh; test âm (từ chối quyền, lỗi validation) bắt buộc với mọi endpoint. **"Test tương ứng" (D-44, 15/10/2026)** = TC có task chủ là task đó (TEST_Plan §12). TC chỉ ghi `PASSED` khi task chủ chạy toàn bộ kịch bản xanh trong CI; task khác tham chiếu TC chỉ ghi "bằng chứng thành phần", không phải PASS; task sau chạy lại TC như hồi quy (quy tắc R1–R7, [Q-51_TC_Ownership_Draft](Q-51_TC_Ownership_Draft.md) mục 2).
3. Thao tác nhạy cảm có audit (thành công và thất bại); không log secret.
4. Migration (nếu có) chạy được từ rỗng → head trong CI; có ràng buộc CSDL theo Database_Design §8.
5. API khớp API_Specification; thay đổi contract phải cập nhật tài liệu trước.
6. Requirements_Traceability cập nhật cột Task/Test; trạng thái requirement chỉ chuyển `IMPLEMENTED` khi có code, `VERIFIED` khi test liên quan xanh trong CI.

## 3. Trình tự và phụ thuộc

```mermaid
flowchart LR
    P0["P0 Nền tảng: repo, CI, compose, DB, audit, jobs, frontend nền tảng"] --> P1["P1 Identity và Access"]
    P1 --> P2["P2 Org và Data Capture"]
    P1 --> P3["P3 AI control: gateway, kill switch"]
    P3 --> P2
    P1 --> P4["P4 Finance Lite"]
    P3 --> P4
    P2 --> P5["P5 Goals, Work, Briefing (phần có căn cứ)"]
    P3 --> P5
    P4 --> P5
    P5 --> P6["P6 Hardening, benchmark, DR"]
    P2 --> P6
```

Đường găng (suy ra từ cột "Phụ thuộc" ở mục 4; chưa có ước lượng thời lượng nên tính theo số task nối tiếp; `{…}` = cần tất cả; cập nhật 14/10/2026 theo D-43): P0: T-001 → {T-002, T-004} → T-005 → T-008 → T-009; T-003, T-006 chỉ cần T-001, T-007 và T-010 cần T-005, T-011 cần T-004, T-012 cần T-001 và T-002 — làm song song; T-013 (Compose tích hợp) cần T-003, T-004, T-005, T-006, T-009. Chuỗi dài nhất tới P5: T-001 → {T-002, T-004} → T-005 → T-101 → T-102 → T-104 → T-402 → T-403 → T-404 → T-406 → T-510 → T-511. **Cập nhật 15/10/2026 (D-44: T-510 thêm T-211, T-206 thêm T-112; D-49: T-513):** chuỗi dài nhất tới P5 là T-001 → T-004 → T-005 → T-101 → T-107 → T-108 → T-201 → T-202 → T-203 → T-206 → T-211 → T-510 → T-511 (13 task); tới P6: … → T-510 → T-513 → T-608 (14 task). Kiểm tra tự động: không có vòng phụ thuộc. Finance (P4) có thể làm song song P2 sau khi có T-108 và T-302.

## 4. Danh sách task

### P0 — Nền tảng

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-001 | Khung repo: `backend/` (package theo module ADR-001), `frontend/` (React + Vite + TS strict), `infra/` (Compose), `docs/` | — | ADR-001, ADR-002, ADR-003 | Architecture §3 | Cấu trúc thư mục khớp module; README chạy local | READY |
| T-002 | Toolchain + CI: lint, format, type check (Python, TS), pytest với PostgreSQL container, Vitest, quét phụ thuộc, kiểm tra quy tắc import giữa module | T-001 | ADR-013, ADR-001 | ADR-013 | CI chặn merge khi một bước lỗi; vi phạm ranh giới module làm CI đỏ | READY |
| T-003 | Docker Compose — **cấu hình** (D-43): khai báo `proxy` (TLS nội bộ), `api`, `worker`, `db`, `scanner`, service cập nhật chữ ký scanner (D-45, chỉ service này có đường ra internet tới nguồn chữ ký); mạng nội bộ, volume, biến môi trường/secret theo mục 7 (chỉ tên), healthcheck; chỉ `proxy` publish cổng. Không gồm profile `llm` (chờ D-08) và `observability` (D-43). Chạy đủ service thuộc T-013 | T-001 | SRS-NFR-04 | Architecture §9.1, ADR-004, D-43 | `docker compose config` hợp lệ — chạy ở môi trường có Docker (CI); không có Docker → ghi NOT RUN, không tuyên bố đạt. Kiểm tra tĩnh: chỉ `proxy` có `ports`, `db` không publish cổng, mạng backend `internal`, không có giá trị secret trong file | READY — công cụ đã duyệt (D-43, 15/10/2026): Caddy, ClamAV; cập nhật chữ ký bằng service riêng, `scanner` ở mạng `internal`, tuổi chữ ký ≤ 90 ngày (D-45) |
| T-004 | Cấu hình và secret: loader kiểm tra biến bắt buộc khi khởi động, không có giá trị mặc định cho secret, `.env.example` chỉ chứa tên biến (mục 7) | T-001 | ADR-006, ADR-011 | Architecture §9.1 | Thiếu secret → tiến trình dừng với lỗi rõ ràng, không in giá trị | READY |
| T-005 | Nền CSDL: SQLAlchemy 2, Alembic, 3 role CSDL (`aieos_owner`, `aieos_app`, `aieos_backup`), harness test migration; engine/session và tích hợp Alembic ở `platform` (D-42) | T-002, T-004 (D-43: bỏ T-003) | SRS-NFR-03 | Database_Design §2, §10 | Migration rỗng → head trong CI; role ứng dụng không có DDL | READY |
| T-006 | Logging JSON, correlation ID, bộ lọc che secret, `/health/live`, `/health/ready` | T-001 | SRS-GEN-05 | ADR-012, API-SYS-01, API-SYS-02 | Test: header `Authorization`, cookie, mật khẩu không xuất hiện trong log | READY |
| T-007 | Hạ tầng HTTP: lỗi `problem+json`, CSRF + kiểm tra `Origin`, idempotency store, `ETag`/`If-Match`, rate limit | T-005 | SRS-GEN-01, SRS-GEN-02, SRS-GEN-03, SRS-GEN-04, SRS-GEN-05 | API_Specification §1 | Test TC-GEN-01…05 | READY |
| T-008 | Module audit: bảng append-only, trigger chặn UPDATE/DELETE, API ghi trong transaction, che trường nhạy cảm | T-005 | SRS-AUD-01, SRS-AUD-02, SRS-AUD-03 | ADR-010, Database_Design §9 | UPDATE/DELETE audit bị CSDL từ chối; TC-AUD-03 (chủ: T-008); bằng chứng thành phần TC-AUD-01 (chủ T-109), TC-AUD-02 (chủ T-105) — D-55 | READY |
| T-009 | Module jobs: queue, claim `SKIP LOCKED`, lease, reaper, retry + backoff, scheduler (advisory lock), registry `job_class` + test cấm handler `ORCHESTRATION` gọi gateway/provider/bảng nghiệp vụ | T-005, T-008 | SRS-JOB-01, SRS-JOB-02, SRS-JOB-03, SRS-AIC-06 | ADR-005 (+Amendment 1), Database_Design §5 | TC-JOB-01…04, TC-JOB-06 (chủ: T-009); bằng chứng thành phần TC-JOB-05 (chủ T-203, D-56); tham số kỹ thuật theo D-56 | READY |
| T-010 | Thông báo in-app | T-005, T-102 (D-58) | SRS-NTF-01, SRS-NTF-02 | API-NOT-01, API-NOT-02 | Nội dung thông báo không chứa dữ liệu nhạy cảm; bằng chứng thành phần TC-NTF-01 (chủ T-510, D-58) | READY |
| T-011 | Storage adapter (volume cục bộ), khóa UUID | T-004 | SRS-CAP-03 | ADR-004 | Không đường dẫn nào lấy từ tên file người dùng | READY |
| T-012 | Nền tảng frontend (ADR-003): Tailwind CSS + shadcn/ui (Radix) với design token trung tính (D-35); React Router; TanStack Query (request kèm cookie session, không lưu token ở `localStorage`/`sessionStorage`); manifest PWA + service worker chỉ cache tài nguyên tĩnh, không cache response `/api`. Không gồm: đăng nhập, app shell nghiệp vụ (T-111), i18n (T-607), màn hình nghiệp vụ | T-001, T-002 | ADR-003 | ADR-003, UX §8.1–8.2, Architecture §2.2 | Qua toàn bộ `scripts/ci.sh` (T-002); test: service worker không cache `/api`; không dùng `dangerouslySetInnerHTML`; build không có inline script (tương thích CSP của ADR-003). Chưa có TC trong TEST_Plan — bổ sung khi triển khai, cần CDA duyệt | READY (đủ căn cứ: Q-45, D-41) — dependency T-001, T-002 đã `DONE`; thực thi: mục 10 |
| T-013 | Docker Compose — **tích hợp** (D-43): Dockerfile/image `api`, `worker` build được; `docker compose up` chạy đủ service của T-003 và vượt healthcheck; `db` dùng script role và lệnh migration của T-005 | T-003, T-004, T-005, T-006, T-009 | SRS-NFR-04 | Architecture §9.1, ADR-004, ADR-012, D-43 | Mọi service `healthy` ở môi trường có Docker (CI); TC-NFR-01; không publish cổng DB | READY — như T-003 (D-43, D-45); TC-NFR-01 theo phạm vi D-45 |

### P1 — Identity và Access

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-101 | Bảng `identity.*` + migration | T-005 | SRS-IAM-06 | Database_Design §4 | Token chỉ lưu hash | READY |
| T-102 | Đăng nhập, session (xoay ID, hết hạn), đăng xuất, `/auth/me`, giới hạn thử | T-101, T-007 | SRS-IAM-04, SRS-IAM-06, SRS-IAM-07, SRS-GEN-01 | API-AUTH-01, API-AUTH-06, API-AUTH-07 | TC-IAM-01…05; TC-AUD-02 (phần đăng nhập, D-55) | READY |
| T-103 | MFA TOTP: đăng ký, xác minh, mã khôi phục; bắt buộc với ADMIN | T-102 | SRS-IAM-05 | API-AUTH-02, API-AUTH-03, API-AUTH-04 | TC-IAM-06, TC-IAM-07; TC-AUD-02 (phần MFA, D-55) | READY |
| T-104 | Step-up (reauth), đổi mật khẩu + thu hồi session khác | T-102 | SRS-IAM-08, SRS-IAM-11 | API-AUTH-05, API-AUTH-09 | TC-IAM-08; TC-AUD-02 (phần đổi mật khẩu, D-55) | READY |
| T-105 | Tạo tài khoản + lời mời; chấp nhận lời mời | T-102, T-108, T-103, T-104 (D-55) | SRS-IAM-01, SRS-IAM-02, SRS-IAM-03 | API-ADM-02, API-ADM-03, API-AUTH-08 | TC-IAM-09, TC-IAM-10; thời hạn lời mời và chính sách mật khẩu là cấu hình (PROPOSED); TC-AUD-02 (phần lời mời + đạt tổng, D-55) | READY |
| T-106 | CLI `bootstrap-admin`, `recover-admin` | T-101, T-107, T-010 (D-58) | SRS-IAM-09, SRS-IAM-10 | ADR-006 | TC-IAM-11, TC-IAM-12 | READY |
| T-107 | Bảng `access.*`, seed role/permission (Architecture §6) qua migration, trigger INV-09/10/11, kiểm tra điều kiện assignment | T-101 | SRS-ACC-05, SRS-ACC-06, SRS-ACC-07, SRS-ACC-08 | Database_Design §4, §8 | Không seed tài khoản; seed `hr.*`, `pii.unmask`, `goals.activate` **không** có quyền nền | READY |
| T-108 | Module policy `authorize()`, bộ lọc phạm vi, mặc định deny, bắt buộc mọi route khai báo permission | T-107 | SRS-ACC-01, SRS-ACC-02, SRS-ACC-03, SRS-ACC-09, SRS-ACC-11 | ADR-007 | Route chưa khai báo quyền bị từ chối (TC-ACC-02) | PARTIAL — SRS-ACC-04 (định nghĩa "team") dùng mặc định PROPOSED |
| T-109 | API quản trị người dùng/role/assignment, thu hồi session, khóa ADMIN cuối | T-108, T-104 | SRS-ACC-05, SRS-ACC-06, SRS-ACC-07, SRS-ACC-08, SRS-IAM-11 | API-ADM-01, API-ADM-04, API-ADM-05, API-ADM-06, API-ADM-07, API-ADM-08, API-ADM-09 | TC-ACC-04…08, TC-AUD-01 (D-55) | READY |
| T-110 | Xem audit, trang tình trạng hệ thống (gồm cảnh báo thiếu người quản lý kỳ, không có kỳ mở, hàng chờ không người, chưa ai có `goals.activate`) | T-109, T-009, T-401 hoặc T-402 (D-44, `[CẦN XÁC NHẬN]` — chưa thêm vào chuỗi phụ thuộc) | SRS-AUD-04, SRS-FIN-12 | API-ADM-10, API-ADM-11 | TC-AUD-04, TC-FIN-14 (chủ: T-110, D-44) | READY |
| T-111 | Frontend: app shell, đăng nhập, MFA, chấp nhận lời mời, quản trị người dùng/quyền, ẩn mục không có quyền, trạng thái chung | T-102…T-109, T-012 | SRS-ACC-09, SRS-GEN-06 | UX_Flows §0, FL-01, FL-02, FL-03 | Bằng chứng thành phần TC-E2E-01 (chủ: T-608, D-44) | READY |
| T-112 | Che dữ liệu cá nhân: phát hiện bằng quy tắc (CCCD, số tài khoản…), nhãn `sensitivity`, che ở API, file xuất, câu trả lời AI | T-108 | SRS-ACC-10, SRS-PRV-02 | Architecture §6, §8.5 | TC-PRV-01…03 | READY — R6 đã quyết: không ai giữ quyền `hr.*`, `pii.unmask` trong MVP (D-21, 15/10/2026) |

### P2 — Org và Data Capture

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-201 | `org.*` + API danh bạ | T-108 | SRS-ACC-11 | API-ORG-01, API-ORG-02, Database_Design §6 | Chỉ trường danh bạ | READY |
| T-202 | Bảng `capture.*` + migration | T-005, T-201 | SRS-CAP-13, SRS-REV-07, SRS-REV-09 | Database_Design §6 | — | READY |
| T-203 | Upload: allowlist + magic bytes, giới hạn, chuẩn hóa tên, lưu, hash trùng, job quét mã độc | T-202, T-011, T-009 | SRS-CAP-01, SRS-CAP-02, SRS-CAP-03, SRS-CAP-04, SRS-CAP-05, SRS-CAP-06, SRS-CAP-07 | API-DOC-01, API-DOC-02, API-DOC-03, API-DOC-04, API-DOC-05 | TC-FILE-01…08, TC-JOB-05 (D-56) | READY |
| T-204 | Provider adapter: interface LLM/OCR/converter, adapter giả lập cho test, định tuyến theo phân loại dữ liệu, timeout/retry/fallback, call log, trần chi phí | T-004, T-009 | SRS-PRV-01, SRS-PRV-02, SRS-PRV-03, SRS-PRV-04, SRS-NFR-07 | ADR-011 | TC-PRV-04…07; trần chi phí là cấu hình (GAP-14) | READY |
| T-205 | Adapter provider thật (LLM, OCR) | T-204, T-606 | SRS-PRV-01 | ADR-011 | Theo kết quả benchmark | PARTIAL — D-50: DeepSeek qua OpenRouter cho demo; provider local cho production chờ T-606 (D-08). `[CẦN XÁC NHẬN]` phần demo có cần chờ T-606 không |
| T-206 | Pipeline xử lý: tiền xử lý ảnh, phân loại, trích xuất, chuẩn hóa VN, kiểm tra, định tuyến (tự ghi tắt mặc định), tách/gộp, thử lại | T-203, T-204, T-302, T-112 (D-44) | SRS-CAP-08, SRS-CAP-10, SRS-CAP-11, SRS-CAP-12, SRS-CAP-14, SRS-CAP-15, SRS-CAP-16, SRS-CAP-17, SRS-CAP-18, SRS-CAP-20, SRS-CAP-21, SRS-CAP-22 | Architecture §8.5, API-DOC-06, API-DOC-07 | TC-CAP-01…04, TC-CAP-06…08, TC-SEC-06 (chủ: T-206); TC-CAP-05 chủ T-208 (D-44) | READY — GAP-13, D-16, D-29 đã quyết theo mặc định (D-51) |
| T-207 | Hàng chờ review + API + UI bàn phím | T-206, T-108, T-012, T-408 (D-44) | SRS-REV-01, SRS-REV-02, SRS-REV-03, SRS-REV-04, SRS-REV-05, SRS-REV-06, SRS-REV-07, SRS-REV-08, SRS-REV-09, SRS-NFR-10 | API-REV-01…07, FL-05 | TC-REV-01…06 (gồm TC-REV-05, D-44) | READY — SLA review là cấu hình, giá trị trống (GAP-18, D-51) |
| T-208 | Cấu hình loại tài liệu/schema/ngưỡng, kiểm tra điều kiện bật tự ghi (BR-05) | T-206 | SRS-CAP-15, SRS-CAP-16, SRS-CAP-17 | API-CFG-01…05 | TC-CAP-05 (chủ: T-208); TC-CAP-06 chủ T-206 (D-44) | READY |
| T-209 | Form sinh từ schema, gợi ý/trùng, nhập ngôn ngữ tự nhiên (bản dự kiến), lưu nháp, audit thay đổi thủ công | T-206, T-204 | SRS-CAP-30, SRS-CAP-31, SRS-CAP-32, SRS-CAP-33, SRS-CAP-34 | API-CAP-01…04 | TC-CAP-09…11 | READY |
| T-210 | Import XLSX/CSV: map cột, xem trước, lỗi theo dòng, commit qua gateway; import nhân sự giới hạn cột | T-206, T-302 | SRS-IMP-01, SRS-IMP-02, SRS-IMP-03 | API-IMP-01…05, FL-06 | TC-IMP-01…04 | READY |
| T-211 | Lineage API + popover nguồn | T-206 | SRS-CAP-19, SRS-BRF-04 | API-ORG-03 | TC-CAP-12 | READY |
| T-212 | Frontend capture: drop zone toàn cục, thẻ tiến trình, chụp ảnh (app đang mở), import | T-203, T-210, T-012 | SRS-CAP-09 | FL-04, FL-06 | Bằng chứng thành phần TC-E2E-02 (chủ: T-608, D-44) | READY |

### P3 — AI control

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-301 | Bảng `ai.*`, seed Tool Registry (tool BRD §3.9 + tool đích MVP), trần autonomy | T-005, T-107 | SRS-AIC-02, SRS-AIC-03 | Database_Design §5, INV-12, INV-13 | CHECK trần có hiệu lực | READY |
| T-302 | Write gateway: thứ tự kiểm tra, bản nháp L2, thực thi L3, idempotency, audit; lint chặn ghi domain bỏ qua gateway | T-301, T-108, T-008 | SRS-AIC-01, SRS-AIC-02, SRS-AIC-05, SRS-AIC-09, SRS-CAP-18 | ADR-008, Architecture §8.1 | TC-AIC-01…06 | READY |
| T-303 | Kill switch: API, step-up, banner, tích hợp gateway và jobs (`job_class`) | T-302, T-009 | SRS-AIC-04, SRS-AIC-05, SRS-AIC-06 | API-AI-01, API-AI-02, FL-10 | TC-KS-01…07, TC-KS-10; TC-KS-08, TC-KS-09 chủ T-511 (D-44) | READY |
| T-304 | Bản nháp: review/xác nhận/từ chối, hoàn tác L3 (toast + 24 giờ), đánh dấu quá hạn (cấu hình, mặc định 30 ngày), nhắc hằng ngày | T-302, T-010 | SRS-AIC-07, SRS-AIC-08, SRS-AIC-10, SRS-AIC-11 | API-AI-06, API-AI-07, API-AI-08, API-AI-09, API-AI-10, API-AI-11, FL-09 | TC-AIC-07…11; TC-NTF-01 (phần bản nháp AI, D-58) | READY |
| T-305 | Cấu hình autonomy trong trần | T-301 | SRS-AIC-15 | API-AI-03, API-AI-04, API-AI-05 | TC-AIC-12 | READY |
| T-306 | Chat AI: SSE, tool READ theo phạm vi, trích dẫn, Dừng, trả lời theo ngôn ngữ câu hỏi | T-204, T-108 | SRS-AIC-12, SRS-AIC-13 | API-AI-12 | TC-AIC-13…15 (adapter giả lập) | PARTIAL — chất lượng trả lời chờ provider thật (D-08) |
| T-307 | Phản hồi người dùng; harness Evaluation Engine (bộ câu hỏi/đáp án, chạy trước thay đổi model/prompt) | T-306 | SRS-AIC-14, SRS-AIC-16 | API-AI-13, ADR-013 | Harness chạy được với adapter giả lập | READY |
| T-308 | Frontend panel chat AI (D-49): thanh/panel AI, trả lời truyền dần (SSE), bước thật, nút Dừng, source chip, độ tin cậy Cao/TB/Thấp; render nội dung AI dạng văn bản (ADR-003) | T-306, T-111, T-012 | SRS-AIC-12, SRS-AIC-13 | API-AI-12, UX_Flows §0.3 | Test component (Vitest): không dùng `dangerouslySetInnerHTML`, Dừng hủy luồng, source chip hiển thị. Chưa có TC trong TEST_Plan — bổ sung cần CDA duyệt | READY |

### P4 — Finance Lite

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-401 | Bảng `finance.*` + trigger INV-01…07, ràng buộc loại trừ chồng lấn kỳ, `ON_HOLD`/`hold_reason` | T-005, T-107 | SRS-FIN-13, SRS-FIN-17 | Database_Design §7, §8 | TC-FIN-01…04 ở mức CSDL | READY |
| T-402 | Kỳ báo cáo: mở/khóa, khóa dòng, chặn khóa khi còn chờ duyệt | T-401, T-104 | SRS-FIN-12 | API-FIN-01, API-FIN-02, API-FIN-03 | TC-FIN-12, TC-FIN-13, TC-FIN-15; TC-FIN-14 chủ T-110 (D-44) | PARTIAL — độ dài kỳ: tháng (Q-31, D-51); người giữ `finance.period.manage` do CDA giao vận hành (D-14, còn mở) |
| T-403 | Tạo/sửa/gửi/hủy/rút lại giao dịch; idempotency; kiểm tra kỳ `OPEN` khi gửi (AMD-01); cờ thiếu người duyệt | T-401, T-402, T-010 | SRS-FIN-01, SRS-FIN-02, SRS-FIN-04, SRS-FIN-05, SRS-FIN-06, SRS-FIN-07, SRS-FIN-16 | API-FIN-04…09 | TC-FIN-05…11; TC-NTF-01 (phần giao dịch chờ duyệt, D-58) | READY — danh mục là văn bản tự do (Q-42, D-51) |
| T-404 | Duyệt/từ chối: khóa dòng, version, tách nhiệm vụ, nhánh `ON_HOLD` | T-403 | SRS-FIN-08, SRS-FIN-09, SRS-FIN-17 | API-FIN-10, API-FIN-11 | TC-FIN-16…22 | READY |
| T-405 | Bút toán đảo và điều chỉnh | T-404 | SRS-FIN-10, SRS-FIN-11 | API-FIN-12 | TC-FIN-23…28 | READY |
| T-406 | Lịch sử, tổng hợp doanh thu/chi phí/tiền mặt với `as_of` | T-404 | SRS-FIN-14 | API-FIN-13, API-FIN-14 | TC-FIN-29 | READY |
| T-407 | Runway | T-406 | SRS-FIN-15 | API-FIN-14 | — | BLOCKED — Q-39 một phần (D-51): còn thiếu định nghĩa burn ròng và cửa sổ tính |
| T-408 | Tool AI `create_finance_draft` qua gateway (chỉ tạo `DRAFT`) | T-302, T-403 | SRS-FIN-03, SRS-REV-08 | ADR-008, ADR-009 | TC-FIN-30 | READY |
| T-409 | Frontend tài chính (FL-11, FL-12) | T-403…T-406, T-012 | SRS-FIN-12 | UX_Flows FL-11, FL-12 | Bằng chứng thành phần TC-E2E-03 (chủ: T-608, D-44) | READY |

### P5 — Goals, Work, Briefing (phần có căn cứ)

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-501 | `goals.*`: tạo/sửa bản nháp, đo lường, check-in, xem theo phạm vi; hiển thị baseline/target/giá trị, **không** tính % | T-108, T-201 | SRS-GOAL-01, SRS-GOAL-02, SRS-GOAL-05, SRS-GOAL-06, SRS-GOAL-07, SRS-GOAL-09, SRS-GOAL-11 | API-GOAL-01, API-GOAL-02, API-GOAL-03, API-GOAL-05, API-GOAL-06 | TC-GOAL-01…06 | READY — nhịp check-in, thang độ tự tin theo đề xuất (Q-30, D-51) |
| T-502 | Kích hoạt mục tiêu với permission `goals.activate` (assignment, không quyền nền) | T-501, T-109 | SRS-GOAL-03, SRS-GOAL-04 | API-GOAL-04 | TC-GOAL-07, TC-GOAL-08; TC-ACC-03 (phần mục tiêu, D-59) | PARTIAL — kích hoạt: CEO cấp công ty, MANAGER cấp đơn vị (Q-28, D-51); vòng đời ngoài DRAFT/ACTIVE và người được giao `goals.activate` còn mở |
| T-503 | Commit mục tiêu và giá trị đo từ tài liệu (kế hoạch, báo cáo định kỳ) qua gateway; gợi ý alignment L1 | T-206, T-302, T-501 | SRS-GOAL-03, SRS-GOAL-06, SRS-GOAL-10 | ADR-008 | TC-GOAL-09 | READY |
| T-504 | Frontend mục tiêu (cây, check-in) | T-501, T-502, T-012 | SRS-GOAL-08 | FL-15 | Bằng chứng thành phần TC-E2E-04 (chủ: T-608, D-44) | PARTIAL — điền sẵn check-in = giá trị đo gần nhất (PROPOSED); điền từ task: CDA đồng ý (Q-29, D-51) nhưng quy tắc chưa đặc tả |
| T-505 | `work.task`: tạo, sửa, hoàn thành/mở lại, xem theo phạm vi | T-108, T-201 | SRS-WRK-01, SRS-WRK-02, SRS-WRK-03, SRS-WRK-04, SRS-WRK-10 | API-WORK-01, API-WORK-03, API-WORK-04, API-WORK-05 | TC-WRK-01…05; TC-NTF-01 (phần giao task, D-58); TC-ACC-03 (chủ, D-59) | READY — trạng thái OPEN/DONE, mở lại bởi người giao (Q-33, D-51) |
| T-506 | Biên bản → Meeting/Decision/ActionItem → giao việc qua gateway | T-206, T-302, T-505 | SRS-WRK-05, SRS-WRK-06, SRS-WRK-07, SRS-WRK-11 | API-WORK-02, API-WORK-06, FL-08 | TC-WRK-06…08 | READY |
| T-507 | Job `ORCHESTRATION` task quá hạn + thông báo | T-009, T-505 | SRS-WRK-09 | ADR-005 | TC-WRK-09 | READY |
| T-508 | Action card F1 tạo task L3 + hoàn tác | T-304, T-505 | SRS-WRK-08 | ADR-008 | TC-WRK-10 | READY |
| T-509 | Frontend công việc | T-505, T-506, T-012 | SRS-WRK-10 | FL-08 | Bằng chứng thành phần TC-E2E-05 (chủ: T-608, D-44) | READY |
| T-510 | Trang chủ CEO: ô chỉ số (nhãn "đề xuất — chưa chính thức", không cảnh báo), "Cần anh quyết" (chỉ mục có nguồn), "AI đã làm", trạng thái trống, ẩn khối chưa đủ căn cứ, chọn ô | T-406, T-501, T-505, T-304, T-211 (D-44) | SRS-BRF-01, SRS-BRF-02, SRS-BRF-03, SRS-BRF-04, SRS-BRF-05, SRS-BRF-06, SRS-BRF-07, SRS-BRF-08, SRS-BRF-09, SRS-BRF-12, SRS-SLS-03 | API-INS-01, API-INS-02, FL-07 | TC-BRF-01…07; TC-NTF-01 (tổng, D-58) | PARTIAL — công thức ô chính thức (Q-37, D-51); ngưỡng "dữ liệu cũ" là cấu hình trống |
| T-511 | Tạo nội dung Briefing (`AI_CONTENT`) theo lịch + API quản lý lịch; hành vi kill switch | T-510, T-303, T-204 | SRS-BRF-10, SRS-BRF-11, SRS-BRF-13 | API-INS-03, ADR-005/008 Amendment 1 | TC-BRF-08…11, TC-KS-08, TC-KS-09 | READY — nội dung, giờ/tần suất theo mặc định (Q-36, D-51); provider demo D-50 |
| T-512 | Tài liệu quy trình/SOP → knowledge item | T-206, T-302 | FR-DCS-02 | API-KNOW-01 | TC-CAP-13 | READY |
| T-513 | Frontend Trang chủ CEO (D-49): dòng tóm tắt, 4 ô chỉ số có độ mới và nguồn, "Cần anh quyết", "AI đã làm", trạng thái trống, popover nguồn | T-510, T-111, T-012 | SRS-BRF-01, SRS-BRF-02, SRS-BRF-03, SRS-BRF-04, SRS-BRF-05, SRS-BRF-06, SRS-BRF-07, SRS-BRF-08, SRS-BRF-09, SRS-BRF-12 | FL-07, API-INS-01, API-INS-02 | Test component (Vitest) cho các khối và trạng thái trống; E2E thuộc TC-E2E-05 (chủ T-608). Chưa có TC riêng — bổ sung cần CDA duyệt | PARTIAL — ngưỡng "dữ liệu cũ" là cấu hình trống (Q-37) |

### P6 — Hardening, benchmark, phục hồi

| ID | Task | Phụ thuộc | SRS / requirement | Thiết kế | DoD riêng | Sẵn sàng |
| --- | --- | --- | --- | --- | --- | --- |
| T-601 | Sinh bộ test ma trận authorization từ seed | T-107; các task API liệt kê ở §17 (D-44) | SRS-ACC-01, SRS-ACC-02, SRS-NFR-11 | ADR-013 | Mọi endpoint × role × phạm vi | READY |
| T-602 | Bộ test bảo mật (TEST_Plan §6) | T-111, T-203, T-306, T-013 (D-44) | SRS-NFR-11 | Architecture §10 | AC-ARCH-05, 07, 08, 09, 11, 12 xanh; TC-SEC-01, TC-SEC-02, TC-SEC-04, TC-SEC-05 (chủ: T-602, D-44) | READY |
| T-603 | Test đồng thời và idempotency | T-404, T-405, T-009 | SRS-GEN-03, SRS-GEN-04 | Architecture §7.2 | AC-ARCH-01, 02, 03 xanh | READY |
| T-604 | Test hiệu năng NFR-01/02 | T-206, T-205 | SRS-NFR-01, SRS-NFR-02 | ADR-005 | Báo cáo số đo; không tuyên bố đạt nếu chưa đo | BLOCKED — cần provider thật (D-08) để đo đại diện; có thể đo pipeline với adapter giả lập |
| T-605 | Backup/restore: base backup + WAL archiving, backup volume, quy trình và diễn tập | T-005, T-013 (D-43), T-203, T-008, T-101, T-107, T-301, T-302, T-401, T-403 (D-44) | SRS-NFR-03 | Architecture §9.3 | Diễn tập ghi kết quả RPO/RTO đo được; TC-DR-01, TC-DR-02, TC-MIG-02 (chủ: T-605, D-44) | READY (công cụ cụ thể chọn khi triển khai) |
| T-606 | Benchmark LLM/OCR: tạo bộ dữ liệu tổng hợp, ground truth, harness, báo cáo | T-204 | SRS-NFR-09 | TEST_Plan §9, ADR-011 | Báo cáo so sánh ≥ 2 phương án; không dùng PII thật | READY |
| T-607 | Truy cập (WCAG 2.1 AA), i18n vi/en | T-111 | SRS-NFR-05, SRS-NFR-08 | ADR-003 | Kiểm tra tự động + thủ công | READY |
| T-608 | E2E Playwright cho FL-01…FL-15 trong phạm vi | T-013 (D-43); task frontend liệt kê ở §17 (D-44) | SRS-NFR-06 | UX_Flows | TC-E2E-01…06 (chủ: T-608, D-44) | READY |

### Bị chặn / ngoài phạm vi triển khai

| ID | Hạng mục | Phụ thuộc | Requirement | Lý do | Sẵn sàng |
| --- | --- | --- | --- | --- | --- |
| T-901 | Sales Pipeline Lite | — | SRS-SLS-01, SRS-SLS-02, FR-HM-04 | D-40, Q-38 — giữ ngoài MVP (D-51) | BLOCKED |
| T-902 | Workload/quá tải (F5) | — | SRS-WRK-12, F5, FR-HM-06 | Q-34 — không có workload trong MVP (D-51) | BLOCKED |
| T-903 | Đặt lịch / đồng bộ lịch | — | SRS-WRK-12 | Q-35, D-31 — không có lịch trong MVP (D-51) | BLOCKED |
| T-904 | % đạt mục tiêu, cảnh báo lệch | — | SRS-GOAL-09 | Q-29 một phần (D-51): công thức % đạt chờ CDA duyệt đề xuất; ngưỡng "dưới 20%" `[CẦN XÁC NHẬN]` | BLOCKED |
| T-905 | Theo dõi Decision Log 30/60/90 | — | SRS-WRK-11 | Q-41 — chỉ ghi quyết định (D-51) | BLOCKED |
| T-906 | Nhắc check-in tự động | — | SRS-GOAL-07 | Q-30 — không nhắc tự động (D-51) | BLOCKED |
| T-907 | Quyền xem dữ liệu nhân sự nhạy cảm | — | SRS-ACC-10 | R6 — không ai giữ trong MVP (D-21, 15/10/2026) | BLOCKED |
| T-908 | Hóa đơn/biên lai, email forwarding, C6–C10, L4 | — | SRS-NTF-03 | D-11, D-17, D-18; điều kiện mở: Phase 2 | BLOCKED |

## 5. Kế hoạch migration (không chạy trong Stage 2D)

| # | Migration | Nội dung | Bất biến kèm theo | Task |
| --- | --- | --- | --- | --- |
| M-01 | `base_roles_schemas` | Schema theo module, quyền role CSDL | Role ứng dụng không DDL | T-005 |
| M-02 | `identity` | Bảng identity | Hash token | T-101 |
| M-03 | `access_seed` | Role, permission, role_permission (seed), user_role, assignment | INV-09, INV-10, INV-11 | T-107 |
| M-04 | `audit` | `audit.event` | INV-14 | T-008 |
| M-05 | `jobs_notify` | `jobs.job` (`job_class`), `jobs.schedule`, `notify.notification` — D-56: tách thành revision `0003` (`jobs.*`, T-009) và revision của T-010 (`notify.notification`) | — | T-009, T-010 |
| M-06 | `org` | `org_unit`, `employee` (chỉ trường danh bạ) | — | T-201 |
| M-07 | `capture` | Bảng capture | — | T-202 |
| M-08 | `ai_seed` | `ai.*`, seed tool | INV-12, INV-13, INV-15 | T-301 |
| M-09 | `finance` | Kỳ, giao dịch (`ON_HOLD`), event, delegation (rỗng) | INV-01…INV-08 | T-401 |
| M-10 | `goals_work_knowledge_insights` | Bảng theo Database_Design §6 | — | T-501, T-505, T-510 |

Quy tắc: một chuỗi revision; mỗi migration có test rỗng → head và test bất biến tương ứng; không seed tài khoản; thay đổi phá vỡ theo mở rộng → di chuyển → thu hẹp (Database_Design §10).

## 6. Môi trường local và điều kiện triển khai

| Hạng mục | Yêu cầu |
| --- | --- |
| Công cụ | Docker + Docker Compose v2; Python và Node phiên bản ổn định được hỗ trợ (chốt trong lockfile ở T-001); trình duyệt hiện đại cho E2E |
| TLS local | Reverse proxy cấp chứng chỉ nội bộ; cookie `Secure` cần HTTPS |
| Phần cứng | Chưa xác định — scanner và model local là phần tốn RAM; xác định sau T-606 |
| Dữ liệu | Chỉ dữ liệu giả/tổng hợp trong dev, test, CI |
| Triển khai nội bộ | Chưa có trong phạm vi Stage 2D; điều kiện: T-605 diễn tập đạt, T-602/T-603 xanh, CDA duyệt |

## 7. Biến cấu hình và secret (chỉ tên, không có giá trị)

| Biến | Loại | Dùng bởi |
| --- | --- | --- |
| `AIEOS_DATABASE_URL` | Secret | api, worker, CLI quản trị `admin-cli` (role `aieos_app`) |
| `AIEOS_DATABASE_OWNER_URL` | Secret | lệnh migration |
| `AIEOS_CSRF_KEY` | Secret | api |
| `AIEOS_TOTP_ENCRYPTION_KEY` | Secret — 32 byte ngẫu nhiên mã hóa base64 (AES-256-GCM cho secret TOTP, T-103); sai định dạng → api thoát mã 2 | api |
| `AIEOS_STORAGE_PATH` | Cấu hình | api, worker |
| `AIEOS_ALLOWED_ORIGINS` | Cấu hình | api |
| `AIEOS_SCANNER_HOST` | Cấu hình | worker |
| `AIEOS_LLM_PROVIDERS`, `AIEOS_OCR_PROVIDERS` | Cấu hình (JSON: tên, URL, `local`, mức phân loại cho phép) | worker, api |
| `AIEOS_LLM_API_KEY_<NAME>` | Secret | worker, api |
| `AIEOS_AI_BUDGET_LIMIT` | Cấu hình (GAP-14) | worker, api |
| `AIEOS_SESSION_IDLE_MINUTES`, `AIEOS_SESSION_ABSOLUTE_HOURS`, `AIEOS_INVITE_TTL_HOURS`, `AIEOS_REAUTH_MINUTES` | Cấu hình | api |
| `AIEOS_BACKUP_TARGET` | Cấu hình | backup |
| `AIEOS_AUTH_RATE_LIMIT_ATTEMPTS`, `AIEOS_AUTH_RATE_LIMIT_WINDOW_SECONDS` | Cấu hình bắt buộc, không mặc định (D-57) — số lần thử tối đa trong cửa sổ, theo IP và theo tài khoản, cho đăng nhập, MFA, chấp nhận lời mời, reauth (API_Specification §1.9); đăng ký vào loader ở T-102 (đã đăng ký) | api |
| `AIEOS_AUTH_LOCKOUT_THRESHOLD`, `AIEOS_AUTH_LOCKOUT_MINUTES` | Cấu hình bắt buộc, không mặc định — số lần sai liên tiếp để khóa tạm và thời gian khóa (SRS-IAM-07 "giá trị cấu hình"; áp nguyên tắc D-57; đăng ký ở T-102) | api |
| `AIEOS_PASSWORD_MIN_LENGTH` | Cấu hình bắt buộc, không mặc định (D-58) — độ dài mật khẩu tối thiểu cho CLI T-106, đổi mật khẩu T-104, lời mời T-105; đăng ký vào loader ở T-106 (đã đăng ký) | api, CLI |

Secret nạp qua Docker secrets hoặc file môi trường không commit. Không có giá trị mặc định cho secret; thiếu → tiến trình dừng (T-004).

## 8. Rủi ro còn mở

| Rủi ro | Ảnh hưởng | Giảm thiểu |
| --- | --- | --- |
| Provider chưa chọn (D-08) | Chất lượng trích xuất, hiệu năng chưa biết | T-606 trước T-205; adapter giả lập để không chặn phát triển |
| Một người tài chính duy nhất | Giao dịch không ghi sổ được | Cảnh báo hệ thống; CDA giao assignment |
| Module P5 thiếu quy tắc | Phải sửa khi có câu trả lời | Giá trị PROPOSED là cấu hình; endpoint giữ ổn định |
| Thông lượng queue PostgreSQL chưa đo | NFR-02 | T-604 |
| Audit không có chuỗi hash | Người có quyền owner CSDL có thể can thiệp | Tách role CSDL; ghi nhận rủi ro (ADR-010) |
| PWA trên iOS | Thông báo/camera hạn chế | Không cam kết (ADR-003) |
| Provider demo cloud cho mọi loại dữ liệu (D-50) | Dữ liệu `PERSONAL`/`SENSITIVE` rời máy triển khai, ra provider ngoài Việt Nam | ADR-011 Amendment 1: chỉ khi demo; production thêm provider local; `[CẦN XÁC NHẬN]` demo dùng dữ liệu tổng hợp |

## 9. Tiêu chí nghiệm thu MVP (kỹ thuật)

1. Mọi task `READY` và phần có căn cứ của task `PARTIAL` hoàn thành theo DoD.
2. AC-ARCH-01…12 xanh trong CI.
3. TEST_Plan: mọi test mức độ P0 xanh; không có lỗi Critical/High mở.
4. Benchmark D-08 có báo cáo; mục tiêu MET-01 chỉ được tuyên bố khi đo đạt.
5. Diễn tập backup/restore có kết quả.
6. Traceability: mọi requirement P0 không DEFERRED có Task và Test, hoặc lý do N/A/BLOCKED.

## 10. Tiến độ thực thi

Điều kiện bắt đầu T-002: đáp ứng theo ngoại lệ ở mục 1 (CDA, 12/10/2026); T-002 đã bắt đầu theo ngoại lệ này, nay `DONE`. T-012 không thuộc ngoại lệ; dependency T-001, T-002 nay đã `DONE`.

Chỉ ghi task đã bắt đầu (ID trong dấu `` ` `` để không trùng với bảng task mục 4); bằng chứng là lệnh đã thực sự chạy. Trạng thái "Sẵn sàng" ở mục 4 không đổi.

| Task | Thực thi | Ngày | Bằng chứng | Chưa đạt / giới hạn |
| --- | --- | --- | --- | --- |
| `T-001` | `DONE` | 12/10/2026 | Cấu trúc `backend/` (package `aieos`, 17 module theo Architecture §3), `frontend/`, `infra/`, README. Python 3.12.14 (uv 0.12.11): `uv lock --check`, `uv sync --locked`, `uv build`, `python -m unittest` (test cấu trúc 2/2 OK; kiểm tra âm — package thừa, file `.py` lẻ, thư mục thiếu `__init__.py`, module bị xóa, module thiếu `__init__.py` — đều FAIL; chạy được từ thư mục khác). Node 22.23.3 / npm 10.9.9: `npm ci`, `npm run typecheck` (rc 0; kiểm tra âm: tham số `any` ngầm → TS7006), `npm run build`, `npm audit` 0 lỗ hổng, `npm run dev` (Vite 8.3.4 trả 200 cho `/` và `/src/main.tsx`); Node 24 bị chặn `EBADENGINE`. Review 12/10/2026: lặp lại các lệnh README trên bản sao sạch (không `.venv`/`node_modules`) → đạt; lockfile có binary cho linux gnu/musl, darwin, win32; không peer dependency `invalid` | **DONE 12/10/2026 — bằng chứng CI:** commit `318689c`, GitHub Actions run `38257197546` (`completed`/`success`): `scripts/ci.sh` 17/17 bước gồm ruff, mypy, import-contracts, pytest 14 passed (có test cấu trúc T-001), ESLint, tsc, Vitest, build. DoD chung: (1) đạt qua run trên; (2) T-001 không có TC trong TEST_Plan, không có endpoint; (3)–(5) không áp dụng (không thao tác nhạy cảm, migration, API); (6) không dòng requirement nào gắn T-001, không đổi trạng thái. DoD riêng: cấu trúc khớp module (test cấu trúc trong run trên); README chạy local (`scripts/ci.sh` local rc 0; `npm run dev` chạy lại 12/10/2026 với cấu hình T-002: 200 cho `/` và `/src/main.tsx`). Giới hạn còn lại (ngoài DoD): chưa kiểm tra giao diện bằng trình duyệt |
| `T-002` | `DONE` | 12/10/2026 | `scripts/ci.sh` local rc 0, 17/17 bước (Python 3.12.14, Node 22.23.3): runtime, docs, `uv lock --check`, `uv sync --locked`, ruff check/format, mypy `--strict`, import-linter C1–C3 (3 kept), pytest (13 passed, 1 skipped = test PostgreSQL NOT RUN), `npm ci`, ESLint, Prettier, tsc, Vitest (1 passed), build, pip-audit (0 lỗ hổng), `npm audit --audit-level=high` (0). `scripts/negative_checks.sh` rc 0: N1–N19 (N17, N19 tách a/b) — 21/21 ca thất bại đúng bước. Workflow `.github/workflows/ci.yml` qua actionlint 1.7.7; `ci.sh`, `negative_checks.sh` qua shellcheck 0.11.0. Thay đổi sản phẩm T-001: TypeScript 7.0.2 → 6.0.3, Node tối thiểu 22.22.2, test chạy bằng pytest | **DONE 12/10/2026.** Branch protection `main` (đọc lại qua `GET …/branches/main/protection`): required check `ci` (GitHub Actions, app_id 15368, `strict: false`), `enforce_admins: true`, bắt buộc PR (0 approval), cấm force-push và xóa branch; không có ruleset. PR đỏ #2 (head `26297bf`, run `38261777697` `failure` tại pytest: `1 failed, 14 passed`): `mergeStateStatus: BLOCKED`, `viewerCanMergeAsAdmin: false`; thử merge thông thường → HTTP 405 `Required status check "ci" is failing.`; `main` không đổi. PR xanh #1 (head `c599fcc`, run `38261808375` `success`): `CLEAN`/`MERGEABLE`, không merge. Hai PR đã đóng, nhánh thử đã xóa. Workflow xanh trên `main`: run `38257197546` (`318689c`, PostgreSQL 18 smoke đạt, pytest 14 passed, 0 skipped), `38260718270` (`2f30196`) |
| `T-004` | `DONE` | 14/10/2026 | Branch `feat/t004-config-secrets`. `backend/src/aieos/platform/config.py` (+ `platform/api.py`): registry biến Plan §7 (loại, tiến trình api/worker/migrate, bắt buộc), `load_settings`, `load_settings_or_exit` (stderr + mã 2), `Secret` (luôn che), `NAME_FILE` cho secret, `is_secret_name` (cho bộ lọc log T-006); `infra/.env.example` chỉ tên biến. Test `backend/tests/test_platform_config.py` (22): đủ biến theo từng tiến trình, thiếu/rỗng, báo mọi lỗi một lần, `_FILE` (đọc, xung đột, file không đọc được — không in đường dẫn), biến cấu hình không nhận `_FILE`, che secret, secret luôn bắt buộc, tiến trình con thoát mã 2 và không in giá trị nào, `.env.example` khớp registry và không có giá trị. Kiểm tra đột biến (sửa tạm rồi khôi phục): mặc định cho secret, `str(Secret)` lộ giá trị, giá trị trong thông điệp lỗi, giá trị trong `.env.example`, mã thoát 0, secret thành tùy chọn → đều đỏ. `scripts/ci.sh` local rc 0 (18/18) | **DONE 14/10/2026 — bằng chứng CI:** PR #8, commit `9e32d22`, GitHub Actions run `38541183244` (`completed`/`success`): `scripts/ci.sh` 18/18 bước, pytest 50 passed (gồm PostgreSQL), import-linter 5 kept. DoD chung: (1) đạt qua run trên; (2) T-004 không có TC trong TEST_Plan, có test âm; (3) không thao tác nhạy cảm cần audit, test xác nhận không in giá trị secret; (4), (5) không có migration, API; (6) không dòng ma trận nào gắn T-004. DoD riêng: thiếu secret → tiến trình dừng mã 2, chỉ nêu tên biến (test tiến trình con). Giả định `[CẦN XÁC NHẬN — T-204]` ở mục 13 |
| `T-005` | `DONE` | 14/10/2026 | Branch `feat/t005-db-foundation`, PR #9. `backend/src/aieos/platform/db.py` (+ `platform/api.py`): engine psycopg 3 từ `Secret` (chỉ PostgreSQL, lỗi không chứa URL), engine `aieos_app`/`aieos_owner`, `make_session_factory`, `transaction()` (commit/rollback), `Base` với naming convention, hàm Alembic (`upgrade`, `downgrade`, `current_revision`, `head_revision`, `compare_schema`, `run_migrations`). Alembic ở `platform/migrations` (một chuỗi revision, cấu hình bằng code, chỉ online, `env.py` không đọc URL); revision `0001` = M-01 `base_roles_schemas`: 13 schema Database_Design §2 thuộc `aieos_owner`, quyền mặc định `aieos_app` SELECT/INSERT/UPDATE (không DDL, DELETE, TRUNCATE), `aieos_backup` SELECT; `aieos_app` đọc được `alembic_version`. `platform/sql/provision_roles.sql`: tạo 3 role không đặc quyền (chạy lại an toàn, không mật khẩu). Lệnh `python -m aieos.app migrate` (role `aieos_owner`; lỗi chỉ in loại lỗi). Phụ thuộc: sqlalchemy 2.1.1, alembic 1.20.0, psycopg[binary] 3.3.6 chuyển sang runtime. Test `backend/tests/test_platform_db.py`: 11 test không CSDL (URL, che mật khẩu, lỗi không chứa giá trị, chuỗi revision tuyến tính + một head, docstring revision có ID, schema/role khớp Database_Design §2, SQL không có mật khẩu, lệnh migrate thiếu biến → mã 2) + 9 test PostgreSQL (role không đặc quyền + chủ CSDL, rỗng → head, model ↔ schema rỗng khác biệt, downgrade một bước rồi upgrade, `aieos_app` bị từ chối DDL ở mọi schema/public/temp, `aieos_app` không chạy được migration, quyền mặc định đúng tập cho phép, `transaction()` commit/rollback, lệnh migrate: role app thất bại, role owner thành công, không in mật khẩu). Local: `scripts/ci.sh` rc 0 (60 passed, 10 skipped = test PostgreSQL NOT RUN local); đột biến (`PASSWORD` trong SQL, bỏ `from None`) → test đỏ | Bằng chứng CI: mục 14. Giữ `IN_REVIEW` vì Q-51 (TC-DR-01/02, TC-MIG-02 trong danh sách nghiệm thu T-005 phụ thuộc task sau T-005) **DONE 15/10/2026 theo D-44:** TC-MIG-01 (chủ T-005, phạm vi revision `0001`) đạt — run `38543440774`. |
| `T-011` | `DONE` | 14/10/2026 | Branch `feat/t011-storage-adapter`. `backend/src/aieos/storage/local.py` (+ `storage/api.py`): `LocalStorage` — `put` (khóa UUID v4 do adapter sinh, SHA-256 + kích thước, ghi nguyên tử file tạm → fsync → `os.replace`, quyền 0o600, dọn file tạm khi lỗi), `get` (context manager), `exists`, `delete_unreferenced` (nơi gọi truyền hàm tham chiếu và tuổi tối thiểu bắt buộc, bỏ qua file lạ/tạm), `is_ready` (cho `/health/ready`); `storage_from_settings` đọc `AIEOS_STORAGE_PATH` qua `platform.api`. Đường dẫn chỉ tạo từ `key.hex`; không tham số nào nhận tên file. Test `backend/tests/test_storage.py` (20): roundtrip + hash, khóa ngẫu nhiên, 5 tên file độc hại (TC-FILE-03 phần storage) không chạm hệ thống file, chữ ký API không có tham số tên/đường dẫn, chỉ nhận `uuid.UUID`, đối tượng thiếu, quyền 0o600, ghi lỗi không để lại file, xóa theo tham chiếu + tuổi, tuổi phải dương, bỏ qua file lạ, thư mục gốc phải tồn tại, readiness, nạp từ cấu hình. Đột biến (bỏ điều kiện tuổi, không dọn file tạm, đường dẫn từ khóa thô, khóa cố định) → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #10, commit `297c047`, run `38544080219` (`success`, pytest 90 passed, 0 skipped) → merge `875c2b7`. Giữ `IN_REVIEW` vì Q-51 (TC-FILE-03 có phần chuẩn hóa tên thuộc T-203) **DONE 15/10/2026 theo D-44:** không làm chủ TC nào; bằng chứng thành phần TC-FILE-03 — run `38544080219`. |
| `T-006` | `DONE` | 14/10/2026 | Branch `feat/t006-logging-health`. `platform/logs.py`: log JSON ra stdout (`ts` UTC, `level`, `logger`, `message`, `correlation_id`, trường `extra`), che theo tên khóa nhạy cảm (authorization, cookie, password, token, secret, csrf, api key, OTP/MFA, session, tên biến secret T-004) và `Secret`; logger `httpx`/`httpcore` chỉ từ WARNING. `platform/web.py`: `create_api` (FastAPI, tắt `/docs`, `/redoc`, `/openapi.json` ở HTTP), middleware ASGI correlation ID (`X-Request-ID` hợp lệ 8–128 ký tự `[A-Za-z0-9._-]` được giữ, ngược lại sinh mới; trả lại trong response), log request chỉ gồm phương thức, đường dẫn không query, status, thời gian; `GET /api/v1/health/live`, `GET /api/v1/health/ready` (200/503, body chỉ trạng thái, tên kiểm tra lỗi chỉ vào log). `platform/db.py`: `database_ready` (kết nối + migration ở head). `app/asgi.py`: `create_app()` lắp cấu hình → logging → engine `aieos_app` → storage → readiness `database`, `storage`; thiếu cấu hình/thư mục storage → thoát mã 2. Phụ thuộc: fastapi 0.142.1, pydantic 2.13.5, starlette 1.7.0 (ghim qua `constraint-dependencies`), httpx 0.28.1 (dev). Fixture CSDL tạm chuyển sang `tests/conftest.py`. Test `backend/tests/test_platform_web.py` (31 + 1 PostgreSQL): log JSON + correlation ID; che trường nhạy cảm lồng nhau; request mang `Authorization`, cookie, CSRF, mật khẩu trong body, token trong query → không giá trị nào vào log (DoD); `httpx` không log URL; `X-Request-ID` hợp lệ/không hợp lệ/thiếu; live; ready đạt / không đạt / kiểm tra ném lỗi (không lộ chi tiết); lỗi 500 không có stack trace; docs tắt; OpenAPI sinh được; `create_app` khi CSDL không kết nối được, thiếu cấu hình, thiếu thư mục storage; [db] ready 503 trước migrate, 200 sau migrate. Đột biến (bỏ che theo khóa, log query string, lộ tên kiểm tra lỗi, bật log `httpx`, nhận mọi `X-Request-ID`, bật docs) → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #11, commit `3ee7e91`, run `38544809935` (`success`, pytest 122 passed, 0 skipped — gồm test readiness PostgreSQL) → merge `aa405fc`. Giữ `IN_REVIEW` vì Q-51 (TC-GEN-05 cần T-007; TC-SEC-05 cần T-102, T-203, T-204) **DONE 15/10/2026 theo D-44:** không làm chủ TC nào; bằng chứng thành phần TC-GEN-05, TC-SEC-05 — run `38544809935`. |
| `T-012` | `DONE` | 14/10/2026 | Branch `feat/t012-frontend-foundation`. Thêm: Tailwind CSS 4.3.3 (`@tailwindcss/vite`), token trung tính `src/index.css`; shadcn/ui (`components.json`, `cn`, `Button` trên `@radix-ui/react-slot` 1.3.3, `class-variance-authority`); React Router 8.4.0 (route `/` và `*`); TanStack Query 5.104.0 + `apiFetch` (`credentials: "include"`); manifest + icon giữ chỗ; service worker `src/sw.ts` → `dist/sw.js`; luật ESLint chặn `dangerouslySetInnerHTML`; `scripts/check-build.js` (bước `build-check` mới của `scripts/ci.sh`). `scripts/ci.sh` local rc 0, 18/18 bước (Python 3.12.14, Node 22.23.3): Vitest 5 file / 47 test passed; pytest 13 passed, 1 skipped (PostgreSQL NOT RUN local); `build-check` OK; pip-audit 0, `npm audit` 0. Kiểm tra âm (sửa tạm rồi khôi phục): script inline trong `dist/index.html` → `build-check` rc 1; tắt luật ESLint → `src/lint.test.ts` đỏ; `credentials: "same-origin"` → test client đỏ; ghi `localStorage` trong client → test client đỏ; cache mọi GET cùng origin → test cache policy đỏ; `dangerouslySetInnerHTML` trong `HomePage` → `npm run lint` rc 1. `vite preview`: `/`, `/sw.js`, `/manifest.webmanifest`, icon, route lạ → 200 | **Bằng chứng CI:** PR #5, commit `16c1e9e`, GitHub Actions run `38536047844` (`completed`/`success`): `scripts/ci.sh` 18/18 bước, pytest 14 passed (PostgreSQL 18.6), Vitest 47 passed, `build-check` OK. DoD riêng phần kỹ thuật (qua `scripts/ci.sh`, test không cache `/api`, không `dangerouslySetInnerHTML`, build không inline script) đạt trong run này. Giữ `IN_REVIEW` vì: 7 test dự kiến (đề xuất TC ở 12.2) ở mục 12 đã viết và chạy (ánh xạ ở 12.1) nhưng **chưa đăng ký TC trong TEST_Plan** — cần CDA duyệt (hàng T-012 mục 4). Chưa kiểm tra trên trình duyệt thật (cài PWA, đăng ký service worker) **DONE 15/10/2026 theo D-44, D-47:** TC-FE-01…07 (D-47) đạt — run `38536047844`. |
| `T-008` | `DONE` | 15/10/2026 | Branch `feat/T-008-audit-append-only`. Migration `0002` (M-04 `audit`): bảng `audit.event` theo Database_Design §9 (`id` bigint identity `ALWAYS`; CHECK `category`, `actor_type`, `outcome`, `autonomy_level` L0–L3, trường AI NULL khi không phải AI, `action` không rỗng; index `(resource_type, resource_id, occurred_at)`, `(actor_user_id, occurred_at)`); thu hồi UPDATE/DELETE/TRUNCATE của `aieos_app` (còn INSERT, SELECT); trigger `audit.reject_modification()` chặn UPDATE/DELETE (từng dòng) và TRUNCATE (câu lệnh) với mọi role (INV-14). Module `audit`: `models.py`, `recorder.py`, `api.py` — `AuditEvent`, `record(session, event)` (transaction hiện hành), `record_separately(factory, event)` (transaction riêng cho DENIED/FAILED/BLOCKED), `mask_changes` (che khóa nhạy cảm theo quy tắc log T-006 + `masked_fields` nơi gọi khai báo); `correlation_id` lấy từ T-006. `app/metadata.py` gom metadata model cho lệnh `migrate` và so khớp model ↔ schema. Test `backend/tests/test_audit.py` (7 không CSDL + 15 PostgreSQL): TC-AUD-03 (`test_app_role_cannot_modify_audit`), trigger chặn cả `aieos_owner`, quyền bảng đúng tập, không giả `id`/không tắt trigger, ghi cùng transaction (rollback → không có audit), DENIED/FAILED còn sau rollback, `changes` trong CSDL không chứa bí mật, CHECK, index, đủ cột + correlation ID. `test_platform_db.py`: so khớp model ↔ schema dùng metadata của `app`; downgrade từng bước tới base. Local (PostgreSQL 18.6 trong container tạm, Node 22.23.3): `scripts/ci.sh` rc 0, 18/18 bước, pytest 144 passed. Đột biến (bỏ trigger, bỏ REVOKE, không che `changes`, `record_separately` dùng chung transaction, bỏ `masked_fields`) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #16, commit `a3e19b8`, GitHub Actions run `38678659141` (`success`): `scripts/ci.sh` 18/18 bước, pytest 144 passed, 0 skipped (PostgreSQL 18.6), import-linter 5 kept. TC-AUD-03 `PASSED`. DoD chung: (1) đạt qua run trên; (2) TC task làm chủ: TC-AUD-03; không có endpoint; (3) không có thao tác nhạy cảm mới; không ghi secret (test che dữ liệu); (4) migration rỗng → head trong CI, ràng buộc INV-14; (5) không có API; (6) FR-DC-05 giữ trạng thái (cần T-209). DoD riêng: UPDATE/DELETE audit bị CSDL từ chối. Bằng chứng thành phần (không phải PASS, D-44 R3): TC-AUD-01 (chủ T-109) — ghi cùng transaction, transaction riêng cho DENIED/FAILED; TC-AUD-02 (chủ T-105) — che dữ liệu |
| `T-009` | `DONE` | 15/10/2026 | Branch `feat/T-009-job-queue`. Migration `0003` (phần `jobs` của M-05, D-56): `jobs.job` (`id` uuid; CHECK `job_class`, `status`, `max_attempts > 0`, `attempts ≤ max_attempts`, job `RUNNING` phải có lease + người giữ; `idempotency_key` UNIQUE — INV-08; index partial claim `(run_after, id) WHERE QUEUED`, reaper `(lease_expires_at) WHERE RUNNING`), `jobs.schedule` (`interval` cố định, không tháng/năm; `may_write = job_class <> 'ORCHESTRATION'`); `aieos_app` SELECT/INSERT/UPDATE, không DELETE. Module `jobs`: `registry.py` (`JobClass`, `JobRegistry`, hằng số `PROPOSED` D-56), `queue.py` (`enqueue` trong transaction nơi gọi, payload phẳng chỉ tham chiếu; `claim` `FOR UPDATE SKIP LOCKED`; `mark_succeeded` chỉ khi còn giữ job; `mark_failed` backoff/`DEAD`/`FAILED`; `reap`; `count_by_status`), `scheduler.py` (advisory lock, slot gần nhất, không chạy bù, điểm cắm `should_skip` cho lịch `may_write` + audit `schedule.skipped`), `worker.py` (`Worker.run_once`/`run_forever`, kiểm tra lại quyền người khởi tạo qua authorizer — mặc định từ chối, audit `SECURITY`/`DENIED`; `last_error` chỉ tên loại lỗi). `app/worker.py` + lệnh `python -m aieos.app worker [--once]` (SIGTERM dừng gọn); `app/metadata.py` thêm `jobs.api`. Test `backend/tests/test_jobs.py` (8 không CSDL + 25 PostgreSQL): TC-JOB-01 (20 lần claim đồng thời), TC-JOB-02, TC-JOB-03 (chết trước commit; worker cũ commit muộn), TC-JOB-04, TC-JOB-06 (quét tĩnh + ca vi phạm), backoff, lỗi vĩnh viễn, idempotency, `job_class` từ registry, gia hạn/mất lease, quyền (authorizer giả lập), CHECK, quyền bảng, scheduler (không chạy bù, advisory lock, bỏ qua `may_write`), lệnh worker. Local (PostgreSQL 18.6 container tạm, Node 22.23.3): `scripts/ci.sh` rc 0, pytest 177 passed. Đột biến (claim không khóa, `mark_succeeded` bỏ `locked_by`, reaper không `DEAD`, enqueue tự commit, bỏ kiểm tra quyền, chạy bù slot, bỏ `should_skip`, bỏ cấm gateway/provider trong quét, không retry lỗi tạm thời) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #17, commit `0e27ae6`, GitHub Actions run `38680383606` (`success`): `scripts/ci.sh` 18/18 bước, pytest 177 passed, 0 skipped (PostgreSQL 18.6). TC-JOB-01…04, TC-JOB-06 `PASSED`. DoD chung: (1) đạt; (2) TC task làm chủ đều `PASSED`, không có endpoint; (3) từ chối quyền và bỏ qua lịch có audit; `last_error` không chứa thông điệp; (4) migration rỗng → head trong CI, INV-08; (5) không có API; (6) FR-DF-05 giữ trạng thái (cần T-507). Bằng chứng thành phần (không phải PASS): TC-JOB-05 (chủ T-203, D-56) — authorizer giả lập; TC-KS-07 (chủ T-303) — `should_skip`; TC-KS-08/09 (chủ T-511) — phân loại `job_class` |
| `T-007` | `DONE` | 15/10/2026 | Branch `feat/T-007-http-infra`. `platform/errors.py`: `ApiError`, `ERROR_CATALOG` khớp API_Specification §10 (test đối chiếu tài liệu), `problem+json` có `correlation_id`. `platform/http.py`: `CsrfMiddleware` (mọi POST/PUT/PATCH/DELETE dưới `/api/v1`: `Origin` thuộc `AIEOS_ALLOWED_ORIGINS` + `X-CSRF-Token` = HMAC-SHA256(`AIEOS_CSRF_KEY`, token session); `exempt_paths` chỉ miễn token, vẫn kiểm `Origin`), `parse_allowed_origins`, `csrf_token`; idempotency `require_idempotency_key`, `request_fingerprint` (JSON chuẩn hóa), `run_idempotent` (phát lại / `409 IDEMPOTENCY_KEY_REUSED`, savepoint + UNIQUE khi đồng thời); `etag`, `require_if_match` (thiếu → 428, sai → 412), `check_version`; `RateLimiter` (cửa sổ trượt, `429` + `Retry-After`, giới hạn do nơi gọi truyền). `platform/web.py`: handler lỗi `ApiError`, 404/405, 422 (không lặp lại giá trị đầu vào); lỗi không lường trước → `500 INTERNAL_ERROR` problem+json có `X-Request-ID` (việc còn lại của T-006). `create_api` bắt buộc `csrf`; `app/asgi.py` dựng `CsrfConfig` từ cấu hình (origin sai → thoát mã 2). API_Specification 1.4: §10 thêm `METHOD_NOT_ALLOWED`, `INTERNAL_ERROR`. Test `backend/tests/test_platform_http.py` (route thử theo bảng task chủ D-44): TC-GEN-01…05 + CSRF mọi method, origin, đường dẫn miễn, validation, định tuyến, idempotency (header, dấu vân tay, thiếu khóa), rate limit; `test_platform_web.py` gửi CSRF hợp lệ. Local (PostgreSQL 18.6 container tạm, Node 22.23.3): `scripts/ci.sh` rc 0, pytest 213 passed. Đột biến (bỏ kiểm Origin, bỏ so token, bỏ so dấu vân tay, bỏ xử lý xung đột đồng thời, 500 không qua problem+json, thiếu If-Match vẫn qua) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #18, commit `4426bcd`, GitHub Actions run `38681777001` (`success`): `scripts/ci.sh` 18/18 bước, pytest 213 passed, 0 skipped (PostgreSQL 18.6). TC-GEN-01…05 `PASSED`. DoD chung: (1) đạt; (2) TC task làm chủ đều `PASSED`, test âm (CSRF, validation) có; (3) không có thao tác nhạy cảm cần audit; log không chứa token CSRF (test); (4) không có migration; (5) API_Specification cập nhật trước (§10, 1.4); (6) không dòng ma trận nào gắn T-007. Bằng chứng thành phần: TC-GEN-06 (chủ T-102), TC-SEC-05 (chủ T-602) |
| `T-101` | `DONE` | 15/10/2026 | Branch `feat/T-101-identity-tables`. Migration `0004` (M-02 `identity`): extension `citext`; `user_account` (email `citext` UNIQUE; `INVITED` ⇔ chưa có `password_hash`; `mfa_enabled` ⇒ có `mfa_secret_enc`; `version`; FK `created_by` tự tham chiếu), `session` (`token_hash` UNIQUE; index `(user_id) WHERE revoked_at IS NULL`; hạn tuyệt đối sau `created_at`), `invitation` (không đồng thời dùng và thu hồi; một lời mời hiệu lực mỗi user), `mfa_recovery_code`, `login_attempt` (`email_hash`, id identity). INV-16: mọi cột token/mã là `bytea` đúng 32 byte (SHA-256). Module `identity`: `models.py`, `tokens.py` (`new_token` 256 bit, `hash_token`, `token_matches`, `hash_email`), `api.py`; `app/metadata.py` thêm `identity.api`. Test `backend/tests/test_identity_schema.py` (2 không CSDL + 6 PostgreSQL): DoD "token chỉ lưu hash" (quét cột + CHECK độ dài từ chối token rõ), email không phân biệt hoa thường, ràng buộc tài khoản, session (trùng hash, FK, hạn), lời mời hiệu lực duy nhất, quyền `aieos_app` không DELETE. Local (PostgreSQL 18.6 container tạm, Node 22.23.3): `scripts/ci.sh` rc 0. Đột biến (bỏ CHECK 32 byte, bỏ unique lời mời hiệu lực, email `text`, bỏ ràng buộc INVITED) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #19, commit `d34b125`, GitHub Actions run `38683463269` (`success`): `scripts/ci.sh` 18/18 bước, pytest 221 passed, 0 skipped (PostgreSQL 18.6). DoD chung: (1) đạt; (2) không làm chủ TC; (3) không có thao tác nhạy cảm; (4) migration rỗng → head trong CI, INV-16 ở CSDL; (5) không có API; (6) không dòng ma trận nào gắn T-101. DoD riêng: token chỉ lưu hash. Không làm chủ TC nào (TC-IAM-02, TC-IAM-05 chủ T-102 — bằng chứng thành phần: bảng session, token chỉ lưu hash, cột hạn) |
| `T-107` | `DONE` | 15/10/2026 | Branch `feat/T-107-access-tables`. Migration `0005` (M-03 `access_seed`): `role`, `permission`, `role_permission` seed theo Architecture §6 (`B` → `BASE`, `A` → `ELIGIBLE`; 5 role, 29 permission; `hr.*`, `pii.unmask` không role nào; `goals.activate` chỉ `ELIGIBLE`); `user_role` (INV-09 CHECK `granted_by <> user_id`, lý do bắt buộc khi có người cấp), `assignment` (INV-09, phạm vi/scope_id, hạn, thu hồi bằng `revoked_at`); trigger INV-10 (ADMIN + CFO, SQLSTATE `AE001`), INV-11 (gỡ role ADMIN hoặc chuyển tài khoản ADMIN khỏi `ACTIVE` khi là ADMIN hoạt động cuối, `AE002`, advisory lock `admin-membership` trong trigger), điều kiện assignment (`AE003`). Quyền: danh mục chỉ SELECT; `user_role` thêm DELETE (gỡ role); `assignment` không DELETE. Module `access`: `models.py`, `service.py` (`grant_role`, `revoke_role`, `create_assignment`, `revoke_assignment` — ánh xạ lỗi CSDL → `ROLE_COMBINATION_FORBIDDEN`, `SELF_ROLE_CHANGE`, `LAST_ADMIN`, `ASSIGNMENT_NOT_ELIGIBLE`; audit `ADMIN` cùng transaction), `api.py`. Test `backend/tests/test_access.py` (2 không CSDL + 8 PostgreSQL): seed khớp Architecture §6 (đọc bảng tài liệu), DoD (không seed tài khoản; quyền nhạy cảm không có quyền nền), quyền bảng, INV-10 cả hai thứ tự + UPDATE, INV-09, INV-11 (gỡ, khóa, vô hiệu; 10 vòng gỡ đồng thời), điều kiện assignment, service + audit. Local (PostgreSQL 18.6 container tạm, Node 22.23.3): `scripts/ci.sh` rc 0. Đột biến (bỏ advisory lock, bỏ chặn ADMIN+CFO, bỏ kiểm assignment, bỏ chặn khóa ADMIN cuối, seed lệch §6) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #20, commit `bc8a592`, GitHub Actions run `38684667496` (`success`): `scripts/ci.sh` 18/18 bước, pytest 231 passed, 0 skipped (PostgreSQL 18.6). DoD chung: (1) đạt; (2) không làm chủ TC; (3) đổi role/assignment có audit `ADMIN`; (4) migration rỗng → head trong CI, INV-09/10/11 ở CSDL; (5) không có API; (6) UX-09 giữ trạng thái (cần T-109). DoD riêng: không seed tài khoản; `hr.*`, `pii.unmask`, `goals.activate` không có quyền nền. Không làm chủ TC nào — bằng chứng thành phần (phần CSDL) cho TC-ACC-04…07 (chủ T-109) |
| `T-102` | `DONE` | 15/10/2026 | Branch `feat/T-102-login-session`. `identity/auth.py` (`Authenticator`): đăng nhập Argon2id (`argon2-cffi` 25.1.0, tham số mặc định thư viện, băm lại khi tham số đổi; email không tồn tại vẫn kiểm trên hash giả), giới hạn thử theo IP + tài khoản (D-57, `RateLimiter` T-007), khóa tạm theo `AIEOS_AUTH_LOCKOUT_*` (`423` chỉ khi mật khẩu đúng), session mới mỗi lần đăng nhập + thu hồi session cũ gửi kèm (chống fixation), hết hạn nhàn rỗi trượt + tuyệt đối, session chờ MFA cho ADMIN/tài khoản bật MFA (`401 MFA_REQUIRED`), `login_attempt`, audit `SECURITY` (không email/mật khẩu/token). `identity/router.py`: API-AUTH-01 `POST /auth/login` (công khai, miễn token CSRF), API-AUTH-06 `POST /auth/logout` (204), API-AUTH-07 `GET /auth/me` (role, permission hiệu lực, token CSRF). `access.api.effective_permissions` (quyền nền + assignment còn hiệu lực, chưa xét phạm vi — T-108). `app/asgi.py`: `PUBLIC_PATHS`, `CSRF_EXEMPT_PATHS`, đọc 6 tham số auth (số nguyên dương, sai → thoát mã 2). Cấu hình: đăng ký `AIEOS_AUTH_RATE_LIMIT_*`, `AIEOS_AUTH_LOCKOUT_*`. T-007: middleware CSRF bỏ qua kiểm token khi request không có cookie session (vẫn kiểm Origin) để endpoint trả 401 (TC-GEN-06). Ràng buộc `pycparser==3.0` (bản 3.11 mới 6 ngày). Test `backend/tests/test_auth.py` (11): TC-IAM-01…05, TC-GEN-06 (mọi endpoint từ OpenAPI của `create_app`), phần đăng nhập TC-AUD-02, tài khoản không hoạt động/khóa bởi admin, chờ MFA, đăng xuất. Local (PostgreSQL 18.6 container tạm, Node 22.23.3): `scripts/ci.sh` rc 0, pytest 242 passed. Đột biến (không thu hồi session cũ, email lạ không chạy Argon2, không khóa tạm, không kiểm hạn session, `/auth/me` không cần session, session chờ MFA dùng mọi API, cookie không HttpOnly) → test đỏ | **DONE 15/10/2026 — bằng chứng CI:** PR #21, commit `28f74cf`, GitHub Actions run `38686690047` (`success`): `scripts/ci.sh` 18/18 bước, pytest 242 passed, 0 skipped (PostgreSQL 18.6). TC-IAM-01…05, TC-GEN-06 `PASSED`. DoD chung: (1) đạt; (2) TC task làm chủ đều `PASSED`, test từ chối quyền (401, MFA_REQUIRED, CSRF) có; (3) đăng nhập thành công/bị từ chối/bị chặn có audit, không ghi secret; (4) không có migration; (5) API-AUTH-01/06/07 khớp API_Specification, chuyển `IMPLEMENTED` (D-52); (6) không dòng ma trận nào gắn T-102. Bằng chứng thành phần: phần đăng nhập TC-AUD-02 (chủ T-105) |
| `T-010` | `DONE` | 15/10/2026 | Branch `feat/T-010-notifications`, PR #22. Migration `0006` (phần `notify` của M-05, D-56): `notify.notification` (CHECK `type`, `title` không rỗng, `link` chỉ đường dẫn nội bộ, `read_at ≥ created_at`; index `(user_id, read_at)`, `(user_id, created_at, id)`; `aieos_app` không DELETE). `notify/service.py`: `notify()` (trong transaction nơi gọi; chặn link ngoài), `list_for_user`, `mark_read` (chỉ chủ; lặp lại giữ `read_at`). `notify/router.py`: API-NOT-01 `GET /api/v1/notifications` (cursor §1.8), API-NOT-02 `POST /api/v1/notifications/{id}/read` (người khác → 404); session đủ MFA; `notify` không import `identity` (giao thức `Recipient`) để T-106 gọi được `notify()`. `platform/http.py`: `encode_cursor`, `decode_cursor`, `PAGE_DEFAULT_LIMIT`, `PAGE_MAX_LIMIT`. Test `backend/tests/test_notify.py` (6). Đột biến (bỏ lọc chủ ở list / mark_read, bỏ kiểm link, ghi đè `read_at`) → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #22, run `38696839691` (`success`, pytest 248 passed, 0 skipped). Bằng chứng thành phần TC-NTF-01 (chủ T-510, D-58) — không ghi PASS. |
| `T-106` | `DONE` | 15/10/2026 | Branch `feat/T-106-admin-cli`, PR #23 (xếp chồng trên #22). `identity/admin.py`: `bootstrap_admin` (advisory lock `admin-membership`; từ chối khi đã có ADMIN `ACTIVE` hoặc email đã có; tài khoản `ACTIVE` + `must_enroll_mfa`, role ADMIN `granted_by = NULL`, audit `BOOTSTRAP`), `recover_admin` (đích ADMIN `ACTIVE`; mật khẩu mới, xóa MFA + mã khôi phục, gỡ khóa tạm, thu hồi session, audit kèm lý do, thông báo ADMIN khác qua T-010). `app/admin_cli.py`: lệnh `bootstrap-admin`, `recover-admin` (`--confirm` bắt buộc; mật khẩu qua file hoặc nhập tương tác). Loader: tiến trình `admin-cli`, `AIEOS_PASSWORD_MIN_LENGTH` (D-58). `access.api.active_admins`. Test `backend/tests/test_admin_cli.py` (10). 8 đột biến → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #23, run `38697852135` (`success`, pytest 259 passed, 0 skipped). TC-IAM-11, TC-IAM-12 `PASSED`. |
| `T-103` | `DONE` | 15/10/2026 | Branch `feat/T-103-mfa-totp`, PR #24. `identity/mfa.py`: TOTP RFC 6238 (SHA1, 6 số, 30 giây, lệch ±1 bước; chống dùng lại qua `mfa_last_step`), secret 20 byte mã hóa AES-256-GCM (`AIEOS_TOTP_ENCRYPTION_KEY`, dữ liệu liên kết = id tài khoản), 10 mã khôi phục một lần (SHA-256), `MfaService` (`enroll` chỉ ADMIN, `confirm`, `verify`; rate limit D-57; audit SECURITY không ghi mã). `identity/router.py`: API-AUTH-02/03/04; response đăng nhập thêm `mfa_enrolled`, `csrf_token`. `Authenticator.rotate_session`. Migration `0007`. `cryptography` 50.0.2. Test `backend/tests/test_mfa.py` (12, gồm vector RFC 6238). 9 đột biến → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #24, run `38700993783` (`success`, pytest 271 passed, 0 skipped). TC-IAM-06, TC-IAM-07 `PASSED`. |
| `T-108` | `DONE` (phần có căn cứ) | 15/10/2026 | Branch `feat/T-108-access-policy`, PR #25. `access/policy.py`: `load_actor`, `authorize` (mặc định deny; phạm vi theo role Architecture §6 và assignment `COMPANY`/`ORG_UNIT`/`DOCUMENT_TYPE`/`REVIEW_QUEUE`), `require` (ngoài phạm vi → 404), `scope_filter` (SQL), `PermissionGuard` (khai báo + kiểm tra route, audit `access.denied`), `OrgScope`/`NO_ORG`. `platform/web.py`: `declare`, dependency toàn cục từ chối route không khai báo. Mọi route hiện có khai báo (`PUBLIC` khớp §1.2). Test `backend/tests/test_policy.py` (9). 10 đột biến → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #25, run `38703355287` (`success`, pytest 280 passed, 0 skipped). TC-ACC-01, TC-ACC-02 `PASSED`; TC-ACC-03 bằng chứng thành phần (Q-52 → D-59: chủ T-505). Chưa làm: "team" (SRS-ACC-04), mục tiêu cha. |
| `T-104` | `DONE` | 15/10/2026 | Branch `feat/T-104-reauth-password`, PR #26. `identity/stepup.py`: `StepUpService.reauth` (mật khẩu + mã MFA khi đã bật; `reauth_at` của session; rate limit D-57; audit), `change_password` (`AIEOS_PASSWORD_MIN_LENGTH`, thu hồi session khác, audit không chứa mật khẩu). `Authenticator.require_step_up` (`401 REAUTH_REQUIRED` ngoài `AIEOS_REAUTH_MINUTES`), `revoke_sessions`. `MfaService.use_code`. API-AUTH-05, API-AUTH-09. Test `backend/tests/test_stepup.py` (6). 9 đột biến → test đỏ. `scripts/ci.sh` local rc 0 | Bằng chứng CI: PR #26, run `38705903816` (`success`, pytest 286 passed, 0 skipped). TC-IAM-08 `PASSED`; phần đổi mật khẩu TC-AUD-02 (chủ T-105) bằng chứng thành phần. |

## 11. Kế hoạch chi tiết T-002 (chưa triển khai)

Căn cứ: hàng T-002 ở mục 4 (không đổi), ADR-013, Decision_Log D-41 (gồm bổ sung 0.9), Q-43…Q-47. **Hướng toolchain đã chốt** (D-41 bổ sung 0.9): TypeScript 6.0.3 + ESLint 10 + typescript-eslint, GitHub Actions (Q-46), PostgreSQL 18 (Q-47). Phiên bản cụ thể dưới đây vẫn là `PROPOSED`: mới kiểm tra metadata registry và resolve lockfile thử trên bản sao (12/10/2026) — **không đủ làm bằng chứng**; chỉ xác nhận sau khi T-002 cài và chạy thành công. **Cập nhật T-002 (12/10/2026):** toàn bộ phiên bản ở 11.1 đã được cài và `scripts/ci.sh` chạy thành công **cục bộ** (mục 10); chưa có lần chạy trên GitHub Actions.

### 11.1. Phiên bản đề xuất và bằng chứng tương thích

| Thành phần | Phiên bản | Bằng chứng |
| --- | --- | --- |
| TypeScript | 6.0.3 (thay 7.0.2 của T-001; hướng đã chốt, phiên bản chờ chạy thực tế) | typescript-eslint 8.71.1 khai báo peer `typescript >=4.8.4 <6.1.0`; TS 7.0.2 nằm ngoài khoảng. Vite 8.3.4, plugin-react 6.1.2, Vitest 5.0.4 không khai báo peer `typescript` |
| ESLint, `@eslint/js` | 10.12.0, 10.0.1 | engines Node `^20.19.0 \|\| ^22.13.0 \|\| >=24`; `@eslint/js` peer `eslint ^10.0.0` |
| typescript-eslint | 8.71.1 | peer `eslint ^8.57.0 \|\| ^9.0.0 \|\| ^10.0.0` |
| eslint-plugin-react-hooks | 7.1.1 | peer gồm `eslint ^10.0.0` |
| eslint-config-prettier, Prettier | 10.1.8, 3.9.10 | peer `eslint >=7.0.0`; Prettier không có peer |
| globals | 17.13.0 | engines `>=18` |
| Vitest | 5.0.4 | peer `vite ^6.4.0 \|\| ^7.0.0 \|\| ^8.0.0`; engines `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0` |
| @testing-library/react, @testing-library/dom | 16.3.3, 10.4.2 | peer `react`/`react-dom` `^18 \|\| ^19`, `@testing-library/dom ^10.0.0` |
| jsdom | 30.1.2 | engines `^22.22.2 \|\| ^24.15.0 \|\| >=26.0.0` — quyết định mức Node tối thiểu (11.2) |
| Resolve thử frontend | — | `npm install --package-lock-only` với toàn bộ bộ trên: rc 0, không xung đột peer, TypeScript trong lock 6.0.3 |
| ruff | 0.17.0 | Lint + format Python; `requires_python >=3.7` |
| mypy | 2.4.0 | Type check `--strict`; `>=3.10` |
| pytest | 9.1.1 | Thay `unittest` của T-001 (chạy được test kiểu `unittest`); `>=3.10` |
| import-linter | 2.15 | Kiểm tra import-contract (ADR-001); `>=3.10` |
| psycopg[binary] | 3.3.6 | Driver test kết nối PostgreSQL; có wheel cp312 manylinux x86_64 |
| pip-audit | 2.10.1 | Quét lỗ hổng Python, nhóm phụ thuộc riêng `audit`. `uv audit` (uv 0.12.11) còn là tính năng thử nghiệm nên không dùng |
| Resolve thử backend | — | `uv add` toàn bộ bộ trên cho Python 3.12: resolve 46 package |

### 11.2. Mức Node tối thiểu

Dependency được chọn yêu cầu Node 22 tối thiểu: jsdom 30.1.2 và phụ thuộc của nó (`^22.22.2`), undici (`>=22.19.0`), ESLint 10 (`^22.13.0`). T-002 nâng mức tối thiểu lên **22.22.2** và đồng bộ: `frontend/package.json` `engines` `>=22.22.2 <23`, `frontend/.nvmrc` `22.23.3` (bản 22 LTS mới nhất đã dùng để kiểm tra), `frontend/.npmrc` giữ `engine-strict=true`, README, CLAUDE.md §5, workflow CI (đọc `.nvmrc`). Python giữ 3.12.x.

### 11.3. `scripts/ci.sh` — nguồn lệnh thống nhất

Chạy tuần tự, dừng ở bước lỗi đầu tiên, in tên bước và mã thoát:

1. Runtime: Python 3.12.x, Node ≥ 22.22.2 và < 23; sai → thất bại.
2. Tài liệu: `python3 scripts/check_docs.py`.
3. Backend: `uv lock --check`, `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports`, `pytest`.
4. Frontend: `npm ci`, `eslint`, `prettier --check`, `tsc --noEmit`, `vitest run`, `vite build`.
5. Quét phụ thuộc: `pip-audit` trên danh sách khóa từ `uv.lock`; `npm audit --audit-level=high`.

**Test PostgreSQL:** marker `db`; biến `AIEOS_TEST_DATABASE_URL`. Khi `AIEOS_REQUIRE_DB=1` (workflow CI đặt biến này) mà thiếu URL → **thất bại**, không skip. Chạy local không đặt `AIEOS_REQUIRE_DB` → các test `db` không chạy và `ci.sh` in rõ "PostgreSQL: NOT RUN — chưa xác minh". T-002 chỉ có smoke test kết nối (`SELECT 1`); schema và migration thuộc T-005.

**Ba lớp, ghi bằng chứng riêng:** (a) `scripts/ci.sh` chạy local — chứng minh được trong T-002; (b) workflow GitHub Actions `.github/workflows/ci.yml` (Q-46): runner Ubuntu, Python theo `backend/.python-version` qua uv, Node theo `frontend/.nvmrc`, service `postgres:18` (Q-47), đặt `AIEOS_REQUIRE_DB=1` và `AIEOS_TEST_DATABASE_URL`, gọi `scripts/ci.sh`; action bên thứ ba ghim theo commit SHA — chỉ xác minh khi có remote GitHub và lần chạy thật; (c) branch protection cho `main` yêu cầu job CI xanh trước merge — cấu hình trên GitHub, chỉ xác minh khi có bằng chứng cấu hình và một PR bị chặn khi CI đỏ. Chưa có (b), (c) thì không tuyên bố "CI chặn merge".

**PostgreSQL 18 (Q-47) — điều kiện xác minh:** smoke test `db` chạy thật trên GitHub Actions với `postgres:18` và psycopg 3.3.6; ghi phiên bản server thực tế (`SHOW server_version`) vào bằng chứng; T-003 (Compose) và T-005 dùng cùng major. Chưa có lần chạy thật thì cấu hình CSDL/CI chưa được coi là hoàn tất.

### 11.4. Import-contract (theo Architecture §3 hiện hành)

| Contract | Quy tắc | Công cụ | Giả định |
| --- | --- | --- | --- |
| C1 | `providers` không import module `aieos` nào khác, trừ `platform` (quy tắc 6, 8) | import-linter `forbidden` | `[CẦN XÁC NHẬN]` diễn giải chặt: cấm cả module hạ tầng (`audit`, `storage`). `platform` được phép theo D-42 |
| C2 | `ai`, `jobs`, `capture` không import `goals`, `work`, `org`, `knowledge`, `finance` (quy tắc 2) | import-linter `forbidden` | Đã chốt (Q-43, D-41 bổ sung 0.9): cấm mọi import, kể cả `<module>.api` và module con; không áp dụng cho `insights`, `gateway` |
| C3 | `goals`, `work`, `org`, `knowledge`, `finance`, `sales` không import `gateway` (quy tắc 3) | import-linter `forbidden` | Danh sách "domain" lấy từ quy tắc 2 cộng `sales` |
| C4 | Module chỉ import `<module>.api` của module khác, không import `models`/`repository`/module con khác (quy tắc 1) | Test pytest phân tích AST toàn bộ `src/aieos` | Không bắt được import động (`importlib`); ghi là giới hạn |
| C5 | `platform` không import module `aieos` nào khác (quy tắc 8, D-42) | import-linter `forbidden` | — |
| C6 | Không module nào import `app` (quy tắc 9, D-42) | import-linter `forbidden` | — |
| C7 | Chỉ `platform` tạo engine SQLAlchemy (`create_engine`, `create_async_engine`), cấu hình logging toàn cục (`logging.basicConfig`, `logging.config.*`), đọc biến môi trường (`os.environ`, `os.getenv`, `os.environb`) (quy tắc 10, D-42) | Test pytest AST `tests/test_platform_ownership.py` | So khớp theo tên; không bắt được gọi gián tiếp (`getattr`, `importlib`) |

Quy tắc 4 (audit qua `audit.api.record`) và 5 (`access.policy.authorize`) không kiểm tra được bằng import-contract; kiểm chứng bằng test ở T-008, T-108.

### 11.5. Kiểm tra âm (mỗi lỗi tiêm vào bản sao tạm, `scripts/ci.sh` phải trả mã khác 0 ở đúng bước)

| # | Lỗi tiêm | Bước phải thất bại |
| --- | --- | --- |
| N1 | Import không dùng trong Python | `ruff check` |
| N2 | Sai định dạng Python | `ruff format --check` |
| N3 | Sai kiểu Python | `mypy --strict` |
| N4 | `aieos.ai` import `aieos.finance` (cả `.api`) | `lint-imports` (C2) |
| N5 | `aieos.providers` import `aieos.access` | `lint-imports` (C1) |
| N6 | `aieos.finance` import `aieos.gateway` | `lint-imports` (C3) |
| N7 | `aieos.goals` import `aieos.finance.models` | test AST (C4) |
| N8 | Test Python sai | `pytest` |
| N9 | `AIEOS_REQUIRE_DB=1` không có `AIEOS_TEST_DATABASE_URL` | `pytest` (thất bại, không skip) |
| N10 | Gọi hook có điều kiện | `eslint` (react-hooks) |
| N11 | Promise không được xử lý | `eslint` (typescript-eslint, luật dựa trên kiểu) |
| N12 | Sai định dạng TS | `prettier --check` |
| N13 | Sai kiểu TS | `tsc --noEmit` |
| N14 | Test frontend sai | `vitest run` |
| N15 | `pyproject.toml` lệch `uv.lock` | `uv lock --check` |
| N16 | `package.json` lệch `package-lock.json` | `npm ci` |
| N17 | Chạy bằng Node 24 hoặc Python 3.10 | Bước runtime |
| N18 | Link hỏng trong tài liệu | `check_docs.py` |
| N19 | Ghim phụ thuộc có lỗ hổng đã công bố (Python và npm) | `pip-audit`, `npm audit` |
| N20 | `aieos.platform` import `aieos.access.api` (D-42) | `lint-imports` (C5) |
| N21 | `aieos.goals` import `aieos.app` (D-42) | `lint-imports` (C6) |
| N22 | `aieos.goals` gọi `create_engine` / đọc `os.environ` (D-42) | test AST (C7) |

### 11.6. Bằng chứng, trạng thái, traceability

- Bằng chứng ghi ở mục 10: lệnh, mã thoát, phiên bản runtime, kết quả N1–N19; lớp (b), (c) của 11.3 ghi riêng.
- T-002 → `IN_REVIEW` khi `scripts/ci.sh` local xanh và N1–N19 đạt; → `DONE` chỉ khi workflow GitHub Actions chạy thật xanh (kể cả test PostgreSQL 18) và branch protection `main` được xác nhận (Q-46, Q-47). **Đã chuyển `DONE` ngày 12/10/2026** (mục 10); N1–N19 đã chạy (mục 10); không TC nào trong TEST_Plan `PASSED`.
- T-001 giữ `IN_REVIEW`; chuyển `DONE` khi bước T-001 nằm trong workflow CI chạy thật xanh (DoD chung 1). **Đã chuyển `DONE` ngày 12/10/2026** — run `38257197546` (mục 10).
- T-002 không có dòng trong ma trận traceability và không có TC trong TEST_Plan → chỉ ghi chú ở Requirements_Traceability; không TC nào chuyển trạng thái.
- T-002 sửa sản phẩm của T-001: TypeScript 7.0.2 → 6.0.3, mức Node (11.2), test cấu trúc chạy bằng pytest, README và CLAUDE.md §5 cập nhật lệnh.
- Ngoài phạm vi T-002: Docker Compose (T-003), cấu hình/secret (T-004), schema và migration (T-005), FastAPI (T-006).

## 12. Ghi chú T-012 (nền tảng frontend)

- ID: dải P0 là T-001…T-011, ID tiếp theo trong dải là T-012; T-012 chưa được dùng hay dành trước ở tài liệu nào (kiểm tra 12/10/2026).
- Dependency: T-001 (khung `frontend/`), T-002 (lint, type check, Vitest, `scripts/ci.sh` phải có trước khi thêm thư viện UI). Task phụ thuộc trực tiếp T-012: T-111, T-207, T-212, T-409, T-504, T-509 (bắc cầu: T-607, T-608); chuỗi dài nhất ở mục 3 không đổi (kiểm tra lại sau khi thêm dependency).
- Dependency của task frontend — cập nhật 12/10/2026 theo yêu cầu CDA rà từng task (thay ghi chú trước đó "giữ nguyên dependency, đề xuất thêm T-012 chờ CDA duyệt"). ID trong bảng đặt trong dấu `` ` `` để không trùng với bảng task mục 4:

| Task | Kết luận | Căn cứ trực tiếp từ phạm vi task |
| --- | --- | --- |
| `T-111` | Thêm T-012 | App shell: điều hướng (React Router), gọi API (TanStack Query), component (shadcn/ui) |
| `T-212` | Thêm T-012 | Màn hình capture (drop zone, thẻ tiến trình, chụp ảnh khi app mở) dựng trên component và lớp dữ liệu của T-012 |
| `T-409` | Thêm T-012 | Màn hình tài chính FL-11, FL-12 |
| `T-504` | Thêm T-012 | Màn hình mục tiêu (cây, check-in) |
| `T-509` | Thêm T-012 | Màn hình công việc |
| `T-607` | Không đổi | Đã phụ thuộc T-111 (nay phụ thuộc T-012) nên có T-012 qua bắc cầu; WCAG/i18n không cần trực tiếp thêm thành phần nào của T-012 ngoài app shell |
| `T-608` | Không đổi | Cột "Phụ thuộc" ghi "Các task frontend", đã bao gồm T-012 |

- Không đổi: phạm vi, trạng thái "Sẵn sàng" và các dependency khác của các task trên. Sau khi thêm: không ID trùng, không dependency thiếu, không chu trình; chuỗi dài nhất không đổi (12 task).
- Rà tiếp T-207, T-306, T-510 (12/10/2026, theo yêu cầu CDA; chỉ thêm T-012 khi deliverable của task có phần frontend):

| Task | Kết luận | Căn cứ |
| --- | --- | --- |
| `T-207` | Thêm T-012 | Phạm vi ghi "Hàng chờ review + API + **UI bàn phím**"; SRS-REV-02 (màn review song song, tô vùng nguồn), SRS-REV-03 (màu và hình), SRS-REV-05 (thao tác bàn phím) là yêu cầu giao diện; TC-REV-06, TC-REV-07 là E2E |
| `T-306` | Không đổi | Thiết kế chỉ có API-AI-12 (SSE); TC-AIC-13…15 đều là test API; "Dừng" và trích dẫn được kiểm ở mức API |
| `T-510` | Không đổi | Thiết kế API-INS-01, API-INS-02; TC-BRF-01…07 là test API/integration (vd. nhãn "chưa chính thức" kiểm bằng trường `official=false`) |

- **Đã quyết (D-49, 15/10/2026): tạo T-308 (panel chat AI) và T-513 (Trang chủ CEO).** Ghi chú gốc: chưa có task frontend nào được giao tường minh cho: thanh/panel chat AI (phần giao diện của SRS-AIC-12: source chip, độ tin cậy, nút Dừng) và màn Trang chủ CEO (FL-07; TC-E2E-05 có FL-07 nhưng gắn với T-509 "Frontend công việc"). Không tạo task hay đổi dependency khi chưa được CDA quyết định.
- Test case dự kiến khi triển khai T-012 (chưa tạo ID, chưa thêm vào TEST_Plan; bổ sung cần CDA duyệt):
  1. Vitest: router hiển thị route gốc và route không tồn tại.
  2. Vitest: client TanStack Query gửi request kèm cookie (`credentials: "include"`) và không đọc/ghi `localStorage`/`sessionStorage`.
  3. Service worker: request `/api/*` không được cache; chỉ tài nguyên tĩnh của bản build được cache.
  4. Manifest PWA hợp lệ (tên, `start_url`, `display`, icon) trong bản build.
  5. `dist/index.html` không có inline script (tương thích CSP ADR-003; liên quan TC-SEC-01).
  6. Lint chặn `dangerouslySetInnerHTML` (luật lõi ESLint `no-restricted-syntax`, không cần thêm plugin; liên quan TC-SEC-01).
  7. Component nền tảng (shadcn/ui) render được với design token trung tính (D-35).


### 12.1. Ghi chú triển khai T-012 (14/10/2026)

- Chọn task: task có mọi dependency `DONE` là T-003, T-004, T-006, T-012. T-004 và T-006 (cùng mã dùng chung của T-005, T-007) chưa có module sở hữu trong Architecture §3 — ghi Q-48, không tự chọn vị trí. T-003 cần chọn reverse proxy, scanner, runtime LLM, stack observability (Architecture §9.1 chỉ ghi "mã nguồn mở") và image `api` chưa có ứng dụng; máy local không có Docker. T-012 đủ căn cứ (Q-45, D-41), không phụ thuộc quyết định đang mở.
- Ánh xạ test dự kiến (mục 12) → file: (1) `src/routes.test.tsx`; (2) `src/api/client.test.ts`; (3) `src/sw/cachePolicy.test.ts` (logic) + `scripts/check-build.js` (`dist/sw.js` độc lập); (4), (5) `scripts/check-build.js`; (6) `src/lint.test.ts` (ESLint API) + luật trong `eslint.config.js`; (7) `src/components/ui/button.test.tsx` (gồm kiểm tra token UX §8.2).
- Service worker viết tay (không dùng plugin PWA): chỉ cache GET cùng origin, không query, đường dẫn `/assets/*` (tên đã băm) hoặc manifest/icon; `/api`, `/api/*` và điều hướng HTML không đi qua cache (không cam kết ngoại tuyến, D-27). Chỉ đăng ký khi build production. Logic ở `src/sw/cachePolicy.ts`; `src/sw.ts` kiểm tra kiểu bằng `tsconfig.sw.json` (lib WebWorker).
- Token: `primary` dùng thang xám vì thương hiệu chưa quyết định (D-35); `ai`, màu trạng thái và icon là giá trị giữ chỗ, ghi chú "đề xuất" trong `src/index.css`. Chưa làm: chế độ tối, hai mật độ, kiểm tra tương phản (T-607), font tải về (chỉ khai báo danh sách font).
- Ngoài phạm vi T-012, chuyển cho task sau: header CSRF cho request ghi (T-007, T-111); xử lý lỗi `problem+json` (T-007); reverse proxy phải trả `sw.js` với `Cache-Control: no-cache` và đặt CSP (T-003).
- Phiên bản phụ thuộc mới ghim chính xác, chọn bản ổn định phát hành trước 30/09/2026 (≥ 2 tuần): tailwindcss, @tailwindcss/vite 4.3.3; react-router 8.4.0; @tanstack/react-query 5.104.0; @radix-ui/react-slot 1.3.3; class-variance-authority 0.7.1; clsx 2.1.1; tailwind-merge 3.7.0.

### 12.2. Đề xuất test case cho T-012 (`PROPOSED` — chờ CDA duyệt, chưa đăng ký trong TEST_Plan)

Mã `ĐX-12-n` chỉ là nhãn đề xuất, **không phải** ID test case. Khi CDA duyệt, ID chính thức được gán theo quy ước TEST_Plan (nhóm và số do CDA chốt) và thêm vào TEST_Plan với trạng thái `NOT RUN`; chỉ khi đó T-012 mới được xét `DONE`. Hiện thực tương ứng đã có trong code và chạy xanh trong GitHub Actions run `38536047844` (mục 10), nhưng đó là bằng chứng kỹ thuật, không thay cho việc duyệt.

| Mã đề xuất | Mục tiêu | Điều kiện tiên quyết | Bước kiểm thử | Kết quả mong đợi | Liên kết DoD T-012 / nguồn | Loại · mức đề xuất | Hiện thực |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ĐX-12-1 | Router hiển thị route gốc và route không tồn tại | `npm ci` | Render `App` với memory router tại `/` và tại một đường dẫn không khai báo | `/`: tiêu đề "AI-EOS"; đường dẫn lạ: "Không tìm thấy hoặc bạn không có quyền" + liên kết "Về Trang chủ" tới `/` | Phạm vi React Router; UX_Flows §0.2, SRS-ACC-02 | U · P1 | `frontend/src/routes.test.tsx` |
| ĐX-12-2 | Client API dùng cookie session, không dùng Web Storage | `fetch` được thay bằng hàm giả | Gọi `apiFetch` (GET, POST, kể cả khi nơi gọi truyền `credentials: "omit"`); theo dõi mọi phương thức của `Storage` | `credentials: "include"` mọi request; không phương thức `Storage` nào được gọi; `localStorage`/`sessionStorage` rỗng; lỗi HTTP → `ApiError` | Phạm vi TanStack Query; ADR-003, ADR-006 | U · P0 | `frontend/src/api/client.test.ts` |
| ĐX-12-3 | Service worker không cache `/api` và HTML | — | Kiểm hàm chính sách cache với `/api`, `/api/*`, `/`, `/index.html`, route SPA, request có query, khác GET, khác origin; kiểm cache-first chỉ lưu response thành công | Chỉ `/assets/*` (GET, cùng origin, không query) và manifest/icon được cache; mọi trường hợp còn lại không qua cache | DoD: "service worker không cache `/api`"; ADR-003 | U · P0 | `frontend/src/sw/cachePolicy.test.ts` |
| ĐX-12-4 | Manifest PWA hợp lệ trong bản build | `vite build` thành công | Chạy `npm run check:build` | `dist/manifest.webmanifest` có `name`, `short_name`, `start_url`, `display`, icon 192 và 512 tồn tại trong `dist`; `index.html` liên kết manifest | Phạm vi manifest PWA; ADR-003 | U · P1 | `frontend/scripts/check-build.js` |
| ĐX-12-5 | Bản build không có script inline | `vite build` thành công | Chạy `npm run check:build` | `dist/index.html` không có `<script>` thiếu `src` hoặc có nội dung, không có thuộc tính sự kiện `on…=`; `dist/sw.js` không import module khác | DoD: "build không có inline script"; ADR-003 (CSP); liên quan TC-SEC-01 | S · P0 | `frontend/scripts/check-build.js` |
| ĐX-12-6 | Lint chặn `dangerouslySetInnerHTML` | `npm ci` | Lint một đoạn TSX có `dangerouslySetInnerHTML` và một đoạn render văn bản | Đoạn thứ nhất: lỗi `no-restricted-syntax` mức error; đoạn thứ hai: không lỗi | DoD: "không dùng `dangerouslySetInnerHTML`"; ADR-003; liên quan TC-SEC-01 | S · P0 | `frontend/src/lint.test.ts` + `frontend/eslint.config.js` |
| ĐX-12-7 | Component nền tảng render với token trung tính | `npm ci` | Render `Button` (mặc định và `asChild`); đọc `src/index.css` | Class dùng token (`bg-primary`…); đủ token UX §8.2 (`primary`, `ai`, `success`, `warning`, `danger`, `info`, `stale`, `neutral-0…900`); `primary` thuộc thang xám (D-35) | Phạm vi Tailwind + shadcn/ui; UX §8.1–8.2, D-35 | U · P2 | `frontend/src/components/ui/button.test.tsx` |

CDA cần quyết định: (1) duyệt hay sửa 7 đề xuất; (2) nhóm ID và mục đặt trong TEST_Plan; (3) mức P0/P1/P2.

Cách đăng ký đề xuất sau khi được duyệt (chưa thực hiện; 14/10/2026):
- Thêm một mục mới trong TEST_Plan (vd. "Nền tảng frontend (T-012)"), cùng định dạng bảng hiện có: ID · Yêu cầu · Loại · Mức · Tình huống · Kết quả mong đợi; cột "Yêu cầu" ghi ADR-003 (T-012 không có SRS riêng).
- Nhóm ID đề xuất: `FE`, số 01…07 theo thứ tự `ĐX-12-1…7`; ID chưa được dùng (TEST_Plan hiện có 24 nhóm, không có `FE`). Đăng ký mới với trạng thái `NOT RUN` (TEST_Plan và `check_docs.py` không cho trạng thái đã chạy).
- Cùng PR: bảng trên giữ cột "Mã đề xuất" và thêm cột ID chính thức để truy vết; Handoff §5 cột "Test case" của T-012 ghi các ID mới; chuyển T-012 sang `DONE` dựa trên run `38536047844` (không cần chạy lại vì mã test không đổi).
- Trước khi duyệt: không đổi nhãn `ĐX-12-n` thành ID chính thức ở bất kỳ tài liệu nào.

### 11.7. Ghi chú triển khai T-002 (12/10/2026)

- Contract import-linter đặt tên không dấu (`C1 providers khong import module aieos khac`, …) để output một dòng, kiểm tra âm grep được; diễn giải tiếng Việt ở chú thích trong `backend/pyproject.toml`.
- ruff `line-length = 120` (docstring tiếng Việt); Prettier `printWidth: 120`.
- `pip-audit` thất bại với **mọi** lỗ hổng đã công bố (công cụ không lọc theo mức) — chặt hơn yêu cầu "mức cao" của ADR-013; `npm audit` dùng `--audit-level=high`.
- Kiểm tra âm N17 tách N17a (Node khác major 22, cần `AIEOS_N17_NODE_DIR`; không đặt → NOT RUN) và N17b (Python khác 3.12 qua `UV_PYTHON`); N19 tách N19a (Python, jinja2 2.10) và N19b (npm, lodash 4.17.20).
- Lỗi phát hiện khi chạy N17b và đã sửa: bước runtime dùng `uv python find` không áp `UV_PYTHON`, nên báo OK trong khi các lệnh uv sau dùng Python 3.10; nay truyền `UV_PYTHON` cho `uv python find`.
- Workflow dùng `POSTGRES_HOST_AUTH_METHOD=trust` cho CSDL tạm của job (không có mật khẩu nên không có secret); action ghim theo commit SHA (checkout v7.0.1, setup-uv v10.3.0, setup-node v7.1.0).

## 13. Ghi chú triển khai T-004 (14/10/2026)

- Vị trí: module `platform` (D-42); module khác dùng qua `platform.api`; chỉ `platform` đọc biến môi trường (C7).
- Biến bắt buộc theo tiến trình lấy từ cột "Dùng bởi" ở mục 7 (`lệnh migration` → tiến trình `migrate`). `AIEOS_BACKUP_TARGET` dùng bởi công cụ backup (T-605), không được tiến trình Python nạp.
- Không đặt giá trị mặc định cho biến nào (kể cả cấu hình): tài liệu không có giá trị mặc định cho session/lời mời/reauth (SRS-IAM-06 "giá trị cấu hình"); thiếu → tiến trình dừng.
- `[CẦN XÁC NHẬN — T-204]` `AIEOS_LLM_PROVIDERS`, `AIEOS_OCR_PROVIDERS`, `AIEOS_AI_BUDGET_LIMIT` là tùy chọn ở T-004 vì hệ thống phải chạy khi không có provider (SRS-NFR-07) và trần chi phí còn mở (GAP-14). `AIEOS_LLM_API_KEY_<NAME>` được nhận diện là secret (`is_secret_name`) nhưng điều kiện bắt buộc phụ thuộc danh sách provider — T-204 kiểm.
- Docker secrets: secret đọc từ `NAME` hoặc file ở `NAME_FILE` (bỏ ký tự xuống dòng cuối); đặt cả hai là lỗi. Biến cấu hình không nhận `_FILE`.
- Ngoài phạm vi: kiểm tra định dạng giá trị (URL, số, JSON, danh sách origin) thuộc task dùng biến (T-005, T-007, T-102, T-204); không từ chối biến `AIEOS_*` lạ (CI dùng `AIEOS_REQUIRE_DB`, `AIEOS_TEST_DATABASE_URL`).

## 14. Ghi chú triển khai T-005 (14/10/2026)

- Vị trí: `platform` (D-42). Model của module dùng `aieos.platform.api.Base`; vì `platform` không import module khác (C5), metadata đầy đủ cho so khớp model ↔ schema do `app` gom và truyền vào `run_migrations`/`compare_schema` (hiện chưa có model nào).
- Role CSDL là đối tượng cấp cụm, cần superuser để tạo → không nằm trong Alembic (chạy bằng `aieos_owner`, không có quyền tạo role). Thứ tự vận hành: superuser chạy `provision_roles.sql` trên CSDL đích → đặt mật khẩu role ngoài file → `python -m aieos.app migrate`. Compose (T-013) dùng cùng script.
- Quyền mặc định không gồm DELETE/TRUNCATE; bảng cần DELETE cấp riêng ở migration của task sở hữu (Database_Design §2: không DELETE trên `finance.*`, `audit.*`). `REPLICATION` cho `aieos_backup` thuộc T-605.
- Engine đồng bộ (psycopg 3). Engine async cho API (ADR-002) quyết định ở T-006/T-102 khi có request lifecycle.
- Test PostgreSQL dùng cụm test riêng: mỗi test tạo CSDL tạm, đặt mật khẩu ngẫu nhiên cho 3 role (không in ra). Chỉ chạy trong CI (máy phát triển không có PostgreSQL/Docker).
- Lỗi phát hiện qua CI và đã sửa trên branch: (1) gửi `provision_roles.sql` qua `exec_driver_sql` làm psycopg hiểu `%I` của `format()` là placeholder — test nay gửi nguyên văn qua kết nối psycopg (như psql); (2) test lệnh migrate bằng role app chạy sau khi đã ở head (không có thao tác nào nên thành công) — nay chạy trên CSDL chưa migrate.
- **Bằng chứng CI:** PR #9, commit `827e516`, GitHub Actions run `38543440774` (`completed`/`success`): `scripts/ci.sh` 18/18 bước, pytest 70 passed, 0 skipped (gồm 9 test PostgreSQL 18 của T-005). Hai run đỏ trước đó trên branch (`38543075935`, `38543253565`) là lỗi test ở ghi chú ngay trên.
- TC-MIG-01 (rỗng → head, so khớp model ↔ schema) có harness và chạy trong CI; TC-MIG-02, TC-DR-01/02 chưa chạy được ở T-005 — Q-51. TEST_Plan không đổi (mọi TC vẫn `NOT RUN`).

## 15. Ghi chú triển khai T-011 (14/10/2026)

- Vị trí: module `storage` (Architecture §3); dùng `platform.api` cho cấu hình (C4, C7). Interface theo ADR-004 (`put`, `get`, `exists`, `delete_unreferenced`); thêm `is_ready` cho `/health/ready` (ADR-012, T-006).
- Bố cục: `<AIEOS_STORAGE_PATH>/<2 ký tự đầu của key.hex>/<key.hex>`. Metadata (tên đã chuẩn hóa, SHA-256, kích thước, khóa) do `capture` lưu trong CSDL (T-202, T-203); cách ly file nhiễm mã độc thuộc T-203.
- `delete_unreferenced` không có tuổi tối thiểu mặc định: giá trị là quyết định vận hành của task gọi (job dọn dẹp); tham số bắt buộc, phải dương.
- Chưa làm: triển khai S3-compatible (ADR-004: phần mở rộng); giới hạn kích thước ở tầng upload (T-203).

## 16. Ghi chú triển khai T-006 (14/10/2026)

- Vị trí (D-42): log, correlation ID, health, cơ chế tạo FastAPI ở `platform`; lắp ráp ở `app/asgi.py` (`uvicorn --factory aieos.app.asgi:create_app` — server ASGI chọn ở T-013).
- Đường dẫn health theo base `/api/v1` (API_Specification §1.1): `/api/v1/health/live`, `/api/v1/health/ready`. Trạng thái API-SYS-01, API-SYS-02 ở API_Specification giữ `DESIGNED` (§1.10 chưa có giá trị cho "đã triển khai"; không tự thêm).
- Readiness dùng mã của T-005 (`database_ready`) và T-011 (`is_ready`), cả hai đã merge nhưng còn `IN_REVIEW`; cột "Phụ thuộc" của T-006 chỉ ghi T-001 nên T-006 không chờ hai task đó, nhưng nghiệm thu `/health/ready` đầy đủ gắn với chúng.
- Phát hiện khi viết test: logger `httpx` ghi URL đầy đủ (kể cả query string) ở INFO — sẽ lộ token/khóa trong URL khi provider adapter (T-204) dùng httpx. Đã hạ `httpx`, `httpcore` xuống WARNING trong `configure_logging`, có test.
- `/docs`, `/redoc`, `/openapi.json` tắt ở HTTP (giảm lộ thông tin); contract test (ADR-013) dùng `app.openapi()`.
- Lỗi 500 hiện là `Internal Server Error` dạng văn bản (không stack trace); `problem+json` có `correlation_id` thuộc T-007. Header `X-Request-ID` chưa có trên response 500 do lớp xử lỗi của Starlette nằm ngoài middleware — T-007.
- `TestClient` của starlette 1.7 cảnh báo deprecation khi dùng httpx (khuyến nghị gói `httpx2`); giữ httpx 0.28.1, chỉ dùng trong test.

## 17. Ghi chú áp dụng quyết định CDA 15/10/2026 (D-44…D-54)

- **Q-51 → D-44:** task chủ của mọi TC ở TEST_Plan §12. Dependency thêm: T-206 ← T-112; T-207 ← T-408; T-510 ← T-211; T-602 ← T-013; T-605 ← T-203, T-008, T-101, T-107, T-301, T-302, T-401, T-403. T-110 ← T-401 hoặc T-402: `[CẦN XÁC NHẬN]` — CDA chọn (a) nhưng không chọn giữa hai task; chưa ghi vào cột "Phụ thuộc" như dependency bắt buộc. DoD riêng của task không làm chủ TC đổi thành "bằng chứng thành phần" (T-111, T-212, T-409, T-504, T-509, T-303, T-402, T-206/T-208).
- **Dependency "các API" của T-601** (CDA ủy quyền agent liệt kê, D-44): task có endpoint trong cột "Thiết kế" (API-xx) và không `BLOCKED` — T-006, T-010, T-102, T-103, T-104, T-105, T-109, T-110, T-201, T-203, T-206, T-207, T-208, T-209, T-210, T-211, T-303, T-304, T-305, T-306, T-307, T-402, T-403, T-404, T-405, T-406, T-501, T-502, T-505, T-506, T-510, T-511, T-512. Không gồm task chỉ dùng API (T-308, T-513) và task `BLOCKED` (T-407: thêm khi mở khóa). Chưa ghi danh sách này vào cột "Phụ thuộc" ở mục 4 để bảng gọn; điều kiện bắt đầu T-601 = mọi task trong danh sách này `DONE`.
- **Dependency "Các task frontend" của T-608** (ủy quyền agent, D-44): T-012, T-111, T-207, T-212, T-308, T-409, T-504, T-509, T-513 (task có phần giao diện), cùng T-013.
- **D-49:** thêm T-308 (P3) và T-513 (P5); ID kế tiếp trong dải, chưa dùng ở tài liệu nào. Tổng task: 83.
- **D-51 → cột "Sẵn sàng":** `PARTIAL` → `READY`: T-112, T-206, T-207, T-403, T-501, T-505, T-511. Vẫn `PARTIAL`: T-108 (SRS-ACC-04), T-205 (D-50), T-306, T-402, T-502, T-504, T-510, T-513. Vẫn `BLOCKED`: T-003, T-013 (đến khi bắt đầu — công cụ đã duyệt, xem dưới), T-407, T-604, T-901…T-908.
- **D-43 + D-45:** công cụ Compose đã duyệt (Caddy, ClamAV + service cập nhật chữ ký riêng; không `observability`) → T-003 hết lý do `BLOCKED`; cột "Sẵn sàng" của T-003, T-013 cập nhật ở mục 4.
- **D-46:** Implementation_Plan, TEST_Plan, CLAUDE.md được duyệt từ 15/10/2026.
- Rủi ro mới (D-50): dữ liệu gửi provider cloud ngoài Việt Nam khi demo — mục 8.
- **D-55 (15/10/2026):** TC-AUD-01 chủ T-109; TC-AUD-02 tách phần T-102/T-103/T-104/T-105, đạt tổng ở T-105 (T-105 thêm dependency T-103, T-104); T-008 chỉ làm chủ TC-AUD-03.

## 18. Ghi chú triển khai T-008 (15/10/2026)

- Vị trí: module `audit` (Architecture §3); module khác chỉ dùng `audit.api` (C4, quy tắc 4). Tên hàm ghi `record` theo Architecture §3 quy tắc 4; thêm `record_separately` cho nhánh "thao tác bị từ chối → audit trong transaction riêng" của ADR-010.
- Quyền: revision `0001` đặt quyền mặc định SELECT, INSERT, UPDATE cho `aieos_app` trên mọi bảng mới → `0002` thu hồi UPDATE (và DELETE, TRUNCATE cho chắc) trên `audit.event` để khớp Database_Design §2. Trigger dùng SQLSTATE `42501` như lỗi quyền.
- Rủi ro còn lại (ADR-010): `aieos_owner` có thể `ALTER TABLE … DISABLE TRIGGER`; không có chuỗi hash trong MVP. `aieos_app` không làm được (test).
- Che dữ liệu: dùng chung `platform.api.redact` (T-006) cho tên khóa nhạy cảm; trường nhạy cảm theo nghiệp vụ (SEC-DC-02: CCCD, số tài khoản, lương…) do nơi gọi khai báo qua `masked_fields` — phát hiện tự động thuộc T-112. Nội dung tài liệu không được truyền vào `changes` (trách nhiệm nơi gọi; SRS-AUD-02).
- Chưa có khóa ngoại `actor_user_id`, `on_behalf_of_user_id` → `identity.user_account` (T-101 chưa có bảng); thêm ở migration của T-101 nếu CDA/thiết kế yêu cầu — Database_Design §9 không ghi khóa ngoại.
- `app/metadata.py`: composition root nạp `<module>.api` để model đăng ký vào `Base.metadata`; lệnh `migrate` và TC-MIG-01 dùng metadata này. Module mới có bảng phải được thêm vào `MODULE_APIS`.
- Ngoài phạm vi: đọc audit và phân quyền xem (SRS-AUD-04, T-110); phân vùng theo tháng (ADR-010: khi dung lượng lớn).
- Môi trường: máy phát triển nay có Docker (29.8.0); test PostgreSQL chạy local được bằng container `postgres:18` tạm (chỉ bind `127.0.0.1`).
- **D-56 (15/10/2026):** TC-JOB-05 chủ T-203; tham số kỹ thuật job queue (lease 300 s, backoff, poll, reaper/scheduler) là hằng số `PROPOSED` trong code; lịch chỉ `interval`, không chạy bù; M-05 tách theo task.

## 19. Ghi chú triển khai T-009 (15/10/2026)

- Vị trí: module `jobs` (Architecture §3); dùng `audit.api` (audit `schedule.skipped`, từ chối quyền) và `platform.api`; không import module nghiệp vụ (C2). Tiến trình worker lắp ở `app/worker.py` (D-42).
- Trạng thái chuyển theo Architecture §8.4. Claim, hoàn tất, lỗi, reaper đều có điều kiện `status`/`locked_by` để worker đã mất job (lease hết hạn) không ghi đè: kết quả của lần chạy đó bị rollback (TC-JOB-03).
- Lease: claim đặt lease mặc định 300 s cho mọi loại job; handler gọi `ctx.extend_lease()` khi chạy lâu (không có lease riêng theo loại job — chưa có yêu cầu).
- Kiểm tra quyền (SRS-JOB-03): loại job khai báo `permission` phải có `initiated_by` (chặn khi xếp); trước khi chạy, worker gọi authorizer do `app` cung cấp. Chưa có `access.policy` (T-108) nên `app` dùng `deny_all` — job cần quyền sẽ `FAILED` `PERMISSION_DENIED` cho tới khi T-108/T-203 nối authorizer thật. Có khoảng hở nhỏ giữa lúc kiểm tra và lúc handler chạy (hai transaction).
- Lịch: chỉ `interval` không chứa tháng/năm (đổi được sang khoảng cố định); job từ lịch không có người khởi tạo, payload `{"slot": <ISO>}`; loại job cần quyền không được đặt lịch. Lịch có `kind` chưa đăng ký ở tiến trình → bỏ qua, không nhảy `next_run_at`, log cảnh báo.
- Quét tĩnh TC-JOB-06 (`tests/test_jobs.py`): import `aieos.gateway`, `aieos.providers` và module nghiệp vụ (`goals`, `work`, `org`, `knowledge`, `finance`, `capture`, `sales`, `insights`), cùng chuỗi SQL nhắc bảng của các schema đó. Giới hạn: không bắt được import động hay SQL dựng từ biến. Hiện chưa module nào đăng ký loại job, nên quét ứng dụng là rỗng; ca vi phạm cố ý chứng minh test đỏ.
- Ngoài phạm vi: kill switch thật và `CANCELLED` `AI_CONTENT` (T-301, T-303, T-511); gateway (T-302); dọn job cũ (cần DELETE và chính sách lưu trữ, GAP-15); trang tình trạng hệ thống (T-110 dùng `count_by_status`); `notify.notification` (T-010).

## 20. Ghi chú triển khai T-007 (15/10/2026)

- Vị trí: `platform` (D-42: hạ tầng HTTP dùng chung); module khác dùng qua `platform.api`.
- **Idempotency:** Database_Design INV-08 đặt khóa ở chính bảng tài nguyên (`UNIQUE (created_by, idempotency_key)`), không có bảng lưu response trung tâm → T-007 không tạo bảng; `run_idempotent` dùng hàm `find`/`create` của module sở hữu bảng. Để phát hiện "cùng khóa, khác nội dung" (SRS-GEN-03), bảng có endpoint `IDEMPOTENT` cần lưu dấu vân tay request (vd. cột `request_hash`) — ghi chú ở Database_Design INV-08; task sở hữu bảng thêm cột trong migration của mình. Kết quả phát lại do module dựng lại từ bản ghi (cùng status).
- **CSRF:** token đồng bộ, không lưu, gắn với token session qua HMAC (`AIEOS_CSRF_KEY`); đổi session (đăng nhập, MFA) → token đổi theo. Danh sách miễn token (`app/asgi.py` `CSRF_EXEMPT_PATHS`) hiện rỗng — T-102/T-105 thêm `POST /auth/login`, `/auth/mfa/verify`, `/auth/invitations/accept` (API_Specification §1.2). Request thay đổi trạng thái không có `Origin` bị từ chối.
- **Rate limit:** tài liệu không có giá trị giới hạn (API_Specification §1.9 chỉ nêu đối tượng áp dụng) → không đặt mặc định; task dùng (T-102, T-103, T-104, T-105) phải lấy giá trị được duyệt. `[CẦN XÁC NHẬN]`: bộ đếm trong bộ nhớ từng tiến trình — khi chạy nhiều worker ASGI, giới hạn thực tế nhân theo số worker; khóa tài khoản theo số lần sai dùng `identity.login_attempt` (T-101/T-102).
- Theo bảng task chủ (Q-51_TC_Ownership_Draft §6, D-44): TC-GEN-03, TC-GEN-04 ở T-007 dùng route thử + bảng thử theo mẫu INV-08; T-603 chạy lại trên endpoint nghiệp vụ.
- Ngoài phạm vi: session/xác thực (TC-GEN-06, T-102); kiểm log khi đăng nhập/upload/gọi provider (TC-SEC-05, T-602).

## 21. Ghi chú triển khai T-101 (15/10/2026)

- Vị trí: module `identity`; bảng theo Database_Design §4, migration `0004` (M-02).
- `citext`: extension trusted, tạo bởi `aieos_owner` (chủ CSDL) trong schema `public`; downgrade xóa extension.
- Ràng buộc bổ sung suy ra từ Database_Design §4 (không thêm nghiệp vụ mới): `INVITED` ⇔ `password_hash` NULL ("NULL khi `INVITED`"); `mfa_enabled` ⇒ có `mfa_secret_enc`; mọi hash 32 byte (SHA-256, INV-16); `absolute_expires_at > created_at`.
- Chưa có khóa ngoại `user_account.employee_id` → `org.employee` vì bảng của T-201 chưa có — thêm ở migration của T-201.
- `[CẦN XÁC NHẬN]` `session.csrf_token_hash` (Database_Design §4) giữ theo thiết kế, cho phép NULL. T-007 dùng token CSRF đồng bộ không lưu (HMAC của token session bằng `AIEOS_CSRF_KEY`, Implementation_Plan §20) nên cột này hiện không được dùng; T-102 quyết định giữ hay đề xuất bỏ khỏi Database_Design.
- `login_attempt` cần dọn theo lịch (Database_Design §4) — cần quyền DELETE và chính sách lưu trữ; chưa cấp DELETE (không task nào dọn ở T-101).
- Hàm băm token đặt ở `identity.api` để T-102 (session), T-103 (mã khôi phục), T-105 (lời mời) dùng chung.

## 22. Ghi chú triển khai T-107 (15/10/2026)

- Vị trí: module `access`; migration `0005` (M-03). Seed là bản chụp cố định của Architecture §6 trong revision; test đọc bảng §6 và so khớp — sửa §6 sau này phải kèm migration mới.
- INV-11 mở rộng theo SRS-ACC-07 ("không gỡ/khóa/vô hiệu Admin hoạt động cuối cùng"): ngoài trigger `trg_last_admin_guard` trên `user_role` (Database_Design §4), thêm trigger `trg_last_admin_status` trên `identity.user_account` khi `status` rời `ACTIVE`. Advisory lock `admin-membership` đặt ngay trong trigger (thay vì chỉ ở ứng dụng) để mọi đường ghi đều tuần tự hóa (A4). Trước bootstrap (T-106) chưa có ADMIN nào nên trigger không chặn gì.
- `aieos_app` được DELETE trên `access.user_role` vì Database_Design §4 mô tả "xóa role" có trigger chặn; `assignment` thu hồi bằng `revoked_at` (SRS-ACC-08) nên không có DELETE. Danh mục role/permission chỉ SELECT (chỉ đổi qua migration).
- SQLSTATE riêng của trigger: `AE001` (ADMIN+CFO), `AE002` (ADMIN cuối), `AE003` (assignment không đủ điều kiện); service `access` ánh xạ sang mã lỗi API_Specification §10.
- Ngoài phạm vi: `authorize()` và bộ lọc phạm vi (T-108); API quản trị, step-up, thu hồi session khi đổi role (T-104, T-109); người giữ quyền tài chính và `goals.activate` (OPEN_DECISIONS 0.7).

## 23. Ghi chú triển khai T-102 (15/10/2026)

- Vị trí: module `identity` (`auth.py` dịch vụ, `router.py` endpoint); `app/asgi.py` lắp ráp. Module khác bảo vệ endpoint bằng dependency `Authenticator.require_session` (SRS-GEN-01); `PUBLIC_PATHS` liệt kê endpoint công khai, test TC-GEN-06 gọi mọi endpoint lấy từ OpenAPI của ứng dụng.
- Khóa tạm (SRS-IAM-07 "giá trị cấu hình"): áp nguyên tắc D-57 (biến bắt buộc, không mặc định) cho `AIEOS_AUTH_LOCKOUT_THRESHOLD`, `AIEOS_AUTH_LOCKOUT_MINUTES`. Đủ ngưỡng → `locked_until` và đặt lại bộ đếm; tài khoản `status = 'LOCKED'` (khóa bởi quản trị) cũng trả `423` sau khi mật khẩu đúng.
- Lỗi tìm thấy và sửa trong khi làm: điều kiện ngắn mạch `row is None or not verify(...)` bỏ qua kiểm tra Argon2 khi email không tồn tại → lộ thời gian (dò email); test TC-IAM-03 (đếm số lần kiểm tra) bắt được và giữ chống hồi quy.
- CSRF (T-007) đổi: request không có cookie session chỉ bị kiểm `Origin` — không có quyền nào để giả mạo; endpoint trả `401` (TC-GEN-06). Request có session vẫn bắt buộc token (TC-GEN-01 không đổi).
- `session.csrf_token_hash` (Database_Design §4): không dùng — CSRF đồng bộ tính bằng HMAC của token session (T-007). `[CẦN XÁC NHẬN]` giữ cột (cho phép NULL) hay bỏ khỏi Database_Design.
- IP lấy từ kết nối (`request.client.host`); sau reverse proxy (T-003) cần cấu hình nguồn IP tin cậy — `[CẦN XÁC NHẬN]` khi làm T-003/T-013.
- Ngoài phạm vi: API MFA (T-103), reauth/đổi mật khẩu/thu hồi session khi đổi role (T-104, T-109), lời mời (T-105), phạm vi quyền (T-108).
- **D-58 (15/10/2026):** T-010 thêm dependency T-102; T-106 thêm dependency T-010; TC-NTF-01 chủ T-510 (tách phần ở T-304, T-403, T-505); `AIEOS_PASSWORD_MIN_LENGTH` là biến cấu hình bắt buộc.

## 24. Ghi chú triển khai T-010 (15/10/2026)

- Vị trí: module `notify` (`service.py`, `router.py`); migration `0006` (phần `notify` của M-05, D-56); `app/asgi.py` lắp router với dependency `Authenticator.require_session` (session đủ MFA). Phân trang cursor dùng chung ở `platform/http.py` (`encode_cursor`, `decode_cursor`, `PAGE_DEFAULT_LIMIT` = 20, `PAGE_MAX_LIMIT` = 100 theo API_Specification §1.8).
- Module khác tạo thông báo bằng `notify.api.notify(session, user_id=, type=, title=, link=, body=)` trong transaction của thao tác nghiệp vụ (thông báo chỉ tồn tại khi thao tác được ghi). `type` là chuỗi tự do — danh mục loại thông báo do task phát sinh sự kiện đặt (T-106, T-304, T-403, T-505…); chưa có tài liệu liệt kê.
- SRS-NTF-02 (không dữ liệu nhạy cảm): CSDL/service không kiểm được nội dung; trách nhiệm ở module gọi và được kiểm ở phần TC-NTF-01 của T-304, T-403, T-505 (D-58). T-010 bảo đảm: chỉ người nhận đọc/đánh dấu được (người khác → `404`), `link` chỉ là đường dẫn nội bộ (service + CHECK CSDL) — quyết định kỹ thuật của agent để thông báo không dẫn ra ngoài hệ thống.
- API-NOT-02 trả `200` kèm thông báo (API_Specification §8 không ghi response; chọn để frontend cập nhật ngay); gọi lại giữ nguyên `read_at`.
- Ngoài phạm vi: số chưa đọc, lọc theo trạng thái, dọn thông báo cũ (cần DELETE + chính sách lưu trữ), giao diện chuông thông báo (T-111/T-513).

## 25. Ghi chú triển khai T-106 (15/10/2026)

- Vị trí: `identity/admin.py` (`bootstrap_admin`, `recover_admin` — logic), `app/admin_cli.py` (lệnh `python -m aieos.app bootstrap-admin|recover-admin`); `access.api.active_admins` (ADMIN có `status = 'ACTIVE'`, cùng định nghĩa INV-11). Không có endpoint HTTP (ADR-006).
- Cấu hình: tiến trình mới `admin-cli` trong loader (T-004) — `AIEOS_DATABASE_URL` (role `aieos_app`, đủ quyền: chỉ INSERT/UPDATE) và `AIEOS_PASSWORD_MIN_LENGTH` (D-58; bắt buộc, không mặc định; thiếu/sai → mã thoát 2). Mật khẩu: `--password-file` (Docker secret) hoặc nhập tương tác hai lần; không nhận qua tham số dòng lệnh (lộ trong lịch sử shell/danh sách tiến trình). Độ dài tối đa 1024 (giới hạn API đăng nhập). Không in email hay mật khẩu.
- Bootstrap: advisory lock `admin-membership` (khóa của trigger INV-11) → chưa có ADMIN `ACTIVE` → tài khoản `ACTIVE`, `must_enroll_mfa = true`, `created_by = NULL`; `grant_role` ADMIN với `granted_by = NULL`; audit `identity.admin.bootstrap` (`actor_type = BOOTSTRAP`). Email đã có tài khoản → từ chối (không nâng tài khoản có sẵn thành ADMIN — quyết định kỹ thuật của agent). Theo ADR-006 (nhập mật khẩu, buộc MFA); đề xuất "mật khẩu tạm buộc đổi ở lần đầu" của D-22 mục 3.3.2 là `PROPOSED`, ADR-006 không yêu cầu — không làm.
- Recover: cần `--confirm` (thiếu → mã 1, không đổi gì) và `--reason`; đích phải là ADMIN `ACTIVE` (trigger INV-11 bảo đảm luôn có ít nhất một). Đặt mật khẩu mới do người vận hành nhập; `mfa_enabled = false`, xóa `mfa_secret_enc`, `must_enroll_mfa = true`; đánh dấu mã khôi phục còn lại đã dùng; gỡ khóa tạm (`locked_until`, bộ đếm); `version + 1`; thu hồi mọi session; audit `identity.admin.recover` kèm lý do; thông báo `ADMIN_RECOVERED` (tiêu đề chung, không tên/email, không link) cho mọi ADMIN `ACTIVE` khác (T-010).
- `[CẦN XÁC NHẬN]` (CDA 15/10/2026: giữ hành vi hiện tại, xác nhận sau): khôi phục tài khoản ADMIN đang `LOCKED`/`DISABLED` (đổi trạng thái về `ACTIVE`) — chưa làm; hiện chỉ khôi phục ADMIN `ACTIVE`. CDA chấp nhận các lựa chọn kỹ thuật ở §24, §25 (link nội bộ, response API-NOT-02, không nhận mật khẩu qua tham số, từ chối email đã có, tiến trình `admin-cli`).
- Đăng nhập lần đầu sau bootstrap/recover: session ở trạng thái chờ MFA (T-102); đăng ký MFA là T-103.

## 26. Ghi chú triển khai T-103 (15/10/2026)

- Vị trí: `identity/mfa.py` (TOTP, mã hóa secret, mã khôi phục, `MfaService`), `identity/router.py` (`build_mfa_router`: API-AUTH-02/03/04), `Authenticator.rotate_session`; `app/asgi.py` nạp `AIEOS_TOTP_ENCRYPTION_KEY`. Migration `0007`: `identity.user_account.mfa_last_step` (Database_Design §4).
- TOTP theo RFC 6238: HMAC-SHA1, 6 chữ số, bước 30 giây (mặc định của ứng dụng xác thực phổ biến), chấp nhận lệch ±1 bước; mã đã chấp nhận không chấp nhận lại (RFC 6238 §5.2) nhờ `mfa_last_step`. Secret 20 byte; lưu AES-256-GCM, dữ liệu liên kết = id tài khoản. Thư viện mới: `cryptography` 50.0.2 (phát hành 30/09/2026, ≥ 2 tuần); TOTP tự viết bằng `hmac` chuẩn, kiểm bằng vector RFC 6238 Phụ lục B.
- Mã khôi phục: 10 mã, 10 ký tự (bảng chữ không có I, O, 0, 1), dạng `XXXXX-XXXXX`, không phân biệt hoa thường/gạch; CSDL lưu SHA-256 (INV-16); xác nhận đăng ký mới → mã cũ bị đánh dấu đã dùng (không DELETE). Số lượng, độ dài, cửa sổ lệch là tham số kỹ thuật do agent chọn (tài liệu chưa ghi).
- Phạm vi đăng ký: chỉ tài khoản bắt buộc MFA (role `ADMIN`) — MFA cho role khác là DEFERRED (D-30) → `403`. Đã bật MFA → `409 INVALID_STATE`; đặt lại MFA qua `recover-admin` (T-106).
- Xác minh/xác nhận xong → xoay session (thu hồi session chờ MFA, tạo session mới `mfa_verified`, ADR-006). Giới hạn thử theo IP + tài khoản dùng chung `AIEOS_AUTH_RATE_LIMIT_*` (D-57); sai mã không tính vào khóa tạm của đăng nhập (SRS-IAM-07 chỉ nói đăng nhập). Audit `auth.mfa.enroll`, `auth.mfa.enroll.confirm`, `auth.mfa.verify` (SECURITY; lý do `INVALID_CODE`/`RATE_LIMITED`, phương thức `TOTP`/`RECOVERY_CODE`), không ghi mã.
- Thay đổi API bổ sung (API_Specification §2, cập nhật trước khi code): response API-AUTH-01 thêm `mfa_enrolled` và `csrf_token` — session chờ MFA không gọi được `GET /auth/me` (TC-IAM-07) nhưng API MFA là POST cần `X-CSRF-Token`. Sau khi xoay session, frontend lấy token mới qua `/auth/me`.
- TC-IAM-06/07: test gọi **mọi** endpoint của `create_app` bằng session chờ MFA — API quản trị chưa có (T-105, T-109) sẽ tự thuộc phạm vi kiểm khi được thêm.
- Ngoài phạm vi: reauth/step-up (T-104), giao diện đăng ký MFA (T-111).

## 27. Ghi chú triển khai T-108 (15/10/2026)

- Vị trí: `access/policy.py` (`load_actor`, `authorize`, `require`, `scope_filter`, `PermissionGuard`, `OrgScope`); `platform/web.py` (`declare`, dependency toàn cục từ chối route không khai báo). Đúng Architecture §3 quy tắc 5 (mọi quyết định quyền qua `access.policy.authorize`).
- Mặc định deny: không có permission → `NO_PERMISSION`; có permission nhưng đối tượng ngoài phạm vi → `OUT_OF_SCOPE`. `require(..., hide=True)` trả `404 NOT_FOUND` (API_Specification §1.4, ADR-007), route-level trả `403 FORBIDDEN` + audit `access.denied` (SECURITY, DENIED, không ghi dữ liệu nghiệp vụ).
- Khai báo quyền cho route (SRS-ACC-09, TC-ACC-02): `PUBLIC` (khớp đúng API_Specification §1.2 — test đối chiếu `PUBLIC_PATHS`), `AUTHENTICATED` (chỉ cần session: `/auth/me`, đăng xuất, API MFA, thông báo) hoặc mã permission qua `PermissionGuard.route(...)` (khai báo và kiểm tra đi cùng nhau). Dependency toàn cục chạy trước mọi dependency của route, áp cả route ẩn khỏi OpenAPI → route quên khai báo bị `403` (fail-closed).
- Phạm vi (SRS-ACC-03, Architecture §6): quyền nền theo role — CEO toàn công ty; CFO tài chính toàn công ty + của mình; MANAGER đơn vị quản lý và cấp dưới; EMPLOYEE của mình; ADMIN không có `data.read`. Assignment: `COMPANY`, `ORG_UNIT` (cây con), `DOCUMENT_TYPE`, `REVIEW_QUEUE`. Tài nguyên quản trị (`business=False`) chỉ xét permission.
- Phần **chưa làm** (task `PARTIAL`, CDA 15/10/2026 cho bỏ qua): "team" của EMPLOYEE (SRS-ACC-04, TC-ACC-10 — định nghĩa còn mở ở mục 0 OPEN_DECISIONS) và "mục tiêu cha" (cần module `goals`) → hiện từ chối (mặc định deny).
- Cây tổ chức: `access` không đọc bảng `org.*` — `OrgScope` (đơn vị do người dùng quản lý, cây con) do T-201 cài; trước đó `NO_ORG` (MANAGER chỉ thấy dữ liệu của mình). `Resource.org_units` = đơn vị của đối tượng và các cấp trên (nơi gọi cung cấp).
- `PermissionGuard` chưa gắn vào router nào của `create_app` (chưa có endpoint cần permission nghiệp vụ); T-109, T-201… dùng khi thêm route.
- TC-ACC-03: không chạy đủ kịch bản ở T-108 (task/mục tiêu, `org.*` chưa có) — Q-52 → D-59: task chủ T-505, phần mục tiêu ở T-502; T-108 giữ bằng chứng thành phần (`scope_filter` trên bảng thử).

## 28. Ghi chú triển khai T-104 (15/10/2026)

- Vị trí: `identity/stepup.py` (`StepUpService.reauth`, `change_password`, `password_problem`), `Authenticator.require_step_up`, `Authenticator.revoke_sessions` (dùng lại ở T-109 cho đổi role/khóa tài khoản — SRS-IAM-11, TC-ACC-08), `MfaService.use_code` (dùng chung cho xác minh MFA và reauth); router `build_stepup_router` (API-AUTH-05, API-AUTH-09).
- Step-up (SRS-IAM-08): `reauth_at` gắn với **session** (reauth ở session này không mở khóa session khác); hiệu lực `AIEOS_REAUTH_MINUTES` (biến đã có, nay đọc vào `AuthSettings`). Route `STEP-UP` dùng dependency `require_step_up` (T-105, T-109… dùng khi thêm route; `PermissionGuard` kết hợp được bằng cách thêm dependency này).
- Reauth: luôn kiểm Argon2 trước, tài khoản đã bật MFA phải kèm mã TOTP chưa dùng hoặc mã khôi phục; sai → `401 INVALID_CREDENTIALS` không phân biệt lý do (lý do chỉ ở audit: `INVALID_PASSWORD`/`INVALID_CODE`). Giới hạn thử D-57 theo IP + tài khoản. Sai reauth **không** tính vào khóa tạm (SRS-IAM-07 chỉ nói đăng nhập) — lựa chọn của agent, đã có rate limit.
- Đổi mật khẩu: không yêu cầu mật khẩu cũ trong body vì đã qua reauth trong cửa sổ; không kiểm trùng mật khẩu cũ/lịch sử (tài liệu không yêu cầu); session hiện tại giữ nguyên, session khác bị thu hồi (API_Specification API-AUTH-09).
- `AuthSettings` thêm `reauth`, `password_min_length` (đọc từ `AIEOS_REAUTH_MINUTES`, `AIEOS_PASSWORD_MIN_LENGTH`; sai → api thoát mã 2). CLI T-106 dùng chung `password_problem`.
- TC-IAM-08 chủ T-104; phần đổi mật khẩu của TC-AUD-02 (chủ T-105, D-55) là bằng chứng thành phần.
- D-59 (CDA, 15/10/2026): TC-ACC-03 → chủ T-505, phần mục tiêu ở T-502 (đóng Q-52).

## 29. Ghi chú triển khai T-109 (15/10/2026)

- Vị trí: `identity/users.py` (`UserAdmin`: danh sách, trạng thái, role) + `identity/router.py` (`build_user_admin_router`: API-ADM-01/04/05); `access/router.py` (`build_access_admin_router`: API-ADM-06/07/08/09); `access/service.py` (`set_roles`, `list_assignments`, `role_catalog`, idempotency). Quyền qua `PermissionGuard.route(permission, step_up=...)` (T-108); `PermissionGuard` nay nhận `require_step_up` (T-104) — kiểm permission trước, step-up sau (người không có quyền nhận `403`, không bị mời reauth).
- Thu hồi session (SRS-IAM-11): đổi role, giao/thu hồi assignment, rời `ACTIVE` → thu hồi mọi session của tài khoản đích. `access` không import `identity`: composition root truyền `Authenticator.revoke_sessions` làm `on_change`.
- **Lỗi tìm thấy và sửa:** test TC-ACC-06 (hai ADMIN gỡ nhau đồng thời) bắt deadlock — service khóa dòng tài khoản đích trước, trigger INV-11 lấy advisory lock `admin-membership` sau rồi đọc các ADMIN khác → thứ tự khóa ngược nhau. Sửa: `UserAdmin` lấy advisory lock trước khi khóa dòng (A4 "tuần tự hóa"). 
- Migration `0008`: `access.assignment.idempotency_key`, `request_hash`, UNIQUE `(granted_by, idempotency_key)` — API-ADM-07 `IDEMPOTENT` theo INV-08 (Database_Design §4 trước đó chưa có cột).
- Lựa chọn của agent: không tự đổi trạng thái tài khoản của mình (`403`, tránh tự khóa); `reason` của API-ADM-04 tùy chọn (tài liệu chỉ bắt buộc ở API-ADM-05); API-ADM-08 không nhận lý do (`revoke_assignment` T-107 không có cột lý do thu hồi); tài khoản `INVITED` không đổi trạng thái ở API-ADM-04.
- Audit (SRS-AUD-01, TC-AUD-01): thành công ghi trong cùng transaction (`access.role.grant/revoke`, `access.assignment.*`, `identity.user.status`); từ chối quyền `access.denied` `DENIED`; lỗi nghiệp vụ `FAILED` (transaction riêng, `reason` = mã lỗi).
- API-ADM-02/03 (tạo tài khoản, lời mời) thuộc T-105; API-ADM-10/11 thuộc T-110.

