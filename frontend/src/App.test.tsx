import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";

describe("App", () => {
  it("hiển thị tiêu đề ứng dụng", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "AI-EOS" })).toBeDefined();
  });
});
