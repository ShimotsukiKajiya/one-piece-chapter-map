"""D2 for the laddered pages — the three the main leak checker cannot see.

`scripts/lib/gate.py` walks LORE_PAGES, and every page there stores a FLAT list
of entries. The three laddered pages store rung stacks instead:

    marines-wg.json    tiers -> members -> rungs
    will-of-d.json     carriers -> rungs
    void-century.json  topics -> rungs

so none of them is inside D2's reach, and a lexicon term sitting in a rung below
its first-safe chapter goes unreported. Three were found that way on 2026-08-24:
"Haki" in the Vice Admirals summary behind a Ch. 92 gate, "Empty Throne" in a
Ch. 906 rung, and "Uranus" in a Ch. 650 rung.

This walks each stack the way the page's own renderer does and asks the D2
question at every probed cutoff: can a reader at this chapter see a term they
have not earned?

Mirrors the renderers exactly, and must change with them:
  - highest earned rung wins; `maxCh` retires one
  - a rung field OVERRIDES the base entry's field (void-century renders
    `r.name || t.name`), so only the shown value is measured
  - a tier with no earned rung, or no earned members, renders nothing

Reporting only — not in the daily CI. Exit 0 = clean, 1 = at least one leak.

Run:
  python scripts/audit_ladder_leaks.py
  python scripts/audit_ladder_leaks.py --verbose
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.gate import load_lexicon

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["marines-wg.json", "will-of-d.json", "void-century.json"]

# Boundary-heavy around the reveals the lexicon actually turns on.
CUTS = [1, 5, 20, 50, 69, 79, 92, 100, 126, 154, 164, 193, 200, 202, 233, 300,
        347, 362, 395, 397, 432, 433, 441, 449, 497, 504, 516, 525, 528, 550,
        574, 594, 596, 597, 628, 650, 700, 762, 763, 783, 802, 900, 906, 908,
        920, 956, 957, 967, 1000, 1018, 1044, 1054, 1060, 1061, 1086, 1136,
        1160, 1188]


def rung_at(rungs, cutoff):
    """Highest rung the reader has earned. Mirrors resolveRungs()."""
    got = [r for r in rungs or []
           if isinstance(r.get("ch"), int) and r["ch"] <= cutoff
           and not (isinstance(r.get("maxCh"), int) and cutoff > r["maxCh"])]
    return got[-1] if got else None


def strings_of(rung):
    out = []
    for k, v in (rung or {}).items():
        if k in ("ch", "maxCh"):
            continue
        if isinstance(v, str):
            out.append((k, v))
        elif isinstance(v, list):
            out += [(k, x) for x in v if isinstance(x, str)]
    return out


def visible_strings(doc, cutoff):
    """Every string a reader at `cutoff` can actually see on the page."""
    out = []
    for t in doc.get("tiers", []):
        tr = rung_at(t.get("rungs"), cutoff)
        if not tr:
            continue
        members = []
        for m in t.get("members", []):
            if isinstance(m.get("maxCh"), int) and cutoff >= m["maxCh"]:
                continue
            mr = rung_at(m.get("rungs"), cutoff)
            if mr:
                members.append((m.get("name", ""), mr))
        if not members:
            continue          # a tier with no earned member renders nothing
        out += strings_of(tr)
        for name, mr in members:
            out.append(("member name", name))
            out += strings_of(mr)

    for c in doc.get("carriers", []):
        cr = rung_at(c.get("rungs"), cutoff)
        if cr:
            out.append(("carrier name", c.get("name", "")))
            out += strings_of(cr)

    for t in doc.get("topics", []):
        tr = rung_at(t.get("rungs"), cutoff)
        if tr:
            # r.name || t.name -- the override replaces the base name
            out.append(("topic name", tr.get("name") or t.get("name", "")))
            out += strings_of(tr)

    for key in ("_canon_hints", "_speculation"):
        for e in doc.get(key) or []:
            if isinstance(e.get("ch"), int) and e["ch"] <= cutoff:
                out += strings_of(e)

    return out


def main():
    verbose = "--verbose" in sys.argv
    lexicon = load_lexicon(ROOT)

    print("=" * 76)
    print("  Ladder leaks — the D2 question on the three rung-stacked pages")
    print("=" * 76)
    print(f"\n  {len(lexicon)} lexicon terms · {len(CUTS)} cutoffs probed\n")

    total = 0
    for fname in PAGES:
        with open(os.path.join(ROOT, fname), encoding="utf-8") as f:
            doc = json.load(f)

        # first cutoff at which each distinct leak becomes visible
        hits = {}
        for cut in CUTS:
            for kind, text in visible_strings(doc, cut):
                for term, ch in lexicon:
                    if ch > cut and term in text:
                        hits.setdefault((term, ch, kind, text[:70]), cut)

        if hits:
            print(f"  ✗ {fname}  —  {len(hits)} leak(s)")
            for (term, ch, kind, text), first in sorted(hits.items(),
                                                        key=lambda x: x[1]):
                print(f"      from Ch. {first}: {term!r} is not safe until {ch}")
                print(f"        in {kind}: {text}")
            total += len(hits)
        else:
            print(f"  ✓ {fname}  —  clean at every probed cutoff")
        if verbose:
            for cut in CUTS:
                n = len(visible_strings(doc, cut))
                print(f"        cut {cut:>5}: {n:>4} visible strings")

    print("\n" + "-" * 76)
    if total:
        print(f"\n  {total} leak(s). A term below its first-safe chapter is a leak "
              f"whatever\n  the rung's own gate says — fail-late and reword, or "
              f"correct the lexicon.\n")
        return 1
    print("\n  ✓ No laddered page shows a term its reader has not earned.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
