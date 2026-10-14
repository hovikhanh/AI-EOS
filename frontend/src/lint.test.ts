// @vitest-environment node
// T-012 — Implementation_Plan §12, test dự kiến 6: ESLint chặn dangerouslySetInnerHTML (ADR-003).
import { ESLint } from "eslint";
import { describe, expect, it } from "vitest";

const RULE = "no-restricted-syntax";

async function lint(code: string) {
  const eslint = new ESLint({
    cwd: decodeURIComponent(new URL("..", import.meta.url).pathname),
    // Chỉ chạy luật cần kiểm; tắt type-aware parsing vì file thử không có trên đĩa.
    overrideConfig: { languageOptions: { parserOptions: { projectService: false, project: null } } },
    ruleFilter: ({ ruleId }) => ruleId === RULE,
  });
  const [result] = await eslint.lintText(code, { filePath: "src/lint-probe.tsx" });
  return result?.messages ?? [];
}

describe("ESLint", () => {
  it("báo lỗi khi dùng dangerouslySetInnerHTML", async () => {
    const messages = await lint(`export const X = () => <div dangerouslySetInnerHTML={{ __html: "<b>x</b>" }} />;\n`);
    expect(messages.some((m) => m.ruleId === RULE && m.severity === 2)).toBe(true);
  });

  it("không báo lỗi với nội dung render dạng văn bản", async () => {
    const messages = await lint(`export const X = ({ t }: { t: string }) => <div>{t}</div>;\n`);
    expect(messages).toEqual([]);
  });
});
