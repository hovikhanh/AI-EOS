# AI-EOS — Architecture (Stage 2C)

> Phiên bản: 1.3 · Ngày: 14/10/2026 · Trạng thái: **Baseline kiến trúc Stage 2C — chờ CDA review** · Thay đổi: §13
> Hiện trạng: AI-EOS **chưa có code** (D-04). Tài liệu mô tả kiến trúc mục tiêu; không có thành phần nào ở trạng thái đã triển khai.
> Liên quan: [ADR-001…013](decisions/), [Database_Design.md](Database_Design.md), [API_Specification.md](API_Specification.md), [Decision_Log.md](../00-source/Decision_Log.md), [Requirements_Traceability.md](../00-source/Requirements_Traceability.md).

**Nguồn thẩm quyền dùng trong tài liệu**

| Nhãn | Ý nghĩa |
| --- | --- |
| `CDA` | Quyết định trực tiếp của chủ dự án đã ghi ở Decision_Log (D-xx) |
| `CDA_DIRECTIVE` | Quy tắc vận hành/nghiệp vụ CDA chốt trong yêu cầu ngày 12/10/2026 (K1–K6, F1–F7, R1–R8, A1–A6) |
| `ARCHITECTURE_DECISION` | Lựa chọn kỹ thuật chốt theo thẩm quyền kiến trúc (ADR-001…013 và các chi tiết thiết kế trong tài liệu này) |
| `SOURCE` | Yêu cầu có trong `BRD_Review.md` / `UI_UX_Proposal.md` (ID ở Requirements_Traceability) |
| `[CẦN XÁC NHẬN]` | Không có nguồn; dùng mặc định an toàn được ghi rõ |

**Sai lệch quy trình (đã xử lý ở 1.1):** bản 1.0 được viết khi Stage 2B chưa thực hiện. Stage 2B đã hoàn thành ([SRS](../02-requirements/SRS.md)); đối chiếu và thay đổi ở §13. Nội dung gốc của ghi chú: Stage 2B (PRD, SRS, UX Flows) **chưa được thực hiện**. Theo chỉ đạo của CDA, Stage 2C được thực hiện trước, dựa trực tiếp trên requirement ID trong Requirements_Traceability. Các module chưa có đặc tả nghiệp vụ (KPI/OKR, Task, CEO Briefing, Sales Lite — D-24) chỉ có kiến trúc ở mức ranh giới và thực thể tối thiểu có nguồn; chi tiết chờ 2B. Khi 2B hoàn thành phải đối chiếu lại Database_Design và API_Specification.

---

## 1. Phạm vi và động lực kiến trúc

**Phạm vi MVP (P0) theo nguồn và quyết định:** Data Capture C1–C5 (SC-01), Data Foundation cơ bản (SC-02), Autonomy L0–L3 + kill switch (SC-03), Finance Lite (SC-04), Sales Pipeline Lite (SC-05, chưa có đặc tả), KPI/OKR + check-in, Task, CEO Briefing (D-24, chưa có đặc tả).
**Ngoài MVP:** hóa đơn/biên lai (D-17), email forwarding (D-18), C6–C10, L4 (D-11), Meeting bot (SC-06), Performance Cycle (SC-07), Workflow Engine, Procurement (SC-10).

| Động lực | Nguồn | Hệ quả kiến trúc |
| --- | --- | --- |
| Toàn vẹn tài chính, không xóa lịch sử | D-12, D-13, F1–F7 | Một CSDL ACID, state machine + ràng buộc CSDL (ADR-001, ADR-009) |
| AI không vượt quyền, kill switch ở backend | D-09…D-12, BR-04 | Write gateway duy nhất (ADR-008) |
| Truy vết nguồn gốc dữ liệu | BR-01, FR-DF-04, FR-DC-23 | Bảng lineage, liên kết tài liệu gốc |
| Chạy Local/Docker Compose, chi phí thấp | D-03, D-07 | Modular monolith, queue trên PostgreSQL, công cụ mã nguồn mở |
| Không khóa provider AI, dữ liệu mật ở nội bộ | D-07, SEC-DC-04 | Provider adapter + định tuyến theo phân loại (ADR-011) |
| Xử lý tài liệu bất đồng bộ | NFR-01, NFR-02 | Worker + job queue (ADR-005) |
| Nhập tay luôn hoạt động khi AI lỗi | BR-21, NFR-07 | Luồng thủ công không phụ thuộc module `providers` |

---

## 2. C4 — System Context và Container

### 2.1. System Context

```mermaid
flowchart LR
    CEO["CEO"]
    MGR["Manager / Employee"]
    CFO["CFO"]
    REV["Reviewer (assignment)"]
    ADM["Admin"]
    SYS["AI-EOS"]
    LLMLOCAL["LLM / OCR chạy local"]
    LLMCLOUD["LLM / OCR cloud (tùy chọn, chỉ dữ liệu không nhạy cảm)"]
    BAK["Nơi lưu bản sao lưu ngoài máy"]
    CEO -->|"Briefing, hỏi AI, quyết định"| SYS
    MGR -->|"Nhập liệu, tải tài liệu, xác nhận việc"| SYS
    CFO -->|"Duyệt giao dịch tài chính"| SYS
    REV -->|"Review trích xuất"| SYS
    ADM -->|"Cấu hình, kill switch, quản lý tài khoản"| SYS
    SYS -->|"Trích xuất, phân loại, trả lời"| LLMLOCAL
    SYS -.->|"Khi được phép theo phân loại dữ liệu"| LLMCLOUD
    SYS -->|"Backup CSDL và file"| BAK
```

Hệ thống ngoài như email, Zalo/Slack/Teams, Google/M365, phần mềm kế toán, ngân hàng: **không có trong MVP** (D-18, D-31, D-32).

### 2.2. Container

```mermaid
flowchart TB
    subgraph Client["Trình duyệt / PWA"]
        SPA["React SPA (Vite, TypeScript)"]
    end
    subgraph Host["Máy triển khai - Docker Compose"]
        PROXY["Reverse proxy: TLS, file tĩnh, header bảo mật"]
        API["API process (FastAPI)"]
        WRK["Worker process (job, scheduler, reaper)"]
        DB[("PostgreSQL")]
        VOL[("Volume file gốc")]
        AV["Malware scanner"]
        LLM["LLM / OCR runtime local (tùy chọn)"]
    end
    EXT["Provider cloud (tùy chọn)"]
    SPA -->|"HTTPS, cookie session, CSRF header"| PROXY
    PROXY -->|"/api"| API
    PROXY -->|"/"| SPA
    API --> DB
    API --> VOL
    WRK --> DB
    WRK --> VOL
    WRK --> AV
    WRK --> LLM
    WRK -.-> EXT
    API -.->|"Chat AI truyền dần"| LLM
```

| Container | Trách nhiệm | Không được |
| --- | --- | --- |
| Reverse proxy | TLS (chứng chỉ nội bộ ở local), phục vụ build SPA, chuyển `/api` tới API, đặt CSP và header bảo mật, giới hạn kích thước body | Phục vụ trực tiếp volume file |
| API | Xác thực, phân quyền, nghiệp vụ đồng bộ, xếp job, SSE chat | Gọi provider cho xử lý tài liệu nặng (để worker làm) |
| Worker | Tiền xử lý, quét mã độc, OCR, trích xuất, validate, commit qua gateway, lịch định kỳ, reaper | Mở cổng mạng; ghi domain bỏ qua gateway |
| PostgreSQL | Nguồn dữ liệu duy nhất, queue, audit, session | Publish cổng ra ngoài máy |
| Malware scanner | Quét file upload (FR-DC-08) | — |
| LLM/OCR local | Xử lý dữ liệu nhạy cảm tại chỗ | — |

---

## 3. Module boundaries và dependency rules

| Module | Trách nhiệm | Thực thể chính | Nguồn |
| --- | --- | --- | --- |
| `identity` | Tài khoản, mật khẩu, MFA, session, lời mời, bootstrap/recovery | user_account, session, invitation | D-22, A1–A6 |
| `access` | Role, permission, assignment, policy | role, permission, user_role, assignment | D-21, R1–R8 |
| `org` | Đơn vị, nhân sự (danh bạ), import danh sách | org_unit, employee | US-DC-007, FR-DCS-02 |
| `capture` | Upload, loại tài liệu, schema, pipeline, review, import, lineage | source_document, extraction, extracted_field, import_batch, data_lineage | Domain 22 |
| `goals` | Objective, KR, KPI, đo lường, check-in | objective, key_result, kpi, kpi_measurement, check_in | US-DC-005, FR-DCS-02 (chi tiết chờ 2B) |
| `work` | Task, cuộc họp, quyết định, action item | task, meeting, decision, action_item | US-DC-004, UC-06 (chi tiết chờ 2B) |
| `knowledge` | Tài liệu quy trình/SOP/chính sách | knowledge_item | FR-DCS-02 |
| `finance` | Kỳ báo cáo, giao dịch, phê duyệt, đảo | reporting_period, transaction | SC-04, ADR-009 |
| `sales` | Pipeline Lite | — (chờ 2B) | SC-05 |
| `insights` | Briefing, ô chỉ số, freshness; tính chỉ số qua API đọc của `finance`, `goals`, `work` | briefing, user_tile_preference | FR-HM, UX-12, SRS §8 |
| `ai` | Orchestrator, chat, bản nháp hành động, autonomy policy, kill switch, feedback, call log | action, kill_switch, autonomy_policy, tool | D-09…D-11, FR-AIQ |
| `gateway` | Cổng ghi duy nhất cho hành động AI và commit trích xuất | — (dùng bảng của `ai`) | ADR-008 |
| `jobs` | Queue, scheduler, reaper | job, schedule | ADR-005 |
| `audit` | Ghi/đọc audit | event | ADR-010 |
| `notify` | Thông báo in-app | notification | K6 |
| `storage` | Adapter lưu file | — | ADR-004 |
| `providers` | LLM/OCR/converter adapter | call_log (thuộc `ai`) | ADR-011 |
| `platform` | Hạ tầng dùng chung, không nghiệp vụ: cấu hình và secret (T-004); engine/session SQLAlchemy và tích hợp cấu hình Alembic (T-005); log JSON, correlation ID, health/readiness, cơ chế tạo ứng dụng FastAPI (T-006); hạ tầng HTTP dùng chung (T-007) | — (không bảng nghiệp vụ) | D-42 |
| `app` | Composition root: lắp ráp ứng dụng API (gắn router của các module), tiến trình worker, lệnh CLI; chỉ khởi tạo và nối module, không chứa nghiệp vụ | — | D-42 |

**Quy tắc phụ thuộc** (`ARCHITECTURE_DECISION`, kiểm tra tự động trong CI):
1. Module chỉ import interface công khai (`<module>.api`) của module khác, không import `models`/`repository` của module khác.
2. `ai`, `jobs`, `capture` **không** gọi service ghi của `goals`, `work`, `org`, `knowledge`, `finance` trực tiếp; chỉ qua `gateway`.
3. `gateway` gọi service ghi của domain qua đăng ký tool; domain không phụ thuộc ngược `gateway`.
4. Mọi module ghi audit qua `audit.api.record(...)` trong transaction hiện hành.
5. Mọi quyết định quyền qua `access.policy.authorize(...)`.
6. `providers` không phụ thuộc module nghiệp vụ nào.
7. Ghi trực tiếp của **người dùng** (form C1, giao dịch tài chính nhập tay) đi qua service của domain với authorization + audit; không cần gateway.
8. `platform` không import module `aieos` nào khác. Module khác dùng `platform` qua `platform.api` (quy tắc 1). `platform` không phải module nghiệp vụ nên `providers` được dùng `platform.api` (quy tắc 6) — `CDA_DIRECTIVE` D-42.
9. `app` chỉ import `<module>.api`; không module nào import `app` — D-42.
10. Chỉ `platform` được tạo engine SQLAlchemy, cấu hình logging toàn cục và đọc biến môi trường; module khác nhận cấu hình, session, logger qua `platform.api` — D-42.

---

## 4. Data model

Chi tiết ở [Database_Design.md](Database_Design.md). Nguyên tắc: một CSDL, schema theo module; bất biến quan trọng được thực thi bằng ràng buộc CSDL (CHECK, unique có điều kiện, trigger) ngoài kiểm tra ở ứng dụng.

---

## 5. Authentication và vòng đời tài khoản

Cơ chế ở ADR-006. Luồng chính:

```mermaid
sequenceDiagram
    autonumber
    actor U as Người dùng
    participant API as API
    participant DB as PostgreSQL
    U->>API: POST /auth/login (email, mật khẩu)
    API->>DB: Kiểm tra giới hạn thử, đọc hash Argon2id
    alt Sai thông tin hoặc bị khóa
        API->>DB: Tăng bộ đếm, audit SECURITY outcome DENIED
        API-->>U: 401 thông báo chung
    else Đúng
        API->>DB: Tạo session mới (hash token), mfa_verified = false
        API-->>U: Cookie session mới, yêu cầu MFA nếu bắt buộc
        U->>API: POST /auth/mfa/verify (mã TOTP)
        API->>DB: Xác minh, xoay session ID, mfa_verified = true
        API-->>U: Cookie session mới, CSRF token
    end
```

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    actor N as Người dùng mới
    participant API as API
    participant DB as PostgreSQL
    A->>API: POST /admin/users (step-up, email, role, lý do)
    API->>DB: Tạo user INVITED, invitation (hash token, hạn), audit
    API-->>A: Link mời hiển thị một lần
    A-->>N: Trao link ngoài hệ thống
    N->>API: POST /auth/invitations/accept (token, mật khẩu)
    API->>DB: Khóa invitation, kiểm tra chưa dùng và còn hạn
    API->>DB: Đặt mật khẩu, user ACTIVE, invitation used_at, audit
    API-->>N: Yêu cầu đăng nhập
```

| Bước | Kiểm soát |
| --- | --- |
| Bootstrap ADMIN đầu tiên (A2) | CLI trong container; từ chối nếu đã có ADMIN hoạt động; không secret hardcode; buộc MFA; audit `BOOTSTRAP` |
| Thay đổi role (A3) | Step-up + lý do + policy; trigger chặn `ADMIN`+`CFO`; CHECK chặn tự cấp; thu hồi session người bị đổi |
| Gỡ/khóa ADMIN (A4) | Advisory lock `admin-membership`; đếm ADMIN hoạt động sau thay đổi ≥ 1 |
| Tự nâng quyền (A5) | `granted_by <> user_id`; API trả 403 khi actor = target |
| Khôi phục (A6) | CLI `recover-admin` có cờ xác nhận; audit; thông báo ADMIN khác |
| Vận hành | Khuyến nghị ≥ 2 ADMIN; không tạo tài khoản giả để đạt số lượng |

---

## 6. Authorization và permission matrix

Cơ chế ở ADR-007. Nội dung role/quyền: `CDA_DIRECTIVE` R1–R8; chi tiết permission là `ARCHITECTURE_DECISION` để hiện thực R1–R8 theo nguyên tắc tối thiểu quyền.

**Ký hiệu:** `B` = quyền nền của role · `A` = chỉ có khi được giao assignment (role này đủ điều kiện nhận) · `—` = không có, không giao được trong MVP.

| Permission | Nhóm | ADMIN | CEO | CFO | MANAGER | EMPLOYEE | Phạm vi / ghi chú | Nguồn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `org.directory.read` | Đọc | B | B | B | B | B | Họ tên, chức danh, đơn vị, quản lý trực tiếp (không nhạy cảm); cần cho khớp tên người (UC-06, F3) | ARCH |
| `data.read` | Đọc | — | B | B | B | B | CEO: toàn công ty; CFO: dữ liệu tài chính toàn công ty + của mình; MANAGER: đơn vị và cấp dưới; EMPLOYEE: của mình, team, mục tiêu cha | UX §4.1, R4 |
| `finance.read` | Đọc | — | B | B | A | — | MANAGER: giao dịch mình tạo/gửi | ARCH |
| `hr.import` | Ghi | B | — | — | — | — | Chỉ import danh sách nhân sự/tổ chức; xem kết quả và lỗi theo dòng, không đọc lại toàn bộ hồ sơ | R4, US-DC-007 |
| `hr.profile.read` | Đọc | — | — | — | — | — | Trường nhân sự nhạy cảm. **Chưa có người giữ** (R6 NEEDS_CONFIRMATION) | R6 |
| `hr.salary.read` | Đọc | — | — | — | — | — | Dự trữ; MVP không lưu lương | R6 |
| `hr.export` | Đọc | — | — | — | — | — | Chưa có người giữ | R6 |
| `pii.unmask` | Đọc | — | — | — | — | — | Bỏ che dữ liệu cá nhân (SEC-DC-02). Chưa có người giữ; mặc định che với mọi người | R6, SEC-DC-02 |
| `record.submit` | Ghi | — | B | B | B | B | Nhập tay, nhập NL, tải file, import (trừ nhân sự) | US-DC-001…003 |
| `action.confirm` | Duyệt | — | B | B | B | B | Bản nháp hành động **không tài chính** mình khởi tạo hoặc thuộc đối tượng mình sở hữu (K4) | UX §7.1, K4 |
| `action.undo` | Ghi | — | B | B | B | B | Hành động L3 mình khởi tạo, trong hạn | BR-11 |
| `extraction.review` | Duyệt | — | A | A | A | A | Theo assignment hàng chờ (loại tài liệu/đơn vị); ADMIN không đủ điều kiện (R4) | FR-DC-21, R1 |
| `finance.submit` | Ghi | — | — | A | A | — | Tạo/gửi giao dịch theo assignment (R5) | R5 |
| `finance.approve` | Duyệt | — | — | A | — | — | Không duyệt giao dịch mình tạo/gửi; CEO không mặc định (R2) | R2, R5, F6 |
| `finance.reverse.request` | Ghi | — | — | A | — | — | Đề nghị đảo | R5 |
| `finance.period.manage` | Duyệt | — | — | A | — | — | Mở/khóa kỳ báo cáo quản trị; người giữ cụ thể `[CẦN XÁC NHẬN]` | F1 |
| `audit.read.admin` | Quản trị | B | — | — | — | — | Audit SECURITY/ADMIN; siêu dữ liệu audit BUSINESS/AI | R3, ADR-010 |
| `audit.read.business` | Đọc | — | B | — | — | — | Audit BUSINESS/AI, chỉ đọc, trong phạm vi `data.read` | R3 |
| `user.manage` | Quản trị | B | — | — | — | — | Tạo tài khoản, lời mời, khóa/mở | A1 |
| `role.assign` | Quản trị | B | — | — | — | — | Không tự cấp; chặn `ADMIN`+`CFO` | A3, A5, R7 |
| `assignment.manage` | Quản trị | B | — | — | — | — | Giao/thu hồi assignment | ARCH |
| `config.document_schema` | Quản trị | B | — | — | — | — | Loại tài liệu, schema, ngưỡng | US-DC-008 |
| `config.autonomy` | Quản trị | B | — | — | — | — | Trong trần L3 / tài chính L2 | R8 |
| `config.draft_expiry` | Quản trị | B | — | — | — | — | Thời hạn bản nháp, audit | K5 |
| `config.briefing_schedule` | Quản trị | B | — | — | — | — | Lịch tạo Briefing; step-up, audit | D-38 |
| `goals.activate` | Duyệt | — | A | — | A | — | Kích hoạt mục tiêu trong phạm vi; **chưa có quyền nền** (D-39, Q-28) | D-39 |
| `ai.kill_switch` | Quản trị | B | — | — | — | — | Chỉ ADMIN | D-09 |
| `system.health.read` | Quản trị | B | — | — | — | — | Trang tình trạng hệ thống | UX §4.1 |
| `ai.use` | Sử dụng AI | B (chỉ cấu hình/audit) | B | B | B | B | Công cụ AI bị giới hạn theo `data.read` của người dùng | UX §4.1 |

**Ràng buộc:** một tài khoản có thể có nhiều role (R7), trừ tổ hợp `ADMIN`+`CFO`. Assignment chỉ được giao cho tài khoản có role đủ điều kiện (cột `A`). Tách nhiệm vụ tính theo **tài khoản**, không theo role.

---

## 7. Financial approval, posting, reversal

Quy tắc ở ADR-009 (D-12, D-13, F1–F7).

### 7.1. State machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> PENDING_APPROVAL: Người tạo gửi
    DRAFT --> CANCELLED: Người tạo hủy
    PENDING_APPROVAL --> CANCELLED: Người tạo rút lại, có lý do
    PENDING_APPROVAL --> REJECTED: Người duyệt khác người tạo, có lý do
    PENDING_APPROVAL --> POSTED: Người duyệt khác người tạo, kỳ OPEN
    PENDING_APPROVAL --> ON_HOLD: Phát hiện kỳ không còn OPEN khi duyệt
    ON_HOLD --> CANCELLED: Người tạo rút lại, có lý do
    ON_HOLD --> REJECTED: Người duyệt khác người tạo, có lý do
    POSTED --> REVERSED: Bút toán đảo liên kết được ghi sổ
    CANCELLED --> [*]
    REJECTED --> [*]
    REVERSED --> [*]
```

Gửi duyệt yêu cầu kỳ của ngày giao dịch `OPEN` (ADR-009 Amendment 1, D-37). `ON_HOLD` là trạng thái phòng thủ: không khóa được kỳ còn giao dịch chờ duyệt, nên trong vận hành bình thường không đi vào nhánh này.

### 7.2. Duyệt và ghi sổ (xử lý đồng thời)

```mermaid
sequenceDiagram
    autonumber
    actor R as Người duyệt
    participant API as API finance
    participant POL as access.policy
    participant DB as PostgreSQL
    R->>API: POST /finance/transactions/{id}/approve, If-Match version, Idempotency-Key
    API->>POL: authorize finance.approve trên giao dịch
    POL-->>API: Allow hoặc Deny
    API->>DB: BEGIN
    API->>DB: SELECT giao dịch FOR UPDATE
    API->>DB: SELECT kỳ ghi sổ FOR SHARE
    alt Trạng thái khác PENDING_APPROVAL hoặc version lệch
        API->>DB: ROLLBACK, audit outcome FAILED
        API-->>R: 409 hoặc 412
    else Người duyệt trùng người tạo hoặc kỳ CLOSED
        API->>DB: ROLLBACK, audit outcome DENIED
        API-->>R: 403 hoặc 409
    else Hợp lệ
        API->>DB: UPDATE status POSTED, approved_by, version + 1
        API->>DB: INSERT transaction_event, audit event
        API->>DB: COMMIT
        API-->>R: 200
    end
```

Khóa kỳ (`finance.period.manage`) lấy `FOR UPDATE` trên hàng kỳ, nên không thể khóa kỳ trong lúc một giao dịch đang được ghi sổ vào kỳ đó.

### 7.3. Bút toán đảo

1. Người có `finance.reverse.request` gọi `POST /finance/transactions/{id}/reversals` với lý do và Idempotency-Key.
2. Kiểm tra: giao dịch gốc `POSTED`, loại `ORIGINAL` hoặc `ADJUSTMENT` (F4), chưa có bút toán đảo đang mở hoặc đã ghi (unique có điều kiện).
3. Tạo giao dịch `REVERSAL` ở `DRAFT` với số tiền mang dấu ngược, `reverses_id`, lý do; kỳ ghi sổ = kỳ của ngày gốc nếu `OPEN`, ngược lại là kỳ đang mở (F2); không có kỳ mở → 409 `NO_OPEN_PERIOD`.
4. Bút toán đảo đi qua `PENDING_APPROVAL → POSTED` như mọi giao dịch (người duyệt khác người đề nghị).
5. Khi bút toán đảo `POSTED`, trong cùng transaction giao dịch gốc chuyển `REVERSED`.
6. Muốn ghi lại số đúng: tạo giao dịch `ADJUSTMENT` với `adjusts_id` trỏ tới gốc, qua quy trình thường.

### 7.4. Thiếu người duyệt hợp lệ

Khi giao dịch vào `PENDING_APPROVAL`, hệ thống tính số người dùng hoạt động có `finance.approve` hợp lệ khác người tạo. Nếu bằng 0: giao dịch giữ `PENDING_APPROVAL`, gắn cờ `no_eligible_approver`, thông báo in-app cho người tạo và ADMIN, hiển thị trên trang tình trạng hệ thống. **Không** tự cấp quyền, không chuyển cho CEO, không tự duyệt (yêu cầu CDA 12/10/2026 §4). Cờ được tính lại khi có assignment mới.

---

## 8. Luồng xử lý: AI write gateway, kill switch, job, tài liệu, audit, adapter

### 8.1. Write gateway

```mermaid
flowchart TD
    REQ["Yêu cầu ghi: hành động AI hoặc commit trích xuất"] --> V["Validate tham số theo schema tool"]
    V -->|"Sai"| E1["Từ chối, audit FAILED"]
    V --> AZ["authorize người khởi tạo trên tool và đối tượng"]
    AZ -->|"Deny"| E2["Từ chối, audit DENIED"]
    AZ --> LV["Mức hiệu lực = min cấu hình, trần tool, L3; tài chính tối đa L2"]
    LV --> KS{"Kill switch bật và chưa có xác nhận của người?"}
    KS -->|"Có"| CAP["Hạ về L2"]
    KS -->|"Không"| ID
    CAP --> ID{"Idempotency key đã dùng?"}
    ID -->|"Có, cùng nội dung"| OLD["Trả kết quả cũ"]
    ID -->|"Có, khác nội dung"| E3["409, audit FAILED"]
    ID -->|"Chưa"| LVL{"Mức hiệu lực"}
    LVL -->|"L0 hoặc L1"| NOWRITE["Không ghi: chỉ trả thông tin hoặc gợi ý"]
    LVL -->|"L2 chưa xác nhận"| DRAFT["Tạo bản nháp ai.action PENDING_REVIEW, thông báo"]
    LVL -->|"L2 đã xác nhận hợp lệ hoặc L3"| EXEC["Gọi service domain qua tool, đặt hạn hoàn tác nếu L3"]
    DRAFT --> AUD["Audit cùng transaction"]
    EXEC --> AUD
    NOWRITE --> AUD
```

### 8.2. Kill switch (K1–K6)

| Tình huống | Hành vi | Nguồn |
| --- | --- | --- |
| Phạm vi | Một công tắc toàn hệ thống | K1 |
| Bật/tắt | Chỉ `ai.kill_switch` (ADMIN), step-up, lý do; cập nhật hàng singleton `FOR UPDATE`; audit; banner trên ứng dụng (UX-29) | D-09 |
| Ghi mới tự động (không có xác nhận của người) | Bị chặn ở gateway → bản nháp L2 | K2, ADR-008 |
| Ghi đã được người có thẩm quyền xác nhận (L2) | Vẫn thực hiện (D-09: hạ về L2, không tắt hẳn) | ARCH diễn giải K2 |
| Job trong queue / đang chạy | Đọc kill switch tại gateway ở thời điểm ghi; tạo bản nháp nếu đủ dữ liệu và an toàn, rồi mới đánh dấu job `SUCCEEDED` (cùng transaction); không đủ dữ liệu → `FAILED` lý do `BLOCKED_BY_KILL_SWITCH` + thông báo | K2 |
| Retry | Mỗi lần retry qua gateway; không thể biến lần bị chặn thành lần ghi | K2 |
| Ghi đã thực hiện trước khi bật | Giữ nguyên, không tự đảo | D-10 |
| Lịch định kỳ `may_write` | Bỏ qua khi bật; log + audit `schedule.skipped`; chạy ở chu kỳ kế tiếp, không chạy bù | K3 |
| Bản nháp | Reviewer có quyền tương ứng; tài chính không tự duyệt; quá hạn (mặc định 30 ngày, ADMIN cấu hình, có audit) → `NEEDS_REVIEW_STALE`, không xóa | K4, K5 |
| Thông báo | In-app ngay cho người khởi tạo; nhắc reviewer hằng ngày (job lịch); email/push là mở rộng chưa cấu hình | K6 |
| Tắt kill switch | Bản nháp không tự thực thi; chỉ hành động mới chạy L3 | D-10 |
| Job `ORCHESTRATION` (bộ hẹn giờ, nhắc việc, đánh dấu bản nháp quá hạn, dọn dẹp) | Chạy bình thường; không được gọi gateway, provider AI hay ghi bảng nghiệp vụ | D-38, ADR-005 Amendment 1 |
| Job `AI_CONTENT` (tạo nội dung Briefing) | Không khởi chạy/không tiếp tục; `CANCELLED` lý do `KILL_SWITCH`; không ghi nội dung mới; Trang chủ dùng bản gần nhất kèm nhãn "AI đang tạm dừng" | D-38 |
| Quản lý lịch Briefing | Thao tác cấu hình (`config.briefing_schedule`), step-up, audit; không kích hoạt tạo nội dung khi kill switch bật | D-38 |
| Chat AI chỉ đọc theo yêu cầu người dùng | Hoạt động (L0, không ghi) — diễn giải `ARCHITECTURE_DECISION`, ghi ở ADR-008 Amendment 1 | D-09 |
| L0/L1, ghi trực tiếp của người dùng | Không bị ảnh hưởng | BRD §4.2 |

### 8.3. Trạng thái bản nháp hành động AI

```mermaid
stateDiagram-v2
    [*] --> PENDING_REVIEW: Gateway tạo bản nháp L2
    PENDING_REVIEW --> EXECUTED: Reviewer hợp lệ xác nhận
    PENDING_REVIEW --> REJECTED: Reviewer từ chối, có lý do
    PENDING_REVIEW --> NEEDS_REVIEW_STALE: Quá thời hạn cấu hình
    NEEDS_REVIEW_STALE --> EXECUTED: Reviewer xác nhận sau rà soát
    NEEDS_REVIEW_STALE --> REJECTED: Reviewer từ chối
    [*] --> EXECUTED: L3 thực thi trực tiếp
    EXECUTED --> UNDONE: Hoàn tác trong hạn bằng hành động bù
    EXECUTED --> FAILED: Lỗi khi thực thi
    REJECTED --> [*]
    UNDONE --> [*]
```

Hoàn tác của hành động không tài chính là hành động bù có audit; dữ liệu tài chính không bao giờ ở L3 nên không đi nhánh này (D-12).

### 8.4. Job queue, retry, idempotency

```mermaid
sequenceDiagram
    autonumber
    participant API as API
    participant DB as PostgreSQL
    participant W as Worker
    participant GW as Gateway
    API->>DB: BEGIN, ghi nghiệp vụ, INSERT job (idempotency_key), COMMIT
    W->>DB: UPDATE job SET RUNNING, lease, attempts + 1 WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED)
    W->>W: Xử lý (OCR, LLM qua adapter)
    W->>DB: BEGIN
    W->>GW: Ghi kết quả qua gateway
    GW->>DB: Kiểm tra quyền, autonomy, kill switch, idempotency, audit
    W->>DB: UPDATE job SUCCEEDED, COMMIT
    Note over W,DB: Process chết trước COMMIT thì không có gì được ghi, lease hết hạn, reaper trả job về QUEUED
```

| Trạng thái job | Chuyển |
| --- | --- |
| `QUEUED` → `RUNNING` | Claim với `SKIP LOCKED`, đặt lease |
| `RUNNING` → `SUCCEEDED` | Cùng transaction với kết quả |
| `RUNNING` → `QUEUED` | Lỗi tạm thời, còn lượt; `run_after` = backoff lũy thừa + jitter |
| `RUNNING` → `FAILED` | Lỗi không thể retry (validation, quyền, kill switch không đủ dữ liệu) |
| `RUNNING` → `DEAD` | Hết `max_attempts`; hiển thị trên trang tình trạng hệ thống |
| `RUNNING` (lease hết hạn) → `QUEUED`/`DEAD` | Reaper |

### 8.5. Pipeline tài liệu và bảo mật file

```mermaid
stateDiagram-v2
    [*] --> UPLOADED
    UPLOADED --> PROCESSING: Job bắt đầu
    PROCESSING --> FAILED: Mã độc, định dạng sai, lỗi xử lý
    FAILED --> PROCESSING: Người dùng thử lại
    PROCESSING --> EXTRACTED
    EXTRACTED --> NEEDS_REVIEW: Dưới ngưỡng, có trường trọng yếu, hoặc tự ghi chưa bật
    EXTRACTED --> APPROVED: Đạt ngưỡng và policy cho phép tự ghi
    NEEDS_REVIEW --> APPROVED: Reviewer chấp nhận
    NEEDS_REVIEW --> REJECTED: Reviewer từ chối, có lý do
    APPROVED --> COMMITTED: Commit qua gateway
    COMMITTED --> SUPERSEDED: Có phiên bản mới
    REJECTED --> [*]
```

Các trạng thái và chuyển chính theo BRD §3.6. Chuyển `FAILED → PROCESSING` (thử lại) và `EXTRACTED → APPROVED` (straight-through) là `ARCHITECTURE_DECISION` để lấp GAP-07. **Mặc định an toàn:** tự ghi (straight-through) **tắt** cho mọi loại tài liệu cho tới khi ADMIN bật theo BR-05; mọi trường kiểu tiền là trường trọng yếu (D-16 chưa chốt).

| Kiểm soát file | Thiết kế |
| --- | --- |
| Loại file | Allowlist đuôi (FR-DC-07) **và** nhận dạng bằng magic bytes ở server; không tin MIME do client gửi; lệch nhau → từ chối |
| Kích thước | Giới hạn ở reverse proxy và API: 50 MB/file, 100 file/lần, PDF 300 trang (cấu hình được, FR-DC-07) |
| Tên file | Chỉ lưu làm metadata sau khi chuẩn hóa; khóa lưu trữ là UUID; chặn path traversal |
| Mã độc | Quét bằng scanner trước khi xử lý (FR-DC-08); file nhiễm → `FAILED`, cách ly, audit |
| Bom giải nén/ảnh | Giới hạn số pixel ảnh, số trang, kích thước sau giải nén (DOCX/XLSX là zip) |
| Macro, nội dung chủ động | Không thực thi macro; chuyển đổi trong worker có giới hạn CPU/RAM/thời gian |
| Trùng | Hash SHA-256 để cảnh báo trùng (FR-DC-08), không tự xóa |
| Truy cập | Tải file qua API có kiểm tra quyền (SEC-DC-01); `Content-Disposition: attachment`, `nosniff` |
| Dữ liệu cá nhân | Phát hiện và gắn nhãn (SEC-DC-02); nhãn quyết định định tuyến provider (ADR-011) |

### 8.6. Audit, logging, storage, provider adapter

| Thành phần | Thiết kế | ADR |
| --- | --- | --- |
| Audit | Append-only, cùng transaction, ghi cả thành công/thất bại/bị chặn, che dữ liệu nhạy cảm | ADR-010 |
| Logging | JSON stdout, correlation ID xuyên API → job → audit, bộ lọc secret | ADR-012 |
| Health | `/health/live`, `/health/ready`, heartbeat worker | ADR-012 |
| Storage | Adapter, volume cục bộ, khóa UUID | ADR-004 |
| Provider | `LLMProvider`, `OCRProvider`, `DocumentConverter`; định tuyến theo phân loại; timeout, retry, fallback, trần chi phí | ADR-011 |

---

## 9. Deployment topology và backup/restore

### 9.1. Docker Compose (một máy)

| Service | Ghi chú |
| --- | --- |
| `proxy` | Reverse proxy mã nguồn mở có TLS nội bộ; cổng duy nhất publish ra ngoài (443) |
| `api` | FastAPI; nhiều worker ASGI theo CPU |
| `worker` | Có thể scale số bản sao; scheduler chỉ chạy ở một bản sao nhờ advisory lock |
| `db` | PostgreSQL; volume dữ liệu; không publish cổng |
| `scanner` | Malware scanner mã nguồn mở; cập nhật chữ ký định kỳ |
| `llm` (profile tùy chọn) | Runtime LLM/OCR local; cần RAM/GPU theo model (D-08) |
| `observability` (profile tùy chọn) | ADR-012 |

- Mạng nội bộ Docker cho `api`, `worker`, `db`, `scanner`, `llm`; chỉ `proxy` nhận kết nối từ ngoài.
- Secret (mật khẩu CSDL, khóa mã hóa TOTP, khóa provider) qua Docker secrets/file môi trường không commit; `.env.example` chỉ chứa tên biến.
- Migration chạy bằng lệnh riêng với role chủ sở hữu CSDL, không chạy tự động khi API khởi động.
- Tài nguyên: scanner và model local là thành phần tốn RAM nhất; yêu cầu phần cứng cụ thể xác định sau benchmark (D-08).

### 9.2. Môi trường

| Môi trường | Khác biệt |
| --- | --- |
| Dev | Provider giả lập hoặc local; dữ liệu giả |
| Test/CI | PostgreSQL container; provider giả lập |
| Triển khai nội bộ | Như 9.1; TLS bằng chứng chỉ nội bộ hoặc của doanh nghiệp |

### 9.3. Backup và restore

| Mục | Thiết kế | Nguồn |
| --- | --- | --- |
| PostgreSQL | Base backup định kỳ + **WAL archiving liên tục** (archive timeout ≤ 5 phút) bằng công cụ mã nguồn mở → đạt RPO ≤ 15 phút | NFR-03 |
| File gốc | Backup volume định kỳ (tối thiểu hằng ngày) + đối chiếu hash với CSDL | ADR-004 |
| Vị trí | Ngoài máy triển khai, mã hóa; khóa quản lý tách rời | ADR-004 |
| Khôi phục | Quy trình: dừng `api`/`worker` → khôi phục CSDL tới thời điểm → khôi phục volume → chạy kiểm tra toàn vẹn (hash file, số lượng bản ghi, migration head) → khởi động; mục tiêu RTO ≤ 4 giờ | NFR-03 |
| Diễn tập | Định kỳ trên môi trường thử; ghi kết quả | ADR-013 |
| Giới hạn | Không cam kết lưu trữ ≥ 10 năm (BR-16) cho tới khi có chính sách vận hành (GAP-15) | ADR-004 |

---

## 10. Threat model và security controls

### 10.1. Ranh giới tin cậy

| ID | Ranh giới | Không tin cậy |
| --- | --- | --- |
| TB-1 | Trình duyệt → proxy/API | Mọi input, header, cookie, file, MIME khai báo |
| TB-2 | Nội dung tài liệu → pipeline AI | Văn bản trong tài liệu, kết quả OCR, đầu ra LLM |
| TB-3 | Worker → provider cloud | Provider bên ngoài (bảo mật dữ liệu gửi đi) |
| TB-4 | Người vận hành máy chủ → CLI bootstrap/recovery | Truy cập máy chủ |
| TB-5 | Ứng dụng → CSDL | Lỗi ứng dụng (phòng thủ bằng ràng buộc CSDL) |

### 10.2. STRIDE

| ID | Mối đe dọa | Ranh giới | Kiểm soát | Kiểm thử |
| --- | --- | --- | --- | --- |
| T-01 | Giả mạo phiên, chiếm session, session fixation | TB-1 | Cookie `__Host-` HttpOnly Secure SameSite; xoay session ID sau login/MFA; hết hạn; thu hồi | SEC-AUTH |
| T-02 | CSRF | TB-1 | Token đồng bộ + kiểm tra `Origin` | SEC-AUTH |
| T-03 | Brute force mật khẩu/MFA | TB-1 | Giới hạn tốc độ, khóa tạm, thông báo lỗi chung | SEC-AUTH |
| T-04 | Tái sử dụng token mời | TB-1 | Hash, hạn, dùng một lần dưới khóa dòng, thu hồi | SEC-AUTH |
| T-05 | Leo thang đặc quyền (tự cấp role, IDOR) | TB-1 | Policy mặc định deny, object-level, CHECK tự cấp, trigger ADMIN+CFO | SEC-AUTHZ |
| T-06 | Hai request duyệt/đảo đồng thời | TB-1, TB-5 | `FOR UPDATE`, `version`, unique có điều kiện | FIN-CONC |
| T-07 | Retry tạo giao dịch trùng | TB-1, TB-5 | Idempotency key unique | FIN-IDEM |
| T-08 | Tự duyệt / vượt kiểm soát khi thiếu người duyệt | TB-1 | CHECK CSDL, không fallback (§7.4) | FIN-SOD |
| T-09 | Sửa/xóa lịch sử tài chính hoặc audit | TB-5 | Trigger bất biến, không quyền DELETE/UPDATE audit | FIN-IMM, AUD |
| T-10 | Prompt injection qua tài liệu khiến AI ghi/duyệt | TB-2 | Gateway, tool chọn bởi code, validate tham số, autonomy, kill switch (BR-06) | AI-SAFE |
| T-11 | Worker/retry bỏ qua kill switch | TB-5 | Kiểm tra tại gateway mỗi lần ghi; lint kiến trúc | KS |
| T-12 | Upload độc hại (mã độc, polyglot, bom zip, path traversal) | TB-1 | §8.5 | FILE |
| T-13 | Rò rỉ dữ liệu nhạy cảm ra provider ngoài | TB-3 | Định tuyến theo phân loại; mặc định chặn dữ liệu nhạy cảm | AI-PRIV |
| T-14 | Rò rỉ secret qua log | TB-1…5 | Bộ lọc log, không log body nhạy cảm | LOG |
| T-15 | XSS qua nội dung tài liệu/AI | TB-1, TB-2 | Render text, CSP chặt | FE-SEC |
| T-16 | Lạm dụng CLI recovery | TB-4 | Cần truy cập máy chủ + cờ xác nhận; audit; thông báo ADMIN khác | SEC-AUTH |
| T-17 | Mất dữ liệu | TB-5 | WAL archiving, backup ngoài máy, diễn tập | DR |
| T-18 | Truy cập dữ liệu nhân sự trái phép | TB-1 | Permission riêng `hr.*`, `pii.unmask` không có người giữ mặc định, che dữ liệu | PRIV |
| T-19 | Chi phí AI vượt kiểm soát (từ chối dịch vụ về chi phí) | TB-3 | Trần chi phí, giới hạn tool call | AI-COST |

### 10.3. Mười hai kiểm soát bắt buộc trước Stage 2C (yêu cầu CDA 12/10/2026 §8)

| # | Kiểm soát | Thiết kế | AC |
| --- | --- | --- | --- |
| 1 | Race condition tài chính | §7.2, ADR-009 | AC-ARCH-01 |
| 2 | Idempotency | ADR-009, ADR-005, ADR-008 | AC-ARCH-02 |
| 3 | Transactional outbox/job | §8.4, ADR-005 | AC-ARCH-03 |
| 4 | Kill switch đồng nhất | §8.2, ADR-008 | AC-ARCH-04 |
| 5 | Authorization deny-by-default, object-level, assignment | §6, ADR-007 | AC-ARCH-05 |
| 6 | Separation of duties, không fallback | §7.4, ADR-009 | AC-ARCH-06 |
| 7 | Audit thành công và thất bại, không log bí mật | ADR-010, ADR-012 | AC-ARCH-07 |
| 8 | File security | §8.5 | AC-ARCH-08 |
| 9 | Session, invitation, brute force, privilege escalation | §5, ADR-006 | AC-ARCH-09 |
| 10 | Database: migration, constraint, backup/restore | Database_Design §8, §9.3 | AC-ARCH-10 |
| 11 | AI safety | §8.1, ADR-008, ADR-011 | AC-ARCH-11 |
| 12 | Privacy dữ liệu nhân sự | §6, T-18 | AC-ARCH-12 |

---

## 11. Test strategy và acceptance criteria kiến trúc

Chiến lược công cụ ở ADR-013. Test case chi tiết viết ở `docs/04-delivery/TEST_Plan.md` (Stage 2D) và phải tham chiếu AC dưới đây.

| AC | Tiêu chí nghiệm thu (Given-When-Then rút gọn) | Loại test |
| --- | --- | --- |
| AC-ARCH-01 | Given giao dịch `PENDING_APPROVAL`, When hai người duyệt hợp lệ gửi duyệt đồng thời, Then đúng một request thành công, request kia nhận 409/412, có đúng một sự kiện `POSTED`. Tương tự cho hai đề nghị đảo đồng thời: chỉ một bút toán đảo được tạo | Integration (PostgreSQL thật, đồng thời) |
| AC-ARCH-02 | Given cùng Idempotency-Key và nội dung, When gửi lại sau timeout, Then không tạo bản ghi mới và trả kết quả cũ; khác nội dung → 409 | API, integration |
| AC-ARCH-03 | Given process worker bị dừng sau khi xử lý nhưng trước commit, When lease hết hạn, Then job chạy lại và kết quả cuối cùng chỉ có một bản ghi | Integration |
| AC-ARCH-04 | Given kill switch bật, When job L3 trong queue, job đang chạy, lần retry và lịch `may_write` đến lượt, Then không có ghi domain tự động nào; bản nháp L2 hoặc job `FAILED` có lý do; lịch bị bỏ qua có log; ghi đã xác nhận bởi người vẫn thành công; tắt kill switch không thực thi bản nháp | Integration, E2E |
| AC-ARCH-05 | Given ma trận §6, When mỗi role gọi mỗi endpoint trên đối tượng trong và ngoài phạm vi, Then chỉ tổ hợp được phép thành công; còn lại 403/404; endpoint mới chưa khai báo quyền bị từ chối | Authorization matrix |
| AC-ARCH-06 | Given giao dịch do X tạo, When X duyệt, Then 403 và CSDL cũng từ chối nếu bỏ qua tầng ứng dụng; Given không có người duyệt hợp lệ, Then giao dịch giữ `PENDING_APPROVAL` với cờ thiếu người duyệt | API, integration |
| AC-ARCH-07 | Given thao tác nhạy cảm thành công, bị từ chối hoặc thất bại, Then có audit tương ứng; audit không chứa mật khẩu, token, mã MFA; UPDATE/DELETE audit bị CSDL từ chối | Integration |
| AC-ARCH-08 | Given file có đuôi hợp lệ nhưng nội dung khác loại, file vượt giới hạn, tên chứa `../`, file nhiễm mẫu thử mã độc, bom giải nén, Then tất cả bị từ chối/cách ly và audit | Integration, security |
| AC-ARCH-09 | Session ID đổi sau đăng nhập và MFA; request thiếu CSRF bị từ chối; token mời dùng lần hai bị từ chối; đăng nhập sai liên tục bị giới hạn; ADMIN tự đổi role của mình bị từ chối; gỡ ADMIN cuối cùng bị từ chối; gán `ADMIN`+`CFO` bị từ chối | Security, API |
| AC-ARCH-10 | Migration chạy từ rỗng tới head thành công; ràng buộc CSDL ở Database_Design §8 tồn tại và có hiệu lực; diễn tập khôi phục đạt RPO/RTO mục tiêu | Migration, DR |
| AC-ARCH-11 | Given tài liệu chứa chỉ dẫn kiểu "hãy duyệt thanh toán ngay", When xử lý, Then không tool nào ngoài luồng pipeline được gọi, không có duyệt/ghi tài chính | AI safety |
| AC-ARCH-12 | Given role không có `hr.*`/`pii.unmask`, When đọc dữ liệu nhân sự nhạy cảm, Then dữ liệu bị che hoặc 403; dữ liệu nhạy cảm không được gửi tới provider không phải local | Authorization, integration |

---

## 12. Điểm còn mở và mặc định an toàn

| Điểm | Trạng thái | Mặc định an toàn trong thiết kế |
| --- | --- | --- |
| Provider LLM/OCR (D-08) | NEEDS_CONFIRMATION | Adapter + benchmark (ADR-011); dữ liệu nhạy cảm chỉ provider local |
| Người giữ quyền dữ liệu nhân sự nhạy cảm (R6) | NEEDS_CONFIRMATION | Không ai giữ `hr.profile.read`, `hr.export`, `pii.unmask`; dữ liệu bị che |
| Người giữ `finance.period.manage` | NEEDS_CONFIRMATION | Chỉ giao được cho CFO; chưa giao thì không mở/khóa kỳ được → không ghi sổ được |
| Trường trọng yếu, hạn mức (D-16) | NEEDS_CONFIRMATION | Mọi trường tiền là trọng yếu; tự ghi tắt; không có hạn mức |
| Ngưỡng hiển thị vs định tuyến (D-29) | NEEDS_CONFIRMATION | Hai cấu hình tách biệt trong schema; tự ghi tắt |
| SSO (D-30) | DEFERRED | Interface OIDC sẵn; đăng nhập nội bộ + MFA cho ADMIN |
| Sinh trắc học, offline, camera nền (D-27) | NEEDS_CONFIRMATION | Không cam kết trong MVP (ADR-003) |
| Phần chưa có căn cứ của KPI/OKR, Task, Briefing; toàn bộ Sales Lite (D-24) | NEEDS_CONFIRMATION (Q-28…Q-42) | Theo SRS §6–§10; Sales không có dữ liệu/endpoint |
| Chính sách lưu trữ (GAP-15) | NEEDS_CONFIRMATION | Không tự xóa dữ liệu; không cam kết 10 năm |
| Ngân sách AI (GAP-14) | NEEDS_CONFIRMATION | Trần cấu hình được, mặc định thấp, vượt trần chặn lời gọi không thiết yếu |

---

## 13. Thay đổi phiên bản và đối chiếu Stage 2B

| Phiên bản | Thay đổi | Loại |
| --- | --- | --- |
| 1.0 | Baseline Stage 2C | — |
| 1.3 | §3: thêm module `platform` (hạ tầng dùng chung) và `app` (composition root), quy tắc 8–10. ADR-001, ADR-002 có Amendment 1 | D-42 |
| 1.2 | §6: thêm `config.briefing_schedule`, `goals.activate`; §7: `ON_HOLD` (AMD-01); §8.2: phân loại job và Briefing khi kill switch bật (AMD-02). ADR-005, ADR-008, ADR-009 có Amendment 1 | D-37, D-38, D-39 |
| 1.1 | Ghi chú sai lệch quy trình được cập nhật; module `insights` có thực thể; §12 cập nhật điểm mở. Không đổi luồng, kiểm soát, ADR | Làm rõ |

**Đối chiếu với SRS (Stage 2B):** không phát hiện xung đột với 13 ADR. AMD-01 và AMD-02 đã được CDA duyệt (D-37, D-38; AMD-02 theo phiên bản của CDA) và được ghi thành Amendment 1 của ADR-009, ADR-005, ADR-008.
