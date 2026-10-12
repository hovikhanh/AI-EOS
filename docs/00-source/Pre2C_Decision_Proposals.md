# AI-EOS — Đề xuất quyết định trước Stage 2C

> Phiên bản: 0.2 · Ngày: 12/10/2026 · Trạng thái: **Đã xử lý — lưu làm hồ sơ phân tích phương án**
> **Cập nhật 0.2:** CDA chỉ định các khuyến nghị làm quyết định mặc định (yêu cầu 12/10/2026). ADR-001…013 đã được chuyển sang `docs/03-architecture/decisions/` ở trạng thái CONFIRMED (`ARCHITECTURE_DECISION`). K1–K6, F1–F7, R1–R8, A1–A6 được chốt dưới dạng `CDA_DIRECTIVE` với các điều chỉnh so với khuyến nghị: K5 (30 ngày, ADMIN cấu hình), F6 (không hạn mức; thiết kế sẵn ủy quyền), R5 (quyền tài chính theo assignment, không theo tên role), R6 (permission `hr.*` riêng thay vì thêm role HR), A4/A5 (khuyến nghị ≥ 2 ADMIN, không tạo tài khoản giả). Nội dung ADR mục 7 dưới đây là **bản nháp lịch sử**; bản hiện hành nằm ở thư mục ADR.
> Phạm vi: chuẩn bị phương án cho D-06, D-10, D-14, D-21, D-22 trong [Decision_Log.md](Decision_Log.md). Đây **không** phải tài liệu Stage 2C. Mọi ADR ở mục 7 là dự thảo `PROPOSED`; khi CDA duyệt sẽ được chuyển sang `docs/03-architecture/decisions/` giữ nguyên số.
> Nguồn: `BRD_Review.md` (BRD), `UI_UX_Proposal.md` (UX), Decision_Log 0.3. Toàn văn BRD v1.1 không có trong repository (D-01). A-EMS không được dùng làm nguồn hay bằng chứng (D-04, D-05).

**Nhãn:** `[CDA nêu]` = chủ dự án đã nêu, chưa đủ để đóng quyết định · `[KHUYẾN NGHỊ]` = phương án mặc định do người phân tích đề xuất · `[CẦN XÁC NHẬN]` = không có nguồn.

---

## 1. Tóm tắt

| Quyết định | Trạng thái hiện tại | Đã có | Còn cần CDA |
| --- | --- | --- | --- |
| D-06 Tech stack | NEEDS_CONFIRMATION | `[CDA nêu]` định hướng: backend Python, frontend React, Local/Docker Compose, ưu tiên miễn phí/mã nguồn mở, LLM/OCR qua adapter | Chọn framework và các thành phần (mục 2, 7) |
| D-10 Kill switch | PROPOSED | 8 nguyên tắc `[CDA nêu]` (Decision_Log 3.1.1) | 6 câu hỏi (mục 3) |
| D-14 Bút toán đảo | PROPOSED | 7 nguyên tắc `[CDA nêu]` (Decision_Log 3.2.2) | 7 câu hỏi (mục 4) |
| D-21 Ma trận vai trò | PROPOSED | 5 role nền tảng, Reviewer là assignment `[CDA nêu]` | 7 câu hỏi (mục 5) |
| D-22 Gán role | PROPOSED | 5 nguyên tắc bảo mật `[CDA nêu]` (Decision_Log 3.3.1) | 6 câu hỏi (mục 6) |

---

## 2. D-06 — Đánh giá công nghệ

Tiêu chí chung: chi phí (bản quyền, tài nguyên) · chạy Local/Docker Compose · bảo mật · kiểm thử · bảo trì · mở rộng · phù hợp yêu cầu AI-EOS. Phần dưới chỉ so sánh; quyết định viết ở ADR mục 7.

### 2.1. Kiểu kiến trúc (ảnh hưởng mọi lựa chọn khác)

| Tiêu chí | A. Modular monolith + worker `[KHUYẾN NGHỊ]` | B. Microservices |
| --- | --- | --- |
| Toàn vẹn giao dịch tài chính (D-14) | Một CSDL, transaction ACID cho chuyển trạng thái + audit + outbox | Cần saga/outbox liên service; khó bảo đảm "đảo một lần" |
| Cổng ghi duy nhất, kill switch (D-10, D-26) | Một Tool Registry trong cùng process/CSDL | Mỗi service phải tự kiểm tra; dễ có đường vòng |
| Vận hành Local/Docker Compose | 4–6 container | Nhiều container + CSDL; tốn RAM |
| Quy mô | Một doanh nghiệp (D-03); NFR-02 ≥ 1.000 trang/giờ — mở rộng bằng tăng số worker | Mở rộng độc lập từng service |
| Rủi ro | Module ăn mòn ranh giới nếu không có quy tắc import | Phức tạp phân tán sớm |

### 2.2. Backend: FastAPI vs Django REST Framework

| Tiêu chí | FastAPI + SQLAlchemy 2 + Alembic `[KHUYẾN NGHỊ, có điều kiện]` | Django + DRF |
| --- | --- | --- |
| Chi phí | Mã nguồn mở, miễn phí | Mã nguồn mở, miễn phí |
| Docker Compose | Một image Python + server ASGI | Một image Python + WSGI/ASGI |
| Streaming AI (UX-23: trả lời truyền dần, nút Dừng) | Hỗ trợ async/SSE tự nhiên | DRF chủ yếu đồng bộ; streaming cần view async riêng ngoài DRF |
| Schema trích xuất động (FR-DCS-01: Admin cấu hình schema) | Pydantic tạo/validate model động tốt | Serializer động được nhưng kém tự nhiên |
| OpenAPI cho API Specification | Sinh tự động từ type hint | Cần thư viện bổ sung |
| Xác thực, phân quyền | **Phải tự lắp** (hash mật khẩu, session, CSRF, MFA) → rủi ro bảo mật nếu làm sai | Có sẵn auth, session, CSRF, permission framework đã được kiểm chứng |
| Quản trị cấu hình (US-DC-008) | Phải tự làm giao diện | Có Django Admin (nhưng UX yêu cầu giao diện riêng — UX §4) |
| Transaction, khóa dòng (D-14) | SQLAlchemy hỗ trợ đầy đủ | Django ORM hỗ trợ đầy đủ |
| Kiểm thử | pytest + httpx | pytest-django + APIClient |
| Bảo trì | Ít "quy ước sẵn", cần kỷ luật kiến trúc | Quy ước mạnh, hệ sinh thái lớn |

Kết luận: FastAPI phù hợp hơn với phần AI (streaming, schema động, OpenAPI); Django + DRF mạnh hơn ở auth/admin có sẵn. Khuyến nghị FastAPI **với điều kiện** phần xác thực dùng thư viện đã được kiểm chứng (mục 2.5), không tự viết thuật toán. Nếu CDA ưu tiên giảm rủi ro auth và đội quen Django, chọn B. Kinh nghiệm của đội phát triển là tiêu chí chưa có thông tin `[CẦN XÁC NHẬN]`.

### 2.3. Frontend: React + Vite vs Next.js

| Tiêu chí | React + Vite (SPA) + PWA `[KHUYẾN NGHỊ]` | Next.js |
| --- | --- | --- |
| Nhu cầu SSR/SEO | Ứng dụng nội bộ sau đăng nhập, không cần SEO | Mạnh ở SSR/SEO — không cần ở đây |
| PWA (D-27, UX §9.1: cài màn hình chính, camera, push) | Plugin PWA cho Vite, bản build tĩnh | Làm được nhưng thêm cấu hình với server Node |
| Docker Compose | Build tĩnh, phục vụ bằng web server nhẹ (vd. Nginx/Caddy) | Thêm một server Node chạy thường trực |
| Bề mặt tấn công | Chỉ file tĩnh; mọi logic và quyền ở backend | Thêm tầng server (route handler, server action) cần bảo vệ |
| UI kit theo UX §8.3 (shadcn/ui trên Radix) | Tương thích | Tương thích |
| Bảo trì | Ít khái niệm hơn | App Router, server/client component phức tạp hơn |

Kèm theo `[KHUYẾN NGHỊ]`: TypeScript strict, React Router, TanStack Query, Tailwind + shadcn/ui (theo UX §8.3, ASM-04), i18n vi/en (NFR-05).

### 2.4. CSDL, lưu trữ file, queue

| Hạng mục | Phương án | Đánh giá | Khuyến nghị |
| --- | --- | --- | --- |
| CSDL | A. PostgreSQL | Mã nguồn mở; ACID, khóa dòng, ràng buộc unique có điều kiện, JSONB cho trường trích xuất, full-text search; có extension vector nếu cần tìm kiếm ngữ nghĩa | `[KHUYẾN NGHỊ]` |
| | B. MySQL/MariaDB | Khả thi nhưng JSON và ràng buộc kém linh hoạt hơn cho nhu cầu này | |
| File gốc (C3, SEC-DC-05, lưu ≥ 10 năm BR-16) | A. Adapter lưu trữ, mặc định volume cục bộ | Đơn giản nhất cho Docker Compose; sao lưu theo volume | `[KHUYẾN NGHỊ]` cho MVP |
| | B. Object storage tương thích S3 tự host | Tách biệt, dễ mở rộng; thêm container; cần kiểm tra giấy phép từng sản phẩm trước khi chọn | Để sau, adapter đã sẵn |
| Queue / job (NFR-01 bất đồng bộ; D-10 retry, lịch) | A. Job queue lưu trên PostgreSQL (`SELECT … FOR UPDATE SKIP LOCKED`, qua thư viện hoặc tự viết) | Không thêm hạ tầng; xếp job **cùng transaction** với dữ liệu nghiệp vụ; kill switch và job dùng cùng CSDL; đủ cho quy mô một doanh nghiệp | `[KHUYẾN NGHỊ]` |
| | B. Redis/Valkey + thư viện worker (Celery, Dramatiq, RQ…) | Phổ biến, nhanh; thêm container; job và dữ liệu không cùng transaction (cần outbox); kiểm tra giấy phép bản Redis đang dùng — Valkey là nhánh mã nguồn mở | Phương án thay thế khi tải vượt A |
| | C. RabbitMQ | Mạnh cho định tuyến sự kiện; nặng hơn nhu cầu MVP | Không khuyến nghị cho MVP |

### 2.5. Xác thực và phân quyền

| Phương án | Ưu | Nhược | Docker Compose | Khuyến nghị |
| --- | --- | --- | --- | --- |
| A. Xác thực trong backend: mật khẩu băm bằng thuật toán chậm (vd. Argon2id), **session phía server + cookie HttpOnly/SameSite**, chống CSRF, TOTP MFA | Nhẹ; thu hồi phiên tức thời khi đổi role hoặc khóa tài khoản (D-22); không thêm dịch vụ | Phải tự ghép từ thư viện; trách nhiệm bảo mật thuộc đội | Không thêm container | `[KHUYẾN NGHỊ]` cho MVP, thiết kế sẵn chỗ cho OIDC |
| B. Identity provider tự host (Keycloak, hoặc lựa chọn nhẹ hơn) qua OIDC | SSO, MFA, chính sách mật khẩu có sẵn; chuẩn | Nặng (RAM, cấu hình), thêm vận hành; quá mức khi D-30 (SSO) chưa có yêu cầu | Thêm 1–2 container | Khi CDA chốt cần SSO (D-30) |
| C. JWT stateless | Đơn giản cho API | Khó thu hồi ngay khi đổi role; lộ token trong trình duyệt | — | Không khuyến nghị cho phiên người dùng |

Phân quyền `[KHUYẾN NGHỊ]`: mô hình role → permission → assignment lưu trong CSDL (D-21); kiểm tra ở tầng service backend qua một module policy duy nhất; phạm vi dữ liệu (công ty/đơn vị/bản thân) áp dụng trong truy vấn. Thư viện policy bên ngoài (Casbin, OPA) là phương án thay thế khi quy tắc phức tạp hơn.

### 2.6. LLM / OCR adapter (D-07, D-08)

| Hạng mục | Phương án | Đánh giá | Khuyến nghị |
| --- | --- | --- | --- |
| Lớp adapter | A. Interface riêng trong code (`LLMProvider`, `OCRProvider`), adapter đầu tiên dùng API tương thích OpenAI | Mỏng, tự kiểm soát; một adapter phủ được nhiều nhà cung cấp và runtime local có API tương thích | `[KHUYẾN NGHỊ]` |
| | B. Thư viện/gateway đa provider (vd. LiteLLM) | Nhiều provider sẵn; thêm phụ thuộc lớn | Có thể dùng **bên dưới** interface A |
| LLM chạy local (dữ liệu mật, SEC-DC-04) | Runtime local (vd. Ollama) + model mở | Miễn phí, dữ liệu không rời máy; cần RAM/GPU; chất lượng tiếng Việt phải đo | Ứng viên đánh giá |
| LLM cloud | Provider có API tương thích, chi phí thấp | Chất lượng cao hơn; dữ liệu ra ngoài (CMP-02) | Ứng viên đánh giá, chỉ cho dữ liệu không mật |
| OCR | Tesseract (có gói tiếng Việt), PaddleOCR, docTR; hoặc model thị giác (VLM) | Khác nhau về độ chính xác tiếng Việt có dấu, chữ viết tay, tài nguyên | Đo trên bộ mẫu trước khi chọn (D-08) |

Provider cụ thể chưa chọn (D-08 `NEEDS_CONFIRMATION`). Đề xuất quy trình chọn: bộ tài liệu mẫu MVP (biên bản họp, kế hoạch KPI, danh sách nhân sự) → đo field accuracy (MET-01), thời gian (NFR-01), chi phí/tài liệu (MET-05) → CDA chọn.

### 2.7. Logging / monitoring

| Phương án | Đánh giá | Khuyến nghị |
| --- | --- | --- |
| A. Log có cấu trúc (JSON) ra stdout, correlation id xuyên request → job; health check; chỉ số cơ bản; ngăn xếp quan sát (vd. Prometheus + Grafana + Loki) là **profile tùy chọn** trong Compose | Nhẹ mặc định; bật khi cần | `[KHUYẾN NGHỊ]` |
| B. OpenTelemetry đầy đủ (trace, metric, log) + collector | Chuẩn, mở rộng tốt; nhiều thành phần | Đường nâng cấp từ A |
| C. Nền tảng theo dõi lỗi tự host | Nặng cho Compose | Không khuyến nghị cho MVP |

Bắt buộc với mọi phương án: audit log nghiệp vụ lưu trong CSDL, tách khỏi log kỹ thuật (D-25); không ghi secret, mật khẩu, token, dữ liệu cá nhân chưa che vào log; theo dõi chi phí AI theo tác vụ (FR-AIQ-05, MET-05).

### 2.8. Kiểm thử

| Tầng | Công cụ `[KHUYẾN NGHỊ]` | Ghi chú |
| --- | --- | --- |
| Unit backend | pytest | Logic nghiệp vụ, state machine D-14, policy D-21 |
| Integration backend | pytest + PostgreSQL thật trong container | Không dùng SQLite thay PostgreSQL: khác hành vi khóa dòng, ràng buộc, JSON |
| API / contract | Kiểm thử theo OpenAPI (vd. property-based từ schema) | Đối chiếu API Specification |
| Frontend | Vitest + Testing Library | |
| E2E | Playwright | Luồng F1–F5, review tài liệu |
| Authorization | Bảng kiểm thử sinh từ ma trận D-21: mỗi permission × role × phạm vi, cả trường hợp bị từ chối | |
| Kill switch, bút toán đảo | Test đồng thời (hai yêu cầu đảo cùng lúc), retry, idempotency | D-10, D-14 |
| AI | Adapter giả lập trong test; bộ đánh giá vàng cho Evaluation Engine (FR-AIQ-01) | Không gọi provider thật trong CI |
| Bảo mật | Quét phụ thuộc Python/JS, phân tích tĩnh, kiểm thử prompt injection qua tài liệu (BR-06) | |

---

## 3. D-10 — Kill switch: câu hỏi chuẩn hóa

Nguyên tắc `[CDA nêu]` đã ghi ở Decision_Log 3.1.1 (không lặp lại). Cơ chế chung `[KHUYẾN NGHỊ]`: trạng thái kill switch lưu trong CSDL; cổng ghi (Tool Registry) đọc trạng thái **trong cùng transaction** với lệnh ghi; job mang mức autonomy dự kiến nhưng cổng ghi luôn dùng trạng thái hiện hành.

| # | Câu hỏi | Phương án | Khuyến nghị | Tác động |
| --- | --- | --- | --- | --- |
| K1 | Phạm vi | A. Một công tắc toàn hệ thống · B. Theo module/agent | **A** cho MVP (BRD §4.2: "toàn bộ"); B để sau | B cần thêm cấu hình và ma trận test |
| K2 | Job trong queue / đang chạy / retry | A. Chặn tại cổng ghi → tạo bản nháp L2; xác nhận job đã xong chỉ sau khi bản nháp được lưu; retry chỉ được tạo bản nháp · B. Hủy job, không giữ kết quả | **A** (đúng `[CDA nêu]` 2: chuyển thành bản nháp) | A cần bảng bản nháp hành động; B mất công việc AI đã làm |
| K3 | Lịch định kỳ khi tắt kill switch | A. Chạy tiếp từ lần kế tiếp, không chạy bù · B. Giữ tạm dừng đến khi ADMIN bật lại từng lịch | **A** | B an toàn hơn nhưng dễ quên bật lại |
| K4 | Người review bản nháp | A. Người khởi tạo tác vụ hoặc chủ entity có permission tương ứng; tài chính theo `finance.approve` (D-14) · B. Chỉ quản lý trực tiếp | **A** | Cần xác định "chủ entity" cho từng loại hành động |
| K5 | Thời hạn bản nháp | A. 30 ngày → trạng thái "cần rà soát", không xóa, không thực thi · B. Không hạn · C. ADMIN cấu hình, mặc định 30 | **C** | 30 ngày là đề xuất, không có nguồn |
| K6 | Thông báo | A. In-app ngay cho người khởi tạo + nhắc người review hằng ngày đến khi xử lý · B. Chỉ in-app khi chuyển | **A**; kênh ngoài in-app phụ thuộc D-32 | Nhắc hằng ngày cần job lịch |

Audit `[KHUYẾN NGHỊ]`: `kill_switch.enabled`, `kill_switch.disabled` (người, lý do bắt buộc), `ai_action.blocked_to_draft`, `schedule.paused`, `schedule.resumed`, `draft.marked_stale`, `draft.approved`/`draft.rejected`.
Khi tắt `[CDA nêu]` 4: bản nháp giữ nguyên chờ review; chỉ tác vụ **mới** chạy lại ở L3. Hành động ghi do **người** thực hiện không bị kill switch ảnh hưởng; L0/L1 vẫn hoạt động `[KHUYẾN NGHỊ]`.

---

## 4. D-14 — Bút toán đảo: câu hỏi chuẩn hóa

Nguyên tắc `[CDA nêu]` ở Decision_Log 3.2.2; bảng chuyển trạng thái ở 3.2.1.

| # | Câu hỏi | Phương án | Khuyến nghị | Tác động |
| --- | --- | --- | --- | --- |
| F1 | Nguồn trạng thái kỳ | A. AI-EOS tự quản lý kỳ (bảng kỳ `OPEN`/`CLOSED`, người có quyền khóa kỳ) · B. Lấy từ phần mềm kế toán ngoài · C. Không có khái niệm kỳ trong MVP | **A**, giới hạn là **kỳ báo cáo quản trị** của AI-EOS, không thay kỳ kế toán pháp lý (BR-18). Quyền khóa kỳ: thêm permission `finance.period.close` `[CẦN XÁC NHẬN]` | B cần tích hợp (MVP không có — D-31); C không thực thi được "không ghi vào kỳ đã khóa" |
| F2 | Kỳ gốc đã khóa | A. Ghi bút toán đảo vào kỳ đang mở, liên kết giao dịch và kỳ gốc · B. Từ chối đảo, yêu cầu mở lại kỳ | **A** | B cần quy trình mở lại kỳ, chưa có nguồn |
| F3 | Hủy/rút giao dịch chờ duyệt | A. Người tạo được rút `PENDING_APPROVAL → CANCELLED` trước khi duyệt; muốn sửa thì tạo bản nháp mới · B. Cho trả về `DRAFT` để sửa | **A** | A giữ lịch sử đơn giản (không có vòng sửa-duyệt); B cần ghi lịch sử từng phiên bản |
| F4 | Đảo một bút toán đảo | A. Không cho phép; muốn khôi phục thì tạo giao dịch mới qua quy trình thường, tham chiếu cả hai · B. Cho phép | **A** | B tạo chuỗi đảo phức tạp, khó đối soát |
| F5 | AI soạn vs nhập tay | A. Cùng state machine, cùng quyền duyệt; giao dịch AI soạn thay người dùng X thì X là "người tạo" (X không được duyệt) · B. AI soạn cần thêm một cấp duyệt | **A** (D-12 đã yêu cầu L2 cho mọi ghi tài chính) | B tăng tải duyệt |
| F6 | Ủy quyền và hạn mức | A. Assignment ủy quyền có phạm vi (đơn vị, loại giao dịch, thời hạn hiệu lực, hạn mức tùy chọn); **giá trị hạn mức do CDA cấu hình, hệ thống không có giá trị mặc định**; nếu chưa cấu hình hạn mức thì chỉ người có phạm vi đầy đủ được duyệt · B. Chỉ role `CFO` duyệt, không ủy quyền trong MVP | **B cho MVP**, A sau khi CDA cung cấp quy tắc | A cần CDA cung cấp hạn mức (D-16); B có rủi ro tắc nghẽn nếu chỉ có một CFO |
| F7 | Entity tài chính MVP | A. Theo Finance Lite (BRD §6.1): ghi nhận doanh thu, ghi nhận chi phí, số dư tiền mặt (runway là chỉ số tính ra) · B. Thêm ngân sách (BRD §4.3 có chỉ số chênh lệch ngân sách) | **A**; B `[CẦN XÁC NHẬN]`. Hóa đơn là Phase 2 (D-17) | Xác định bảng nào áp dụng state machine |

Kỹ thuật `[KHUYẾN NGHỊ]` (chi tiết ở ADR-009): ràng buộc duy nhất "mỗi giao dịch gốc tối đa một bút toán đảo đã ghi"; ràng buộc duy nhất cho idempotency key; cột `version` cho optimistic locking; kiểm tra "người duyệt ≠ người tạo" ở backend; audit ghi cùng transaction với chuyển trạng thái; kiểu tiền `NUMERIC` (không dùng số thực dấu phẩy động).

**Mâu thuẫn tiềm ẩn:** nguyên tắc "người tạo không tự duyệt" cần ít nhất **hai** người có quyền tài chính. Nếu doanh nghiệp chỉ có một CFO và chọn F6-B, CFO không thể ghi giao dịch do chính mình tạo. Cần CDA chọn: người tạo khác (MANAGER, nhân viên tài chính) hoặc người duyệt dự phòng.

---

## 5. D-21 — Ma trận vai trò: câu hỏi chuẩn hóa

Ma trận đề xuất ở Decision_Log mục 4 (không lặp lại).

| # | Câu hỏi | Phương án | Khuyến nghị | Tác động |
| --- | --- | --- | --- | --- |
| R1 | Năm role nền tảng + Reviewer là assignment | A. Đồng ý · B. Thêm role (vd. HR, Legal) | **A** cho MVP | Xem R6 về dữ liệu nhân sự |
| R2 | `CEO` có `finance.approve`? | A. Không mặc định; chỉ khi được giao ủy quyền · B. Có | **A** (tách người ra quyết định và người duyệt ghi sổ) | B làm CEO thành người duyệt dự phòng (giải mâu thuẫn mục 4) |
| R3 | Quyền xem audit log | A. `ADMIN`: toàn bộ; `CEO`: audit hành động nghiệp vụ và AI, chỉ đọc; khác: audit bản ghi mình có quyền đọc · B. Chỉ `ADMIN` | **A** | A cần phân loại audit nghiệp vụ / hệ thống |
| R4 | `ADMIN` đọc dữ liệu nghiệp vụ? | A. Không, trừ kết quả import danh sách nhân sự và lỗi import · B. Có toàn quyền đọc | **A** (least privilege) | ADMIN khó hỗ trợ người dùng khi cần xem dữ liệu → cần quy trình hỗ trợ có cấp quyền tạm thời `[CẦN XÁC NHẬN]` |
| R5 | Người giữ `finance.submit`, `finance.reverse.request` | A. `CFO` và `MANAGER` (chi phí đơn vị) · B. Chỉ `CFO` | **A**: MANAGER `finance.submit`; `finance.reverse.request` chỉ `CFO` | EMPLOYEE gửi chứng từ là Phase 2 (D-17) |
| R6 | Người giữ `pii.read` (lương, CCCD, sức khỏe) | A. `CEO`, `CFO` (chi phí lương); EMPLOYEE thấy của mình · B. Thêm role/assignment nhân sự | **B** `[CẦN XÁC NHẬN]`: nguồn có US-DC-007 (import nhân sự) nhưng không có persona HR | Không có HR thì không ai quản lý hồ sơ nhân sự ngoài ADMIN import |
| R7 | Nhiều role trên một tài khoản; ai giao assignment | A. Cho nhiều role (UX §4.2 đổi ngữ cảnh); quy tắc "không tự duyệt" theo tài khoản; hàng chờ review: ADMIN tạo hàng chờ, MANAGER giao trong đơn vị; ủy quyền tài chính: CFO đề nghị, ADMIN áp dụng · B. Một role/tài khoản | **A**; cấm tổ hợp `ADMIN` + `CFO` trên cùng tài khoản `[CẦN XÁC NHẬN]` | A cần kiểm tra tổ hợp role bị cấm |
| R8 | `config.autonomy` | A. `ADMIN`, nhưng **không** thể nâng tài chính lên trên L2 (D-12) và không vượt L3 (D-11) — chặn cứng trong code · B. Thay đổi tăng autonomy cần thêm CEO duyệt | **A**; B tùy chọn | B thêm luồng duyệt hai người |

---

## 6. D-22 — Gán role: câu hỏi chuẩn hóa

Nguyên tắc `[CDA nêu]` ở Decision_Log 3.3.1. Không có tài khoản mặc định hay bí mật hardcode trong source code hoặc seed.

| # | Câu hỏi | Phương án | Khuyến nghị | Tác động |
| --- | --- | --- | --- | --- |
| A1 | Cấp tài khoản | A. ADMIN tạo tài khoản + gửi lời mời dùng một lần, có hạn; người dùng tự đặt mật khẩu · B. ADMIN đặt mật khẩu tạm · C. SSO (D-30) | **A** (B lộ mật khẩu qua người thứ ba) | Lời mời cần kênh gửi (in-app/email) → phụ thuộc D-32; nếu chưa có email, ADMIN trao link trực tiếp |
| A2 | Bootstrap ADMIN đầu tiên | A. Lệnh CLI chạy một lần trong container, nhận thông tin qua biến môi trường/secret file hoặc nhập tương tác; từ chối nếu đã có ADMIN; buộc đổi mật khẩu + đăng ký MFA ở lần đầu; ghi audit `bootstrap` · B. Endpoint setup trên web chỉ mở khi chưa có ADMIN | **A** (B có cửa sổ bị chiếm quyền nếu lộ ra mạng) | Cần truy cập máy chủ để bootstrap |
| A3 | Thay đổi role | ADMIN qua API có xác thực, yêu cầu xác thực lại (step-up) + lý do; audit trước/sau; **thu hồi mọi phiên** của người bị đổi | Khuyến nghị | Phiên phía server (mục 2.5-A) |
| A4 | Gỡ ADMIN cuối cùng | A. Chặn gỡ/khóa ADMIN đang hoạt động cuối cùng · B. Cho phép | **A** | Cần quy trình khôi phục (A6) |
| A5 | ADMIN tự nâng quyền | A. ADMIN không được sửa role/permission/assignment của chính mình; cần ADMIN khác · B. Cho phép có audit | **A**; hệ quả: nên có **tối thiểu 2 ADMIN** `[CẦN XÁC NHẬN]` | Với một ADMIN duy nhất, mọi thay đổi quyền của chính ADMIN cần A6 |
| A6 | Khôi phục khi mất mọi ADMIN | Lệnh CLI khôi phục cần quyền truy cập máy chủ, ghi audit, thông báo ADMIN khác (nếu có) | Khuyến nghị | — |

---

## 7. Dự thảo ADR `[PROPOSED]` (lịch sử — bản hiện hành: `docs/03-architecture/decisions/`)

Mẫu chung: Bối cảnh · Vấn đề · Phương án · Quyết định đề xuất · Lý do · Hệ quả · Rủi ro · Trạng thái. Tất cả ở trạng thái **PROPOSED**; không ADR nào được coi là đã chốt.

### ADR-001 — Kiểu kiến trúc: modular monolith + worker
- **Bối cảnh:** hệ thống nội bộ một doanh nghiệp, Local/Docker Compose (D-03); cần cổng ghi duy nhất (BR-04), kill switch ở backend (D-09), toàn vẹn giao dịch tài chính (D-13, D-14).
- **Vấn đề:** tách service hay một ứng dụng chia module?
- **Phương án:** A. Modular monolith (API + worker cùng codebase, một CSDL) · B. Microservices.
- **Quyết định đề xuất:** A. Module theo domain (data capture, goals/KPI, tasks, finance lite, sales lite, identity/access, AI orchestration, audit); quy tắc phụ thuộc giữa module được kiểm tra tự động.
- **Lý do:** mục 2.1.
- **Hệ quả:** một CSDL; worker là process riêng dùng chung code; có thể tách service sau theo ranh giới module.
- **Rủi ro:** ranh giới module bị phá → cần lint kiến trúc trong CI.
- **Trạng thái:** PROPOSED.

### ADR-002 — Backend: Python + FastAPI
- **Bối cảnh:** `[CDA nêu]` backend Python. Cần streaming AI, schema trích xuất động, OpenAPI.
- **Phương án:** A. FastAPI + SQLAlchemy 2 + Alembic + Pydantic · B. Django + DRF.
- **Quyết định đề xuất:** A, điều kiện: auth dùng thư viện đã kiểm chứng (ADR-006).
- **Lý do / Hệ quả / Rủi ro:** mục 2.2. Rủi ro chính: tự lắp auth; giảm bằng ADR-006 và bộ test authorization (ADR-013).
- **Trạng thái:** PROPOSED. Phương án thay thế B nếu CDA ưu tiên auth/admin có sẵn.

### ADR-003 — Frontend: React + Vite (SPA) + PWA
- **Bối cảnh:** `[CDA nêu]` frontend React; UX đề xuất web responsive + PWA (UX §9.1), shadcn/ui trên Radix (UX §8.3).
- **Phương án:** A. React + Vite SPA · B. Next.js.
- **Quyết định đề xuất:** A + TypeScript strict, React Router, TanStack Query, Tailwind + shadcn/ui, plugin PWA, i18n vi/en.
- **Lý do / Hệ quả / Rủi ro:** mục 2.3. Rủi ro: PWA trên iOS hạn chế push/camera nền → ảnh hưởng UX-18, liên quan D-27.
- **Trạng thái:** PROPOSED.

### ADR-004 — CSDL và lưu trữ file
- **Quyết định đề xuất:** PostgreSQL; adapter lưu trữ file với triển khai mặc định là volume cục bộ, triển khai S3-compatible để sau. Tiền dùng `NUMERIC`.
- **Phương án thay thế:** MySQL/MariaDB; object storage ngay từ MVP.
- **Hệ quả:** sao lưu gồm CSDL + volume file (NFR-03: RPO ≤ 15 phút, RTO ≤ 4 giờ → cần chiến lược backup liên tục cho PostgreSQL, chi tiết ở 2C).
- **Rủi ro:** volume cục bộ không đủ cho lưu trữ 10 năm (BR-16) nếu không có backup ngoài máy.
- **Trạng thái:** PROPOSED.

### ADR-005 — Job queue trên PostgreSQL
- **Quyết định đề xuất:** queue lưu trong PostgreSQL (khóa dòng bỏ qua dòng đã khóa), job xếp cùng transaction với dữ liệu; retry có giới hạn và backoff; lịch định kỳ là bản ghi trong CSDL để kill switch tạm dừng được.
- **Phương án thay thế:** Redis/Valkey + thư viện worker; RabbitMQ.
- **Hệ quả:** không thêm container; mọi job đi qua cổng ghi khi ghi dữ liệu (ADR-008).
- **Rủi ro:** thông lượng thấp hơn broker chuyên dụng → theo dõi theo NFR-02; đường nâng cấp sang phương án B.
- **Trạng thái:** PROPOSED.

### ADR-006 — Xác thực
- **Quyết định đề xuất:** xác thực trong backend: Argon2id, session phía server + cookie HttpOnly/Secure/SameSite, chống CSRF, TOTP MFA bắt buộc với ADMIN `[CẦN XÁC NHẬN — D-30]`, khóa tạm khi đăng nhập sai nhiều lần, lời mời tài khoản dùng một lần (D-22 A1), bootstrap qua CLI (D-22 A2). Chừa giao diện cho OIDC.
- **Phương án thay thế:** IdP tự host qua OIDC; JWT stateless.
- **Hệ quả:** thu hồi phiên tức thời khi đổi role/khóa tài khoản.
- **Rủi ro:** lỗi tự triển khai → dùng thư viện đã kiểm chứng, test bảo mật.
- **Trạng thái:** PROPOSED.

### ADR-007 — Phân quyền: role → permission → assignment
- **Quyết định đề xuất:** lưu role, permission, assignment trong CSDL; một module policy duy nhất ở backend quyết định; phạm vi dữ liệu áp dụng ở truy vấn; mặc định từ chối; ràng buộc cứng: người duyệt ≠ người tạo (D-14), tài chính không vượt L2 (D-12), không vượt L3 (D-11), ADMIN không tự sửa quyền mình (D-22 A5); AI hành động trong quyền của người dùng khởi tạo.
- **Phương án thay thế:** thư viện policy ngoài (Casbin/OPA).
- **Hệ quả:** ma trận test authorization sinh từ dữ liệu ma trận D-21.
- **Trạng thái:** PROPOSED — nội dung ma trận chờ D-21.

### ADR-008 — Cổng ghi AI: Tool Registry, autonomy, kill switch
- **Bối cảnh:** BR-04, BR-09, FR-DCS-05, D-09, D-10, D-11, D-12, D-26.
- **Quyết định đề xuất:** mọi hành động ghi do AI khởi tạo đi qua Tool Registry; mỗi tool có `operation_type` (READ/WRITE/EXECUTION), `risk_level`, `approval_required`, mức autonomy mặc định; tại thời điểm ghi, cổng kiểm tra lần lượt: permission của người dùng khởi tạo → autonomy hiệu lực (cấu hình, bị chặn trần bởi D-11, D-12) → kill switch → idempotency; nếu hiệu lực là L2 thì tạo bản nháp chờ xác nhận. Nội dung tài liệu không bao giờ kích hoạt tool (BR-06).
- **Phương án thay thế:** kiểm tra autonomy ở từng module (bị loại: dễ có đường vòng).
- **Hệ quả:** cần bảng bản nháp hành động, trạng thái kill switch, cấu hình autonomy.
- **Rủi ro:** module gọi thẳng repository bỏ qua cổng → kiểm tra kiến trúc tự động + test.
- **Trạng thái:** PROPOSED; điểm mở D-10 mục 3.

### ADR-009 — Giao dịch tài chính và bút toán đảo
- **Quyết định đề xuất:** state machine Decision_Log 3.2.1; bút toán đảo là giao dịch mới liên kết gốc; ràng buộc unique "một bút toán đảo đã ghi cho mỗi gốc"; idempotency key unique; optimistic locking; người duyệt ≠ người tạo; kỳ báo cáo `OPEN`/`CLOSED` (F1-A) với ghi đảo vào kỳ đang mở (F2-A); audit cùng transaction; không có thao tác xóa vật lý (D-15).
- **Phương án thay thế:** cập nhật tại chỗ có lịch sử phiên bản (bị loại theo D-13).
- **Trạng thái:** PROPOSED; điểm mở D-14 mục 4.

### ADR-010 — Audit log
- **Quyết định đề xuất:** bảng audit append-only trong PostgreSQL; ghi cùng transaction với thay đổi nghiệp vụ; trường: thời điểm, actor, loại actor (người/AI/hệ thống), người khởi tạo (với AI), autonomy level, hành động, đối tượng, giá trị trước/sau (che dữ liệu nhạy cảm), lý do, correlation id; tài khoản ứng dụng không có quyền UPDATE/DELETE trên bảng audit; xem audit theo D-21 R3.
- **Phương án thay thế:** ghi audit qua log kỹ thuật (bị loại: không đảm bảo toàn vẹn, khó truy vấn).
- **Rủi ro:** bảng lớn dần → phân vùng theo thời gian, chính sách lưu trữ (GAP-15).
- **Trạng thái:** PROPOSED.

### ADR-011 — LLM/OCR adapter
- **Quyết định đề xuất:** interface `LLMProvider`, `OCRProvider` trong code; adapter đầu tiên dùng API tương thích OpenAI (phủ runtime local và provider cloud); định tuyến theo mức phân loại dữ liệu: dữ liệu mật chỉ đến provider local (SEC-DC-04, CMP-02); cấu hình provider qua biến môi trường/secret, không trong code; fallback model (NFR-07); ghi chi phí theo lời gọi (FR-AIQ-05).
- **Phương án thay thế:** thư viện đa provider làm lõi.
- **Trạng thái:** PROPOSED; provider cụ thể chờ D-08.

### ADR-012 — Logging và monitoring
- **Quyết định đề xuất:** mục 2.7 phương án A.
- **Trạng thái:** PROPOSED.

### ADR-013 — Chiến lược kiểm thử
- **Quyết định đề xuất:** mục 2.8; PostgreSQL thật cho integration; ma trận authorization; test đồng thời cho tài chính; adapter AI giả lập trong CI.
- **Trạng thái:** PROPOSED.

---

## 8. Mâu thuẫn, giả định, rủi ro

| # | Loại | Nội dung | Liên quan |
| --- | --- | --- | --- |
| 1 | Mâu thuẫn tiềm ẩn | "Người tạo không tự duyệt" cần ≥ 2 người có quyền tài chính; F6-B (chỉ CFO) có thể tắc nghẽn | D-14, D-21 R2, R5 |
| 2 | Mâu thuẫn tiềm ẩn | "ADMIN không tự sửa quyền mình" + "chặn gỡ ADMIN cuối cùng" ⇒ hệ thống một ADMIN không tự đổi được quyền của chính ADMIN đó | D-22 A4, A5 |
| 3 | Khoảng trống | Không có persona/role nhân sự trong khi có import nhân sự và dữ liệu lương | D-21 R6, US-DC-007, SEC-DC-02 |
| 4 | Ranh giới | Kỳ báo cáo trong AI-EOS không phải kỳ kế toán pháp lý (BR-18) | D-14 F1 |
| 5 | Giả định | Kinh nghiệm của đội phát triển với FastAPI/Django chưa biết | D-06 |
| 6 | Rủi ro | PWA trên một số nền tảng di động hạn chế push/camera nền/sinh trắc học | D-27, UX-18, UX-19 |
| 7 | Rủi ro | Chất lượng OCR/LLM tiếng Việt chưa đo; mục tiêu field accuracy ≥ 90% (MET-01) có thể không đạt với provider miễn phí | D-08 |
| 8 | Ràng buộc | Lời mời tài khoản và nhắc việc cần kênh thông báo; D-32 chưa chốt | D-22 A1, D-10 K6 |
