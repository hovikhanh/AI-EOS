# ADR-001 — Kiểu kiến trúc: modular monolith + worker

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` — khuyến nghị tại `Pre2C_Decision_Proposals.md` §2.1, được CDA chỉ định làm quyết định mặc định (yêu cầu ngày 12/10/2026) |
| Liên quan | D-03, D-06, D-09, D-13, D-14, D-26; BR-04, NFR-02 |
| Ngày cập nhật | 12/10/2026 |

## Context
AI-EOS là hệ thống nội bộ một doanh nghiệp, triển khai Local/Docker Compose (D-03). Yêu cầu có tính toàn vẹn cao: mọi ghi từ Domain 22 đi qua Tool Registry (BR-04), kill switch thực thi ở backend (D-09), giao dịch tài chính có phê duyệt và bút toán đảo (D-13, D-14). Thông lượng mục tiêu MVP ≥ 1.000 trang/giờ (NFR-02).

## Decision
- Một ứng dụng backend Python duy nhất (API process) và một hoặc nhiều **worker process** chạy cùng codebase, dùng chung **một PostgreSQL** làm nguồn dữ liệu chính.
- Code chia theo module nghiệp vụ với ranh giới rõ (xem `Architecture.md` §3): `identity`, `access`, `org`, `capture`, `goals`, `work`, `finance`, `sales` (khung), `ai`, `gateway`, `jobs`, `audit`, `notify`, `storage`, `providers`.
- Module chỉ giao tiếp qua interface công khai (service API trong process) hoặc qua job/sự kiện trong CSDL; không truy cập bảng của module khác trực tiếp, trừ module `audit` (chỉ ghi qua API audit).
- Quy tắc phụ thuộc được kiểm tra tự động trong CI (vd. công cụ kiểm tra import-contract).
- Không dùng microservices trong MVP.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Microservices | Cần saga/outbox liên service cho giao dịch tài chính; mỗi service phải tự thực thi kill switch → dễ có đường vòng; nhiều container hơn cho một doanh nghiệp |
| Monolith không chia module | Khó bảo đảm ranh giới cổng ghi, khó tách sau này |

## Consequences
- Giao dịch ACID một CSDL cho: chuyển trạng thái + audit + xếp job (outbox tự nhiên).
- Một cổng ghi duy nhất cho hành động AI (ADR-008).
- Mở rộng bằng tăng số worker; API process stateless (session lưu CSDL).
- Có thể tách service sau theo ranh giới module nếu có nhu cầu đo được.

## Security Considerations
- Một tiến trình API → một bề mặt xác thực và một policy module (ADR-007), giảm nguy cơ lệch quyền giữa service.
- Worker không mở cổng mạng ra ngoài; chỉ kết nối CSDL, storage, provider.
- Vi phạm ranh giới module (gọi repository của module khác, bỏ qua cổng ghi) là lỗi chặn merge.
