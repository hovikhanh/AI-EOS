import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter } from "react-router";
import { createQueryClient } from "./api/queryClient";
import { App } from "./App";
import { routes } from "./routes";
import "./index.css";

const root = document.getElementById("root");
if (!root) {
  throw new Error("Không tìm thấy phần tử #root");
}

createRoot(root).render(
  <StrictMode>
    <App router={createBrowserRouter(routes)} queryClient={createQueryClient()} />
  </StrictMode>,
);

// PWA (ADR-003): service worker chỉ cache tài nguyên tĩnh của bản build; không đăng ký ở chế độ dev.
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch((error: unknown) => {
    console.error("Không đăng ký được service worker", error);
  });
}
