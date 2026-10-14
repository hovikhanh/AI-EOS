// T-012 — Implementation_Plan §12, test dự kiến 3: service worker không cache `/api`; chỉ cache tài nguyên tĩnh.
import { describe, expect, it, vi } from "vitest";
import { STATIC_CACHE, isCacheableRequest, isStaleCache, respondFromStaticCache } from "./cachePolicy";

const ORIGIN = "https://aieos.local";

describe("isCacheableRequest", () => {
  it.each([
    "/api",
    "/api/",
    "/api/auth/me",
    "/api/assets/x.js",
    "/api/manifest.webmanifest",
    "/",
    "/index.html",
    "/finance",
    "/assets/index-abc.js?v=1",
  ])("không cache %s", (path) => {
    expect(isCacheableRequest("GET", `${ORIGIN}${path}`, ORIGIN)).toBe(false);
  });

  it.each(["/assets/index-abc123.js", "/assets/index-abc123.css", "/manifest.webmanifest", "/icons/icon-192.png"])(
    "cache tài nguyên tĩnh %s",
    (path) => {
      expect(isCacheableRequest("GET", `${ORIGIN}${path}`, ORIGIN)).toBe(true);
    },
  );

  it("không cache request khác GET hoặc khác origin", () => {
    expect(isCacheableRequest("POST", `${ORIGIN}/assets/a.js`, ORIGIN)).toBe(false);
    expect(isCacheableRequest("HEAD", `${ORIGIN}/assets/a.js`, ORIGIN)).toBe(false);
    expect(isCacheableRequest("GET", "https://cdn.example/assets/a.js", ORIGIN)).toBe(false);
  });
});

function fakeCache(initial?: Response) {
  return {
    match: vi.fn().mockResolvedValue(initial),
    put: vi.fn().mockResolvedValue(undefined),
  };
}

describe("respondFromStaticCache", () => {
  const request = new Request(`${ORIGIN}/assets/a.js`);

  it("trả bản trong cache mà không gọi mạng", async () => {
    const cached = new Response("cached");
    const cache = fakeCache(cached);
    const fetchFn = vi.fn<(r: Request) => Promise<Response>>();
    await expect(respondFromStaticCache(request, cache as unknown as Cache, fetchFn)).resolves.toBe(cached);
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it("lưu response thành công khi chưa có trong cache", async () => {
    const cache = fakeCache();
    const network = new Response("net", { status: 200 });
    Object.defineProperty(network, "type", { value: "basic" });
    const fetchFn = vi.fn<(r: Request) => Promise<Response>>().mockResolvedValue(network);
    await expect(respondFromStaticCache(request, cache as unknown as Cache, fetchFn)).resolves.toBe(network);
    expect(cache.put).toHaveBeenCalledOnce();
  });

  it("không lưu response lỗi", async () => {
    const cache = fakeCache();
    const network = new Response("x", { status: 404 });
    Object.defineProperty(network, "type", { value: "basic" });
    const fetchFn = vi.fn<(r: Request) => Promise<Response>>().mockResolvedValue(network);
    await respondFromStaticCache(request, cache as unknown as Cache, fetchFn);
    expect(cache.put).not.toHaveBeenCalled();
  });
});

describe("isStaleCache", () => {
  it("chỉ xóa cache tĩnh phiên bản cũ của ứng dụng", () => {
    expect(isStaleCache(STATIC_CACHE)).toBe(false);
    expect(isStaleCache("aieos-static-v0")).toBe(true);
    expect(isStaleCache("cache-khac")).toBe(false);
  });
});
