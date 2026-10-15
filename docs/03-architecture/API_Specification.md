# AI-EOS — API Specification (Stage 2C)

> Phiên bản: 1.4 (15/10/2026, T-007) · Ngày: 12/10/2026 · Trạng thái: **Thiết kế — chưa triển khai** · Thay đổi: §11
> Trạng thái endpoint: mục 1.10. Từ 15/10/2026 (D-52) endpoint có code và test xanh trong CI ghi `IMPLEMENTED` (hiện: API-SYS-01, API-SYS-02, API-AUTH-01, API-AUTH-06, API-AUTH-07); còn lại `DESIGNED`. OpenAPI sinh từ code (ADR-002) và được contract test đối chiếu với tài liệu này (ADR-013).
> Từ 1.1, endpoint đối chiếu với [SRS](../02-requirements/SRS.md) (Stage 2B). Sales Pipeline Lite vẫn `SKELETON` (Q-38).
> Liên quan: [Architecture.md](Architecture.md), [Database_Design.md](Database_Design.md), ADR-006…ADR-011.

## 1. Quy ước chung

### 1.1. Base URL, định dạng
- Base: `https://<host>/api/v1`. JSON UTF-8; upload dùng `multipart/form-data`.
- Thời gian ISO 8601 UTC; ngày `YYYY-MM-DD`; tiền là **chuỗi thập phân** (vd. `"1250000.00"`) kèm `currency`, tránh sai số số thực.
- Tên trường `snake_case`.

### 1.2. Xác thực
- Cookie session `__Host-aieos_session` (HttpOnly, Secure, SameSite=Lax) do `POST /auth/login` và `POST /auth/mfa/verify` cấp (ADR-006).
- Mọi endpoint yêu cầu session hợp lệ và (với ADMIN) đã xác minh MFA, **trừ**: `POST /auth/login`, `POST /auth/mfa/verify` (session chờ MFA), `POST /auth/invitations/accept`, `GET /health/live`, `GET /health/ready`.
- **Step-up:** endpoint đánh dấu `STEP-UP` yêu cầu `POST /auth/reauth` trong khoảng thời gian cấu hình; nếu không → `401` mã `REAUTH_REQUIRED`.

### 1.3. CSRF
Mọi request `POST`/`PUT`/`PATCH`/`DELETE` phải có header `X-CSRF-Token` khớp session và header `Origin` khớp host; sai → `403 CSRF_FAILED`. Token lấy từ `GET /auth/me`.

### 1.4. Phân quyền
Mỗi endpoint ghi permission theo Architecture §6. Không đủ quyền → `403 FORBIDDEN`; đối tượng ngoài phạm vi đọc → `404 NOT_FOUND` (không lộ sự tồn tại). Mọi lần từ chối với thao tác nhạy cảm được audit. Trong code, mọi route khai báo quyền (`PUBLIC`, `AUTHENTICATED` hoặc mã permission); route không khai báo bị từ chối `403 FORBIDDEN` (T-108).

### 1.5. Lỗi
Định dạng `application/problem+json`:
```json
{
  "type": "https://aieos.local/errors/VERSION_CONFLICT",
  "title": "Version conflict",
  "status": 412,
  "code": "VERSION_CONFLICT",
  "detail": "Giao dịch đã thay đổi",
  "correlation_id": "c0a8…",
  "errors": [{ "field": "amount", "message": "..." }]
}
```
Không trả stack trace, câu SQL, đường dẫn file hay dữ liệu nhạy cảm.

### 1.6. Idempotency
Endpoint đánh dấu `IDEMPOTENT` **bắt buộc** header `Idempotency-Key` (chuỗi ngẫu nhiên do client sinh, ≤ 128 ký tự). Cùng key + cùng nội dung → trả lại kết quả cũ (cùng status); cùng key + khác nội dung → `409 IDEMPOTENCY_KEY_REUSED`. Thiếu key → `400 IDEMPOTENCY_KEY_REQUIRED`.

### 1.7. Đồng thời
Tài nguyên có `version` trả header `ETag: "<version>"`. Endpoint đánh dấu `IF-MATCH` bắt buộc `If-Match`; lệch → `412 VERSION_CONFLICT`; thiếu → `428 PRECONDITION_REQUIRED`.

### 1.8. Phân trang, lọc
Cursor: `?limit=` (mặc định 20, tối đa 100) `&cursor=`; response `{ "items": [...], "next_cursor": "..." }`.

### 1.9. Giới hạn tốc độ
Đăng nhập, MFA, chấp nhận lời mời, reauth: giới hạn theo IP và tài khoản → `429 RATE_LIMITED` kèm `Retry-After`. Upload và chat AI có giới hạn theo người dùng.

### 1.10. Trạng thái triển khai
| Giá trị | Ý nghĩa |
| --- | --- |
| `DESIGNED` | Đã thiết kế ở 2C, chưa có code |
| `IMPLEMENTED` | Có code và test chạy xanh trong CI (D-52). Hiện có: API-SYS-01, API-SYS-02 (`/api/v1/health/live`, `/api/v1/health/ready`; T-006, run `38544809935`); API-AUTH-01, API-AUTH-06 (trả `204`), API-AUTH-07 (T-102, run `38686690047`); API-NOT-01, API-NOT-02 (T-010, run `38696839691`); API-AUTH-02, API-AUTH-03, API-AUTH-04 (T-103, run `38700993783`); API-AUTH-05, API-AUTH-09 (T-104, run `38705903816`); API-ADM-01, API-ADM-04…09 (T-109, run `38708289449`); API-ADM-02, API-ADM-03, API-AUTH-08 (T-105, run `38710976904`); API-ORG-01, API-ORG-02 (T-201, run `38737949724`); API-WORK-01, API-WORK-03, API-WORK-04, API-WORK-05 (T-505, run `38752643215`) |
| `SKELETON` | Chỉ khung; chi tiết chờ 2B (D-24) |
| `DEFERRED` | Ngoài MVP |

---

## 2. Authentication — `identity`

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Status | Req |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-AUTH-01 | POST | `/auth/login` | Công khai | rate limit | Email + mật khẩu → session (chờ MFA nếu bắt buộc). Lỗi chung `401 INVALID_CREDENTIALS` | IMPLEMENTED | D-22, ADR-006 |
| API-AUTH-02 | POST | `/auth/mfa/verify` | Session chờ MFA | rate limit | Mã TOTP hoặc mã khôi phục → xoay session | DESIGNED | ADR-006 |
| API-AUTH-03 | POST | `/auth/mfa/enroll` | Đã đăng nhập | — | Tạo secret TOTP tạm, trả URI cấu hình | DESIGNED | ADR-006 |
| API-AUTH-04 | POST | `/auth/mfa/enroll/confirm` | Đã đăng nhập | — | Xác nhận mã, bật MFA, trả mã khôi phục một lần | DESIGNED | ADR-006 |
| API-AUTH-05 | POST | `/auth/reauth` | Đã đăng nhập | rate limit | Xác thực lại (mật khẩu + MFA nếu có) cho thao tác STEP-UP | DESIGNED | A3 |
| API-AUTH-06 | POST | `/auth/logout` | Đã đăng nhập | — | Thu hồi session hiện tại; `204` | IMPLEMENTED | ADR-006 |
| API-AUTH-07 | GET | `/auth/me` | Đã đăng nhập | — | Thông tin người dùng, role, permission hiệu lực, CSRF token | IMPLEMENTED | UX-08, UX-09 |
| API-AUTH-08 | POST | `/auth/invitations/accept` | Công khai (token) | rate limit | Token mời + mật khẩu mới → kích hoạt. Token sai/hết hạn/đã dùng → `400 INVITATION_INVALID` (không phân biệt lý do) | DESIGNED | A1 |
| API-AUTH-09 | POST | `/auth/password` | Đã đăng nhập | STEP-UP | Đổi mật khẩu; thu hồi các session khác | DESIGNED | ADR-006 |

Không có endpoint đăng ký công khai. Bootstrap và khôi phục ADMIN chỉ qua CLI (A2, A6).

**API-AUTH-03** (T-103) chỉ tài khoản bắt buộc MFA (role `ADMIN`; MFA cho role khác DEFERRED — D-30), session chờ MFA được phép → `200 { "secret": "<base32>", "otpauth_uri": "otpauth://totp/..." }`; gọi lại thay secret tạm; đã bật MFA → `409 INVALID_STATE` (đặt lại MFA qua `recover-admin`); role khác → `403 FORBIDDEN`.
**API-AUTH-04** (T-103) `{ "code": "123456" }` → `200 { "recovery_codes": [10 mã] }` (chỉ trả một lần) + cookie session mới (đã xác minh MFA); mã sai → `401 INVALID_CREDENTIALS`; không có secret tạm → `409 INVALID_STATE`; rate limit.
**API-AUTH-02** (T-103) `{ "code": "<TOTP 6 số | mã khôi phục>" }` → `204` + cookie session mới; mã sai/đã dùng → `401 INVALID_CREDENTIALS`; chưa đăng ký MFA hoặc session đã xác minh → `409 INVALID_STATE`; rate limit. Sau khi xoay session, lấy `csrf_token` mới qua `GET /auth/me`.
**API-AUTH-05** (T-104) session đủ MFA; `{ "password": "...", "code": "<TOTP | mã khôi phục, bắt buộc khi đã bật MFA>" }` → `204`; đặt `reauth_at` của **session hiện tại** — thao tác `STEP-UP` hợp lệ trong `AIEOS_REAUTH_MINUTES`; sai mật khẩu hoặc mã → `401 INVALID_CREDENTIALS` (không phân biệt); rate limit.
**API-AUTH-09** (T-104, `STEP-UP`) `{ "new_password": "..." }` → `204`; độ dài theo `AIEOS_PASSWORD_MIN_LENGTH` (tối đa 1024) → sai `422 VALIDATION_ERROR`; thu hồi mọi session **khác** của tài khoản (session hiện tại giữ); chưa reauth → `401 REAUTH_REQUIRED`.

**API-AUTH-01** request `{ "email": "...", "password": "..." }` → `200 { "mfa_required": true|false, "mfa_enrolled": true|false, "csrf_token": "..." }` + cookie (T-103 bổ sung `mfa_enrolled` — frontend chọn màn đăng ký hay nhập mã — và `csrf_token` của session mới, vì session chờ MFA không gọi được `GET /auth/me` mà vẫn phải gửi `X-CSRF-Token` cho API MFA; thay đổi bổ sung, tương thích); `401 INVALID_CREDENTIALS`; `429 RATE_LIMITED`; `423 ACCOUNT_LOCKED` chỉ trả **sau khi** mật khẩu đúng (tránh dò tài khoản).

---

## 3. Quản trị người dùng và quyền — `identity`, `access`

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-ADM-01 | GET | `/admin/users` | `user.manage` | — | Danh sách tài khoản, role, trạng thái | A1 |
| API-ADM-02 | POST | `/admin/users` | `user.manage` | STEP-UP, IDEMPOTENT | Tạo tài khoản `INVITED` + lời mời; trả link mời **một lần** | A1 |
| API-ADM-03 | POST | `/admin/users/{id}/invitations` | `user.manage` | STEP-UP | Cấp lời mời mới, thu hồi lời mời cũ | A1 |
| API-ADM-04 | PATCH | `/admin/users/{id}` | `user.manage` | STEP-UP, IF-MATCH | Khóa/mở/vô hiệu tài khoản; thu hồi session. Vô hiệu ADMIN cuối cùng → `409 LAST_ADMIN` | A4 |
| API-ADM-05 | PUT | `/admin/users/{id}/roles` | `role.assign` | STEP-UP, IF-MATCH | Thay tập role, `reason` bắt buộc. Actor = target → `403 SELF_ROLE_CHANGE`; `ADMIN`+`CFO` → `422 ROLE_COMBINATION_FORBIDDEN`; gỡ ADMIN cuối → `409 LAST_ADMIN`; thu hồi session đích | A3, A5, R7 |
| API-ADM-06 | GET | `/admin/assignments` | `assignment.manage` | — | Lọc theo user/permission | R1, R5 |
| API-ADM-07 | POST | `/admin/assignments` | `assignment.manage` | STEP-UP, IDEMPOTENT | Giao permission có phạm vi; role không đủ điều kiện → `422 ASSIGNMENT_NOT_ELIGIBLE`; tự giao → `403` | R1, R5, CDA-F1 |
| API-ADM-08 | DELETE | `/admin/assignments/{id}` | `assignment.manage` | STEP-UP | Thu hồi (đánh dấu `revoked_at`, không xóa) | R5 |
| API-ADM-09 | GET | `/admin/roles` | `user.manage` | — | Role, permission nền và permission đủ điều kiện (chỉ đọc; seed qua migration) | R1 |
| API-ADM-10 | GET | `/admin/audit-events` | `audit.read.admin` | — | Audit SECURITY/ADMIN đầy đủ; BUSINESS/AI chỉ siêu dữ liệu | R3, ADR-010 |
| API-ADM-11 | GET | `/admin/system-health` | `system.health.read` | — | Trạng thái worker, queue, job DEAD, giao dịch thiếu người duyệt, kill switch (số tác vụ chuyển nháp, job bị chặn, lịch bị bỏ qua), cảnh báo "chưa có người quản lý kỳ", "không có kỳ mở", "hàng chờ review không có người" | UX §4.1, ADR-012, SRS-FIN-12 |

**API-ADM-05** request `{ "roles": ["MANAGER"], "reason": "..." }` → `200` user mới, `ETag`; lỗi: `403 SELF_ROLE_CHANGE`, `409 LAST_ADMIN`, `412 VERSION_CONFLICT`, `422 ROLE_COMBINATION_FORBIDDEN`, `401 REAUTH_REQUIRED`.

Chi tiết T-105:
- **API-ADM-02** `{ "email", "display_name", "roles": [...], "reason" }` + `Idempotency-Key` → `201 { "user": {…}, "invitation": { "link": "/invite#token=…", "expires_at" } }`, `Cache-Control: no-store`. Link chỉ trả **một lần**: gọi lại cùng khóa + cùng nội dung → `201` cùng `user`, `invitation: null` (token chỉ lưu hash — dùng API-ADM-03 để cấp lại). Có `roles` thì cần thêm `role.assign`. Email đã có → `422` (trường `email`); `ADMIN`+`CFO` → `422 ROLE_COMBINATION_FORBIDDEN`. Token đặt trong fragment (`#`) để không tới máy chủ/log khi mở trang; trang `/invite` thuộc frontend (T-111). Hạn: `AIEOS_INVITE_TTL_HOURS`.
- **API-ADM-03** → `201 { "link", "expires_at" }`; thu hồi lời mời còn hiệu lực; tài khoản không còn `INVITED` → `409 INVALID_STATE`. Chưa có endpoint hủy lời mời riêng (SRS-IAM-02 "Admin hủy") — lời mời chỉ bị thu hồi khi cấp lại; CDA 15/10/2026 tạm giữ, `[CẦN XÁC NHẬN]`.
- **API-AUTH-08** (công khai, miễn CSRF token, vẫn kiểm `Origin`) `{ "token", "password" }` → `204` (tài khoản `ACTIVE`; đăng nhập lại qua API-AUTH-01); mật khẩu không đạt `AIEOS_PASSWORD_MIN_LENGTH` → `422` (kiểm trước token); token sai/hết hạn/đã dùng/đã thu hồi → `400 INVITATION_INVALID` cùng nội dung; rate limit theo IP và token.

Chi tiết T-109:
- User (API-ADM-01/04/05): `{ "id", "email", "display_name", "status", "roles": [...], "mfa_enabled", "created_at", "version" }`; `ETag` = `"<version>"` (tăng khi đổi trạng thái hoặc role). API-ADM-01 phân trang cursor §1.8 (mới nhất trước).
- **API-ADM-04** `{ "status": "ACTIVE" | "LOCKED" | "DISABLED", "reason": "..." (tùy chọn) }` → `200` user + `ETag`. Tài khoản `INVITED` → `409 INVALID_STATE` (kích hoạt qua lời mời, T-105); tự đổi trạng thái của mình → `403 FORBIDDEN`; rời `ACTIVE` → thu hồi mọi session; về `ACTIVE` → xóa khóa tạm.
- API-ADM-04/05 thiếu `If-Match` → `428`; lệch → `412`. Role không tồn tại → `422 VALIDATION_ERROR`.
- **API-ADM-06** `?user_id=&permission=&limit=&cursor=` → `{ "items": [assignment], "next_cursor" }`; gồm cả assignment đã thu hồi/hết hạn. Assignment: `{ "id", "user_id", "permission", "scope_type", "scope_id", "valid_from", "valid_to", "granted_by", "reason", "created_at", "revoked_at", "revoked_by" }`.
- **API-ADM-07** `{ "user_id", "permission", "scope_type", "scope_id", "valid_to", "reason" }` + `Idempotency-Key` → `201` assignment; phạm vi sai (vd. `ORG_UNIT` thiếu `scope_id`) → `422 VALIDATION_ERROR` (trường `scope_id`). Giao/thu hồi → thu hồi mọi session của tài khoản đích (SRS-IAM-11).
- **API-ADM-08** → `204` (đã thu hồi trước đó → `204`, không đổi gì); không tồn tại → `404`; tự thu hồi của mình → `403 SELF_ROLE_CHANGE`.
- **API-ADM-09** → `200 [{ "code", "base": [...], "eligible": [...] }]`.
- Lỗi nghiệp vụ trên các API ghi ở đây được audit `FAILED`; thiếu quyền → audit `DENIED` (SRS-AUD-01).

---

## 4. AI control, hành động và trợ lý — `ai`, `gateway`

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-AI-01 | GET | `/admin/ai/kill-switch` | `ai.kill_switch` | — | Trạng thái, người/thời điểm/lý do đổi gần nhất | D-09 |
| API-AI-02 | PUT | `/admin/ai/kill-switch` | `ai.kill_switch` | STEP-UP, IF-MATCH | `{ "enabled": true, "reason": "..." }` | D-09, K1, BR-13 |
| API-AI-03 | GET | `/admin/ai/tools` | `config.autonomy` | — | Tool Registry (chỉ đọc) | FR-DCS-05, BR-09 |
| API-AI-04 | GET | `/admin/ai/autonomy-policies` | `config.autonomy` | — | Danh sách policy | FR-AUT-02 |
| API-AI-05 | PUT | `/admin/ai/autonomy-policies/{id}` | `config.autonomy` | STEP-UP, IF-MATCH | Vượt trần → `422 AUTONOMY_CAP_EXCEEDED` | FR-AUT-02, R8 |
| API-AI-06 | PUT | `/admin/ai/settings/draft-expiry` | `config.draft_expiry` | STEP-UP | `{ "days": 30, "reason": "..." }`; audit | K5 |
| API-AI-07 | GET | `/ai/actions` | đã đăng nhập; lọc theo quyền | — | Bản nháp chờ tôi review, hành động của tôi, feed "AI đã làm" (lọc module, người, mức) | UX-27, FR-AUT-01 |
| API-AI-08 | GET | `/ai/actions/{id}` | reviewer hợp lệ hoặc người khởi tạo | — | Chi tiết, xem trước kết quả | UX-05 |
| API-AI-09 | POST | `/ai/actions/{id}/confirm` | `action.confirm` (không tài chính); tài chính: luồng §6 | IF-MATCH, IDEMPOTENT | Xác nhận bản nháp L2 → thực thi qua gateway | D-09, K4, UX-05 |
| API-AI-10 | POST | `/ai/actions/{id}/reject` | như API-AI-09 | IF-MATCH | Lý do bắt buộc | K4 |
| API-AI-11 | POST | `/ai/actions/{id}/undo` | `action.undo` | IF-MATCH, IDEMPOTENT | Hoàn tác L3 trong hạn; hết hạn → `409 UNDO_WINDOW_EXPIRED`; tài chính → `422` (không có L3 tài chính) | BR-11, FR-AUT-03 |
| API-AI-12 | POST | `/ai/chat` | `ai.use` | rate limit | SSE: sự kiện `step` (bước thật), `token`, `citation`, `done`, `error`; client đóng kết nối = Dừng. Chỉ dùng tool READ trong phạm vi người dùng | UX-02, UX-22, UX-23, UX-24, FR-AIQ-02, BR-14 |
| API-AI-13 | POST | `/ai/feedback` | `ai.use` | — | `{ target_type, target_id, verdict, comment }` | FR-AIQ-04, UX-28 |

Bản nháp của hành động **tài chính** là giao dịch `DRAFT` trong `finance`, xử lý bằng API-FIN (không confirm qua API-AI-09) — bảo đảm cùng quy trình duyệt (F5).

---

## 5. Data capture — `capture`, `org`

### 5.1. Tài liệu

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-DOC-01 | POST | `/documents` | `record.submit` | IDEMPOTENT | Multipart 1–100 file; tùy chọn `document_type_code`, `context` (màn hình hiện tại cho AI đoán đích, U5). Trả `202` với danh sách tài liệu `UPLOADED`. Lỗi: `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_FILE_TYPE` (theo magic bytes), `422 TOO_MANY_FILES` | C3, C4, FR-DC-07, FR-DC-08, FR-DC-09, US-DC-003, UX-04 |
| API-DOC-02 | GET | `/documents` | `data.read` (phạm vi) | — | Lọc trạng thái, loại, người tải | US-DC-003 |
| API-DOC-03 | GET | `/documents/{id}` | `data.read` (SEC-DC-01) | — | Metadata, trạng thái, loại, kết quả quét, cảnh báo trùng | FR-DC-08 |
| API-DOC-04 | GET | `/documents/{id}/file` | `data.read` (SEC-DC-01) | — | Tải file gốc; `Content-Disposition: attachment`, `nosniff`; dữ liệu cá nhân không bị che trong file gốc → cần thêm `pii.unmask` nếu `sensitivity <> NORMAL` | FR-DC-23, SEC-DC-01, SEC-DC-02 |
| API-DOC-05 | GET | `/documents/{id}/pages/{n}` | như API-DOC-04 | — | Ảnh trang để hiển thị vùng nguồn | FR-DC-19 |
| API-DOC-06 | POST | `/documents/{id}/retry` | người tải hoặc reviewer | IDEMPOTENT | `FAILED → PROCESSING` (không áp dụng cho `INFECTED`) | GAP-07 |
| API-DOC-07 | GET | `/documents/{id}/extraction` | reviewer được giao hoặc người tải | — | Trường: giá trị, độ tin cậy, trang, bbox, đoạn gốc, `critical`, lý do không chắc | FR-DC-11, FR-DC-12, UX-16 |

### 5.2. Review

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-REV-01 | GET | `/review-queue` | `extraction.review` (assignment) | — | Hàng chờ được giao, sắp theo ưu tiên; SLA nếu cấu hình | FR-DC-21, US-DC-006 |
| API-REV-02 | PATCH | `/extractions/{id}/fields` | `extraction.review` | IF-MATCH | Sửa giá trị trường; lưu `reviewed_value`, `corrected` | FR-DC-22, FR-LRN-01 |
| API-REV-03 | POST | `/extractions/{id}/approve` | `extraction.review` | IF-MATCH, IDEMPOTENT | Chấp nhận → `APPROVED` → job commit qua gateway. Trường `critical` chưa được đi qua → `422 CRITICAL_FIELDS_NOT_REVIEWED` | FR-DC-16, FR-DC-17, FR-DC-20, BR-03 |
| API-REV-04 | POST | `/extractions/{id}/reject` | `extraction.review` | IF-MATCH | Lý do bắt buộc | FR-DC-22 |
| API-REV-05 | POST | `/extractions/{id}/reassign` | `extraction.review` | IF-MATCH | Chuyển cho người có assignment phù hợp | FR-DC-22 |
| API-REV-06 | POST | `/extractions/{id}/change-type` | `extraction.review` | IF-MATCH | Đổi loại tài liệu → trích xuất lại | FR-DC-22 |
| API-REV-07 | POST | `/documents/{id}/split` · `/documents/merge` | `extraction.review` | IDEMPOTENT | Tách/gộp | FR-DC-10, FR-DC-22 |

### 5.3. Nhập tay, nhập ngôn ngữ tự nhiên, import

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-CAP-01 | GET | `/capture/forms/{entity}` | `record.submit` | — | Định nghĩa form sinh từ schema (trường, kiểu, bắt buộc, quy tắc) | FR-DC-01 |
| API-CAP-02 | POST | `/capture/suggestions` | `record.submit` | rate limit | Gợi ý giá trị, cảnh báo trùng (master data) | FR-DC-02 |
| API-CAP-03 | POST | `/capture/natural-language` | `record.submit`, `ai.use` | IDEMPOTENT | Văn bản (hoặc bản ghi giọng nói đã chuyển văn bản) → **bản ghi dự kiến** để xác nhận; không ghi | FR-DC-03, US-DC-002, C2 |
| API-CAP-04 | POST/GET/PUT | `/capture/drafts` · `/capture/drafts/{id}` | `record.submit` | IF-MATCH | Lưu nháp form | FR-DC-04 |
| API-IMP-01 | POST | `/imports` | `record.submit`; nhân sự: `hr.import` | IDEMPOTENT | File XLSX/CSV + đích → `PREVIEW`, AI đề xuất map cột | FR-DC-18, C5, US-DC-007 |
| API-IMP-02 | GET | `/imports/{id}` | người tạo | — | Bản xem trước, lỗi theo dòng | FR-DC-18 |
| API-IMP-03 | PUT | `/imports/{id}/mapping` | người tạo | IF-MATCH | Sửa map cột | FR-DC-18 |
| API-IMP-04 | POST | `/imports/{id}/commit` | người tạo | IF-MATCH, IDEMPOTENT | Ghi các dòng hợp lệ qua gateway | FR-DC-17, FR-DC-18 |
| API-IMP-05 | GET | `/imports/{id}/errors.csv` | người tạo | — | Xuất file lỗi | FR-DC-18 |

Ghi chính thức bản ghi từ form (C1) đi qua endpoint của module đích (chờ 2B, trừ tài chính ở §6).

### 5.4. Cấu hình loại tài liệu

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-CFG-01 | GET | `/admin/document-types` | `config.document_schema` | — | Loại MVP và Phase 2 (Phase 2 không bật được — D-17) | FR-DCS-02, FR-DCS-03 |
| API-CFG-02 | POST | `/admin/document-types/{code}/schemas` | `config.document_schema` | STEP-UP | Tạo phiên bản schema `DRAFT` | FR-DCS-01, US-DC-008 |
| API-CFG-03 | POST | `/admin/extraction-schemas/{id}/activate` | `config.document_schema` | STEP-UP, IF-MATCH | Kích hoạt | FR-DCS-01 |
| API-CFG-04 | PUT | `/admin/document-types/{code}/auto-commit` | `config.document_schema` | STEP-UP | Bật tự ghi chỉ khi đạt BR-05 (≥ 98% trên ≥ 200 tài liệu) — hệ thống kiểm tra số liệu, không đạt → `422 AUTO_COMMIT_CRITERIA_NOT_MET` | BR-05, FR-LRN-03 |
| API-CFG-05 | PUT/GET | `/admin/review-queues` | `config.document_schema` | STEP-UP | Hàng chờ theo loại/đơn vị | FR-DC-21 |

### 5.5. Tổ chức

| ID | Method | Path | Quyền | Mô tả | Req |
| --- | --- | --- | --- | --- | --- |
| API-ORG-01 | GET | `/org/units` | `org.directory.read` | Cây tổ chức | UC-07 |
| API-ORG-02 | GET | `/org/employees` | `org.directory.read` | Danh bạ (chỉ trường không nhạy cảm) | UC-06, US-DC-007 |
| API-ORG-03 | GET | `/lineage/{resource_type}/{resource_id}` | `data.read` trên đối tượng | Nguồn gốc: bản ghi, người nhập, tài liệu, trang | FR-DF-04, US-DC-011, UX-03 |

**API-ORG-01** (T-201) → `200 { "items": [{ "id", "name", "code", "parent_id", "head_employee_id" }] }` — danh sách phẳng, client dựng cây theo `parent_id`.
**API-ORG-02** (T-201) `?q=&org_unit_id=&limit=&cursor=` → `{ "items": [{ "id", "full_name", "title", "org_unit_id", "org_unit_name", "manager_id", "manager_name" }], "next_cursor" }` — chỉ nhân viên đang làm (`ACTIVE`), sắp theo họ tên; `q` tìm trong họ tên (không phân biệt hoa thường). Chỉ trường danh bạ (SRS-ACC-11).

---

## 6. Finance — `finance`

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Req |
| --- | --- | --- | --- | --- | --- | --- |
| API-FIN-01 | GET | `/finance/periods` | `finance.read` | — | Danh sách kỳ | CDA-F1 |
| API-FIN-02 | POST | `/finance/periods` | `finance.period.manage` | STEP-UP, IDEMPOTENT | Mở kỳ mới; chồng lấn → `409 PERIOD_OVERLAP` | CDA-F1 |
| API-FIN-03 | POST | `/finance/periods/{id}/close` | `finance.period.manage` | STEP-UP, IF-MATCH | Khóa kỳ; còn giao dịch `PENDING_APPROVAL` thuộc kỳ → `409 PERIOD_HAS_PENDING` | CDA-F1 |
| API-FIN-04 | POST | `/finance/transactions` | `finance.submit` | IDEMPOTENT | Tạo `DRAFT` (`REVENUE`/`EXPENSE`/`CASH_BALANCE`, `ORIGINAL` hoặc `ADJUSTMENT` với `adjusts_id`) | SC-04, D-12, CDA-F7 |
| API-FIN-05 | GET | `/finance/transactions` | `finance.read` | — | Lọc loại, trạng thái, kỳ, người tạo | SC-04 |
| API-FIN-06 | GET | `/finance/transactions/{id}` | `finance.read` | — | Chi tiết, `ETag`, liên kết gốc/đảo, `no_eligible_approver` | SC-04 |
| API-FIN-07 | PATCH | `/finance/transactions/{id}` | người tạo | IF-MATCH | Sửa khi `DRAFT`; trạng thái khác → `409 INVALID_STATE` | D-12 |
| API-FIN-08 | POST | `/finance/transactions/{id}/submit` | người tạo | IF-MATCH, IDEMPOTENT | `DRAFT → PENDING_APPROVAL`; tính `no_eligible_approver`. Kỳ của ngày giao dịch không `OPEN` → `409 PERIOD_CLOSED`; không có kỳ → `409 NO_OPEN_PERIOD` | D-12, D-37, SRS-FIN-05, SRS-FIN-06 |
| API-FIN-09 | POST | `/finance/transactions/{id}/cancel` | người tạo | IF-MATCH | `DRAFT`/`PENDING_APPROVAL`/`ON_HOLD` → `CANCELLED`; `reason` bắt buộc khi đang chờ duyệt hoặc tạm giữ | CDA-F3, SRS-FIN-17 |
| API-FIN-10 | POST | `/finance/transactions/{id}/approve` | `finance.approve` (phạm vi) | IF-MATCH, IDEMPOTENT | `→ POSTED`. Lỗi: `403 SELF_APPROVAL_FORBIDDEN`, `409 PERIOD_CLOSED`, `409 INVALID_STATE`, `412 VERSION_CONFLICT` | D-12, D-14, CDA-F6 |
| API-FIN-11 | POST | `/finance/transactions/{id}/reject` | `finance.approve` (phạm vi) | IF-MATCH | `PENDING_APPROVAL`/`ON_HOLD` → `REJECTED`; `reason` bắt buộc; tự từ chối giao dịch của mình → `403` | D-14, BR-15, SRS-FIN-17 |
| API-FIN-12 | POST | `/finance/transactions/{id}/reversals` | `finance.reverse.request` | IDEMPOTENT | Tạo bút toán đảo `DRAFT`, `reason` bắt buộc. Lỗi: `422 CANNOT_REVERSE_REVERSAL`, `409 ALREADY_REVERSED`, `409 NO_OPEN_PERIOD`, `409 INVALID_STATE` | D-13, D-14, CDA-F2, CDA-F4, FR-AUT-03 |
| API-FIN-13 | GET | `/finance/transactions/{id}/history` | `finance.read` | — | Lịch sử trạng thái | FR-DC-05 |
| API-FIN-14 | GET | `/finance/summary` | `finance.read` | — | Doanh thu, chi phí, tiền mặt, runway theo kỳ; mỗi số kèm `as_of` và liên kết lineage | SC-04, FR-DF-03, BR-14 |

**API-FIN-10 — chi tiết**

Request: header `If-Match: "3"`, `Idempotency-Key: …`, `X-CSRF-Token: …`; body `{}` hoặc `{ "comment": "..." }`.

| Status | Code | Khi |
| --- | --- | --- |
| 200 | — | Ghi sổ thành công; body là giao dịch `POSTED`, `ETag` mới |
| 403 | `FORBIDDEN` | Không có `finance.approve` trong phạm vi |
| 403 | `SELF_APPROVAL_FORBIDDEN` | Người duyệt là người tạo/gửi |
| 404 | `NOT_FOUND` | Ngoài phạm vi đọc |
| 409 | `INVALID_STATE` | Không ở `PENDING_APPROVAL` |
| 409 | `PERIOD_CLOSED` | Kỳ ghi sổ không còn `OPEN`; giao dịch được chuyển `ON_HOLD` (SRS-FIN-17) |
| 409 | `IDEMPOTENCY_KEY_REUSED` | Cùng key, khác nội dung |
| 412 | `VERSION_CONFLICT` | `If-Match` lệch (vd. người khác đã duyệt) |
| 428 | `PRECONDITION_REQUIRED` | Thiếu `If-Match` |

**API-FIN-12 — chi tiết**

Request `{ "reason": "Nhập sai số tiền" }` → `201` bút toán đảo `DRAFT` với `kind=REVERSAL`, `reverses_id`, `amount` mang dấu ngược, `period_id` = kỳ gốc nếu `OPEN`, ngược lại kỳ đang mở.

---

## 7. KPI/OKR, công việc, tri thức, Briefing, Sales

Đặc tả theo SRS §6–§10. Phần chưa có căn cứ không có endpoint (Q-28…Q-41).

| ID | Method | Path | Quyền | Đánh dấu | Mô tả | Status | Req |
| --- | --- | --- | --- | --- | --- | --- | --- |
| API-GOAL-01 | GET | `/goals/objectives` | `data.read` (phạm vi) | — | Cây Objective/KR trong phạm vi, kèm baseline, target, giá trị đo gần nhất, trạng thái; tổng hợp check-in team cho MANAGER | DESIGNED | US-DC-005, FR-DCS-02 |
| API-GOAL-02 | GET | `/goals/kpis` | `data.read` | — | KPI và đo lường | DESIGNED | US-DC-005, FR-DCS-02 |
| API-GOAL-03 | POST/PATCH | `/goals/objectives` · `/goals/key-results` · `/goals/kpis` | `record.submit` (phạm vi) | IDEMPOTENT / IF-MATCH | Tạo/sửa bản `DRAFT` thủ công (form C1) | DESIGNED | FR-DC-01 |
| API-GOAL-04 | POST | `/goals/{type}/{id}/activate` | `goals.activate` trong phạm vi (assignment; chưa có quyền nền — D-39, Q-28) | IF-MATCH | `DRAFT → ACTIVE` | DESIGNED | US-DC-005 |
| API-GOAL-05 | POST | `/goals/key-results/{id}/check-ins` | owner KR | IDEMPOTENT | `{ value, confidence, blocker }` | DESIGNED | FR-DC-06 |
| API-GOAL-06 | POST | `/goals/{type}/{id}/measurements` | `record.submit` trên chỉ số | IDEMPOTENT | Ghi giá trị thực tế + kỳ báo cáo (nhập tay; từ tài liệu đi qua gateway) | DESIGNED | US-DC-005 |
| API-WORK-01 | GET | `/work/tasks` | `data.read` | — | Lọc owner, trạng thái, trễ, đơn vị; CEO: tổng quan | DESIGNED | US-DC-004, UC-06 |
| API-WORK-02 | GET | `/work/meetings/{id}` | `data.read` | — | Quyết định, action item | DESIGNED | UC-06 |
| API-WORK-03 | POST | `/work/tasks` | `record.submit`; owner trong phạm vi (SRS-WRK-04) | IDEMPOTENT | Tạo task thủ công | DESIGNED | FR-DC-01 |
| API-WORK-04 | PATCH | `/work/tasks/{id}` | người giao hoặc owner | IF-MATCH | Sửa tiêu đề, hạn, owner (người giao) | DESIGNED | FR-DC-01 |
| API-WORK-05 | POST | `/work/tasks/{id}/complete` · `/reopen` | owner hoặc người giao / người giao | IF-MATCH | `OPEN ↔ DONE` | DESIGNED | US-DC-004 |
| API-WORK-06 | POST | `/work/meetings/{id}/assign` | người chủ trì (người tải biên bản) | IDEMPOTENT | Giao các action item hợp lệ thành task qua gateway; trả danh sách dòng lỗi | DESIGNED | US-DC-004, UC-06 |
| API-KNOW-01 | GET | `/knowledge/items` | `data.read` | — | Tài liệu quy trình/SOP | DESIGNED | FR-DCS-02 |
| API-INS-01 | GET | `/insights/briefing` | `data.read` (CEO: công ty) | — | Bản chụp Briefing mới nhất (kèm `ai_paused` khi kill switch bật) + ô chỉ số tính lại tại thời điểm đọc, mỗi ô có `as_of`, nguồn, `official=false` (D-39); khối "Cần anh quyết", "AI đã làm" | DESIGNED (công thức ô: PROPOSED, Q-37) | UX-12, FR-DF-03 |
| API-INS-02 | PUT | `/insights/tiles` | người dùng | — | Chọn 4 ô chỉ số | DESIGNED | UX-12 |
| API-INS-03 | GET/PUT | `/admin/insights/briefing-schedule` | `config.briefing_schedule` | STEP-UP (PUT), IF-MATCH | Giờ, tần suất, bật/tắt lịch tạo Briefing; `reason` bắt buộc; audit. Không kích hoạt tạo Briefing khi kill switch bật | DESIGNED | D-38, SRS-BRF-13 |
| API-SALES-01 | — | Sales Pipeline Lite | — | — | Chưa có endpoint; chưa thuộc phạm vi triển khai MVP (D-40) | SKELETON | SC-05 |

Chi tiết T-505: task `{ "id", "title", "owner_user_id", "assigned_by", "due_date", "status", "completed_at", "completed_by", "objective_id", "created_via", "created_at", "version", "overdue", "completed_on_time" }`, `ETag` = `"<version>"`. `overdue` = `OPEN` và hạn trước hôm nay (giờ Việt Nam); `completed_on_time` = ngày hoàn thành ≤ hạn (`null` khi chưa xong hoặc không có hạn). API-WORK-01 `?owner_user_id=&status=&overdue=&org_unit_id=&limit=&cursor=` (đơn vị gồm cấp dưới); thấy task khi owner trong phạm vi `data.read` hoặc mình là owner/người giao. API-WORK-03 `{ "title", "owner_user_id", "due_date", "objective_id"? }` → `201`; owner ngoài phạm vi hoặc EMPLOYEE giao cho người khác → `403`. API-WORK-04 `{ "title"?, "due_date"?, "owner_user_id"? }` (đổi owner: chỉ người giao). API-WORK-05 đã ở trạng thái đích → `409 INVALID_STATE`. Task ngoài phạm vi → `404`; thấy nhưng không phải owner/người giao → `403`.

## 8. Thông báo và hệ thống

| ID | Method | Path | Quyền | Mô tả | Req |
| --- | --- | --- | --- | --- | --- |
| API-NOT-01 | GET | `/notifications` | đã đăng nhập | Thông báo in-app của tôi | K6 |
| API-NOT-02 | POST | `/notifications/{id}/read` | chủ thông báo | Đánh dấu đã đọc | K6 |
| API-SYS-01 | GET | `/health/live` | công khai | Tiến trình sống | ADR-012 |
| API-SYS-02 | GET | `/health/ready` | công khai, không lộ chi tiết | CSDL, storage, migration | ADR-012 |

**API-NOT-01** (T-010) phân trang cursor §1.8; mới nhất trước → `200 { "items": [{ "id", "type", "title", "body", "link", "created_at", "read_at" }], "next_cursor": "..." | null }`; `limit`/`cursor` sai → `422 VALIDATION_ERROR`. Chỉ trả thông báo của người đang đăng nhập.
**API-NOT-02** (T-010) → `200` thông báo sau khi đánh dấu (gọi lại không đổi `read_at`); thông báo của người khác hoặc không tồn tại → `404 NOT_FOUND`. `link` luôn là đường dẫn nội bộ (bắt đầu bằng một `/`).

---

## 9. Ngoài MVP

| Chức năng | Trạng thái | Nguồn |
| --- | --- | --- |
| Hóa đơn/biên lai capture, XML hóa đơn | DEFERRED | D-17 |
| Email forwarding, chat bot, Drive sync, API/Webhook nhập liệu (C6–C10) | DEFERRED | D-18, D-02 |
| SSO/OIDC | DEFERRED | D-30 |
| Ủy quyền/hạn mức duyệt tài chính | DEFERRED | F6 |
| Đảo một phần | DEFERRED | D-14 |

---

## 10. Mã lỗi

| Code | HTTP | Ý nghĩa |
| --- | --- | --- |
| `VALIDATION_ERROR` | 422 | Dữ liệu không hợp lệ |
| `UNAUTHENTICATED` | 401 | Chưa đăng nhập/session hết hạn |
| `INVALID_CREDENTIALS` | 401 | Đăng nhập sai (thông báo chung) |
| `REAUTH_REQUIRED` | 401 | Cần step-up |
| `MFA_REQUIRED` | 401 | Cần xác minh MFA |
| `FORBIDDEN` | 403 | Thiếu quyền |
| `CSRF_FAILED` | 403 | CSRF/Origin sai |
| `SELF_APPROVAL_FORBIDDEN` | 403 | Tự duyệt tài chính |
| `SELF_ROLE_CHANGE` | 403 | Tự đổi role |
| `NOT_FOUND` | 404 | Không tồn tại hoặc ngoài phạm vi |
| `METHOD_NOT_ALLOWED` | 405 | Phương thức không hỗ trợ trên đường dẫn (T-007) |
| `INVALID_STATE` | 409 | Chuyển trạng thái không hợp lệ |
| `PERIOD_CLOSED`, `NO_OPEN_PERIOD`, `PERIOD_OVERLAP`, `PERIOD_HAS_PENDING` | 409 | Kỳ báo cáo |
| `ALREADY_REVERSED` | 409 | Đã có bút toán đảo |
| `LAST_ADMIN` | 409 | Gỡ ADMIN cuối cùng |
| `IDEMPOTENCY_KEY_REUSED` | 409 | Cùng key khác nội dung |
| `UNDO_WINDOW_EXPIRED` | 409 | Quá hạn hoàn tác |
| `INVITATION_INVALID` | 400 | Lời mời không dùng được |
| `IDEMPOTENCY_KEY_REQUIRED` | 400 | Thiếu key |
| `VERSION_CONFLICT` | 412 | Lệch version |
| `PRECONDITION_REQUIRED` | 428 | Thiếu `If-Match` |
| `FILE_TOO_LARGE` | 413 | Vượt giới hạn |
| `UNSUPPORTED_FILE_TYPE` | 415 | Định dạng không cho phép |
| `ACCOUNT_LOCKED` | 423 | Khóa tạm |
| `ROLE_COMBINATION_FORBIDDEN`, `ASSIGNMENT_NOT_ELIGIBLE`, `AUTONOMY_CAP_EXCEEDED`, `CANNOT_REVERSE_REVERSAL`, `CRITICAL_FIELDS_NOT_REVIEWED`, `AUTO_COMMIT_CRITERIA_NOT_MET`, `TOO_MANY_FILES` | 422 | Vi phạm quy tắc |
| `RATE_LIMITED` | 429 | Quá tốc độ |
| `INTERNAL_ERROR` | 500 | Lỗi không lường trước; body không có chi tiết nội bộ, chỉ `correlation_id` (SRS-GEN-05, T-007) |
| `AI_UNAVAILABLE` | 503 | Provider lỗi hết fallback; luồng thủ công vẫn chạy (BR-21) |

## 11. Thay đổi phiên bản

| Phiên bản | Thay đổi | Lý do | Loại |
| --- | --- | --- | --- |
| 1.4 | §10 thêm `METHOD_NOT_ALLOWED` (405), `INTERNAL_ERROR` (500) — mã cho lỗi định tuyến và lỗi không lường trước ở hạ tầng HTTP | T-007 | Không phá vỡ |
| 1.3 | §1.10 thêm trạng thái `IMPLEMENTED`; API-SYS-01, API-SYS-02 → `IMPLEMENTED` | D-52 | Không phá vỡ |
| 1.0 | Thiết kế ban đầu | Stage 2C | — |
| 1.2 | AMD-01: API-FIN-08 (bỏ nhãn PROPOSED), API-FIN-09/11 thêm `ON_HOLD`, lỗi `PERIOD_CLOSED` của API-FIN-10 dẫn tới `ON_HOLD`. AMD-02: thêm API-INS-03; API-INS-01 thêm `ai_paused`, `official`. API-GOAL-04 dùng `goals.activate` (D-39). API-SALES-01 ghi D-40 | D-37…D-40 | Thay đổi có kiểm soát |
| 1.1 | Cột Req của API-FIN-01…14 và API-ADM-07: quy tắc tài chính ghi `CDA-F1…CDA-F7` để phân biệt với luồng UX F1–F5 (sửa lỗi truy vết). §7 viết lại: API-GOAL-01/02, API-WORK-01/02, API-KNOW-01, API-INS-01 từ `SKELETON` → `DESIGNED`; thêm API-GOAL-03…06, API-WORK-03…06, API-INS-02. API-FIN-08 thêm lỗi kỳ theo AMD-01 (PROPOSED). API-ADM-11 thêm cảnh báo vận hành. Header tham chiếu SRS | SRS Stage 2B (C-03…C-05) | Làm rõ; API-FIN-08 phụ thuộc AMD-01 |
