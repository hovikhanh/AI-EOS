// Lớp gọi API (T-012, T-111; ADR-003, ADR-006, API_Specification §1). Xác thực bằng cookie session HttpOnly do
// trình duyệt tự gửi; không đọc/ghi token ở localStorage/sessionStorage. Token CSRF chỉ giữ trong bộ nhớ (lấy từ
// response đăng nhập hoặc `GET /auth/me`) và gửi ở header `X-CSRF-Token` cho request ghi (API_Specification §1.3).

export const API_BASE = "/api/v1";
const UNSAFE = new Set(["POST", "PUT", "PATCH", "DELETE"]);

let csrfToken: string | null = null;

/** Đặt token CSRF của session hiện tại (null khi đăng xuất/hết phiên). Chỉ trong bộ nhớ. */
export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export function hasCsrfToken(): boolean {
  return csrfToken !== null;
}

export type FieldError = { field: string; message: string };

/** Lỗi API theo `application/problem+json` (API_Specification §1.5). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string | null;
  readonly errors: FieldError[];

  constructor(status: number, code = "", correlationId: string | null = null, errors: FieldError[] = []) {
    super(`API trả về HTTP ${status}${code ? ` ${code}` : ""}`);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
    this.errors = errors;
  }
}

function asProblem(body: unknown): { code: string; correlationId: string | null; errors: FieldError[] } {
  if (typeof body !== "object" || body === null) {
    return { code: "", correlationId: null, errors: [] };
  }
  const record = body as Record<string, unknown>;
  const errors = Array.isArray(record.errors)
    ? record.errors.filter(
        (e): e is FieldError =>
          typeof e === "object" &&
          e !== null &&
          typeof (e as FieldError).field === "string" &&
          typeof (e as FieldError).message === "string",
      )
    : [];
  return {
    code: typeof record.code === "string" ? record.code : "",
    correlationId: typeof record.correlation_id === "string" ? record.correlation_id : null,
    errors,
  };
}

export type ApiInit = Omit<RequestInit, "body"> & { json?: unknown };

/** Gọi `${API_BASE}${path}`; trả JSON đã parse (kiểu `unknown`) hoặc `undefined` khi 204. */
export async function apiFetch(path: string, init: ApiInit = {}): Promise<unknown> {
  if (!path.startsWith("/") || path.startsWith("//")) {
    throw new Error("Đường dẫn API phải bắt đầu bằng một dấu '/'");
  }
  const { json, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  const method = (rest.method ?? "GET").toUpperCase();
  if (UNSAFE.has(method) && csrfToken !== null) {
    headers.set("X-CSRF-Token", csrfToken);
  }
  let body: BodyInit | undefined;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }
  const response = await fetch(`${API_BASE}${path}`, { ...rest, method, headers, body, credentials: "include" });
  if (!response.ok) {
    let problem = { code: "", correlationId: null as string | null, errors: [] as FieldError[] };
    try {
      problem = asProblem(await response.json());
    } catch {
      // body không phải JSON — giữ mã HTTP
    }
    throw new ApiError(response.status, problem.code, problem.correlationId, problem.errors);
  }
  if (response.status === 204) {
    return undefined;
  }
  return (await response.json()) as unknown;
}

/** Khóa `Idempotency-Key` ngẫu nhiên cho một thao tác (API_Specification §1.6); tạo một lần, dùng lại khi thử lại. */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

export function isApiError(error: unknown, code?: string): error is ApiError {
  return error instanceof ApiError && (code === undefined || error.code === code);
}
