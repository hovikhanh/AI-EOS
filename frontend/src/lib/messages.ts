// Thông điệp người dùng cho mã lỗi API (API_Specification §10), theo ngôn ngữ đang dùng (T-607). Không hiển thị chi
// tiết kỹ thuật.
import { ApiError } from "@/api/client";
import { vi, type Messages } from "@/i18n/vi";

export function errorMessage(error: unknown, t: Messages = vi): string {
  if (error instanceof ApiError) {
    const fieldErrors = error.errors.map((e) => e.message).filter(Boolean);
    const base = t.errors[error.code] ?? t.errors.fallback;
    return error.code === "VALIDATION_ERROR" && fieldErrors.length ? `${base} ${fieldErrors.join("; ")}` : base;
  }
  return t.errors.network;
}
