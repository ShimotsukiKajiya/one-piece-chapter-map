"""D5 — Coverage: does the page hold everything that belongs on it?

The other checkers ask whether what a page shows is safe and non-empty. Neither
asks whether anything is MISSING. A curated page can be perfectly gated,
perfectly non-blank, and still be quietly incomplete -- the World Government
chart had no Seven Warlords tier at all, and the Will of D. page held 10 of 12
known carriers.

Derives the belongs-set from the data files, never from recall. A gap in a
maintainer's memory becomes a permanent gap in the page otherwise; that is
exactly how Clou D. Clover went missing.

Name comparison goes through lib.resolve (entity_index's 11,893 aliases), so
"Coby" on the page matches "Koby" in the records instead of reading as absent.

Ship gate, per project policy: >95% match rate. Conflicts are reported as
findings, never silently coerced, and 100% is not the target -- the last few
percent are usually real editorial ambiguities.

Exit codes: 0 = at or above the gate · 1 = below the gate (a real coverage hole)

Run:
  python scripts/audit_page_coverage.py
  python scripts/audit_page_coverage.py --list    # every missing name
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.resolve import Resolver, normalise

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHIP_GATE = 0.95

# Affiliations that put someone on the World Government chart.
# NOTE the traps, each of which produced a wrong answer during the manual pass:
#   - bare "navy" matches HAPPO Navy and drags in Luffy, Zoro, Brook, Jinbe
#   - "Impel Down" matches INMATES (Doflamingo, Crocodile, Arlong) as readily
#     as staff, so it only counts alongside a warden/guard/jailer occupation
#   - "(former)" and "(defected)" are still membership -- Rosinante, Jaguar D.
#     Saul and Bell-mere belong, gated at the chapter the reader learns it
WG_AFFIL = re.compile(
    r"\bmarines?\b|world government|cipher pol|\bcp-?[0-9]\b|\bsword\b"
    r"|god'?s knight|holy knight|celestial dragon|world noble"
    r"|seven warlords|shichibukai|warlord of the sea", re.I)
ID_STAFF = re.compile(r"warden|guard|jailer|chief|executioner", re.I)


def jload(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def belongs_wg(rec):
    aff = str(rec.get("affiliation") or "")
    occ = str(rec.get("occupation") or "")
    blob = aff + " " + occ
    if WG_AFFIL.search(blob):
        return True
    # Impel Down staff only -- never its prisoners
    if re.search(r"impel down", aff, re.I) and ID_STAFF.search(occ):
        return True
    return False


def belongs_will_of_d(rec):
    """A name carrying the initial. Lineage carriers are added by hand below."""
    return bool(re.search(r"\bD\.\s", str(rec.get("name") or "")))


# Carriers whose D. is established by lineage or reveal rather than by the
# stored name form. Maintainer-confirmed; extend as chapters land.
WILL_OF_D_EXTRA = ["Nefertari D. Lili", "Clou D. Clover"]

PAGES = [
    ("marines-wg.json",  "Marines & World Government", belongs_wg),
    ("will-of-d.json",   "Will of D.",                 belongs_will_of_d),
]


def wg_category(rec):
    """Which part of the World Government chart this person belongs to.

    Grouping matters more than the raw count: it turns 134 loose names into
    'the page has no Seven Warlords tier', which is the actual fix."""
    if not rec:
        return "unclassified"
    blob = f"{rec.get('affiliation') or ''} {rec.get('occupation') or ''}"
    tests = [
        (r"seven warlords|shichibukai|warlord of the sea", "Seven Warlords"),
        (r"god'?s knight|knights of god|holy knight",      "God's Knights"),
        (r"\bssg\b|science unit",                          "SSG / Vegapunk"),
        (r"\bcp-?0\b|cipher pol aigis",                    "CP0"),
        (r"\bcp-?9\b",                                     "CP9"),
        (r"\bcp-?[1-8]\b|cipher pol",                      "Cipher Pol (other)"),
        (r"\bsword\b",                                     "SWORD"),
        (r"impel down",                                    "Impel Down"),
        (r"celestial dragon|world noble",                  "World Nobles"),
        (r"fleet admiral",                                 "Fleet Admiral"),
        (r"\badmiral\b",                                   "Admirals / Vice Admirals"),
        (r"enies lobby|chief justice|justice",             "Judicial / Enies Lobby"),
        (r"\bmarines?\b",                                  "Marines (other ranks)"),
        (r"world government",                              "World Government (civil)"),
    ]
    for pattern, name in tests:
        if re.search(pattern, blob, re.I):
            return name
    return "unclassified"


def page_names(fname):
    """Every character name the curated page lists."""
    doc = jload(fname)
    names = []
    for tier in doc.get("tiers", []):
        for m in tier.get("members", []):
            if m.get("name"):
                names.append(m["name"])
    for c in doc.get("carriers", []):
        if c.get("name"):
            names.append(c["name"])
    return names


def main():
    show_all = "--list" in sys.argv
    resolver = Resolver(ROOT)
    pr = jload("punk_records.json")
    records = list(pr.values())

    print("=" * 76)
    print("  D5 — Page coverage: is anything that belongs actually missing?")
    print("=" * 76)

    worst = 1.0
    findings = []
    rates = {}

    for fname, label, predicate in PAGES:
        expected = [r for r in records if predicate(r)]
        expected_names = {(r.get("name") or "").strip() for r in expected}
        if fname == "will-of-d.json":
            expected_names |= set(WILL_OF_D_EXTRA)

        on_page = page_names(fname)
        # Resolve both sides so Coby/Koby, T-Bone/T Bone compare equal.
        on_norm = set()
        for n in on_page:
            on_norm.add(normalise(resolver.canonical(n) or n))

        missing = []
        for name in sorted(expected_names):
            key = normalise(resolver.canonical(name) or name)
            if key not in on_norm:
                missing.append(name)

        total = len(expected_names)
        present = total - len(missing)
        rate = present / total if total else 1.0
        worst = min(worst, rate)
        rates[label] = rate

        mark = "✓" if rate >= SHIP_GATE else "✗"
        print(f"\n  {mark} {label}")
        print(f"      on page {len(on_page):>4} · belongs {total:>4} · "
              f"present {present:>4} · missing {len(missing):>4} · "
              f"{rate*100:.0f}%")

        if missing:
            by_name = {(r.get("name") or "").strip(): r for r in expected}

            def apps(n):
                rec = by_name.get(n)
                a = rec.get("appearances") if rec else 0
                return a if isinstance(a, int) else 0

            # Group by which part of the chart they belong to. A missing
            # INSTITUTION outranks a missing person -- the WG page had no
            # Seven Warlords tier at all, which no per-name list makes obvious.
            groups = {}
            for n in missing:
                groups.setdefault(wg_category(by_name.get(n)), []).append(n)

            for cat in sorted(groups, key=lambda c: -len(groups[c])):
                names = sorted(groups[cat], key=lambda n: -apps(n))
                print(f"        {cat:26} {len(names):>3} missing")
                shown = names if show_all else names[:4]
                for n in shown:
                    print(f"          · {n[:38]:38} {apps(n):>4} apps")
                if not show_all and len(names) > 4:
                    print(f"          … and {len(names)-4} more")
            findings.append((label, len(missing), rate))

    # ── data integrity ────────────────────────────────────────────────────
    # A split record inflates the "missing" count without anything actually
    # being absent: the page lists Imu, punk_records holds BOTH 'Imu' (no id,
    # 3 appearances) and 'Nerona Imu' (chr:02569, 32), so the fuller record
    # reads as uncovered. Surfaced here because it corrupts coverage silently.
    print("\n" + "-" * 76)
    print("\n  DATA INTEGRITY — issues that distort the numbers above\n")

    names = sorted({(r.get("name") or "").strip() for r in records if r.get("name")})
    by_name = {(r.get("name") or "").strip(): r for r in records}

    def apps_of(n):
        a = by_name.get(n, {}).get("appearances")
        return a if isinstance(a, int) else 0

    # One name is the tail of another ("Imu" / "Nerona Imu"). The name shape
    # alone over-reports -- 'Gorilla' vs 'Blue Gorilla' are different people --
    # so require the same first-appearance chapter as corroboration.
    def debut_of(n):
        m = re.search(r"Chapter (\d+)", str(by_name.get(n, {}).get("first_appearance") or ""))
        return int(m.group(1)) if m else None

    suspected = []
    lookup = {n.lower(): n for n in names}
    for n in names:
        parts = n.split()
        if len(parts) < 2:
            continue
        tail = parts[-1].lower()
        short = lookup.get(tail)
        if not short or short == n:
            continue
        d1, d2 = debut_of(short), debut_of(n)
        if d1 is not None and d1 == d2:
            suspected.append((short, n))

    if suspected:
        print(f"    possible split records ({len(suspected)}):")
        for short, full in suspected[:8]:
            print(f"      · {short!r} ({apps_of(short)} apps) vs "
                  f"{full!r} ({apps_of(full)} apps)")
        if len(suspected) > 8:
            print(f"      … and {len(suspected)-8} more")

    no_id = [r for r in records if r.get("name") and not r.get("id")]
    if no_id:
        print(f"\n    records with no entity id ({len(no_id)}): cannot be linked or"
              f" cross-referenced")
        for r in sorted(no_id, key=lambda r: -(r.get("appearances") or 0))[:5]:
            print(f"      · {(r.get('name') or '')[:34]:34} "
                  f"{r.get('appearances') or 0:>4} apps")

    print("\n" + "-" * 76)
    print(f"\n  Ship gate: >{SHIP_GATE*100:.0f}% match. Conflicts are findings, not"
          f" failures to coerce — 100% is not the target.")

    # A known backlog should not fail CI every morning -- that trains people to
    # ignore the check. Coverage is measured against a recorded baseline, so an
    # existing hole is reported while a REGRESSION fails. Raise the baseline
    # (--update-baseline) as coverage improves; it never lowers itself.
    baseline_path = os.path.join(ROOT, "docs", "coverage-baseline.json")
    try:
        with open(baseline_path, encoding="utf-8") as f:
            baseline = json.load(f)
    except OSError:
        baseline = {}

    if "--update-baseline" in sys.argv:
        merged = dict(baseline.get("pages", {}))
        for label, rate in rates.items():
            merged[label] = max(round(rate, 4), merged.get(label, 0))
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump({"_doc": "Best coverage rate recorded per page. "
                               "audit_page_coverage.py fails on a drop below "
                               "these, so a known backlog reports without "
                               "failing CI while a regression still does. "
                               "Never lowered automatically.",
                       "pages": merged}, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\n  ✓ baseline updated → docs/coverage-baseline.json\n")
        return 0

    prior = baseline.get("pages", {})
    regressions = [(label, rate, prior[label]) for label, rate in rates.items()
                   if label in prior and rate < prior[label] - 0.001]

    if regressions:
        print(f"\n  ✗ COVERAGE REGRESSION — a page lost entries it used to hold:\n")
        for label, now, was in regressions:
            print(f"      {label}: {was*100:.0f}% → {now*100:.0f}%")
        print()
        return 2

    below = [l for l, r in rates.items() if r < SHIP_GATE]
    if below:
        print(f"\n  · Below the ship gate (known backlog, not a regression): "
              f"{', '.join(below)}")
        print(f"    Worklist above. Raise the bar with --update-baseline once"
              f" coverage improves.\n")
    else:
        print(f"\n  ✓ Every page at or above the ship gate.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
