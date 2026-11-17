// Service worker mínimo: permite instalar la app en el móvil y abrirla sin conexión
// (muestra la pantalla de inicio). Los datos y el análisis siempre van al servidor.
const CACHE = "telerehab-v4";
const ESTATICOS = ["/", "/static/app.css", "/static/app.js", "/static/icono-192.png", "/static/icono.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ESTATICOS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});
// Red primero (para ver siempre la última versión) y caché como respaldo sin conexión
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/") || url.pathname.startsWith("/ws/")
      || url.pathname.startsWith("/videos_explicativos/")) return;
  e.respondWith(fetch(e.request).then((r) => {
    const copia = r.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copia));
    return r;
  }).catch(() => caches.match(e.request)));
});
