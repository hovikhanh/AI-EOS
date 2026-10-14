# Q-51 — Dự thảo phân tích chủ sở hữu test case

> **DỰ THẢO — `PROPOSED`, chưa có hiệu lực.** Tài liệu phân tích để CDA quyết định Q-51 ([Decision_Log](../00-source/Decision_Log.md) mục 3.7, mục 8). Không thay đổi quyết định, trạng thái task hay trạng thái TC nào. Mọi TC trong [TEST_Plan](TEST_Plan.md) vẫn `NOT RUN`; T-005, T-006, T-011 vẫn `IN_REVIEW`.
> Ngày: 14/10/2026 · Dữ liệu đọc từ `main` commit `ebf9f37`: cột "Phụ thuộc" và "DoD riêng" của [Implementation_Plan](Implementation_Plan.md) §4, cột "Test case" của [Implementation_Handoff](../Implementation_Handoff.md) §5, bảng TC của TEST_Plan.

## 1. Tóm tắt

- TEST_Plan có **199** TC; **65** TC được Handoff §5 gán cho từ hai task trở lên (đã đếm lại, khớp hồ sơ 3.7).
- Áp quy tắc "task chủ" (mục 2) cho 65 TC:

| Nhóm | Số TC | TC |
| --- | --- | --- |
| Có task chủ trong số task đang tham chiếu, đủ dependency | 52 | Bảng mục 3 |
| Có task chủ trong số task tham chiếu nhưng dependency của task chủ ghi chung chung, chưa kiểm chứng được | 5 | TC-E2E-01…05 (T-608: "Các task frontend") |
| Task chủ nằm **ngoài** các task đang tham chiếu | 1 | TC-SEC-05 → T-602 |
| **Không task nào trong toàn plan chạy được đầy đủ** (xung đột dependency) | 7 | TC-DR-02, TC-FIN-14, TC-MIG-02, TC-REV-05, TC-SEC-01, TC-SEC-02, TC-SEC-06 |

- Plan §4 tự gán cùng một TC vào DoD riêng của hai task ở 10 TC: TC-CAP-05, TC-CAP-06, TC-E2E-01…05, TC-FIN-14, TC-KS-08, TC-KS-09.
- Không tạo vòng phụ thuộc: kiểm tra tự động xác nhận mọi task mà kịch bản TC cần đều là tổ tiên của task chủ (hoặc chính nó), trừ 7 TC xung đột.

## 2. Quy tắc đề xuất (phương án A)

| # | Quy tắc |
| --- | --- |
| R1 | Mỗi TC có đúng **một** task chủ: task sớm nhất trong chuỗi dependency mà kịch bản **đầy đủ** của TC chạy được. Ưu tiên task có TC trong DoD riêng (Plan §4) nếu task đó đủ dependency. |
| R2 | TC chỉ được ghi đạt khi test hiện thực **toàn bộ** kịch bản và kết quả mong đợi ở TEST_Plan chạy xanh trong CI của task chủ. Bằng chứng: lệnh, run CI, commit ghi ở Implementation_Plan §10 dòng của task chủ. |
| R3 | Task khác đang tham chiếu TC nghiệm thu bằng DoD riêng và **bằng chứng thành phần** (cột "Bằng chứng thành phần"). Bằng chứng thành phần ghi ở Plan §10 của task đó dưới nhãn "bằng chứng thành phần của TC-…", **không** là PASS của TC và không đổi trạng thái TC. |
| R4 | Task sau task chủ chạy lại test như hồi quy; CI đỏ thì task sau không đạt DoD chung 1. |
| R5 | TC cần tách: không tạo ID mới; ghi "TC-XXX-NN (phần …)" khi nói về phần. TC chỉ đạt khi mọi phần đạt ở task chủ hoặc ở mốc CDA chỉ định. |
| R6 | Không task nào chạy đủ một TC (mục 4) → CDA chọn: thêm dependency, hoặc tách TC và chỉ định mốc tổng hợp. Chưa quyết thì TC không có chủ và không task nào được dùng TC đó làm điều kiện `DONE`. |
| R7 | TEST_Plan không đổi nội dung TC. Yêu cầu bảo mật giữ nguyên. |

Định nghĩa "chạy được đầy đủ" dựa trên kịch bản và kết quả mong đợi ở TEST_Plan; điều kiện thực hiện của từng TC ở cột "Điều kiện thực hiện".

## 3. Bảng ánh xạ 65 TC

Tiêu chí PASS của mỗi TC là cột "Kết quả mong đợi" ở TEST_Plan (không nhắc lại); bằng chứng theo R2.

| TC | Yêu cầu | Task tham chiếu (Handoff §5) | DoD Plan §4 | Task chủ đề xuất | Lý do | Điều kiện thực hiện (task cần có) | Bằng chứng thành phần (không phải PASS) | Tách | Xung đột / câu hỏi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-ACC-01 | SRS-ACC-01 | T-108, T-601 | — | **T-108** | `authorize()` tính quyền hiệu lực (phạm vi T-108) | T-107, T-108 | T-601: hồi quy trong ma trận | — | — |
| TC-ACC-02 | SRS-ACC-02, SRS-ACC-09 | T-108, T-111, T-601 | T-108 | **T-108** | Plan §4 DoD T-108 ghi TC-ACC-02 | T-108 | T-111: ẩn mục ở giao diện (thuộc TC-E2E-01); T-601: hồi quy mọi endpoint | — | "mọi đối tượng ngoài phạm vi" chỉ đủ khi có endpoint nghiệp vụ — T-601 chạy lại; xem §6 |
| TC-ACC-04 | SRS-ACC-05 | T-107, T-109 | T-109 | **T-109** | Plan §4 DoD T-109; cần API gán role | T-107, T-109 | T-107: phần CSDL: SQL role ứng dụng bị trigger INV-10 từ chối | Có: phần CSDL / phần API | — |
| TC-ACC-05 | SRS-ACC-06 | T-107, T-109 | T-109 | **T-109** | Plan §4 DoD T-109 | T-107, T-109 | T-107: phần CSDL: CHECK INV-09 | Có: phần CSDL / phần API | — |
| TC-ACC-06 | SRS-ACC-07 | T-107, T-109 | T-109 | **T-109** | Plan §4 DoD T-109; đồng thời qua API | T-107, T-109 | T-107: trigger INV-11 | — | — |
| TC-ACC-07 | SRS-ACC-08 | T-107, T-109 | T-109 | **T-109** | Plan §4 DoD T-109 | T-107, T-109 | T-107: kiểm tra điều kiện assignment ở CSDL | — | — |
| TC-ACC-08 | SRS-IAM-11 | T-104, T-109 | T-109 | **T-109** | Plan §4 DoD T-109; đổi role qua API | T-104, T-109 | T-104: hàm thu hồi session | — | — |
| TC-ACC-09 | SRS-ACC-11 | T-108, T-201 | — | **T-201** | Cần API danh bạ (T-201) | T-108, T-201 | — | — | — |
| TC-AIC-02 | SRS-AIC-02 | T-301, T-302 | T-302 | **T-302** | Plan §4 DoD T-302 | T-301, T-302 | T-301: phần CSDL: CHECK trần (DoD T-301) | Có: phần code / phần CSDL | — |
| TC-AIC-03 | SRS-AIC-03 | T-301, T-302 | T-302 | **T-302** | Plan §4 DoD T-302 | T-301, T-302 | T-301: seed Tool Registry | — | — |
| TC-CAP-02 | SRS-CAP-12, SRS-CAP-13 | T-202, T-206 | T-206 | **T-206** | Plan §4 DoD T-206 | T-202, T-206 | T-202: bảng `capture.*` | — | — |
| TC-CAP-04 | SRS-CAP-16 | T-206, T-208 | T-206 | **T-206** | Plan §4 DoD T-206; tự ghi tắt mặc định | T-206 | T-208: hồi quy khi đổi cấu hình | — | — |
| TC-CAP-05 | SRS-CAP-16 | T-206, T-208 | T-206, T-208 | **T-208** | Kịch bản là bật tự ghi qua cấu hình (BR-05) — phạm vi T-208 | T-206, T-208 | T-206: định tuyến theo cấu hình | — | Plan §4 DoD gán cho cả T-206 (TC-CAP-01…08) và T-208 |
| TC-CAP-06 | SRS-CAP-17 | T-206, T-208 | T-206, T-208 | **T-206** | Mặc định "mọi trường tiền trọng yếu" áp dụng ở định tuyến (T-206) | T-206 | T-208: hồi quy khi sửa schema | — | Plan §4 DoD gán cho cả T-206 và T-208 |
| TC-CAP-08 | SRS-CAP-18, SRS-CAP-22 | T-206, T-302 | T-206 | **T-206** | Plan §4 DoD T-206; commit qua gateway | T-206, T-302 | T-302: đường commit trong gateway | — | — |
| TC-CAP-12 | SRS-CAP-19, SRS-BRF-04 | T-211, T-510 | T-211 | **T-211** | Plan §4 DoD T-211 (lineage API) | T-211 | T-510: popover nguồn trên Trang chủ | — | T-510 dùng lineage (SRS-BRF-04) nhưng không phụ thuộc T-211 |
| TC-CAP-15 | SRS-CAP-15 | T-206, T-208 | — | **T-206** | Kiểm tra/chuẩn hóa thuộc pipeline T-206 | T-206 | — | — | — |
| TC-DR-01 | SRS-NFR-03 | T-005, T-605 | — | **T-605** | Diễn tập khôi phục — DoD T-605 | T-005, T-013, T-605 | — | — | — |
| TC-DR-02 | SRS-NFR-03 | T-005, T-605 | — | **Chưa có** (§4) | Cần hash file lưu ở CSDL (T-203) và stack chạy được (T-013) | T-203, T-013, T-605 | — | — | T-605 không phụ thuộc T-203 → không task nào chạy đủ |
| TC-E2E-01 | FL-01, FL-02, FL-03 | T-111, T-608 | T-111, T-608 | **T-608** | E2E chạy trên môi trường Compose (TEST_Plan §1) → cần T-013 | T-111, T-013 | T-111: test component/Vitest của màn hình | — | Plan §4 DoD gán cho cả T-111 và T-608; dependency "Các task frontend" chưa liệt kê task |
| TC-E2E-02 | FL-04, FL-05, FL-06 | T-212, T-608 | T-212, T-608 | **T-608** | Như TC-E2E-01 | T-212, T-013 | T-212: test component | — | Plan §4 DoD gán cho cả T-212 và T-608; dependency "Các task frontend" chưa liệt kê task |
| TC-E2E-03 | FL-11, FL-12 | T-409, T-608 | T-409, T-608 | **T-608** | Như TC-E2E-01 | T-409, T-013 | T-409: test component | — | Plan §4 DoD gán cho cả T-409 và T-608; dependency "Các task frontend" chưa liệt kê task |
| TC-E2E-04 | FL-15 | T-504, T-608 | T-504, T-608 | **T-608** | Như TC-E2E-01 | T-504, T-013 | T-504: test component | — | Plan §4 DoD gán cho cả T-504 và T-608; dependency "Các task frontend" chưa liệt kê task |
| TC-E2E-05 | FL-07, FL-08 | T-509, T-608 | T-509, T-608 | **T-608** | Như TC-E2E-01 | T-509, T-013 | T-509: test component | — | Plan §4 DoD gán cho cả T-509 và T-608; dependency "Các task frontend" chưa liệt kê task |
| TC-FILE-03 | SRS-CAP-03 | T-011, T-203 | T-203 | **T-203** | Plan §4 DoD T-203; cần chuẩn hóa tên | T-011, T-203 | T-011: phần lưu bằng UUID (run `38544080219`) | Có: phần lưu trữ / phần chuẩn hóa tên | — |
| TC-FIN-03 | SRS-FIN-08 | T-401, T-404 | T-401 | **T-401** | Plan §4 DoD T-401 "TC-FIN-01…04 ở mức CSDL" | T-401 | T-404: hồi quy qua API duyệt | — | — |
| TC-FIN-04 | SRS-FIN-17 | T-401, T-404 | T-401 | **T-401** | Như TC-FIN-03 | T-401 | T-404: hồi quy qua API duyệt | — | — |
| TC-FIN-12 | SRS-FIN-12 | T-110, T-402, T-409 | T-402 | **T-402** | Plan §4 DoD T-402 | T-402 | T-409: giao diện kỳ | — | — |
| TC-FIN-13 | SRS-FIN-12 | T-110, T-402, T-409 | T-402 | **T-402** | Plan §4 DoD T-402 | T-402 | T-409: giao diện kỳ | — | — |
| TC-FIN-14 | SRS-FIN-12 | T-110, T-402, T-409 | T-110, T-402 | **Chưa có** (§4) | Kết quả mong đợi là cảnh báo trên trang tình trạng (T-110) về assignment và kỳ mở | T-109, T-110, T-401 | T-402: chặn thao tác khi không có kỳ mở | — | Plan §4 DoD gán cho cả T-110 và T-402; T-110 không phụ thuộc T-401 → không task nào chạy đủ |
| TC-FIN-15 | SRS-FIN-12 | T-110, T-402, T-409 | T-402 | **T-402** | Plan §4 DoD T-402 | T-402 | T-409: giao diện kỳ | — | — |
| TC-FIN-19 | SRS-FIN-17 | T-401, T-404 | T-404 | **T-404** | Plan §4 DoD T-404 | T-401, T-404 | T-401: trigger INV-07 | — | — |
| TC-FIN-20 | SRS-FIN-17 | T-401, T-404 | T-404 | **T-404** | Plan §4 DoD T-404 | T-401, T-404 | T-401: trạng thái `ON_HOLD` ở CSDL | — | — |
| TC-GEN-03 | SRS-GEN-03 | T-007, T-603 | T-007 | **T-007** | Plan §4 DoD T-007 (TC-GEN-01…05) | T-007 | T-603: đồng thời trên endpoint nghiệp vụ (AC-ARCH) | — | Ở T-007 chỉ có route thử; xem §6 |
| TC-GEN-04 | SRS-GEN-03 | T-007, T-603 | T-007 | **T-007** | Plan §4 DoD T-007 | T-007 | T-603: hồi quy | — | — |
| TC-GEN-05 | SRS-GEN-04, SRS-GEN-05 | T-006, T-007, T-603 | T-007 | **T-007** | Plan §4 DoD T-007 | T-007 | T-006: correlation ID, không stack trace; T-603: hồi quy | — | — |
| TC-GEN-06 | SRS-GEN-01 | T-007, T-102 | — | **T-102** | Cần session (T-102) | T-007, T-102 | T-007: khung lỗi `problem+json` | — | "mọi endpoint" chỉ đủ khi có endpoint nghiệp vụ — T-601 chạy lại; xem §6 |
| TC-GOAL-03 | SRS-GOAL-06 | T-501, T-503 | T-501 | **T-501** | Plan §4 DoD T-501 | T-501 | T-503: giá trị đo từ tài liệu (hồi quy) | — | — |
| TC-GOAL-08 | SRS-GOAL-03 | T-502, T-503 | T-502 | **T-502** | Plan §4 DoD T-502 | T-502 | — | — | — |
| TC-GOAL-09 | SRS-GOAL-03, SRS-GOAL-10 | T-502, T-503 | T-503 | **T-503** | Plan §4 DoD T-503 | T-501, T-503 | — | — | — |
| TC-IAM-02 | SRS-IAM-06 | T-101, T-102 | T-102 | **T-102** | Plan §4 DoD T-102 | T-101, T-102 | T-101: bảng session, token chỉ lưu hash | — | — |
| TC-IAM-05 | SRS-IAM-06 | T-101, T-102 | T-102 | **T-102** | Plan §4 DoD T-102 | T-101, T-102 | T-101: cột hạn session | — | — |
| TC-IAM-08 | SRS-IAM-08, SRS-IAM-11 | T-104, T-109 | T-104 | **T-104** | Plan §4 DoD T-104 | T-104 | T-109: hồi quy khi đổi role | — | — |
| TC-JOB-06 | SRS-AIC-06 | T-009, T-303 | T-009 | **T-009** | Plan §4 DoD T-009 (quét registry) | T-009 | T-303: hồi quy | — | — |
| TC-KS-03 | SRS-AIC-05 | T-302, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-302, T-303 | T-302: kiểm tra kill switch ở gateway | — | — |
| TC-KS-04 | SRS-AIC-05 | T-302, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-302, T-303 | T-302: kiểm tra trước cổng ghi | — | — |
| TC-KS-05 | SRS-AIC-05 | T-302, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-302, T-303 | T-302: retry qua gateway | — | — |
| TC-KS-06 | SRS-AIC-05 | T-302, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-302, T-303 | T-302: bản nháp L2 | — | — |
| TC-KS-07 | SRS-AIC-06 | T-009, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-009, T-303 | T-009: scheduler, `may_write` | — | — |
| TC-KS-08 | SRS-AIC-06, SRS-BRF-11 | T-009, T-303, T-511 | T-303, T-511 | **T-511** | Cần lịch Briefing (T-510, T-511) | T-303, T-511 | T-303: chặn `AI_CONTENT` với job thử; T-009: phân loại job | — | Plan §4 DoD gán cho cả T-303 và T-511 |
| TC-KS-09 | SRS-AIC-06 | T-009, T-303, T-511 | T-303, T-511 | **T-511** | Job nhắc review/đánh dấu quá hạn thuộc T-304; T-303 không phụ thuộc T-304 | T-303, T-304 | T-303: `ORCHESTRATION` với job thử; T-009: registry | — | Plan §4 DoD gán cho cả T-303 và T-511; chủ hợp lý hơn có thể là task phụ thuộc T-303 và T-304 |
| TC-KS-10 | SRS-AIC-05 | T-302, T-303 | T-303 | **T-303** | Plan §4 DoD T-303 | T-302, T-303 | T-302: bản nháp không tự chạy | — | — |
| TC-MIG-01 | SRS-NFR-03 | T-005, T-605 | — | **T-005** | Harness rỗng → head + so khớp model ↔ schema (T-005); chạy lại ở mọi migration (Plan §5) | T-005 | T-605: khôi phục rồi kiểm tra migration head | — | Đạt ở T-005 với metadata rỗng; xem §6 |
| TC-MIG-02 | SRS-NFR-03 | T-005, T-605 | — | **Chưa có** (§4) | INV-01…16 tạo ở T-008, T-101, T-107, T-301, T-302, T-401, T-403… | T-008, T-101, T-107, T-301, T-302, T-401, T-403, T-009 | T-008: INV-14; T-101: INV-16; T-107: INV-09…11; T-301: INV-12, 13, 15; T-401: INV-01…07; T-403: INV-08 (giao dịch) | Có: mỗi task tạo bất biến kiểm phần của mình | Task duy nhất có đủ mọi task tạo bất biến là T-511 (không liên quan) → cần mốc tổng hợp |
| TC-PRV-04 | SRS-PRV-02 | T-112, T-204 | T-204 | **T-204** | Plan §4 DoD T-204 (định tuyến theo nhãn) | T-204 | T-112: phát hiện và gắn nhãn `sensitivity` | — | — |
| TC-PRV-07 | SRS-PRV-01 | T-204, T-205 | T-204 | **T-204** | Plan §4 DoD T-204 (adapter giả lập) | T-204 | T-205: hồi quy với provider thật | — | — |
| TC-REV-04 | SRS-REV-07, SRS-REV-09 | T-202, T-207 | T-207 | **T-207** | Plan §4 DoD T-207 | T-202, T-207 | T-202: bảng review | — | — |
| TC-REV-05 | SRS-REV-08 | T-207, T-408 | T-207 | **Chưa có** (§4) | Duyệt tài liệu tạo giao dịch `DRAFT` → cần hàng chờ review (T-207) và tool tạo bản nháp tài chính (T-408) | T-207, T-408 | T-207: duyệt tài liệu; T-408: chỉ tạo `DRAFT` (TC-FIN-30) | — | Plan §4 DoD gán cho T-207; T-207 không phụ thuộc T-408 → không task nào chạy đủ |
| TC-SEC-01 | SRS-NFR-11 | T-601, T-602 | — | **Chưa có** (§4) | Kiểm tra hiển thị dạng văn bản và CSP do proxy đặt | T-111, T-203, T-306, T-013 | T-012: lint chặn `dangerouslySetInnerHTML`, build không có script inline (run `38536047844`) | Có: phần render (frontend) / phần CSP (proxy) | T-602 không phụ thuộc T-013 (proxy) → không task nào chạy đủ |
| TC-SEC-02 | SRS-NFR-11 | T-601, T-602 | — | **Chưa có** (§4) | Header bảo mật do reverse proxy đặt (ADR-003, Architecture §2.2) | T-013, T-602 | — | — | T-602 không phụ thuộc T-013 → không task nào chạy đủ |
| TC-SEC-03 | SRS-NFR-11 | T-601, T-602 | — | **T-601** | IDOR trên mọi resource = ma trận endpoint × role × phạm vi | T-601 | T-602: chạy trong bộ test bảo mật | — | Phụ thuộc T-601 ghi "các API" (không liệt kê); dependency "các API" chưa liệt kê task |
| TC-SEC-04 | SRS-NFR-11 | T-601, T-602 | — | **T-602** | Bộ test bảo mật (TEST_Plan §6) | T-602 | T-002: `pip-audit`, `npm audit` chạy ở mọi CI run | — | Bằng chứng đã có ở mọi CI run từ T-002; xem §6 |
| TC-SEC-05 | SRS-GEN-05 | T-006, T-007 | — | **T-602** | Cần luồng đăng nhập (T-102), upload (T-203), gọi provider (T-204); T-602 là task duy nhất có đủ | T-102, T-203, T-204 | T-006: bộ lọc log (run `38544809935`); T-007: log lỗi HTTP | — | Task chủ không nằm trong các task đang tham chiếu (T-006, T-007) |
| TC-SEC-06 | SRS-PRV-02 | T-112, T-204 | — | **Chưa có** (§4) | Không gọi ra ngoài (T-204) + nhãn dữ liệu (T-112) + bước AI bỏ qua, chuyển thủ công (T-206) | T-112, T-204, T-206 | T-204: từ chối định tuyến ra cloud; T-112: gắn nhãn | Có: phần định tuyến / phần luồng tài liệu | Không task nào phụ thuộc cả T-112 và T-206 |
| TC-WRK-05 | SRS-WRK-10 | T-505, T-509 | T-505 | **T-505** | Plan §4 DoD T-505 (API theo phạm vi) | T-505 | T-509: giao diện danh sách | — | — |

## 4. Xung đột dependency (7 TC — không task nào chạy đủ)

| TC | Cần | Thiếu | Lựa chọn cho CDA |
| --- | --- | --- | --- |
| TC-DR-02 | Khôi phục (T-605) + hash file lưu ở CSDL (T-203) + stack (T-013) | T-605 không phụ thuộc T-203 | (a) thêm T-203 vào dependency T-605; (b) TC-DR-02 chủ là task khác do CDA chỉ định |
| TC-FIN-14 | Trang tình trạng (T-110) + dữ liệu assignment (T-109) + kỳ (T-401) | T-110 không phụ thuộc T-401; Plan §4 gán cả T-110 và T-402 | (a) thêm T-401 (hoặc T-402) vào dependency T-110, chủ T-110; (b) tách: phần chặn thao tác ở T-402, phần cảnh báo ở T-110 |
| TC-MIG-02 | INV-01…16 từ T-008, T-101, T-107, T-301, T-302, T-401, T-403 | Task duy nhất có đủ là T-511 (không liên quan) | Tách theo bất biến: mỗi task tạo bất biến kiểm phần của mình (R5); TC đạt tổng khi bất biến cuối có — CDA chỉ định mốc (vd. thêm dependency cho một task kiểm thử tổng hợp ở P6) |
| TC-REV-05 | Duyệt tài liệu (T-207) + tạo giao dịch `DRAFT` (T-408) | Không task nào phụ thuộc cả hai | (a) thêm T-408 vào dependency T-207 (T-207 chủ); (b) chủ là T-408 nếu thêm T-207 vào dependency T-408 |
| TC-SEC-01 | Render dạng văn bản (frontend) + CSP ở proxy (T-013) | T-602 không phụ thuộc T-013 | (a) thêm T-013 vào dependency T-602; (b) tách: phần render ở T-602, phần CSP ở T-013 |
| TC-SEC-02 | Header bảo mật do proxy đặt | T-602 không phụ thuộc T-013 | (a) thêm T-013 vào dependency T-602; (b) chủ T-013 |
| TC-SEC-06 | Nhãn dữ liệu (T-112) + không gọi ra ngoài (T-204) + bước AI bỏ qua, chuyển thủ công (T-206) | Không task nào phụ thuộc cả T-112 và T-206 | (a) thêm T-112 vào dependency T-206 (chủ T-206); (b) tách: phần định tuyến ở T-204, phần luồng tài liệu ở T-206 |

Khoảng trống liên quan (không gây xung đột TC nhưng ảnh hưởng truy vết): T-510 dùng lineage (SRS-BRF-04) nhưng không phụ thuộc T-211; dependency của T-601 ("các API") và T-608 ("Các task frontend") chưa liệt kê task cụ thể.

## 5. Gán trùng trong DoD Plan §4 (10 TC)

| TC | DoD Plan §4 gán cho | Đề xuất chủ | Lý do |
| --- | --- | --- | --- |
| TC-CAP-05 | T-206, T-208 | T-208 | Kịch bản bật tự ghi qua cấu hình (BR-05) |
| TC-CAP-06 | T-206, T-208 | T-206 | Mặc định "mọi trường tiền trọng yếu" áp dụng ở định tuyến; T-208 hồi quy |
| TC-E2E-01…05 | Task frontend tương ứng, T-608 | T-608 | E2E chạy trên Compose (TEST_Plan §1) → cần T-013; task frontend không phụ thuộc T-013 |
| TC-FIN-14 | T-110, T-402 | Xung đột (mục 4) | — |
| TC-KS-08 | T-303, T-511 | T-511 | Cần lịch Briefing |
| TC-KS-09 | T-303, T-511 | T-511 | Job nhắc review/đánh dấu quá hạn thuộc T-304; T-303 không phụ thuộc T-304 |

## 6. Vòng phụ thuộc và nguy cơ "đạt một phần"

**Vòng phụ thuộc.** Theo R1, task chủ có mọi task cần thiết làm tổ tiên, nên điều kiện `DONE` của một task không bao giờ cần task sau nó. Kiểm tra tự động trên 58 TC có chủ: không trường hợp nào task chủ thiếu dependency (5 TC-E2E chỉ kiểm chứng được khi T-608 liệt kê cụ thể "Các task frontend"). Quy tắc cũ (Handoff §5 theo nghĩa chặt) tạo vòng ít nhất ở T-005 → T-605 → T-005 (TC-DR-01/02).

**Nguy cơ ghi đạt khi mới kiểm tra một phần** và cách chặn:

| TC | Nguy cơ | Cách chặn đề xuất |
| --- | --- | --- |
| TC-MIG-01 | Ở T-005 chưa có model nào → so khớp model ↔ schema đạt hiển nhiên | Ghi đạt ở T-005 kèm phạm vi "schema tại revision `0001`"; bắt buộc chạy trong mọi CI sau (R4) — mọi migration mới làm đỏ nếu lệch |
| TC-MIG-02 | Đạt từng bất biến bị hiểu là đạt cả 16 | R5: chỉ ghi "TC-MIG-02 (INV-xx)" ở task tạo bất biến; TC đạt khi đủ 16 tại mốc CDA chỉ định |
| TC-GEN-03 | Ở T-007 chỉ có route thử; "đồng thời" trên endpoint nghiệp vụ ở T-603 | Chủ T-007 với route thử (kịch bản không gắn endpoint cụ thể); T-603 hồi quy trên endpoint thật (AC-ARCH) |
| TC-ACC-02, TC-GEN-06 | "Mọi endpoint/đối tượng" khi mới có ít endpoint | Đạt ở task chủ với endpoint hiện có; T-601 (ma trận) chạy lại trên mọi endpoint |
| TC-SEC-04 | Quét phụ thuộc đã chạy ở mọi CI từ T-002 nhưng chủ là T-602 | Chủ T-602 ghi đạt dựa trên CI tại thời điểm đó; không ghi đạt sớm |
| TC-FILE-03 | Phần lưu bằng UUID (T-011) bị hiểu là đạt cả TC | R3: chỉ là bằng chứng thành phần; TC đạt ở T-203 |

## 7. Tác động lên task cụ thể

| Task | TC thuộc task (là chủ) | TC chỉ có bằng chứng thành phần | Trạng thái nếu duyệt |
| --- | --- | --- | --- |
| T-005 | TC-MIG-01 | TC-MIG-02 (không có bất biến nào ở T-005); TC-DR-01/02 → T-605 | Đủ điều kiện `DONE` (run `38543440774`) |
| T-006 | — | TC-GEN-05 → T-007; TC-SEC-05 → T-602 (bộ lọc log, run `38544809935`) | Đủ điều kiện `DONE` (run `38544809935`) |
| T-011 | — | TC-FILE-03 → T-203 (phần lưu UUID, run `38544080219`) | Đủ điều kiện `DONE` (run `38544080219`) |
| T-007 | TC-GEN-03, TC-GEN-04, TC-GEN-05 (cùng TC-GEN-01, 02 chỉ thuộc T-007) | TC-GEN-06 → T-102; TC-SEC-05 → T-602 | — |
| T-009 | TC-JOB-06 (cùng TC-JOB-01…05) | TC-KS-07 → T-303; TC-KS-08, 09 → T-511 | — |
| T-101 | — | TC-IAM-02, 05 → T-102 | DoD riêng "token chỉ lưu hash" |
| T-107 | — | TC-ACC-04…07 → T-109 (phần CSDL) | DoD riêng (seed, trigger INV-09/10/11) |
| T-302 | TC-AIC-02, TC-AIC-03 (cùng TC-AIC-01, 04…06) | TC-KS-03…06, 10 → T-303; TC-CAP-08 → T-206 | — |
| T-401 | TC-FIN-03, TC-FIN-04 (cùng TC-FIN-01, 02) | TC-FIN-19, 20 → T-404 | — |

## 8. Dự thảo nội dung quyết định Q-51

> **(Dự thảo — chỉ có hiệu lực khi CDA duyệt; ID quyết định `D-xx` gán khi duyệt.)**
> Q-51 trả lời theo phương án A. Mỗi TC có đúng một task chủ theo R1; TC chỉ ghi đạt khi task chủ chạy toàn bộ kịch bản xanh trong CI (R2). Task khác tham chiếu TC nghiệm thu bằng DoD riêng và bằng chứng thành phần (R3), chạy lại TC như hồi quy (R4). TC tách theo phần không đổi ID (R5). Bảng chủ sở hữu: tài liệu này mục 3, với các điều chỉnh CDA chọn ở mục 4 và 5. "Test tương ứng" ở Implementation_Plan §2 mục 2 = TC có task chủ là task đó. T-005, T-006, T-011 chuyển `DONE` dựa trên bằng chứng CI đã có. Yêu cầu bảo mật và nội dung TC không đổi.

## 9. Câu hỏi để CDA xác nhận

1. **Quy tắc:** duyệt R1–R7 (mục 2), gồm định nghĩa "test tương ứng" = TC có task chủ là task đó, và chuyển T-005, T-006, T-011 sang `DONE` theo mục 7?
2. **Gán trùng trong Plan §4 (mục 5):** chấp nhận chủ đề xuất (TC-CAP-05 → T-208, TC-CAP-06 → T-206, TC-E2E-01…05 → T-608, TC-KS-08/09 → T-511) và sửa DoD riêng của task còn lại thành "bằng chứng thành phần"? Đồng thời liệt kê cụ thể dependency "Các task frontend" của T-608 và "các API" của T-601?
3. **Xung đột dependency (mục 4):** với từng TC trong 7 TC, chọn (a) thêm dependency hay (b) tách TC và chỉ định mốc tổng hợp?
4. **TC dạng hồi quy/tổng hợp:** chấp nhận TC-MIG-01 ghi đạt ở T-005 với phạm vi revision hiện có và bắt buộc giữ xanh ở mọi CI sau; TC-MIG-02 chỉ đạt tổng khi đủ INV-01…16 tại mốc CDA chỉ định?

## 10. Tài liệu cần cập nhật sau khi CDA duyệt (chưa thực hiện)

| Tài liệu | Cập nhật |
| --- | --- |
| Decision_Log | Quyết định mới cho Q-51 (nội dung mục 8 + lựa chọn câu 2–4); dòng Q-51 → "Đã trả lời"; mục 3.7 ghi kết quả |
| Implementation_Plan | §2 DoD chung 2: định nghĩa "test tương ứng"; §4: dependency mới theo câu 3, DoD riêng theo câu 2, liệt kê dependency của T-601, T-608; §10: T-005, T-006, T-011 → `DONE` kèm run CI |
| Implementation_Handoff | §5: thay câu "Tiêu chí nghiệm thu…" bằng quy tắc R1–R3; thêm cột "Task chủ" (TC trong cột "Test case" mà task không là chủ ghi kèm "(thành phần)") |
| TEST_Plan | Không đổi nội dung TC; thêm bảng "Task chủ" (TC → task chủ) hoặc tham chiếu tài liệu này; TC tách theo phần ghi bằng chú thích, không thêm ID |
| Requirements_Traceability | Cột Task/Test giữ nguyên; khi chuyển `VERIFIED` chỉ dùng TC đã đạt ở task chủ |
| `scripts/check_docs.py` (tùy chọn) | Kiểm tra mỗi TC có đúng một task chủ và task chủ đủ dependency |

## 11. Cách tái lập phân tích

Đọc ba nguồn ở đầu tài liệu; mở rộng khoảng ID kiểu `TC-ACC-04…07`, `T-102…T-109` như `check_docs.py`; một TC "dùng chung" khi xuất hiện ở cột "Test case" của ≥ 2 task; "đủ dependency" = mọi task ở cột "Điều kiện thực hiện" là tổ tiên (theo cột "Phụ thuộc" Plan §4) của task chủ hoặc chính nó. Cột "Lý do", "Điều kiện thực hiện", "Bằng chứng thành phần" là nhận định của người phân tích dựa trên kịch bản và kết quả mong đợi ở TEST_Plan.
