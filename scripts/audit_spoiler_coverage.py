"""Spoiler Shield coverage audit.

Walks every HTML page in the project and reports:
  - Pages that include spoiler.js (✓ has the library)
  - Pages that include spoiler-onboarding.js (✓ first-time visitor lands well)
  - Pages that actually CALL the gate (CodexSpoiler.* references in inline scripts)
  - Pages that are GATE-EXPECTED but missing the library (per docs/spoiler-shield page-audit)
  - Pages that are EXPECTED to be meta/utility (404, news, about, etc.) and need no gate

Run:
  python scripts/audit_spoiler_coverage.py            # report findings, exit 0/1/2
  python scripts/audit_spoiler_coverage.py --strict   # exit 2 if any expected-gated page lacks coverage
"""
import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pages that SHOULD have spoiler gating per the architecture plan
EXPECTED_GATED = {
    # Index pages
    "characters.html", "fruits.html", "fruit.html", "crews.html", "crew.html",
    "ships.html", "ship.html", "locations.html", "location.html", "voices.html",
    "bounties.html", "heights.html", "compare.html", "families.html",
    # Atlas + maps
    "atlas.html", "chapter-release-map.html", "heatmap.html",
    # Curated content
    "timeline.html", "moments.html", "covers.html", "arcs.html", "sagas.html",
    "reverie.html",
    # SBS
    "sbs.html", "sbs-topics.html",
    # Theories + tools
    "theories.html", "workbench.html", "prove.html", "conflicts.html", "quiz.html",
    # LORE essays (character link lists need gating)
    "haki.html", "poneglyphs.html", "void-century.html", "will-of-d.html",
    "ancient-weapons.html", "marines-wg.html", "combat-styles.html",
    "races.html", "materials.html", "items.html", "tech.html",
    "awakenings.html", "jolly-rogers.html",
    # Detail pages
    "character.html",
    # Front door
    "home.html",
    # L12 fix 2026-05-03: moved from EXPECTED_UNGATED after live tests confirmed
    # real spoiler content. world-map has Marineford/Wano/Egghead labels (gated
    # via per-island min-ch in L6 fix). music + episodes have late-arc references
    # (gating still pending — they're EXPECTED_GATED so the audit will flag them
    # if they don't load spoiler.js).
    "world-map.html", "music.html", "episodes.html",
}

# Pages that legitimately need no gate (meta, utility, error, redirect)
EXPECTED_UNGATED = {
    "404.html", "about.html", "corrections.html", "tools.html", "lore.html",
    "punk-records.html", "news.html", "index.html",
}


def scan_page(path):
    """Return summary of spoiler-related includes/calls in this HTML file."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            src = f.read()
    except Exception:
        return None
    return {
        "has_spoiler_js":         "spoiler.js?v=" in src or 'src="spoiler.js"' in src,
        "has_onboarding":         "spoiler-onboarding.js" in src,
        "has_codex_spoiler_call": "CodexSpoiler" in src,
        "has_chr_debut_map":      "chr-debut-map" in src,
    }


def main():
    args = sys.argv[1:]
    strict = "--strict" in args

    print("=" * 60)
    print("  Spoiler Shield Coverage Audit")
    print("=" * 60)
    print()

    gated_pages = []         # has library + a call
    library_only_pages = []  # has spoiler.js but no CodexSpoiler.* call
    missing_pages = []       # expected to be gated but no coverage at all
    not_gated_correctly = [] # expected ungated but found library (worth knowing)
    no_onboarding = []       # has spoiler.js but no onboarding (cold-start visitors land cold)
    expected_ungated_clean = 0

    expected_total = len(EXPECTED_GATED)

    for fname in sorted(os.listdir(ROOT)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(ROOT, fname)
        info = scan_page(path)
        if info is None:
            continue
        if fname in EXPECTED_GATED:
            if info["has_spoiler_js"] and info["has_codex_spoiler_call"]:
                gated_pages.append(fname)
            elif info["has_spoiler_js"]:
                library_only_pages.append(fname)
            else:
                missing_pages.append(fname)
            if info["has_spoiler_js"] and not info["has_onboarding"]:
                no_onboarding.append(fname)
        elif fname in EXPECTED_UNGATED:
            if info["has_spoiler_js"]:
                not_gated_correctly.append(fname)
            else:
                expected_ungated_clean += 1
        else:
            # Page exists but isn't classified — could be detail page or new addition
            pass

    print(f"  EXPECTED GATED:  {expected_total} pages")
    print(f"    ✓ Fully gated (library + call):  {len(gated_pages)}")
    print(f"    ⚠ Library-only (no gate call):    {len(library_only_pages)}")
    print(f"    ✗ Missing entirely:               {len(missing_pages)}")
    print(f"    ⚠ No onboarding overlay:          {len(no_onboarding)} (visitors land cold)")
    print()
    print(f"  EXPECTED UNGATED: {len(EXPECTED_UNGATED)} pages")
    print(f"    ✓ Clean (no spoiler.js):  {expected_ungated_clean}")
    print(f"    ⓘ Has spoiler.js anyway:  {len(not_gated_correctly)} (harmless but noted)")
    print()

    if missing_pages:
        print("  ✗ MISSING COVERAGE on expected-gated pages:")
        for p in missing_pages:
            print(f"      - {p}")
        print()
    if library_only_pages:
        print("  ⚠ Library included but no CodexSpoiler.* call (gate isn't doing anything):")
        for p in library_only_pages:
            print(f"      - {p}")
        print()
    if no_onboarding:
        print("  ⚠ Has spoiler.js but no onboarding overlay:")
        for p in no_onboarding[:10]:
            print(f"      - {p}")
        if len(no_onboarding) > 10:
            print(f"      … and {len(no_onboarding) - 10} more")
        print()

    pct = (len(gated_pages) / expected_total * 100) if expected_total else 0
    print("=" * 60)
    print(f"  Coverage: {len(gated_pages)} / {expected_total} expected ({pct:.0f}%)")
    print("=" * 60)

    if strict and (missing_pages or library_only_pages):
        return 2
    return 1 if missing_pages else 0


if __name__ == "__main__":
    sys.exit(main())
