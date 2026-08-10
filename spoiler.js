/**
 * SpoilerGuard — The Shimotsuki Codex
 * ---------------------------------------------------------------------------
 *  Copyright (c) 2024–2026 Shimotsuki Kajiya. All rights reserved.
 *
 *  Code: licensed under the MIT License (see /LICENSE).
 *  Architecture & design: documented in /docs/spoilerguard-design.md
 *  and licensed under CC BY-NC 4.0 (see /LICENSE-DATA.md).
 *
 *  "SpoilerGuard" is the informal name for the system architected here.
 *  The code is freely reusable under MIT terms; the SYSTEM DESIGN
 *  (taxonomy, watchlist, defense layers, and surface map) is a separate
 *  intellectual contribution covered by the CC BY-NC license.
 *
 *  If you fork this code: keep this notice, link back to the source
 *  repo, and preserve attribution in any derivative.
 * ---------------------------------------------------------------------------
 *
 * Universal filter library. Every gated surface imports this:
 *   <script src="spoiler.js"></script>
 *
 * Single source of truth for "is this content safe to show to this user?"
 * Architecture: see /docs/spoilerguard-design.md
 *
 * Usage:
 *   const safe = CodexSpoiler.filterPool(items, 'public');
 *   if (CodexSpoiler.isSafe(item, 'detail')) { render(item); }
 *   const fact = CodexSpoiler.pickDeterministic(pool);
 *   CodexSpoiler.gateRender(elementSelector, item, 'public');
 *
 * Fail-closed: any item without `reveal_chapter` is treated as unsafe.
 * Backwards compat: legacy localStorage.spoilerCutoff is still read (one release).
 */
(function (global) {
  'use strict';

  // ── CONSTANTS ────────────────────────────────────────────────
  const STATE_KEY        = 'codex-spoiler-state';
  const LEGACY_KEY       = 'spoilerCutoff';
  const LEGACY_KEY_EP    = 'spoilerCutoffEp';

  // Updated when a new chapter ships. Single place to bump.
  // Sourced from chapter_dates.json `latest_chapter` at last refresh.
  const LATEST_PUBLISHED_CHAPTER = 1190;

  // Default state for first-time visitors.
  const DEFAULTS = {
    cutoff_chapter:   0,        // 0 = no shield set yet → triggers Strict default
    cutoff_episode:   0,
    buffer_chapters:  5,        // user-tunable in Settings (range 0-50)
    shield_mode:      'auto',   // 'auto' | 'strict' | 'off'
    seen_facts:       [],       // FIFO of last 60 fact IDs (Today in Canon rotation)
    seen_at:          '',       // ISO date — resets seen_facts daily
    unlocked:         {},       // {item_id: true} — explicit per-item reveals
    greeted:          false,    // has cold-start onboarding been shown
  };

  const SEEN_FACTS_MAX = 60;

  // Episode→chapter map (lazy-loaded from episode_map.json on first use)
  let _epToCh = null;
  function loadEpisodeMap() {
    if (_epToCh !== null) return Promise.resolve(_epToCh);
    return fetch('episode_map.json')
      .then(r => r.ok ? r.json() : null)
      .then(em => {
        const out = {};
        for (const e of (em && em.episodes) || []) {
          if (typeof e.ep === 'number' && Array.isArray(e.chapters) && e.chapters.length) {
            // 'last manga chapter covered by this episode' — conservative for shield
            out[e.ep] = Math.max.apply(null, e.chapters);
          }
        }
        _epToCh = out;
        return out;
      })
      .catch(() => { _epToCh = {}; return _epToCh; });
  }

  function episodeToChapterSync(ep) {
    if (!ep || !_epToCh) return null;
    return _epToCh[ep] || null;
  }

  // Character → debut chapter map. Lazy-loaded from chr-debut-map.json so
  // pages that need per-character gating (crews, ships, families, etc.)
  // can call characterDebutChapter(name) sync after `await loadCharacterDebutMap()`.
  let _chrDebut = null;
  // Lower-cased index built from _chrDebut keys for case-insensitive + alias
  // lookup. Built on first use so we don't pay the cost upfront.
  let _chrDebutLowerIdx = null;
  function _buildLowerIdx() {
    if (_chrDebutLowerIdx || !_chrDebut) return;
    const idx = {};
    for (const k of Object.keys(_chrDebut)) {
      idx[k.toLowerCase()] = _chrDebut[k];
      // Common short-form: surname only (last token), e.g. "Luffy" → Monkey D. Luffy
      const tokens = k.split(/\s+/);
      if (tokens.length > 1) {
        const last = tokens[tokens.length - 1].toLowerCase();
        if (!(last in idx)) idx[last] = _chrDebut[k];
      }
    }
    _chrDebutLowerIdx = idx;
  }
  function loadCharacterDebutMap() {
    if (_chrDebut !== null) return Promise.resolve(_chrDebut);
    return fetch('chr-debut-map.json')
      .then(r => r.ok ? r.json() : null)
      .then(m => { _chrDebut = m || {}; _chrDebutLowerIdx = null; return _chrDebut; })
      .catch(() => { _chrDebut = {}; _chrDebutLowerIdx = null; return _chrDebut; });
  }
  function characterDebutChapter(name) {
    if (!name || !_chrDebut) return null;
    // Exact match (preserves case-sensitivity for canonical keys)
    if (_chrDebut[name] != null) return _chrDebut[name];
    // Trim trailing semicolon-noise (e.g. "Luffy; Straw Hat")
    const trimmed = String(name).split(';')[0].trim();
    if (trimmed && _chrDebut[trimmed] != null) return _chrDebut[trimmed];
    // Patch 6: case-insensitive + last-token (alias) fallback. Closes the
    // "characterDebutChapter('Luffy') returned null while ('Monkey D. Luffy')
    // worked" gap surfaced by the 2026-05-02 stress test.
    _buildLowerIdx();
    if (_chrDebutLowerIdx) {
      const lk = String(trimmed || name).toLowerCase();
      if (_chrDebutLowerIdx[lk] != null) return _chrDebutLowerIdx[lk];
    }
    return null;
  }

  // ── STATE I/O ────────────────────────────────────────────────
  // Tampered/corrupted localStorage values must never bypass the shield.
  // clampInt + VALID_MODES + sanitiseState cover Patch 4 from the
  // remediation drafts. Negative buffer no longer flips direction;
  // shield_mode="PWN" no longer disables filtering.
  const VALID_MODES = ['auto', 'strict', 'off'];
  function clampInt(v, lo, hi, fallback) {
    const n = parseInt(v, 10);
    if (!isFinite(n)) return fallback;
    return Math.max(lo, Math.min(hi, n));
  }
  function sanitiseState(raw) {
    if (!raw || typeof raw !== 'object') raw = {};
    return {
      cutoff_chapter:  clampInt(raw.cutoff_chapter,  0, LATEST_PUBLISHED_CHAPTER, DEFAULTS.cutoff_chapter),
      cutoff_episode:  clampInt(raw.cutoff_episode,  0, 9999,                     DEFAULTS.cutoff_episode),
      buffer_chapters: clampInt(raw.buffer_chapters, 0, 50,                       DEFAULTS.buffer_chapters),
      shield_mode:     VALID_MODES.indexOf(raw.shield_mode) >= 0 ? raw.shield_mode : DEFAULTS.shield_mode,
      seen_facts:      Array.isArray(raw.seen_facts) ? raw.seen_facts.slice(0, SEEN_FACTS_MAX) : [],
      seen_at:         typeof raw.seen_at === 'string' ? raw.seen_at : '',
      unlocked:        (raw.unlocked && typeof raw.unlocked === 'object') ? raw.unlocked : {},
      greeted:         raw.greeted === true,
    };
  }

  function loadState() {
    let raw;
    try { raw = JSON.parse(localStorage.getItem(STATE_KEY) || 'null'); }
    catch (_) { raw = null; }

    // Read-compat: migrate legacy keys if present and new state isn't.
    if (!raw) {
      const legacyCh = parseInt(localStorage.getItem(LEGACY_KEY) || '0', 10);
      const legacyEp = parseInt(localStorage.getItem(LEGACY_KEY_EP) || '0', 10);
      if (legacyCh > 0 || legacyEp > 0) {
        raw = {
          cutoff_chapter: legacyCh,
          cutoff_episode: legacyEp,
          // user had a cutoff set, so they've effectively been "greeted"
          greeted: true,
        };
      }
    }
    const merged = sanitiseState(raw);

    // Daily reset of seen_facts so the rotation refreshes.
    const today = new Date().toISOString().slice(0, 10);
    if (merged.seen_at !== today) {
      // Don't WIPE — just bump the date. Rotation uses the seen_facts list to
      // avoid showing the same fact twice within the rolling window. Keeping
      // last 60 across days is the desired feel ("haven't seen this recently").
      merged.seen_at = today;
    }
    return merged;
  }

  function saveState(s) {
    try { localStorage.setItem(STATE_KEY, JSON.stringify(s)); } catch (_) {}
  }

  // Mutable singleton state — read on script load.
  let STATE = loadState();

  // ── CORE GATE ────────────────────────────────────────────────

  /**
   * Effective cutoff chapter for filtering, given the surface class.
   *
   * Surface classes:
   *   'detail'  — user clicked through to a specific entity. Trust them: use exact cutoff.
   *               (Exception: shield_mode 'strict' applies buffer everywhere.)
   *   'public'  — index page, random card, search result. Apply buffer.
   *   'random'  — Today in Canon, Surprise Me. Apply buffer.
   *
   * Most-conservative-of-chapter-and-episode rule applied (anime-only viewers
   * still get manga-spoiler protection).
   */
  function effectiveCutoff(surface) {
    surface = surface || 'public';
    if (STATE.shield_mode === 'off') return Infinity;

    const fromChapter = STATE.cutoff_chapter > 0
      ? STATE.cutoff_chapter : Infinity;
    const fromEpisode = STATE.cutoff_episode > 0
      ? (episodeToChapterSync(STATE.cutoff_episode) || Infinity) : Infinity;
    let base = Math.min(fromChapter, fromEpisode);

    // No cutoff set anywhere → strict default mode: show nothing past the
    // safe pre-timeskip boundary. This is the "first-time visitor" experience.
    if (base === Infinity) base = STATE.shield_mode === 'strict' ? 0 : 597;

    const buffer = STATE.buffer_chapters || 0;
    const apply_buffer = STATE.shield_mode === 'strict' || surface !== 'detail';
    const eff = apply_buffer ? base - buffer : base;
    // Patch 5: hard top-bound. Even if state is corrupted past sanitisation
    // or shield_mode='off' bumped base to Infinity, never return more than
    // the latest published chapter. Prevents accidental "show everything".
    return Math.max(0, Math.min(eff, LATEST_PUBLISHED_CHAPTER));
  }

  /**
   * Is this item safe to show on this surface?
   * Returns false if the item lacks reveal_chapter (fail-closed).
   */
  function isSafe(item, surface) {
    if (!item || typeof item !== 'object') return false;
    const rc = item.reveal_chapter;
    if (typeof rc !== 'number' || rc <= 0) return false;        // fail-closed on missing
    if (rc > LATEST_PUBLISHED_CHAPTER) return false;            // hard top-bound (data error guard)
    if (rc > effectiveCutoff(surface)) return false;
    return true;
  }

  /** Filter an array of items down to safe ones. */
  function filterPool(items, surface) {
    if (!Array.isArray(items)) return [];
    return items.filter(i => isSafe(i, surface));
  }

  // ── DETERMINISTIC PICK FOR DAILY-FRESH FEATURES ──────────────

  // Per-day deterministic hash, mixed with user state so per-user pools differ.
  function dayHash() {
    const d = new Date();
    const ymd = d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate();
    let h = ymd ^ 0x9e3779b9;
    h = ((h >>> 16) ^ h) * 0x85ebca6b;
    h = ((h >>> 13) ^ h) * 0xc2b2ae35;
    h = (h >>> 16) ^ h;
    return Math.abs(h);
  }

  // User mix so users with different cutoffs see different facts on the same day.
  function userMix() {
    return ((STATE.cutoff_chapter | 0) * 73856093) ^ ((STATE.cutoff_episode | 0) * 19349663);
  }

  /**
   * Pick one item deterministically per user-day. Avoids items in seen_facts.
   * Records the chosen item's id into seen_facts (FIFO, capped at 60).
   * Pool should already be safe-filtered (caller's responsibility).
   */
  function pickDeterministic(pool, getId) {
    if (!Array.isArray(pool) || !pool.length) return null;
    getId = getId || (i => i.id || i.fact_id || JSON.stringify(i));

    const seen = new Set(STATE.seen_facts || []);
    let candidates = pool.filter(i => !seen.has(getId(i)));
    if (!candidates.length) candidates = pool;  // pool fully recycled — start over

    const seed = (dayHash() ^ userMix()) >>> 0;
    const idx = seed % candidates.length;
    const pick = candidates[idx];
    if (!pick) return null;

    // Record into seen_facts FIFO
    const id = getId(pick);
    const seenList = (STATE.seen_facts || []).filter(x => x !== id);
    seenList.push(id);
    while (seenList.length > SEEN_FACTS_MAX) seenList.shift();
    STATE.seen_facts = seenList;
    saveState(STATE);

    return pick;
  }

  // ── INLINE BLUR/REVEAL HELPER (for character.html-style per-fact UX) ─────

  /**
   * Wrap a DOM element so that if its item is unsafe, it renders blurred
   * with a "Reveal" button. If safe, leaves it alone. Mirrors the existing
   * character.html pattern, normalised so other pages can reuse.
   */
  function gateRender(el, item, surface) {
    if (!el) return;
    if (isSafe(item, surface)) return;
    if (STATE.unlocked && STATE.unlocked[item.id || item.fact_id]) return;

    el.classList.add('spoiler-blur');
    if (!el.querySelector('.spoiler-reveal-btn')) {
      const btn = document.createElement('button');
      btn.className = 'spoiler-reveal-btn';
      btn.type = 'button';
      btn.textContent = '👁 Reveal';
      btn.style.cssText = 'position:absolute;inset:0;background:rgba(26,22,16,.85);'
        + 'border:1px solid #4a3820;color:#d4a44a;font:inherit;cursor:pointer;'
        + 'padding:6px 12px;border-radius:6px;letter-spacing:1px;';
      btn.addEventListener('click', e => {
        e.stopPropagation();
        el.classList.remove('spoiler-blur');
        btn.remove();
        if (item.id || item.fact_id) {
          const id = item.id || item.fact_id;
          STATE.unlocked = STATE.unlocked || {};
          STATE.unlocked[id] = true;
          saveState(STATE);
        }
      });
      el.style.position = el.style.position || 'relative';
      el.appendChild(btn);
    }
  }

  // ── PUB/SUB ──────────────────────────────────────────────────
  // Pages subscribe via CodexSpoiler.onChange(cb) and the library calls all
  // subscribers when the spoiler state changes (cutoff, shield mode, buffer,
  // caught-up). This is the contract that lets every gated page re-render
  // live when the user changes their setting, without each page having to
  // listen on `storage` events or implement window.setSpoilerCutoff.
  const _listeners = [];
  function onChange(cb) {
    if (typeof cb === 'function') _listeners.push(cb);
    return () => {  // unsubscribe handle
      const i = _listeners.indexOf(cb);
      if (i >= 0) _listeners.splice(i, 1);
    };
  }
  function _emit(reason) {
    for (const cb of _listeners) {
      try { cb(reason || 'change', snapshot()); }
      catch (e) { console.warn('[CodexSpoiler] listener threw:', e); }
    }
  }

  // ── DEFAULT AUTO-RELOAD ──────────────────────────────────────
  // Most gated pages don't (and shouldn't have to) implement a custom
  // re-render when the cutoff changes. They render once at load and trust
  // that future changes will trigger a refresh. This default listener
  // provides that refresh as a reload — universal correctness at the cost
  // of losing in-page state (scroll, search filters).
  //
  // Pages that DO implement a custom re-render (atlas, home Today in Canon,
  // character) call `CodexSpoiler.suppressDefaultReload()` at boot to
  // opt out so the user keeps their scroll position and any interactive state.
  let _suppressReload = false;
  let _reloadTimer = null;
  function suppressDefaultReload() { _suppressReload = true; }
  onChange(function () {
    if (_suppressReload) return;
    // Debounce so a sequence of mutator calls (setCutoff + setShieldMode in
    // the same Apply click) only reloads once.
    if (_reloadTimer) clearTimeout(_reloadTimer);
    _reloadTimer = setTimeout(function () {
      try { location.reload(); } catch (_) {}
    }, 250);
  });

  // ── STATE MUTATORS (used by Settings UI) ─────────────────────

  function setCutoff(chapter, episode) {
    // Clamp on write so the stored value is always in safe range.
    // (Patch 5 also clamps on read in effectiveCutoff, but Settings UI
    // reads STATE.cutoff_chapter directly — without write clamping it
    // would briefly display "99999" for a tampered/typo'd input.)
    if (typeof chapter === 'number' && chapter >= 0) {
      STATE.cutoff_chapter = Math.min(chapter, LATEST_PUBLISHED_CHAPTER);
    }
    if (typeof episode === 'number' && episode >= 0) {
      STATE.cutoff_episode = Math.min(episode, 9999);
    }
    STATE.greeted = true;  // setting cutoff = no longer needs onboarding
    saveState(STATE);
    // Mirror to legacy keys so any non-migrated consumer still works
    try {
      if (chapter > 0) localStorage.setItem(LEGACY_KEY,    String(chapter));
      else             localStorage.removeItem(LEGACY_KEY);
      if (episode > 0) localStorage.setItem(LEGACY_KEY_EP, String(episode));
      else             localStorage.removeItem(LEGACY_KEY_EP);
    } catch (_) {}
    _emit('cutoff');
  }

  function setShieldMode(mode) {
    if (['auto', 'strict', 'off'].includes(mode)) {
      STATE.shield_mode = mode;
      saveState(STATE);
      _emit('mode');
    }
  }

  function setBuffer(n) {
    n = parseInt(n, 10);
    if (!isFinite(n) || n < 0) n = 0;
    if (n > 50) n = 50;
    STATE.buffer_chapters = n;
    saveState(STATE);
    _emit('buffer');
  }

  function markGreeted() {
    STATE.greeted = true;
    saveState(STATE);
    // No emit — greeting state doesn't change cutoff/visibility logic.
  }

  function setCaughtUp() {
    STATE.cutoff_chapter = LATEST_PUBLISHED_CHAPTER;
    STATE.greeted = true;
    saveState(STATE);
    try { localStorage.setItem(LEGACY_KEY, String(LATEST_PUBLISHED_CHAPTER)); } catch (_) {}
    _emit('cutoff');
  }

  /** Read-only view of current state — for diagnostics + Settings UI. */
  function snapshot() { return Object.assign({}, STATE); }

  // ── PORTRAIT GATE (era-aware per-image silhouette) ──────────
  //
  // pickPortrait(c, opts) — returns { url, isSilhouette, label } for the
  // character record `c` at the user's effective cutoff.
  //
  // Selection priority:
  //   1. If c.era_portraits exists with at least one entry whose
  //      from_ch <= cutoff: use the latest qualifying entry.
  //   2. Else if user is caught-up AND opts.fallbackUrl is provided
  //      (the wiki "current" portrait): use that.
  //   3. Else: generic silhouette SVG.
  //
  // Replaces the legacy blanket-CSS brightness(0) silhouette. Callers
  // are responsible for setting alt="Hidden by Spoiler Guard" when
  // isSilhouette is true so the alt-text doesn't leak the name.
  function pickPortrait(c, opts) {
    opts = opts || {};
    const surface = opts.surface || 'detail';
    const fallbackUrl = opts.fallbackUrl || null;
    const cutoff = effectiveCutoff(surface);
    const isCaughtUp = cutoff >= LATEST_PUBLISHED_CHAPTER;

    if (c && Array.isArray(c.era_portraits) && c.era_portraits.length) {
      const sorted = c.era_portraits.slice().sort(
        function (a, b) { return (a.from_ch || 0) - (b.from_ch || 0); }
      );
      let chosen = null;
      for (let i = 0; i < sorted.length; i++) {
        const e = sorted[i];
        if ((e.from_ch || 1) <= cutoff && e.url) chosen = e;
      }
      if (chosen) {
        return { url: chosen.url, isSilhouette: false, label: chosen.label || null };
      }
    }

    if (isCaughtUp && fallbackUrl) {
      return { url: fallbackUrl, isSilhouette: false, label: null };
    }

    return {
      url: 'assets/silhouettes/generic-character-v02.jpg',
      isSilhouette: true,
      label: null,
    };
  }

  // ── PUBLIC API ───────────────────────────────────────────────
  global.CodexSpoiler = {
    // Constants
    LATEST_PUBLISHED_CHAPTER,
    SEEN_FACTS_MAX,
    // Core gate
    isSafe,
    filterPool,
    pickDeterministic,
    gateRender,
    // Per-image portrait gate (era_portraits → silhouette)
    pickPortrait,
    // State accessors
    snapshot,
    effectiveCutoff,
    // State mutators
    setCutoff,
    setShieldMode,
    setBuffer,
    markGreeted,
    setCaughtUp,
    // Pub/sub — pages subscribe to re-render on cutoff/mode/buffer changes
    onChange,
    // Pages with their own re-render logic call this to skip the default reload
    suppressDefaultReload,
    // Episode map (async; resolves once)
    loadEpisodeMap,
    // Character debut map (async; resolves once) + sync lookup after load
    loadCharacterDebutMap,
    characterDebutChapter,
    // For tests / inspection
    _STATE: () => STATE,
  };

  // Pre-load both maps in the background so the first call is sync-fast.
  loadEpisodeMap();
  loadCharacterDebutMap();
})(typeof window !== 'undefined' ? window : this);
