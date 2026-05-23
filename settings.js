/**
 * The Shimotsuki Codex — Global Settings System
 *
 * Settings are stored in localStorage under 'codex-settings' as JSON.
 * Each page that includes this script gets:
 *   • A floating gear button (top-right)
 *   • A modal with all the options
 *   • Settings applied on load (theme, avatars, animations)
 *
 * Add a tiny stub to any page:  <script src="settings.js"></script>
 */
(function () {
  'use strict';

  // ── DEFAULTS ─────────────────────────────────────────────────
  const DEFAULTS = {
    // Reader avatar: 'char-v01'..'char-v04' (owned chibi-character silhouettes),
    // 'flag-v01' (owned mystery jolly-roger), 'svg', 'none', 'pandaman'.
    // Oda avatar: 'wiki', 'mushi-v01'/'mushi-v02' (owned den-den-mushi),
    // 'flag-v02'/'flag-v03'/'flag-v04' (owned mystery jolly-roger), 'svg'.
    readerAvatar:   'char-v01',
    odaAvatar:      'wiki',
    theme:          'treasure',     // 'treasure' | 'marine' | crew theme key (luffy/zoro/...)
    animations:     true,           // sea kings, fish, doons, decorations
    compactCards:   false,          // tighter Q&A cards
    burgerStyle:    'bars',         // 'bars' | 'burger' | 'meat' — nav menu icon look
    atmosphericBg:  'on',           // 'on' | 'minimal' | 'off' — page-themed bg layer
    pageNav:        true,           // prev / next page arrow buttons
  };

  const KEY = 'codex-settings';

  // ── AVATAR PATH MAPPINGS ─────────────────────────────────────
  // Variant key → image src. 'svg' / 'none' stay handled by CSS rules below.
  const READER_AVATAR_SRC = {
    'pandaman':  'logo/reader-avatar.png',
    'char-v01':  'assets/silhouettes/generic-character-v01.jpg',
    'char-v02':  'assets/silhouettes/generic-character-v02.jpg',
    'char-v03':  'assets/silhouettes/generic-character-v03.jpg',
    'char-v04':  'assets/silhouettes/generic-character-v04.jpg',
    'flag-v01':  'assets/silhouettes/jolly-roger-mystery-v01.jpg',
  };
  const ODA_AVATAR_SRC = {
    'wiki':      'logo/oda-avatar.png',
    'mushi-v01': 'assets/silhouettes/den-den-mushi-v01.jpg',
    'mushi-v02': 'assets/silhouettes/den-den-mushi-v02.jpg',
    'flag-v02':  'assets/silhouettes/jolly-roger-mystery-v02.jpg',
    'flag-v03':  'assets/silhouettes/jolly-roger-mystery-v03.jpg',
    'flag-v04':  'assets/silhouettes/jolly-roger-mystery-v04.jpg',
  };
  // Public API — pages render avatars by querying these so settings get
  // applied on first render (no flicker) and live-update on change.
  window.CodexAvatars = {
    getReaderSrc() { return READER_AVATAR_SRC[settings.readerAvatar] || READER_AVATAR_SRC['char-v01']; },
    getOdaSrc()    { return ODA_AVATAR_SRC[settings.odaAvatar]       || ODA_AVATAR_SRC['wiki']; },
  };
  function updateAvatarSrcs() {
    const rSrc = READER_AVATAR_SRC[settings.readerAvatar];
    const oSrc = ODA_AVATAR_SRC[settings.odaAvatar];
    if (rSrc) document.querySelectorAll('.avatar-d > img').forEach(img => { if (img.src.split('/').pop() !== rSrc.split('/').pop()) img.src = rSrc; });
    if (oSrc) document.querySelectorAll('.avatar-o > img').forEach(img => { if (img.src.split('/').pop() !== oSrc.split('/').pop()) img.src = oSrc; });
  }

  // ── LOAD / SAVE ──────────────────────────────────────────────
  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      return Object.assign({}, DEFAULTS, raw ? JSON.parse(raw) : {});
    } catch (_) { return Object.assign({}, DEFAULTS); }
  }
  function save(s) {
    localStorage.setItem(KEY, JSON.stringify(s));
  }

  let settings = load();

  // ── APPLY ────────────────────────────────────────────────────
  function apply() {
    const root = document.documentElement;
    root.dataset.theme        = settings.theme;
    root.dataset.readerAvatar = settings.readerAvatar;
    root.dataset.odaAvatar    = settings.odaAvatar;
    root.dataset.burgerStyle  = settings.burgerStyle;
    root.dataset.atmosphericBg = settings.atmosphericBg;
    root.classList.toggle('no-animations', !settings.animations);
    root.classList.toggle('compact-cards',  settings.compactCards);
    root.classList.toggle('no-page-nav',    !settings.pageNav);
    updateAvatarSrcs();
  }

  // ── INJECT CSS for theme variants + opt-out classes ─────────
  function injectCSS() {
    if (document.getElementById('codex-settings-css')) return;
    const css = `
      /* Theme variants override the :root vars set in each page's stylesheet */
      :root[data-theme="marine"] {
        --bg: #06121e; --surface: #0e1f33; --surface2: #182b42;
        --border: #2a4566; --text: #d8e8f5; --muted: #5a7595;
        --gold: #6db8ff; --gold-bright: #a0d4ff; --ink-blue: #4dbbff;
      }

      /* ── Strawhat crew themes (per SBS Vol 109 official colours) ── */
      :root[data-theme="luffy"]   {  /* 赤 — Red */
        --bg: #140808; --surface: #1f1010; --surface2: #2c1a18;
        --border: #5a2820; --text: #f0d8c0; --muted: #8a6858;
        --gold: #e84030; --gold-bright: #ff6055; --ink-blue: #f5c95e;
      }
      :root[data-theme="zoro"]    {  /* 緑 — Green */
        --bg: #08120a; --surface: #101a14; --surface2: #1a2620;
        --border: #2a4830; --text: #d8e8d0; --muted: #688060;
        --gold: #2b8c3e; --gold-bright: #5ec968; --ink-blue: #d4a44a;
      }
      :root[data-theme="nami"]    {  /* 橙 — Orange */
        --bg: #140c08; --surface: #20140e; --surface2: #2c1e16;
        --border: #5a3818; --text: #f0e0c8; --muted: #8a7048;
        --gold: #ff8030; --gold-bright: #ffa055; --ink-blue: #4dbbff;
      }
      :root[data-theme="usopp"]   {  /* 黄 — Yellow */
        --bg: #100e08; --surface: #1c1810; --surface2: #28221a;
        --border: #5a4818; --text: #f0e8d0; --muted: #8a7848;
        --gold: #f0c040; --gold-bright: #ffd866; --ink-blue: #6a3f1f;
      }
      :root[data-theme="sanji"]   {  /* 青 — Blue */
        --bg: #060a14; --surface: #0e141e; --surface2: #18202c;
        --border: #2a3a5a; --text: #d8e0f0; --muted: #607080;
        --gold: #1f4fa8; --gold-bright: #4d7fd0; --ink-blue: #f5c95e;
      }
      :root[data-theme="chopper"] {  /* 桃色 — Peach Pink */
        --bg: #140810; --surface: #20121a; --surface2: #2c1c24;
        --border: #5a2a40; --text: #f0d8e0; --muted: #806070;
        --gold: #ff80a8; --gold-bright: #ffa0c0; --ink-blue: #b8682a;
      }
      :root[data-theme="robin"]   {  /* 紫 — Purple */
        --bg: #0a0814; --surface: #14101e; --surface2: #1e1a2c;
        --border: #3a2858; --text: #e0d8f0; --muted: #706080;
        --gold: #7b3fa0; --gold-bright: #a368c8; --ink-blue: #d4a44a;
      }
      :root[data-theme="franky"]  {  /* 水色 — Sky Cyan */
        --bg: #061218; --surface: #0e1c24; --surface2: #182830;
        --border: #285060; --text: #d8e8f0; --muted: #608090;
        --gold: #1ec6f5; --gold-bright: #5ed8ff; --ink-blue: #ff6b1a;
      }
      :root[data-theme="brook"]   {  /* 紺 — Navy / Indigo */
        --bg: #06081a; --surface: #0e1024; --surface2: #181a30;
        --border: #2a3060; --text: #d8d8f0; --muted: #6868a0;
        --gold: #1f2a6a; --gold-bright: #5060a0; --ink-blue: #b388ff;
      }
      :root[data-theme="jinbe"]   {  /* 黄土色 — Ochre */
        --bg: #100c06; --surface: #1c1610; --surface2: #28201a;
        --border: #5a4218; --text: #f0e0c0; --muted: #8a7048;
        --gold: #c89030; --gold-bright: #e8b860; --ink-blue: #1f3060;
      }

      /* Avatar variants — when 'svg' selected, hide the img and force the
         SVG fallback visible (overriding the default 'img + svg' hide rule). */
      :root[data-reader-avatar="svg"]   .avatar-d > img { display: none !important; }
      :root[data-reader-avatar="svg"]   .avatar-d > svg { display: block !important; }
      :root[data-oda-avatar="svg"]      .avatar-o > img { display: none !important; }
      :root[data-oda-avatar="svg"]      .avatar-o > svg { display: block !important; }
      /* When 'none' selected, hide both — leave just the gradient circle */
      :root[data-reader-avatar="none"]  .avatar-d > img,
      :root[data-reader-avatar="none"]  .avatar-d > svg { display: none !important; }

      /* Animation opt-out — disable all decorative motion + decorations */
      :root.no-animations .deco,
      :root.no-animations .deco-fish,
      :root.no-animations .deco-serpent,
      :root.no-animations .deco-waves,
      :root.no-animations .doon { display: none !important; animation: none !important; }
      :root.no-animations *,
      :root.no-animations *::before,
      :root.no-animations *::after { animation: none !important; transition: none !important; }

      /* MOBILE PERF — auto-disable heavy decorations on small screens.
         Sea kings, fish school, sound effects, side covers all skipped. */
      @media (max-width: 760px) {
        .deco, .deco-fish, .deco-serpent, .deco-waves,
        .doon, .qa-side-cover { display: none !important; }
      }
      /* Respect OS-level reduced-motion preference */
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }
      }

      /* Compact cards */
      :root.compact-cards .qa { padding: 18px 16px 14px !important; margin-bottom: 24px !important; gap: 8px !important; }
      :root.compact-cards .avatar { width: 90px !important; height: 90px !important; }
      :root.compact-cards .avatar svg { width: 70px !important; height: 70px !important; }
      :root.compact-cards .bubble { padding: 12px 16px !important; font-size: 0.9rem !important; }
      :root.compact-cards .qa-side-cover { width: 130px !important; height: 200px !important; left: -160px !important; }

      /* ── GEAR BUTTON ────────────────────────────────────────── */
      #codex-gear {
        position: fixed; top: 16px; right: 16px;
        width: 40px; height: 40px;
        border-radius: 50%;
        background: rgba(0,0,0,0.5);
        border: 1px solid var(--border, #4a3820);
        color: var(--gold, #d4a44a);
        font-size: 1.2rem;
        display: flex; align-items: center; justify-content: center;
        cursor: pointer;
        z-index: 9999;
        opacity: 0.6;
        transition: all 0.18s ease;
      }
      #codex-gear:hover { opacity: 1; transform: rotate(45deg); border-color: var(--gold, #d4a44a); }

      /* ── MODAL ──────────────────────────────────────────────── */
      #codex-overlay {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.7);
        display: none; align-items: center; justify-content: center;
        z-index: 10000;
      }
      #codex-overlay.on { display: flex; }
      #codex-modal {
        background: var(--surface, #1a1610);
        border: 1px solid var(--gold, #d4a44a);
        border-radius: 14px;
        padding: 28px;
        max-width: 520px; width: 92%;
        max-height: 85vh; overflow-y: auto;
        color: var(--text, #e8d8b0);
        font-family: 'Segoe UI', system-ui, sans-serif;
        box-shadow: 0 12px 32px rgba(0,0,0,0.7);
      }
      #codex-modal h2 {
        font-size: 1.4rem; font-weight: 800;
        background: linear-gradient(180deg, var(--gold-bright, #f5c95e), var(--gold, #d4a44a));
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 4px;
      }
      #codex-modal .modal-sub {
        font-size: 0.75rem; color: var(--muted, #8a7548);
        letter-spacing: 1px; text-transform: uppercase;
        margin-bottom: 22px;
      }
      .codex-section {
        margin-bottom: 22px;
        padding-bottom: 18px;
        border-bottom: 1px dashed rgba(212,164,74,0.2);
      }
      .codex-section:last-child { border-bottom: none; }
      .codex-section h3 {
        font-size: 0.7rem; font-weight: 700;
        color: var(--gold, #d4a44a);
        letter-spacing: 2px; text-transform: uppercase;
        margin-bottom: 10px;
      }
      .codex-options {
        display: flex; flex-wrap: wrap; gap: 8px;
      }
      .codex-opt {
        padding: 8px 14px;
        background: rgba(0,0,0,0.3);
        border: 1px solid var(--border, #4a3820);
        border-radius: 8px;
        color: var(--text, #e8d8b0);
        font-size: 0.85rem; font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
      }
      .codex-opt:hover { border-color: var(--gold, #d4a44a); color: var(--gold-bright, #f5c95e); }
      .codex-crew-row {
        margin-top: 12px; display: flex; align-items: center; gap: 10px;
        flex-wrap: wrap;
      }
      .codex-crew-label {
        font-size: 0.78rem; color: var(--muted, #8a7548);
        font-style: italic;
      }
      .codex-crew-select {
        flex: 1; min-width: 180px;
        background: rgba(0,0,0,0.4);
        border: 1px solid var(--border, #4a3820);
        color: var(--text, #e8d8b0);
        padding: 8px 12px; border-radius: 8px;
        font-family: inherit; font-size: 0.85rem;
        cursor: pointer;
      }
      .codex-crew-select:focus { outline: none; border-color: var(--gold, #d4a44a); }
      .codex-opt.active {
        background: var(--gold, #d4a44a); color: #1a1410;
        border-color: var(--gold, #d4a44a);
      }
      .codex-toggle {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px;
        background: rgba(0,0,0,0.25);
        border: 1px solid var(--border, #4a3820);
        border-radius: 8px;
        cursor: pointer;
        margin-bottom: 8px;
      }
      .codex-toggle:hover { border-color: var(--gold, #d4a44a); }
      .codex-toggle .label { font-size: 0.85rem; }
      .codex-toggle .switch {
        width: 38px; height: 20px; border-radius: 10px;
        background: #444; position: relative; transition: background 0.2s;
      }
      .codex-toggle .switch::after {
        content: ''; position: absolute;
        width: 16px; height: 16px; border-radius: 50%;
        background: #aaa; top: 2px; left: 2px;
        transition: all 0.2s;
      }
      .codex-toggle.on .switch { background: var(--gold, #d4a44a); }
      .codex-toggle.on .switch::after { background: #fff; left: 20px; }
      .codex-actions {
        display: flex; gap: 10px; margin-top: 18px;
      }
      .codex-btn {
        flex: 1;
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 0.85rem; font-weight: 700;
        cursor: pointer; border: 1px solid var(--border, #4a3820);
        background: transparent; color: var(--muted, #8a7548);
        transition: all 0.15s;
      }
      .codex-btn:hover { color: var(--text, #e8d8b0); border-color: var(--gold, #d4a44a); }
      .codex-btn.primary {
        background: var(--gold, #d4a44a); color: #1a1410;
        border-color: var(--gold, #d4a44a);
      }
      .codex-btn.primary:hover { background: var(--gold-bright, #f5c95e); }
    `;
    const style = document.createElement('style');
    style.id = 'codex-settings-css';
    style.textContent = css;
    document.head.appendChild(style);
  }

  // ── BUILD UI ────────────────────────────────────────────────
  function buildUI() {
    if (document.getElementById('codex-overlay')) return;

    // The floating ⚙ gear is no longer injected — nav-burger.js's
    // action strip surfaces Settings as one of its icons. Keeping the
    // modal markup + open/close exposed via window.codexSettings.

    const overlay = document.createElement('div');
    overlay.id = 'codex-overlay';
    overlay.onclick = e => { if (e.target === overlay) closeModal(); };
    overlay.innerHTML = `
      <div id="codex-modal">
        <h2>Codex Settings</h2>
        <div class="modal-sub">Personalise the experience · Saved to your browser</div>

        <div class="codex-section" id="codex-spoiler-section" style="border-left:3px solid var(--gold,#d4a44a);padding-left:14px">
          <h3>🛡 Spoiler Guard <span style="font-size:0.7rem;color:var(--muted,#8a7548);font-weight:400;letter-spacing:1px;text-transform:uppercase;margin-left:8px">on by default for new visitors</span></h3>
          <div class="codex-crew-label" style="margin-bottom:14px;line-height:1.65">
            The Codex hides every character, fact, relationship, theory, and event that debuts past your reading point — across the entire site. Tell us how far you've gotten and the codex unlocks for you.
          </div>
          <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px">
            <label style="font-size:0.88rem;color:var(--text,#e8d8b0)">
              Ch.&nbsp;<input type="number" id="codex-spoiler-input" min="0" max="9999"
                placeholder="e.g. 1000"
                style="width:78px;background:var(--surface2,#251f15);border:1px solid var(--border,#4a3820);
                       color:var(--text,#e8d8b0);padding:5px 8px;border-radius:6px;
                       font-size:0.9rem;font-family:inherit">
            </label>
            <label style="font-size:0.88rem;color:var(--text,#e8d8b0)">
              Ep.&nbsp;<input type="number" id="codex-spoiler-ep-input" min="0" max="9999"
                placeholder="e.g. 1100"
                style="width:78px;background:var(--surface2,#251f15);border:1px solid var(--border,#4a3820);
                       color:var(--text,#e8d8b0);padding:5px 8px;border-radius:6px;
                       font-size:0.9rem;font-family:inherit">
            </label>
            <button class="codex-btn primary" id="codex-spoiler-apply" style="flex:0 0 auto;padding:7px 16px">Apply</button>
            <button class="codex-btn" id="codex-spoiler-caughtup" style="flex:0 0 auto;padding:7px 14px">I'm caught up</button>
            <button class="codex-btn" id="codex-spoiler-clear" style="flex:0 0 auto;padding:7px 14px">Clear</button>
          </div>

          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:10px">
            <label style="font-size:0.84rem;color:var(--text,#e8d8b0)">
              Shield strictness:
              <select id="codex-spoiler-mode" style="background:var(--surface2,#251f15);border:1px solid var(--border,#4a3820);color:var(--text,#e8d8b0);padding:5px 8px;border-radius:6px;font-size:0.86rem;font-family:inherit;margin-left:6px">
                <option value="auto">Auto — relax on detail pages</option>
                <option value="strict">Strict — protect everywhere</option>
                <option value="off">Off — no protection</option>
              </select>
            </label>
            <label style="font-size:0.84rem;color:var(--text,#e8d8b0)">
              Buffer:
              <input type="number" id="codex-spoiler-buffer" min="0" max="50" placeholder="5"
                style="width:56px;background:var(--surface2,#251f15);border:1px solid var(--border,#4a3820);color:var(--text,#e8d8b0);padding:5px 8px;border-radius:6px;font-size:0.86rem;font-family:inherit;margin-left:6px">
              <span style="color:var(--muted,#8a7548);font-size:0.78rem;margin-left:4px">chapters under cutoff (default 5)</span>
            </label>
          </div>

          <div id="codex-spoiler-status" style="margin-top:6px;font-size:0.78rem;color:var(--ink-blue,#6a9ec8);min-height:1.2em"></div>
        </div>

        <div class="codex-section">
          <h3>Theme</h3>
          <div class="codex-options" data-key="theme">
            <button class="codex-opt" data-val="treasure">📜 Treasure Map</button>
            <button class="codex-opt" data-val="marine">⚓ Marine Navy</button>
          </div>
          <div class="codex-crew-row">
            <label class="codex-crew-label">…or pick a Strawhat crew theme:</label>
            <select id="codex-crew-select" class="codex-crew-select">
              <option value="">— Standard theme —</option>
              <option value="luffy">🎩 Luffy · Red</option>
              <option value="zoro">🗡 Zoro · Green</option>
              <option value="nami">🍊 Nami · Orange</option>
              <option value="usopp">🎯 Usopp · Yellow</option>
              <option value="sanji">🚬 Sanji · Blue</option>
              <option value="chopper">🦌 Chopper · Pink</option>
              <option value="robin">📚 Robin · Purple</option>
              <option value="franky">🤖 Franky · Sky Cyan</option>
              <option value="brook">🎻 Brook · Indigo</option>
              <option value="jinbe">🐠 Jinbe · Ochre</option>
            </select>
          </div>
        </div>

        <div class="codex-section">
          <h3>Reader Avatar</h3>
          <div class="codex-options" data-key="readerAvatar">
            <button class="codex-opt" data-val="char-v01">👤 Reader I</button>
            <button class="codex-opt" data-val="char-v02">👤 Reader II</button>
            <button class="codex-opt" data-val="char-v03">👤 Reader III</button>
            <button class="codex-opt" data-val="char-v04">👤 Reader IV</button>
            <button class="codex-opt" data-val="flag-v01">🏴 Mystery Flag</button>
            <button class="codex-opt" data-val="none">🚫 Hide</button>
            <button class="codex-opt" data-val="pandaman">🐼 Pandaman</button>
          </div>
        </div>

        <div class="codex-section">
          <h3>Oda Avatar</h3>
          <div class="codex-options" data-key="odaAvatar">
            <button class="codex-opt" data-val="wiki">🐟 Wiki Avatar</button>
            <button class="codex-opt" data-val="mushi-v01">🐌 Den-den Mushi I</button>
            <button class="codex-opt" data-val="mushi-v02">🐌 Den-den Mushi II</button>
            <button class="codex-opt" data-val="flag-v02">🏴 Mystery Flag I</button>
            <button class="codex-opt" data-val="flag-v03">🏴 Mystery Flag II</button>
            <button class="codex-opt" data-val="flag-v04">🏴 Mystery Flag III</button>
          </div>
        </div>

        <div class="codex-section">
          <h3>Menu Icon</h3>
          <div class="codex-options" data-key="burgerStyle">
            <button class="codex-opt" data-val="bars">≡ Bars (animated)</button>
            <button class="codex-opt" data-val="burger">🍔 Literal Burger</button>
            <button class="codex-opt" data-val="meat">🍖 Meat on Bone</button>
          </div>
        </div>

        <div class="codex-section">
          <h3>Atmospheric Background</h3>
          <div class="codex-options" data-key="atmosphericBg">
            <button class="codex-opt" data-val="on">⚡ Full</button>
            <button class="codex-opt" data-val="minimal">🌙 Minimal</button>
            <button class="codex-opt" data-val="off">🚫 Off</button>
          </div>
          <div class="codex-crew-label">Page-themed scenes — Haki lightning on Punk Records, treasure on Bounty Wall, etc.</div>
        </div>

        <div class="codex-section">
          <h3>Display</h3>
          <div class="codex-toggle" data-key="animations">
            <span class="label">Background animations (sea kings, fish, sound effects)</span>
            <span class="switch"></span>
          </div>
          <div class="codex-toggle" data-key="compactCards">
            <span class="label">Compact cards (less padding, smaller avatars)</span>
            <span class="switch"></span>
          </div>
          <div class="codex-toggle" data-key="pageNav">
            <span class="label">Prev / Next page buttons (← left and right → edges)</span>
            <span class="switch"></span>
          </div>
        </div>

        <div class="codex-section">
          <h3>Navigation</h3>
          <div class="codex-crew-label" style="line-height:1.7">
            Several ways to flip between pages:<br>
            • <strong>Side arrows</strong> at the bottom-left and bottom-right corners<br>
            • <strong>Keyboard</strong> — <code style="background:rgba(0,0,0,0.3);padding:1px 5px;border-radius:3px">←</code> and <code style="background:rgba(0,0,0,0.3);padding:1px 5px;border-radius:3px">→</code> arrow keys<br>
            • <strong>Mobile swipe</strong> — swipe left for next, right for previous<br>
            • <strong>Burger menu</strong> (top-right) for the full index
          </div>
        </div>

        <div class="codex-section">
          <h3>Privacy</h3>
          <div class="codex-crew-label" style="margin-bottom:10px">Reset the fan disclaimer so it shows again on your next visit.</div>
          <button class="codex-btn" id="codex-reset-disclaimer">Reset disclaimer modal</button>
        </div>

        <div class="codex-actions">
          <button class="codex-btn" onclick="window.codexSettings.reset()">Reset to defaults</button>
          <button class="codex-btn primary" onclick="window.codexSettings.close()">Done</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    // Wire up option groups
    overlay.querySelectorAll('.codex-options').forEach(group => {
      const key = group.dataset.key;
      group.querySelectorAll('.codex-opt').forEach(btn => {
        btn.onclick = () => {
          settings[key] = btn.dataset.val;
          save(settings); apply(); refreshUI();
        };
      });
    });
    // Wire up toggles
    overlay.querySelectorAll('.codex-toggle').forEach(t => {
      t.onclick = () => {
        const key = t.dataset.key;
        settings[key] = !settings[key];
        save(settings); apply(); refreshUI();
      };
    });
    // Spoiler Guard wiring (dual-write: legacy keys + new CodexSpoiler state)
    const spoilerInput     = document.getElementById('codex-spoiler-input');
    const spoilerEpInput   = document.getElementById('codex-spoiler-ep-input');
    const spoilerApply     = document.getElementById('codex-spoiler-apply');
    const spoilerCaughtUp  = document.getElementById('codex-spoiler-caughtup');
    const spoilerClear     = document.getElementById('codex-spoiler-clear');
    const spoilerStatus    = document.getElementById('codex-spoiler-status');
    const spoilerMode      = document.getElementById('codex-spoiler-mode');
    const spoilerBuffer    = document.getElementById('codex-spoiler-buffer');

    // Pre-fill from CodexSpoiler state if present, else from legacy keys
    (function _prefillSpoilerControls() {
      let snap = null;
      if (window.CodexSpoiler && typeof window.CodexSpoiler.snapshot === 'function') {
        snap = window.CodexSpoiler.snapshot();
      }
      const ch = snap ? snap.cutoff_chapter : parseInt(localStorage.getItem('spoilerCutoff') || '0', 10);
      const ep = snap ? snap.cutoff_episode : parseInt(localStorage.getItem('spoilerCutoffEp') || '0', 10);
      if (spoilerInput   && ch > 0) spoilerInput.value   = ch;
      if (spoilerEpInput && ep > 0) spoilerEpInput.value = ep;
      if (spoilerMode    && snap)   spoilerMode.value    = snap.shield_mode || 'auto';
      if (spoilerBuffer  && snap)   spoilerBuffer.value  = (snap.buffer_chapters != null ? snap.buffer_chapters : 5);
    })();

    function applySpoilerCutoff(chVal, epVal) {
      const ch = parseInt(chVal, 10);
      const ep = parseInt(epVal, 10);
      const chOk = !isNaN(ch) && ch > 0;
      const epOk = !isNaN(ep) && ep > 0;

      // Legacy keys (read-compat for any consumer not yet migrated)
      if (chOk) localStorage.setItem('spoilerCutoff',   String(ch));
      else      localStorage.removeItem('spoilerCutoff');
      if (epOk) localStorage.setItem('spoilerCutoffEp', String(ep));
      else      localStorage.removeItem('spoilerCutoffEp');

      // New CodexSpoiler state (canonical going forward)
      if (window.CodexSpoiler) {
        window.CodexSpoiler.setCutoff(chOk ? ch : 0, epOk ? ep : 0);
      }

      if (spoilerInput)   spoilerInput.value   = chOk ? ch : '';
      if (spoilerEpInput) spoilerEpInput.value = epOk ? ep : '';

      const parts = [];
      if (chOk) parts.push(`Ch. ${ch}`);
      if (epOk) parts.push(`Ep. ${ep}`);
      if (spoilerStatus) {
        spoilerStatus.textContent = parts.length
          ? `Active — hiding content after ${parts.join(' / ')}.`
          : 'No cutoff set — defaulting to strict mode (pre-timeskip safe pool).';
      }
      if (typeof window.setSpoilerCutoff === 'function') window.setSpoilerCutoff();
    }

    if (spoilerApply) {
      spoilerApply.addEventListener('click', () => {
        applySpoilerCutoff(
          spoilerInput   ? spoilerInput.value.trim()   : '',
          spoilerEpInput ? spoilerEpInput.value.trim() : ''
        );
      });
    }
    if (spoilerCaughtUp) {
      spoilerCaughtUp.addEventListener('click', () => {
        if (!window.CodexSpoiler) return;
        window.CodexSpoiler.setCaughtUp();
        const latest = window.CodexSpoiler.LATEST_PUBLISHED_CHAPTER;
        applySpoilerCutoff(String(latest), '');
      });
    }
    if (spoilerClear) {
      spoilerClear.addEventListener('click', () => applySpoilerCutoff('', ''));
    }
    if (spoilerMode) {
      spoilerMode.addEventListener('change', () => {
        if (window.CodexSpoiler) window.CodexSpoiler.setShieldMode(spoilerMode.value);
        if (spoilerStatus) {
          spoilerStatus.textContent = `Shield mode: ${spoilerMode.value}`;
        }
      });
    }
    if (spoilerBuffer) {
      spoilerBuffer.addEventListener('change', () => {
        if (window.CodexSpoiler) window.CodexSpoiler.setBuffer(spoilerBuffer.value);
      });
      spoilerBuffer.addEventListener('blur', () => {
        if (window.CodexSpoiler) window.CodexSpoiler.setBuffer(spoilerBuffer.value);
      });
    }
    const onEnter = e => {
      if (e.key === 'Enter') spoilerApply && spoilerApply.click();
    };
    if (spoilerInput)   spoilerInput.addEventListener('keydown',   onEnter);
    if (spoilerEpInput) spoilerEpInput.addEventListener('keydown', onEnter);

    // Reset disclaimer button
    const resetDisclaimer = document.getElementById('codex-reset-disclaimer');
    if (resetDisclaimer) {
      resetDisclaimer.addEventListener('click', () => {
        try { localStorage.removeItem('codex-legal-v1'); } catch (_) {}
        resetDisclaimer.textContent = 'Done — reload to see it';
        resetDisclaimer.disabled = true;
      });
    }

    // Wire up the crew theme dropdown
    const crewSelect = document.getElementById('codex-crew-select');
    if (crewSelect) {
      crewSelect.addEventListener('change', () => {
        const v = crewSelect.value;
        if (v) {
          settings.theme = v;
        } else {
          // Empty = revert to default treasure theme
          settings.theme = 'treasure';
        }
        save(settings); apply(); refreshUI();
      });
    }
  }

  function refreshUI() {
    const CREW_THEMES = ['luffy','zoro','nami','usopp','sanji','chopper','robin','franky','brook','jinbe'];
    document.querySelectorAll('.codex-options').forEach(group => {
      const key = group.dataset.key;
      group.querySelectorAll('.codex-opt').forEach(btn => {
        // For theme buttons, only highlight if current theme matches AND isn't a crew theme
        if (key === 'theme') {
          const isCrew = CREW_THEMES.includes(settings.theme);
          btn.classList.toggle('active', !isCrew && btn.dataset.val === settings[key]);
        } else {
          btn.classList.toggle('active', btn.dataset.val === settings[key]);
        }
      });
    });
    // Sync crew dropdown
    const crewSelect = document.getElementById('codex-crew-select');
    if (crewSelect) {
      crewSelect.value = CREW_THEMES.includes(settings.theme) ? settings.theme : '';
    }
    document.querySelectorAll('.codex-toggle').forEach(t => {
      const key = t.dataset.key;
      t.classList.toggle('on', !!settings[key]);
    });
  }

  function openModal()  {
    buildUI();
    refreshUI();
    // Sync spoiler inputs to current values. Prefer CodexSpoiler state
    // (canonical going forward); fall back to legacy localStorage keys.
    const inp     = document.getElementById('codex-spoiler-input');
    const inpEp   = document.getElementById('codex-spoiler-ep-input');
    const st      = document.getElementById('codex-spoiler-status');
    const inpMode = document.getElementById('codex-spoiler-mode');
    const inpBuf  = document.getElementById('codex-spoiler-buffer');

    let curCh = 0, curEp = 0, curMode = 'auto', curBuf = 5;
    if (window.CodexSpoiler && typeof window.CodexSpoiler.snapshot === 'function') {
      const snap = window.CodexSpoiler.snapshot();
      curCh   = snap.cutoff_chapter   || 0;
      curEp   = snap.cutoff_episode   || 0;
      curMode = snap.shield_mode      || 'auto';
      curBuf  = (snap.buffer_chapters != null) ? snap.buffer_chapters : 5;
    } else {
      curCh = parseInt(localStorage.getItem('spoilerCutoff')   || '0', 10);
      curEp = parseInt(localStorage.getItem('spoilerCutoffEp') || '0', 10);
    }

    if (inp)     inp.value     = curCh > 0 ? curCh : '';
    if (inpEp)   inpEp.value   = curEp > 0 ? curEp : '';
    if (inpMode) inpMode.value = curMode;
    if (inpBuf)  inpBuf.value  = curBuf;
    if (st) {
      const parts = [];
      if (curCh > 0) parts.push(`Ch. ${curCh}`);
      if (curEp > 0) parts.push(`Ep. ${curEp}`);
      st.textContent = parts.length
        ? `Active — hiding content after ${parts.join(' / ')}.`
        : 'No cutoff set — defaulting to strict mode (pre-timeskip safe pool).';
    }
    document.getElementById('codex-overlay').classList.add('on');
  }
  function closeModal() { document.getElementById('codex-overlay').classList.remove('on'); }
  function reset() {
    settings = Object.assign({}, DEFAULTS);
    save(settings); apply(); refreshUI();
  }

  // ── INIT ────────────────────────────────────────────────────
  // Apply theme/etc immediately so there's no flash
  injectCSS();
  apply();

  // Defer UI build until DOM ready (so the gear button has a body to attach to)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', buildUI);
  } else {
    buildUI();
  }

  // Expose for inline button handlers
  window.codexSettings = { open: openModal, close: closeModal, reset: reset };
})();
