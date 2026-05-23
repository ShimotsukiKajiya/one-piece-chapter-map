/* chr-link-upgrader.js — upgrades character.html?name= links to ?id= using the
   baked chr-id-map block. Runs synchronously after render() has already built
   the DOM, so all link nodes exist when this script executes. */
(function () {
  var el = document.getElementById('chr-id-map');
  if (!el) return;
  var map;
  try { map = JSON.parse(el.textContent || '{}'); } catch (_) { return; }
  var keys = Object.keys(map);
  if (!keys.length) return;
  document.querySelectorAll('a[href*="character.html?name="]').forEach(function (a) {
    var m = a.href.match(/[?&]name=([^&]+)/);
    if (!m) return;
    var name = decodeURIComponent(m[1]);
    // 1. Exact lookup
    var id = map[name];
    // 2. Fallback: strip trailing parenthetical and retry
    //    e.g. "Enel (Mantra)" → "Enel", "Whitebeard (implied)" → "Whitebeard"
    if (!id) {
      var stripped = name.replace(/\s*\([^)]*\)\s*$/, '').trim();
      if (stripped && stripped !== name) id = map[stripped];
    }
    // 3. Fallback: case-insensitive match
    if (!id) {
      var lc = name.toLowerCase();
      for (var k in map) { if (k.toLowerCase() === lc) { id = map[k]; break; } }
    }
    if (id) a.href = 'character.html?id=' + encodeURIComponent(id);
  });
})();
