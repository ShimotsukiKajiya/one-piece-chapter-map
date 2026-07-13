/**
 * SpoilerGuard — Onboarding overlay
 * ---------------------------------------------------------------------------
 *  Copyright (c) 2024–2026 Shimotsuki Kajiya. All rights reserved.
 *  Code: MIT License (see /LICENSE).  Design: CC BY-NC 4.0 (see /LICENSE-DATA.md).
 *  Part of the SpoilerGuard system — see /docs/spoilerguard-design.md.
 * ---------------------------------------------------------------------------
 *
 * Cold-start onboarding overlay
 *
 * One-time educational greeting for first-time visitors. Triggered when
 * STATE.greeted === false. Calm parchment-styled card, NOT a modal that
 * interrupts content. Uses the codex's own visual language.
 *
 * Loaded by every page alongside spoiler.js. Self-installs after a small
 * delay so it doesn't compete with the page's own load animations.
 *
 * Three actions:
 *   1. "Set my reading progress" → opens Settings → Spoiler Guard pane (top of menu)
 *   2. "I'm fully caught up"     → sets cutoff to LATEST, marks greeted=true
 *   3. "Let me look around"      → marks greeted=true, leaves cutoff at 0 (strict default)
 *
 * After any action, the overlay never reappears for that visitor.
 */
(function (global) {
  'use strict';

  if (!global.CodexSpoiler) {
    console.warn('[spoiler-onboarding] CodexSpoiler not loaded — onboarding disabled');
    return;
  }

  // Don't show if already greeted
  function shouldShow() {
    const s = global.CodexSpoiler.snapshot();
    return s && s.greeted === false;
  }

  function injectStyles() {
    if (document.getElementById('codex-spoiler-onboarding-styles')) return;
    const css = `
      #codex-onboarding-backdrop {
        position: fixed; inset: 0; z-index: 9999;
        background: rgba(12, 10, 20, 0.78);
        backdrop-filter: blur(4px);
        display: flex; align-items: center; justify-content: center;
        padding: 24px;
        opacity: 0; transition: opacity .25s ease;
        pointer-events: none;
      }
      #codex-onboarding-backdrop.on { opacity: 1; pointer-events: auto; }
      #codex-onboarding-card {
        max-width: 540px; width: 100%;
        background: linear-gradient(135deg, #1a1610 0%, #251f15 100%);
        border: 1px solid #4a3820;
        border-left: 4px solid #d4a44a;
        border-radius: 14px;
        padding: 28px 32px;
        color: #e8d8b0;
        font-family: 'Segoe UI', system-ui, sans-serif;
        box-shadow: 0 16px 60px rgba(0,0,0,.6), 0 4px 14px rgba(212,164,74,.08);
        transform: translateY(8px);
        transition: transform .25s ease;
      }
      #codex-onboarding-backdrop.on #codex-onboarding-card { transform: translateY(0); }
      #codex-onboarding-card h2 {
        margin: 0 0 6px;
        font-size: 1.05rem; font-weight: 800;
        color: #f5c95e;
        letter-spacing: 2px; text-transform: uppercase;
      }
      #codex-onboarding-card .sub {
        color: #8a7548; font-size: .78rem; letter-spacing: 1.5px;
        text-transform: uppercase; font-weight: 600;
        margin-bottom: 16px;
      }
      #codex-onboarding-card p {
        margin: 0 0 16px; font-size: 1rem; line-height: 1.6;
      }
      #codex-onboarding-card .actions {
        display: flex; flex-direction: column; gap: 8px;
        margin-top: 20px;
      }
      #codex-onboarding-card button {
        font-family: inherit; font-size: .92rem;
        background: #251f15; border: 1px solid #4a3820;
        color: #e8d8b0;
        padding: 11px 16px; border-radius: 8px;
        cursor: pointer; text-align: left;
        letter-spacing: .3px;
        transition: border-color .15s, background .15s;
      }
      #codex-onboarding-card button:hover {
        border-color: #d4a44a; background: #2d2519;
      }
      #codex-onboarding-card button.primary {
        background: linear-gradient(180deg, #f5c95e 0%, #d4a44a 100%);
        color: #1a1610; font-weight: 700; border-color: #d4a44a;
      }
      #codex-onboarding-card button.primary:hover { filter: brightness(1.06); }
      #codex-onboarding-card .hint {
        font-size: .76rem; color: #8a7548;
        margin-top: 14px; text-align: center;
        font-style: italic;
      }
    `;
    const style = document.createElement('style');
    style.id = 'codex-spoiler-onboarding-styles';
    style.textContent = css;
    document.head.appendChild(style);
  }

  function close() {
    const el = document.getElementById('codex-onboarding-backdrop');
    if (!el) return;
    el.classList.remove('on');
    setTimeout(() => el.remove(), 300);
  }

  function buildOverlay() {
    injectStyles();
    const backdrop = document.createElement('div');
    backdrop.id = 'codex-onboarding-backdrop';
    backdrop.innerHTML = `
      <div id="codex-onboarding-card" role="dialog" aria-labelledby="codex-onboarding-title">
        <div class="sub">🛡 Spoiler Guard · welcome</div>
        <h2 id="codex-onboarding-title">Your shield is on by default</h2>
        <p>
          The Codex covers <strong>every chapter</strong> of One Piece —
          characters, fights, devil fruits, crews, SBS answers, the lot.
          To stop spoilers from reaching you, content past your reading point is
          <strong>hidden everywhere</strong> until you tell us how far you've gotten.
        </p>
        <p style="font-size:.92rem;color:#a99a72;margin-bottom:0">
          Pick one — you can change it any time from the gear icon (top right).
        </p>
        <div class="actions">
          <button class="primary" id="codex-onboarding-set">
            📖 Set my reading progress
            <div style="font-size:.76rem;font-weight:400;margin-top:3px;color:#1a1610;opacity:.7">
              Tell us your chapter or episode — codex unlocks for you
            </div>
          </button>
          <button id="codex-onboarding-caughtup">
            🏴‍☠️ I'm fully caught up
            <div style="font-size:.76rem;font-weight:400;margin-top:3px;color:#8a7548">
              Set cutoff to the latest published chapter (Ch.${global.CodexSpoiler.LATEST_PUBLISHED_CHAPTER})
            </div>
          </button>
          <button id="codex-onboarding-skip">
            👀 Let me look around first
            <div style="font-size:.76rem;font-weight:400;margin-top:3px;color:#8a7548">
              Shield stays on — pre-timeskip content visible only
            </div>
          </button>
        </div>
        <div class="hint">All choices remembered locally on your device.</div>
      </div>
    `;
    document.body.appendChild(backdrop);

    // Click outside card = treat as "look around" (greeted but no cutoff)
    backdrop.addEventListener('click', e => {
      if (e.target === backdrop) {
        global.CodexSpoiler.markGreeted();
        close();
      }
    });

    backdrop.querySelector('#codex-onboarding-set').addEventListener('click', () => {
      global.CodexSpoiler.markGreeted();
      close();
      // Open settings, scroll to top (Spoiler Guard is now first section)
      setTimeout(() => {
        if (global.codexSettings && typeof global.codexSettings.open === 'function') {
          global.codexSettings.open();
          // Focus the chapter input if present
          setTimeout(() => {
            const inp = document.getElementById('codex-spoiler-input');
            if (inp) inp.focus();
          }, 200);
        }
      }, 250);
    });

    backdrop.querySelector('#codex-onboarding-caughtup').addEventListener('click', () => {
      global.CodexSpoiler.setCaughtUp();
      close();
    });

    backdrop.querySelector('#codex-onboarding-skip').addEventListener('click', () => {
      // Patch 7 (2026-05-03): write the safe pre-timeskip cutoff explicitly
      // rather than letting effectiveCutoff fall back to the magic 597.
      // Settings UI now shows "Ch. 597" instead of an empty field, and any
      // future change to the default boundary lives in one place.
      global.CodexSpoiler.setCutoff(597, 0);
      global.CodexSpoiler.markGreeted();
      close();
    });

    // Animate in
    requestAnimationFrame(() => backdrop.classList.add('on'));
  }

  function maybeShow() {
    if (!shouldShow()) return;
    // Small delay so the page's own intro animations settle first.
    setTimeout(buildOverlay, 600);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', maybeShow);
  } else {
    maybeShow();
  }
})(typeof window !== 'undefined' ? window : this);
