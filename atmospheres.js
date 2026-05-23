/* atmospheres.js — injects the atmospheric SVG behind page content based
 * on the body class (atm-haki, atm-treasure, etc.). Honours the user's
 * setting (Codex Settings → Atmospheric backgrounds: on / minimal / off).
 *
 * Usage on a page:
 *   <body class="atm-haki">
 *   <link rel="stylesheet" href="atmospheres.css">
 *   <script src="atmospheres.js" defer></script>
 *
 * That's it.
 */
(function () {
  const body = document.body;
  if (!body) return;

  // Pick the requested atmosphere from body class
  const klass = (body.className || '').split(/\s+/).find(c => c.startsWith('atm-'));
  if (!klass) return;
  const kind = klass.slice(4);  // 'haki', 'treasure', etc.

  // Respect setting — if user selected 'off', skip injection entirely
  let setting = 'on';
  try {
    const raw = localStorage.getItem('codex-settings');
    if (raw) {
      const s = JSON.parse(raw);
      if (s.atmosphericBg) setting = s.atmosphericBg;
    }
  } catch (_) {}
  if (setting === 'off') {
    document.documentElement.dataset.atmosphericBg = 'off';
    return;
  }
  document.documentElement.dataset.atmosphericBg = setting;

  // Don't inject twice
  if (document.getElementById('op-atmosphere')) return;

  const wrap = document.createElement('div');
  wrap.id = 'op-atmosphere';

  if (kind === 'haki') {
    wrap.innerHTML = svgHaki();
  } else if (kind === 'treasure') {
    wrap.innerHTML = svgTreasure();
  }

  // Insert as the first child of <body> so it sits beneath everything
  body.insertBefore(wrap, body.firstChild);

  // ─── SVG generators ───
  function svgHaki() {
    // Thick, branched lightning bolts — Conqueror's-coating style from the
    // Luffy vs Kaidou rooftop fight + Gear 5 + Egghead Saturn moments.
    // Each bolt = a main jagged spine with 1-3 forked branches.
    // Drawn as TWO paths: black outline (thicker) + coloured core (thinner).
    const COLOURS = ['gold','crimson','gold','crimson','indigo','gold','crimson','crimson','indigo','gold'];
    const bolts = [];

    function jagged(x, y, segments, biasY = 1) {
      // Returns [path-string, end-x, end-y, branch-points[]]
      let path = `M ${x.toFixed(0)} ${y.toFixed(0)}`;
      const branches = [];
      for (let s = 0; s < segments; s++) {
        const dx = -110 + Math.random() * 220;
        const dy = (60 + Math.random() * 110) * biasY;
        x += dx;
        y += dy;
        path += ` L ${x.toFixed(0)} ${y.toFixed(0)}`;
        // Maybe spawn a branch point on this segment (40% chance, not on first or last)
        if (s > 0 && s < segments - 1 && Math.random() < 0.5) {
          branches.push([x, y]);
        }
      }
      return [path, x, y, branches];
    }

    for (let i = 0; i < 8; i++) {
      const startX = 80 + Math.random() * 1760;
      const startY = -40 + Math.random() * 220;
      const segments = 6 + Math.floor(Math.random() * 4);
      const [mainPath, ex, ey, branchPts] = jagged(startX, startY, segments);

      // 1-2 branch forks per bolt
      const branchCount = Math.min(branchPts.length, 1 + Math.floor(Math.random() * 2));
      const forkPaths = [];
      for (let b = 0; b < branchCount; b++) {
        const [bx, by] = branchPts[b];
        const bSegs = 2 + Math.floor(Math.random() * 3);
        const [bp] = jagged(bx, by, bSegs, 0.85);
        forkPaths.push(bp);
      }

      const dur = (5 + Math.random() * 7).toFixed(1);
      const delay = (Math.random() * 8).toFixed(1);
      const coreSw = (3 + Math.random() * 2.5).toFixed(1);  // thicker than before
      const outlineSw = (parseFloat(coreSw) + 3).toFixed(1);  // black outline 3px wider

      // Main bolt: outline first, then coloured core ON TOP
      bolts.push(
        `<g class="bolt-group" style="--dur:${dur}s;--delay:${delay}s">
           <path class="bolt-outline" d="${mainPath}" stroke-width="${outlineSw}"/>
           <path class="bolt ${COLOURS[i]}" d="${mainPath}" stroke-width="${coreSw}"/>
           ${forkPaths.map(fp => `
             <path class="bolt-outline" d="${fp}" stroke-width="${(parseFloat(coreSw)*0.7+3).toFixed(1)}"/>
             <path class="bolt ${COLOURS[i]}" d="${fp}" stroke-width="${(parseFloat(coreSw)*0.7).toFixed(1)}"/>
           `).join('')}
         </g>`
      );
    }

    // Conqueror's aura — large faint radial circles that pulse slowly
    const auras = `
      <circle class="conqueror-aura" cx="320" cy="240" r="220" fill="url(#cg1)" />
      <circle class="conqueror-aura" cx="1500" cy="780" r="280" fill="url(#cg2)" style="animation-delay:-4s" />
    `;

    return `<svg viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="cg1" cx="50%" cy="50%" r="50%">
          <stop offset="0%"  stop-color="#f5c95e" stop-opacity="0.32"/>
          <stop offset="55%" stop-color="#e04030" stop-opacity="0.14"/>
          <stop offset="100%" stop-color="transparent"/>
        </radialGradient>
        <radialGradient id="cg2" cx="50%" cy="50%" r="50%">
          <stop offset="0%"  stop-color="#e04030" stop-opacity="0.26"/>
          <stop offset="55%" stop-color="#6a9ec8" stop-opacity="0.12"/>
          <stop offset="100%" stop-color="transparent"/>
        </radialGradient>
      </defs>
      ${auras}
      ${bolts.join('\n')}
    </svg>`;
  }

  function svgTreasure() {
    // Helper: draw a single Beli coin (gold disk with ฿ glyph + edge highlight)
    function beliCoin(cx, cy, r, opacity) {
      return `
        <g class="beli-coin">
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="#d4a44a" opacity="${opacity.toFixed(2)}" stroke="#7a4818" stroke-width="${(r*0.08).toFixed(2)}"/>
          <circle cx="${cx}" cy="${cy}" r="${(r*0.85).toFixed(1)}" fill="none" stroke="#7a4818" stroke-width="${(r*0.05).toFixed(2)}" opacity="${(opacity*0.6).toFixed(2)}"/>
          <text x="${cx}" y="${(cy+r*0.42).toFixed(1)}" text-anchor="middle"
                font-family="Georgia,serif" font-weight="900"
                font-size="${(r*1.2).toFixed(0)}" fill="#7a4818"
                opacity="${(opacity*0.85).toFixed(2)}">฿</text>
          <ellipse cx="${(cx-r*0.35).toFixed(1)}" cy="${(cy-r*0.45).toFixed(1)}"
                   rx="${(r*0.3).toFixed(1)}" ry="${(r*0.18).toFixed(1)}"
                   fill="#f5deb3" opacity="${(opacity*0.7).toFixed(2)}"/>
        </g>`;
    }

    // Floating individual Beli coins scattered
    const coins = [];
    for (let i = 0; i < 18; i++) {
      const cx = 80 + Math.random() * 1760;
      const cy = 80 + Math.random() * 920;
      const r  = 11 + Math.random() * 14;
      const dur = (4 + Math.random() * 6).toFixed(1);
      const delay = (Math.random() * 5).toFixed(1);
      const opacity = 0.45 + Math.random() * 0.4;
      coins.push(
        `<g class="coin" style="--dur:${dur}s;--delay:${delay}s">${beliCoin(cx, cy, r, opacity)}</g>`
      );
    }

    // Coin piles next to the chests — clusters of overlapping coins
    function coinPile(originX, originY, count = 8) {
      const out = [];
      for (let i = 0; i < count; i++) {
        const offX = -50 + Math.random() * 100;
        const offY = -25 + Math.random() * 30;
        const r = 12 + Math.random() * 8;
        const cx = originX + offX;
        const cy = originY + offY;
        out.push(beliCoin(cx, cy, r, 0.85));
      }
      return out.join('\n');
    }

    // Sparkles on coins (twinkling on the metal surface)
    const coinSparkles = [];
    for (let i = 0; i < 24; i++) {
      const cx = 60 + Math.random() * 1800;
      const cy = 60 + Math.random() * 960;
      const sz = 3 + Math.random() * 4;
      const dur = (2 + Math.random() * 4).toFixed(1);
      const delay = (Math.random() * 5).toFixed(1);
      coinSparkles.push(
        `<path class="sparkle coin-sparkle" d="M ${cx} ${cy-sz} L ${cx+sz*0.3} ${cy-sz*0.3} L ${cx+sz} ${cy} L ${cx+sz*0.3} ${cy+sz*0.3} L ${cx} ${cy+sz} L ${cx-sz*0.3} ${cy+sz*0.3} L ${cx-sz} ${cy} L ${cx-sz*0.3} ${cy-sz*0.3} Z"
           fill="#fff8c8" style="--dur:${dur}s;--delay:${delay}s"/>`
      );
    }

    // Big floating sparkles (kept from before — these are the airborne ones)
    const bigSparkles = [];
    const SPARK_POSITIONS = [
      [180, 180], [1620, 250], [870, 320], [1100, 200], [1350, 180],
      [200, 540], [1700, 600], [870, 580], [430, 480], [1500, 500],
      [340, 920], [1750, 880], [550, 900], [1350, 910], [950, 850]
    ];
    SPARK_POSITIONS.forEach(([cx, cy], i) => {
      const dur = (3 + Math.random() * 4).toFixed(1);
      const delay = (Math.random() * 5).toFixed(1);
      bigSparkles.push(
        `<path class="sparkle" d="M ${cx} ${cy-14} L ${cx+4} ${cy-4} L ${cx+14} ${cy} L ${cx+4} ${cy+4} L ${cx} ${cy+14} L ${cx-4} ${cy+4} L ${cx-14} ${cy} L ${cx-4} ${cy-4} Z"
           fill="#f5deb3" style="--dur:${dur}s;--delay:${delay}s"/>`
      );
    });

    // ── Oda-styled treasure chests ──
    // Wider rectangular base + domed lid + iron bands + big circular lock plate
    function odaChest(x, y, scale = 1) {
      // Base coords (chest at 0,0 origin, 200×140):
      // Body: x to x+200, y to y+140
      // Lid: domed top from y-50 to y
      const w = 200 * scale, h = 140 * scale;
      const lidH = 55 * scale;
      return `
      <g class="chest" transform="translate(${x},${y}) scale(${scale})">
        <!-- Chest body (wooden box) -->
        <rect x="0" y="0" width="200" height="140" fill="#5a3818" stroke="#2a1408" stroke-width="3" rx="4"/>
        <!-- Wood plank lines -->
        <line x1="0" y1="50" x2="200" y2="50" stroke="#3a2010" stroke-width="1.5"/>
        <line x1="0" y1="95" x2="200" y2="95" stroke="#3a2010" stroke-width="1.5"/>
        <!-- Iron vertical bands left + right -->
        <rect x="0" y="0" width="20" height="140" fill="#3a2818" stroke="#1a0a04" stroke-width="2"/>
        <rect x="180" y="0" width="20" height="140" fill="#3a2818" stroke="#1a0a04" stroke-width="2"/>
        <!-- Rivets on bands -->
        <circle cx="10" cy="20" r="3" fill="#7a5028"/>
        <circle cx="10" cy="70" r="3" fill="#7a5028"/>
        <circle cx="10" cy="120" r="3" fill="#7a5028"/>
        <circle cx="190" cy="20" r="3" fill="#7a5028"/>
        <circle cx="190" cy="70" r="3" fill="#7a5028"/>
        <circle cx="190" cy="120" r="3" fill="#7a5028"/>
        <!-- Domed lid -->
        <path d="M 0 0 Q 0 -${lidH}, 100 -${lidH} Q 200 -${lidH}, 200 0 Z"
              fill="#6a4220" stroke="#2a1408" stroke-width="3"/>
        <!-- Lid iron strap horizontal -->
        <path d="M 0 -25 Q 100 -${lidH+5}, 200 -25" fill="none" stroke="#3a2818" stroke-width="6"/>
        <!-- Big circular lock plate front-centre -->
        <circle cx="100" cy="0" r="18" fill="#d4a44a" stroke="#3a2010" stroke-width="3"/>
        <rect x="93" y="-3" width="14" height="20" fill="#1a0a04" rx="2"/>
        <!-- Highlight on lid -->
        <path d="M 30 -${lidH-6} Q 100 -${lidH-2}, 170 -${lidH-6}" stroke="#f5deb3" stroke-width="2" fill="none" opacity="0.5"/>
      </g>`;
    }

    const chests = odaChest(60, 880, 1.0) + odaChest(1660, 60, 0.7);

    // Jewels (kept, slightly upgraded)
    const jewels = `
      <polygon class="jewel" points="1450,910 1465,895 1480,910 1465,930" fill="#e07070" stroke="#7a1818" stroke-width="1.5" style="color:#e07070"/>
      <polygon class="jewel" points="350,170 365,155 380,170 365,190" fill="#6a9ec8" stroke="#1f3060" stroke-width="1.5" style="color:#6a9ec8"/>
      <polygon class="jewel" points="1550,160 1562,148 1574,160 1562,176" fill="#7ac290" stroke="#1f4030" stroke-width="1.5" style="color:#7ac290"/>
      <polygon class="jewel" points="1430,890 1442,878 1454,890 1442,906" fill="#b388ff" stroke="#3a1858" stroke-width="1.5" style="color:#b388ff"/>
    `;

    // Piles of coins beside the chests
    const piles = coinPile(280, 1010, 14) + coinPile(160, 1030, 10) + coinPile(1860, 200, 6);

    return `<svg viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">
      ${chests}
      ${piles}
      ${jewels}
      ${coins.join('\n')}
      ${bigSparkles.join('\n')}
      ${coinSparkles.join('\n')}
    </svg>`;
  }
})();
