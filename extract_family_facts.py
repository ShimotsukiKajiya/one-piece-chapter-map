"""Extract family canon_facts from families.json.

Mirrors extract_manga_facts.py's pattern: derives tier-tagged canon_facts
from a curated source file. families.json is hand-curated (every edge has
a manga chapter citation), so each edge becomes a canon-tier fact.

Output: appends/updates canon_facts.json (idempotent — re-runs replace
matching IDs in place).

Per Phase F (docs/convergence-plan.md), these canon_facts then become
the cross-reference target for scripts/link_family.py.

Run:
  py extract_family_facts.py
  py extract_family_facts.py --dry-run
"""
import os, sys, json, re
from datetime import date
from collections import Counter

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR             = os.path.dirname(__file__)
FAMILIES_PATH   = os.path.join(DIR, "families.json")
CANON_FACTS     = os.path.join(DIR, "canon_facts.json")
TODAY           = date.today().isoformat()
VERIFIER        = "extract_family_facts.py v1"

# Map families.json relation strings → canonical predicate (matches the
# schema v2 family_relation enum + extract_family.py's mapping for
# round-trip consistency).
_RELATION_PREDICATE: dict[str, str | None] = {
    "father":               "father",
    "mother":               "mother",
    "grandfather":          "grandfather",
    "grandmother":          "grandmother",
    "son":                  "son",
    "daughter":             "daughter",
    "brother":              "brother",
    "sister":               "sister",
    "wife":                 "wife",
    "husband":              "husband",
    "child":                "child",
    "parent":               "parent",
    "ancestor":             "ancestor",
    "descendant":           "descendant",
    "lover":                "partner",
    "adoptive father":      "adoptive-father",
    "adoptive mother":      "adoptive-mother",
    "adoptive son":         "adoptive-son",
    "adoptive daughter":    "adoptive-daughter",
    "adoptive brother":     "adoptive-brother",
    "adoptive sister":      "adoptive-sister",
    "sworn brother":        "sworn-brother",
    "sworn sister":         "sworn-sister",
    "guardian":             "guardian",
    "guardian (childhood)": "guardian",
    # Non-family relations the shard intentionally skips. Captured as
    # canon_facts because they ARE manga claims (e.g. "Vegapunk Pythagoras
    # is a satellite of Vegapunk Stella") even though they aren't FAMILY.
    # The family shard linker won't match these (no shard rows exist),
    # but they'll be available for future shards (trains-with for mentor,
    # etc.) and for renderers that want to show them.
    "satellite":         "satellite",
    "rival (childhood)": "rival-childhood",
    "mentor":            "mentor",
    "sovereign of":      "sovereign-of",
    "alleged son":       "alleged-son",
}


def slugify(s: str) -> str:
    return re.sub(r"[^\w]+", "_", s).strip("_")[:80]


def parse_source(s: str) -> tuple[dict | None, str]:
    """Return (source_citation_dict, default_tier) from a families.json
    `source` string. Recognises 'Chapter N' (manga, canon) and falls
    back to a generic citation for non-manga sources."""
    if not s:
        return None, "speculation"
    m = re.match(r"^Chapter\s+(\d+)\s*$", s.strip(), re.IGNORECASE)
    if m:
        chapter = int(m.group(1))
        return {"type": "manga", "chapter": chapter}, "canon"
    # Non-canon source citations (e.g. "Film: Red")
    return {"type": "manual", "ref": s}, "likely"


def main() -> None:
    dry = "--dry-run" in sys.argv

    with open(FAMILIES_PATH, encoding="utf-8") as f:
        edges = json.load(f).get("edges", [])

    new_facts: list[dict] = []
    skipped: list[str] = []
    relation_counts: Counter[str] = Counter()

    for edge in edges:
        from_name = edge.get("from", "").strip()
        to_name   = edge.get("to",   "").strip()
        relation  = (edge.get("relation") or "").strip().lower()
        source    = edge.get("source", "")

        predicate = _RELATION_PREDICATE.get(relation)
        if predicate is None:
            skipped.append(f"unknown relation {relation!r}: {from_name} → {to_name}")
            continue

        src_dict, default_tier = parse_source(source)
        # 'alleged son' is a non-confirmed manga claim — even with a chapter
        # citation, downgrade to speculation per canon-policy.md.
        if predicate == "alleged-son":
            tier = "speculation"
        else:
            tier = default_tier

        fact_id = f"family:{slugify(from_name)}:{predicate}:{slugify(to_name)}"
        fact = {
            "id":        fact_id,
            "subject":   from_name,
            "predicate": predicate,
            "value":     to_name,
            "tier":      tier,
            "intent":    "serious",
            "sources":   [src_dict] if src_dict else [],
            "evidence_notes": (
                f"Hand-curated in families.json with citation '{source}'. "
                f"Subject's {predicate.replace('-', ' ')} is {to_name}."
            ),
            "verified_on": TODAY,
            "verified_by": VERIFIER,
        }
        new_facts.append(fact)
        relation_counts[predicate] += 1

    # Stats
    print("=" * 60)
    print(f"  Extract Family Facts")
    print(f"  Edges read:     {len(edges)}")
    print(f"  Facts produced: {len(new_facts)}")
    print(f"  Skipped:        {len(skipped)}")
    print("=" * 60)
    print("\n  By predicate:")
    for p, n in relation_counts.most_common():
        print(f"    {n:>3}  {p}")
    if skipped:
        print(f"\n  Skipped relations (will not be canon facts):")
        for s in skipped:
            print(f"    - {s}")

    if dry:
        print("\n  (dry run — canon_facts.json not modified)")
        return

    # Merge into canon_facts.json (idempotent — replace by ID)
    facts: list[dict] = []
    if os.path.exists(CANON_FACTS):
        with open(CANON_FACTS, encoding="utf-8") as f:
            facts = json.load(f)
    facts_by_id = {f["id"]: f for f in facts}

    new_count = 0
    replaced  = 0
    for f in new_facts:
        if f["id"] in facts_by_id:
            replaced += 1
        else:
            new_count += 1
        facts_by_id[f["id"]] = f

    merged = list(facts_by_id.values())
    text = json.dumps(merged, ensure_ascii=False, indent=2)
    tmp = CANON_FACTS + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text); f.write("\n")
    os.replace(tmp, CANON_FACTS)
    print(f"\n  ✓ Wrote {CANON_FACTS}")
    print(f"     {new_count} new, {replaced} replaced, {len(merged):,} total")


if __name__ == "__main__":
    main()
