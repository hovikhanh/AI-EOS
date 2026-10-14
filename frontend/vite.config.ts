import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // "/src" là đường dẫn tính từ gốc dự án Vite, dùng được trên mọi hệ điều hành.
    alias: { "@": "/src" },
  },
  build: {
    rolldownOptions: {
      // Service worker (T-012) build riêng thành `sw.js` ở gốc để có scope "/"; không băm tên.
      input: { main: "index.html", sw: "src/sw.ts" },
      output: {
        entryFileNames: (chunk) => (chunk.name === "sw" ? "sw.js" : "assets/[name]-[hash].js"),
      },
    },
  },
  test: {
    environment: "jsdom",
    css: true,
  },
});
