/**
 * cite.js — shared widget to pin Fact Cards into the Theory Workbench.
 *
 * Used by character.html, sbs.html, theories.html. Reads/writes the same
 * localStorage key the Workbench uses (`op-workbench-v1`). When called,
 * appends a citation to the active draft (creates one if none exists),
 * shows a toast, and updates a floating badge in the bottom-right
 * corner with the live cite-count + a link to workbench.html.
 *
 * Usage from any page:
 *   citeFact({
 *     id:       'char:Roronoa Zoro',
 *     type:     'character',
 *     title:    'Roronoa Zoro',
 *     subtitle: 'Pirate Hunter · Strawhats',
 *     href:     'character.html?name=Roronoa+Zoro',
 *   });
 */
(function () {
  const STORAGE_KEY = 'op-workbench-v1';

  function load() {
    try {
      const s = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (s && Array.isArray(s.drafts)) return s;
    } catch (e) {}
    return { drafts: [], activeDraftId: null };
  }
  function save(s) { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); }
  function newDraftId() {
    return 'wb_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 6);
  }

  function ensureActiveDraft(s) {
    let d = s.drafts.find(x => x.id === s.activeDraftId);
    if (d) return d;
    if (!s.drafts.length) {
      d = { id: newDraftId(), title: 'Untitled theory', body: '',
            citations: [], createdAt: Date.now(), updatedAt: Date.now() };
      s.drafts.push(d);
    } else {
      d = s.drafts[0];
    }
    s.activeDraftId = d.id;
    return d;
  }

  function citeFact(card) {
    if (!card || !card.id) return false;
    const s = load();
    const d = ensureActiveDraft(s);
    if (d.citations.some(c => c.id === card.id)) {
      toast('Already in your active draft');
      updateBadge();
      return false;
    }
    d.citations.push({
      id:       card.id,
      stance:   'context',
      note:     '',
      snapshot: {
        type:     card.type,
        title:    card.title,
        subtitle: card.subtitle || '',
        href:     card.href     || '',
      },
    });
    d.updatedAt = Date.now();
    save(s);
    toast(`✓ Cited in "${(d.title || 'Untitled').slice(0, 40)}"`);
    updateBadge();
    return true;
  }

  // ── BADGE ────────────────────────────────────────────────
  function updateBadge() {
    const s = load();
    const d = s.drafts.find(x => x.id === s.activeDraftId);
    const n = d ? d.citations.length : 0;
    let el = document.getElementById('cite-badge');
    if (!n) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('a');
      el.id = 'cite-badge';
      el.href = 'workbench.html';
      el.style.cssText =
        'position:fixed;bottom:20px;right:20px;z-index:9990;' +
        'background:#1a1610;color:#f5c95e;border:1px solid #d4a44a;' +
        'border-radius:999px;padding:10px 16px;font-size:0.85rem;' +
        'font-family:"Segoe UI",system-ui,sans-serif;text-decoration:none;' +
        'box-shadow:0 4px 16px rgba(0,0,0,0.5);transition:transform .15s';
      el.onmouseenter = () => el.style.transform = 'translateY(-2px)';
      el.onmouseleave = () => el.style.transform = 'translateY(0)';
      document.body.appendChild(el);
    }
    el.textContent = `📌 ${n} cited · open Workbench →`;
  }

  // ── TOAST ────────────────────────────────────────────────
  let toastTimer = null;
  function toast(msg) {
    let el = document.getElementById('cite-toast');
    if (!el) {
      el = document.createElement('div');
      el.id = 'cite-toast';
      el.style.cssText =
        'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);' +
        'background:#1a1610;color:#e8d8b0;border:1px solid #d4a44a;' +
        'border-radius:10px;padding:10px 16px;font-size:0.88rem;z-index:9999;' +
        'font-family:"Segoe UI",system-ui,sans-serif;' +
        'box-shadow:0 6px 24px rgba(0,0,0,0.6);' +
        'opacity:0;pointer-events:none;transition:opacity .2s';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.style.opacity = '0'; }, 1800);
  }

  // Expose globally + initial badge update on page load
  window.citeFact = citeFact;
  window.addEventListener('DOMContentLoaded', updateBadge);
  // React to other tabs editing the workbench
  window.addEventListener('storage', e => {
    if (e.key === STORAGE_KEY) updateBadge();
  });
})();
