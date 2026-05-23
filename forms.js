/* forms.js — Character form-cycle UI module.
 *
 * Wraps a portrait element with form-cycling controls:
 *   • Click left half of portrait  → previous form
 *   • Click right half of portrait → next form
 *   • Right-click anywhere on portrait → next form (also)
 *   • Small label below shows current form name
 *   • Tinted aura indicates non-default forms
 *   • Dot indicator shows position in form list
 *   • Fade transition (200ms) on swap
 *
 * Usage:
 *   <script src="forms.js" defer></script>
 *   <script>
 *     // After page renders, find any element with [data-form-character] attribute
 *     // and wrap it. Or call manually:
 *     OPForms.wrap(element, "Monkey D. Luffy");
 *   </script>
 *
 * Data source:
 *   <script id="character-forms" type="application/json">{...}</script>
 *   (baked by bake_character_forms() in bake.py)
 */
(function () {
  if (window.OPForms) return;

  // Pull data from the page payload — graceful if absent
  const FORMS = (() => {
    const el = document.getElementById('character-forms');
    if (!el) return {};
    try { return JSON.parse(el.textContent || '{}').characters || {}; }
    catch (_) { return {}; }
  })();

  // ─── styles ───
  if (!document.getElementById('forms-styles')) {
    const style = document.createElement('style');
    style.id = 'forms-styles';
    style.textContent = `
      .op-form-wrap {
        position: relative;
        display: inline-block;
      }
      .op-form-wrap .op-form-zone-left,
      .op-form-wrap .op-form-zone-right {
        position: absolute; top: 0; bottom: 0;
        width: 35%;
        cursor: pointer;
        z-index: 5;
        background: transparent;
        border: none;
        transition: background 0.15s;
        display: flex; align-items: center;
        opacity: 0;
      }
      .op-form-wrap .op-form-zone-left  { left: 0;  justify-content: flex-start; padding-left: 3px; }
      .op-form-wrap .op-form-zone-right { right: 0; justify-content: flex-end;   padding-right: 3px; }
      /* Subtle on hover — image stays clearly visible */
      .op-form-wrap:hover .op-form-zone-left,
      .op-form-wrap:hover .op-form-zone-right { opacity: 0.75; }
      .op-form-wrap .op-form-zone-left:hover {
        background: linear-gradient(90deg, rgba(212,164,74,0.18) 0%, transparent 70%);
        opacity: 1;
      }
      .op-form-wrap .op-form-zone-right:hover {
        background: linear-gradient(270deg, rgba(212,164,74,0.18) 0%, transparent 70%);
        opacity: 1;
      }
      .op-form-wrap .op-form-arrow {
        color: #f5c95e;
        font-size: 1.2rem;
        font-weight: 900;
        text-shadow: 0 0 4px rgba(0,0,0,0.95), 0 1px 2px rgba(0,0,0,0.95);
        line-height: 1;
        pointer-events: none;
      }

      /* Image filter swap — gives a real visible change between forms
         even when we don't have separate form images. The base form has
         no filter; non-default forms get a distinctive hue + saturate. */
      .op-form-wrap > img,
      .op-form-wrap img {
        transition: filter 0.3s ease, opacity 0.2s ease;
      }
      .op-form-wrap > img,
      .op-form-wrap > span {
        transition: opacity 0.2s ease;
      }
      .op-form-wrap.swapping > img,
      .op-form-wrap.swapping > span,
      .op-form-wrap.swapping img { opacity: 0.25; }

      /* Aura tint overlay — much more visible than before */
      .op-form-wrap .op-form-aura {
        position: absolute; inset: 0;
        border-radius: inherit;
        opacity: 0;
        transition: opacity 0.3s, background 0.3s, box-shadow 0.3s;
        pointer-events: none;
        z-index: 2;
        mix-blend-mode: color;
      }
      .op-form-wrap .op-form-aura.active { opacity: 0.7; }

      /* Pulsing ring around the portrait when not on default form */
      .op-form-wrap.in-form {
        box-shadow: 0 0 0 2px var(--op-form-color, #d4a44a),
                    0 0 14px var(--op-form-color, #d4a44a);
      }

      .op-form-badge {
        position: absolute;
        bottom: 4px; left: 50%; transform: translateX(-50%);
        background: rgba(26, 22, 16, 0.92);
        border: 1px solid #d4a44a;
        color: #f5c95e;
        font-size: 0.62rem;
        letter-spacing: 0.5px;
        padding: 2px 7px;
        border-radius: 9px;
        font-weight: 700;
        white-space: nowrap;
        max-width: 90%;
        overflow: hidden;
        text-overflow: ellipsis;
        z-index: 6;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.18s;
        font-family: 'Segoe UI', system-ui, sans-serif;
      }
      .op-form-wrap.has-form .op-form-badge { opacity: 1; }
      .op-form-wrap:hover .op-form-badge { opacity: 1; }

      .op-form-dots {
        position: absolute;
        top: 4px; left: 50%; transform: translateX(-50%);
        display: flex; gap: 3px;
        z-index: 6;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.18s;
      }
      .op-form-wrap:hover .op-form-dots { opacity: 1; }
      .op-form-dots .dot {
        width: 5px; height: 5px;
        background: rgba(212,164,74,0.4);
        border-radius: 50%;
        border: 1px solid rgba(0,0,0,0.4);
      }
      .op-form-dots .dot.active {
        background: #f5c95e;
      }

      /* compact mode for small tile portraits */
      .op-form-wrap.compact .op-form-arrow { font-size: 0.85rem; }
      .op-form-wrap.compact .op-form-badge { font-size: 0.55rem; padding: 1px 5px; bottom: 2px; }
      .op-form-wrap.compact .op-form-dots .dot { width: 4px; height: 4px; }

      /* Indicator showing this character has multiple forms — shown when not hovering */
      .op-form-wrap.has-multiple::before {
        content: '⇆';
        position: absolute;
        bottom: 2px; right: 2px;
        background: rgba(26, 22, 16, 0.85);
        color: #d4a44a;
        font-size: 0.6rem;
        width: 14px; height: 14px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        z-index: 6;
        pointer-events: none;
        font-weight: 900;
        opacity: 0.75;
        transition: opacity 0.15s;
      }
      .op-form-wrap.has-multiple:hover::before { opacity: 0; }
    `;
    document.head.appendChild(style);
  }

  // ─── core ───
  // Prefer CodexSpoiler.effectiveCutoff('detail') (mirrors the rest of the
  // spoiler system, including buffer + shield mode). Fall back to the legacy
  // localStorage key if spoiler.js hasn't loaded yet.
  function getSpoilerCutoff() {
    if (typeof CodexSpoiler !== 'undefined' && CodexSpoiler.effectiveCutoff) {
      const eff = CodexSpoiler.effectiveCutoff('detail');
      return Number.isFinite(eff) ? eff : 0;
    }
    return parseInt(localStorage.getItem('spoilerCutoff') || '0', 10);
  }
  function parseFormDebut(debut) {
    if (!debut) return 0;
    const m = String(debut).match(/\d+/);
    return m ? parseInt(m[0]) : 0;
  }

  function getForms(name) {
    if (!FORMS[name] || !FORMS[name].forms) return null;
    const all = FORMS[name].forms;
    const cutoff = getSpoilerCutoff();
    if (!cutoff) return all;
    // Always keep index-0 (the default/base form). Filter non-default forms
    // whose debut chapter exceeds the reader's current chapter.
    const visible = all.filter((f, i) => {
      if (i === 0) return true;
      const ch = parseFormDebut(f.debut);
      return ch === 0 || ch <= cutoff;
    });
    // Need at least 2 visible forms for the cycle UI to make sense.
    return visible.length >= 2 ? visible : null;
  }

  function wrap(el, characterName, options = {}) {
    if (!el || !characterName) return false;
    if (el.dataset.opFormWrapped === '1') return true;
    const forms = getForms(characterName);
    if (!forms || forms.length < 2) return false;

    el.dataset.opFormWrapped = '1';
    el.classList.add('op-form-wrap', 'has-multiple');
    if (options.compact) el.classList.add('compact');

    let idx = 0;

    // Aura layer (for tint without replacing image)
    const aura = document.createElement('span');
    aura.className = 'op-form-aura';
    el.appendChild(aura);

    // Click zones
    const zL = document.createElement('button');
    zL.className = 'op-form-zone-left';
    zL.type = 'button';
    zL.setAttribute('aria-label', 'Previous form');
    zL.innerHTML = '<span class="op-form-arrow">‹</span>';
    const zR = document.createElement('button');
    zR.className = 'op-form-zone-right';
    zR.type = 'button';
    zR.setAttribute('aria-label', 'Next form');
    zR.innerHTML = '<span class="op-form-arrow">›</span>';
    el.appendChild(zL);
    el.appendChild(zR);

    // Dots indicator
    const dots = document.createElement('div');
    dots.className = 'op-form-dots';
    forms.forEach((_, i) => {
      const d = document.createElement('span');
      d.className = 'dot' + (i === 0 ? ' active' : '');
      dots.appendChild(d);
    });
    el.appendChild(dots);

    // Form name badge
    const badge = document.createElement('div');
    badge.className = 'op-form-badge';
    badge.textContent = forms[0].name;
    el.appendChild(badge);

    // CSS filter recipe per kind — gives a strong visible image change
    // even when we don't have a real separate image per form.
    const FILTER = {
      'default':   '',
      'haki':      'saturate(1.6) brightness(0.85) contrast(1.15) drop-shadow(0 0 6px rgba(212,164,74,.6))',
      'haki-tech': 'saturate(1.7) brightness(0.9) contrast(1.2) hue-rotate(-15deg) drop-shadow(0 0 8px rgba(255,107,26,.55))',
      'tech':      'sepia(0.35) saturate(1.4) contrast(1.15) hue-rotate(-8deg)',
      'ability':   'saturate(1.6) hue-rotate(15deg) brightness(1.05) drop-shadow(0 0 6px rgba(255,107,26,.5))',
      'form':      'saturate(1.55) contrast(1.15) brightness(1.05)',
      'full':      'saturate(1.8) contrast(1.35) brightness(0.9) drop-shadow(0 0 10px rgba(180,80,40,.7))',
      'awakened':  'saturate(2.2) contrast(1.4) brightness(1.1) drop-shadow(0 0 14px rgba(245,201,94,.85))',
      'race':      'saturate(2) hue-rotate(-12deg) contrast(1.3) brightness(1.05) drop-shadow(0 0 10px rgba(255,107,26,.7))',
      'alter-ego': 'sepia(0.5) saturate(1.5) hue-rotate(20deg) contrast(1.15)',
    };

    function applyFilter(kind) {
      const filter = FILTER[kind] || FILTER['form'];
      const targets = el.querySelectorAll('img');
      targets.forEach(img => { img.style.filter = filter; });
      // Also style the gold-initial fallback span if any
      const spans = el.querySelectorAll(':scope > span:not(.op-form-aura):not(.op-form-zone-left):not(.op-form-zone-right):not(.op-form-dots):not(.op-form-badge)');
      spans.forEach(s => { s.style.filter = filter; });
    }

    // Cache the original img src so we can revert to default form.
    // CRITICAL: clear the inline onerror="this.remove()" set by character.html etc.
    // — otherwise a single failed form-image load nukes the IMG element entirely.
    const baseImg = el.querySelector('img');
    const baseSrc = baseImg ? baseImg.src : null;
    if (baseImg) {
      baseImg.removeAttribute('onerror');
      baseImg.dataset.opOriginal = baseSrc || '';
    }

    function applyImage(form) {
      const img = el.querySelector('img');
      if (!img) return;
      // Use the form's curated image if present, otherwise revert to baseSrc.
      const target = form.image || baseSrc;
      if (!target) return;
      if (img.src === target) return;
      // Pre-load via a probe Image so we can revert cleanly if it 404s
      // — without leaving the visible img in a broken state.
      const probe = new Image();
      probe.onload = () => {
        img.src = target;
      };
      probe.onerror = () => {
        // Stay on whatever was last successful
      };
      probe.src = target;
    }

    function show(i) {
      const next = ((i % forms.length) + forms.length) % forms.length;
      el.classList.add('swapping', 'has-form');
      setTimeout(() => {
        idx = next;
        const f = forms[idx];
        badge.textContent = f.name;
        // Aura tint
        if (f.tint && f.kind !== 'default') {
          aura.style.background = f.tint;
          aura.classList.add('active');
          el.classList.add('in-form');
          el.style.setProperty('--op-form-color', f.tint);
        } else {
          aura.classList.remove('active');
          el.classList.remove('in-form');
        }
        // Swap actual image if the form has a curated image URL
        applyImage(f);
        // Apply filter to image so the user can SEE a change even without separate images
        applyFilter(f.kind);
        // Dots
        dots.querySelectorAll('.dot').forEach((d, j) => d.classList.toggle('active', j === idx));
        el.classList.remove('swapping');
        // Hide form badge again on default to declutter (still appears on hover)
        if (idx === 0) el.classList.remove('has-form');
      }, 100);
    }

    function next(e) { e.preventDefault(); e.stopPropagation(); show(idx + 1); }
    function prev(e) { e.preventDefault(); e.stopPropagation(); show(idx - 1); }

    zL.addEventListener('click', prev);
    zR.addEventListener('click', next);
    el.addEventListener('contextmenu', next);

    return true;
  }

  // Auto-wrap any element marked [data-form-character]
  function autoWrap(root = document) {
    root.querySelectorAll('[data-form-character]').forEach(el => {
      if (el.dataset.opFormWrapped === '1') return;
      const name = el.dataset.formCharacter;
      const compact = el.dataset.formCompact === '1';
      wrap(el, name, { compact });
    });
  }

  // Reset a previously-wrapped element back to its bare state so it can be
  // re-wrapped after a cutoff change. Removes injected children, classes,
  // inline filter, and the wrapped flag.
  function unwrap(el) {
    if (!el || el.dataset.opFormWrapped !== '1') return false;
    el.querySelectorAll('.op-form-zone-left, .op-form-zone-right, .op-form-dots, .op-form-badge, .op-form-aura').forEach(n => n.remove());
    el.classList.remove('op-form-wrap', 'has-multiple', 'compact', 'has-form');
    delete el.dataset.opFormWrapped;
    const img = el.querySelector('img');
    if (img) img.style.filter = '';
    return true;
  }
  function rewrapAll() {
    document.querySelectorAll('[data-form-character]').forEach(el => unwrap(el));
    autoWrap();
  }

  window.OPForms = {
    wrap,
    autoWrap,
    unwrap,
    rewrapAll,
    has: name => !!getForms(name),
    forms: name => getForms(name),
  };

  // Initial pass
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => autoWrap());
  } else {
    autoWrap();
  }

  // Re-evaluate the cycler whenever the spoiler cutoff changes — otherwise
  // a user who navigated while caught-up, cycled to a late form, and then
  // lowered their cutoff would still see the late form's badge text.
  function _subscribeOnChange() {
    if (typeof CodexSpoiler !== 'undefined' && CodexSpoiler.onChange) {
      CodexSpoiler.onChange(rewrapAll);
    } else {
      // spoiler.js may load after forms.js — retry briefly.
      setTimeout(_subscribeOnChange, 200);
    }
  }
  _subscribeOnChange();
})();
