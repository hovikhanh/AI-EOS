// Service worker PWA (T-012, ADR-003). Request không thỏa isCacheableRequest (gồm mọi `/api`, điều hướng HTML,
// request khác origin) không bị chặn: trình duyệt xử lý như không có service worker.
import { STATIC_CACHE, isCacheableRequest, isStaleCache, respondFromStaticCache } from "./sw/cachePolicy";

declare const self: ServiceWorkerGlobalScope;

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) => Promise.all(names.filter(isStaleCache).map((name) => caches.delete(name)))),
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (!isCacheableRequest(request.method, request.url, self.location.origin)) {
    return;
  }
  event.respondWith(caches.open(STATIC_CACHE).then((cache) => respondFromStaticCache(request, cache, fetch)));
});
