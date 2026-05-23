/**
 * The Shimotsuki Codex — Universal Search
 *
 * Press / or Ctrl/Cmd-K on any page to open a search modal that hits:
 *   • SBS Q&As (volume + Q + A text)
 *   • Theories (title + description)
 *   • Cover stories (name + summary)
 *   • Characters (name)
 *   • Chapters (number)
 *
 * Loads data lazily from the JSON files via fetch (works on hosted/served
 * pages). Falls back gracefully if a data file isn't reachable from a
 * particular page (e.g. covers.html on its own).
 *
 * Add a tiny stub to any page: <script src="search.js"></script>
 */
(function () {
  'use strict';

  let dataReady = false;
  let sbs = [];
  let theories = [];
  let coverStories = [];
  // characters: array of { name, debut } where debut is the first chapter number (0 = unknown).
  let characters = [];
  let chapters = [];

  function getSpoilerCutoff()   { return parseInt(localStorage.getItem('spoilerCutoff')   || '0', 10); }
  function getSpoilerCutoffEp() { return parseInt(localStorage.getItem('spoilerCutoffEp') || '0', 10); }

  function parseDebut(firstAppearance) {
    if (!firstAppearance) return 0;
    const m = String(firstAppearance).match(/Chapter\s+(\d+)/i);
    return m ? parseInt(m[1]) : (String(firstAppearance).match(/\d+/) ? parseInt(String(firstAppearance).match(/\d+/)[0]) : 0);
  }
  function parseDebutEp(firstAppearance) {
    if (!firstAppearance) return 0;
    const m = String(firstAppearance).match(/Episode\s+(\d+)/i);
    return m ? parseInt(m[1]) : 0;
  }

  // ── DATA LOADERS ───────────────────────────────────────────
  async function loadAll() {
    if (dataReady) return;
    // Read from baked <script id="..."> blocks if present (preferred — same-page),
    // otherwise fetch from JSON files
    const tryBaked = (id) => {
      const el = document.getElementById(id);
      if (!el) return null;
      const txt = el.textContent.trim();
      if (txt.length < 5) return null;
      try { return JSON.parse(txt); } catch (_) { return null; }
    };

    const fetchJson = async (path) => {
      try {
        const r = await fetch(path);
        if (!r.ok) return null;
        return await r.json();
      } catch (_) { return null; }
    };

    sbs          = tryBaked('sbs-data')           || await fetchJson('sbs_archive.json')   || [];
    theories     = tryBaked('theories-data')      || await fetchJson('theories_import.json') || [];
    coverStories = tryBaked('cover-stories-data') || await fetchJson('cover_stories.json') || [];

    // Build character set — try punk-records-data first (character.html),
    // then appearances-data CSV (atlas/index pages), then fetch punk_records.json.
    const pr = tryBaked('punk-records-data');
    if (pr && Array.isArray(pr) && pr.length > 10) {
      for (const rec of pr) {
        if (rec.name) characters.push({
          name: rec.name,
          debut:   parseDebut(rec.first_appearance),
          debutEp: parseDebutEp(rec.first_appearance),
        });
      }
    }

    const apps = document.getElementById('appearances-data');
    if (apps && apps.textContent.length > 100) {
      // CSV format: chapter,name,type — first appearance per character = lowest chapter seen
      const debutMap = {};
      const lines = apps.textContent.trim().split(/\r?\n/).slice(1);
      for (const line of lines) {
        const parts = line.split(',');
        if (parts.length >= 2) {
          const ch = parseInt(parts[0]);
          const name = parts[1].replace(/^"|"$/g, '').trim();
          if (name && ch) {
            if (!debutMap[name] || ch < debutMap[name]) debutMap[name] = ch;
          }
          if (ch && !chapters.includes(ch)) chapters.push(ch);
        }
      }
      chapters.sort((a, b) => a - b);
      if (characters.length === 0) {
        for (const [name, debut] of Object.entries(debutMap)) {
          characters.push({ name, debut });
        }
      }
    }

    // Last resort: fetch punk_records.json directly
    if (characters.length === 0) {
      const prJson = await fetchJson('punk_records.json');
      if (prJson) {
        for (const [name, rec] of Object.entries(prJson)) {
          characters.push({
            name,
            debut:   parseDebut(rec.first_appearance),
            debutEp: parseDebutEp(rec.first_appearance),
          });
        }
      }
    }
    dataReady = true;
  }

  // ── SEARCH ─────────────────────────────────────────────────
  function search(q) {
    if (!q || q.length < 2) return [];
    const lc = q.toLowerCase();
    const isWordBoundary = (text, term) => {
      const re = new RegExp(`\\b${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
      return re.test(text);
    };
    const results = [];

    // Chapters: exact number match
    if (/^\d{1,4}$/.test(q.trim())) {
      const ch = parseInt(q.trim());
      if (ch >= 1 && ch <= 1200) {
        results.push({
          kind: 'chapter',
          icon: '🗺️',
          title: `Chapter ${ch}`,
          subtitle: 'Open Chapter Atlas',
          url:   `index.html?ch=${ch}`,
        });
      }
    }

    // Characters — filtered by spoiler cutoff (chapter and/or episode)
    const cutoff   = getSpoilerCutoff();
    const cutoffEp = getSpoilerCutoffEp();
    let charHits = 0;
    for (const { name, debut, debutEp } of characters) {
      if (charHits >= 5) break;
      if (cutoff   > 0 && debut   > 0 && debut   > cutoff)   continue;
      if (cutoffEp > 0 && debutEp > 0 && debutEp > cutoffEp) continue;
      if (name.toLowerCase().includes(lc) || isWordBoundary(name, q)) {
        results.push({
          kind: 'character',
          icon: '👤',
          title: name,
          subtitle: 'Character Profile · Punk Records',
          url: `character.html?name=${encodeURIComponent(name)}`,
        });
        charHits++;
      }
    }

    // L10 fix: helper to extract earliest chapter from a theory's chapter
    // field (which is a string like "1085, 1181" or "1113-1181" or "1085").
    // Theories cite future events; the earliest chapter referenced is the
    // earliest spoiler. If no chapter parseable → assume LATEST (only
    // visible to caught-up readers). Fail-closed.
    function _theoryMinCh(t) {
      const s = String(t.chapter || '');
      if (!s) return 1181;
      const nums = s.match(/\d+/g);
      if (!nums || !nums.length) return 1181;
      return Math.min.apply(null, nums.map(n => parseInt(n, 10)));
    }
    // SBS volume → approximate last chapter (each manga vol covers ~10 chs).
    // Used as the spoiler boundary for SBS Q&As (volume N is published with
    // the manga vol N which contains chapters up to ~N*10).
    function _sbsVolMaxCh(vol) {
      vol = parseInt(vol, 10) || 0;
      return Math.min(vol * 10 + 5, 1181);  // +5 buffer for Wano-era multi-Q&A volumes
    }
    // Cover stories: their chapter_range gives the chapter window. Earliest
    // chapter is the minimum spoiler; latest is when the cover ENDS (but
    // showing the END is itself a spoiler about how long the side story
    // ran). Use earliest chapter as the gate — if you've reached the
    // start, you're likely fine seeing the cover existed.
    function _coverMinCh(cs) {
      if (Array.isArray(cs.chapters) && cs.chapters.length) return Math.min.apply(null, cs.chapters);
      return 1181;
    }

    // Cover stories — gated by earliest chapter
    for (const cs of coverStories) {
      if ((cs.name && cs.name.toLowerCase().includes(lc))
          || (cs.summary && cs.summary.toLowerCase().includes(lc))) {
        if (_coverMinCh(cs) > cutoff && cutoff > 0) continue;
        results.push({
          kind: 'cover',
          icon: '🏴‍☠️',
          title: cs.name,
          subtitle: `Cover Compendium · ${cs.chapter_range || ''}`,
          url: `covers.html#${encodeURIComponent(cs.slug || cs.name)}`,
        });
      }
    }

    // Theories — gated by earliest cited chapter
    let thHits = 0;
    for (const t of theories) {
      if (thHits >= 6) break;
      const text = `${t.title} ${t.description || ''}`.toLowerCase();
      if (text.includes(lc)) {
        if (_theoryMinCh(t) > cutoff && cutoff > 0) continue;
        const num = (typeof t.num === 'number') ? String(t.num).padStart(4, '0') : null;
        results.push({
          kind: 'theory',
          icon: '🔥',
          title: t.title,
          subtitle: `Theory Forge · ${t.status}${num ? ' · #' + num : ''}`,
          url: num ? `theories.html#theory-${num}` : 'theories.html',
        });
        thHits++;
      }
    }

    // SBS Q&As — gated by their volume's approximate manga chapter window
    let sbsHits = 0;
    for (const qa of sbs) {
      if (sbsHits >= 10) break;
      const text = `${qa.question} ${qa.answer}`.toLowerCase();
      if (text.includes(lc)) {
        if (_sbsVolMaxCh(qa.volume) > cutoff && cutoff > 0) continue;
        const id = qa.id_num ? String(qa.id_num).padStart(4, '0') : '';
        results.push({
          kind: 'sbs',
          icon: '📜',
          title: (qa.question || '').slice(0, 80) + ((qa.question || '').length > 80 ? '…' : ''),
          subtitle: `SBS Vault · Vol ${qa.volume}${qa.name ? ' · ' + qa.name : ''}${id ? ' · #' + id : ''}`,
          url: id ? `sbs.html#${id}` : 'sbs.html',
        });
        sbsHits++;
      }
    }

    return results;
  }

  // ── UI ─────────────────────────────────────────────────────
  function injectCSS() {
    if (document.getElementById('codex-search-css')) return;
    const css = `
      #codex-search-overlay {
        position: fixed; inset: 0; z-index: 10001;
        background: rgba(0,0,0,0.78);
        display: none; align-items: flex-start; justify-content: center;
        padding-top: 12vh;
      }
      #codex-search-overlay.on { display: flex; }
      #codex-search-modal {
        background: var(--surface, #1a1610);
        border: 1px solid var(--gold, #d4a44a);
        border-radius: 12px;
        width: 92%; max-width: 660px;
        max-height: 75vh; overflow: hidden;
        display: flex; flex-direction: column;
        box-shadow: 0 20px 60px rgba(0,0,0,0.8);
      }
      #codex-search-input {
        width: 100%;
        background: transparent;
        border: none;
        border-bottom: 1px solid var(--border, #4a3820);
        color: var(--text, #e8d8b0);
        padding: 18px 22px;
        font-size: 1.05rem;
        outline: none;
        font-family: inherit;
      }
      #codex-search-results {
        overflow-y: auto;
        padding: 6px 0;
      }
      .codex-search-hit {
        display: flex; gap: 14px; align-items: center;
        padding: 10px 22px;
        cursor: pointer;
        border-left: 3px solid transparent;
        text-decoration: none;
        color: var(--text, #e8d8b0);
        transition: background 0.12s, border-color 0.12s;
      }
      .codex-search-hit:hover, .codex-search-hit.active {
        background: rgba(212,164,74,0.1);
        border-left-color: var(--gold, #d4a44a);
      }
      .codex-search-icon { font-size: 1.4rem; flex-shrink: 0; width: 24px; text-align: center; }
      .codex-search-text { flex: 1; min-width: 0; }
      .codex-search-title {
        font-weight: 600; font-size: 0.95rem;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      .codex-search-subtitle {
        font-size: 0.72rem; color: var(--muted, #8a7548);
        margin-top: 2px;
        text-transform: uppercase; letter-spacing: 1px;
      }
      .codex-search-empty {
        padding: 30px 22px; text-align: center;
        color: var(--muted, #8a7548);
        font-size: 0.85rem;
      }
      .codex-search-hint {
        padding: 10px 22px; border-top: 1px solid var(--border, #4a3820);
        font-size: 0.7rem; color: var(--muted, #8a7548);
        background: rgba(0,0,0,0.25);
        display: flex; gap: 14px; flex-wrap: wrap;
      }
      .codex-search-hint kbd {
        background: rgba(212,164,74,0.15);
        border: 1px solid rgba(212,164,74,0.3);
        border-radius: 4px;
        padding: 1px 6px;
        font-size: 0.7rem;
        color: var(--gold, #d4a44a);
      }
      /* Search trigger button — sits next to the gear */
      #codex-search-btn {
        position: fixed; top: 16px; right: 64px;
        width: 40px; height: 40px;
        border-radius: 50%;
        background: rgba(0,0,0,0.5);
        border: 1px solid var(--border, #4a3820);
        color: var(--gold, #d4a44a);
        font-size: 1.1rem;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer; opacity: 0.6;
        transition: all 0.18s ease;
        z-index: 9998;
      }
      #codex-search-btn:hover { opacity: 1; border-color: var(--gold, #d4a44a); transform: scale(1.06); }
      @media (max-width: 760px) {
        #codex-search-btn { right: 60px; }
      }

      /* Reserve space in the page header so floating gear + search don't
         overlap the rightmost nav link. The two buttons together occupy
         ~104px (40+8+40+16 padding); 116px gives them a clean gutter. */
      header { padding-right: 116px !important; }
      @media (max-width: 760px) { header { padding-right: 110px !important; } }
      @media (max-width: 500px) {
        /* On very small screens, drop the gutter to avoid wrapping the
           logo onto a new line when the nav is already wrapped below. */
        header { padding-right: 56px !important; }
        #codex-search-btn, #codex-gear { top: 10px; }
        #codex-search-btn { right: 50px; width: 34px; height: 34px; font-size: 0.95rem; }
        #codex-gear      { right: 12px; width: 34px; height: 34px; font-size: 0.95rem; }
      }
    `;
    const s = document.createElement('style');
    s.id = 'codex-search-css'; s.textContent = css;
    document.head.appendChild(s);
  }

  function buildUI() {
    if (document.getElementById('codex-search-overlay')) return;

    // The floating 🔍 button is no longer injected — nav-burger.js's
    // action strip surfaces Search as one of its icons. Keeping the
    // overlay + open/close exposed via window.codexSearch.

    const overlay = document.createElement('div');
    overlay.id = 'codex-search-overlay';
    overlay.onclick = e => { if (e.target === overlay) close(); };
    overlay.innerHTML = `
      <div id="codex-search-modal">
        <input id="codex-search-input" type="text" placeholder="Search Codex — characters, SBS, theories, chapters, cover stories…" autocomplete="off">
        <div id="codex-search-results"></div>
        <div class="codex-search-hint">
          <span><kbd>↑</kbd> <kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>esc</kbd> close</span>
          <span style="margin-left:auto;opacity:0.7">Powered by The Shimotsuki Codex</span>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const input   = document.getElementById('codex-search-input');
    const results = document.getElementById('codex-search-results');
    let activeIdx = 0;
    let currentResults = [];

    const render = (q) => {
      currentResults = search(q);
      activeIdx = 0;
      if (!q.trim()) {
        results.innerHTML = `<div class="codex-search-empty">Start typing to search · 1,659 SBS · 94 theories · 21 cover stories · 1,546 characters · 1,181 chapters</div>`;
        return;
      }
      if (!currentResults.length) {
        results.innerHTML = `<div class="codex-search-empty">No matches for "${q}"</div>`;
        return;
      }
      results.innerHTML = currentResults.map((r, i) => `
        <a class="codex-search-hit ${i === 0 ? 'active' : ''}" href="${r.url}" data-idx="${i}">
          <span class="codex-search-icon">${r.icon}</span>
          <div class="codex-search-text">
            <div class="codex-search-title">${escHtml(r.title)}</div>
            <div class="codex-search-subtitle">${escHtml(r.subtitle)}</div>
          </div>
        </a>
      `).join('');
    };

    let debounce;
    input.addEventListener('input', e => {
      clearTimeout(debounce);
      debounce = setTimeout(() => render(e.target.value), 80);
    });

    input.addEventListener('keydown', e => {
      const hits = results.querySelectorAll('.codex-search-hit');
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, hits.length - 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, 0);
      } else if (e.key === 'Enter') {
        if (hits[activeIdx]) hits[activeIdx].click();
      } else if (e.key === 'Escape') {
        close();
      } else {
        return;
      }
      hits.forEach((h, i) => h.classList.toggle('active', i === activeIdx));
      hits[activeIdx]?.scrollIntoView({ block: 'nearest' });
    });

    overlay._render = render;
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  async function open() {
    buildUI();
    await loadAll();
    const overlay = document.getElementById('codex-search-overlay');
    overlay.classList.add('on');
    const input = document.getElementById('codex-search-input');
    input.focus(); input.select();
    if (!input.value) overlay._render('');
  }
  function close() {
    document.getElementById('codex-search-overlay')?.classList.remove('on');
  }

  // Global keyboard shortcut: / or Ctrl/Cmd-K
  document.addEventListener('keydown', e => {
    // Skip when typing in any input/textarea — except / when overlay is open
    const activeTag = (document.activeElement || {}).tagName;
    const inField = activeTag === 'INPUT' || activeTag === 'TEXTAREA';

    if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) {
      e.preventDefault(); open(); return;
    }
    if (e.key === '/' && !inField) {
      e.preventDefault(); open(); return;
    }
  });

  // Init
  injectCSS();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }

  window.codexSearch = { open, close };
})();
