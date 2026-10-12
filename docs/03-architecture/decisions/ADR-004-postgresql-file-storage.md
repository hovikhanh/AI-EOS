# ADR-004 — PostgreSQL và lưu trữ file qua storage adapter

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` — `Pre2C_Decision_Proposals.md` §2.4, chỉ định của CDA (12/10/2026) |
| Liên quan | D-03, D-13, D-14; FR-DC-07, FR-DC-08, SEC-DC-05, BR-16, NFR-03, NFR-04 |
| Ngày cập nhật | 12/10/2026 |

## Context
Cần ACID, khóa dòng, ràng buộc duy nhất có điều kiện (bút toán đảo, idempotency), JSON cho trường trích xuất, tìm kiếm tài liệu. File gốc (PDF, DOCX, ảnh, Excel) phải lưu bền và truy ngược được (FR-DC-23). NFR-03: RPO ≤ 15 phút, RTO ≤ 4 giờ.

## Decision
- **PostgreSQL** (bản ổn định được hỗ trợ) là nguồn dữ liệu chính duy nhất; schema riêng theo module (Database_Design §2).
- Tiền tệ lưu kiểu `NUMERIC`, không dùng số thực dấu phẩy động.
- **Storage adapter** (`put`, `get`, `delete_unreferenced`, `exists`) — triển khai mặc định là **volume cục bộ** trên máy triển khai; triển khai S3-compatible là phần mở rộng, không cần đổi logic nghiệp vụ.
- File lưu theo khóa ngẫu nhiên (UUID), không dùng tên file của người dùng làm đường dẫn; metadata và hash SHA-256 lưu trong CSDL.
- **Backup/restore** (chi tiết Architecture §9.3): base backup + WAL archiving liên tục cho PostgreSQL để đạt RPO ≤ 15 phút; backup volume file định kỳ; bản sao lưu đặt **ngoài máy triển khai**; diễn tập khôi phục định kỳ.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| MySQL/MariaDB | JSON và ràng buộc kém linh hoạt hơn cho nhu cầu này |
| Object storage tự host ngay từ MVP | Thêm container; adapter đã cho phép chuyển sau. Kiểm tra giấy phép từng sản phẩm trước khi chọn |
| Lưu file trong CSDL (bytea) | Làm phình CSDL và backup |

## Consequences
- **Không cam kết lưu chứng từ ≥ 10 năm (BR-16)** chỉ với volume cục bộ. Cam kết này phụ thuộc chính sách vận hành backup ngoài máy và lưu trữ dài hạn, chưa có (GAP-15). Hóa đơn/chứng từ kế toán thuộc Phase 2 (D-17), nên MVP chưa phát sinh nghĩa vụ này cho hóa đơn.
- Cần dung lượng đĩa theo khối lượng tài liệu; theo dõi trong monitoring (ADR-012).

## Security Considerations
- Volume file không được phục vụ trực tiếp bởi web server; chỉ tải qua API có kiểm tra quyền (API-DOC-04), header `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`.
- Ba role CSDL: chủ sở hữu (chạy migration), ứng dụng (DML có giới hạn, không UPDATE/DELETE bảng audit), backup (chỉ đọc). Mật khẩu qua secret, không trong code.
- Kết nối CSDL chỉ trong mạng nội bộ Docker; không publish cổng PostgreSQL ra ngoài máy.
- Bản sao lưu được mã hóa khi đặt ngoài máy; khóa mã hóa quản lý tách khỏi bản sao lưu.
