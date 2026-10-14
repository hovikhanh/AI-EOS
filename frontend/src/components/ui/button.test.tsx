// T-012 — Implementation_Plan §12, test dự kiến 7: component nền tảng render với design token trung tính (D-35).
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import css from "../../index.css?raw";
import { Button } from "./button";

afterEach(cleanup);

describe("Button", () => {
  it("render nút với token primary", () => {
    render(<Button>Lưu</Button>);
    const button = screen.getByRole("button", { name: "Lưu" });
    expect(button.className).toContain("bg-primary");
    expect(button.className).toContain("text-primary-foreground");
  });

  it("asChild render phần tử con (vd. liên kết) với class của nút", () => {
    render(
      <Button asChild variant="outline">
        <a href="/x">Mở</a>
      </Button>,
    );
    const link = screen.getByRole("link", { name: "Mở" });
    expect(link.className).toContain("border-input");
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("design token (UX §8.2)", () => {
  const semantic = ["primary", "ai", "success", "warning", "danger", "info", "stale"];
  const neutral = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((step) => `neutral-${step}`);

  it.each([...semantic, ...neutral])("khai báo biến --%s và màu Tailwind tương ứng", (token) => {
    expect(css).toMatch(new RegExp(`^\\s*--${token}:`, "m"));
    expect(css).toMatch(new RegExp(`^\\s*--color-${token}: var\\(--${token}\\);`, "m"));
  });

  it("primary là màu trung tính (thang xám), không phải màu thương hiệu", () => {
    expect(css).toMatch(/^\s*--primary: var\(--neutral-\d+\);/m);
  });
});
