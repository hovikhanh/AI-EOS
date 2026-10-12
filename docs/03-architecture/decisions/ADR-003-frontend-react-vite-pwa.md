# ADR-003 — Frontend: React + Vite + TypeScript + PWA

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` trong định hướng `[CDA nêu]` "frontend React" (D-06); so sánh tại `Pre2C_Decision_Proposals.md` §2.3 |
| Liên quan | D-06, D-27, D-33; UX §8–§9, UX-31…UX-37, NFR-05, NFR-06 |
| Ngày cập nhật | 12/10/2026 |

## Context
Ứng dụng nội bộ sau đăng nhập, không cần SEO/SSR. UX đề xuất web responsive + PWA (UX §9.1), shadcn/ui trên Radix (UX §8.3), hai mật độ, tiếng Việt mặc định, WCAG 2.1 AA (UX §9.2).

## Decision
- **React + Vite + TypeScript (strict)**, xuất bản build tĩnh, phục vụ bởi reverse proxy (Architecture §9).
- **Tailwind CSS + shadcn/ui (Radix)**; design token theo UX §8.1–8.2.
- React Router; TanStack Query cho dữ liệu server; i18n vi/en (NFR-05).
- **PWA**: manifest + service worker để cài lên màn hình chính, chụp ảnh qua input file/camera của trình duyệt (C4), nhận thông báo in-app.
- Không dùng Next.js server trong MVP.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Next.js | Thêm server Node thường trực và tầng server cần bảo vệ; lợi thế SSR/SEO không cần cho ứng dụng nội bộ |
| Ứng dụng native | Ngoài phạm vi MVP (D-27, UX §9.1) |

## Consequences
- Frontend không giữ bí mật, không chứa logic phân quyền có hiệu lực; mọi quyết định quyền ở backend (ADR-007).
- **Giới hạn nền tảng (không được tuyên bố là hỗ trợ):** push notification, camera chạy nền và sinh trắc học trên PWA phụ thuộc trình duyệt/hệ điều hành, đặc biệt iOS có hạn chế. MVP chỉ cam kết: thông báo in-app (K6), chụp ảnh khi ứng dụng đang mở. "Chụp chứng từ chạy nền" (UX-18), xác thực sinh trắc học (UX-19) và ngoại tuyến (UX-20) không thuộc cam kết MVP (D-27).
- Màn ngoài 4 việc cốt lõi trên mobile: chờ D-33; mặc định an toàn là chỉ đọc.

## Security Considerations
- Session bằng cookie HttpOnly (ADR-006): JavaScript không đọc được token; không lưu token trong `localStorage`/`sessionStorage`.
- Gửi CSRF token trong header cho mọi request thay đổi trạng thái.
- Content-Security-Policy chặt (không inline script), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `frame-ancestors 'none'` do reverse proxy đặt.
- Service worker không cache response API chứa dữ liệu nghiệp vụ; chỉ cache tài nguyên tĩnh.
- Nội dung do AI hoặc tài liệu tạo ra được render như văn bản (không `dangerouslySetInnerHTML`), chống XSS qua nội dung tài liệu.
