"""Reveal-chapter coverage audit — the Spoiler Guard's honesty check.

The other audit (audit_spoiler_coverage.py) only checks whether a page LOADS
the shield library. This one checks whether the shield can actually DO anything:
for every entity the site lists, do we know the chapter it was revealed in?

An entity with a known reveal chapter can be hidden precisely (like the fruits
page hides Loki's Nidhöggr below Ch.1170). An entity WITHOUT one cannot be
gated at all — it will show to every reader regardless of their cutoff. That
is a potential spoiler, and this report is the exact worklist for closing it.

Run:
  python scripts/audit_reveal_coverage.py           # human report
  python scripts/audit_reveal_coverage.py --list    # also print every ungated entity
"""
import os
import re
import json
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST = "--list" in sys.argv

# (data file, display name, the page it feeds, candidate chapter fields)
SOURCES = [
    ("devil_fruits.json",   "Devil Fruits",   "fruits.html",     ["debut_chapter", "first_appearance"]),
    ("weapons.json",        "Weapons & Meito", "weapons.html",    ["debut_chapter", "debut", "first_appearance"]),
    ("items.json",          "Items",          "items.html",      ["debut_chapter", "debut", "first_appearance"]),
    ("materials.json",      "Materials",      "materials.html",  ["debut_chapter", "debut", "first_appearance"]),
    ("tech.json",           "Tech & Artifacts", "tech.html",     ["debut_chapter", "debut", "first_appearance"]),
    ("ships.json",          "Ships",          "ships.html",      ["debut_chapter", "first_appearance"]),
    ("locations.json",      "Locations",      "locations.html",  ["debut_chapter", "first_appearance"]),
    ("ancient-weapons.json","Ancient Weapons","ancient-weapons.html", ["debut_chapter", "debut", "first_appearance"]),
    ("punk_records.json",   "Characters",     "characters.html", ["first_appearance", "debut_chapter"]),
]


def _iter_entities(data):
    """Yield (name, record) for list- or dict-shaped entity files."""
    if isinstance(data, list):
        for r in data:
            if isinstance(r, dict):
                yield r.get("name", "?"), r
    elif isinstance(data, dict):
        # Some files wrap the list under a key; find the first list value.
        for key in ("fruits", "weapons", "items", "ships", "locations",
                    "materials", "tech", "ancient_weapons", "entries"):
            if isinstance(data.get(key), list):
                for r in data[key]:
                    if isinstance(r, dict):
                        yield r.get("name", "?"), r
                return
        for name, r in data.items():
            if isinstance(r, dict):
                yield r.get("name", name), r


def _chapter_of(record, fields):
    """Return an int chapter if any candidate field carries a parseable one."""
    for f in fields:
        v = record.get(f)
        if v is None:
            continue
        if isinstance(v, (int, float)) and v > 0:
            return int(v)
        m = re.search(r"[Cc]hapter\s*(\d{1,4})", str(v)) or re.search(r"\b(\d{2,4})\b", str(v))
        if m:
            return int(m.group(1))
    return None


def main():
    print("=" * 60)
    print("  Reveal-Chapter Coverage — can the Spoiler Guard hide it?")
    print("=" * 60)
    total_ent = total_gatable = 0
    worst = []
    for fn, label, page, fields in SOURCES:
        path = os.path.join(ROOT, fn)
        if not os.path.exists(path):
            print(f"\n  {label:<16} (—) {fn} not found")
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            print(f"\n  {label:<16} (!) unreadable: {e}")
            continue
        ents = [(n, r) for n, r in _iter_entities(data)
                if r.get("found", True)]  # skip not-found wiki stubs
        gatable = [(n, r) for n, r in ents if _chapter_of(r, fields) is not None]
        ungated = [n for n, r in ents if _chapter_of(r, fields) is None]
        n, g = len(ents), len(gatable)
        total_ent += n
        total_gatable += g
        pct = (100 * g // n) if n else 0
        flag = "✓" if pct >= 90 else ("⚠" if pct >= 40 else "✗")
        print(f"\n  {flag} {label:<16} {g:>4}/{n:<4} gatable ({pct}%)   → {page}")
        if pct < 90:
            worst.append((label, len(ungated), page))
            if LIST and ungated:
                shown = ", ".join(ungated[:25])
                more = f" … +{len(ungated)-25} more" if len(ungated) > 25 else ""
                print(f"       ungatable: {shown}{more}")
    overall = (100 * total_gatable // total_ent) if total_ent else 0
    print("\n" + "=" * 60)
    print(f"  Overall: {total_gatable}/{total_ent} entities have a reveal chapter ({overall}%)")
    if worst:
        print("  Biggest gaps (patch these to close spoiler holes):")
        for label, n_missing, page in sorted(worst, key=lambda x: -x[1]):
            print(f"    • {label}: {n_missing} entities need a reveal chapter ({page})")
    print("  Re-run with --list to see the exact entities.")
    print("=" * 60)


if __name__ == "__main__":
    main()
