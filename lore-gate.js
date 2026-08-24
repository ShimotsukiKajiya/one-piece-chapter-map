/* lore-gate.js — Spoiler Shield for the curated lore pages.
 *
 * These pages (tech, items, materials, ancient-weapons, poneglyphs, races,
 * moments, music, and the prose pages) render from small curated JSON files.
 * Every entry already carries a debut chapter — the gate was simply never
 * wired, and the page-scoped hook at the bottom of each page was a documented
 * no-op. This supplies the missing gate.
 *
 * Load this BEFORE the page's render script. It deliberately does not depend
 * on spoiler.js, which those pages load after they render.
 *
 * Two layers:
 *   1. DEBUT GATE  — hide an entry whose debut chapter is past the cutoff.
 *   2. LEXICON GATE — hide an entry whose visible text names a concept the
 *      reader has not reached. Catches prose and summaries, where the leak is
 *      a word rather than a dated field.
 *
 * Fail-late throughout: when a chapter cannot be determined, hide.
 */
(function (root) {
  'use strict';

  // term -> first chapter at which it is safe to show.
  // Longest-match first matters for overlapping terms.
  // LEXICON-START
  // Generated from docs/leak-lexicon.json by scripts/sync_lexicon.py.
  // Do not hand-edit: edit the JSON and re-run the script.
  // Longest terms first, so an overlapping shorter term cannot shadow one.
  var LEXICON = [
    ['Trafalgar D. Water Law', 763], ['Marshall D. Teach', 234],
    ['Celestial Dragon', 497], ['Ancient Kingdom', 395],
    ['Rocks D. Xebec', 957], ['Four Emperors', 432], ["God's Knights", 1086],
    ['Empty Throne', 908], ['Kouzuki Oden', 920], ['Mother Flame', 1086],
    ['Void Century', 395], ['Buster Call', 395], ['Devil Fruit', 19],
    ['World Noble', 497], ['Laugh Tale', 967], ['Awakening', 783],
    ['Poneglyph', 202], ['Flevance', 762], ['Poseidon', 628],
    ['Shamrock', 1136], ['Vegapunk', 433], ['Joy Boy', 628],
    ['Lulusia', 1060], ['Ope Ope', 504], ['Gear 5', 1044], ['Nerona', 1086],
    ['Pluton', 193], ['Uranus', 906], ['Yonko', 432], ['Haki', 597],
    ['Nika', 1018], ['Imu', 908]
  ];
  // LEXICON-END

  var CAP = 1190; // latest published chapter; keep in step with spoiler.js

  function cutoff() {
    // Mirrors spoiler.js effectiveCutoff('public') closely enough to gate with,
    // but works before spoiler.js has loaded. Same 597 first-visit default.
    try {
      if (typeof CodexSpoiler !== 'undefined' && CodexSpoiler.effectiveCutoff) {
        return CodexSpoiler.effectiveCutoff('public');
      }
      var raw = JSON.parse(localStorage.getItem('codex-spoiler-state') || 'null');
      if (raw) {
        if (raw.shield_mode === 'off') return CAP;
        if (typeof raw.cutoff_chapter === 'number' && raw.cutoff_chapter > 0) {
          var buf = raw.buffer_chapters || 0;
          return Math.max(0, Math.min(raw.cutoff_chapter - buf, CAP));
        }
      }
      var legacy = parseInt(localStorage.getItem('spoilerCutoff') || '0', 10);
      if (legacy > 0) return Math.min(legacy, CAP);
    } catch (e) { /* fall through to strict default */ }
    return 597;
  }

  function isCaughtUp() { return cutoff() >= CAP; }

  // Accepts 655, "Ch. 655", "Chapter 655", "Ch. 655-660". Episode forms are
  // NOT chapters — return null so the caller fails late.
  function parseChapter(v) {
    if (v == null) return null;
    if (typeof v === 'number') return v > 0 ? v : null;
    var s = String(v);
    if (/episode/i.test(s) && !/ch/i.test(s)) return null;
    var m = s.match(/(\d{1,4})/);
    return m ? parseInt(m[1], 10) : null;
  }

  function chapterOf(entry, keys) {
    // `gate_chapter` is written by scripts/derive_gate_chapters.py and is the
    // normalised answer: explicit field, else episode->chapter, else earliest
    // debut of a named user. It wins over the raw per-file fields, which use
    // several key names and formats.
    keys = keys || ['gate_chapter', 'debut_chapter', 'debut', 'chapter', 'reveal_chapter', 'since'];
    for (var i = 0; i < keys.length; i++) {
      var n = parseChapter(entry[keys[i]]);
      if (n !== null) return n;
    }
    return null;
  }

  // Any lexicon term in this text that the reader has not earned?
  function textLeaks(text, cut) {
    if (!text) return null;
    for (var i = 0; i < LEXICON.length; i++) {
      if (LEXICON[i][1] > cut && text.indexOf(LEXICON[i][0]) !== -1) return LEXICON[i][0];
    }
    return null;
  }

  function entryText(entry) {
    var parts = [];
    for (var k in entry) {
      if (!Object.prototype.hasOwnProperty.call(entry, k)) continue;
      var v = entry[k];
      if (typeof v === 'string') parts.push(v);
      else if (Array.isArray(v)) parts.push(v.filter(function (x) { return typeof x === 'string'; }).join(' '));
    }
    return parts.join(' ');
  }

  function isSafe(entry, keys) {
    if (isCaughtUp()) return true;
    var cut = cutoff();
    var ch = chapterOf(entry, keys);
    if (ch === null) return false;          // undatable -> fail late
    if (ch > cut) return false;             // debut gate
    return textLeaks(entryText(entry), cut) === null;   // lexicon gate
  }

  /* For curated lists that carry NO chapter field at all (combat-styles).
   * Requiring a chapter there would fail-late into an empty page, so apply
   * the lexicon gate only: drop entries whose text names an unearned concept,
   * keep the rest. Weaker than filterList — use filterList when dates exist. */
  function filterByText(items) {
    if (!Array.isArray(items)) return [];
    if (isCaughtUp()) return items;
    var cut = cutoff();
    return items.filter(function (e) { return textLeaks(entryText(e), cut) === null; });
  }

  /* RUNG LADDER — the answer to a page going blank.
   *
   * An entry may carry `rungs: [{ch, ...fields}]`, each a snapshot of the truth
   * as it stood at that chapter. The reader sees the HIGHEST rung they have
   * earned, with its fields laid over the base entry. So the Skypiea Poneglyph
   * can appear at Ch. 301 described as a stone the Shandia guarded, and only
   * become "a Road Poneglyph pointing to Laugh Tale" at 967 -- instead of being
   * hidden for 666 chapters because its only description used a late name.
   *
   * `maxCh` retires a provisional rung when a fuller one lands. Retire, never
   * delete: a reader below maxCh must still see the older, partial version.
   *
   * Returns null when no rung is earned -- the entry is simply not there yet.
   */
  function resolveRungs(entry, cut) {
    var rungs = entry && entry.rungs;
    if (!Array.isArray(rungs) || !rungs.length) return entry;
    var pick = null;
    for (var i = 0; i < rungs.length; i++) {
      var r = rungs[i];
      if (typeof r.ch !== 'number' || r.ch > cut) continue;
      if (typeof r.maxCh === 'number' && cut > r.maxCh) continue;
      if (!pick || r.ch >= pick.ch) pick = r;
    }
    if (!pick) return null;
    var out = {}, k;
    for (k in entry) {
      if (Object.prototype.hasOwnProperty.call(entry, k) && k !== 'rungs') out[k] = entry[k];
    }
    for (k in pick) {
      if (Object.prototype.hasOwnProperty.call(pick, k) && k !== 'ch' && k !== 'maxCh') {
        out[k] = pick[k];
      }
    }
    out.gate_chapter = pick.ch;
    return out;
  }

  function filterList(items, keys) {
    if (!Array.isArray(items)) return [];
    if (isCaughtUp()) {
      return items.map(function (e) { return resolveRungs(e, CAP) || e; });
    }
    var cut = cutoff(), out = [];
    for (var i = 0; i < items.length; i++) {
      var resolved = resolveRungs(items[i], cut);
      if (!resolved) continue;                    // no rung earned yet
      if (!isSafe(resolved, keys)) continue;      // debut + lexicon gates
      out.push(resolved);
    }
    return out;
  }

  /* Prose pages: drop any element whose own text names an unearned concept.
   * Walks leaf-ward so only the smallest containing block is removed. */
  function scrubDom(rootEl, selector) {
    if (isCaughtUp()) return 0;
    var cut = cutoff(), removed = 0;
    var nodes = (rootEl || document.body).querySelectorAll(selector || 'li,p,dd,dt,tr,article,section>div');
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (!el.isConnected) continue;
      if (textLeaks(el.textContent || '', cut)) { el.remove(); removed++; }
    }
    return removed;
  }

  /* Page intros ("<p class='blurb'>") are hand-written and routinely name
   * concepts the reader has not reached — the Poneglyphs blurb names Laugh
   * Tale, the Moments blurb names the Nika reveal. Replace a leaking intro
   * with a neutral line rather than deleting it, so the page still reads. */
  var SAFE_BLURB = 'Entries appear here as the story reveals them. Set your chapter to see more.';
  function gateBlurb(selector, fallback) {
    if (isCaughtUp()) return 0;
    var cut = cutoff(), n = 0;
    // Descriptive copy lives under several class names across the site. Only
    // elements that actually leak are rewritten, so a wide net is safe here.
    var els = document.querySelectorAll(selector ||
      '.blurb, .feature p, .card p, .card .summary, .summary, .tool-desc, .lede');
    for (var i = 0; i < els.length; i++) {
      if (textLeaks(els[i].textContent || '', cut)) {
        els[i].textContent = fallback || SAFE_BLURB;
        n++;
      }
    }
    return n;
  }

  /* Declarative gate for hand-written markup: put data-min-ch="395" on any
   * element (a hub card, a link, a paragraph) and it is removed for readers
   * below that chapter. Lets prose pages gate without bespoke JS. */
  function gateMinCh(rootEl) {
    if (isCaughtUp()) return 0;
    var cut = cutoff(), n = 0;
    var els = (rootEl || document).querySelectorAll('[data-min-ch]');
    for (var i = 0; i < els.length; i++) {
      var need = parseInt(els[i].getAttribute('data-min-ch'), 10);
      if (!isNaN(need) && need > cut) { els[i].remove(); n++; }
    }
    return n;
  }

  // Self-installing: any page that loads this file gets its intro gated with
  // no per-page wiring. Runs after DOM parse so the blurb exists.
  function autoInit() {
    try {
      gateMinCh();
      gateBlurb();
      // Prose pages opt in with <body data-lore-scrub="1">. Removes any block
      // that names an unearned concept — the blunt instrument for hand-written
      // copy that has no per-entry chapter to gate on.
      if (document.body && document.body.getAttribute('data-lore-scrub') === '1') {
        scrubDom(document.body, 'li,p,dd,dt,tr,figcaption,.card,.feature,.chip,.pill,'
          + '.quick-pick,.stat,.summary,.tag,.filter,button,option,[data-filter],[data-set],'
          + '.legend-item,.desc,.roger,.crew-name,.group-head');
      }
    } catch (e) { /* never break a page */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }

  root.LoreGate = {
    cutoff: cutoff, isCaughtUp: isCaughtUp, parseChapter: parseChapter,
    chapterOf: chapterOf, isSafe: isSafe, filterList: filterList,
    filterByText: filterByText,
    textLeaks: textLeaks, scrubDom: scrubDom, gateBlurb: gateBlurb,
    gateMinCh: gateMinCh,
    LEXICON: LEXICON
  };
})(window);
