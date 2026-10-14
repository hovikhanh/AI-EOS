// Chính sách cache của service worker (T-012, ADR-003): chỉ cache tài nguyên tĩnh của bản build, không bao giờ
// cache `/api` hay trang HTML. Tách khỏi src/sw.ts để test được bằng Vitest; chỉ dùng kiểu có ở cả lib DOM và WebWorker.

export const STATIC_CACHE_PREFIX = "aieos-static-";
export const STATIC_CACHE = `${STATIC_CACHE_PREFIX}v1`;

/** File tĩnh ngoài thư mục `assets/` (thư mục chứa file đã băm tên của Vite). */
const STATIC_FILES = new Set(["/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"]);

export function isApiPath(pathname: string): boolean {
  return pathname === "/api" || pathname.startsWith("/api/");
}

export function isCacheableRequest(method: string, url: string, origin: string): boolean {
  if (method !== "GET") {
    return false;
  }
  const parsed = new URL(url);
  if (parsed.origin !== origin || isApiPath(parsed.pathname) || parsed.search !== "") {
    return false;
  }
  return parsed.pathname.startsWith("/assets/") || STATIC_FILES.has(parsed.pathname);
}

/** Cache-first cho request tĩnh; chỉ lưu response thành công cùng origin. */
export async function respondFromStaticCache(
  request: Request,
  cache: Cache,
  fetchFn: (request: Request) => Promise<Response>,
): Promise<Response> {
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetchFn(request);
  if (response.ok && response.type === "basic") {
    await cache.put(request, response.clone());
  }
  return response;
}

export function isStaleCache(name: string): boolean {
  return name.startsWith(STATIC_CACHE_PREFIX) && name !== STATIC_CACHE;
}
