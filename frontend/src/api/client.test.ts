// T-012 — Implementation_Plan §12, test dự kiến 2: request kèm cookie, không đọc/ghi localStorage/sessionStorage.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch } from "./client";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  fetchMock.mockReset();
});

function lastCall(): [string, RequestInit] {
  const call = fetchMock.mock.calls.at(-1);
  if (!call) {
    throw new Error("fetch chưa được gọi");
  }
  return [call[0] as string, call[1] ?? {}];
}

describe("apiFetch", () => {
  it("gọi /api với credentials include và trả JSON", async () => {
    fetchMock.mockResolvedValue(Response.json({ ok: true }));
    await expect(apiFetch("/auth/me")).resolves.toEqual({ ok: true });
    const [url, init] = lastCall();
    expect(url).toBe("/api/auth/me");
    expect(init.credentials).toBe("include");
    expect(new Headers(init.headers).get("Accept")).toBe("application/json");
  });

  it("không cho nơi gọi ghi đè credentials", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(apiFetch("/x", { method: "POST", credentials: "omit" })).resolves.toBeUndefined();
    const [, init] = lastCall();
    expect(init.credentials).toBe("include");
    expect(init.method).toBe("POST");
  });

  it("không đọc hay ghi localStorage/sessionStorage", async () => {
    const spies = (["getItem", "setItem", "removeItem", "clear", "key"] as const).map((name) =>
      vi.spyOn(Storage.prototype, name),
    );
    fetchMock.mockResolvedValue(Response.json({ token: "khong-duoc-luu" }));
    await apiFetch("/auth/me");
    for (const spy of spies) {
      expect(spy).not.toHaveBeenCalled();
    }
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("ném ApiError với mã HTTP khi response lỗi", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 403 }));
    await expect(apiFetch("/admin/users")).rejects.toEqual(new ApiError(403));
  });

  it("từ chối đường dẫn không bắt đầu bằng một dấu '/'", async () => {
    await expect(apiFetch("auth/me")).rejects.toThrow();
    await expect(apiFetch("//evil.example/x")).rejects.toThrow();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
