/**
 * The Shimotsuki Codex — Fan Disclaimer Notice
 *
 * First visit:       blocking modal, checkbox required before entry
 * Visits 1–3:        gold pulse ring on the ℹ info button, stops on click
 * After that:        nothing (footer note stays permanently on every page)
 */
(function () {
  'use strict';

  const KEY = 'codex-legal-v1';

  function load() {
    try { return JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (_) { return {}; }
  }
  function save(patch) {
    try {
      const s = load();
      localStorage.setItem(KEY, JSON.stringify(Object.assign(s, patch)));
    } catch (_) {}
  }

  const state  = load();
  const visits = (state.visits || 0) + 1;
  save({ visits });

  // First visit OR never confirmed — show modal
  if (!state.confirmed) {
    showModal();
    // pulse still wires up after modal is dismissed (below)
  }

  // Pulse the ℹ button on visits 1–3 to guide users toward the legal statement
  if (visits <= 3 && !state.infoPulseDismissed) {
    pulseInfoBtn();
  }

  // ─── Modal ────────────────────────────────────────────────────
  function showModal() {
    const st = document.createElement('style');
    st.textContent = `
      #cl-overlay {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(10, 8, 18, 0.93);
        display: flex; align-items: center; justify-content: center;
        padding: 20px;
        backdrop-filter: blur(5px); -webkit-backdrop-filter: blur(5px);
      }
      #cl-box {
        background: #221e14;
        border: 1px solid #5c4828;
        border-top: 3px solid #d4a44a;
        border-radius: 16px;
        padding: 40px 44px;
        max-width: 580px; width: 100%;
        box-shadow: 0 24px 64px rgba(0,0,0,0.85);
        position: relative;
      }
      #cl-box .cl-anchor {
        text-align: center; font-size: 2.2rem; margin-bottom: 18px;
        filter: drop-shadow(0 2px 8px rgba(212,164,74,0.4));
      }
      #cl-box h2 {
        font-size: 1.1rem; font-weight: 900;
        letter-spacing: 3px; text-transform: uppercase;
        color: #f5c95e; text-align: center; margin-bottom: 22px;
      }
      #cl-box p {
        font-size: 0.93rem; line-height: 1.8;
        color: #f0e8d4; margin-bottom: 14px;
      }
      #cl-box .cl-em { color: #f5c95e; font-weight: 700; }
      #cl-box .cl-divider {
        height: 1px; margin: 22px 0;
        background: linear-gradient(to right, transparent, #5c4828, transparent);
      }
      #cl-check-row {
        display: flex; align-items: flex-start; gap: 13px;
        margin-bottom: 20px; cursor: pointer;
      }
      #cl-check-row input[type=checkbox] {
        width: 20px; height: 20px; margin-top: 2px;
        accent-color: #d4a44a; flex-shrink: 0; cursor: pointer;
      }
      #cl-check-row label {
        font-size: 0.9rem; line-height: 1.55;
        color: #f0e8d4; cursor: pointer;
      }
      #cl-confirm {
        width: 100%; padding: 14px;
        background: linear-gradient(135deg, #d4a44a 0%, #f5c95e 100%);
        color: #0c0a14; border: none; border-radius: 10px;
        font-size: 0.95rem; font-weight: 900;
        letter-spacing: 2px; text-transform: uppercase;
        cursor: pointer; opacity: 0.35; pointer-events: none;
        transition: opacity 0.2s, transform 0.15s;
      }
      #cl-confirm.cl-ready { opacity: 1; pointer-events: all; }
      #cl-confirm.cl-ready:hover { transform: translateY(-1px); opacity: 0.9; }
      #cl-more, #cl-more:visited {
        display: block; text-align: center; margin-top: 16px;
        font-size: 0.78rem; color: #6a9ec8; text-decoration: underline;
      }
      @media (max-width: 480px) {
        #cl-box { padding: 30px 22px; }
        #cl-box h2 { font-size: 0.95rem; letter-spacing: 2px; }
        #cl-box p  { font-size: 0.88rem; }
      }
    `;
    document.head.appendChild(st);

    const overlay = document.createElement('div');
    overlay.id = 'cl-overlay';
    overlay.innerHTML = `
      <div id="cl-box" role="dialog" aria-modal="true" aria-labelledby="cl-title">
        <div class="cl-anchor">⚓</div>
        <h2 id="cl-title">A note before you sail</h2>

        <p>
          <span class="cl-em">The Shimotsuki Codex is an unofficial fan reference.</span>
          It has no affiliation with, and is not endorsed or authorised by,
          Eiichiro Oda, Shueisha, or Toei Animation.
        </p>
        <p>
          One Piece — its story, characters, art, and world — belongs entirely
          to Eiichiro Oda and Shueisha. This site makes no claim over any of it.
          No original artwork, scans, or official media are hosted here.
        </p>
        <p>
          This is a fan-built, non-commercial project. It exists to help fans
          explore, fact-check, and celebrate One Piece together — to support the
          community and the series, not to compete with or profit from the official work.
        </p>

        <div class="cl-divider"></div>

        <div id="cl-check-row">
          <input type="checkbox" id="cl-cb">
          <label for="cl-cb">I understand this is an unofficial fan project with no affiliation to Oda, Shueisha, or Toei Animation.</label>
        </div>
        <button id="cl-confirm" disabled>
          Understood — let's go ›
        </button>
        <a class="cl-more" href="about.html">Read the full project statement →</a>
      </div>
    `;
    document.body.appendChild(overlay);

    const cb  = overlay.querySelector('#cl-cb');
    const btn = overlay.querySelector('#cl-confirm');

    cb.addEventListener('change', () => {
      btn.classList.toggle('cl-ready', cb.checked);
      btn.disabled = !cb.checked;
    });

    btn.addEventListener('click', () => {
      if (!cb.checked) return;
      save({ confirmed: true, confirmedOn: new Date().toISOString() });
      overlay.remove();
    });

    // Navigating via the "full statement" link counts as implicit confirmation
    const link = overlay.querySelector('.cl-more');
    link.addEventListener('click', () => {
      save({ confirmed: true, confirmedOn: new Date().toISOString() });
    });
  }

  // ─── ℹ button pulse ──────────────────────────────────────────
  function pulseInfoBtn() {
    const st = document.createElement('style');
    st.textContent = `
      @keyframes cl-pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(212,164,74,0); }
        50%       { box-shadow: 0 0 0 5px rgba(212,164,74,0.45); }
      }
      #nav-info-btn.cl-pulsing {
        animation: cl-pulse 2.2s ease-in-out infinite;
        position: relative;
      }
      #nav-info-btn.cl-pulsing::after {
        content: '';
        position: absolute; top: -3px; right: -3px;
        width: 8px; height: 8px;
        background: #d4a44a; border-radius: 50%;
        border: 2px solid #0c0a14;
        pointer-events: none;
      }
    `;
    document.head.appendChild(st);

    // nav-info-btn is injected by nav-burger.js (defer) — wait for it
    function attach() {
      const btn = document.getElementById('nav-info-btn');
      if (!btn) return;
      btn.classList.add('cl-pulsing');
      btn.addEventListener('click', () => {
        btn.classList.remove('cl-pulsing');
        save({ infoPulseDismissed: true });
      }, { once: true });
    }

    // Try immediately, then poll briefly in case burger hasn't run yet
    if (document.getElementById('nav-info-btn')) {
      attach();
    } else {
      const t = setInterval(() => {
        if (document.getElementById('nav-info-btn')) {
          clearInterval(t);
          attach();
        }
      }, 80);
      // Give up after 3s (page without nav-burger)
      setTimeout(() => clearInterval(t), 3000);
    }
  }
})();
