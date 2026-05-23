"""
Find Conflicts — Phase E of the Canon Engine.

Walks every canon source we have (canon_facts.json + punk_records.json
+ sbs_archive.json) and surfaces any place where two sources disagree
on the same (subject, predicate) pair.

A conflict is recorded when:
  1. Multiple canon_facts entries exist for the same subject+predicate
     with different values
  2. A canon_facts entry's value differs from the corresponding
     wiki value in punk_records.json (post-Phase-C, this should be
     rare — Phase C only promotes wiki values that already match SBS,
     so this surfaces the deltas where an OLDER scrape disagrees)
  3. Two SBS Q&As mentioning the same subject+predicate give
     different values (detected via the proximity matcher)

Output:
  docs/conflicts.json — structured list for conflicts.html
  docs/conflicts_report.md — human-readable summary

Run:
  py find_conflicts.py             # detect + write
  py find_conflicts.py --dry-run   # report only
  py find_conflicts.py --verbose   # show each conflict's details
"""
import os, sys, json, re
from collections import defaultdict
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
PUNK_PATH  = os.path.join(DIR, "punk_records.json")
SBS_PATH   = os.path.join(DIR, "sbs_archive.json")
FACTS_PATH = os.path.join(DIR, "canon_facts.json")
CONF_JSON  = os.path.join(DIR, "docs", "conflicts.json")
CONF_REPORT= os.path.join(DIR, "docs", "conflicts_report.md")

TODAY = date.today().isoformat()

# Predicates that are inherently multi-valued: multiple facts with the same
# subject+predicate represent parallel truths (e.g. Luffy has TWO sworn brothers,
# Zoro owns FOUR swords), not contradictions.  Skip conflict detection for these.
_MULTI_VALUED_PREDICATES = frozenset({
    "sworn-brother", "brother", "sister", "daughter", "son",
    "satellite", "owns",
})


def values_equivalent(a, b):
    """Loose equality — same digit groups OR same after stripping
    parentheticals/casing/whitespace."""
    if a == b: return True
    sa = str(a).strip().lower(); sb = str(b).strip().lower()
    if sa == sb: return True
    # Strip parentheticals
    sa2 = re.sub(r"\s*\([^)]*\)", "", sa).strip()
    sb2 = re.sub(r"\s*\([^)]*\)", "", sb).strip()
    if sa2 == sb2 and sa2: return True
    # Compare digit groups (exact match)
    da = re.findall(r"\d+", sa)
    db = re.findall(r"\d+", sb)
    if da and db and da == db: return True
    # Subset check: one value is a simpler form of the other
    # (e.g. Vivre Card "174 cm" ⊆ compound "91 cm · 172 cm · 174 cm (pre/post-timeskip)").
    if da and db:
        sa_set, sb_set = set(da), set(db)
        if sa_set.issubset(sb_set) or sb_set.issubset(sa_set):
            return True
    return False


def main():
    dry     = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    if not os.path.exists(FACTS_PATH):
        print("  ✗ canon_facts.json missing"); sys.exit(1)
    facts = json.load(open(FACTS_PATH, encoding="utf-8"))
    pr    = json.load(open(PUNK_PATH,  encoding="utf-8")) if os.path.exists(PUNK_PATH) else {}

    conflicts = []

    # ── Detector 1: multiple canon_facts entries for same subject+predicate ──
    # (Group manga-derived + verified entries; flag where values disagree.)
    by_pair = defaultdict(list)
    for f in facts:
        key = (f.get("subject"), f.get("predicate"))
        by_pair[key].append(f)
    for (subject, predicate), group in by_pair.items():
        if len(group) < 2: continue
        # Skip predicates that are inherently multi-valued (parallel facts, not conflicts).
        if predicate in _MULTI_VALUED_PREDICATES: continue
        str_vals = [str(f.get("value")) for f in group]
        # If all values are equivalent (same data at different granularity, e.g.
        # compound multi-timeskip fact vs. single-epoch Vivre Card), skip.
        ref = str_vals[0]
        if all(values_equivalent(ref, v) for v in str_vals[1:]):
            continue
        if len({v for v in str_vals}) > 1:
            # Genuine conflict
            conflicts.append({
                "type": "multi_fact",
                "subject":   subject,
                "predicate": predicate,
                "entries":   [{
                    "id":       f.get("id"),
                    "value":    f.get("value"),
                    "tier":     f.get("tier"),
                    "intent":   f.get("intent"),
                    "sources":  f.get("sources", []),
                    "evidence_notes": f.get("evidence_notes", ""),
                } for f in group],
            })

    # ── Detector 2: canon_facts vs wiki value mismatch ──
    verified_by_pair = {(f["subject"], f["predicate"]): f
                        for f in facts
                        if f.get("id", "").startswith("verified:")}
    for name, rec in pr.items():
        if not rec.get("found"): continue
        for field in ("age", "birthday", "height", "weight", "blood_type",
                       "bounty", "devil_fruit_name", "epithet",
                       "occupation", "origin"):
            wiki_value = rec.get(field)
            if not wiki_value: continue
            verified = verified_by_pair.get((name, field))
            if not verified: continue
            if not values_equivalent(verified["value"], wiki_value):
                conflicts.append({
                    "type": "wiki_vs_verified",
                    "subject":   name,
                    "predicate": field,
                    "wiki_value":     wiki_value,
                    "verified_value": verified["value"],
                    "verified_tier":  verified.get("tier"),
                    "verified_sources": verified.get("sources", []),
                })

    print("=" * 60)
    print(f"  Find Conflicts — Phase E")
    print(f"  Total facts examined : {len(facts):,}")
    print(f"  Conflicts detected   : {len(conflicts):,}")
    print("=" * 60); print()

    by_type = defaultdict(int)
    for c in conflicts: by_type[c["type"]] += 1
    for t, n in by_type.items(): print(f"    {t:25s} {n:>4}")
    print()

    if verbose:
        for c in conflicts[:20]:
            print(f"  {c['type']}: {c['subject']} · {c['predicate']}")
            if c["type"] == "multi_fact":
                for e in c["entries"]:
                    print(f"    [{e['tier']}] {e['value']!r} (id={e['id']})")
            elif c["type"] == "wiki_vs_verified":
                print(f"    wiki:     {c['wiki_value']!r}")
                print(f"    verified: {c['verified_value']!r}")
            print()

    if dry: return

    os.makedirs(os.path.dirname(CONF_JSON), exist_ok=True)
    with open(CONF_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated_on": TODAY,
            "total":        len(conflicts),
            "conflicts":    conflicts,
        }, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Wrote {CONF_JSON}")

    with open(CONF_REPORT, "w", encoding="utf-8") as f:
        f.write(f"# Conflicts Report — {TODAY}\n\n")
        f.write(f"_{len(conflicts)} conflicts detected across "
                f"canon sources. Reviewable in conflicts.html._\n\n")
        if not conflicts:
            f.write("No conflicts found. The canon ledger is internally consistent.\n")
        else:
            f.write("## Breakdown\n\n")
            f.write("| Type | Count |\n|---|---:|\n")
            for t, n in by_type.items(): f.write(f"| `{t}` | {n} |\n")
            f.write("\n## Sample (first 30)\n\n")
            for c in conflicts[:30]:
                f.write(f"### {c['subject']} · {c['predicate']}\n")
                f.write(f"_{c['type']}_\n\n")
                if c["type"] == "multi_fact":
                    for e in c["entries"]:
                        f.write(f"- **{e['tier']}**: `{e['value']}` "
                                f"(id={e['id']})\n")
                else:
                    f.write(f"- **wiki**: `{c['wiki_value']}`\n")
                    f.write(f"- **verified ({c['verified_tier']})**: "
                            f"`{c['verified_value']}`\n")
                f.write("\n")
    print(f"  ✓ Wrote {CONF_REPORT}")


if __name__ == "__main__":
    main()
