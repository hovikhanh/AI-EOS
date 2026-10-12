# AI-EOS — Documentation Review (cuối Stage 2D)

> Phiên bản: 1.0 · Ngày: 12/10/2026 · Người lập: coding agent (Claude Code) · Trạng thái: **Chờ CDA duyệt trước khi triển khai code**
> Phạm vi: toàn bộ `docs/`, `CLAUDE.md`, `scripts/check_docs.py` của `AI-EOS/`. Không có code ứng dụng để đối chiếu.

## 1. Danh sách tài liệu

| Stage | File | Trạng thái |
| --- | --- | --- |
| Nguồn | `00-source/BRD_Review.md`, `00-source/UI_UX_Proposal.md` | Không sửa (md5 kiểm tra bằng script) |
| 1 / 2A | `00-source/Source_Analysis.md` (0.2), `00-source/Requirements_Traceability.md` (0.6), `00-source/Decision_Log.md` (0.7), `00-source/Pre2C_Decision_Proposals.md` (0.2, hồ sơ lịch sử) | Cập nhật xuyên suốt, có lịch sử phiên bản |
| 2B | `01-strategy/Product_Vision.md`, `01-strategy/Business_OKRs.md`, `02-requirements/Personas.md`, `User_Journeys.md`, `PRD.md` (1.1), `SRS.md` (1.1), `UX_Flows.md` (1.1) | Tạo ở 2B, cập nhật ở 2D theo D-37…D-40 |
| 2C | `03-architecture/Architecture.md` (1.2), `Database_Design.md` (1.2), `API_Specification.md` (1.2), `decisions/ADR-001…013` | ADR-005, ADR-008, ADR-009 có Amendment 1 |
| 2D | `04-delivery/Implementation_Plan.md`, `TEST_Plan.md`, `Documentation_Review.md`, `../CLAUDE.md`, `../scripts/check_docs.py` | Tạo mới |

## 2. Quyết định đã chốt (theo nguồn thẩm quyền)

| Nguồn | Quyết định |
| --- | --- |
| `CDA` | D-01…D-05, D-07, D-09, D-11…D-13, D-17, D-18, D-37 (AMD-01), D-38 (AMD-02 theo phiên bản CDA) |
| `CDA_DIRECTIVE` | D-10 (K1–K6), D-14 (CDA-F1…F7), D-21 (R1–R8, trừ R6), D-22 (A1–A6), D-32 (in-app), D-39 (mặc định tạm thời Q-28/29/36/37), D-40 (Sales Lite chưa triển khai) |
| `ARCHITECTURE_DECISION` | D-06 (ADR-001…013), D-25, D-26, D-27 (PWA), D-30 (đăng nhập nội bộ + MFA Admin), diễn giải K2, phân loại `job_class`, trạng thái `ON_HOLD` |

## 3. Quyết định còn mở

| ID | Nội dung | Mặc định an toàn hiện hành |
| --- | --- | --- |
| D-08 | Provider LLM/OCR | Adapter + benchmark dữ liệu tổng hợp (TEST_Plan §9); dữ liệu nhạy cảm chỉ provider local |
| D-16, D-29 | Trường trọng yếu, ngưỡng | Mọi trường tiền là trọng yếu; tự ghi tắt |
| R6 | Người giữ quyền dữ liệu nhân sự nhạy cảm | Không ai giữ; dữ liệu bị che |
| Q-28 | Ai kích hoạt mục tiêu | `goals.activate` chỉ qua assignment, không quyền nền |
| Q-29, Q-37 | % đạt, công thức ô chỉ số | Không tính %; ô có nhãn "chưa chính thức", không cảnh báo |
| Q-30, Q-31, Q-32, Q-33, Q-34, Q-35, Q-36, Q-39, Q-41, Q-42 | Chi tiết nghiệp vụ M3–M6 | Xem Decision_Log §7 |
| Q-38 | Sales Lite | Không triển khai (D-40) |
| D-20, D-23, D-28, D-31, D-33 | Chỉ số review, danh sách domain, bộ chỉ số, lịch, mobile | Như Decision_Log |
| Người giữ `finance.period.manage` | Vận hành | Chỉ giao được cho `CFO`; chưa giao → không mở kỳ, cảnh báo Admin |

## 4. Xung đột đã xử lý

| Xung đột | Xử lý |
| --- | --- |
| CON-01…CON-14 (giữa hai nguồn) | Đã giải quyết hoặc ghi mặc định an toàn (Decision_Log §5) |
| CON-15…CON-19 (dự án cũ A-EMS) | Đóng, `[LEGACY FINDING — A-EMS]`; AI-EOS độc lập |
| Trùng mã `F1–F7` (quy tắc tài chính CDA) với luồng UX `F1–F5` | Ký hiệu `CDA-F1…CDA-F7` trong cột truy vết; sửa ánh xạ API sai của F1–F4 trong traceability (phát hiện ở 2B) |
| AMD-02 đề xuất (Briefing chạy khi kill switch bật) vs phiên bản CDA (chặn) | Áp dụng phiên bản CDA; SRS-BRF-11 đảo lại; ADR-005/008 Amendment 1 |
| AMD-01: "kỳ bị đóng trước khi duyệt" vs thiết kế cấm khóa kỳ còn giao dịch chờ duyệt | Giữ phòng ngừa; thêm `ON_HOLD` làm lớp phòng thủ (ADR-009 Amendment 1) |
| Tiêu đề §4 Decision_Log còn ghi PROPOSED sau khi D-21 chốt | Thêm ghi chú hiện hành |

## 5. Độ phủ traceability

Số liệu từ Requirements_Traceability §9–§11 (do script tính khi điền):

| Chặng | Kết quả |
| --- | --- |
| Requirement trong ma trận | 217 ID, không đổi; không dòng nào `IMPLEMENTED`/`VERIFIED` |
| → SRS | 141 dòng có SRS; 49 `N/A` có lý do; 5 "chưa đặc tả" (FR-DF-02, FR-HM-06, FR-HM-07, FR-LRN-02, SEC-DC-05 — không P0) |
| → API | 72 dòng trỏ endpoint (cập nhật cộng dồn theo API_Specification 1.2, thêm 10 tham chiếu endpoint mới); còn lại `N/A` có lý do, ADR thay thế, hoặc DEFERRED |
| → Task | 142 dòng có task; FR-HM-03, FR-HM-04, FR-HM-06, NFR-02, F5 chỉ có task BLOCKED |
| → Test | 139 dòng có test case (`NOT RUN`); FR-HM-04, F5 chưa có test vì bị chặn |
| AC-ARCH-01…12 | Mỗi AC ánh xạ tới ≥ 1 TC (TEST_Plan §11) |

## 6. Khác biệt tài liệu và code

Không có code AI-EOS để đối chiếu. Mọi API ở trạng thái `DESIGNED`/`SKELETON`; mọi task `TODO`; mọi test `NOT RUN`. Code A-EMS không được dùng làm bằng chứng (D-04, D-05).

## 7. Giới hạn và nội dung chưa xác minh

- Toàn văn BRD v1.1 không có; nội dung ngoài hai file nguồn là `[CẦN XÁC NHẬN]`.
- Persona là giả thuyết (ASM-01); wireframe gốc bị mất (GAP-12); không có prototype.
- Không chỉ tiêu nào đã được đo: field accuracy, thông lượng, latency, RPO/RTO, SUS.
- Mermaid chỉ được kiểm tra cú pháp (parser), không kiểm tra hiển thị.
- Script kiểm tra tài liệu chỉ phát hiện lỗi cấu trúc/tham chiếu, không đánh giá đúng sai nghiệp vụ.

## 8. Kiểm tra đã chạy ở Stage 2D

Đã chạy: `python3 scripts/check_docs.py --mermaid-modules <scratchpad>` → 0 lỗi, 0 cảnh báo (33 file, 58 link, 172 tham chiếu mục, 217 requirement, 18/18 sơ đồ Mermaid). Kiểm tra âm: bản sao có lỗi cố ý về link, ID, quyền, trạng thái, phạm vi, task/test, nguồn → script phát hiện đủ. Lệnh tái lập: `python3 scripts/check_docs.py --mermaid-modules <dir có mermaid, jsdom>`.

## 9. Cần CDA phê duyệt trước khi triển khai code

1. Implementation_Plan và TEST_Plan (thứ tự giai đoạn, task READY/PARTIAL/BLOCKED).
2. `CLAUDE.md` làm quy tắc cho coding agent.
3. Giao assignment vận hành: người có role `CFO` giữ `finance.period.manage`, `finance.approve` (tối thiểu hai người có quyền tài chính để tách nhiệm vụ); người giữ `goals.activate`; hàng chờ review.
4. Phê duyệt bộ dữ liệu tổng hợp cho benchmark D-08; quyết định có dùng tài liệu thật (đã xử lý) hay không.
5. Chấp nhận diễn giải ADR-008 Amendment 1: chat AI chỉ đọc vẫn hoạt động khi kill switch bật.
6. Trả lời (hoặc giữ mặc định) Q-28…Q-42 theo ưu tiên ở Decision_Log §7.
