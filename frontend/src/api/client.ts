// Lớp gọi API cho TanStack Query (T-012, ADR-003, ADR-006): xác thực bằng cookie session HttpOnly do trình duyệt
// tự gửi. Không đọc/ghi token ở localStorage/sessionStorage. CSRF header cho request ghi thuộc T-007/T-111.

export const API_BASE = "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`API trả về HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Gọi `${API_BASE}${path}`; trả về JSON đã parse (kiểu `unknown`, nơi gọi tự kiểm tra) hoặc `undefined` khi 204. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<unknown> {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("Đường dẫn API phải bắt đầu bằng một dấu '/'");
  }
  const headers = new Headers(init.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" });
  if (!response.ok) {
    throw new ApiError(response.status);
  }
  if (response.status === 204) {
    return undefined;
  }
  return (await response.json()) as unknown;
}
