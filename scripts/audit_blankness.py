"""D3 — Completeness: does the page still say anything at the reader's chapter?

The dimension nobody was checking. A leak audit rewards hiding, so a gate can
score perfectly while emptying the site: after the 2026-08 sweep, `combat-styles`
rendered zero entries at every chapter and `music` showed 2 of 18 tracks to
anyone not caught up. Both scored "no leaks".

A page fails here when a reader can REACH it (the nav does not gate it at their
chapter) and it renders nothing. Either the nav gate should be raised to the
page's first-content chapter, or the entries need earlier rungs.

Exit codes match audit.py: 0 = clean · 2 = a reachable page renders nothing.

Run:
  python scripts/audit_blankness.py
  python scripts/audit_blankness.py --table    # full survival table
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.gate import (LORE_PAGES, THRESHOLDS, load_lexicon, load_page, visible,
                      gate_chapter, nav_gates)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    show_table = "--table" in sys.argv
    lexicon = load_lexicon(ROOT)
    gates = nav_gates(ROOT)

    print("=" * 78)
    print("  D3 — Blankness: can a reader reach a page that shows them nothing?")
    print("=" * 78)

    if show_table:
        print(f"\n  {'page':22} {'tot':>3} | " + " ".join(f"{c:>4}" for c in THRESHOLDS))
        print("  " + "-" * 74)

    blank = []
    recommended = {}

    for fname, key, page in LORE_PAGES:
        entries = load_page(ROOT, fname, key)
        gate = gates.get(page, 0)
        counts = []
        for cut in THRESHOLDS:
            n = len(visible(entries, cut, lexicon))
            counts.append(n)
            if n == 0 and cut >= gate:
                blank.append((page, cut, gate))
        dated = [c for c in (gate_chapter(e) for e in entries) if c]
        recommended[page] = min(dated) if dated else None
        if show_table:
            row = " ".join(f"{n:>4}" for n in counts)
            flag = "" if all(c > 0 for c, t in zip(counts, THRESHOLDS) if t >= gate) else "  <-- BLANK"
            print(f"  {page:22} {len(entries):>3} | {row}{flag}")

    print("\n  " + "-" * 74)

    if blank:
        # collapse to the worst (highest) blank chapter per page
        worst = {}
        for page, cut, gate in blank:
            if page not in worst or cut > worst[page][0]:
                worst[page] = (cut, gate)
        print(f"\n  ✗ {len(worst)} page(s) reachable but empty:\n")
        for page, (cut, gate) in sorted(worst.items()):
            rec = recommended.get(page)
            g = f"nav gate {gate}" if gate else "no nav gate"
            print(f"      {page:22} blank up to ch {cut:>4} · {g}")
            if rec:
                print(f"      {'':22} → raise the nav gate to {rec}, or ladder its"
                      f" entries below {rec}")
        print()
        return 2

    print("\n  ✓ Every reachable page shows at least one entry.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
