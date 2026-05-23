/* Codex service worker — SELF-UNREGISTERING shim.
 *
 * The previous SW was caching too aggressively, blocking visitors from
 * picking up updated JS/CSS even with ?v= cache-busters. Rather than
 * keep wrestling with cache strategies, this version:
 *
 *   1. Refuses to install/activate as a real worker
 *   2. Unregisters itself on activate
 *   3. Deletes all previously cached entries
 *   4. Lets every fetch go straight to the network
 *
 * After every visitor's browser hits this once, the SW is gone and
 * future requests behave like a normal site (browser cache only,
 * which respects ?v= cache-busters correctly).
 *
 * If we want PWA / offline behaviour back later, we'll re-introduce
 * a more conservative SW that only caches assets with explicit
 * versioned URLs and never HTML.
 */
self.addEventListener("install", e => {
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    // Nuke every cache this origin holds
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));
    // Take control of all open tabs immediately
    await self.clients.claim();
    // Unregister self so no future control intercepts requests
    await self.registration.unregister();
  })());
});

// Pure passthrough — never intercept. Every request goes to network.
self.addEventListener("fetch", () => {});
