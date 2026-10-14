import { QueryClient } from "@tanstack/react-query";

/** Client TanStack Query dùng chung; dữ liệu server chỉ giữ trong bộ nhớ, không lưu xuống storage của trình duyệt. */
export function createQueryClient(): QueryClient {
  return new QueryClient();
}
