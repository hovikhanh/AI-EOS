// Phiên đăng nhập phía client (T-111, ADR-006): trạng thái lấy từ `GET /auth/me`; không lưu gì xuống storage.
import { useQuery } from "@tanstack/react-query";
import { apiFetch, ApiError, setCsrfToken } from "@/api/client";
import type { Me } from "@/api/types";

export const ME_KEY = ["auth", "me"] as const;

export async function fetchMe(): Promise<Me> {
  const me = (await apiFetch("/auth/me")) as Me;
  setCsrfToken(me.csrf_token);
  return me;
}

/** `me` khi đã đăng nhập đủ (đã xác minh MFA nếu bắt buộc); lỗi 401 → chưa đăng nhập / chờ MFA. */
export function useMe() {
  return useQuery({
    queryKey: ME_KEY,
    queryFn: fetchMe,
    retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    staleTime: 60_000,
  });
}

export function hasPermission(me: Me | undefined, permission: string): boolean {
  return Boolean(me?.permissions.includes(permission));
}
