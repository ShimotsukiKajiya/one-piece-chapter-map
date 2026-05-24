/* nav-burger.js — Shared global navigation for The Shimotsuki Codex.
 * Injects a hamburger button + slide-in drawer with the full IA.
 * Single source of truth: edit the GROUPS array below, all pages update.
 *
 * Usage on a page:
 *   <script src="nav-burger.js" defer></script>
 *
 * The drawer auto-marks the current page active by matching location.pathname.
 */
(function () {
  // ── Anti-clickjacking ────────────────────────────────────────────
  // GitHub Pages can't set X-Frame-Options/CSP frame-ancestors headers,
  // so we frame-bust here as defence-in-depth. If the page is loaded
  // inside an iframe, redirect the top window to ourselves; if same-origin
  // policy blocks the redirect (cross-origin parent), hide the body so
  // no UI can be transparently overlaid. Skipped on file:// for local dev.
  if (window.top !== window.self && location.protocol !== 'file:') {
    try { window.top.location = window.self.location.href; }
    catch (e) {
      document.documentElement.style.display = 'none';
      console.warn('Codex: refusing to render inside an iframe.');
      return;
    }
  }

  // Bulletproof dedup — strip any pre-existing nav from a stale cached
  // load before injecting fresh. Catches cases where two versions of
  // nav-burger.js race or get loaded together by an HMR / cache hiccup.
  ['nav-action-strip', 'nav-burger-btn', 'nav-drawer', 'nav-backdrop',
   'nav-burger-styles'].forEach(id => {
    const old = document.getElementById(id);
    if (old) old.remove();
  });

  const GROUPS = [
    {
      label: 'Home',
      icon: '🏠',
      isStandalone: true,
      items: [{ href: 'home.html', icon: '🏠', name: 'Home' }],
    },
    {
      label: 'Lore',
      icon: '📚',
      hubLink: 'lore.html',
      items: [
        { href: 'atlas.html',        icon: '🧭', name: 'Chapter Atlas' },
        { href: 'chapter-release-map.html', icon: '📅', name: 'Release Map' },
        { href: 'world-map.html',    icon: '🌐', name: 'World Map', soon: true },
        { href: 'sagas.html',        icon: '📖', name: 'Sagas' },
        { href: 'arcs.html',         icon: '🎭', name: 'Story Arcs' },
        { href: 'timeline.html',     icon: '📈', name: 'Timeline' },
        { href: 'moments.html',      icon: '🪙', name: 'Iconic Moments' },
        { href: 'reverie.html',      icon: '⏰', name: 'Reverie & World Events', minCh: 903 },
        { href: 'covers.html',       icon: '🏴‍☠️', name: 'Cover Compendium' },
        { href: 'heatmap.html',      icon: '🔥', name: 'Canon Density' },
        { href: 'episodes.html',     icon: '📺', name: 'Manga ↔ Anime' },
        { href: 'sbs.html',          icon: '📜', name: 'SBS Vault' },
        { href: 'sbs-topics.html',   icon: '🗂', name: 'SBS by Topic' },
        { href: 'music.html',        icon: '🎵', name: 'Music & Songs' },
        { href: 'poneglyphs.html',   icon: '🪨', name: 'Poneglyphs' },
        { href: 'void-century.html', icon: '🕯', name: 'Void Century' },
      ],
    },
    {
      label: 'Punk Records',
      icon: '🧠',
      hubLink: 'punk-records.html',
      defaultCollapsed: false,
      // People items are flattened to top level (no separate sub-heading)
      // — they're the most-used pages in the encyclopedia.
      // Order: individuals → identity → comparison → relationships → groups → peoples
      items: [
        { href: 'characters.html',   icon: '👤', name: 'Characters' },
        { href: 'bounties.html',     icon: '💰', name: 'Bounty Wall' },
        { href: 'voices.html',       icon: '🎙️', name: 'Voice Cast' },
        { href: 'compare.html',      icon: '⚖',  name: 'Compare Stats' },
        { href: 'heights.html',      icon: '📏', name: 'Compare Heights' },
        { href: 'families.html',     icon: '🌳', name: 'Family Trees' },
        { href: 'will-of-d.html',    icon: '🇩', name: 'Will of D.' },
        { href: 'crews.html',        icon: '⚓', name: 'Crews & Orgs' },
        { href: 'marines-wg.html',   icon: '🪽', name: 'Marines & World Govt' },
        { href: 'jolly-rogers.html', icon: '🏴‍☠️', name: 'Jolly Rogers' },
        { href: 'races.html',        icon: '🦊', name: 'Races & Tribes' },
      ],
      subGroups: [
        {
          label: 'Powers',
          icon: '💥',
          items: [
            { href: 'fruits.html',       icon: '🍎', name: 'Devil Fruits' },
            { href: 'awakenings.html',   icon: '💥', name: 'Awakenings' },
            { href: 'haki.html',         icon: '✦',  name: 'Haki Codex' },
            { href: 'combat-styles.html',icon: '🥋', name: 'Combat Styles' },
            // Sulong, Electro, and other race-bound powers live in
            // Combat Styles. Races & Tribes (the peoples themselves)
            // is now a top-level Punk Records item above.
          ],
        },
        {
          label: 'Setting',
          icon: '🏛',
          items: [
            { href: 'locations.html',    icon: '🗺',  name: 'Locations' },
            { href: 'ships.html',        icon: '⛵', name: 'Ships' },
            // Marines & World Govt moved to top-level next to Crews & Orgs
            // — it's a structural organisation like the Marines wiki page,
            // belongs alongside the other group/affiliation pages.
          ],
        },
        {
          label: 'Gear',
          icon: '⚔',
          items: [
            { href: 'weapons.html',      icon: '⚔',  name: 'Weapons & Meito' },
            { href: 'items.html',        icon: '🧪', name: 'Items' },
            { href: 'materials.html',    icon: '⚙',  name: 'Materials' },
            { href: 'tech.html',         icon: '🤖', name: 'Tech & Artifacts' },
            { href: 'ancient-weapons.html', icon: '🏛', name: 'Ancient Weapons' },
          ],
        },
      ],
    },
    {
      label: 'Theories',
      icon: '🔥',
      hubLink: 'theories.html',  // small '→' button on heading → Theory Forge
      items: [
        // Theory Forge accessed via heading hub-link, not duplicated as an item
        { href: 'workbench.html',    icon: '📌', name: 'Theory Workbench' },
        { href: 'prove.html',        icon: '🔍', name: 'Prove an Idea' },
        // conflicts.html hidden from public nav 2026-05-24 launch:
        // internal canon-engine view, currently 0 active conflicts.
        // Still reachable by direct URL if you need it.
        { href: 'corrections.html',  icon: '📥', name: 'Corrections Inbox' },
      ],
    },
    {
      label: 'Tools',
      icon: '🛠',
      hubLink: 'tools.html',
      defaultCollapsed: true,
      items: [
        { href: 'quiz.html',     icon: '🎯', name: 'Trivia Trial' },
        // curate.html removed from public nav 2026-05-23 launch:
        // it's the maintainer-only review queue, not a visitor surface.
        // Still reachable by direct URL if you really want.
      ],
    },
    {
      label: 'About',
      icon: 'ℹ',
      hubLink: 'about.html',
      defaultCollapsed: true,
      items: [
        { href: 'about.html', icon: 'ℹ',  name: 'About the Codex' },
        { href: 'news.html',  icon: '📰', name: "What's New", soon: true },
        { href: 'feed.xml',   icon: '📡', name: 'RSS Feed', external: true },
        { href: 'https://github.com/ShimotsukiKajiya/one-piece-chapter-map', icon: '🐙', name: 'GitHub', external: true },
      ],
    },
  ];

  // ─── Collapse state ───
  const COLLAPSE_KEY = 'codex-nav-collapsed';
  let collapsedSet;
  try {
    collapsedSet = new Set(JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '[]'));
  } catch (_) {
    collapsedSet = new Set();
  }
  function isCollapsed(group) {
    if (group.isStandalone) return false;
    if (collapsedSet.has(group.label)) return true;
    if (collapsedSet.has('!' + group.label)) return false;  // explicitly expanded override
    return !!group.defaultCollapsed;
  }
  function toggleCollapsed(group) {
    if (group.isStandalone) return;
    const explicitlyExpanded = collapsedSet.has('!' + group.label);
    const isColl = isCollapsed(group);
    if (isColl) {
      // Was collapsed → expand
      collapsedSet.delete(group.label);
      if (group.defaultCollapsed) collapsedSet.add('!' + group.label);
    } else {
      // Was expanded → collapse
      collapsedSet.delete('!' + group.label);
      if (!group.defaultCollapsed) collapsedSet.add(group.label);
    }
    try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify([...collapsedSet])); } catch (_) {}
  }

  // ─── Styles ───
  const css = `
    /* Reserve space at the top-right of every page header for the action
       strip (search · info · settings · burger), so it never overlaps. */
    header, .topbar { padding-right: 240px !important; padding-left: 24px !important; }
    @media (max-width: 600px) {
      header, .topbar { padding-right: 185px !important; }
    }
    @media (max-width: 480px) {
      header, .topbar { padding-right: 175px !important; }
      #nav-action-strip { gap: 5px !important; top: 10px !important; right: 10px !important; }
      #nav-action-strip .nav-action-btn { width: 36px !important; height: 36px !important; border-radius: 9px !important; font-size: 1rem !important; }
      #nav-action-strip .nav-action-btn svg { width: 17px !important; height: 17px !important; }
      #nav-burger-btn { width: 40px !important; height: 40px !important; border-radius: 10px !important; }
      .logo-sub { display: none !important; }
    }
    /* Hide the legacy floating buttons (settings gear, search button) that
       settings.js / search.js inject — we surface them in the action strip. */
    #codex-gear, #codex-search-btn { display: none !important; }

    /* Action strip — Search · Info · Burger, stacked at top-right */
    #nav-action-strip {
      position: fixed; top: 14px; right: 14px; z-index: 1000;
      display: flex; gap: 8px; align-items: center;
    }
    #nav-action-strip .nav-action-btn {
      width: 44px; height: 44px;
      background: rgba(26, 22, 16, 0.92);
      border: 1px solid #4a3820;
      border-radius: 11px;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.18s ease;
      backdrop-filter: blur(6px);
      padding: 0;
      color: #d4a44a;
      text-decoration: none;
      font-size: 1.15rem;
    }
    #nav-action-strip .nav-action-btn:hover {
      border-color: #d4a44a;
      color: #f5c95e;
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
    #nav-action-strip .nav-action-btn:focus-visible {
      outline: 2px solid #f5c95e;
      outline-offset: 3px;
      border-color: #d4a44a;
    }
    #nav-action-strip .nav-action-btn svg { width: 20px; height: 20px; }

    #nav-burger-btn {
      width: 48px; height: 48px;
      background: rgba(26, 22, 16, 0.92);
      border: 1px solid #4a3820;
      border-radius: 12px;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: all 0.2s ease;
      backdrop-filter: blur(6px);
      padding: 0;
    }
    #nav-burger-btn:hover {
      border-color: #d4a44a;
      transform: translateY(-1px);
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
    #nav-burger-btn:focus-visible {
      outline: 2px solid #f5c95e;
      outline-offset: 3px;
      border-color: #d4a44a;
    }
    /* ── BARS STYLE (default) — animated 3-line that morphs to X ── */
    #nav-burger-btn .bars-icon {
      display: flex; flex-direction: column; gap: 5px;
      align-items: center; justify-content: center;
    }
    #nav-burger-btn .bars-icon .bar {
      width: 22px; height: 2px;
      background: #d4a44a;
      border-radius: 2px;
      transition: transform .25s ease, opacity .2s ease;
    }
    #nav-burger-btn.open .bars-icon .bar:nth-child(1) { transform: translateY(7px) rotate(45deg); }
    #nav-burger-btn.open .bars-icon .bar:nth-child(2) { opacity: 0; }
    #nav-burger-btn.open .bars-icon .bar:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

    /* ── BURGER STYLE (opt-in) — literal SVG burger ── */
    #nav-burger-btn .burger-svg,
    #nav-burger-btn .meat-svg {
      width: 36px; height: 36px;
      transition: transform .3s cubic-bezier(.4,0,.2,1);
    }
    #nav-burger-btn.open .burger-svg,
    #nav-burger-btn.open .meat-svg { transform: rotate(360deg) scale(.92); }
    #nav-burger-btn .burger-svg .seed { fill: #f5deb3; }

    /* Toggle visibility based on data-burger-style on <html> */
    #nav-burger-btn .bars-icon  { display: flex; }
    #nav-burger-btn .burger-svg { display: none; }
    #nav-burger-btn .meat-svg   { display: none; }
    :root[data-burger-style="burger"] #nav-burger-btn .bars-icon  { display: none; }
    :root[data-burger-style="burger"] #nav-burger-btn .burger-svg { display: block; }
    :root[data-burger-style="meat"]   #nav-burger-btn .bars-icon  { display: none; }
    :root[data-burger-style="meat"]   #nav-burger-btn .meat-svg   { display: block; }

    /* Hide the action strip when the drawer is open — user has the
       drawer's own controls + backdrop click + Esc to close. */
    #nav-action-strip.drawer-open { opacity: 0; pointer-events: none; transition: opacity 0.2s; }

    #nav-backdrop {
      position: fixed; inset: 0;
      background: rgba(0, 0, 0, 0.55);
      z-index: 998;
      opacity: 0; pointer-events: none;
      transition: opacity 0.22s ease;
      backdrop-filter: blur(2px);
    }
    #nav-backdrop.open { opacity: 1; pointer-events: auto; }

    #nav-drawer {
      position: fixed; top: 0; right: 0; bottom: 0;
      width: 340px; max-width: 90vw;
      background: linear-gradient(180deg, #1a1610 0%, #0c0a14 100%);
      border-left: 1px solid #4a3820;
      z-index: 999;
      transform: translateX(100%);
      transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
      overflow-y: auto;
      box-shadow: -4px 0 20px rgba(0, 0, 0, 0.4);
      font-family: 'Segoe UI', system-ui, sans-serif;
    }
    #nav-drawer.open { transform: translateX(0); }

    #nav-drawer .nav-header {
      padding: 22px 22px 14px 22px;
      border-bottom: 1px solid #4a3820;
      background: linear-gradient(135deg, rgba(212, 164, 74, 0.08) 0%, transparent 100%);
    }
    #nav-drawer .nav-header h2 {
      font-size: 1.05rem; font-weight: 900;
      letter-spacing: 3px;
      background: linear-gradient(180deg, #f5c95e, #d4a44a);
      -webkit-background-clip: text; background-clip: text;
      -webkit-text-fill-color: transparent;
      text-transform: uppercase;
    }
    #nav-drawer .nav-header .sub {
      font-size: 0.65rem;
      color: #8a7548;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin-top: 4px;
      font-style: italic;
    }
    #nav-drawer .filter-row {
      padding: 12px 16px;
      border-bottom: 1px solid #2a2418;
    }
    #nav-drawer .filter-row input {
      width: 100%;
      background: #251f15;
      border: 1px solid #4a3820;
      color: #e8d8b0;
      padding: 8px 12px;
      border-radius: 6px;
      font-family: inherit;
      font-size: 0.85rem;
    }
    #nav-drawer .filter-row input:focus {
      outline: none; border-color: #d4a44a;
    }
    #nav-drawer .filter-row input:focus-visible {
      outline: 2px solid #f5c95e; outline-offset: 2px; border-color: #d4a44a;
    }
    /* Site-wide focus-visible — make keyboard navigation legible on every
       custom-styled link/button without overriding existing :hover styles.
       Native browser default ring gets clobbered by the page-specific styles
       on every page; this puts a consistent gold ring back. */
    a:focus-visible,
    button:focus-visible,
    select:focus-visible,
    [role="button"]:focus-visible {
      outline: 2px solid #f5c95e;
      outline-offset: 2px;
      border-radius: 4px;
    }
    /* Inputs already use border-color shifts on :focus; keep those but add
       a faint ring so the focus is unambiguous when an input has no border. */
    input:focus-visible,
    textarea:focus-visible {
      outline: 2px solid rgba(245,201,94,0.6);
      outline-offset: 1px;
    }

    #nav-drawer .group {
      padding: 14px 14px 6px;
    }
    #nav-drawer .group.group-standalone {
      padding: 8px 14px 4px;
      border-bottom: 1px solid #2a2418;
    }
    #nav-drawer .group.group-standalone + .group {
      padding-top: 14px;
    }
    #nav-drawer .group h3 {
      font-size: 0.7rem;
      font-weight: 800;
      color: #d4a44a;
      letter-spacing: 2.5px;
      text-transform: uppercase;
      padding: 8px 8px 10px;
      border-bottom: 1px solid #2a2418;
      margin-bottom: 6px;
      display: flex; align-items: center; gap: 8px;
      cursor: pointer;
      user-select: none;
      transition: color 0.15s;
    }
    #nav-drawer .group h3:hover { color: #f5c95e; }
    #nav-drawer .group h3 .gicon { font-size: 0.9rem; }
    #nav-drawer .group h3 .glabel { flex: 1; }
    /* Hub-link button on the left of the heading — small chevron-arrow that
       navigates to the group's landing page without toggling the dropdown. */
    #nav-drawer .group h3 .group-hub-link {
      display: inline-flex; align-items: center; justify-content: center;
      width: 22px; height: 22px;
      border: 1px solid #4a3820;
      border-radius: 5px;
      color: #d4a44a;
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 700;
      transition: all 0.12s;
      flex-shrink: 0;
      background: rgba(212,164,74,0.08);
    }
    #nav-drawer .group h3 .group-hub-link:hover {
      border-color: #d4a44a;
      background: #d4a44a;
      color: #1a1610;
      transform: translateX(-1px);
    }
    #nav-drawer .group h3 .gcount {
      background: #2a2418;
      color: #8a7548;
      font-size: 0.6rem;
      padding: 2px 6px;
      border-radius: 8px;
      letter-spacing: 1px;
      font-weight: 700;
    }
    #nav-drawer .group h3 .chevron {
      width: 9px; height: 9px;
      border-right: 2px solid currentColor;
      border-bottom: 2px solid currentColor;
      transform: rotate(45deg);
      transition: transform 0.22s ease;
      margin-left: 2px;
      margin-top: -3px;
    }
    #nav-drawer .group.collapsed h3 .chevron {
      transform: rotate(-45deg);
      margin-top: 0;
    }
    /* Collapsed state — hide all items inside the group */
    #nav-drawer .group.collapsed .item,
    #nav-drawer .group.collapsed .subgroup,
    #nav-drawer .subgroup.collapsed .item {
      display: none !important;
    }
    /* When user is typing in the filter, override collapse so matches show */
    #nav-drawer .group.filtering.collapsed .item,
    #nav-drawer .group.filtering.collapsed .subgroup,
    #nav-drawer .subgroup.filtering.collapsed .item {
      display: flex !important;
    }
    #nav-drawer .group.filtering .chevron { opacity: 0.3; }

    /* Nested sub-groups — indented look inside parent group */
    #nav-drawer .subgroup {
      padding: 4px 0 4px 0;
      margin-left: 8px;
      border-left: 1px solid #2a2418;
    }
    #nav-drawer .subgroup h4 {
      font-size: 0.66rem;
      font-weight: 700;
      color: #a08040;
      letter-spacing: 2px;
      text-transform: uppercase;
      padding: 6px 8px 6px 12px;
      margin: 2px 0 4px;
      display: flex; align-items: center; gap: 7px;
      cursor: pointer;
      user-select: none;
      transition: color 0.15s;
    }
    #nav-drawer .subgroup h4:hover { color: #d4a44a; }
    #nav-drawer .subgroup h4 .gicon { font-size: 0.85rem; }
    #nav-drawer .subgroup h4 .glabel { flex: 1; }
    #nav-drawer .subgroup h4 .gcount {
      background: #1a1410;
      color: #6a5028;
      font-size: 0.55rem;
      padding: 1px 5px;
      border-radius: 7px;
      letter-spacing: 1px;
      font-weight: 700;
    }
    #nav-drawer .subgroup h4 .chevron {
      width: 7px; height: 7px;
      border-right: 2px solid currentColor;
      border-bottom: 2px solid currentColor;
      transform: rotate(45deg);
      transition: transform 0.22s ease;
      margin-top: -3px;
    }
    #nav-drawer .subgroup.collapsed h4 .chevron {
      transform: rotate(-45deg);
      margin-top: 0;
    }
    #nav-drawer .subgroup .item {
      padding-left: 22px;  /* extra indent for sub-group items */
    }

    #nav-drawer .item {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 12px;
      color: #e8d8b0;
      text-decoration: none;
      font-size: 0.88rem;
      border-radius: 6px;
      transition: all 0.12s;
      position: relative;
    }
    #nav-drawer .item .ic {
      font-size: 1.05rem;
      flex-shrink: 0;
      width: 22px; text-align: center;
    }
    #nav-drawer .item .name { flex: 1; }
    #nav-drawer .item:hover {
      background: #251f15;
      color: #f5c95e;
      padding-left: 16px;
    }
    #nav-drawer .item.active {
      background: rgba(212, 164, 74, 0.12);
      color: #f5c95e;
      border-left: 3px solid #d4a44a;
      padding-left: 9px;
    }
    #nav-drawer .item.active::after {
      content: '●';
      color: #d4a44a;
      font-size: 0.6rem;
    }
    #nav-drawer .item.soon {
      opacity: 0.45;
      cursor: not-allowed;
    }
    #nav-drawer .item.soon:hover {
      background: transparent;
      color: #e8d8b0;
      padding-left: 12px;
    }
    #nav-drawer .item.soon .badge-soon {
      font-size: 0.55rem;
      background: #4a3820;
      color: #8a7548;
      padding: 2px 6px;
      border-radius: 8px;
      letter-spacing: 1px;
      text-transform: uppercase;
      font-weight: 700;
    }
    #nav-drawer .item.external::after {
      content: '↗';
      color: #6a9ec8;
      font-size: 0.85rem;
      margin-left: auto;
    }
    #nav-drawer .nav-footer {
      padding: 16px 22px 24px;
      color: #8a7548;
      font-size: 0.7rem;
      letter-spacing: 1px;
      text-align: center;
      border-top: 1px solid #2a2418;
      margin-top: 14px;
    }

    @media (max-width: 480px) {
      #nav-drawer { width: 280px; }
      #nav-burger-btn { width: 40px; height: 40px; top: 12px; left: 12px; }
    }
  `;

  // Inject styles
  const style = document.createElement('style');
  style.id = 'nav-burger-styles';
  style.textContent = css;
  document.head.appendChild(style);

  // Build the action strip (Search · Info · Burger)
  const strip = document.createElement('div');
  strip.id = 'nav-action-strip';

  // Search button — opens window.codexSearch.open() if available
  const searchBtn = document.createElement('button');
  searchBtn.className = 'nav-action-btn';
  searchBtn.id = 'nav-search-btn';
  searchBtn.type = 'button';
  searchBtn.title = 'Search the Codex (press / or Ctrl+K)';
  searchBtn.setAttribute('aria-label', 'Search the Codex');
  searchBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="10.5" cy="10.5" r="6.5"/><line x1="20" y1="20" x2="15.5" y2="15.5"/></svg>`;
  searchBtn.addEventListener('click', () => {
    if (window.codexSearch && window.codexSearch.open) {
      window.codexSearch.open();
    } else {
      // Fallback: navigate to characters search
      location.href = 'characters.html';
    }
  });

  // Info button — opens about.html
  const infoBtn = document.createElement('a');
  infoBtn.className = 'nav-action-btn';
  infoBtn.id = 'nav-info-btn';
  infoBtn.href = 'about.html';
  infoBtn.title = 'About the Shimotsuki Codex';
  infoBtn.setAttribute('aria-label', 'About');
  infoBtn.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><circle cx="12" cy="12" r="9.5" fill="none" stroke="currentColor" stroke-width="2.2"/><text x="12" y="17" text-anchor="middle" font-family="Georgia,serif" font-weight="900" font-size="13" font-style="italic" fill="currentColor">i</text></svg>`;

  // Settings button — opens window.codexSettings.open() (replaces the
  // legacy floating gear, which we hide via CSS above).
  const settingsBtn = document.createElement('button');
  settingsBtn.className = 'nav-action-btn';
  settingsBtn.id = 'nav-settings-btn';
  settingsBtn.type = 'button';
  settingsBtn.title = 'Codex Settings';
  settingsBtn.setAttribute('aria-label', 'Codex Settings');
  settingsBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>`;
  settingsBtn.addEventListener('click', () => {
    if (window.codexSettings && window.codexSettings.open) {
      window.codexSettings.open();
    }
  });

  // Burger menu button
  const btn = document.createElement('button');
  btn.id = 'nav-burger-btn';
  btn.setAttribute('aria-label', 'Open navigation');
  btn.innerHTML = `
    <span class="bars-icon">
      <span class="bar"></span>
      <span class="bar"></span>
      <span class="bar"></span>
    </span>
    <svg class="burger-svg" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M 6 28 Q 6 12, 32 12 Q 58 12, 58 28 L 58 32 L 6 32 Z" fill="#d68a3a" stroke="#a05a18" stroke-width="1.2"/>
      <path d="M 12 22 Q 25 14, 50 18" stroke="#f5deb3" stroke-width="1.5" fill="none" opacity="0.55" stroke-linecap="round"/>
      <ellipse class="seed" cx="20" cy="22" rx="2.2" ry="1.2" transform="rotate(-18 20 22)"/>
      <ellipse class="seed" cx="32" cy="18" rx="2.2" ry="1.2"/>
      <ellipse class="seed" cx="44" cy="22" rx="2.2" ry="1.2" transform="rotate(18 44 22)"/>
      <path d="M 4 32 L 60 32 L 56 38 L 8 38 Z" fill="#ffd75e" stroke="#c89a18" stroke-width="0.8"/>
      <path d="M 4 36 Q 10 33, 16 36 T 28 36 T 40 36 T 52 36 T 60 36 L 60 41 L 4 41 Z" fill="#7ac290" stroke="#4a8b5a" stroke-width="0.8"/>
      <rect x="6" y="40" width="52" height="8" rx="2" ry="2" fill="#5a3018" stroke="#2a1408" stroke-width="1"/>
      <circle cx="16" cy="44" r="1" fill="#3a1d0a" opacity="0.7"/>
      <circle cx="28" cy="46" r="1" fill="#3a1d0a" opacity="0.7"/>
      <circle cx="42" cy="44" r="1" fill="#3a1d0a" opacity="0.7"/>
      <circle cx="50" cy="46" r="1" fill="#3a1d0a" opacity="0.7"/>
      <path d="M 6 47 L 58 47 L 58 50 Q 58 56, 32 56 Q 6 56, 6 50 Z" fill="#b8682a" stroke="#7a4515" stroke-width="1.2"/>
    </svg>
    <svg class="meat-svg" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <!-- Bone ends — classic two-pronged Y/wishbone tips, drawn first -->
      <g fill="#f5ede0" stroke="#3a1f10" stroke-width="3" stroke-linejoin="round">
        <!-- Left: thin shaft narrowing into a forked two-lobe tip -->
        <path d="M 22 31
                 L 14 31
                 Q 14 24, 8 24
                 Q 2 24, 2 30
                 Q 2 33, 5 34
                 Q 2 35, 2 38
                 Q 2 44, 8 44
                 Q 14 44, 14 37
                 L 22 37 Z"/>
        <!-- Right: mirror -->
        <path d="M 42 31
                 L 50 31
                 Q 50 24, 56 24
                 Q 62 24, 62 30
                 Q 62 33, 59 34
                 Q 62 35, 62 38
                 Q 62 44, 56 44
                 Q 50 44, 50 37
                 L 42 37 Z"/>
      </g>
      <!-- Meat — organic warm-tan blob, slightly asymmetric for character -->
      <path d="M 14 30
               Q 12 16, 26 14
               Q 42 13, 48 22
               Q 53 30, 50 38
               Q 46 47, 36 49
               Q 22 50, 16 44
               Q 11 38, 14 30 Z"
            fill="#c07838" stroke="#3a1f10" stroke-width="3" stroke-linejoin="round"/>
      <!-- Skin texture dots (Korean-style cartoon meat detail) -->
      <g fill="#7a4018" opacity="0.7">
        <circle cx="22" cy="22" r="0.9"/>
        <circle cx="30" cy="20" r="0.8"/>
        <circle cx="36" cy="22" r="0.9"/>
        <circle cx="20" cy="32" r="0.8"/>
        <circle cx="40" cy="32" r="0.9"/>
        <circle cx="26" cy="38" r="0.8"/>
        <circle cx="34" cy="40" r="0.9"/>
        <circle cx="42" cy="42" r="0.8"/>
      </g>
      <!-- Subtle shadow on bottom-right for 3D depth -->
      <path d="M 42 26 Q 50 32, 48 42 Q 44 47, 38 47"
            stroke="#8a4a18" stroke-width="2.4" fill="none"
            stroke-linecap="round" opacity="0.45"/>
    </svg>`;

  // Build backdrop
  const backdrop = document.createElement('div');
  backdrop.id = 'nav-backdrop';

  // Build drawer
  const drawer = document.createElement('aside');
  drawer.id = 'nav-drawer';
  drawer.setAttribute('role', 'navigation');

  const currentPage = (location.pathname.split('/').pop() || 'home.html').toLowerCase();

  let html = `
    <div class="nav-header">
      <h2>The Shimotsuki Codex</h2>
      <div class="sub">Forging clarity from chaos</div>
    </div>
    <div class="filter-row">
      <input id="nav-filter" type="search" placeholder="Filter menu…" autocomplete="off" />
    </div>
  `;

  // L23 fix: read effective cutoff from CodexSpoiler if loaded, else direct
  // localStorage. Used to gate menu items whose page name is itself a
  // late-arc spoiler (e.g. "Reverie & World Events" is a Ch.903+ arc).
  function _effCutoff() {
    if (typeof CodexSpoiler !== 'undefined' && CodexSpoiler.effectiveCutoff) {
      return CodexSpoiler.effectiveCutoff('public');
    }
    try {
      const raw = JSON.parse(localStorage.getItem('codex-spoiler-state') || 'null');
      if (raw && typeof raw.cutoff_chapter === 'number' && raw.cutoff_chapter > 0) {
        return Math.min(raw.cutoff_chapter, 1181);
      }
      const legacy = parseInt(localStorage.getItem('spoilerCutoff') || '0', 10);
      if (legacy > 0) return Math.min(legacy, 1181);
    } catch (_) {}
    return 597;  // strict default
  }

  function renderItem(item) {
    // Per-item cutoff gate. Items with `minCh` attribute hidden when their
    // referenced arc/concept is past the user's effective cutoff.
    if (typeof item.minCh === 'number' && item.minCh > _effCutoff()) return '';

    const isActive = !item.soon && !item.external && item.href.toLowerCase() === currentPage;
    const cls = ['item'];
    if (isActive) cls.push('active');
    if (item.soon) cls.push('soon');
    if (item.external) cls.push('external');
    const target = item.external ? ' target="_blank" rel="noopener"' : '';
    const href = item.soon ? '#' : item.href;
    const onclick = item.soon ? ` onclick="event.preventDefault();return false"` : '';
    const badge = item.soon ? `<span class="badge-soon">soon</span>` : '';
    return `<a class="${cls.join(' ')}" href="${href}"${target}${onclick} data-name="${item.name.toLowerCase()}">
      <span class="ic">${item.icon}</span>
      <span class="name">${item.name}</span>
      ${badge}
    </a>`;
  }

  function totalItemCount(group) {
    if (group.subGroups) return group.subGroups.reduce((n, s) => n + s.items.length, 0);
    return (group.items || []).length;
  }

  for (const group of GROUPS) {
    const collapsed = isCollapsed(group);
    const hubBtn = group.hubLink
      ? `<a class="group-hub-link" href="${group.hubLink}" title="Open ${group.label} hub" aria-label="Open ${group.label} hub">→</a>`
      : '';
    const headerHtml = group.isStandalone
      ? ''
      : `<h3 data-group-label="${group.label}">
           ${hubBtn}
           <span class="gicon">${group.icon}</span>
           <span class="glabel">${group.label}</span>
           <span class="gcount">${totalItemCount(group)}</span>
           <span class="chevron"></span>
         </h3>`;
    const cls = ['group'];
    if (group.isStandalone) cls.push('group-standalone');
    if (collapsed) cls.push('collapsed');
    if (group.subGroups) cls.push('group-nested');
    html += `<div class="${cls.join(' ')}" data-group="${group.label.toLowerCase()}">
      ${headerHtml}`;
    if (group.subGroups) {
      // Render any top-level items FIRST (before sub-groups)
      for (const item of (group.items || [])) html += renderItem(item);
      // Then render each sub-group as its own collapsible block
      for (const sub of group.subGroups) {
        const subCollapsed = isCollapsed({ label: group.label + '/' + sub.label, defaultCollapsed: sub.defaultCollapsed });
        const subCls = ['subgroup'];
        if (subCollapsed) subCls.push('collapsed');
        html += `<div class="${subCls.join(' ')}" data-subgroup="${sub.label.toLowerCase()}">
          <h4 data-group-label="${group.label}/${sub.label}">
            <span class="gicon">${sub.icon}</span>
            <span class="glabel">${sub.label}</span>
            <span class="gcount">${sub.items.length}</span>
            <span class="chevron"></span>
          </h4>`;
        for (const item of sub.items) html += renderItem(item);
        html += `</div>`;
      }
    } else {
      for (const item of (group.items || [])) html += renderItem(item);
    }
    html += `</div>`;
  }

  html += `<div class="nav-footer">
    Built with calm and Claude · <a href="https://github.com/ShimotsukiKajiya/one-piece-chapter-map" target="_blank" rel="noopener" style="color:#6a9ec8;text-decoration:none">GitHub</a>
  </div>`;

  drawer.innerHTML = html;

  // Strip = Search · Info · Settings · Burger (left-to-right inside the strip)
  strip.appendChild(searchBtn);
  strip.appendChild(infoBtn);
  strip.appendChild(settingsBtn);
  strip.appendChild(btn);
  document.body.appendChild(strip);
  document.body.appendChild(backdrop);
  document.body.appendChild(drawer);

  // ─── Prev / Next page buttons ───────────────────────────────
  (function buildPageNav() {
    // Flat ordered page list (mirrors nav drawer order)
    const PAGE_ORDER = [
      'home.html',
      'atlas.html','chapter-release-map.html','world-map.html','sagas.html','arcs.html','timeline.html',
      'moments.html','reverie.html','covers.html','heatmap.html','episodes.html',
      'sbs.html','sbs-topics.html','music.html','poneglyphs.html','void-century.html',
      'characters.html','bounties.html','voices.html','compare.html','heights.html',
      'families.html','will-of-d.html','crews.html','marines-wg.html',
      'jolly-rogers.html','races.html',
      'fruits.html','awakenings.html','haki.html','combat-styles.html',
      'locations.html','ships.html',
      'weapons.html','items.html','materials.html','tech.html','ancient-weapons.html',
      'theories.html','workbench.html','prove.html','conflicts.html','corrections.html',
      'quiz.html','curate.html',
      'about.html','news.html',
    ];

    const cur = location.pathname.split('/').pop() || 'home.html';
    const idx = PAGE_ORDER.indexOf(cur);
    if (idx === -1) return; // page not in list — skip

    const prevPage = idx > 0 ? PAGE_ORDER[idx - 1] : null;
    const nextPage = idx < PAGE_ORDER.length - 1 ? PAGE_ORDER[idx + 1] : null;

    const label = h => h.replace(/\.html$/, '').replace(/-/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());

    const btnCss = `
      .codex-page-nav {
        position: fixed; bottom: 80px;
        z-index: 1100; display: flex; align-items: center;
        background: rgba(20,16,10,.75); border: 1px solid rgba(212,164,74,.3);
        color: var(--gold, #d4a44a); text-decoration: none;
        border-radius: 8px; padding: 10px 8px;
        font-size: 1.1rem; line-height: 1;
        backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
        transition: background .15s, border-color .15s, padding .2s;
        max-width: 40px; overflow: hidden; white-space: nowrap;
        cursor: pointer;
      }
      .codex-page-nav:hover {
        background: rgba(212,164,74,.15); border-color: var(--gold, #d4a44a);
        max-width: 200px; padding: 10px 12px;
      }
      .codex-page-nav.prev { left: 0; border-left: none; border-radius: 0 8px 8px 0; }
      .codex-page-nav.next { right: 0; border-right: none; border-radius: 8px 0 0 8px; text-align: right; flex-direction: row-reverse; }
      .codex-page-nav .pn-arrow { flex-shrink: 0; }
      .codex-page-nav .pn-label { font-size: .7rem; letter-spacing: .5px; margin: 0 6px; opacity: 0; transition: opacity .2s; text-transform: uppercase; overflow: hidden; }
      .codex-page-nav:hover .pn-label { opacity: 1; }
      html.no-page-nav .codex-page-nav { display: none !important; }
      @media (max-width: 480px) {
        .codex-page-nav { bottom: 70px; padding: 8px 6px; font-size: .95rem; }
      }
    `;
    const st = document.createElement('style');
    st.textContent = btnCss;
    document.head.appendChild(st);

    function makeBtn(href, arrow, lbl, cls) {
      const a = document.createElement('a');
      a.href = href;
      a.className = 'codex-page-nav ' + cls;
      a.title = lbl;
      a.setAttribute('aria-label', (cls === 'prev' ? 'Previous: ' : 'Next: ') + lbl);
      a.innerHTML = `<span class="pn-arrow">${arrow}</span><span class="pn-label">${lbl}</span>`;
      return a;
    }

    if (prevPage) document.body.appendChild(makeBtn(prevPage, '‹', label(prevPage), 'prev'));
    if (nextPage) document.body.appendChild(makeBtn(nextPage, '›', label(nextPage), 'next'));

    // ── Keyboard shortcuts: ← / → for prev/next ──
    // Skipped when typing in an input, when a modifier is held (browser shortcuts),
    // or when the drawer is open (drawer's own input has focus then).
    document.addEventListener('keydown', (e) => {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      const tgt = e.target;
      if (tgt && tgt.matches && tgt.matches('input, textarea, select, [contenteditable=""], [contenteditable="true"]')) return;
      if (drawer && drawer.classList.contains('open')) return;
      if (document.documentElement.classList.contains('no-page-nav')) return;
      if (e.key === 'ArrowLeft' && prevPage) { e.preventDefault(); location.href = prevPage; }
      else if (e.key === 'ArrowRight' && nextPage) { e.preventDefault(); location.href = nextPage; }
    });

    // ── Swipe gestures (mobile): left → next, right → prev ──
    // Skipped when the swipe starts inside a horizontally-scrollable element
    // (atlas grid, episodes table, families tree) so existing scroll wins.
    let tx = 0, ty = 0, tStart = null;
    document.addEventListener('touchstart', (e) => {
      if (e.touches.length !== 1) { tStart = null; return; }
      tx = e.touches[0].clientX; ty = e.touches[0].clientY; tStart = e.target;
    }, { passive: true });
    document.addEventListener('touchend', (e) => {
      if (!tStart) return;
      const t = e.changedTouches[0];
      const dx = t.clientX - tx, dy = t.clientY - ty;
      const start = tStart; tStart = null;
      if (Math.abs(dx) < 80 || Math.abs(dx) < Math.abs(dy) * 1.8) return;
      if (drawer && drawer.classList.contains('open')) return;
      if (document.documentElement.classList.contains('no-page-nav')) return;
      // Walk up the DOM — if any ancestor scrolls horizontally, let it own the gesture
      let el = start;
      while (el && el !== document.body) {
        const ox = getComputedStyle(el).overflowX;
        if ((ox === 'auto' || ox === 'scroll') && el.scrollWidth > el.clientWidth + 4) return;
        el = el.parentElement;
      }
      if (dx > 0 && prevPage) location.href = prevPage;
      else if (dx < 0 && nextPage) location.href = nextPage;
    }, { passive: true });
  })();

  // Open / close
  function open() {
    btn.classList.add('open');
    drawer.classList.add('open');
    backdrop.classList.add('open');
    strip.classList.add('drawer-open');  // hides the action strip while drawer's up
    document.body.style.overflow = 'hidden';
    setTimeout(() => {
      const f = document.getElementById('nav-filter');
      if (f) f.focus();
    }, 280);
  }
  function close() {
    btn.classList.remove('open');
    drawer.classList.remove('open');
    backdrop.classList.remove('open');
    strip.classList.remove('drawer-open');
    document.body.style.overflow = '';
  }
  btn.addEventListener('click', () => {
    if (drawer.classList.contains('open')) close();
    else open();
  });
  backdrop.addEventListener('click', close);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer.classList.contains('open')) close();
  });

  // Hub link buttons (small "→" on a heading) navigate to the hub page,
  // they MUST NOT bubble up and trigger the heading's collapse toggle.
  drawer.querySelectorAll('.group-hub-link').forEach(a => {
    a.addEventListener('click', (e) => e.stopPropagation());
  });

  // Click on a group OR sub-group heading toggles its collapsed state
  drawer.querySelectorAll('h3[data-group-label], h4[data-group-label]').forEach(h => {
    h.addEventListener('click', (e) => {
      // If the click was on the hub-link, let it through (already stopped above)
      if (e.target.closest('.group-hub-link')) return;
      e.stopPropagation();
      const label = h.dataset.groupLabel;
      // Sub-groups have labels like "World/People"
      if (label.includes('/')) {
        const [parentLabel, subLabel] = label.split('/');
        const parent = GROUPS.find(g => g.label === parentLabel);
        const sub = parent && parent.subGroups && parent.subGroups.find(s => s.label === subLabel);
        if (!sub) return;
        const subEl = h.closest('.subgroup');
        toggleCollapsed({ label, defaultCollapsed: sub.defaultCollapsed });
        subEl.classList.toggle('collapsed', isCollapsed({ label, defaultCollapsed: sub.defaultCollapsed }));
      } else {
        const group = GROUPS.find(g => g.label === label);
        if (!group) return;
        const groupEl = h.closest('.group');
        toggleCollapsed(group);
        groupEl.classList.toggle('collapsed', isCollapsed(group));
      }
    });
  });

  // Filter
  const filter = drawer.querySelector('#nav-filter');
  if (filter) {
    filter.addEventListener('input', (e) => {
      const q = e.target.value.trim().toLowerCase();
      drawer.querySelectorAll('.group').forEach(g => {
        let anyVisible = false;
        g.querySelectorAll('.item').forEach(it => {
          const match = !q || it.dataset.name.includes(q);
          it.style.display = match ? '' : 'none';
          if (match) anyVisible = true;
        });
        g.style.display = anyVisible ? '' : 'none';
        // Force-expand any group with matches while filtering
        // (so collapsed groups don't hide their hits behind the chevron).
        if (q) {
          g.classList.toggle('filtering', true);
        } else {
          g.classList.remove('filtering');
        }
      });
    });
  }
})();
