// ESLint flat config (D-41): typescript-eslint có kiểm tra theo kiểu, luật React Hooks, tắt luật định dạng (Prettier).
import js from "@eslint/js";
import { defineConfig, globalIgnores } from "eslint/config";
import prettier from "eslint-config-prettier";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default defineConfig([
  globalIgnores(["dist", "coverage"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, tseslint.configs.recommendedTypeChecked, reactHooks.configs.flat.recommended],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { projectService: true, tsconfigRootDir: import.meta.dirname },
    },
    rules: {
      // ADR-003: nội dung AI/tài liệu render dạng văn bản, không chèn HTML thô (T-012).
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: "Không dùng dangerouslySetInnerHTML (ADR-003): render nội dung dạng văn bản.",
        },
      ],
    },
  },
  {
    // Service worker dùng lib WebWorker, nằm ở tsconfig riêng (không lẫn với lib DOM).
    files: ["src/sw.ts"],
    languageOptions: {
      globals: globals.serviceworker,
      parserOptions: { projectService: false, project: "./tsconfig.sw.json", tsconfigRootDir: import.meta.dirname },
    },
  },
  {
    files: ["**/*.js"],
    extends: [js.configs.recommended],
    languageOptions: { globals: globals.node },
  },
  prettier,
]);
