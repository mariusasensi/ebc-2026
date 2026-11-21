// Memòria cau de la web EBC 2026.
// Canvia VERSION quan pugis canvis importants perquè tothom rebi la versió nova.
const VERSION = "ebc-v7";
const STATIC = VERSION + "-static", RUNTIME = VERSION + "-runtime", TILES = VERSION + "-tiles";
const MAX_TILES = 400;

self.addEventListener("install", e => {
  e.waitUntil(caches.open(STATIC).then(c => c.addAll(["./", "./index.html", "./og.jpg", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png"])).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => !k.startsWith(VERSION)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function trim(name, max) {
  const c = await caches.open(name), keys = await c.keys();
  for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
}
// Primer la cau i, en segon pla, actualitza (per a la pàgina, fotos, GPX i PDF)
async function staleWhileRevalidate(req, name) {
  const c = await caches.open(name), hit = await c.match(req);
  const net = fetch(req).then(r => { if (r.ok) c.put(req, r.clone()); return r; }).catch(() => hit);
  return hit || net;
}
// Primer la cau, sense revalidar (llibreries amb versió fixa i fonts)
async function cacheFirst(req, name) {
  const c = await caches.open(name), hit = await c.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok || r.type === "opaque") c.put(req, r.clone());
  return r;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    e.respondWith(staleWhileRevalidate(req, req.mode === "navigate" ? STATIC : RUNTIME));
  } else if (/cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/.test(url.host)) {
    e.respondWith(cacheFirst(req, RUNTIME));
  } else if (/tile\.openstreetmap\.org|tile\.opentopomap\.org|arcgisonline\.com/.test(url.host)) {
    e.respondWith(staleWhileRevalidate(req, TILES).then(r => { trim(TILES, MAX_TILES); return r; }));
  }
});
