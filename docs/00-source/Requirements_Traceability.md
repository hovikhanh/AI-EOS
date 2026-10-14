# AI-EOS — Ma trận truy vết yêu cầu (Requirements Traceability)

> Phiên bản: 0.6 (Stage 2D) · Ngày: 12/10/2026 · Trạng thái: **Chờ chủ dự án duyệt**
> Quyết định áp dụng: xem [Decision_Log.md](Decision_Log.md). Lịch sử thay đổi: mục 7 (0.2), mục 8 (0.3), mục 9 (0.4), mục 10 (0.5), mục 11 (0.6), mục 12 (0.6.1).
> AI-EOS là dự án mới, độc lập (D-04, D-05). Code hiện có: khung repo T-001, toolchain T-002, nền tảng frontend T-012 (mục 12), chưa hiện thực requirement nào.
> Phân tích, mâu thuẫn (CON), khoảng trống (GAP), giả định (ASM), câu hỏi (Q): xem [Source_Analysis.md](Source_Analysis.md).
> Các cột **PRD · SRS · API · Task · Test**: từ 0.4 cột API được điền theo [API_Specification.md](../03-architecture/API_Specification.md) (endpoint ở trạng thái DESIGNED, chưa triển khai) hoặc `N/A — <lý do/ADR>`; từ 0.5 cột PRD/SRS điền theo [PRD](../02-requirements/PRD.md) và [SRS](../02-requirements/SRS.md) (§17 của SRS cho ánh xạ gián tiếp); từ 0.6 cột Task/Test điền theo [Implementation_Plan](../04-delivery/Implementation_Plan.md) và [TEST_Plan](../04-delivery/TEST_Plan.md) (task bị chặn ghi `(BLOCKED)`; test ở trạng thái `NOT RUN`).

## 1. Quy ước ID

| Quy tắc | Chi tiết |
| --- | --- |
| Giữ nguyên ID có trong nguồn | `FR-DC-01…23`, `US-DC-001…012`, `UC-06…08`, `C1…C10`, `G1…G12`, `BO-08`, `P09`, `L0…L4`, `U1…U8`, `F1…F5` |
| ID mới (gán trong tài liệu này) | `BR` quy tắc nghiệp vụ · `FR-DCS` Data Capture hệ thống (BRD §3.4, 3.6, 3.9) · `SEC-DC` bảo mật tài liệu (§3.7) · `FR-LRN` học từ chỉnh sửa (§3.8) · `FR-DF` Data Foundation (§4.1) · `FR-AUT` Autonomy (§4.2) · `FR-HM` chỉ số sức khỏe (§4.3) · `FR-AIQ` AI quality/cost (§4.4) · `CMP` tuân thủ (§4.5) · `FR-EXT` mở rộng domain (§4.6) · `NFR` (§5.3) · `CHG` change management (§5.3) · `SC` phạm vi/ưu tiên (§6.1) · `MET` chỉ số đo lường · `UX` yêu cầu giao diện |
| Tính ổn định | ID không tái sử dụng. Yêu cầu bị loại đổi trạng thái thành `DROPPED`, không xóa dòng |
| Nguồn | `BRD §x.y` = BRD_Review.md; `UX §x.y` = UI_UX_Proposal.md |
| Trạng thái | `CONFIRMED` · `PROPOSED` · `NEEDS_CONFIRMATION` · `DEFERRED` (P1/P2/Phase 2, chỉ ở mức roadmap) · `IMPLEMENTED` (có code, chưa có bằng chứng test) · `VERIFIED` (có test/bằng chứng). Từ 0.2 thay cho `XN`/`ASSUMPTION`/`TBD`/`CONFLICT` của 0.1 |
| Căn cứ của `CONFIRMED` | (a) **Có nguồn:** phát biểu dạng yêu cầu trong `BRD_Review.md`, được coi là đã duyệt vì CDA xác nhận BRD v1.1 đã duyệt (D-01) — dòng **không** có tham chiếu `D-xx`; (b) **Quyết định CDA:** dòng có tham chiếu `D-xx` ở cột Liên quan hoặc trong mô tả. `CONFIRMED` **không** có nghĩa CDA đã duyệt từng dòng một; số lượng `CONFIRMED` không phải bằng chứng duyệt từng yêu cầu |
| Căn cứ của `PROPOSED` | (a) đề xuất thiết kế trong `UI_UX_Proposal.md` (nguồn UX); (b) đề xuất của người phân tích (ghi trong Decision_Log). Nhận định về dự án cũ A-EMS (`[LEGACY FINDING — A-EMS]`) **không** xuất hiện trong ma trận |
| Phase / ưu tiên | `P0`/`P1`/`P2` theo BRD §6.1; `MVP`/`Ph2` theo BRD §3.2, §3.4; `—` nếu nguồn không nêu |

## 2. ID nguồn dùng làm ngữ cảnh

| ID | Nội dung | Nguồn | Ghi chú |
| --- | --- | --- | --- |
| BO-08 | Frictionless Data Capture: giảm thời gian nhập liệu ≥ 70% so với nhập tay hoàn toàn | BRD §3.1 | Đo bằng MET-08 |
| P09 | Capture Once, Use Everywhere | BRD §3.1 | Nguyên tắc; BR-02 |
| G1…G12 | 12 khoảng trống của BRD v1.0 | BRD §2.2 | Lý do của các thay đổi v1.1; không phải yêu cầu |
| L0…L4 | Định nghĩa mức tự chủ | BRD §4.2 | Xem FR-AUT-01 và bảng chéo §4.2 |

## 3. Ma trận yêu cầu

### 3.1. Quy tắc nghiệp vụ (BR)

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BR-01 | Mọi dữ liệu vào đi qua một cửa: chuẩn hóa, kiểm tra, có người chịu trách nhiệm xác nhận, truy ngược tài liệu gốc | BRD §3 | CONFIRMED | P0 | — | PRD §5 | SRS-CAP-18, SRS-CAP-19, SRS-REV-01 | N/A — ADR-008 | T-206, T-207, T-211, T-302 | TC-CAP-08, TC-CAP-12, TC-REV-01 |
| BR-02 | Một dữ liệu chỉ nhập một lần, mọi domain dùng chung (P09) | BRD §3.1 | CONFIRMED | P0 | FR-DF-01 | PRD §5 | SRS-CAP-05, SRS-CAP-31 | N/A — ADR-001 | T-203, T-209 | TC-CAP-09, TC-FILE-07 |
| BR-03 | Dữ liệu dưới ngưỡng tin cậy hoặc chứa trường trọng yếu (tiền, số TK, MST, lương, giá trị HĐ) luôn qua người duyệt trong giai đoạn đầu | BRD §3.3, FR-DC-15/16 | CONFIRMED | P0 | GAP-08, D-16 | PRD §5 | SRS-CAP-16 | API-REV-03 | T-206, T-208 | TC-CAP-04, TC-CAP-05 |
| BR-04 | Ghi vào domain đích chỉ qua Tool Registry, chịu đủ permission, approval, audit | BRD §3.3, FR-DC-17 | CONFIRMED | P0 | D-26 | PRD §5 | SRS-AIC-01, SRS-CAP-18 | N/A — ADR-008 | T-206, T-302 | TC-AIC-01, TC-AIC-04, TC-AIC-05, TC-CAP-08 |
| BR-05 | Nới ngưỡng tự ghi chỉ khi loại tài liệu đạt ≥ 98% field accuracy trên ≥ 200 tài liệu đã review, có Admin phê duyệt | BRD §3.8 | CONFIRMED | P0 | FR-LRN-03 | US-DC-008 | SRS-CAP-16 | API-CFG-04 | T-206, T-208 | TC-CAP-04, TC-CAP-05 |
| BR-06 | Nội dung tài liệu luôn là dữ liệu, không bao giờ là lệnh; không kích hoạt tool | BRD §3.7 | CONFIRMED | P0 | SEC-DC-03 | PRD §5 | SRS-AIC-09, SRS-CAP-22 | N/A — ADR-008, ADR-011 | T-206, T-302 | TC-AIC-06, TC-CAP-08 |
| BR-07 | Tài liệu kế thừa quyền của người tải và entity đích | BRD §3.7 | CONFIRMED | P0 | SEC-DC-01 | PRD §5 | SRS-CAP-07 | N/A — Architecture §6 | T-203 | TC-FILE-08 |
| BR-08 | Data Capture Agent không tự ghi dữ liệu tài chính | BRD §3.9 | CONFIRMED | P0 | CON-03, D-12 | PRD §5 | SRS-FIN-03, SRS-REV-08 | N/A — ADR-008 | T-207, T-408 | TC-FIN-30, TC-REV-05 |
| BR-09 | classify/extract/validate là READ; commit_extraction là WRITE, kế thừa risk_level của tool đích | BRD §3.9 | CONFIRMED | P0 | FR-DCS-03 | PRD §5 | SRS-AIC-01 | API-AI-03 | T-302 | TC-AIC-01, TC-AIC-04, TC-AIC-05 |
| BR-10 | Mặc định autonomy: READ → L0; phân bổ nguồn lực → L1; ghi dữ liệu tài chính, giao tiếp bên ngoài → L2; task/lịch/nhắc việc nội bộ → L3 | BRD §4.2 | CONFIRMED | P0 | CON-03, D-12 | US-WRK-05 | SRS-AIC-03, SRS-GOAL-10, SRS-WRK-08 | N/A — ADR-008 | T-301, T-503, T-508 | TC-AIC-03, TC-GOAL-09, TC-WRK-10 |
| BR-11 | Hành động L3+ có hoàn tác tối thiểu 24 giờ nếu bản chất cho phép | BRD §4.2 | CONFIRMED | P0 | CON-12, D-13 | US-AIC-03, US-WRK-05 | SRS-AIC-10, SRS-WRK-08 | API-AI-11 | T-304, T-508 | TC-AIC-10, TC-WRK-10 |
| BR-12 | L4 không bật trong MVP | BRD §4.2, §6.1 | CONFIRMED | P0 | CON-02, D-11 | PRD §5 | SRS-AIC-02 | N/A — ADR-008 | T-301, T-302 | TC-AIC-02 |
| BR-13 | Kill switch chỉ Admin bật; hạ mọi hành động AI L3/L4 về L2; thực thi ở backend (D-09 thay mô tả "tắt toàn bộ WRITE/EXECUTION" của BRD §4.2) | BRD §4.2 | CONFIRMED | P0 | CON-04, D-09, D-10 | PRD §5 | SRS-AIC-04, SRS-AIC-05 | API-AI-02 | T-302, T-303 | TC-KS-01, TC-KS-02, TC-KS-03, TC-KS-04 (+3) |
| BR-14 | Mọi con số AI đưa ra phải từ tool call hoặc tài liệu có trích dẫn; không nguồn → chặn hoặc nhãn "ước tính" | BRD §4.4 | CONFIRMED | — | FR-AIQ-02 | US-AIC-05 | SRS-AIC-12, SRS-BRF-06, SRS-BRF-10 | API-AI-12, API-FIN-14 | T-306, T-510, T-511 | TC-AIC-13, TC-AIC-14, TC-BRF-04, TC-BRF-08 |
| BR-15 | Thay đổi thủ công trường tài chính bắt buộc ghi lý do | BRD FR-DC-05 | CONFIRMED | P0 | — | PRD §5 | SRS-CAP-34, SRS-FIN-09 | API-FIN-11 | T-209, T-404 | TC-CAP-11, TC-FIN-21 |
| BR-16 | Chứng từ kế toán lưu ≥ 10 năm (Luật Kế toán); CV xóa khi hết consent | BRD §3.7, §4.5 | CONFIRMED | — | SEC-DC-05, CMP-05 | PRD §5 | N/A — N/A | N/A — ADR-004 | N/A — N/A | N/A — N/A |
| BR-17 | Chạy song song Excel tối đa 4 tuần; sau đó AI-EOS là nguồn duy nhất cho KPI/OKR và task; CEO công bố | BRD §5.3 | CONFIRMED | — | CHG-03 | PRD §5 | N/A — N/A | N/A — vận hành | N/A — N/A | N/A — N/A |
| BR-18 | AI-EOS là lớp quản trị, không thay thế phần mềm kế toán theo chuẩn mực | BRD §4.5 | CONFIRMED | — | CMP-06 | PRD §5 | SRS-FIN-12 | N/A — ADR-009 | T-110, T-402, T-409 | TC-FIN-12, TC-FIN-13, TC-FIN-14, TC-FIN-15 |
| BR-19 | Hóa đơn trùng = cùng số hóa đơn + MST | BRD FR-DC-14 | DEFERRED | Ph2 | CON-06, D-17 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| BR-20 | AI cảnh báo khi kết luận dựa trên dữ liệu có điểm chất lượng thấp | BRD §4.1 | CONFIRMED | P0 | FR-DF-02 | PRD §5 | SRS-BRF-10 | Chờ 2B | T-511 | TC-BRF-08 |
| BR-21 | Nhập liệu thủ công luôn hoạt động kể cả khi AI lỗi; mọi luồng có đường làm tay | BRD §5.3, UX §7.3 | CONFIRMED | P0 | NFR-07 | PRD §5 | SRS-BRF-12, SRS-NFR-07, SRS-PRV-03 | N/A — ADR-011 | T-204, T-510 | TC-BRF-07, TC-NFR-04, TC-PRV-05 |
| BR-22 | Ngân sách AI theo tenant/phòng ban/agent; cảnh báo khi đạt 80% | BRD §4.4 | CONFIRMED | — | FR-AIQ-05, GAP-14 | PRD §5 | SRS-PRV-04 | N/A — ADR-011 | T-204 | TC-PRV-06 |

### 3.2. Data Capture & IDP — kênh, chức năng, hệ thống

**Kênh nhập liệu (BRD §3.2)**

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Nhập thủ công qua form, validate tức thì, AI gợi ý/tự điền | BRD §3.2 | CONFIRMED | MVP | FR-DC-01…06 | PRD §3.1 | SRS-CAP-30 | Chờ 2B | T-209 | TC-CAP-09 |
| C2 | Nhập bằng ngôn ngữ tự nhiên (text, voice) | BRD §3.2 | CONFIRMED | MVP | FR-DC-03 | PRD §3.1 | SRS-CAP-32 | API-CAP-03 | T-209 | TC-CAP-10 |
| C3 | Tải file lên (PDF text/scan, DOC/DOCX, JPG/PNG/HEIC/WEBP, XLS/XLSX/CSV) | BRD §3.2 | CONFIRMED | MVP | FR-DC-07 | PRD §3.1 | SRS-CAP-01 | API-DOC-01 | T-203 | TC-FILE-02 |
| C4 | Chụp ảnh trên mobile, tự căn góc, khử nghiêng | BRD §3.2 | CONFIRMED | MVP | UX-18, CON-08 | PRD §3.1 | SRS-CAP-08, SRS-CAP-09 | API-DOC-01 | T-206, T-212 | TC-CAP-14, TC-CAP-17 |
| C5 | Import hàng loạt Excel/CSV, AI map cột | BRD §3.2 | CONFIRMED | MVP | FR-DC-18 | PRD §3.1 | SRS-IMP-01 | API-IMP-01 | T-210 | TC-IMP-01, TC-IMP-04 |
| C6 | Email forwarding, hộp thư riêng theo tenant/phòng ban | BRD §3.2 | DEFERRED | Ph2 | CON-05, D-18 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| C7 | Chat integration (Zalo/Slack/Teams bot) | BRD §3.2 | DEFERRED | Ph2 | Q-17, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| C8 | Hóa đơn điện tử XML theo NĐ 123/2020 | BRD §3.2 | DEFERRED | Ph2 | CMP-04, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| C9 | Đồng bộ thư mục Google Drive/SharePoint | BRD §3.2 | DEFERRED | Ph2 | D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| C10 | API / Webhook từ hệ thống ngoài | BRD §3.2 | DEFERRED | Ph2 | GAP-09, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |

**Yêu cầu chức năng (BRD §3.5)** — ưu tiên P0 theo SC-01 trừ khi ghi khác.

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR-DC-01 | Form nhập sinh từ schema cho mọi entity; validate bắt buộc, định dạng, khoảng giá trị, tham chiếu master data | BRD §3.5 | CONFIRMED | P0 | US-DC-001 | US-DC-001, US-WRK-04 | SRS-CAP-30, SRS-WRK-04 | API-CAP-01, API-GOAL-03, API-WORK-03, API-WORK-04 | T-209, T-505 | TC-CAP-09, TC-WRK-04 |
| FR-DC-02 | AI gợi ý giá trị, tự điền (vd. cost center), cảnh báo bản ghi có khả năng trùng | BRD §3.5 | CONFIRMED | P0 | US-DC-001 | US-DC-001 | SRS-CAP-31 | API-CAP-02 | T-209 | TC-CAP-09 |
| FR-DC-03 | Nhập NL (text/voice) qua AI Assistant; luôn hiển thị bản ghi dự kiến để xác nhận trước khi ghi | BRD §3.5 | CONFIRMED | P0 | US-DC-002, UX-02 | US-DC-002 | SRS-CAP-32 | API-CAP-03 | T-209 | TC-CAP-10 |
| FR-DC-04 | Lưu nháp; sửa hàng loạt dạng grid | BRD §3.5 | CONFIRMED | P0 | GAP-07 | US-DC-001 | SRS-CAP-33 | API-CAP-04 | T-209 | TC-CAP-11 |
| FR-DC-05 | Audit thay đổi thủ công: ai, lúc nào, giá trị cũ/mới, lý do | BRD §3.5 | CONFIRMED | P0 | BR-15, D-25 | UX_Flows | SRS-AUD-01, SRS-CAP-34 | API-FIN-13 | T-008, T-209 | TC-AUD-01, TC-CAP-11 |
| FR-DC-06 | Giao diện nhập mobile cho check-in KPI/OKR, chi phí, task | BRD §3.5 | CONFIRMED | P0 | CON-14, UX-17 | US-GOAL-03 | SRS-GOAL-07 | API-GOAL-05 | T-501, T-906 (BLOCKED) | TC-GOAL-04 |
| FR-DC-07 | Định dạng nhận; ≤ 50 MB/file, ≤ 100 file/lần, PDF ≤ 300 trang (configurable) | BRD §3.5 | CONFIRMED | P0 | C3 | US-DC-003 | SRS-CAP-01 | API-DOC-01 | T-203 | TC-FILE-02 |
| FR-DC-08 | Tiền xử lý: quét mã độc, phát hiện file trùng bằng hash, xử lý ảnh, tách trang | BRD §3.5 | CONFIRMED | P0 | — | US-DC-003 | SRS-CAP-02, SRS-CAP-04, SRS-CAP-05, SRS-CAP-08 | API-DOC-01, API-DOC-03 | T-203, T-206 | TC-CAP-14, TC-FILE-01, TC-FILE-04, TC-FILE-07 |
| FR-DC-09 | AI tự phân loại loại tài liệu; người dùng có thể chọn trước | BRD §3.5 | CONFIRMED | P0 | MET-07 | US-DC-003 | SRS-CAP-10 | API-DOC-01 | T-206 | TC-CAP-01 |
| FR-DC-10 | Tách một file nhiều tài liệu; gộp nhiều ảnh thành một tài liệu | BRD §3.5 | CONFIRMED | P0 | — | UX_Flows | SRS-CAP-08, SRS-CAP-11 | API-REV-07 | T-206 | TC-CAP-14 |
| FR-DC-11 | Trích xuất trường đơn, bảng, checkbox, chữ ký/con dấu, văn bản tự do; tiếng Việt có dấu, tiếng Anh; chữ viết tay best-effort luôn review | BRD §3.5 | CONFIRMED | P0 | — | UX_Flows | SRS-CAP-12 | API-DOC-07 | T-206 | TC-CAP-02 |
| FR-DC-12 | Mỗi trường có: giá trị, độ tin cậy 0–1, vị trí nguồn (trang, tọa độ), đoạn văn bản gốc | BRD §3.5 | CONFIRMED | P0 | UX-13 | UX_Flows | SRS-CAP-13 | API-DOC-07 | T-202 | TC-CAP-02 |
| FR-DC-13 | Chuẩn hóa ngữ cảnh VN: ngày, số, tiền tệ, MST 10/13 số, SĐT, địa chỉ theo đơn vị hành chính mới | BRD §3.5 | CONFIRMED | P0 | GAP-13 | UX_Flows | SRS-CAP-14, SRS-FIN-01 | N/A — giao diện (UX Flows 2B) | T-206, T-403 | TC-CAP-03, TC-FIN-05 |
| FR-DC-14 | Kiểm tra nghiệp vụ: tổng tiền, ngày, MST, so khớp mờ master data, phát hiện trùng | BRD §3.5 | CONFIRMED | P0 / Ph2 (phần hóa đơn) | BR-19, CON-06 | UX_Flows | SRS-CAP-15 | N/A — giao diện (UX Flows 2B) | T-206, T-208 | TC-CAP-15 |
| FR-DC-15 | Định tuyến theo ngưỡng tin cậy (theo loại tài liệu và theo trường): straight-through hoặc hàng chờ review | BRD §3.5 | NEEDS_CONFIRMATION | P0 | CON-07, D-29 | UX_Flows | SRS-CAP-16 | N/A — giao diện (UX Flows 2B) | T-206, T-208 | TC-CAP-04, TC-CAP-05 |
| FR-DC-16 | Trường trọng yếu luôn cần người xác nhận giai đoạn đầu | BRD §3.5 | CONFIRMED | P0 | BR-03, GAP-08, D-16 | US-DC-006 | SRS-CAP-16, SRS-CAP-17, SRS-REV-04 | API-REV-03 | T-206, T-207, T-208 | TC-CAP-04, TC-CAP-05, TC-CAP-06, TC-REV-02 |
| FR-DC-17 | Ghi vào domain đích chỉ qua Tool Registry | BRD §3.5 | CONFIRMED | P0 | BR-04 | UX_Flows | SRS-CAP-18, SRS-GOAL-06, SRS-IMP-03, SRS-WRK-06 | API-IMP-04, API-REV-03 | T-206, T-210, T-302, T-501 (+2) | TC-CAP-08, TC-GOAL-03, TC-IMP-03, TC-WRK-07 |
| FR-DC-18 | Import Excel/CSV: map cột, xem trước, lỗi theo dòng, ghi dòng hợp lệ, xuất file lỗi | BRD §3.5 | CONFIRMED | P0 | US-DC-007, C5 | US-DC-007 | SRS-IMP-01 | API-IMP-01, API-IMP-02, API-IMP-03, API-IMP-04, API-IMP-05 | T-210 | TC-IMP-01, TC-IMP-04 |
| FR-DC-19 | Màn review song song: gốc trái, form phải; bấm trường tô sáng vùng nguồn | BRD §3.5 | CONFIRMED | P0 | US-DC-006, UX-13 | UX_Flows | SRS-REV-02 | API-DOC-05 | T-207 | TC-REV-07 |
| FR-DC-20 | Màu theo độ tin cậy; "Chấp nhận tất cả trường tin cậy cao"; điều hướng toàn bằng bàn phím | BRD §3.5 | CONFIRMED | P0 | UX-14, UX-15 | UX_Flows | SRS-REV-03, SRS-REV-04, SRS-REV-05 | API-REV-03 | T-207 | TC-REV-02, TC-REV-06, TC-REV-07 |
| FR-DC-21 | Hàng chờ review theo phòng ban/vai trò, có SLA, nhắc việc, escalation | BRD §3.5 | CONFIRMED | P0 | GAP-18 | UX_Flows | SRS-REV-01 | API-CFG-05, API-REV-01 | T-207 | TC-REV-01 |
| FR-DC-22 | Reviewer: sửa, từ chối (kèm lý do), đổi loại, tách/gộp, chuyển người khác | BRD §3.5 | CONFIRMED | P0 | GAP-07 | UX_Flows | SRS-REV-06 | API-REV-02, API-REV-04, API-REV-05, API-REV-06, API-REV-07 | T-207 | TC-REV-03 |
| FR-DC-23 | Bản ghi có liên kết "Xem tài liệu gốc"; AI trích dẫn đúng trang | BRD §3.5 | CONFIRMED | P0 | US-DC-011, UX-24 | UX_Flows | SRS-CAP-19 | API-DOC-04 | T-211 | TC-CAP-12 |

**Hệ thống, bảo mật, học từ chỉnh sửa**

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR-DCS-01 | Extraction Schema theo loại tài liệu (trường, kiểu, bắt buộc, quy tắc) do Admin cấu hình, không hard-code | BRD §3.4 | CONFIRMED | P0 | US-DC-008 | UX_Flows | SRS-CAP-15, SRS-CAP-17 | API-CFG-02, API-CFG-03 | T-206, T-208 | TC-CAP-06, TC-CAP-15 |
| FR-DCS-02 | Catalog loại tài liệu MVP: biên bản họp; kế hoạch/OKR/KPI; báo cáo kết quả định kỳ; danh sách nhân sự/sơ đồ tổ chức; SOP/chính sách | BRD §3.4 | CONFIRMED | MVP | — | UX_Flows | SRS-CAP-10, SRS-GOAL-01, SRS-WRK-05 | API-CFG-01, API-GOAL-01, API-GOAL-02, API-KNOW-01 | T-206, T-501, T-506, T-512 | TC-CAP-01, TC-CAP-13, TC-GOAL-01, TC-WRK-06 |
| FR-DCS-03 | Catalog loại tài liệu Phase 2: hóa đơn GTGT; biên lai/phiếu chi/tạm ứng; hợp đồng; báo giá/PO; sao kê; CV; danh thiếp; bảng chấm công | BRD §3.4 | DEFERRED | Ph2 | CON-06, D-17 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| FR-DCS-04 | Vòng đời tài liệu: UPLOADED → PROCESSING → EXTRACTED → NEEDS_REVIEW → APPROVED → COMMITTED; FAILED; REJECTED; SUPERSEDED | BRD §3.6 | NEEDS_CONFIRMATION | P0 | GAP-07, CON-12, D-14 | UX_Flows | SRS-CAP-20 | N/A — Architecture §8.5 | T-206 | TC-CAP-07 |
| FR-DCS-05 | Tools: upload_document, classify_document, extract_document, validate_extraction, submit_extraction_for_review, approve_extraction, commit_extraction, import_table, search_documents, get_source_document | BRD §3.9 | CONFIRMED | P0 | BR-09, D-26 | UX_Flows | SRS-AIC-01 | API-AI-03 | T-302 | TC-AIC-01, TC-AIC-04, TC-AIC-05 |
| FR-DCS-06 | Entities: SourceDocument, DocumentPage, DocumentType, ExtractionSchema, ExtractionJob, ExtractedField, ExtractionReview, ValidationRule, ImportBatch, DataLineage | BRD §3.9 | CONFIRMED | P0 | FR-DF-04 | UX_Flows | SRS-CAP-13, SRS-CAP-19 | N/A — Database_Design §6 | T-202, T-211 | TC-CAP-02, TC-CAP-12 |
| FR-DCS-07 | Data Capture Agent: phân loại, trích xuất, kiểm tra, đề xuất ghi | BRD §3.9 | CONFIRMED | P0 | BR-08 | UX_Flows | SRS-AIC-01 | N/A — ADR-008 | T-302 | TC-AIC-01, TC-AIC-04, TC-AIC-05 |
| FR-DCS-08 | Hành động AI sau khi ghi theo loại tài liệu (vd. tạo task từ biên bản, đề xuất cây alignment, dựng cây tổ chức) | BRD §3.4 | CONFIRMED | MVP / Ph2 | FR-AUT-02 | UX_Flows | SRS-GOAL-10, SRS-WRK-06 | N/A — ADR-008 | T-503, T-506 | TC-GOAL-09, TC-WRK-07 |
| SEC-DC-01 | Quyền tài liệu kế thừa người tải và entity đích | BRD §3.7 | CONFIRMED | P0 | BR-07, GAP-03 | PRD §3.1 | SRS-CAP-07 | API-DOC-04 | T-203 | TC-FILE-08 |
| SEC-DC-02 | Tự phát hiện, gắn nhãn dữ liệu cá nhân (CCCD, số TK, lương, sức khỏe); che khi không có quyền | BRD §3.7 | CONFIRMED | P0 | CMP-01 | US-PRV-01 | SRS-ACC-10 | API-DOC-04 | T-112, T-907 (BLOCKED) | TC-PRV-01, TC-PRV-02, TC-PRV-03 |
| SEC-DC-03 | Chống prompt injection qua tài liệu | BRD §3.7 | CONFIRMED | P0 | BR-06 | PRD §3.1 | SRS-AIC-09, SRS-CAP-22 | N/A — ADR-008 | T-206, T-302 | TC-AIC-06, TC-CAP-08 |
| SEC-DC-04 | Chọn nơi xử lý (model nội bộ/cloud) theo mức phân loại dữ liệu; dữ liệu mật chỉ xử lý tại VN (cấu hình) | BRD §3.7 | CONFIRMED | — | NFR-04, FR-AIQ-06 | PRD §3.1 | SRS-PRV-02 | N/A — ADR-011 | T-112, T-204 | TC-PRV-04, TC-SEC-06 |
| SEC-DC-05 | Chính sách lưu trữ file gốc theo loại | BRD §3.7 | CONFIRMED | — | BR-16, GAP-15 | PRD §3.1 | Chưa đặc tả | N/A — ADR-004 | Chưa có task (chưa đặc tả) | Chưa có test (chưa đặc tả) |
| FR-LRN-01 | Lưu mọi chỉnh sửa của reviewer làm ground truth theo loại tài liệu, NCC, mẫu | BRD §3.8, UX §6.2 | CONFIRMED | P0 | — | UX_Flows | SRS-REV-07 | API-REV-02 | T-202, T-207 | TC-REV-04 |
| FR-LRN-02 | Nhận biết mẫu lặp lại và cải thiện độ chính xác theo thời gian | BRD §3.8 | CONFIRMED | — | — | UX_Flows | Chưa đặc tả | Chờ 2B | Chưa có task (chưa đặc tả) | Chưa có test (chưa đặc tả) |
| FR-LRN-03 | Quy tắc nới ngưỡng tự ghi | BRD §3.8 | CONFIRMED | P0 | BR-05 | UX_Flows | SRS-CAP-16 | API-CFG-04 | T-206, T-208 | TC-CAP-04, TC-CAP-05 |

### 3.3. User stories và use case (Domain 22)

| ID | Mô tả ngắn | Nguồn | Trạng thái | Ưu tiên | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| US-DC-001 | Employee nhập qua form có kiểm tra tức thì, cảnh báo trùng, lưu nháp | BRD §5.1 | CONFIRMED | P0 | FR-DC-01/02/04 | US-DC-001 | SRS-CAP-30, SRS-CAP-31, SRS-CAP-33 | Chờ 2B | T-209 | TC-CAP-09, TC-CAP-11 |
| US-DC-002 | Manager nói/gõ một câu để AI tạo bản ghi; ghi sau khi xác nhận | BRD §5.1 | CONFIRMED | P0 | FR-DC-03 | US-DC-002 | SRS-CAP-32 | API-CAP-03 | T-209 | TC-CAP-10 |
| US-DC-003 | User tải PDF/Word/ảnh để AI trích xuất; phân loại đúng ≥ 95% loại tài liệu MVP | BRD §5.1 | CONFIRMED | P0 | FR-DC-07/09, MET-07, F2 | US-DC-003 | SRS-CAP-01, SRS-CAP-10, SRS-CAP-12, SRS-CAP-21 | API-DOC-01, API-DOC-02 | T-203, T-206 | TC-CAP-01, TC-CAP-02, TC-CAP-16, TC-FILE-02 |
| US-DC-004 | Manager tải biên bản họp Word → task có owner, deadline, link đoạn gốc | BRD §5.1 | CONFIRMED | P0 | UC-06, F3 | US-WRK-01 | SRS-WRK-01, SRS-WRK-07 | API-WORK-01, API-WORK-05, API-WORK-06 | T-505, T-506 | TC-WRK-01, TC-WRK-07 |
| US-DC-005 | Manager tải kế hoạch KPI/OKR → dựng KPI/Objective/KR; duyệt trước khi kích hoạt | BRD §5.1 | CONFIRMED | P0 | FR-DCS-02, GAP-04, D-24 | US-GOAL-01 | SRS-GOAL-03, SRS-GOAL-04, SRS-GOAL-05 | API-GOAL-01, API-GOAL-02, API-GOAL-04, API-GOAL-06 | T-501, T-502, T-503 | TC-GOAL-02, TC-GOAL-07, TC-GOAL-08, TC-GOAL-09 |
| US-DC-006 | Reviewer xem gốc cạnh dữ liệu trích; tô sáng, màu tin cậy; ≤ 60 giây/tài liệu | BRD §5.1 | CONFIRMED | P0 | FR-DC-19/20, MET-04, F2 | US-DC-006 | SRS-REV-02, SRS-REV-03, SRS-REV-04, SRS-REV-05 | API-REV-01 | T-207 | TC-REV-02, TC-REV-06, TC-REV-07 |
| US-DC-007 | Admin import danh sách nhân sự từ Excel: map cột, lỗi theo dòng, ghi dòng hợp lệ | BRD §5.1 | CONFIRMED | P0 | FR-DC-18, UC-07 | US-DC-007 | SRS-IMP-02 | API-IMP-01, API-ORG-02 | T-210 | TC-IMP-02 |
| US-DC-008 | Admin cấu hình loại tài liệu, schema, ngưỡng tự ghi theo trường, không cần code | BRD §5.1 | CONFIRMED | P0 | FR-DCS-01, CON-07 | US-DC-008 | SRS-CAP-15, SRS-CAP-16, SRS-CAP-17 | API-CFG-02 | T-206, T-208 | TC-CAP-04, TC-CAP-05, TC-CAP-06, TC-CAP-15 |
| US-DC-009 | Finance chụp/tải hóa đơn → chi phí, công nợ; khớp tổng; phát hiện trùng; trường tiền luôn review | BRD §5.1 | DEFERRED | P1 | CON-06, D-17 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| US-DC-010 | Legal/Sales tải hợp đồng → giá trị, mốc thanh toán, hạn gia hạn; nhắc việc | BRD §5.1 | DEFERRED | P1 | FR-EXT-03, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| US-DC-011 | CEO bấm mọi con số AI báo cáo để xem nguồn gốc tới bản ghi và trang tài liệu | BRD §5.1 | CONFIRMED | P0 | FR-DF-04, UX-03 | US-DC-011 | SRS-BRF-04 | API-ORG-03 | T-211, T-510 | TC-CAP-12 |
| US-DC-012 | Bộ phận chuyển tiếp email có đính kèm → vào hàng xử lý đúng phòng ban | BRD §5.1 | DEFERRED | P1 | C6, CON-05, D-18 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| UC-06 | Biên bản họp (giấy/Word) → AI trích quyết định, việc → khớp nhân sự → thư ký duyệt → task, lịch, thông báo, Decision Log | BRD §5.2 | CONFIRMED | P0 | F3, GAP-10, D-31 | US-WRK-01 | SRS-ACC-11, SRS-WRK-06, SRS-WRK-11 | API-ORG-02, API-WORK-01, API-WORK-02, API-WORK-06 | T-108, T-201, T-506, T-905 (BLOCKED) | TC-ACC-09, TC-WRK-07, TC-WRK-08 |
| UC-07 | Onboarding doanh nghiệp trong một ngày: sơ đồ tổ chức, nhân sự, kế hoạch, KPI → CEO có dashboard đầu tiên | BRD §5.2 | CONFIRMED | P0 | US-DC-005/007 | PRD §3.1 | SRS-GOAL-03, SRS-IMP-01, SRS-IMP-02 | API-ORG-01 | T-210, T-502, T-503 | TC-GOAL-08, TC-GOAL-09, TC-IMP-01, TC-IMP-02 (+1) |
| UC-08 | Hóa đơn → kiểm tra trùng, khớp PO → Finance duyệt → công nợ → dự báo dòng tiền → CEO Briefing nếu runway dưới ngưỡng | BRD §5.2 | DEFERRED | P1 | CON-06, FR-EXT-02, D-17 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |

### 3.4. Data Foundation, Autonomy, chỉ số, AI quality, tuân thủ, mở rộng

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FR-DF-01 | Master Data Management: Employee, Customer, Partner, Vendor, Product, Project có nguồn gốc chỉ định, data owner, khử trùng, merge | BRD §4.1 | CONFIRMED | P0 (cơ bản) | BR-02 | UX_Flows | SRS-CAP-31 | Chờ 2B | T-209 | TC-CAP-09 |
| FR-DF-02 | Data Quality Score theo domain (đầy đủ, chính xác, kịp thời, nhất quán) | BRD §4.1 | CONFIRMED | — | BR-20 | UX_Flows | Chưa đặc tả | Chờ 2B | Chưa có task (chưa đặc tả) | Chưa có test (chưa đặc tả) |
| FR-DF-03 | Data Freshness: mọi chỉ số hiển thị thời điểm cập nhật; Briefing nêu dữ liệu cũ | BRD §4.1 | CONFIRMED | P0 | UX-26 | US-BRF-01, US-FNL-05 | SRS-BRF-03, SRS-BRF-10, SRS-FIN-14 | API-FIN-14, API-INS-01 | T-406, T-510, T-511 | TC-BRF-03, TC-BRF-08, TC-FIN-29 |
| FR-DF-04 | Data Lineage: từ con số trên báo cáo truy ngược tới bản ghi, người nhập, tài liệu gốc | BRD §4.1 | CONFIRMED | P0 | US-DC-011 | US-DC-011 | SRS-CAP-19 | API-ORG-03 | T-211 | TC-CAP-12 |
| FR-DF-05 | Event backbone: mọi thay đổi nghiệp vụ phát sự kiện (vd. invoice.created, kpi.measured, task.overdue) | BRD §4.1 | CONFIRMED | — | GAP-06 | UX_Flows | SRS-JOB-01, SRS-WRK-09 | N/A — ADR-005 (outbox; danh mục sự kiện chờ 2B) | T-009, T-507 | TC-JOB-01, TC-JOB-02, TC-JOB-04, TC-WRK-09 |
| FR-DF-06 | Semantic layer / Metric store: định nghĩa chỉ số một lần, dùng chung dashboard, báo cáo, AI | BRD §4.1 | CONFIRMED | — | FR-HM-02 | UX_Flows | SRS-BRF-05 | Chờ 2B | T-510 | TC-BRF-02 |
| FR-AUT-01 | Định nghĩa 5 mức L0 Inform, L1 Suggest, L2 Draft & Confirm, L3 Act & Notify, L4 Autonomous | BRD §4.2 | CONFIRMED | P0 (L0–L3) | CON-02, D-11 | UX_Flows | SRS-AIC-02, SRS-AIC-03 | API-AI-07 | T-301, T-302 | TC-AIC-02, TC-AIC-03 |
| FR-AUT-02 | Level cấu hình theo tool × vai trò × ngưỡng giá trị | BRD §4.2 | CONFIRMED | P0 | GAP-08 | US-AIC-04 | SRS-AIC-02, SRS-AIC-15 | API-AI-04, API-AI-05 | T-301, T-302, T-305 | TC-AIC-02, TC-AIC-12 |
| FR-AUT-03 | Hoàn tác ≥ 24 giờ cho L3; với dữ liệu tài chính chỉ bằng bút toán đảo liên kết bản gốc, không xóa lịch sử/audit | BRD §4.2 | CONFIRMED | P0 | BR-11, CON-12, UX-41, D-13, D-14 | UX_Flows | SRS-AIC-10, SRS-FIN-10 | API-AI-11, API-FIN-12 | T-304, T-405 | TC-AIC-10, TC-FIN-23, TC-FIN-24, TC-FIN-25 (+2) |
| FR-AUT-04 | Kill switch chỉ Admin; hạ L3/L4 về L2; kiểm tra ở cổng ghi backend | BRD §4.2 | CONFIRMED | P0 | BR-13, CON-04, UX-29, D-09, D-10 | UX_Flows | SRS-AIC-04 | N/A — giao diện (UX Flows 2B) | T-303 | TC-KS-01, TC-KS-02 |
| FR-HM-01 | Bộ chỉ số sức khỏe mặc định, doanh nghiệp tinh chỉnh được | BRD §4.3 | CONFIRMED | — | CON-09 | UX_Flows | SRS-BRF-02 | N/A — giao diện (UX Flows 2B) | T-510 | TC-BRF-01 |
| FR-HM-02 | Chỉ số có công thức và ngưỡng, dùng chung cho Dashboard, Briefing, AI | BRD §4.3 | CONFIRMED | — | FR-DF-06 | UX_Flows | SRS-BRF-05 | N/A — giao diện (UX Flows 2B) | T-510 | TC-BRF-02 |
| FR-HM-03 | Nhóm Tài chính: tăng trưởng DT, biên LN gộp/EBITDA, cash runway, DSO/DPO/CCC, công nợ quá hạn, chênh lệch ngân sách | BRD §4.3 | PROPOSED | — | CON-09, GAP-16 | US-FNL-05 | SRS-FIN-15 | N/A — giao diện (UX Flows 2B) | T-407 (BLOCKED) | TC-FIN-31 (BLOCKED) |
| FR-HM-04 | Nhóm Khách hàng: pipeline coverage, tỷ lệ chuyển đổi/chu kỳ bán, NRR/churn, tập trung DT, CAC/LTV/NPS | BRD §4.3 | PROPOSED | — | CON-09 | UX_Flows | SRS-SLS-02 | N/A — giao diện (UX Flows 2B) | T-901 (BLOCKED) | Chưa có test |
| FR-HM-05 | Nhóm Vận hành: hoàn thành đúng hạn, dự án trễ, thực thi quyết định | BRD §4.3 | PROPOSED | — | CON-09 | US-WRK-03 | SRS-WRK-02 | N/A — giao diện (UX Flows 2B) | T-505 | TC-WRK-02 |
| FR-HM-06 | Nhóm Con người: DT/nhân sự và chi phí NS/DT, tỷ lệ nghỉ việc, quá tải | BRD §4.3 | PROPOSED | — | CON-09 | UX_Flows | Chưa đặc tả | N/A — giao diện (UX Flows 2B) | T-902 (BLOCKED) | Chưa có test (chưa đặc tả) |
| FR-HM-07 | Nhóm Chiến lược: strategy execution index | BRD §4.3 | NEEDS_CONFIRMATION | — | CON-09, D-28 | UX_Flows | Chưa đặc tả | N/A — giao diện (UX Flows 2B) | Chưa có task (chưa đặc tả) | Chưa có test (chưa đặc tả) |
| FR-AIQ-01 | Evaluation Engine: bộ test chuẩn mỗi agent và loại câu hỏi; chạy lại trước mọi thay đổi model/prompt | BRD §4.4 | CONFIRMED | — | — | UX_Flows | SRS-AIC-16 | N/A — ADR-013 | T-307 | TC-AIC-16 |
| FR-AIQ-02 | Grounding bắt buộc | BRD §4.4 | CONFIRMED | — | BR-14, UX-24 | UX_Flows | SRS-AIC-12, SRS-BRF-10 | API-AI-12 | T-306, T-511 | TC-AIC-13, TC-AIC-14, TC-BRF-08 |
| FR-AIQ-03 | Confidence có hiệu chỉnh; chưa hiệu chỉnh thì dùng Cao/TB/Thấp kèm lý do | BRD §4.4 | CONFIRMED | — | UX-25 | UX_Flows | SRS-AIC-12 | Chờ 2B | T-306 | TC-AIC-13, TC-AIC-14 |
| FR-AIQ-04 | Phản hồi đúng/sai và lý do trên mọi câu trả lời, khuyến nghị; vào Evaluation Engine | BRD §4.4 | CONFIRMED | — | UX-28 | US-AIC-06 | SRS-AIC-14 | API-AI-13 | T-307 | TC-AIC-16 |
| FR-AIQ-05 | Model routing theo độ phức tạp; ngân sách AI; báo cáo chi phí AI trên mỗi quyết định | BRD §4.4 | CONFIRMED | — | BR-22 | UX_Flows | SRS-PRV-04 | N/A — ADR-011 | T-204 | TC-PRV-06 |
| FR-AIQ-06 | Model Gateway model-agnostic; hỗ trợ model on-premise cho dữ liệu mật | BRD §4.4 | CONFIRMED | — | SEC-DC-04, GAP-06, D-07, D-08 | UX_Flows | SRS-PRV-01, SRS-PRV-02 | N/A — ADR-011 | T-112, T-204, T-205 (BLOCKED) | TC-PRV-04, TC-PRV-07, TC-SEC-06 |
| CMP-01 | Bảo vệ dữ liệu cá nhân (NĐ 13/2023, Luật BVDLCN): consent, phân loại nhạy cảm, quyền truy cập/xóa, hồ sơ đánh giá tác động | BRD §4.5 | CONFIRMED | — | SEC-DC-02, GAP-15 | US-PRV-01 | SRS-ACC-10, SRS-PRV-02 | N/A — ADR-011, Architecture §6 | T-112, T-204, T-907 (BLOCKED) | TC-PRV-01, TC-PRV-02, TC-PRV-03, TC-PRV-04 (+1) |
| CMP-02 | Kiểm soát chuyển dữ liệu ra nước ngoài khi dùng AI cloud | BRD §4.5 | CONFIRMED | — | SEC-DC-04, NFR-04 | PRD §3.1 | SRS-PRV-02 | N/A — ADR-011 | T-112, T-204 | TC-PRV-04, TC-SEC-06 |
| CMP-03 | Ghi âm họp: thông báo, cơ chế từ chối, chính sách lưu trữ và xóa | BRD §4.5 | DEFERRED | P1 | SC-06, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| CMP-04 | Hóa đơn điện tử theo NĐ 123/2020 và văn bản sửa đổi | BRD §4.5 | DEFERRED | Ph2 | C8, D-17 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| CMP-05 | Lưu trữ chứng từ theo Luật Kế toán | BRD §4.5 | CONFIRMED | — | BR-16 | PRD §3.1 | N/A — N/A | N/A — ADR-004 | N/A — N/A | N/A — N/A |
| CMP-06 | Tích hợp phần mềm kế toán (MISA, Fast, Bravo…), không thay thế | BRD §4.5 | CONFIRMED | — | BR-18, FR-EXT-06 | PRD §3.1 | N/A — N/A | N/A — không tích hợp trong MVP (D-31) | N/A — N/A | N/A — N/A |
| CMP-07 | Chữ ký số cho phê duyệt có giá trị pháp lý | BRD §4.5 | DEFERRED | Ph2+ | D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| FR-EXT-01 | Workflow Engine tổng quát, cấu hình bằng giao diện hoặc NL; AI là một bước | BRD §4.6 | DEFERRED | P1 | SC-10, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| FR-EXT-02 | Domain Procurement/Vendor: NCC, đề nghị mua, PO, nghiệm thu, đánh giá NCC | BRD §4.6 | DEFERRED | P1 | SC-10, CON-01, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| FR-EXT-03 | Contract Lifecycle: entity xuyên domain, nghĩa vụ, mốc, gia hạn; AI nhắc hạn, cảnh báo điều khoản bất lợi | BRD §4.6 | DEFERRED | P1 | US-DC-010, CON-01, D-02 | PRD §3.2–3.3 | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED | N/A — DEFERRED |
| FR-EXT-04 | Decision Log: quyết định, lý do, phương án loại, người quyết, kết quả kỳ vọng; AI đối chiếu sau 30/60/90 ngày | BRD §4.6 | CONFIRMED | — | UC-06, F1 | UX_Flows | SRS-WRK-11 | N/A — giao diện (UX Flows 2B) | T-506, T-905 (BLOCKED) | TC-WRK-08 |
| FR-EXT-05 | Scenario planning (what-if trên dữ liệu thực) | BRD §4.6 | CONFIRMED | — | — | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| FR-EXT-06 | Tích hợp VN: Zalo/Zalo OA, MISA, ngân hàng, cổng hóa đơn điện tử, Microsoft 365, Google Workspace | BRD §4.6 | CONFIRMED | — | GAP-10 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |

### 3.5. Yêu cầu phi chức năng (NFR)

| ID | Mô tả ngắn | Nguồn | Trạng thái | Phase | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NFR-01 | Tài liệu ≤ 5 trang: trích xuất p95 ≤ 60 giây; xử lý bất đồng bộ, thông báo khi xong | BRD §5.3 | CONFIRMED | MVP | — | PRD §6 | SRS-CAP-21, SRS-NFR-01 | N/A — ADR-005 | T-206, T-604 (BLOCKED) | TC-CAP-16, TC-PERF-01 |
| NFR-02 | Thông lượng ≥ 1.000 trang/giờ/tenant ở MVP, mở rộng ngang | BRD §5.3 | CONFIRMED | MVP | GAP-05 | PRD §6 | SRS-NFR-02 | N/A — ADR-005 | T-604 (BLOCKED) | TC-PERF-02 |
| NFR-03 | RPO ≤ 15 phút, RTO ≤ 4 giờ cho core platform | BRD §5.3 | CONFIRMED | — | — | PRD §6 | SRS-NFR-03 | N/A — ADR-004, Architecture §9.3 | T-005, T-605 | TC-DR-01, TC-DR-02, TC-MIG-01, TC-MIG-02 |
| NFR-04 | Cấu hình vùng lưu trữ; tùy chọn lưu trữ và xử lý tại Việt Nam | BRD §5.3 | CONFIRMED | — | SEC-DC-04 | PRD §6 | SRS-NFR-04 | N/A — ADR-011, ADR-004 | T-003, T-013 | TC-NFR-01 |
| NFR-05 | Giao diện và AI tiếng Việt, tiếng Anh; hiểu câu hỏi trộn hai ngôn ngữ | BRD §5.3 | CONFIRMED | — | UX-37, UX-38 | PRD §6 | SRS-GEN-06, SRS-NFR-05 | N/A — ADR-003 | T-111, T-607 | TC-GEN-07, TC-NFR-02 |
| NFR-06 | Mobile: chụp tài liệu, duyệt, check-in, hỏi AI (PWA hoặc app) | BRD §5.3 | NEEDS_CONFIRMATION | — | CON-08, D-27 | PRD §6 | SRS-NFR-06 | N/A — ADR-003 | T-608 | TC-NFR-03 |
| NFR-07 | Khả dụng AI: tự chuyển model dự phòng; nhập thủ công luôn hoạt động | BRD §5.3 | CONFIRMED | — | BR-21 | PRD §6 | SRS-BRF-12, SRS-NFR-07, SRS-PRV-03 | N/A — ADR-011 | T-204, T-510 | TC-BRF-07, TC-NFR-04, TC-PRV-05 |
| NFR-08 | WCAG 2.1 AA | UX §9.2 | PROPOSED | — | UX-36 | PRD §6 | SRS-NFR-08 | N/A — ADR-003 | T-607 | TC-NFR-05 |

### 3.6. Chỉ số đo lường (MET)

| ID | Chỉ số | Mục tiêu | Nguồn | Trạng thái | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MET-01 | Field accuracy | ≥ 90% chung; ≥ 95% tài liệu có lớp text | BRD §3.8 | CONFIRMED | FR-LRN-01 | Business_OKRs | SRS-NFR-09 | N/A — chỉ số đo lường | T-606 | TC-NFR-06 |
| MET-02 | Straight-through rate | ≥ 50% sau 3 tháng | BRD §3.8 | CONFIRMED | FR-DC-15 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-03 | Time to data | p50 ≤ 5 phút (chưa tính chờ review) | BRD §3.8 | CONFIRMED | NFR-01 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-04 | Review effort | ≤ 60 giây/tài liệu | BRD §3.8, US-DC-006 | CONFIRMED | MET-13, D-20 | Business_OKRs | SRS-NFR-10, SRS-REV-09 | N/A — chỉ số đo lường | T-202, T-207 | TC-NFR-07, TC-REV-04 |
| MET-05 | Chi phí / tài liệu | Theo dõi từ ngày đầu, có ngân sách trần `[TBD]` | BRD §3.8 | NEEDS_CONFIRMATION | GAP-14, GAP-14 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-06 | Error leakage | < 0,5% trường trọng yếu | BRD §3.8 | CONFIRMED | — | Business_OKRs | SRS-NFR-09 | N/A — chỉ số đo lường | T-606 | TC-NFR-06 |
| MET-07 | Độ chính xác phân loại loại tài liệu MVP | ≥ 95% | BRD US-DC-003 | CONFIRMED | FR-DC-09 | Business_OKRs | SRS-NFR-09 | N/A — chỉ số đo lường | T-606 | TC-NFR-06 |
| MET-08 | Giảm thời gian nhập liệu (BO-08) | ≥ 70% so với nhập tay | BRD §3.1 | CONFIRMED | BO-08 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-09 | Độ chính xác trường trọng yếu sau review | ≥ 99% | BRD §3.1 | CONFIRMED | — | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-10 | Adoption: WAU/tổng user; % KPI cập nhật đúng hạn; % dữ liệu vào qua AI capture | ≥ 70%; ≥ 90%; `[TBD]` | BRD §5.3 | CONFIRMED | CHG-01…03 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-11 | Giờ/tuần CEO tiết kiệm cho tổng hợp báo cáo; thời gian từ phát hiện rủi ro đến hành động | ≥ 5 giờ; `[TBD]` | BRD §5.3 | CONFIRMED | — | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-12 | Thời gian đến insight đầu tiên của CEO | ≤ 10 giây | UX §10.1, U1 | PROPOSED | F1 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-13 | Thời gian review một hóa đơn 6 trường | ≤ 60 giây | UX §10.1 | NEEDS_CONFIRMATION | CON-06, MET-04, D-20 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-14 | Tỷ lệ hoàn thành F1–F5 không cần hỗ trợ | ≥ 90% | UX §10.1 | PROPOSED | F1…F5 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-15 | Điểm SUS | ≥ 75 (sau 30 ngày) | UX §10.1 | PROPOSED | — | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-16 | Tỷ lệ quản lý dùng hàng tuần | ≥ 80% | UX §10.1 | PROPOSED | MET-10 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-17 | Action card L2 được xác nhận không sửa | ≥ 60% và tăng dần | UX §10.1 | PROPOSED | UX-05 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-18 | Tỷ lệ hoàn tác hành động L3 | ≤ 5% | UX §10.1 | PROPOSED | UX-27 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |
| MET-19 | Tỷ lệ câu trả lời AI được mở nguồn | Theo dõi, không ngưỡng | UX §10.1 | PROPOSED | UX-24 | Business_OKRs | N/A — N/A | N/A — chỉ số đo lường | N/A — N/A | N/A — N/A |

### 3.7. UX — nguyên tắc, luồng, yêu cầu giao diện

Toàn bộ mục này là `PROPOSED` (đề xuất thiết kế) trừ khi ghi khác.

**Nguyên tắc (UX §3)**

| ID | Nguyên tắc | Kiểm tra nhanh | Liên quan |
| --- | --- | --- | --- |
| U1 | Ngoại lệ trước, chi tiết sau | CEO trả lời "có gì cần tôi?" trong 10 giây | MET-12, UX-12 |
| U2 | Hỏi ở bất kỳ đâu | Không cần chuyển trang để hỏi | UX-02, UX-22 |
| U3 | Mọi con số có nguồn | Không có con số "mồ côi" | UX-03, FR-DF-04 |
| U4 | AI hiển thị trạng thái thật | Luôn trả lời được "AI vừa làm gì?" | UX-05, UX-21, UX-27 |
| U5 | Nhập một lần, nhập ở đâu cũng được | Cập nhật task ≤ 10 giây; gửi chứng từ ≤ 3 chạm trên mobile | UX-04, BR-02 |
| U6 | Hành động ngay tại chỗ | Không có cảnh báo "chỉ để xem" | UX-12 |
| U7 | Hai mật độ cho hai kiểu người | Reviewer xử lý hoàn toàn bằng bàn phím | UX-40 |
| U8 | Tiếng Việt là mặc định | Không có nhãn dịch máy gượng gạo | UX-37 |

**Luồng chính (UX §5)**

| ID | Luồng | Mục tiêu | Nguồn liên kết | Trạng thái | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | CEO buổi sáng: Briefing → giao việc | ≤ 2 phút, ≤ 5 chạm | UC-01, UC-03 (v1.0) | PROPOSED | GAP-01, FR-EXT-04 | US-BRF-04, US-WRK-05 | SRS-BRF-01, SRS-BRF-07, SRS-BRF-11, SRS-NTF-01 (+2) | API-INS-01, API-AI-07, API-AI-09 | T-010, T-506, T-508, T-510 (+2) | TC-BRF-01, TC-BRF-05, TC-BRF-09, TC-BRF-11 (+4) |
| F2 | Gửi tài liệu và AI trích xuất | Gửi ≤ 3 chạm; review ≤ 60 giây | US-DC-003, 006 | PROPOSED | CON-05, D-18 | UX_Flows | SRS-CAP-01, SRS-CAP-21, SRS-REV-04 | API-DOC-01, API-REV-01, API-REV-03 | T-203, T-206, T-207 | TC-CAP-16, TC-FILE-02, TC-REV-02 |
| F3 | Biên bản họp thành việc | ≤ 10 phút kể cả duyệt | UC-06 (UC-02 v1.0) | PROPOSED | CON-11 | UX_Flows | SRS-ACC-11, SRS-WRK-05, SRS-WRK-06, SRS-WRK-07 | API-WORK-02, API-WORK-06 | T-108, T-201, T-506 | TC-ACC-09, TC-WRK-06, TC-WRK-07 |
| F4 | Check-in KPI/OKR của nhân viên | ≤ 30 giây | US-OKR-006 (v1.0) | PROPOSED | GAP-01 | US-GOAL-03 | SRS-GOAL-07, SRS-GOAL-08, SRS-GOAL-11, SRS-NTF-01 | API-GOAL-05 | T-010, T-501, T-504, T-906 (BLOCKED) | TC-GOAL-04, TC-GOAL-06, TC-GOAL-10, TC-NTF-01 |
| F5 | Manager xử lý cảnh báo quá tải | ≤ 1 phút | US-TASK-003/004 (v1.0) | PROPOSED | GAP-01, BR-10 | US-WRK-05 | SRS-WRK-12 | N/A — chưa đặc tả (Q-34) | T-902 (BLOCKED), T-903 (BLOCKED) | Chưa có test |

**Yêu cầu giao diện**

| ID | Mô tả ngắn | Nguồn | Trạng thái | Liên quan | PRD | SRS | API | Task | Test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UX-01 | Trang chủ theo vai trò, lấy ngoại lệ làm trung tâm; nội dung theo vai trò (UX §4.1) | UX §1, §4.1 | PROPOSED | CON-13 | UX_Flows | SRS-BRF-01 | N/A — giao diện (UX Flows 2B) | T-510 | TC-BRF-01 |
| UX-02 | Thanh AI toàn cục (⌘K/Ctrl+K): tìm kiếm, hỏi, ra lệnh, nhập bằng lời, thả file; gợi ý theo màn hình | UX §1, §7.2 | PROPOSED | FR-DC-03 | US-AIC-05 | SRS-AIC-12 | API-AI-12 | T-306 | TC-AIC-13, TC-AIC-14 |
| UX-03 | Mọi con số bấm được: popover công thức, nguồn, thời điểm cập nhật, bản ghi, tài liệu gốc | UX §1, U3 | PROPOSED | US-DC-011 | UX_Flows | SRS-BRF-04 | API-ORG-03 | T-211, T-510 | TC-CAP-12 |
| UX-04 | Vùng thả file toàn cục; Hộp thư dữ liệu; AI đoán đích đến theo ngữ cảnh | UX §1, U5 | PROPOSED | C3 | UX_Flows | SRS-CAP-01 | API-DOC-01 | T-203 | TC-FILE-02 |
| UX-05 | Mỗi Autonomy Level một mẫu giao diện cố định (insight card, suggestion chip, action card, undo toast, báo cáo hoạt động) | UX §7.1 | PROPOSED | FR-AUT-01, CON-02, D-11 | UX_Flows | SRS-AIC-07, SRS-AIC-11 | API-AI-08, API-AI-09 | T-304 | TC-AIC-07, TC-AIC-08, TC-AIC-09, TC-AIC-17 |
| UX-06 | Mobile tập trung 4 việc: Briefing, hỏi AI, chụp/gửi tài liệu, duyệt | UX §1, §6.3 | PROPOSED | NFR-06 | UX_Flows | SRS-NFR-06 | N/A — giao diện (UX Flows 2B) | T-608 | TC-NFR-03 |
| UX-07 | IA theo việc người dùng làm: 8 mục điều hướng + Quản trị riêng | UX §4 | NEEDS_CONFIRMATION | CON-01, GAP-17, D-23 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-08 | Mục không có quyền thì ẩn hẳn | UX §4.2 | PROPOSED | GAP-03 | UX_Flows | SRS-ACC-09 | API-AUTH-07 | T-108, T-111 | TC-ACC-02 |
| UX-09 | Người đa vai trò đổi ngữ cảnh ở thanh trên; Trang chủ đổi theo | UX §4.2 | PROPOSED | CON-13 | UX_Flows | SRS-ACC-05 | API-AUTH-07 | T-107, T-109 | TC-ACC-04 |
| UX-10 | Breadcrumb theo chuỗi nghiệp vụ Chiến lược › Objective › KR › Dự án › Task (P06) | UX §4.2 | PROPOSED | GAP-01 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-11 | Trang chi tiết entity cùng bố cục; tab Tổng quan, Liên kết, Lịch sử, Tài liệu gốc, Hoạt động AI; panel AI phải | UX §4.2 | PROPOSED | — | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-12 | Trang chủ CEO: dòng tóm tắt; 4 ô chỉ số chọn được (mặc định doanh thu, dòng tiền, OKR, task trễ); "Cần anh quyết" trên "Rủi ro"; "AI đã làm"; panel AI | UX §6.1 | PROPOSED | CON-09 | UX_Flows | SRS-BRF-01 | API-INS-01, API-INS-02 | T-510 | TC-BRF-01 |
| UX-13 | Review: liên kết hai chiều trường ↔ vùng trên bản gốc | UX §6.2 | PROPOSED | FR-DC-19 | UX_Flows | SRS-REV-02 | N/A — giao diện (UX Flows 2B) | T-207 | TC-REV-07 |
| UX-14 | Độ tin cậy 3 mức màu + hình (● ◐ ○); mặc định ≥ 90 / 60–89 / < 60; chỉnh theo loại tài liệu | UX §6.2 | NEEDS_CONFIRMATION | CON-07, ASM-05, D-29 | UX_Flows | SRS-REV-03 | N/A — giao diện (UX Flows 2B) | T-207 | TC-REV-07 |
| UX-15 | Con trỏ nhảy vào trường cần xem trước; trường trọng yếu luôn phải đi qua; tài liệu kế tiếp mở ngay | UX §6.2 | PROPOSED | BR-03 | US-DC-006 | SRS-REV-04, SRS-REV-05 | N/A — giao diện (UX Flows 2B) | T-207 | TC-REV-02, TC-REV-06 |
| UX-16 | AI nêu lý do không chắc ("ảnh mờ") thay vì chỉ phần trăm | UX §6.2 | PROPOSED | — | UX_Flows | SRS-CAP-13 | API-DOC-07 | T-202 | TC-CAP-02 |
| UX-17 | Mobile: tab dưới 4 mục, nút + (chụp chứng từ, ghi âm, cập nhật task, check-in) | UX §6.3 | PROPOSED | FR-DC-06 | UX_Flows | SRS-NFR-06 | N/A — giao diện (UX Flows 2B) | T-608 | TC-NFR-03 |
| UX-18 | Chụp chứng từ chạy nền, nhận cạnh, chụp nhiều trang, báo khi xong | UX §6.3 | PROPOSED | C4 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-19 | Thẻ duyệt mobile; vuốt duyệt hàng loạt mục rủi ro thấp; sinh trắc học cho mục tài chính trên ngưỡng | UX §6.3 | NEEDS_CONFIRMATION | CON-08, GAP-08, D-27, D-16 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-20 | Ngoại tuyến: xếp hàng ảnh chụp và cập nhật task, nhãn "chưa đồng bộ" | UX §6.3 | NEEDS_CONFIRMATION | CON-08, D-27 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-21 | Một từ vựng trạng thái ("AI gợi ý", "AI soạn", "AI đã làm"); màu `ai` chỉ cho nội dung do AI tạo | UX §7.1, §8.2 | PROPOSED | U4 | UX_Flows | SRS-AIC-11 | N/A — giao diện (UX Flows 2B) | T-304 | TC-AIC-17 |
| UX-22 | Panel AI theo ngữ cảnh, hiển thị "AI đang xem: …" | UX §7.2 | PROPOSED | U2 | UX_Flows | SRS-AIC-12 | API-AI-12 | T-306 | TC-AIC-13, TC-AIC-14 |
| UX-23 | Trạng thái đang nghĩ hiện các bước thật; streaming; nút Dừng | UX §7.2 | PROPOSED | — | UX_Flows | SRS-AIC-12 | API-AI-12 | T-306 | TC-AIC-13, TC-AIC-14 |
| UX-24 | Source chip trích dẫn trên mỗi khẳng định; mở bản ghi/tài liệu gốc đúng đoạn | UX §7.2 | PROPOSED | FR-AIQ-02, FR-DC-23 | US-AIC-05 | SRS-AIC-12 | API-AI-12 | T-306 | TC-AIC-13, TC-AIC-14 |
| UX-25 | Nhãn độ tin cậy Cao/TB/Thấp trong hội thoại; phần trăm chỉ ở màn Review | UX §7.2 | PROPOSED | FR-AIQ-03 | UX_Flows | SRS-AIC-12, SRS-REV-03 | N/A — giao diện (UX Flows 2B) | T-207, T-306 | TC-AIC-13, TC-AIC-14, TC-REV-07 |
| UX-26 | Nhãn độ tươi dữ liệu, cảnh báo khi quá ngưỡng của chỉ số | UX §7.2 | PROPOSED | FR-DF-03 | UX_Flows | SRS-BRF-03 | N/A — giao diện (UX Flows 2B) | T-510 | TC-BRF-03 |
| UX-27 | Feed "AI đã làm": timeline L3/L4, lọc, lý do, nút Hoàn tác | UX §7.2 | PROPOSED | CON-02, CON-12, D-11 | US-BRF-03 | SRS-BRF-08 | API-AI-07 | T-510 | TC-BRF-06 |
| UX-28 | Phản hồi một chạm 👍/👎 và "Sai ở đâu?" trên câu trả lời và bản trích xuất | UX §7.2 | PROPOSED | FR-AIQ-04 | US-AIC-06 | SRS-AIC-14 | API-AI-13 | T-307 | TC-AIC-16 |
| UX-29 | Kill switch trong AI Control Center, **chỉ Admin** (D-09 bỏ quyền CEO của UX §7.2); L3/L4 → L2; băng thông báo | UX §7.2 | CONFIRMED | CON-04, D-09 | UX_Flows | SRS-AIC-04 | N/A — giao diện (UX Flows 2B) | T-303 | TC-KS-01, TC-KS-02 |
| UX-30 | AI nói "chưa có dữ liệu" kèm gợi ý; nguồn mâu thuẫn hiện cả hai, người chọn, ghi Lineage | UX §7.3 | PROPOSED | FR-DF-04 | US-AIC-05 | SRS-AIC-13, SRS-BRF-06 | N/A — giao diện (UX Flows 2B) | T-306, T-510 | TC-AIC-15, TC-BRF-04 |
| UX-31 | Design token: Be Vietnam Pro (dự phòng Inter), cỡ chữ, lưới 4 px, bo góc, độ sâu, chuyển động, màu ngữ nghĩa | UX §8.1, §8.2 | PROPOSED | Q-18 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-32 | Thư viện thành phần (cơ bản, dữ liệu, AI, nhập liệu, điều hướng); xây trên shadcn/ui + Radix | UX §8.3 | PROPOSED | ASM-04, GAP-06, D-06 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-33 | Quy tắc trực quan hóa: tiêu đề là kết luận, luôn có đường kế hoạch, đơn vị rút gọn kiểu Việt, điểm dữ liệu bấm được | UX §8.4 | PROPOSED | — | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-34 | Điểm ngắt: ≥ 1440 / 1280–1439 / 768–1279 / < 768 px | UX §9.1 | NEEDS_CONFIRMATION | CON-14, D-33 | UX_Flows | SRS-NFR-06 | N/A — giao diện (UX Flows 2B) | T-608 | TC-NFR-03 |
| UX-35 | MVP web responsive + PWA, chưa native | UX §9.1 | NEEDS_CONFIRMATION | CON-08, Q-12, D-27 | UX_Flows | SRS-NFR-06 | N/A — giao diện (UX Flows 2B) | T-608 | TC-NFR-03 |
| UX-36 | WCAG 2.1 AA: tương phản, bàn phím, trình đọc màn hình, bảng dữ liệu thay thế biểu đồ, vùng chạm ≥ 44 px | UX §9.2 | PROPOSED | NFR-08 | UX_Flows | SRS-NFR-08 | N/A — giao diện (UX Flows 2B) | T-607 | TC-NFR-05 |
| UX-37 | Tiếng Việt mặc định; định dạng tiền, ngày, phần trăm VN/EN | UX §9.3, U8 | PROPOSED | NFR-05 | UX_Flows | SRS-GEN-06 | N/A — giao diện (UX Flows 2B) | T-111 | TC-GEN-07 |
| UX-38 | AI trả lời bằng ngôn ngữ người dùng hỏi | UX §9.3 | PROPOSED | NFR-05 | UX_Flows | SRS-AIC-12 | N/A — giao diện (UX Flows 2B) | T-306 | TC-AIC-13, TC-AIC-14 |
| UX-39 | Cách AI xưng hô do Admin cấu hình | UX §9.3 | PROPOSED | Q-19 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-40 | Hai mật độ Thoáng/Gọn trên cùng component | UX §3, §8.1 | PROPOSED | U7 | UX_Flows | N/A — N/A | N/A — giao diện (UX Flows 2B) | N/A — N/A | N/A — N/A |
| UX-41 | Undo toast 10 giây, tạm dừng khi hover/focus; sau đó Hoàn tác trong feed 24 giờ | UX §7.1, §9.2 | PROPOSED | FR-AUT-03 | US-AIC-03 | SRS-AIC-10 | N/A — giao diện (UX Flows 2B) | T-304 | TC-AIC-10 |

### 3.8. Change management (CHG)

| ID | Mô tả ngắn | Nguồn | Trạng thái | Liên quan |
| --- | --- | --- | --- | --- |
| CHG-01 | Mỗi phòng ban có một "AI champion" | BRD §5.3 | CONFIRMED | MET-10 |
| CHG-02 | Chương trình đào tạo 2 giờ cho nhân viên | BRD §5.3 | CONFIRMED | MET-10 |
| CHG-03 | Chạy song song Excel ≤ 4 tuần, CEO công bố chuyển đổi | BRD §5.3 | CONFIRMED | BR-17 |

### 3.9. Phạm vi và ưu tiên MVP (SC, BRD §6.1)

| ID | Năng lực | v1.0 | v1.1 | Trạng thái | Liên quan |
| --- | --- | --- | --- | --- | --- |
| SC-01 | Data Capture: nhập tay, NL, upload PDF/Word/ảnh/Excel, review | — | P0 | CONFIRMED | §3.2, §3.3, CON-10 |
| SC-02 | Data Foundation cơ bản (master data, freshness, lineage) | — | P0 | CONFIRMED | FR-DF-01, 03, 04 |
| SC-03 | AI Autonomy L0–L3 + kill switch | — | P0 | CONFIRMED | FR-AUT-01…04 |
| SC-04 | Finance Lite (doanh thu, chi phí, tiền mặt, runway; nhập tay hoặc import) | P1 | P0 | NEEDS_CONFIRMATION | GAP-04, CON-06, D-24 |
| SC-05 | Sales Pipeline Lite | P1 | P0 | NEEDS_CONFIRMATION | GAP-04, D-24 |
| SC-06 | Meeting: AI join Google Meet | P0 | P1 | DEFERRED | UC-06 thay thế ở MVP, D-02 |
| SC-07 | Performance Cycle đầy đủ | P0 | P1 | DEFERRED | CON-11, D-02 |
| SC-08 | Risk Intelligence (bản đầu dùng ngưỡng chỉ số sức khỏe) | P1 | P1 | DEFERRED | FR-HM-01, D-02 |
| SC-09 | Hóa đơn, hợp đồng, email capture, XML hóa đơn | — | P1 | DEFERRED | CON-05, CON-06, D-17, D-18 |
| SC-10 | Procurement/Vendor, Workflow Engine | — | P1 | DEFERRED | FR-EXT-01, 02, D-02 |
| SC-11 | Governance | P2 | P2 | DEFERRED | GAP-01, D-02 |

Module lõi được BRD §6 ngầm giữ ở P0 nhưng không có trong bảng §6.1: KPI/OKR + check-in, Task, CEO Briefing/Dashboard → `[TBD]` (GAP-04).

## 4. Bảng chéo

### 4.1. User story ↔ FR ↔ Use case ↔ Luồng UX

| User story | FR-DC | Use case | Luồng UX | Chỉ số |
| --- | --- | --- | --- | --- |
| US-DC-001 | 01, 02, 04, 05 | — | — | — |
| US-DC-002 | 03 | — | (UX-02) | — |
| US-DC-003 | 07, 08, 09, 10, 11, 12, 13 | UC-07 | F2 | MET-07 |
| US-DC-004 | 09, 11, 17 | UC-06 | F3 | — |
| US-DC-005 | 09, 11, 17 | UC-07 | — | — |
| US-DC-006 | 19, 20, 21, 22 | — | F2 | MET-04, MET-13 |
| US-DC-007 | 18 | UC-07 | — | — |
| US-DC-008 | 15, 16 (+ FR-DCS-01) | — | — | — |
| US-DC-009 | 14, 16 | UC-08 | (UX-18) | — |
| US-DC-010 | 11, 17 | — | — | — |
| US-DC-011 | 23 (+ FR-DF-04) | — | F1 | MET-19 |
| US-DC-012 | (C6) | UC-08 | F2 | — |
| — (chưa có US) | 06 | — | F4 | — |

### 4.2. Autonomy level ↔ mặc định ↔ mẫu giao diện

| Level | Mặc định cho (BRD §4.2) | Mẫu UI (UX §7.1) | MVP | Ghi chú |
| --- | --- | --- | --- | --- |
| L0 Inform | Mọi tool READ | Insight card | Có | — |
| L1 Suggest | Phân bổ nguồn lực | Suggestion chip | Có | F5 |
| L2 Draft & Confirm | Ghi dữ liệu tài chính, giao tiếp bên ngoài | Action card | Có | D-12; kill switch hạ L3 về đây (D-09) |
| L3 Act & Notify | Task, lịch, nhắc việc nội bộ | Undo toast + feed 24h | Có (mức cao nhất MVP) | D-11; không áp dụng cho dữ liệu tài chính (D-12) |
| L4 Autonomous | Không bật trong MVP | Báo cáo hoạt động tuần | **Không** | D-11: không triển khai trong MVP |

### 4.3. Kênh ↔ Phase ↔ ưu tiên user story

| Kênh | Phase (BRD §3.2) | User story | Ưu tiên US | Khớp? |
| --- | --- | --- | --- | --- |
| C1 | MVP | US-DC-001 | P0 | Có |
| C2 | MVP | US-DC-002 | P0 | Có |
| C3 | MVP | US-DC-003…006 | P0 | Có |
| C4 | MVP | US-DC-009 (gián tiếp) | P1 → DEFERRED | C4 vẫn MVP cho tài liệu MVP; chụp hóa đơn/biên lai Phase 2 (D-17) |
| C5 | MVP | US-DC-007 | P0 | Có |
| C6 | Ph2 | US-DC-012 | P1 → DEFERRED | Đã giải quyết: Phase 2, bỏ nhánh email khỏi F2 (D-18) |
| C7–C10 | Ph2 | — | — | — |

## 5. Thống kê

Không có dòng nào ở trạng thái `IMPLEMENTED`/`VERIFIED`: AI-EOS chưa có code (D-04).

| Nhóm | Số ID | CONFIRMED | PROPOSED | NEEDS_CONFIRMATION | DEFERRED |
| --- | --- | --- | --- | --- | --- |
| BR | 22 | 21 | 0 | 0 | 1 |
| C (kênh) | 10 | 5 | 0 | 0 | 5 |
| FR-DC | 23 | 22 | 0 | 1 | 0 |
| FR-DCS | 8 | 6 | 0 | 1 | 1 |
| SEC-DC | 5 | 5 | 0 | 0 | 0 |
| FR-LRN | 3 | 3 | 0 | 0 | 0 |
| US-DC | 12 | 9 | 0 | 0 | 3 |
| UC | 3 | 2 | 0 | 0 | 1 |
| FR-DF | 6 | 6 | 0 | 0 | 0 |
| FR-AUT | 4 | 4 | 0 | 0 | 0 |
| FR-HM | 7 | 2 | 4 | 1 | 0 |
| FR-AIQ | 6 | 6 | 0 | 0 | 0 |
| CMP | 7 | 4 | 0 | 0 | 3 |
| FR-EXT | 6 | 3 | 0 | 0 | 3 |
| NFR | 8 | 6 | 1 | 1 | 0 |
| MET | 19 | 10 | 7 | 2 | 0 |
| U (nguyên tắc) | 8 | 0 | 8 | 0 | 0 |
| F (luồng) | 5 | 0 | 5 | 0 | 0 |
| UX | 41 | 1 | 34 | 6 | 0 |
| CHG | 3 | 3 | 0 | 0 | 0 |
| SC | 11 | 3 | 0 | 2 | 6 |
| **Tổng** | **217** | **121** | **59** | **14** | **23** |

Ngoài ma trận: 19 CON, 25 GAP, 8 ASM, 27 Q (Source_Analysis §7–§10 và Decision_Log §1.3, §5). Trạng thái từng mục: Decision_Log §3.

## 6. ID tham chiếu tới BRD v1.0 (không có nguồn)

Các ID dưới đây được nhắc trong nguồn nhưng nội dung nằm ở BRD v1.0. Giữ nguyên ID để tránh xung đột khi nhận được BRD v1.0; nội dung `[TBD — nguồn không có]` (GAP-01).

| Nhóm | ID được nhắc | Nơi nhắc |
| --- | --- | --- |
| Use case | UC-01, UC-02, UC-03 | UX §5 (F1, F3), BRD §5.2, §6.1 |
| CEO | US-CEO-001…008 | UX §2.1, §2.2 |
| KPI | US-KPI-001…010 | UX §2.1, §2.2 |
| OKR | US-OKR-001…003, 005…009 | UX §2.1, §2.2 |
| Task | US-TASK-001…004, 006 | UX §2.1, §2.2, F5 |
| Meeting | US-MTG-002 | UX §2.1, §2.2 |
| Tổ chức | US-ORG-002…004 | UX §2.1, §2.2 |
| AI | US-AI-004…008 | UX §2.1, §2.2 |
| Performance | US-PERF-001 | UX §2.2 |
| Finance | US-FIN-003 | UX §2.2 |
| Sales | US-SAL-004 | UX §2.2 |
| Strategy | US-STR-003 | UX §2.1 |
| Nguyên tắc | P01…P08 (P06 Traceability được nhắc) | UX §4.2 |
| Mục BRD v1.0 | §5, 7.6, 9.2, 34, 37–42, 44, 46, 47, 50, 75–77, 82, 87–89, 91 | BRD §2–§6 |

## 7. Cập nhật checkpoint 2A

### 7.1. Thay đổi trạng thái

- Toàn bộ `XN` → `CONFIRMED` (D-01: BRD v1.1 đã được duyệt; nội dung kiểm chứng được trong `BRD_Review.md`).
- `TBD`, `ASSUMPTION` → `NEEDS_CONFIRMATION`, trừ UX-32 → `PROPOSED` (D-06).
- Các dòng `CONFLICT` được giải theo quyết định: BR-12, BR-13, FR-AUT-01, FR-AUT-03, FR-AUT-04, UX-29 → `CONFIRMED` (D-09, D-11, D-13); C6, US-DC-009, US-DC-012, BR-19, FR-DCS-03, SC-09 → `DEFERRED` (D-17, D-18); FR-DC-15, UX-14, NFR-06, UX-19, UX-20, UX-34, UX-35, FR-HM-07, MET-13 → `NEEDS_CONFIRMATION`.
- Yêu cầu P1/Phase 2 có căn cứ (C7–C10, US-DC-010, UC-08, CMP-03, CMP-04, CMP-07, FR-EXT-01…03, SC-06…SC-11) → `DEFERRED` theo D-02 (chỉ mô tả mức roadmap). Ưu tiên gốc trong cột Phase giữ nguyên.
- Mô tả được sửa theo quyết định của chủ dự án: BR-13, FR-AUT-03, FR-AUT-04, UX-29 (ghi rõ D-xx trong mô tả).
- Không đổi, không xóa, không tái sử dụng ID nào.

### 7.2. (Đã rút lại ở 0.3) Hiện thực liên quan trong A-EMS

Bản 0.2 liệt kê code của dự án cũ `Final_Project/A-EMS` có liên quan tới FR-AIQ-02, BR-14, UX-24, FR-AIQ-04, UX-28, FR-AIQ-06, UX-23, FR-DF-05, FR-DF-01, BR-21, NFR-07, SC-04, SC-05. Bảng này **bị rút lại** theo D-04, D-05: A-EMS không phải implementation hay baseline của AI-EOS. Trạng thái các dòng trên không thay đổi vì bản 0.2 chưa từng nâng chúng lên `IMPLEMENTED`.

### 7.3. Giới hạn

- Nhận định ở bản 0.2 về hiện trạng code dựa trên đọc tĩnh repo A-EMS; không còn được dùng cho AI-EOS.
- Cột PRD/SRS/API/Task/Test vẫn `—`; sẽ điền ở 2B–2D, dùng `N/A — <lý do>` khi không áp dụng.

## 8. Cập nhật 0.3 (hiệu chỉnh checkpoint 2A)

- Không đổi, không thêm, không xóa requirement ID (vẫn 217). Không đổi trạng thái dòng nào.
- Làm rõ căn cứ của `CONFIRMED` (có nguồn vs quyết định CDA) và `PROPOSED` (nguồn UX vs đề xuất phân tích) — mục 1.
- Rút lại bảng "Hiện thực liên quan trong A-EMS" (mục 7.2) và các câu ngụ ý A-EMS là implementation của AI-EOS (mục 5, 7.3).
- Tham chiếu `D-xx` trong ma trận vẫn hợp lệ; nội dung một số quyết định đã đổi ở Decision_Log 0.2 (D-06, D-15, D-19, D-21, D-22, D-24) nhưng không làm đổi trạng thái dòng nào trong ma trận.

## 9. Cập nhật 0.4 (Stage 2C)

- Không đổi, không thêm, không xóa requirement ID (vẫn 217). **Không đổi trạng thái** dòng nào: các quyết định chốt ngày 12/10/2026 (Decision_Log 0.5) chỉ cụ thể hóa thiết kế cho các dòng đã `CONFIRMED`; không dòng nào lên `IMPLEMENTED`/`VERIFIED` vì chưa có code.
- Cột API được điền cho 195 dòng có cột downstream: 71 dòng trỏ tới endpoint, 116 dòng `N/A` kèm lý do hoặc ADR/kiến trúc thay thế, 8 dòng `Chờ 2B` (chưa có đặc tả để thiết kế API — chủ yếu module D-24 và yêu cầu Data Foundation chi tiết).
- Dòng `DEFERRED`: `N/A — DEFERRED` cho API/Task/Test; PRD/SRS ghi `Roadmap (2B)`.
- Bảng nguyên tắc U1–U8, CHG, SC không có cột downstream; độ phủ kiến trúc của SC: SC-01 → Architecture §8.5, API-DOC/REV/IMP/CAP; SC-02 → API-ORG-03, Database_Design §6; SC-03 → ADR-008; SC-04 → ADR-009, API-FIN; SC-05 → SKELETON (D-24).
- **Sai lệch quy trình:** Stage 2B chưa thực hiện; cột PRD/SRS chưa thể điền. Khi 2B hoàn thành phải rà lại cột API và các endpoint `SKELETON`.

## 10. Cập nhật 0.5 (Stage 2B)

### 10.1. Thay đổi
- Không đổi, không xóa requirement ID (vẫn 217 trong §3); **không đổi trạng thái** dòng nào.
- Cột PRD, SRS được điền cho 195 dòng có cột downstream: 141 dòng trỏ tới SRS, 49 dòng `N/A` có lý do (DEFERRED, chỉ số, UI, vận hành), 5 dòng `Chưa đặc tả` (mục 10.4).
- Sửa lỗi truy vết từ 0.4: dòng luồng UX F1–F4 bị gán nhầm API tài chính do trùng mã với quy tắc tài chính `F1–F7` của CDA. Quy tắc tài chính nay ghi `CDA-F1…CDA-F7` (Decision_Log, ký hiệu); cột API của F1–F5 được tính lại.

### 10.2. ID mới của Stage 2B (đăng ký, không phải requirement nguồn)

| Loại | ID | Định nghĩa | Nguồn gốc |
| --- | --- | --- | --- |
| User story | US-IAM-01…04, US-GOAL-01…04, US-WRK-01…05, US-BRF-01…04, US-FNL-01…05, US-SLS-01, US-AIC-01…06, US-PRV-01 | PRD §4 | Mỗi story ghi requirement nguồn/quyết định ngay trong dòng |
| Yêu cầu phần mềm | SRS-GEN, SRS-IAM, SRS-ACC, SRS-CAP, SRS-REV, SRS-IMP, SRS-GOAL, SRS-WRK, SRS-BRF, SRS-FIN, SRS-SLS, SRS-AIC, SRS-JOB, SRS-NTF, SRS-AUD, SRS-PRV, SRS-NFR | SRS | Cột "Nguồn" của từng dòng |
| Luồng | FL-01…FL-15 | UX_Flows | Mỗi flow liệt kê SRS/PRD |
| Hành trình | J1…J8 | User_Journeys | UX F1–F5, UC-06, UC-07 |
| Câu hỏi | Q-28…Q-42 | Decision_Log §7 | NEEDS_CONFIRMATION |
| Đề xuất amendment | AMD-01, AMD-02 | SRS §15.2 | PROPOSED |
| Thay đổi 2C | C-01…C-05 | SRS §15.1 | Đã áp dụng vào Database_Design 1.1, API_Specification 1.1 |

### 10.3. Độ phủ theo module (Source → PRD → SRS → UX → API → Data → AC)

| Module | PRD | SRS | UX Flow | API | Data | AC | Trạng thái đặc tả |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M1 Tài khoản, quyền | US-IAM-01…04 | SRS-IAM, SRS-ACC | FL-01…03, FL-13 | API-AUTH, API-ADM | `identity`, `access` | SRS §3–4, AC-ARCH-05, 09 | Đầy đủ (trừ R6) |
| M2 Data Capture | US-DC-001…008, 011 | SRS-CAP, SRS-REV, SRS-IMP | FL-04…06 | API-DOC, REV, CAP, IMP, CFG | `capture`, `org` | SRS §5, AC-ARCH-08, 11 | Đầy đủ (ngưỡng/trường trọng yếu chờ D-16, D-29) |
| M3 KPI/OKR | US-GOAL-01…04 | SRS-GOAL | FL-15 | API-GOAL-01…06 | `goals` | SRS §6 | Một phần (Q-28…Q-32) |
| M4 Task, biên bản | US-WRK-01…05 | SRS-WRK | FL-08 | API-WORK-01…06 | `work` | SRS §7 | Một phần (Q-33…Q-35, Q-41) |
| M5 CEO Briefing | US-BRF-01…04 | SRS-BRF | FL-07 | API-INS-01, 02 | `insights` | SRS §8 | Một phần (Q-36, Q-37) |
| M6 Finance Lite | US-FNL-01…05 | SRS-FIN | FL-11, FL-12 | API-FIN-01…14 | `finance` | SRS §9, AC-ARCH-01, 02, 06 | Đầy đủ (Q-39, Q-40, Q-42; người giữ `finance.period.manage`) |
| M7 Sales Lite | US-SLS-01 | SRS-SLS | — | API-SALES-01 (SKELETON) | — | — | **Chưa đặc tả** (Q-38) |
| M8 AI control | US-AIC-01…06 | SRS-AIC, SRS-PRV, SRS-JOB | FL-09, FL-10 | API-AI-01…13 | `ai`, `jobs` | SRS §11, AC-ARCH-03, 04, 11 | Đầy đủ (provider D-08) |
| Chung | — | SRS-NTF, SRS-AUD, SRS-NFR | FL-14, §0 | API-NOT, API-SYS, API-ADM-10 | `audit`, `notify` | SRS §12–13, AC-ARCH-07, 10, 12 | Đầy đủ |

### 10.4. Requirement chưa đặc tả trong SRS

FR-DF-02, FR-HM-06, FR-HM-07, FR-LRN-02, SEC-DC-05 — lý do ở SRS §17. Không có requirement P0 nào thiếu ánh xạ mà không có lý do.

### 10.5. Chưa truy vết được
- Cột Task, Test: chờ Stage 2D.
- Requirement của BRD v1.0 (§6): không có nội dung, không truy vết được (D-01).

## 11. Cập nhật 0.6 (Stage 2D)

- Không đổi, không xóa requirement ID (vẫn 217); **không đổi trạng thái** dòng nào. Không dòng nào `IMPLEMENTED`/`VERIFIED` (chưa có code, chưa chạy test).
- Cột Task, Test điền cho 178 dòng không DEFERRED có cột downstream: 142 dòng có task, 139 dòng có test case; còn lại `N/A` có lý do (chỉ số, UI, vận hành) hoặc `Chưa đặc tả`. Dòng DEFERRED giữ `N/A — DEFERRED`.
- Requirement chỉ có task bị chặn: FR-HM-03, FR-HM-04, FR-HM-06, NFR-02, F5.
- Requirement có SRS nhưng chưa có task/test: FR-HM-04 (test), F5 (test).
- Cột API được cập nhật cộng dồn theo API_Specification 1.2 (endpoint mới của 2B/2D: API-GOAL, API-WORK, API-INS, API-CAP…); giữ nguyên giá trị `N/A` và phần sửa tay cho F1–F5.
- Quyết định Stage 2D ảnh hưởng ma trận: D-37 (AMD-01), D-38 (AMD-02), D-39, D-40 — chỉ đổi thiết kế/kế hoạch, không đổi trạng thái requirement. SC-05 giữ `NEEDS_CONFIRMATION`; triển khai bị chặn (T-901).

## 12. Cập nhật 0.6.1 (T-001)

- T-001 (khung repo) `DONE` (commit `318689c`, GitHub Actions run `38257197546`) — Implementation_Plan §10. T-001 chỉ truy vết tới ADR-001, ADR-002, ADR-003; không dòng nào trong ma trận có cột Task chứa T-001, nên không có trạng thái requirement nào thay đổi.
- Không requirement nào `IMPLEMENTED`/`VERIFIED`; không test case nào trong TEST_Plan được chạy (test cấu trúc của T-001 không thuộc TEST_Plan).
- T-002 (toolchain + CI) `DONE` (branch protection `main`, PR đỏ #2 bị chặn merge, GitHub Actions xanh) — Implementation_Plan §10. T-002 không có dòng trong ma trận và không có TC trong TEST_Plan; không trạng thái requirement nào thay đổi; mọi TC vẫn `NOT RUN`.
- T-012 (nền tảng frontend) `IN_REVIEW` (14/10/2026) — Implementation_Plan §10. T-012 chỉ truy vết tới ADR-003; không dòng nào trong ma trận có cột Task chứa T-012, nên không trạng thái requirement nào thay đổi. Các task phụ thuộc T-012 (T-111, T-207, T-212, T-409, T-504, T-509) vẫn `TODO`; mọi TC vẫn `NOT RUN` (test của T-012 chưa đăng ký trong TEST_Plan).
- 14/10/2026 (D-42, D-43): thêm task T-013 (Compose — tích hợp); dòng NFR-04 cột Task thêm T-013 (TC-NFR-01 cần stack chạy được, thuộc T-013). T-005 đổi dependency (T-002, T-004). Không trạng thái requirement nào thay đổi; mọi TC vẫn `NOT RUN`.
- T-004 (cấu hình và secret, module `platform`) `DONE` (14/10/2026, PR #8, run `38541183244`) — Implementation_Plan §10, §13. T-004 chỉ truy vết tới ADR-006, ADR-011; không dòng nào trong ma trận có cột Task chứa T-004 → không trạng thái requirement nào thay đổi.
- T-005 (nền CSDL, module `platform`) `IN_REVIEW` (14/10/2026, PR #9) — Implementation_Plan §10, §14. Dòng NFR-03 (Task T-005, T-605) giữ trạng thái: RPO/RTO chưa đo (T-605); Q-51 về phạm vi TC nghiệm thu T-005.
- T-011 (storage adapter, module `storage`) `IN_REVIEW` (14/10/2026) — Implementation_Plan §10, §15. T-011 không có ở cột Task của ma trận → không trạng thái requirement nào thay đổi; Q-51 về TC-FILE-03.
- T-006 (log JSON, correlation ID, health; module `platform`, `app`) `IN_REVIEW` (14/10/2026) — Implementation_Plan §10, §16. T-006 không có ở cột Task của ma trận → không trạng thái requirement nào thay đổi; Q-51 về TC-GEN-05, TC-SEC-05.
