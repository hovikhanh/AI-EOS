# ADR-011 — LLM / OCR qua provider adapter

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED (cơ chế adapter) · Amendment 1 (15/10/2026, D-50): provider demo DeepSeek qua OpenRouter · provider local cho production: NEEDS_CONFIRMATION (D-08) |
| Source | D-07 (CDA); cơ chế: `ARCHITECTURE_DECISION`; quy tắc benchmark và dữ liệu nhạy cảm: `CDA_DIRECTIVE` (yêu cầu 12/10/2026 §7) |
| Liên quan | D-07, D-08; FR-AIQ-05, FR-AIQ-06, SEC-DC-04, CMP-02, NFR-07, MET-01, MET-05, BR-06 |
| Ngày cập nhật | 15/10/2026 |

## Context
Không khóa provider (D-07); ưu tiên miễn phí/chi phí thấp; dữ liệu mật có thể chỉ xử lý tại hạ tầng nội bộ (SEC-DC-04); chuyển model dự phòng khi model chính lỗi (NFR-07).

## Decision
- Interface trong module `providers`: `LLMProvider` (chat/complete, structured output, streaming), `OCRProvider` (ảnh/PDF → text + vị trí + độ tin cậy), `DocumentConverter` (DOC/DOCX/XLSX → định dạng xử lý được). Logic nghiệp vụ chỉ phụ thuộc interface.
- Adapter đầu tiên cho LLM: API tương thích OpenAI (dùng được với runtime chạy local và provider cloud). Adapter OCR: chọn sau benchmark.
- **Cấu hình** provider (URL, model, key) qua biến môi trường/secret, không trong code hay CSDL dạng rõ.
- **Định tuyến theo phân loại dữ liệu:** mỗi lời gọi mang `data_classification`; dữ liệu nhân sự, lương, chứng từ nhạy cảm, dữ liệu gắn nhãn cá nhân (SEC-DC-02) **chỉ** được gửi tới provider được đánh dấu `local=true`. Gửi ra provider bên ngoài bị chặn mặc định cho các loại này cho đến khi có quyết định về xử lý dữ liệu (CMP-02).
- **Timeout**, **retry giới hạn** với backoff, **fallback** sang provider dự phòng cùng mức phân loại (NFR-07); hết lượt → lỗi rõ ràng, luồng thủ công vẫn chạy (BR-21).
- **Giới hạn chi phí:** ghi mỗi lời gọi (provider, model, token/trang, thời gian, chi phí ước tính) vào `ai.call_log`; trần ngân sách cấu hình; vượt trần → chặn lời gọi mới không thiết yếu và báo ADMIN (BR-22, giá trị trần: GAP-14).
- **Đầu ra không tin cậy:** structured output validate theo schema; không bao giờ diễn giải đầu ra là lệnh (BR-06, ADR-008).

**Benchmark trước khi khóa provider (D-08):**
| Thành phần | Nội dung |
| --- | --- |
| Tập dữ liệu | Tài liệu tiếng Việt thuộc loại MVP (FR-DCS-02), **được CDA phê duyệt sử dụng**; tách tập có lớp text / scan / ảnh chụp / chữ viết tay |
| Ground truth | Giá trị đúng từng trường, do người nhập và kiểm tra chéo |
| Trường | Theo Extraction Schema của từng loại tài liệu |
| Accuracy | Field accuracy = số trường đúng không cần sửa / tổng trường (MET-01); tính riêng trường trọng yếu |
| Lỗi nghiêm trọng | Sai trường trọng yếu mà độ tin cậy báo cao |
| Chi phí, latency | Chi phí/tài liệu (MET-05), p50/p95 thời gian (NFR-01) |
| Ràng buộc | Dữ liệu nhạy cảm chỉ chạy với provider local |

Không tuyên bố đạt field accuracy ≥ 90% (MET-01) trước khi có kết quả benchmark.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Gắn chặt một SDK provider | Vi phạm D-07 |
| Thư viện đa provider làm lõi | Có thể dùng **bên dưới** adapter; không để logic nghiệp vụ phụ thuộc trực tiếp |

## Consequences
- Có thể chạy hoàn toàn local (dev, dữ liệu mật) hoặc kết hợp cloud cho dữ liệu không mật.
- Model local cần RAM/GPU; ghi nhận trong yêu cầu tài nguyên triển khai (Architecture §9).

## Security Considerations
- Prompt hệ thống và policy nằm trong code; nội dung tài liệu được đặt trong vùng dữ liệu rõ ràng, có chỉ dẫn coi là dữ liệu (BR-06), nhưng **an toàn không dựa vào prompt** mà dựa vào gateway (ADR-008).
- Converter/OCR chạy trong worker với giới hạn tài nguyên và thời gian; không thực thi macro trong tài liệu Office.
- Không ghi nội dung tài liệu vào log kỹ thuật.

## Amendments

### Amendment 1 — D-50 (15/10/2026)
- **Nguồn:** quyết định `CDA` ngày 15/10/2026 (OPEN_DECISIONS.md, D-43 mục 4 và câu hỏi bổ sung cùng ngày; Decision_Log D-50).
- **Thay đổi:** DeepSeek qua OpenRouter (provider cloud) là một provider được cấu hình qua adapter, dùng cho **mọi loại dữ liệu khi demo**, kể cả `PERSONAL`/`SENSITIVE`. Đây là ngoại lệ có thẩm quyền đối với quy tắc định tuyến "dữ liệu nhạy cảm chỉ tới provider local" ở mục Decision. Sau khi triển khai production sẽ tích hợp thêm option provider local (D-08).
- **Không thay đổi:** cơ chế adapter, định tuyến theo phân loại dữ liệu (vẫn hiện thực, để bật lại cho production), call log, trần chi phí, timeout/retry, giả lập trong CI (CI không gọi provider thật), đầu ra LLM là dữ liệu không tin cậy, mọi ghi qua gateway (ADR-008).
- **`[CẦN XÁC NHẬN]`:** (1) môi trường demo dùng dữ liệu tổng hợp hay dữ liệu thật — CLAUDE.md §6 cấm dữ liệu thật trong dev/test/CI; (2) cách định tuyến `PERSONAL`/`SENSITIVE` ở production trước khi có provider local; (3) DeepSeek có là phương án trong benchmark T-606 không.
- **Rủi ro ghi nhận:** dữ liệu rời máy triển khai, tới provider ngoài Việt Nam (liên quan CMP-02, BRD §4.5); khóa API là secret (`AIEOS_LLM_API_KEY_<NAME>`), không commit.
