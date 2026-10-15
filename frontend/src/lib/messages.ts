// Thông điệp người dùng cho mã lỗi API (API_Specification §10). Không hiển thị chi tiết kỹ thuật.
import { ApiError } from "@/api/client";

const MESSAGES: Record<string, string> = {
  INVALID_CREDENTIALS: "Email, mật khẩu hoặc mã không đúng.",
  ACCOUNT_LOCKED: "Tài khoản đang bị khóa tạm. Thử lại sau hoặc liên hệ quản trị.",
  RATE_LIMITED: "Thử quá nhiều lần. Vui lòng chờ rồi thử lại.",
  INVITATION_INVALID: "Lời mời không còn hiệu lực. Vui lòng liên hệ quản trị.",
  FORBIDDEN: "Bạn không có quyền thực hiện thao tác này.",
  NOT_FOUND: "Không tìm thấy hoặc bạn không có quyền.",
  VERSION_CONFLICT: "Dữ liệu đã thay đổi bởi người khác. Tải lại rồi thao tác lại.",
  PRECONDITION_REQUIRED: "Dữ liệu đã thay đổi bởi người khác. Tải lại rồi thao tác lại.",
  SELF_ROLE_CHANGE: "Không thể tự thay đổi role hay quyền của chính mình.",
  ROLE_COMBINATION_FORBIDDEN: "Không được gán ADMIN và CFO cho cùng một tài khoản.",
  ASSIGNMENT_NOT_ELIGIBLE: "Role của người này không đủ điều kiện nhận quyền được chọn.",
  LAST_ADMIN: "Không thể gỡ hay khóa quản trị viên hoạt động cuối cùng.",
  INVALID_STATE: "Thao tác không hợp lệ với trạng thái hiện tại.",
  IDEMPOTENCY_KEY_REUSED: "Yêu cầu trùng với một yêu cầu trước nhưng khác nội dung. Vui lòng thử lại.",
  VALIDATION_ERROR: "Dữ liệu chưa hợp lệ.",
  CSRF_FAILED: "Phiên làm việc không hợp lệ. Vui lòng đăng nhập lại.",
  UNAUTHENTICATED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  MFA_REQUIRED: "Cần xác minh MFA.",
  REAUTH_REQUIRED: "Cần xác thực lại để tiếp tục.",
};

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const fieldErrors = error.errors.map((e) => e.message).filter(Boolean);
    const base = MESSAGES[error.code] ?? "Có lỗi tạm thời. Vui lòng thử lại.";
    return error.code === "VALIDATION_ERROR" && fieldErrors.length ? `${base} ${fieldErrors.join("; ")}` : base;
  }
  return "Không kết nối được máy chủ. Vui lòng thử lại.";
}
