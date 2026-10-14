# infra

Chỗ dành cho Docker Compose và cấu hình triển khai (Architecture §9.1). Compose: T-003 (cấu hình), T-013 (tích hợp) — chưa có (D-43).

`.env.example` (T-004): danh sách tên biến cấu hình/secret, **không có giá trị** (Implementation_Plan §7). Sao chép thành file môi trường không commit rồi điền giá trị; secret có thể đặt qua `<TÊN>_FILE` (Docker secrets). Loader: `backend/src/aieos/platform/config.py` — thiếu biến bắt buộc thì tiến trình dừng (mã 2), thông báo chỉ nêu tên biến.
