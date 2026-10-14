# AI-EOS — Decision Log

> Phiên bản: 0.12 (hồ sơ Q-48, thêm Q-49) · Ngày: 14/10/2026 · Trạng thái: **Chờ chủ dự án duyệt các mục PROPOSED / NEEDS_CONFIRMATION**
> Liên quan: [Source_Analysis.md](Source_Analysis.md) (CON/GAP/Q/ASM gốc), [Requirements_Traceability.md](Requirements_Traceability.md) (trạng thái từng yêu cầu).
> ID quyết định `D-xx` ổn định, không tái sử dụng. Lịch sử thay đổi: mục 6.

> Đề xuất chi tiết và dự thảo ADR cho D-06, D-10, D-14, D-21, D-22: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md).

**Nguồn thẩm quyền (từ 0.5):** `CDA` = quyết định trực tiếp của chủ dự án ở các vòng trước · `CDA_DIRECTIVE` = quy tắc CDA chốt trong yêu cầu ngày 12/10/2026 (K1–K6, F1–F7, R1–R8, A1–A6) · `ARCHITECTURE_DECISION` = lựa chọn kỹ thuật chốt theo thẩm quyền kiến trúc (ADR-001…013), **không** phải phê duyệt trực tiếp của CDA cho từng chi tiết.

**Ký hiệu (từ 0.6):** quy tắc tài chính `F1–F7` của `CDA_DIRECTIVE` trùng mã với luồng UX `F1–F5` (UX §5). Trong các cột truy vết và tài liệu Stage 2B, quy tắc tài chính được ghi `CDA-F1…CDA-F7`; `F1–F5` không tiền tố là luồng UX. Văn bản đã có trong ADR, Architecture và mục 2–3 của file này giữ nguyên vì luôn đi kèm ngữ cảnh `CDA_DIRECTIVE`/tài chính.

**Nhãn nội dung:** `[CDA nêu]` = nguyên tắc chủ dự án đưa ra, được ghi nhận, nhưng quyết định chứa nó chưa `CONFIRMED` khi còn điểm mở.
**Trạng thái:** `CONFIRMED` (chủ dự án đã chốt, hoặc hệ quả trực tiếp của quyết định đã chốt — ghi rõ căn cứ) · `PROPOSED` (đề xuất của người phân tích, chưa duyệt) · `NEEDS_CONFIRMATION` (thiếu thông tin, cần chủ dự án quyết) · `DEFERRED` (để sau MVP hoặc ưu tiên thấp).
**Ưu tiên** cho mục chưa đóng: `Cao` = chặn 2B hoặc 2C · `TB` = chặn một phần tài liệu · `Thấp` = không chặn.
**Người phê duyệt:** CDA = chủ dự án.
**Nhãn `[LEGACY FINDING — A-EMS]`:** nhận định về dự án cũ A-EMS, **không** phải hiện trạng hay lỗi của AI-EOS; chỉ giữ để truy vết lịch sử.

---

## 1. Ranh giới dự án

### 1.1. Hiện trạng AI-EOS

| Hạng mục | Hiện trạng | Căn cứ |
| --- | --- | --- |
| Vị trí | `CyEyes/AI-EOS/` (thư mục untracked trong git repo `CyEyes`, branch `feature/hr-service-lab`) | `git status` |
| Nội dung | Chỉ có tài liệu trong `docs/00-source/` | Liệt kê thư mục |
| Code, cấu hình, Docker Compose, schema, migration, API, test | **Chưa có** | Liệt kê thư mục |
| Nguồn yêu cầu | `BRD_Review.md`, `UI_UX_Proposal.md`. BRD v1.1 đã được chủ dự án xác nhận là bản được duyệt (D-01), nhưng **toàn văn BRD v1.1 không có trong repository** | D-01 |

Hệ quả: mọi quyết định kiến trúc và thiết kế ở Giai đoạn 2 dựa trên tài liệu AI-EOS đã được duyệt và các quyết định trong file này. Không giả định đã có codebase. Không có yêu cầu nào ở trạng thái `IMPLEMENTED` hoặc `VERIFIED`.

### 1.2. A-EMS — dự án cũ, ngoài phạm vi

AI-EOS là hệ thống mới, độc lập (D-05). Không dùng code A-EMS làm baseline (D-04). Hai vị trí A-EMS đã được nhận diện ở checkpoint 2A bản 0.1, chỉ ghi lại để tránh nhầm lẫn:

| Vị trí | Mô tả | Xử lý |
| --- | --- | --- |
| `CyEyes/A-EMS/` | Có trong `HEAD` của repo `CyEyes`, đã bị xóa khỏi working tree | Không khôi phục, không dùng |
| `CyEyes/Final_Project/A-EMS/` | Git repo riêng của dự án cũ | Không dùng làm nguồn yêu cầu, persona, role, API, database hay kiến trúc |

### 1.3. Phát hiện ghi nhận ở bản 0.1 — phân loại lại

Các ID được giữ nguyên để không mất lịch sử; nội dung và trạng thái được phân loại lại theo D-04, D-05.

| ID | Nhãn | Nội dung (bản 0.1) | Trạng thái 0.2 | Xử lý cho AI-EOS |
| --- | --- | --- | --- | --- |
| CON-15 | `[LEGACY FINDING — A-EMS]` | Phạm vi A-EMS (dashboard + AI chỉ đọc; loại trừ workflow/approval) khác AI-EOS | CONFIRMED — đóng, ngoài phạm vi (D-05) | Không áp dụng. Phạm vi AI-EOS chỉ theo nguồn AI-EOS |
| CON-16 | `[LEGACY FINDING — A-EMS]` | Tập 8 role của A-EMS khác persona AI-EOS | CONFIRMED — đóng, ngoài phạm vi (D-05) | Role AI-EOS xây mới, xem D-21 |
| CON-17 | `[LEGACY FINDING — A-EMS]` | Repo `Final_Project/A-EMS`, finance-service: revenues/expenses/budgets có `DELETE` xóa cứng | CONFIRMED — đóng, không phải lỗi AI-EOS (D-15) | Chuyển thành kiểm soát thiết kế có căn cứ D-13 (xem D-15) |
| CON-18 | `[LEGACY FINDING — A-EMS]` | Repo `Final_Project/A-EMS`, auth-service: `POST /auth/register` public cho phép tự chọn role | CONFIRMED — đóng, không phải lỗi AI-EOS (D-22) | Chuyển thành kiểm soát thiết kế `PROPOSED` (xem D-22) |
| CON-19 | — | Hai vị trí code A-EMS; tên AI-EOS vs A-EMS | CONFIRMED — đã giải quyết (D-04, D-05) | AI-EOS độc lập, chưa có code |
| GAP-22 | `[LEGACY FINDING — A-EMS]` | A-EMS không có audit log nghiệp vụ | CONFIRMED — đóng, ngoài phạm vi | Với AI-EOS, audit là yêu cầu có nguồn (FR-DC-05, BR-04, FR-DCS-06); thiết kế ở D-25 |
| GAP-23 | `[LEGACY FINDING — A-EMS]` | A-EMS không có approval, Tool Registry có `risk_level`, hàng đợi tác vụ AI | CONFIRMED — đóng, ngoài phạm vi | Với AI-EOS là yêu cầu có nguồn (BR-04, BR-09, FR-DCS-05); thiết kế ở D-26 |
| GAP-24 | `[LEGACY FINDING — A-EMS]` | A-EMS không có OCR, chỉ một provider LLM | CONFIRMED — đóng, ngoài phạm vi | Với AI-EOS: provider chưa chọn (D-08) |
| GAP-25 | `[LEGACY FINDING — A-EMS]` | `CLAUDE.md` của A-EMS lệch code | CONFIRMED — đóng, không liên quan | CLAUDE.md của AI-EOS viết mới ở 2D |

---

## 2. Danh sách quyết định

| ID | Nội dung cần quyết định | Nguồn / liên quan | Trạng thái | Quyết định hiện tại | Phương án đề xuất | Tác động | Người phê duyệt | Điều kiện đóng |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D-01 | Tình trạng và phạm vi nguồn BRD | Q-01, Q-02, GAP-01, GAP-02, ASM-07 | CONFIRMED | BRD v1.1 đã được duyệt (theo xác nhận của CDA). Repository chỉ có `BRD_Review.md` và `UI_UX_Proposal.md`; toàn văn BRD v1.0/v1.1 không có. Nội dung không có trong hai file giữ `[CẦN XÁC NHẬN]`, không gán cho BRD | — | Tất cả tài liệu; mã tham chiếu v1.0 vẫn `[TBD]` | CDA | Đã đóng |
| D-02 | Độ sâu tài liệu Giai đoạn 2 | Q-03 | CONFIRMED | P0 chi tiết đủ để triển khai và nghiệm thu; P1/P2 ở mức roadmap | — | PRD, SRS, Implementation Plan, Test Plan | CDA | Đã đóng |
| D-03 | Mô hình triển khai | Q-04, GAP-05 | CONFIRMED | Hệ thống nội bộ một doanh nghiệp; hạ tầng mục tiêu Local/Docker Compose | Diễn giải chỗ BRD nói "tenant" (C6, NFR-02, BR-22) thành "toàn hệ thống/phòng ban" `[PROPOSED]` | Architecture, DB (không cần `tenant_id`), NFR-02 | CDA | Đã đóng |
| D-04 | Code baseline | CON-19, Q-23 | CONFIRMED | **Không** dùng A-EMS cũ (`Final_Project/A-EMS`, `CyEyes/A-EMS` hoặc commit của chúng) làm baseline. Không khôi phục code đã xóa. AI-EOS hiện chưa có code; thiết kế dựa trên tài liệu AI-EOS đã duyệt | — | Architecture, DB, API, CLAUDE.md, Implementation Plan (toàn bộ là việc mới) | CDA | Đã đóng |
| D-05 | Quan hệ AI-EOS và A-EMS | CON-15, CON-16, Q-24 | CONFIRMED | AI-EOS là hệ thống mới, độc lập. Tài liệu A-EMS chỉ là tham khảo lịch sử khi thực sự cần, không phải nguồn sự thật cho yêu cầu, persona, role, API, database, kiến trúc | — | Mọi tài liệu Giai đoạn 2 | CDA | Đã đóng |
| D-06 | Tech stack AI-EOS | Q-05, GAP-06, ASM-04 | CONFIRMED — `ARCHITECTURE_DECISION` (trong định hướng `[CDA nêu]`) | AI-EOS **chưa có** tech stack được xác nhận. Nguyên tắc: mọi lựa chọn và thay đổi công nghệ cần lý do + ADR; không tái sử dụng stack A-EMS cũ làm baseline. Nguồn AI-EOS chỉ có giả định UI "shadcn/ui trên Radix" (UX §8.3, ASM-04) và nguyên tắc Model Gateway model-agnostic (BRD §4.4) **[CDA nêu] định hướng (chưa phải quyết định cuối):** backend Python, frontend React, Local/Docker Compose, ưu tiên miễn phí/mã nguồn mở, LLM/OCR qua adapter. **Chốt 12/10/2026:** ADR-001…ADR-013 (`docs/03-architecture/decisions/`): modular monolith + worker, FastAPI + SQLAlchemy 2 + Alembic, React + Vite + TypeScript + PWA, PostgreSQL + storage adapter, queue trên PostgreSQL, session phía server + Argon2id + MFA ADMIN, RBAC + permission + assignment, write gateway, giao dịch tài chính, audit append-only, provider adapter, logging, testing. | Ở 2C đề xuất phương án + ADR `PROPOSED` cho frontend, backend, database, queue, authentication/authorization, LLM/OCR adapter, logging/monitoring, testing; ưu tiên chi phí thấp, mã nguồn mở, chạy được Local/Docker Compose (mục 3.4). Không chốt trước khi CDA duyệt Đánh giá và dự thảo ADR-001…013: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md) mục 2, 7. | Architecture, ADR, CLAUDE.md, Implementation Plan | CDA | CDA duyệt các ADR công nghệ ở 2C |
| D-07 | Nguyên tắc tích hợp LLM/OCR | Q-05, FR-AIQ-06, SEC-DC-04 | CONFIRMED | Tích hợp qua lớp adapter/interface, không khóa vào một provider; cấu hình provider tách khỏi logic nghiệp vụ; ưu tiên provider miễn phí hoặc chi phí thấp; không ghi secret vào tài liệu/repo | Hai interface tách biệt cho LLM và OCR; định tuyến theo mức phân loại dữ liệu (SEC-DC-04) `[PROPOSED]`; ADR ở 2C | Architecture, ADR, SRS | CDA | Đã đóng (nguyên tắc) |
| D-08 | Chọn provider LLM/OCR cụ thể | Q-27, SEC-DC-04, CMP-02, D-07 | NEEDS_CONFIRMATION (TB) | Chưa chọn **Cập nhật 12/10/2026:** chưa khóa provider; kế hoạch benchmark (tập dữ liệu được CDA duyệt, ground truth, trường, cách tính accuracy, lỗi nghiêm trọng, chi phí, latency) ở ADR-011; dữ liệu nhạy cảm không gửi provider ngoài cho tới khi có quyết định; không tuyên bố đạt MET-01 trước benchmark. **Chỉ đạo 12/10/2026 (`CDA_DIRECTIVE`):** benchmark trước bằng tài liệu tiếng Việt **tổng hợp, không có PII thật**; tài liệu thật chỉ khi người có thẩm quyền phê duyệt và đã xử lý phù hợp; định nghĩa dataset, ground truth, metric, lỗi nghiêm trọng, latency, chi phí trước khi đo; không gửi dữ liệu nhạy cảm ra provider ngoài. Kế hoạch: TEST_Plan §9. | 2C lập bảng đánh giá: chất lượng tiếng Việt có dấu và chữ viết tay, khả năng chạy local, quyền riêng tư/chuyển dữ liệu ra nước ngoài, chi phí, yêu cầu tài nguyên. Ứng viên chỉ để đánh giá, không phải lựa chọn: LLM chạy local và LLM cloud có API tương thích; OCR mã nguồn mở chạy local. Dữ liệu mật mặc định không gửi cloud `[PROPOSED]` | ADR, NFR, chi phí | CDA | CDA chọn sau khi xem bảng đánh giá |
| D-09 | Kill switch: ai bật, hiệu lực | Q-06, CON-04, BR-13, FR-AUT-04, UX-29 | CONFIRMED | Chỉ `ADMIN` kích hoạt. Khi bật, mọi hành động AI L3/L4 hạ về L2 (AI chỉ soạn, người có thẩm quyền xác nhận). Thực thi ở backend/service, không chỉ ẩn nút ở frontend | — | SRS (authz), Architecture, API, DB, Test | CDA | Đã đóng |
| D-10 | Kill switch: xử lý tác vụ đang chờ/đang chạy/retry/định kỳ | Q-26, D-09, D-26 | CONFIRMED — `CDA_DIRECTIVE` (K1–K6) | Nguyên tắc do CDA nêu đã được ghi nhận (mục 3.1.1): kiểm tra ở mọi cổng ghi kể cả retry; chưa ghi → bản nháp L2, đã ghi → giữ nguyên; tạm dừng lịch định kỳ; tắt kill switch không tự thực thi bản nháp; review theo permission, tài chính theo quyền duyệt tài chính; audit event + thông báo người khởi tạo; không xóa bản nháp, không tự chạy lại **Chốt 12/10/2026 (K1–K6):** toàn hệ thống; chặn ghi tự động tại gateway, job → bản nháp nếu đủ dữ liệu và an toàn, job chỉ hoàn tất sau khi lưu bền, retry không ghi; lịch bỏ qua → chu kỳ kế tiếp, không chạy bù, có log; reviewer có quyền tương ứng, tài chính không tự duyệt; 30 ngày → "cần rà soát", ADMIN cấu hình có audit; in-app ngay + nhắc hằng ngày. Thiết kế: ADR-008, Architecture §8.2. Diễn giải K2 (ghi đã có xác nhận của người vẫn thực hiện) là `ARCHITECTURE_DECISION` theo D-09. | Điểm mở (mục 3.1.3): phạm vi toàn hệ thống trong MVP; 30 ngày → "cần rà soát"; quy tắc thông báo, nhắc hạn; xử lý queue/retry Câu hỏi chuẩn hóa K1–K6: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md) mục 3; ADR-008. | SRS, Architecture, DB, Test | CDA | CDA xác nhận mục 3.1.3 |
| D-11 | Mức tự chủ tối đa MVP | Q-07, CON-02, BR-12 | CONFIRMED | L4 không thuộc MVP; tối đa L3. Kiến trúc có thể mở rộng nhưng không mô tả L4 là tính năng MVP đã triển khai hoặc đã duyệt | Mẫu UI L4 (UX §7.1) giữ ở trạng thái `DEFERRED` `[PROPOSED]` | PRD, UX, Test | CDA | Đã đóng |
| D-12 | Ghi dữ liệu tài chính | Q-07, CON-03, BR-08, BR-10 | CONFIRMED | L2: AI đề xuất/soạn; người có thẩm quyền xác nhận trước khi ghi chính thức. Việc người duyệt nội dung **không** ngầm cho phép hệ thống tự ghi sau đó, trừ khi quy trình cụ thể được duyệt | Ví dụ L3 "nhập hóa đơn đã duyệt" (UX §7.1) không áp dụng | SRS, API, UX, Test | CDA | Đã đóng |
| D-13 | Hoàn tác dữ liệu tài chính | Q-11, CON-12, FR-AUT-03 | CONFIRMED | Dùng bút toán đảo / điều chỉnh có liên kết giao dịch gốc; không xóa lịch sử giao dịch hay audit log để giả lập hoàn tác | — | DB, API, Test | CDA | Đã đóng |
| D-14 | Quy trình bút toán đảo | Q-11, GAP-07, D-12, D-13 | CONFIRMED — `CDA_DIRECTIVE` (F1–F7) · NEEDS_CONFIRMATION (người giữ `finance.period.manage`) | Nguyên tắc do CDA nêu đã được ghi nhận (mục 3.2.2): không sửa/xóa giao dịch đã ghi; người tạo không tự duyệt; đảo duyệt ở L2; MVP chỉ đảo toàn bộ (đảo một phần DEFERRED); không ghi vào kỳ đã khóa; liên kết gốc, idempotency key, version, audit; quyền qua permission trong phạm vi được cấp **Chốt 12/10/2026 (F1–F7):** kỳ báo cáo quản trị OPEN/CLOSED (không phải sổ cái); kỳ gốc đóng → đảo vào kỳ mở, không có kỳ mở → từ chối; người tạo rút lại → CANCELLED; không đảo bút toán đảo; AI soạn và nhập tay cùng quy trình, AI ghi riêng trong audit; không hạn mức tự suy đoán, không tự duyệt, không fallback; MVP: doanh thu, chi phí, số dư tiền mặt + đảo/điều chỉnh. Thiết kế: ADR-009, Database_Design §7. | Bảng chuyển trạng thái `DRAFT → PENDING_APPROVAL → POSTED → REVERSED`, `REJECTED`, `CANCELLED` (mục 3.2.1); ghi đảo vào kỳ đang mở (mục 3.2.3); 7 câu hỏi mở (mục 3.2.4) Câu hỏi chuẩn hóa F1–F7: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md) mục 4; ADR-009. | DB, API, SRS, ADR, Test | CDA | CDA duyệt mục 3.2.1, 3.2.3 và trả lời 3.2.4 |
| D-15 | Xóa giao dịch tài chính | CON-17 | CONFIRMED (phân loại) | Phát hiện `DELETE` cứng là `[LEGACY FINDING — A-EMS]`, không phải lỗi AI-EOS, không yêu cầu sửa hay tái sử dụng code A-EMS. **Kiểm soát thiết kế cho AI-EOS** (hệ quả trực tiếp của D-13): không cung cấp thao tác xóa vật lý giao dịch tài chính đã ghi; chỉ hủy (khi chưa ghi) hoặc đảo (khi đã ghi) | Phạm vi "giao dịch tài chính" cụ thể xác định ở SRS 2B `[CẦN XÁC NHẬN]` | SRS, API, DB, Test | CDA | Đã đóng phần phân loại; phạm vi entity đóng ở 2B |
| D-16 | Danh sách trường trọng yếu, ngưỡng giá trị autonomy, ngưỡng sinh trắc học | GAP-08, Q-07 | NEEDS_CONFIRMATION (TB) | Không tự đặt. Nguồn chỉ có ví dụ (số tiền, số tài khoản, MST, lương, giá trị hợp đồng; "5 triệu") **Mặc định an toàn 12/10/2026 (`ARCHITECTURE_DECISION`):** mọi trường tiền là trọng yếu; tự ghi tắt; không có hạn mức. | Cấu hình được; mặc định "mọi trường kiểu tiền là trọng yếu" `[PROPOSED]` | SRS, DB (cấu hình), Test | CDA | CDA cung cấp danh sách/ngưỡng |
| D-17 | Nhập hóa đơn/biên lai | Q-08, CON-06, US-DC-009, FR-DCS-03, BR-19 | CONFIRMED | Phase 2, không thuộc nghiệm thu MVP | — | PRD, Test (loại khỏi AC MVP) | CDA | Đã đóng |
| D-18 | Email forwarding | Q-08, CON-05, C6, US-DC-012 | CONFIRMED | Phase 2, không thuộc nghiệm thu MVP; luồng F2 bỏ nhánh email ở MVP | — | PRD, UX Flows | CDA | Đã đóng |
| D-19 | Module hóa đơn thủ công có sẵn trong finance A-EMS | D-17 | CONFIRMED — không áp dụng | Bản 0.1 hỏi về module hóa đơn của A-EMS. Theo D-04, D-05 câu hỏi không còn áp dụng. Phạm vi hóa đơn của AI-EOS chỉ theo D-17 | — | — | CDA | Đã đóng |
| D-20 | Tài liệu chuẩn cho chỉ số "review ≤ 60 giây" (MET-13 dùng hóa đơn) | CON-06, MET-04, MET-13 | NEEDS_CONFIRMATION (TB) | — | Đo MET-04 trên loại tài liệu MVP (biên bản họp, báo cáo KPI); MET-13 chuyển `DEFERRED` sang Phase 2 cùng hóa đơn `[PROPOSED]` | PRD, Test | CDA | CDA xác nhận |
| D-21 | Ma trận vai trò | Q-09, CON-13, GAP-03 | CONFIRMED — `CDA_DIRECTIVE` (R1–R8) · NEEDS_CONFIRMATION (R6: người giữ quyền dữ liệu nhân sự nhạy cảm) | Năm role nền tảng đề xuất: `ADMIN`, `CEO`, `CFO`, `MANAGER`, `EMPLOYEE`; Reviewer là permission/assignment. Không phải baseline **Chốt 12/10/2026 (R1–R8):** 5 role; Reviewer là assignment; CEO không duyệt tài chính mặc định; ADMIN xem audit quản trị, CEO xem audit nghiệp vụ; ADMIN không đọc dữ liệu nghiệp vụ, import nhân sự giới hạn; quyền tài chính theo assignment; quyền `hr.*` riêng, chưa giao cho role nào; nhiều role/tài khoản trừ `ADMIN`+`CFO`; autonomy có trần cứng. Ma trận permission: Architecture §6 (`ARCHITECTURE_DECISION` hiện thực R1–R8). **Chỉ đạo 12/10/2026 về R6:** tiếp tục deny mặc định; tách `hr.profile.read`, `hr.salary.read`, `hr.import`, `hr.export`, `pii.unmask`; không cấp theo tên role. | Mục 4: tách role, permission, assignment; năm nhóm quyền; `ADMIN` không mặc định duyệt tài chính, `CFO` không quản trị hệ thống; permission thiếu căn cứ gắn `[CẦN XÁC NHẬN]` Câu hỏi chuẩn hóa R1–R8: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md) mục 5; ADR-007. | SRS (authz), API, DB, Test | CDA | CDA duyệt mục 4 và trả lời 4.5 |
| D-22 | Gán role và khởi tạo tài khoản quản trị | CON-18, D-21, D-30 | CONFIRMED — `CDA_DIRECTIVE` (A1–A6) | Phát hiện đăng ký public tự chọn role là `[LEGACY FINDING — A-EMS]`, không phải lỗi AI-EOS (phân loại này giữ nguyên từ 0.2). Nguyên tắc do CDA nêu đã được ghi nhận (mục 3.3.1): không tự chọn/nâng role; chỉ `ADMIN` đổi role qua backend có xác thực; audit mọi thay đổi role; `ADMIN` đầu tiên qua bootstrap an toàn, không qua self-registration; backend thực thi authorization **Chốt 12/10/2026 (A1–A6):** ADMIN tạo tài khoản + lời mời dùng một lần (hash, hạn, thu hồi), không mật khẩu mặc định; bootstrap CLI một lần, MFA bắt buộc, audit BOOTSTRAP; đổi role: step-up, lý do, audit, thu hồi session; chặn gỡ ADMIN cuối và tự nâng quyền; khuyến nghị ≥ 2 ADMIN; khôi phục qua CLI. Thiết kế: ADR-006, Architecture §5. | Cơ chế bootstrap, chặn gỡ `ADMIN` cuối cùng (mục 3.3.2) Câu hỏi chuẩn hóa A1–A6: [Pre2C_Decision_Proposals.md](Pre2C_Decision_Proposals.md) mục 6; ADR-006. | SRS, API, ADR auth, Test | CDA | CDA xác nhận mục 3.3 |
| D-23 | Danh sách domain (22 vs 28) và 8 mục IA | Q-10, CON-01, GAP-17 | NEEDS_CONFIRMATION (TB) | — | Dùng 22 domain + Procurement/Contract (P1) đến khi có danh sách 28 `[PROPOSED]` | PRD, UX Flows | CDA | CDA cung cấp danh sách |
| D-24 | KPI/OKR, Task, CEO Briefing | GAP-04, SC-04, SC-05 | CONFIRMED (cách xử lý) | Giữ ở P0, không loại. Chỉ tạo user story khung, gắn `[CẦN XÁC NHẬN]` cho mọi nội dung không có nguồn. Không tự tạo KPI mục tiêu, công thức KPI, SLA, ngưỡng cảnh báo, cam kết hiệu quả; không tự quyết luồng phê duyệt hay quyền ghi. Tách phần có nguồn khỏi phần đề xuất. Acceptance criteria chi tiết chỉ khi có căn cứ; nếu không, ghi câu hỏi cần xác nhận | Finance Lite, Sales Lite (SC-04, SC-05) cũng thiếu chi tiết → áp dụng cùng cách xử lý `[PROPOSED]` | PRD, SRS, DB, API | CDA | Đã đóng cách xử lý; nội dung chi tiết chờ CDA bổ sung |
| D-25 | Audit log | FR-DC-05, BR-04, FR-DCS-06, D-13 | CONFIRMED — `ARCHITECTURE_DECISION` | Yêu cầu có nguồn; thiết kế chưa có Chốt bằng ADR-010. | Audit append-only cho hành động người và AI: actor, loại actor, autonomy level, giá trị trước/sau, lý do, thời điểm, correlation id; không cho sửa/xóa qua ứng dụng; ADR ở 2C | DB, Architecture, Test | CDA | Duyệt ADR ở 2C |
| D-26 | Tool Registry, approval, hàng đợi tác vụ AI | BR-04, BR-09, FR-DCS-05, D-09, D-10 | CONFIRMED — `ARCHITECTURE_DECISION` | Yêu cầu có nguồn; thiết kế chưa có Chốt bằng ADR-008. | Cổng ghi duy nhất qua Tool Registry, kiểm tra quyền + autonomy + kill switch tại đây; ADR ở 2C | Architecture, DB, API | CDA | Duyệt ADR ở 2C |
| D-27 | Mobile: PWA hay native; sinh trắc học, offline | Q-12, CON-08 | CONFIRMED (PWA) — `ARCHITECTURE_DECISION` · NEEDS_CONFIRMATION (sinh trắc học, offline, camera nền) | — PWA chốt ở ADR-003. MVP **không cam kết** push ngoài in-app, camera chạy nền, sinh trắc học, ngoại tuyến (giới hạn nền tảng, đặc biệt iOS — yêu cầu CDA 12/10/2026 §7). | PWA cho MVP (UX §9.1); sinh trắc học và offline `DEFERRED` sau MVP `[PROPOSED]` | PRD, UX, Architecture | CDA | CDA xác nhận |
| D-28 | Bộ chỉ số sức khỏe MVP | Q-13, CON-09, GAP-16 | NEEDS_CONFIRMATION (TB) | — | Dùng 4 ô mặc định UX §6.1 (doanh thu, dòng tiền, OKR, task trễ); công thức và ngưỡng theo BRD §4.3 là "gợi ý", chờ CDA chốt `[PROPOSED]` | PRD, SRS | CDA | CDA xác nhận |
| D-29 | Ngưỡng độ tin cậy hiển thị vs định tuyến | Q-14, CON-07 | NEEDS_CONFIRMATION (TB) | — Schema tách hai cấu hình (Database_Design §6); giá trị chờ CDA. | Hai cấu hình tách biệt: ngưỡng hiển thị (mặc định 90/60, UX §6.2) và ngưỡng tự ghi (theo loại tài liệu + theo trường, BRD FR-DC-15) `[PROPOSED]` | SRS, DB | CDA | CDA xác nhận |
| D-30 | Xác thực: SSO, MFA, cách tạo tài khoản | Q-15, GAP-09, D-22 | CONFIRMED (đăng nhập nội bộ + MFA bắt buộc cho ADMIN) — `ARCHITECTURE_DECISION` · DEFERRED (SSO/OIDC; MFA cho role khác) | Nguồn không có yêu cầu xác thực ADR-006; interface OIDC dự phòng. | MFA bắt buộc cho `ADMIN` `[PROPOSED]`; SSO chờ CDA | SRS, Architecture | CDA | CDA xác nhận |
| D-31 | Tích hợp lịch và tích hợp ngoài trong MVP | Q-16, GAP-10 | NEEDS_CONFIRMATION (TB) | — | MVP không tích hợp lịch ngoài; "đồng bộ lịch" (UC-06, F1) dùng lịch nội bộ `[PROPOSED]` | PRD, API | CDA | CDA xác nhận |
| D-32 | Kênh thông báo | Q-17, GAP-11 | CONFIRMED (in-app) — `CDA_DIRECTIVE` K6 · DEFERRED (email, push, Zalo/Slack/Teams) | — Kênh ngoài là phần mở rộng, không giả định đã cấu hình. | MVP: in-app (+ push PWA nếu D-27 chọn PWA); Zalo/Slack/Teams Phase 2 `[PROPOSED]` | PRD, Architecture | CDA | CDA xác nhận |
| D-33 | Màn ngoài 4 việc cốt lõi trên mobile | Q-21, CON-14 | NEEDS_CONFIRMATION (Thấp) | — | Chỉ đọc (UX §9.1) `[PROPOSED]` | UX Flows | CDA | CDA xác nhận |
| D-34 | Sửa tham chiếu CON-10, CON-11 | Q-22 | PROPOSED | — | Theo BRD §6.1: 5 kênh MVP; US-PERF-001 và UC-02 là P1 | PRD, UX Flows | CDA | Không phản đối khi review |
| D-35 | Thương hiệu, xưng hô AI, người tham gia test | Q-18, Q-19, Q-20 | DEFERRED | — | Token trung tính; xưng hô mặc định "bạn", cấu hình được (UX-39) `[PROPOSED]` | Design system, Test Plan | CDA | Trước giai đoạn hi-fi/usability test |
| D-36 | Vị trí tài liệu và CLAUDE.md | CON-19 | PROPOSED (Thấp) | Không commit; không khôi phục/xóa `CyEyes/A-EMS` | Tài liệu ở `AI-EOS/docs/`; `CLAUDE.md` đặt ở `AI-EOS/`; không trỏ tới A-EMS | CLAUDE.md | CDA | Không phản đối khi review |
| D-37 | AMD-01: gửi duyệt giao dịch tài chính chỉ khi kỳ của ngày giao dịch đang mở | SRS §15.2, Q-40, D-14 | CONFIRMED — `CDA` (duyệt AMD-01, 12/10/2026) | Gửi duyệt yêu cầu kỳ `OPEN`; không tự đổi ngày, không tự chuyển kỳ, không bỏ qua phê duyệt. Nếu kỳ bị đóng khi giao dịch còn chờ duyệt: chuyển sang trạng thái tạm giữ có lý do rõ ràng, thông báo, yêu cầu người có thẩm quyền xử lý (rút lại/từ chối) | Phòng ngừa chính: không cho khóa kỳ khi còn giao dịch chờ duyệt (đã có); tạm giữ `ON_HOLD` là lớp phòng thủ (`ARCHITECTURE_DECISION`, ADR-009 amendment 1) | ADR-009, SRS-FIN-05/16/17, API-FIN-08/10, Database_Design §7, FL-11, TEST_Plan | CDA | Đã đóng |
| D-38 | AMD-02: phân loại lịch Briefing và tác vụ trong queue khi kill switch bật | SRS §15.2, D-10, Q-36 | CONFIRMED — `CDA` (duyệt AMD-02 theo phiên bản 12/10/2026) | Quản lý lịch Briefing là cấu hình có authorization + audit; khi kill switch bật **không** khởi chạy/tiếp tục tác vụ AI tạo nội dung Briefing mới, không ghi nội dung mới; tác vụ điều phối không tạo kết quả nghiệp vụ được phép tiếp tục nếu được xác định rõ; không phân loại lại thao tác ghi để né kill switch | Phân loại job cố định trong code: `ORCHESTRATION` / `AI_CONTENT` / `BUSINESS_WRITE` (`ARCHITECTURE_DECISION`, ADR-005 amendment 1, ADR-008 amendment 1). **Thay thế** phiên bản AMD-02 do người phân tích đề xuất (Briefing vẫn chạy khi kill switch bật) | ADR-005, ADR-008, SRS-BRF-11, SRS-AIC-06, API-INS-03, Architecture §6, §8.2, TEST_Plan | CDA | Đã đóng |
| D-39 | Mặc định an toàn cho Stage 2D đối với Q-28, Q-29, Q-36, Q-37 | Q-28, Q-29, Q-36, Q-37 | CONFIRMED — `CDA_DIRECTIVE` (mặc định tạm thời cho lập kế hoạch, 12/10/2026). **Các câu hỏi nghiệp vụ vẫn NEEDS_CONFIRMATION** | Q-28: mục tiêu mới ở `DRAFT`, kích hoạt cần thao tác rõ ràng của người có quyền. Q-29: không tính % đạt. Q-36: Briefing chỉ hiển thị nội dung có nguồn truy vết được; ẩn khối chưa đủ căn cứ. Q-37: 4 ô chỉ số vẫn `PROPOSED`, không hiển thị như chỉ số chính thức, không dùng làm cơ sở cảnh báo | Người giữ quyền kích hoạt mục tiêu: permission `goals.activate` giao qua assignment, chưa có quyền nền (chờ Q-28) | SRS-GOAL-04, SRS-BRF-05/07/09, Implementation_Plan | CDA | Đóng khi CDA trả lời Q-28, Q-29, Q-36, Q-37 |
| D-40 | Sales Pipeline Lite trong triển khai MVP | Q-38, SC-05 | CONFIRMED — `CDA_DIRECTIVE` (12/10/2026): chưa thuộc phạm vi **triển khai** MVP | Không thiết kế nghiệp vụ, forecast, pipeline, KPI, API dựa trên tên module. Trạng thái SC-05 trong traceability **giữ nguyên** (`NEEDS_CONFIRMATION`) vì BRD xếp P0; chỉ việc triển khai bị chặn | — | Implementation_Plan (BLOCKED), API-SALES-01 giữ `SKELETON` | CDA | Khi CDA cung cấp đặc tả (Q-38) hoặc loại SC-05 khỏi MVP |
| D-41 | Toolchain kiểm tra và CI cho T-002 | T-001 review, T-002, ADR-003, ADR-013, Q-43…Q-47 | CONFIRMED — `CDA_DIRECTIVE` (12/10/2026) cho nguyên tắc; phiên bản cụ thể `PROPOSED` (Implementation_Plan §11). **Bổ sung 0.9:** CONFIRMED — `CDA_DIRECTIVE` (12/10/2026) cho Q-43, Q-45, Q-46, Q-47 và hướng toolchain; phiên bản TypeScript/toolchain và PostgreSQL 18 chỉ xác nhận sau kiểm thử thực tế. **Đóng 12/10/2026:** mọi điều kiện thực thi đã đạt (xem cột "Điều kiện đóng") | (1) Lint frontend: ESLint + typescript-eslint + luật React Hooks + Prettier; TypeScript dùng phiên bản typescript-eslint hỗ trợ chính thức (đánh giá 6.0.3), không dùng TS 7 khi không tương thích. (2) Không tự cài Docker/PostgreSQL hay đổi hệ thống; test CSDL chạy trên CI có PostgreSQL service; thiếu `AIEOS_TEST_DATABASE_URL` khi CI yêu cầu → test **thất bại**, không skip; test PostgreSQL ghi "chưa xác minh tại local" đến khi có bằng chứng. (3) `scripts/ci.sh` là nguồn lệnh thống nhất; phân biệt script local, workflow CI thực tế, branch protection; chưa có remote → không tuyên bố CI chặn merge. (4) Chỉ nâng mức Node tối thiểu khi dependency được chọn yêu cầu; nếu là 22.22.2 thì đồng bộ `.nvmrc`, `package.json`, `.npmrc`, tài liệu, CI. (5) Tạm cấm `ai`, `jobs`, `capture` import trực tiếp module nghiệp vụ, kể cả API đọc — giả định `[CẦN XÁC NHẬN]` (Q-43); không sửa Architecture/ADR khi chưa có amendment. **Bổ sung 0.9 (CDA 12/10/2026):** (6) Toolchain frontend: TypeScript 6.0.3 + ESLint 10 + typescript-eslint; phiên bản cụ thể chỉ được xác nhận sau khi cài và chạy thành công — resolve lockfile không đủ làm bằng chứng. (7) Q-43: cấm `ai`, `jobs`, `capture` import trực tiếp `goals`, `work`, `org`, `knowledge`, `finance`, kể cả API đọc (contract C2, Implementation_Plan §11.4). (8) Q-45: tách task nền tảng frontend ADR-003 thành task riêng T-012, không mở rộng T-111. (9) Q-46: GitHub Actions. (10) Q-47: PostgreSQL 18, có điều kiện xác minh tương thích thực tế | — | Implementation_Plan §4 (T-012), §11, T-002, frontend toolchain | CDA | Đóng phần nguyên tắc và Q-43, Q-45, Q-46, Q-47; điều kiện thực thi: phiên bản toolchain chốt khi T-002 cài và chạy thành công; PostgreSQL 18 chốt khi smoke test chạy thật trên GitHub Actions; "CI chặn merge" chỉ khi có remote, lần chạy workflow thật và branch protection được xác minh. **Đã đạt (12/10/2026):** (a) toolchain Implementation_Plan §11.1 cài và chạy thành công (T-002, Implementation_Plan §10); (b) PostgreSQL 18: run `38257197546` (commit `318689c`, image `postgres:18`, pytest 14 passed, 0 skipped); (c) remote `hovikhanh/AI-EOS`, branch protection `main` đọc lại từ GitHub (required check `ci`, GitHub Actions app 15368, `enforce_admins: true`, bắt buộc PR); PR #2 CI đỏ bị chặn merge (HTTP 405 `Required status check "ci" is failing.`); PR #3 merge sau khi CI xanh; run `38262327635` `success` trên `main` commit `b7ba32d` |

---

## 3. Chi tiết các đề xuất mở

> **Cập nhật 0.5:** các điểm mở ở 3.1.3, 3.2.4, 3.3.2 và 4.5 đã được chốt bằng K1–K6, F1–F7, A1–A6, R1–R8 (`CDA_DIRECTIVE`, 12/10/2026). Nội dung dưới đây giữ nguyên làm lịch sử; thiết kế hiện hành ở ADR-006…ADR-009 và Architecture §5–§8. Còn mở: người giữ `finance.period.manage` và quyền dữ liệu nhân sự nhạy cảm (R6).

Quy ước trong mục này: **[CDA nêu]** = nguyên tắc do chủ dự án đưa ra ở vòng review 2A (12/10/2026), được ghi nhận nhưng quyết định tổng thể vẫn `PROPOSED` đến khi các điểm mở được xác nhận · `[PROPOSED]` = đề xuất của người phân tích, chưa được xác nhận · `[CẦN XÁC NHẬN]` = chưa có căn cứ.

### 3.1. D-10 — Kill switch và tác vụ đang xử lý

**3.1.1. Nguyên tắc [CDA nêu]**
1. Backend kiểm tra trạng thái kill switch ở **mọi cổng ghi dữ liệu**, ngay trước khi ghi, ở mọi lần thực thi kể cả retry. Không dựa vào trạng thái lúc tác vụ được tạo/xếp hàng, không dựa vào frontend.
2. Tác vụ **chưa ghi** dữ liệu được chuyển thành bản nháp L2; tác vụ **đã ghi** giữ nguyên (không tự xóa, không tự đảo chỉ vì kill switch bật).
3. Lịch định kỳ có khả năng tạo hành động ghi tự động bị tạm dừng.
4. Khi tắt kill switch, bản nháp **không** tự thực thi lại.
5. Bản nháp phải được review bởi người có permission phù hợp với loại hành động.
6. Bản nháp liên quan tài chính tuân theo quyền duyệt tài chính (D-12, D-14).
7. Mọi lần bật/tắt và mọi chuyển tác vụ sang bản nháp đều sinh audit event; người khởi tạo tác vụ được thông báo.
8. Bản nháp không bị xóa khi quá hạn; tác vụ không bao giờ tự chạy lại.

**3.1.2. Xử lý theo trạng thái tác vụ (L3) khi kill switch bật**

| Trạng thái | Xử lý | Căn cứ |
| --- | --- | --- |
| Trong queue, chưa chạy | Khi worker lấy ra, cổng ghi chặn thực thi tự động → bản nháp L2 | [CDA nêu] 1, 2 |
| Đang chạy, chưa ghi | Phần đọc/soạn được hoàn tất; lệnh ghi bị chặn tại cổng ghi → bản nháp L2 | [CDA nêu] 1, 2 |
| Đã ghi trước thời điểm bật | Giữ nguyên; hoàn tác theo chính sách thường (BR-11, D-13) | [CDA nêu] 2 |
| Retry | Mỗi lần retry đi qua cổng ghi như lần đầu; không có đường retry bỏ qua kiểm tra | [CDA nêu] 1 |
| Lịch định kỳ có thể tạo hành động ghi | Tạm dừng; không chạy bù khi tắt kill switch | [CDA nêu] 3, 4 |
| Bản nháp L2 tạo trong thời gian bật | Giữ ở trạng thái chờ review; tắt kill switch không thực thi chúng | [CDA nêu] 4 |
| Hành động L0/L1 | Không bị ảnh hưởng | BRD §4.2 (L0/L1 không ghi) |

**3.1.3. Đề xuất chưa được xác nhận `[PROPOSED]`**

| # | Đề xuất | Ghi chú |
| --- | --- | --- |
| a | Phạm vi kill switch trong MVP: **một công tắc toàn hệ thống** (BRD §4.2 nói "toàn bộ"); phạm vi theo module/agent để sau MVP | Cần CDA xác nhận |
| b | Bản nháp sinh do kill switch sau **30 ngày** chưa xử lý chuyển sang trạng thái "cần rà soát" (không xóa, không thực thi) | Con số 30 ngày là đề xuất, không có trong nguồn |
| c | Thông báo: in-app cho người khởi tạo ngay khi tác vụ chuyển sang bản nháp; nhắc người review theo SLA hàng chờ (FR-DC-21) | Kênh thông báo phụ thuộc D-32; giá trị SLA chưa có (GAP-18) |
| d | Queue/retry: thông điệp đã bị chặn tại cổng ghi được xác nhận (ack) sau khi bản nháp lưu thành công, để không bị retry lại thành hành động ghi; nếu lưu bản nháp lỗi thì retry chỉ được tạo bản nháp, không được ghi | Chi tiết kỹ thuật thể hiện trong ADR ở 2C |
| e | Kill switch là trạng thái lưu bền, mọi worker đọc cùng một nguồn | Chi tiết kỹ thuật thể hiện trong ADR ở 2C |

**3.1.4. Hệ quả**
- Mọi hành động ghi của AI phải đi qua một cổng duy nhất (trùng BR-04, D-26).
- Cần mô hình dữ liệu cho bản nháp hành động và trạng thái kill switch.
- Hàng chờ review L2 có thể tăng đột ngột sau khi bật.

**3.1.5. Điều kiện đóng D-10:** CDA xác nhận 3.1.3 (a)–(e).

### 3.2. D-14 — Quy trình bút toán đảo

**3.2.1. Trạng thái giao dịch tài chính `[PROPOSED]`**

```text
DRAFT → PENDING_APPROVAL → POSTED → REVERSED
DRAFT → CANCELLED
PENDING_APPROVAL → REJECTED
```

| Từ | Đến | Ai | Điều kiện | Căn cứ |
| --- | --- | --- | --- | --- |
| (mới) | `DRAFT` | Người dùng có `finance.submit`, hoặc AI soạn thay người dùng | Có idempotency key | D-12, [CDA nêu] |
| `DRAFT` | `PENDING_APPROVAL` | Người tạo | Dữ liệu hợp lệ (FR-DC-01, FR-DC-14) | D-12 |
| `DRAFT` | `CANCELLED` | Người tạo `[CẦN XÁC NHẬN: người khác có được hủy không]` | Chưa có hiệu lực tài chính; giữ bản ghi, không xóa | [CDA nêu] |
| `PENDING_APPROVAL` | `POSTED` | Người có `finance.approve` trong phạm vi được cấp, **khác người tạo** | Kỳ kế toán của ngày ghi đang mở; version khớp; idempotency key chưa dùng | [CDA nêu] |
| `PENDING_APPROVAL` | `REJECTED` | Người có `finance.approve` trong phạm vi được cấp, khác người tạo | Lý do bắt buộc (FR-DC-05) | [CDA nêu], FR-DC-05 |
| `POSTED` | `REVERSED` | Hệ thống, tự động trong cùng transaction khi bút toán đảo liên kết chuyển `POSTED` | Bút toán gốc chưa từng bị đảo | [CDA nêu] |

Trạng thái kết thúc: `REJECTED`, `CANCELLED`, `REVERSED`. Nội dung tài chính của giao dịch `POSTED`/`REVERSED` không bao giờ bị sửa; chỉ trạng thái và liên kết thay đổi.

**3.2.2. Nguyên tắc [CDA nêu]**
1. Không xóa hoặc sửa lịch sử giao dịch gốc đã ghi.
2. Người tạo không được tự duyệt bút toán của chính mình.
3. Bút toán đảo là một giao dịch mới, duyệt ở L2, theo cùng quy trình `DRAFT → PENDING_APPROVAL → POSTED`, bắt buộc liên kết giao dịch gốc.
4. MVP chỉ hỗ trợ **đảo toàn bộ**; đảo một phần `DEFERRED`.
5. Không ghi vào kỳ kế toán đã khóa.
6. Mỗi giao dịch có idempotency key; kiểm soát concurrency bằng version; mỗi giao dịch gốc chỉ đảo một lần; audit trail cho mọi chuyển trạng thái.
7. Quyền duyệt kiểm soát qua permission; `CFO` hoặc người được ủy quyền chỉ có quyền trong phạm vi đã cấp.

**3.2.3. Đề xuất xử lý kỳ kế toán đã khóa `[PROPOSED]`**
Nếu giao dịch gốc thuộc kỳ đã khóa, bút toán đảo được ghi với ngày hạch toán trong **kỳ đang mở**, giữ liên kết tới giao dịch gốc và kỳ gốc; kỳ đã khóa không bị thay đổi. Phương án này phải được thể hiện trong ADR hoặc tài liệu nghiệp vụ (SRS) trước khi triển khai.

**3.2.4. Còn cần CDA xác nhận**
1. AI-EOS có tự quản lý kỳ kế toán (mở/khóa kỳ) hay nhận trạng thái kỳ từ phần mềm kế toán bên ngoài? (BR-18: AI-EOS không thay phần mềm kế toán.) Ai có quyền khóa kỳ?
2. Phương án 3.2.3 cho kỳ đã khóa.
3. `PENDING_APPROVAL` có được trả về `DRAFT` để sửa, hoặc người tạo rút lại (`CANCELLED`) không?
4. Đảo một bút toán đảo (khôi phục bản gốc) có được phép không, xử lý thế nào?
5. Giao dịch do AI soạn và giao dịch do người nhập tay có cùng quy trình duyệt không?
6. Phạm vi ủy quyền duyệt tài chính được định nghĩa theo tiêu chí nào (đơn vị, loại giao dịch, hạn mức)? Không tự đặt hạn mức (D-16).
7. Danh sách entity được coi là "giao dịch tài chính" trong MVP (liên quan Finance Lite, SC-04, D-24).

**3.2.5. Điều kiện đóng D-14:** CDA trả lời 3.2.4 và duyệt bảng 3.2.1.

### 3.3. D-22 — Gán role và tài khoản quản trị

**3.3.1. Nguyên tắc bảo mật [CDA nêu]**
1. Người dùng không được tự chọn hoặc tự nâng role.
2. Chỉ `ADMIN` được thay đổi role, qua API backend có xác thực.
3. Mọi thay đổi role có audit log.
4. Tài khoản `ADMIN` đầu tiên được khởi tạo bằng cơ chế bootstrap an toàn, không qua public self-registration.
5. Backend là nơi thực thi authorization; frontend chỉ ẩn/hiện giao diện.

**3.3.2. Đề xuất chưa được xác nhận `[PROPOSED]`**
- Bootstrap: lệnh khởi tạo một lần chạy trong môi trường triển khai (Docker Compose), nhận thông tin qua biến môi trường/secret, từ chối chạy nếu đã có `ADMIN`; mật khẩu tạm buộc đổi ở lần đăng nhập đầu. Chi tiết trong ADR authentication ở 2C.
- Không cho phép gỡ `ADMIN` cuối cùng của hệ thống.
- `ADMIN` có được tự thay đổi role của chính mình không: `[CẦN XÁC NHẬN]`.
- Cách tạo tài khoản người dùng thường (Admin tạo, mời qua email, SSO): phụ thuộc D-30 `[CẦN XÁC NHẬN]`.

**3.3.3. Điều kiện đóng D-22:** CDA xác nhận 3.3.1 và 3.3.2.

### 3.4. D-06 — Phạm vi ADR công nghệ ở Stage 2C

Stack chưa được xác nhận. Ở 2C, mỗi hạng mục dưới đây có một ADR `PROPOSED` nêu ít nhất hai phương án, tiêu chí so sánh và khuyến nghị; **không chốt stack trước khi CDA duyệt**. Không dùng stack A-EMS cũ làm baseline.

| Hạng mục ADR | Nội dung cần quyết | Liên quan |
| --- | --- | --- |
| Frontend | Framework web, PWA (D-27), thư viện UI (UX §8.3, ASM-04), i18n (NFR-05) | UX §8–§9 |
| Backend | Ngôn ngữ/framework, cấu trúc module/service | BR-04, D-26 |
| Database | CSDL quan hệ, lưu file gốc (C3, SEC-DC-05), tìm kiếm tài liệu | FR-DCS-06, D-14, D-25 |
| Queue / job | Hàng đợi xử lý tài liệu bất đồng bộ (NFR-01), tác vụ AI, retry, lịch định kỳ | D-10, NFR-01, NFR-02 |
| Authentication / authorization | Cơ chế đăng nhập, phiên, MFA, RBAC + permission + assignment, bootstrap Admin | D-21, D-22, D-30 |
| LLM / OCR adapter | Interface, provider ứng viên, định tuyến theo phân loại dữ liệu | D-07, D-08, SEC-DC-04 |
| Logging / monitoring | Log có cấu trúc, audit tách khỏi log kỹ thuật, theo dõi chi phí AI | D-25, FR-AIQ-05, MET-05 |
| Testing | Unit, integration, API, E2E, kiểm thử bảo mật/authorization | Test Plan 2D |

**Tiêu chí chung:** chi phí thấp, mã nguồn mở, chạy được trên Local/Docker Compose (D-03), phù hợp dữ liệu tiếng Việt, bảo mật và quyền riêng tư, tài nguyên phần cứng cần thiết, mức độ phổ biến/bảo trì.

### 3.5. Q-48 — Vị trí mã hạ tầng dùng chung (hồ sơ để CDA quyết định)

Trạng thái: **NEEDS_CONFIRMATION**. Mục này chỉ là hồ sơ phương án; chưa phương án nào được áp dụng vào code. T-004, T-006 không bắt đầu cho tới khi CDA chọn.

**3.5.1. Phạm vi câu hỏi**

| Trách nhiệm | Task | Thiết kế | Nơi dùng |
| --- | --- | --- | --- |
| Loader cấu hình và secret (Implementation_Plan §7), dừng tiến trình khi thiếu secret | T-004 | ADR-006, ADR-011 | api, worker, lệnh migration; `providers` (URL, khóa API), `storage` (đường dẫn volume), `identity` (thời hạn session, khóa TOTP) |
| Engine/session SQLAlchemy, cấu hình Alembic, 3 role CSDL | T-005 | Database_Design §2, §10 | mọi module có bảng |
| Log JSON, correlation ID, bộ lọc secret, `/health/live`, `/health/ready` (CSDL, storage, migration) | T-006 | ADR-012 | api, worker |
| `problem+json`, CSRF + `Origin`, idempotency store, `ETag`/`If-Match`, rate limit | T-007 | API_Specification §1 | mọi router |
| Gốc lắp ráp: tạo ứng dụng FastAPI gắn router của mọi module, tiến trình worker, lệnh CLI | T-006, T-009, T-106 | ADR-001, ADR-002 | — (phải import `api` của mọi module) |

Ràng buộc hiện hành:
- Architecture §3 có 17 module; test cấu trúc T-001 đọc chính bảng này, nên thêm module = thêm dòng vào bảng (sửa Architecture, cần amendment). ADR-001 liệt kê 15 module (Q-44) — nên gộp chung một amendment.
- Contract C1 (Implementation_Plan §11.4): `providers` không import module `aieos` nào, diễn giải chặt `[CẦN XÁC NHẬN]`. Nếu cấu hình/log nằm trong một module `aieos`, `providers` không dùng được khi chưa nới C1.
- D-25: log kỹ thuật tách khỏi audit nghiệp vụ → không đặt logging vào `audit`.
- Hạ tầng phải là "lá" (không import module nghiệp vụ), còn gốc lắp ráp phải import mọi module → hai vai trò này không nằm chung một module nếu không muốn có vòng phụ thuộc.

**3.5.2. Phương án**

| # | Phương án | Ưu điểm | Nhược điểm |
| --- | --- | --- | --- |
| 1 | Thêm **hai** module vào Architecture §3: module hạ tầng (lá: cấu hình, CSDL, log/health, HTTP) và module gốc lắp ráp (import `<module>.api` của mọi module, không module nào import ngược). Thêm contract: hạ tầng không import module nào; không module nào import gốc lắp ráp; nới C1 cho `providers` → hạ tầng | Trách nhiệm rõ; contract kiểm tra tự động như các module khác; test cấu trúc tự nhận module mới; không vòng phụ thuộc | Cần amendment Architecture §3 + ADR-001; thêm 2 contract; phải quyết định ngoại lệ C1 |
| 2 | Thêm **một** module hạ tầng; gốc lắp ráp đặt ngoài package `aieos` (script entry-point) | Ít thay đổi bảng module hơn | Gốc lắp ráp nằm ngoài import-linter và test cấu trúc; vẫn cần amendment và quyết định C1 |
| 3 | Giao từng trách nhiệm cho module hiện có (vd. CSRF/session → `identity` theo ADR-006; health → `jobs`…) | Không thêm module | Cấu hình, engine CSDL, log không có module phù hợp; mọi module phụ thuộc `identity`/`jobs` → tăng coupling; `providers` vẫn vướng C1 |
| 4 | Package riêng ngoài `aieos` trong `backend/src` | Không phải sửa bảng §3 | Thoát khỏi import-linter (`root_package = "aieos"`) và test cấu trúc → ranh giới không được kiểm; vẫn là thay đổi kiến trúc cần CDA duyệt |

**3.5.3. Tác động lên task**

| Task | PA 1 | PA 2 | PA 3 | PA 4 |
| --- | --- | --- | --- | --- |
| T-004 | Làm được ngay sau quyết định | Như PA 1 | Cần chỉ định module cho cấu hình (chưa có ứng viên) | Làm được, ranh giới không kiểm |
| T-006 | Log/health ở hạ tầng; app FastAPI ở gốc lắp ráp | App ngoài `aieos` | Log/health phân tán | Như PA 1 nhưng ngoài contract |
| T-005 | Engine/session + Alembic ở hạ tầng (vẫn cần T-003, xem Q-49) | Như PA 1 | Không có module phù hợp | Như PA 1 |
| T-007 | Middleware/tiện ích HTTP ở hạ tầng; idempotency store là bảng của hạ tầng | Như PA 1 | CSRF ở `identity`, phần còn lại chưa có chỗ | Như PA 1 |

**3.5.4. CDA cần quyết định:** (1) phương án; (2) tên module (nếu thêm); (3) quy tắc phụ thuộc và contract import mới; (4) ngoại lệ C1 cho `providers`; (5) gộp với amendment ADR-001 (Q-44) hay không.

`PROPOSED` (đề xuất kỹ thuật, không phải quyết định): phương án 1 — là phương án duy nhất giữ mọi mã backend trong phạm vi kiểm tra tự động của ADR-001 mà không tạo vòng phụ thuộc.

### 3.6. Q-49 — T-003 (Docker Compose): công cụ chưa chọn và phụ thuộc chưa ghi

Trạng thái: **NEEDS_CONFIRMATION**. T-003 chưa bắt đầu.

- **Công cụ:** Architecture §9.1 chỉ ghi "mã nguồn mở" cho `proxy` và `scanner`; profile `llm` phụ thuộc D-08; profile `observability` là tùy chọn (ADR-012). Khác với T-605, hàng T-003 không có ghi chú "công cụ cụ thể chọn khi triển khai". Ứng viên chỉ xuất hiện dạng ví dụ trong `Pre2C_Decision_Proposals.md` (Nginx/Caddy cho file tĩnh, Ollama cho LLM local, Prometheus cho quan sát); scanner chưa có ứng viên nào được nêu.
- **Phụ thuộc chưa ghi:** DoD "`docker compose up` chạy đủ service" cần image `api` và `worker` chạy được, tức là cần ứng dụng FastAPI (T-006, đang chờ Q-48) và tiến trình worker (T-009). Cột "Phụ thuộc" của T-003 chỉ ghi T-001.
- **Môi trường:** máy phát triển hiện tại không có Docker; runner GitHub Actions có Docker.
- **Đường găng:** T-005 phụ thuộc T-003, trong khi CI đã có PostgreSQL 18 (Q-47) để chạy migration và test `db`.

CDA cần quyết định: (1) chọn công cụ proxy, scanner, runtime LLM, stack quan sát — hoặc cho phép chọn khi triển khai như T-605; (2) xử lý phụ thuộc `api`/`worker`: (a) thêm T-006, T-009 vào dependency của T-003, (b) tách T-003 thành phần hạ tầng (`proxy`, `db`, `scanner`, profile) làm trước và phần `api`/`worker` sau, hoặc (c) giữ nguyên; (3) GitHub Actions có được dùng làm bằng chứng `docker compose up` không; (4) T-005 có cần chờ T-003 không, hay chỉ cần PostgreSQL 18 của CI.

---

## 4. Ma trận vai trò `[PROPOSED — chưa phải baseline, chờ CDA duyệt (D-21)]`

> **Cập nhật 0.6:** D-21 đã được chốt ở 0.5 bằng R1–R8 (`CDA_DIRECTIVE`), trừ R6. Ma trận permission hiện hành là Architecture §6; nội dung mục này giữ nguyên làm lịch sử đề xuất.

Ma trận xây mới từ nguồn AI-EOS; không kế thừa role của A-EMS. Năm role nền tảng `ADMIN`, `CEO`, `CFO`, `MANAGER`, `EMPLOYEE` là đề xuất được CDA chấp nhận làm cơ sở thảo luận; toàn bộ ma trận vẫn `PROPOSED`.

### 4.1. Nguyên tắc

1. **Bốn khái niệm tách biệt:** *persona* (người dùng điển hình — UX §2.1); *role* (nhóm permission gán cho tài khoản); *permission* (quyền nguyên tử được backend kiểm tra); *assignment* (nhiệm vụ được giao theo tác vụ: hàng chờ review, chủ entity, phạm vi ủy quyền tài chính).
2. **Năm nhóm quyền:** đọc · ghi · duyệt · quản trị hệ thống · sử dụng AI.
3. **Least privilege, mặc định từ chối:** không có trong ma trận = không được phép.
4. **Tách quản trị hệ thống và quyền nghiệp vụ:** `ADMIN` **không** mặc định có quyền duyệt tài chính hay đọc dữ liệu nghiệp vụ; `CFO` **không** có quyền quản trị hệ thống.
5. **Kiểm tra ở backend:** frontend ẩn mục không có quyền (UX-08) chỉ là trải nghiệm.
6. **AI không có quyền vượt người dùng:** AI hành động trong phạm vi quyền của người dùng/policy và bị giới hạn thêm bởi autonomy level (BRD §2.1, D-11).
7. **Reviewer** là permission + assignment, không phải role.

### 4.2. Permission

Cột "Căn cứ" ghi nguồn; permission không có căn cứ trực tiếp mang `[CẦN XÁC NHẬN]`.

| Permission | Nhóm | Ý nghĩa | Căn cứ |
| --- | --- | --- | --- |
| `data.read` (có phạm vi) | Đọc | Đọc dữ liệu nghiệp vụ trong phạm vi công ty / đơn vị / bản thân-team | UX §4.1 |
| `record.submit` | Ghi | Nhập tay, nhập NL, tải file, import | US-DC-001…003, 007 |
| `extraction.review` | Duyệt | Xử lý hàng chờ review được giao | FR-DC-21, 22; UX §2.1 |
| `action.confirm` | Duyệt | Xác nhận action card L2 không tài chính | UX §7.1 |
| `action.undo` | Ghi | Hoàn tác hành động L3 | BR-11 |
| `finance.submit` | Ghi | Soạn/đề nghị giao dịch tài chính | D-12 (người soạn); ai được giữ: `[CẦN XÁC NHẬN]` |
| `finance.approve` | Duyệt | Duyệt ghi giao dịch tài chính (L2), trong phạm vi assignment | D-12, D-14 |
| `finance.reverse.request` | Ghi | Đề nghị bút toán đảo | D-13, D-14; ai được giữ: `[CẦN XÁC NHẬN]` |
| `finance.reverse.approve` | Duyệt | Duyệt bút toán đảo | D-14 |
| `config.document_schema` | Quản trị | Loại tài liệu, schema, ngưỡng tự ghi | US-DC-008 (Admin) |
| `config.autonomy` | Quản trị | Cấu hình autonomy theo tool × role × ngưỡng | FR-AUT-02; người giữ: `[CẦN XÁC NHẬN]` |
| `ai.kill_switch` | Quản trị | Bật/tắt kill switch | D-09 |
| `audit.read` | Quản trị | Xem audit log | UX §4.1 (Admin); role khác: `[CẦN XÁC NHẬN]` |
| `user.manage` | Quản trị | Tạo tài khoản, gán role, giao assignment | D-22 [CDA nêu] |
| `pii.read` | Đọc | Xem dữ liệu cá nhân nhạy cảm không bị che | SEC-DC-02 (che với người không có quyền); người giữ: `[CẦN XÁC NHẬN]` |
| `ai.use` (có phạm vi) | Sử dụng AI | Hỏi AI, nhận gợi ý/bản nháp trong phạm vi dữ liệu được đọc | UX §4.1 (cột "Hỏi AI") |

### 4.3. Role / persona

Ký hiệu: `[CXN]` = `[CẦN XÁC NHẬN]`.

| Role / persona | Mục đích | Đọc | Ghi | Duyệt | Quản trị hệ thống | Sử dụng AI | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ADMIN` / Admin | Thiết lập tổ chức, quyền, AI policy, schema tài liệu; kill switch (UX §2.1, D-09) | Cấu hình, tình trạng hệ thống, audit (UX §4.1); dữ liệu nghiệp vụ: **không** mặc định `[CXN]` | `record.submit` chỉ cho import danh sách nhân sự (US-DC-007) `[CXN]` | **Không** (không có `finance.approve`) | `config.document_schema`, `ai.kill_switch`, `user.manage`, `audit.read`; `config.autonomy` `[CXN]` | Cấu hình, audit (UX §4.1) | PROPOSED |
| `CEO` / CEO | Biết tình hình, quyết định, giao việc (UX §2.1) | Toàn công ty (UX §4.1) | `record.submit` | `action.confirm`; `finance.approve` `[CXN]` | **Không** (kill switch chỉ Admin — D-09) | Toàn công ty (UX §4.1) | PROPOSED |
| `CFO` / Director phụ trách tài chính; "Finance" (US-DC-009, UC-08) | Duyệt giao dịch tài chính và bút toán đảo trong phạm vi được cấp | Dữ liệu tài chính `[CXN: toàn công ty hay theo phạm vi]` | `record.submit`; `finance.submit`, `finance.reverse.request` `[CXN]` | `finance.approve`, `finance.reverse.approve` trong phạm vi assignment; không duyệt giao dịch do mình tạo | **Không** | Trong phạm vi tài chính `[CXN]` | PROPOSED |
| `MANAGER` / Director, Manager (UX gộp) | Giữ team đúng hướng, duyệt việc của đơn vị (UX §2.1) | Đơn vị và cấp dưới (UX §4.1) | `record.submit`; `finance.submit` `[CXN]` | `action.confirm` trong đơn vị; `extraction.review` khi được giao | Không | Trong đơn vị (UX §4.1) | PROPOSED |
| `EMPLOYEE` / Employee | Làm việc, cập nhật nhanh, gửi chứng từ (UX §2.1) | Của mình, team, mục tiêu cha (UX §4.1) | `record.submit` | `action.confirm` cho việc của mình `[CXN]` | Không | Dữ liệu của mình và team (UX §4.1) | PROPOSED |
| Reviewer (assignment) / kế toán, thư ký, admin phòng ban | Duyệt nhanh, chính xác hàng chờ trích xuất (UX §2.1) | Tài liệu được giao (UX §4.1) | Sửa bản trích xuất được giao | `extraction.review`; trường tài chính chỉ khi đồng thời có `finance.approve` `[CXN]` | Không | Trong tài liệu được giao (UX §4.1) | PROPOSED — permission + assignment, không phải role |
| Legal / Sales (US-DC-010) | Hợp đồng (P1) | `[CXN]` | `[CXN]` | `[CXN]` | Không | `[CXN]` | NEEDS_CONFIRMATION — P1, không cần cho MVP |

Director và Manager: UX §2.1 gộp hai persona; nguồn không nói Director có quyền khác Manager ngoài phạm vi dữ liệu. Đề xuất Director là `MANAGER` ở đơn vị cấp cao hơn `[CXN]`.

### 4.4. Assignment (nhiệm vụ được giao)

| Assignment | Gán cho | Người giao | Căn cứ |
| --- | --- | --- | --- |
| Hàng chờ review theo loại tài liệu/phòng ban | Tài khoản có `extraction.review` | `ADMIN` hoặc `MANAGER` của đơn vị `[CXN]` | FR-DC-21 |
| Phạm vi ủy quyền duyệt tài chính | Tài khoản có `finance.approve` | `[CXN]` (D-14 3.2.4-6) | D-14 |
| Chủ entity (owner KPI/OKR, task) | Bất kỳ người dùng | Theo nghiệp vụ module `[CXN]` (D-24) | UX §4.2, F1–F5 |

### 4.5. Điểm CDA cần chốt
1. Năm role nền tảng và Reviewer là assignment: có đủ và đúng không?
2. `CEO` có `finance.approve` và `audit.read` không?
3. Ai giữ `finance.submit`, `finance.reverse.request`, `config.autonomy`, `pii.read`?
4. `ADMIN` có cần đọc dữ liệu nghiệp vụ nào ngoài import nhân sự không?
5. Một tài khoản có được giữ nhiều role (UX §4.2 cho phép đổi ngữ cảnh vai trò) không? Nếu có, quy tắc "không tự duyệt" áp dụng theo tài khoản, không theo role `[PROPOSED]`.
6. Ai giao assignment hàng chờ review và phạm vi ủy quyền tài chính?

---

## 5. Trạng thái CON / GAP / Q / ASM

### 5.1. Mâu thuẫn

| ID | Trạng thái | Quyết định |
| --- | --- | --- |
| CON-01 | NEEDS_CONFIRMATION | D-23 |
| CON-02 | CONFIRMED (đã giải quyết) | D-11 |
| CON-03 | CONFIRMED (đã giải quyết) | D-12 |
| CON-04 | CONFIRMED (đã giải quyết) | D-09; còn mở D-10 |
| CON-05 | CONFIRMED (đã giải quyết) | D-18 |
| CON-06 | CONFIRMED (đã giải quyết) | D-17; còn mở D-20 |
| CON-07 | NEEDS_CONFIRMATION | D-29 |
| CON-08 | CONFIRMED một phần | D-27: PWA; sinh trắc học/offline chưa cam kết |
| CON-09 | NEEDS_CONFIRMATION | D-28 |
| CON-10, CON-11 | PROPOSED | D-34 |
| CON-12 | CONFIRMED (đã giải quyết) | D-13; còn mở D-14 |
| CON-13 | CONFIRMED (đã giải quyết) | D-21 |
| CON-14 | NEEDS_CONFIRMATION | D-33 |
| CON-15, CON-16 | CONFIRMED — đóng, `[LEGACY FINDING — A-EMS]` | D-05 |
| CON-17 | CONFIRMED — đóng, `[LEGACY FINDING — A-EMS]` | D-15 |
| CON-18 | CONFIRMED — đóng, `[LEGACY FINDING — A-EMS]` | D-22 |
| CON-19 | CONFIRMED (đã giải quyết) | D-04, D-05 |

### 5.2. Khoảng trống

| ID | Trạng thái | Ghi chú |
| --- | --- | --- |
| GAP-01, GAP-02 | CONFIRMED | D-01: toàn văn không có; v1.1 đã được CDA xác nhận duyệt |
| GAP-03 | CONFIRMED (trừ R6) | D-21 |
| GAP-04 | CONFIRMED (cách xử lý) | D-24; nội dung chi tiết vẫn thiếu |
| GAP-05 | CONFIRMED | D-03 |
| GAP-06 | CONFIRMED (`ARCHITECTURE_DECISION`) | D-06: ADR-001…013 |
| GAP-07 | CONFIRMED (tài chính: D-14) · `ARCHITECTURE_DECISION` (vòng đời tài liệu: Architecture §8.5) | Chi tiết nghiệp vụ tài liệu cần đối chiếu khi viết SRS 2B |
| GAP-08 | NEEDS_CONFIRMATION | D-16 |
| GAP-09 | CONFIRMED một phần | D-30: đăng nhập nội bộ + MFA ADMIN; SSO DEFERRED |
| GAP-10 | NEEDS_CONFIRMATION | D-31 |
| GAP-11 | CONFIRMED (in-app) | D-32 |
| GAP-12 | CONFIRMED (không khôi phục được) | Nội dung nhúng mất; UX Flows dựa trên phần chú thích |
| GAP-13 | NEEDS_CONFIRMATION (Thấp) | Nguồn dữ liệu đơn vị hành chính; không chặn MVP nếu chỉ validate định dạng |
| GAP-14 | NEEDS_CONFIRMATION (TB) | Ngân sách AI, trần chi phí/tài liệu |
| GAP-15 | NEEDS_CONFIRMATION (TB) | Chính sách lưu trữ ngoài chứng từ kế toán và CV |
| GAP-16 | NEEDS_CONFIRMATION | D-28 |
| GAP-17 | NEEDS_CONFIRMATION | D-23 |
| GAP-18 | NEEDS_CONFIRMATION (Thấp) | SLA review: cấu hình được, giá trị chờ CDA |
| GAP-19, GAP-20 | DEFERRED | D-35 |
| GAP-21 | NEEDS_CONFIRMATION (TB) | NFR nền tảng chung chưa có trong nguồn |
| GAP-22 … GAP-25 | CONFIRMED — đóng, `[LEGACY FINDING — A-EMS]` | Mục 1.3 |

### 5.3. Câu hỏi

| ID | Trạng thái | Quyết định |
| --- | --- | --- |
| Q-01, Q-02 | CONFIRMED | D-01 |
| Q-03 | CONFIRMED | D-02 |
| Q-04 | CONFIRMED | D-03 |
| Q-05 | CONFIRMED một phần | D-06, D-07; còn D-08 (provider) |
| Q-06 | CONFIRMED | D-09 |
| Q-07 | CONFIRMED một phần | D-11, D-12; còn D-16 |
| Q-08 | CONFIRMED | D-17, D-18 |
| Q-09 | CONFIRMED (trừ R6) | D-21 |
| Q-10 … Q-22 | Xem D-23 … D-35 | |
| Q-23 | CONFIRMED | D-04 |
| Q-24 | CONFIRMED | D-05 |
| Q-25 | CONFIRMED — đóng (legacy); nguyên tắc AI-EOS ở D-22 `PROPOSED` | D-22 |
| Q-26 | CONFIRMED | D-10 |
| Q-27 | NEEDS_CONFIRMATION (TB) | D-08 |

### 5.4. Giả định

| ID | Trạng thái |
| --- | --- |
| ASM-01, ASM-02, ASM-05, ASM-08 | Giữ nguyên (cần kiểm chứng bằng usability test) |
| ASM-03 | Giữ nguyên; liên quan D-28 |
| ASM-04 | CONFIRMED (ADR-003) |
| ASM-06 | Giữ nguyên: giá trị "vd." không phải quy tắc (D-16) |
| ASM-07 | CONFIRMED (D-01) |

---

## 6. Lịch sử thay đổi

| Phiên bản | Ngày | Thay đổi | Lý do |
| --- | --- | --- | --- |
| 0.1 | 12/10/2026 | Tạo Decision Log; 36 quyết định; ghi nhận CON-15…19, GAP-22…25, Q-23…27 từ đối chiếu repository; đề xuất ma trận role dựa trên 8 role của A-EMS | Checkpoint 2A |
| 0.2 | 12/10/2026 | D-04, D-05 → CONFIRMED (AI-EOS độc lập, không dùng A-EMS). D-06 tách nguyên tắc (CONFIRMED) và stack cụ thể (NEEDS_CONFIRMATION); bỏ stack A-EMS. D-07 bổ sung ưu tiên provider miễn phí/chi phí thấp. D-08 bỏ tham chiếu provider của A-EMS. D-10, D-14 chi tiết hóa, giữ PROPOSED, thêm câu hỏi. D-15, D-22 phân loại `[LEGACY FINDING — A-EMS]`, tách kiểm soát thiết kế AI-EOS. D-19 → không áp dụng. D-21 xây lại ma trận role từ nguồn AI-EOS (không kế thừa 8 role A-EMS), thêm permission. D-24 → CONFIRMED cách xử lý. D-25, D-26, D-27, D-28, D-30, D-31, D-36 bỏ mọi mô tả "hiện trạng A-EMS". Mục 1 viết lại thành ranh giới dự án; CON-15…19, GAP-22…25 phân loại lại, giữ nguyên ID | CDA xác nhận AI-EOS là dự án mới, độc lập; A-EMS ngoài phạm vi |
| 0.3 | 12/10/2026 | D-06: bỏ "CONFIRMED (nguyên tắc)", giữ NEEDS_CONFIRMATION; thêm phạm vi ADR công nghệ (mục 3.4). D-10: ghi nhận nguyên tắc CDA nêu; tách điểm mở (toàn hệ thống, 30 ngày, thông báo, queue/retry); vẫn PROPOSED. D-14: thêm bảng chuyển trạng thái có điều kiện, nguyên tắc CDA nêu (không tự duyệt, chỉ đảo toàn bộ, không ghi kỳ đã khóa), phương án kỳ đang mở, 7 câu hỏi mở; vẫn PROPOSED. D-21: năm role nền tảng, thêm nhóm quyền "sử dụng AI", cột căn cứ, bảng assignment; `ADMIN` không duyệt tài chính, `CFO` không quản trị; vẫn PROPOSED. D-22: chuyển trạng thái tổng thể sang PROPOSED (bỏ nhãn "CONFIRMED (phân loại)" ở cột trạng thái; phân loại legacy giữ trong nội dung), thêm bootstrap Admin; mục 3.3 mới. Thêm nhãn `[CDA nêu]` | Vòng review 2A thứ hai của CDA |
| 0.4 | 12/10/2026 | D-06: ghi nhận định hướng `[CDA nêu]` (Python, React, Local/Docker Compose, miễn phí/mã nguồn mở, adapter); vẫn NEEDS_CONFIRMATION. D-06, D-10, D-14, D-21, D-22: thêm liên kết tới câu hỏi chuẩn hóa và dự thảo ADR-001…013 trong `Pre2C_Decision_Proposals.md`. Không đổi trạng thái quyết định nào | CDA yêu cầu chuẩn bị đề xuất trước Stage 2C |
| 0.5 | 12/10/2026 | Chốt theo yêu cầu CDA 12/10/2026: D-06, D-25, D-26 → CONFIRMED (`ARCHITECTURE_DECISION`, ADR-001…013); D-10, D-14, D-21, D-22 → CONFIRMED (`CDA_DIRECTIVE` K/F/R/A) với phần còn mở ghi rõ (người giữ `finance.period.manage`, R6); D-27, D-30, D-32 chốt một phần; D-08, D-16, D-29 thêm mặc định an toàn. Cập nhật §5 cho GAP-03/06/07/09/11, CON-08/13, Q-05/09/26, ASM-04. Ghi nhận sai lệch quy trình: Stage 2B chưa thực hiện, Stage 2C thực hiện theo chỉ đạo CDA | Yêu cầu CDA "Chốt quyết định kiến trúc AI-EOS và triển khai Stage 2C" |
| 0.6 | 12/10/2026 | Stage 2B: thêm ký hiệu `CDA-F1…CDA-F7` để khử trùng mã với luồng UX F1–F5; thêm §7 với Q-28…Q-42 (NEEDS_CONFIRMATION) và tham chiếu AMD-01, AMD-02 (PROPOSED). Không đổi trạng thái hay ID của quyết định nào | Stage 2B |
| 0.12 | 14/10/2026 | Thêm mục 3.5 (hồ sơ phương án Q-48, chưa quyết định) và 3.6; thêm Q-49 (NEEDS_CONFIRMATION) cho T-003. Không đổi quyết định, ID hay trạng thái cũ | Phiên 14/10/2026: không task nào đủ điều kiện viết code |
| 0.11 | 14/10/2026 | Thêm Q-48 (NEEDS_CONFIRMATION): vị trí mã hạ tầng dùng chung cho T-004…T-007 chưa có trong Architecture §3. Không đổi quyết định, ID hay trạng thái cũ | Chọn task phiên 14/10/2026 (Implementation_Plan §12) |
| 0.10 | 12/10/2026 | D-41 đóng: ghi bằng chứng cho ba điều kiện thực thi (toolchain chạy thành công, PostgreSQL 18 trên GitHub Actions, branch protection + PR đỏ bị chặn). Không đổi nội dung quyết định; Q-44 và giả định C1 vẫn mở | Hoàn tất T-002 |
| 0.9 | 12/10/2026 | D-41 thêm phần bổ sung 0.9 (không tạo quyết định mới): Q-43, Q-45, Q-46, Q-47 → CONFIRMED qua D-41 với điều kiện thực thi; hướng toolchain TypeScript 6.0.3 + ESLint 10 + typescript-eslint, phiên bản chỉ xác nhận sau kiểm thử thực tế; Q-44 giữ NEEDS_CONFIRMATION. Nội dung câu hỏi và mặc định cũ giữ nguyên | Chỉ đạo CDA 12/10/2026 |
| 0.8 | 12/10/2026 | Thêm D-41 (chỉ đạo CDA về toolchain/CI cho T-002) và mục 8 với Q-43…Q-47 (NEEDS_CONFIRMATION). Không đổi trạng thái hay ID của quyết định/câu hỏi cũ | Review T-001, chuẩn bị T-002 |
| 0.7 | 12/10/2026 | Thêm D-37 (AMD-01), D-38 (AMD-02 theo phiên bản CDA, thay đề xuất trước), D-39 (mặc định an toàn tạm thời Q-28/29/36/37), D-40 (Sales Lite chưa triển khai); D-08, D-21 thêm chỉ đạo; Q-40 → CONFIRMED qua D-37. Không đổi trạng thái quyết định cũ | Yêu cầu CDA "Duyệt có điều kiện Stage 2B và tiếp tục Stage 2D" |

## 7. Câu hỏi nghiệp vụ phát sinh ở Stage 2B

Tất cả ở trạng thái **NEEDS_CONFIRMATION**, trừ Q-40 (CONFIRMED qua D-37). Q-28, Q-29, Q-36, Q-37 có mặc định tạm thời D-39; Q-38 có D-40 — các mặc định này **không** phải câu trả lời nghiệp vụ. "Mặc định an toàn" là hành vi đang được đặc tả trong SRS cho tới khi CDA trả lời; không phải quyết định đã duyệt. Ưu tiên: `Cao` = chặn một phần MVP; `TB` = ảnh hưởng hiển thị/báo cáo; `Thấp` = có thể sau MVP.

| ID | Câu hỏi | Module | Tác động | Mặc định an toàn / phương án đề xuất | Ưu tiên | Liên quan |
| --- | --- | --- | --- | --- | --- | --- |
| Q-28 | Vòng đời Objective/KR/KPI ngoài `DRAFT → ACTIVE` (đóng, hủy, lưu trữ)? Ai có quyền kích hoạt mục tiêu cấp công ty/đơn vị? | M3 | Trạng thái, quyền | Chỉ DRAFT/ACTIVE; kích hoạt: CEO (công ty), MANAGER (đơn vị) | Cao | SRS-GOAL-03, 04; Mặc định tạm thời D-39 |
| Q-29 | Công thức % đạt của KR/KPI, chiều tốt, ngưỡng cảnh báo lệch; có điền check-in từ task đã xong không? | M3, M5 | Ô OKR, cảnh báo | Không tính %; chỉ hiển thị baseline/target/giá trị | Cao | SRS-GOAL-08, 09; Mặc định tạm thời D-39 |
| Q-30 | Nhịp check-in, ai bắt buộc check-in, định nghĩa "KPI cập nhật đúng hạn" (MET-10) | M3 | Nhắc việc, KR3.2 | Không nhắc tự động; check-in tự nguyện | TB | SRS-GOAL-07, MET-10 |
| Q-31 | Độ dài kỳ của mục tiêu (quý/tháng/năm) và quan hệ với kỳ báo cáo tài chính | M3, M6 | Schema kỳ | Kỳ mục tiêu là văn bản tự do; kỳ tài chính mặc định tháng | TB | SRS-GOAL-01 |
| Q-32 | Quy tắc cây alignment: KPI có gắn Objective không; có cấp Chiến lược/Initiative/Dự án trong MVP không? | M3 | Breadcrumb UX §4.2 | Chỉ Objective cha–con, KR thuộc Objective, KPI độc lập | TB | SRS-GOAL-01, 10 |
| Q-33 | Trạng thái task ngoài Mở/Xong; task có cần "gửi duyệt" không; ai được mở lại task | M4 | State machine task | Chỉ OPEN/DONE; không duyệt; mở lại bởi người giao | TB | SRS-WRK-02, 03 |
| Q-34 | Mô hình workload (ước lượng, năng lực) cho F5 và chỉ số quá tải | M4 | Hành trình J6 | Không có workload trong MVP | TB | SRS-WRK-12, FR-HM-06 |
| Q-35 | "Đặt lịch"/đồng bộ lịch trong F1, UC-06 có thuộc MVP không (lịch nội bộ hay ngoài)? | M4, M5 | Thực thể lịch | Không có lịch trong MVP | TB | D-31 |
| Q-36 | Nội dung CEO Briefing: loại mục "Cần anh quyết", khối "Rủi ro" khi Risk Intelligence là P1, giờ/tần suất tạo | M5 | Trang chủ CEO | Cần anh quyết = bản nháp AI chờ CEO + task giao cho CEO trễ/sắp đến hạn; ẩn khối Rủi ro; 07:00 hằng ngày | Cao | SRS-BRF-07, 09, 11; Mặc định tạm thời D-39 |
| Q-37 | Công thức 4 ô chỉ số mặc định và ngưỡng "dữ liệu cũ" theo từng chỉ số | M5 | Ô chỉ số | Theo SRS-BRF-05 (PROPOSED) | Cao | D-28; Mặc định tạm thời D-39 |
| Q-38 | Sales Pipeline Lite: thực thể, trường, giai đoạn, trọng số/xác suất, nguồn chỉ tiêu, ai nhập, nhập tay hay import | M7 | Toàn module | Không hiển thị số liệu pipeline | Cao | SRS-SLS-01…03; Triển khai bị chặn D-40 |
| Q-39 | Định nghĩa "burn ròng hàng tháng" và cửa sổ tính runway | M6, M5 | Ô dòng tiền, runway | Runway "không áp dụng" khi burn ≤ 0; công thức BRD §4.3 làm mặc định đề xuất | TB | SRS-FIN-15 |
| Q-40 | Giao dịch gốc có ngày thuộc kỳ đã khóa: từ chối hay ghi vào kỳ đang mở? | M6 | Quy trình gửi | Từ chối khi gửi (AMD-01) | TB | SRS-FIN-05, 16; **Đã trả lời qua D-37 (AMD-01): từ chối khi gửi** — CONFIRMED |
| Q-41 | Decision Log: theo dõi kết quả sau 30/60/90 ngày có trong MVP không? | M4 | North Star | Chỉ ghi quyết định, không theo dõi | Thấp | SRS-WRK-11, FR-EXT-04 |
| Q-42 | Danh mục doanh thu/chi phí và tài khoản tiền mặt (một hay nhiều) | M6 | Schema, báo cáo | Danh mục văn bản tự do; một số dư tiền mặt tổng | TB | SRS-FIN-01 |

Đề xuất amendment ADR từ Stage 2B: **AMD-01** và **AMD-02** — **đã được CDA duyệt ngày 12/10/2026** (D-37, D-38; AMD-02 theo phiên bản của CDA). ADR-005, ADR-008, ADR-009 có mục "Amendments".

## 8. Câu hỏi kỹ thuật phát sinh khi triển khai

Tất cả **NEEDS_CONFIRMATION**, trừ Q-43, Q-45, Q-46, Q-47 (**CONFIRMED** qua D-41 bổ sung 0.9; điều kiện xác minh kỹ thuật ghi riêng ở từng dòng). Mặc định an toàn được dùng tạm cho T-002 và không phải câu trả lời cuối cùng. Không câu hỏi nào được giải quyết bằng cách sửa Architecture/ADR khi chưa có amendment được CDA duyệt.

| ID | Câu hỏi | Liên quan | Mặc định an toàn tạm thời | Ưu tiên |
| --- | --- | --- | --- | --- |
| Q-43 | `ai`, `jobs`, `capture` có được import **API đọc** (`<module>.api`) của `goals`, `work`, `org`, `knowledge`, `finance` không? Architecture §3 quy tắc 2 chỉ cấm gọi service **ghi** | Architecture §3, ADR-001, ADR-008, D-41 | `[CẦN XÁC NHẬN]` Cấm mọi import trực tiếp, kể cả API đọc (import-contract ở T-002). Khi task sau cần đọc dữ liệu domain từ các module này, phải xin xác nhận trước khi nới contract **Đã trả lời qua D-41 (bổ sung 0.9) — CONFIRMED:** cấm `ai`, `jobs`, `capture` import trực tiếp `goals`, `work`, `org`, `knowledge`, `finance`, gồm `<module>.api` (đọc lẫn ghi) và mọi module con. Không áp dụng cho `insights` (Architecture §3 cho phép đọc qua API công khai) và `gateway` (quy tắc 3). Nới quy tắc cần quyết định CDA mới. Điều kiện thực thi: contract C2 (Implementation_Plan §11.4) và kiểm tra âm N4. | TB |
| Q-44 | Đề xuất amendment ADR-001: danh sách module trong ADR-001 có 15 module, thiếu `knowledge` và `insights` so với Architecture §3 (1.2, 17 module) | ADR-001, Architecture §3, T-001 | Code theo Architecture §3 (17 module). ADR-001 giữ nguyên đến khi CDA duyệt amendment | Thấp |
| Q-45 | Đề xuất phạm vi nền tảng frontend ADR-003: Tailwind + shadcn/ui, React Router, TanStack Query, manifest + service worker PWA (chỉ cache tài nguyên tĩnh) chưa được nêu tường minh trong task nào. T-111 có "app shell" nhưng phụ thuộc T-102…T-109; i18n thuộc T-607 | ADR-003, T-111, T-607 | Phương án đề xuất: (a) ghi rõ các hạng mục này vào phạm vi T-111, hoặc (b) task frontend nền tảng riêng chỉ phụ thuộc T-001/T-002 để làm song song P1. Không tạo ID task mới khi chưa được duyệt **Đã trả lời qua D-41 (bổ sung 0.9) — CONFIRMED:** phương án (b), task riêng **T-012** (Implementation_Plan §4, P0); T-111 giữ nguyên phạm vi và dependency. | TB |
| Q-46 | Nền tảng CI và branch protection: dùng nền tảng nào (repo chưa có remote), ai cấu hình bảo vệ nhánh `main` | ADR-013, T-002, D-41 | Chỉ có `scripts/ci.sh` chạy local; workflow CI là bản chưa xác minh cho đến khi có remote và lần chạy thật; không tuyên bố "CI chặn merge" **Đã trả lời qua D-41 (bổ sung 0.9) — CONFIRMED:** GitHub Actions. Điều kiện thực thi: bằng chứng ghi riêng cho `scripts/ci.sh` (local), workflow GitHub Actions (cần remote và lần chạy thật) và branch protection `main` (cần cấu hình và xác minh); chưa có thì không tuyên bố đã xác minh. | Cao (chặn DoD của T-002) |
| Q-47 | Phiên bản major PostgreSQL cho CI service và triển khai (Database_Design không chốt) | ADR-004, T-002, T-003, T-005 | CI service dùng một major được ghim rõ trong workflow, chốt cùng T-003 (Compose) để dev/CI/triển khai giống nhau **Đã trả lời qua D-41 (bổ sung 0.9) — CONFIRMED:** PostgreSQL 18. Điều kiện thực thi: smoke test chạy thật với PostgreSQL 18 trên GitHub Actions trước khi coi cấu hình CSDL/CI hoàn tất; T-003, T-005 dùng cùng major. | TB |
| Q-48 | Mã hạ tầng dùng chung không có module sở hữu: loader cấu hình/secret (T-004), logging JSON + correlation ID + `/health/*` + khởi tạo ứng dụng FastAPI (T-006), engine/session SQLAlchemy và cấu hình Alembic (T-005), hạ tầng HTTP (T-007). Architecture §3 có 17 module, không module nào nhận các trách nhiệm này; test cấu trúc T-001 cấm package hoặc file `.py` ngoài danh sách đó trong `aieos` | Architecture §3, ADR-001, ADR-002, T-004…T-007, Q-44 | Không tạo package/module mới, không đặt mã hạ tầng vào module nghiệp vụ khi chưa có amendment Architecture §3 (và ADR-001, xem Q-44) được CDA duyệt; T-004, T-006 chưa bắt đầu dù dependency đã `DONE`. `[CẦN XÁC NHẬN]` Phương án để CDA chọn: (a) thêm một module hạ tầng vào Architecture §3 kèm quy tắc phụ thuộc (module nghiệp vụ được import, module hạ tầng không import module nghiệp vụ) và contract import tương ứng; (b) giao từng trách nhiệm cho module hiện có (cần chỉ định cụ thể); (c) phương án khác của CDA. Hồ sơ phương án, ưu/nhược điểm và tác động: mục 3.5 | Cao |
| Q-49 | T-003 (Docker Compose): công cụ `proxy`, `scanner`, runtime LLM, stack quan sát chưa được chọn; DoD "`docker compose up` chạy đủ service" cần image `api`/`worker` chạy được (T-006, T-009) nhưng cột "Phụ thuộc" chỉ ghi T-001; máy local không có Docker | Architecture §9.1, ADR-004, ADR-012, T-003, T-005, T-006, T-009, Q-48 | T-003 chưa bắt đầu; không tự chọn công cụ. Chi tiết và các điểm cần quyết định: mục 3.6 | Cao |
