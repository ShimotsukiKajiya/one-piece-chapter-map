"""Cross-link `relationships/family.json` rows to canon_facts entries.

Third convergence pass per docs/convergence-plan.md (Phase F).

Match logic:
  * For each shard row {from: chr_id_A, to: chr_id_B, relation: REL}:
      - Resolve A → name_A, B → name_B via query.display_name.
      - Look up canon_fact with subject=name_A, predicate=REL, value=name_B.
      - If found and value resolves back to chr_id_B → exact match.
      - Tier promoted from canon_fact.

Per docs/convergence-plan.md §"Conflict-tracking discipline": writes
both markdown report and machine-readable JSON conflict log.

Usage:
    python scripts/link_family.py --dry-run
    python scripts/link_family.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CANON_FACTS_PATH = ROOT / "canon_facts.json"
FAMILY_PATH      = ROOT / "relationships" / "family.json"
REPORT_PATH      = ROOT / "docs" / "canon_link_report_family.md"
CONFLICTS_JSON   = ROOT / "docs" / "canon_link_conflicts_family.json"

SHARD_NAME = "family"

# Same default-tier-by-src table as the other linkers.
# TODO: extract into scripts/lib/canon_link.py once we have a 4th linker.
_DEFAULT_TIER_BY_SRC = {
    "sbs":          "canon",
    "manual":       "canon",
    "auto-extract": "likely",
    "wiki":         "speculation",
    "inferred":     "speculation",
}

def default_tier(src: str) -> str:
    return _DEFAULT_TIER_BY_SRC.get(src, "speculation")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only, no writes.")
    args = parser.parse_args()

    with open(CANON_FACTS_PATH, encoding="utf-8") as f:
        canon_facts = json.load(f)
    with open(FAMILY_PATH, encoding="utf-8") as f:
        family_rows = json.load(f)

    # Index canon_facts by (subject_lower, predicate). One subject can have
    # multiple family relations, so we index ALL family-flavoured facts
    # under that subject and match by predicate later.
    family_predicates = {
        "father", "mother", "parent",
        "son", "daughter", "child",
        "brother", "sister", "sibling",
        "half-sibling", "foster-sibling",
        "grandfather", "grandmother", "grandparent",
        "grandson", "granddaughter", "grandchild",
        "wife", "husband", "spouse", "partner",
        "uncle", "aunt", "uncle-aunt",
        "nephew", "niece", "niece-nephew",
        "cousin", "in-law",
        "adoptive-father", "adoptive-mother", "adopted-by",
        "adoptive-son", "adoptive-daughter", "adopted-child",
        "adoptive-brother", "adoptive-sister",
        "ancestor", "descendant",
        "sworn-brother", "sworn-sister", "sworn-sibling",
        "guardian",
    }
    # Index by (subject_chr_id, predicate) → LIST of facts.
    # Two reasons to use chr_id instead of name string:
    #   1. Multi-value: a subject can have several values for the same
    #      predicate (Luffy has two sworn-brothers; Big Mom has many children)
    #   2. Alias collapse: families.json may say "Vinsmoke Sanji" while
    #      punk_records canonicalizes to "Sanji". Both resolve to the same
    #      chr_id via the entity_index.
    # Subjects that don't resolve to a chr: ID are skipped (logged once below).
    from collections import defaultdict as _dd
    facts_by_chr_pred: dict[tuple[str, str], list[dict]] = _dd(list)
    unresolved_subjects: set[str] = set()
    for f in canon_facts:
        pred = f.get("predicate", "")
        if pred not in family_predicates:
            continue
        subj = (f.get("subject") or "").strip()
        if not subj:
            continue
        subj_chr = query.resolve_character(subj)
        if subj_chr is None:
            unresolved_subjects.add(subj)
            continue
        facts_by_chr_pred[(subj_chr, pred)].append(f)

    if unresolved_subjects:
        print(f"  ⚠  {len(unresolved_subjects)} canon_fact subjects didn't resolve to chr: IDs: "
              f"{sorted(unresolved_subjects)[:3]}…", file=sys.stderr)

    counts = Counter()
    conflicts: list[dict] = []
    updated_rows: list[dict] = []

    for row in family_rows:
        from_id  = row["from"]
        to_id    = row["to"]
        relation = row["relation"]
        new_row  = dict(row)

        from_name = query.display_name(from_id)
        to_name   = query.display_name(to_id)

        candidate_facts = facts_by_chr_pred.get((from_id, relation), [])

        if not candidate_facts:
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["no_canon_fact"] += 1
            updated_rows.append(new_row)
            continue

        # Find a canon_fact whose value resolves to this shard row's `to`.
        matched_fact = None
        all_candidate_values: list[tuple[str, str | None]] = []
        for f in candidate_facts:
            v = (f.get("value") or "").strip()
            v_id = query.resolve_character(v) if v else None
            all_candidate_values.append((v, v_id))
            if v_id == to_id:
                matched_fact = f
                break

        if matched_fact is not None:
            promoted = matched_fact.get("tier", "canon")
            new_row["tier"] = promoted
            new_row["evidence"] = [{
                "canon_fact_id": matched_fact["id"],
                "match_type":    "exact",
            }]
            counts["matched"] += 1
            counts[f"matched_{promoted}"] += 1
        else:
            # No canon_fact in the (subject, predicate) bucket points at
            # this `to` — true conflict (or shard has data canon_facts lack)
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["conflict"] += 1
            conflicts.append({
                "from_name":         from_name,
                "from_id":           from_id,
                "relation":          relation,
                "shard_to_name":     to_name,
                "shard_to_id":       to_id,
                "canon_candidates":  all_candidate_values,
                "fact_ids":          [f["id"] for f in candidate_facts],
                "kind":              "value-mismatch",
            })

        updated_rows.append(new_row)

    total = len(family_rows)
    have_fact = total - counts["no_canon_fact"]
    match_rate_overall   = (counts["matched"] / total * 100) if total else 0
    match_rate_have_fact = (counts["matched"] / have_fact * 100) if have_fact else 0

    print(f"family rows:               {total:>4}")
    print(f"  Have a canon fact:       {have_fact:>4}  ({have_fact/total*100:.1f}% coverage)")
    print(f"  Matched:                 {counts['matched']:>4}")
    print(f"    └─ canon-tier:         {counts.get('matched_canon', 0):>4}")
    print(f"    └─ likely-tier:        {counts.get('matched_likely', 0):>4}")
    print(f"    └─ speculation-tier:   {counts.get('matched_speculation', 0):>4}")
    print(f"  Conflicts:               {counts['conflict']:>4}")
    print(f"  No canon fact found:     {counts['no_canon_fact']:>4}")
    print(f"  Match rate (of those with a fact):  {match_rate_have_fact:.1f}%")
    print(f"  Match rate (overall):               {match_rate_overall:.1f}%")

    if conflicts:
        print(f"\nConflicts (first 5):")
        for c in conflicts[:5]:
            cands = ", ".join(f"{v!r}→{i}" for v, i in c["canon_candidates"])
            print(f"  ! {c['from_name']!r} {c['relation']} {c['shard_to_name']!r} ({c['shard_to_id']}); "
                  f"canon candidates: {cands}")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    # Write updated shard atomically
    out_text = json.dumps(updated_rows, ensure_ascii=False, indent=2)
    tmp = FAMILY_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text); f.write("\n")
    tmp.replace(FAMILY_PATH)
    print(f"\nWrote {len(updated_rows):,} rows -> {FAMILY_PATH.relative_to(ROOT)}")

    # Markdown report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append(f"# Canon Link Report — `family` × family-relation predicates\n\n")
    md.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n")
    md.append("Third convergence pass per [`convergence-plan.md`](convergence-plan.md). ")
    md.append("Cross-references each `relationships/family.json` row against ")
    md.append("`canon_facts.json` entries with family-flavoured predicates ")
    md.append("(`father`, `mother`, `son`, `sworn-brother`, `guardian`, etc.).\n\n")
    md.append("Family canon_facts are derived from `families.json` by ")
    md.append("`extract_family_facts.py` — same source as the shard, so a high ")
    md.append("match rate is expected. The cross-link's value here is **tier ")
    md.append("propagation** (the shard inherits canon-tier from the canon_fact's ")
    md.append("manga citation) rather than discovering new agreement.\n\n")
    md.append("## Stats\n\n| Outcome | Count | % |\n|---|---:|---:|\n")
    md.append(f"| Have a canon fact (coverage) | {have_fact} | {have_fact/total*100:.1f}% |\n")
    md.append(f"| Matched (any tier) | {counts['matched']} | {match_rate_overall:.1f}% |\n")
    md.append(f"| └─ matched at canon tier | {counts.get('matched_canon', 0)} | {counts.get('matched_canon', 0)/total*100:.1f}% |\n")
    md.append(f"| └─ matched at likely tier | {counts.get('matched_likely', 0)} | {counts.get('matched_likely', 0)/total*100:.1f}% |\n")
    md.append(f"| └─ matched at speculation tier | {counts.get('matched_speculation', 0)} | {counts.get('matched_speculation', 0)/total*100:.1f}% |\n")
    md.append(f"| Conflicts | {counts['conflict']} | {counts['conflict']/total*100:.1f}% |\n")
    md.append(f"| No canon fact for subject+predicate | {counts['no_canon_fact']} | {counts['no_canon_fact']/total*100:.1f}% |\n")
    md.append(f"\n**Total rows:** {total}\n")
    md.append(f"**Match rate (of those with a fact):** {match_rate_have_fact:.1f}%\n\n")

    if conflicts:
        md.append(f"## Conflicts ({len(conflicts)})\n\n")
        md.append("Rows where the shard and canon_fact assign different values to the same (subject, predicate) pair.\n\n")
        for c in conflicts[:50]:
            cands_str = ", ".join(f"`{v!r}`→`{i}`" for v, i in c["canon_candidates"])
            md.append(f"- **{c['from_name']}** `{c['relation']}` `{c['shard_to_name']}` ({c['shard_to_id']}); "
                      f"canon candidates: {cands_str}\n")
        if len(conflicts) > 50:
            md.append(f"\n_…and {len(conflicts) - 50} more._\n")

    md.append("\n---\n\n*Re-run via `python scripts/link_family.py`. Idempotent.*\n")
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(md)
    print(f"Wrote report -> {REPORT_PATH.relative_to(ROOT)}")

    # JSON conflict log
    conflict_doc = {
        "_doc": "Machine-readable conflict log. Shape per docs/convergence-plan.md §Conflict-tracking discipline.",
        "shard":         SHARD_NAME,
        "linker":        "scripts/link_family.py",
        "linker_target": "family-relation predicates (father/mother/sibling/...)",
        "generated_on":  datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "total":              total,
            "have_canon_fact":    have_fact,
            "matched":            counts["matched"],
            "matched_canon":      counts.get("matched_canon", 0),
            "matched_likely":     counts.get("matched_likely", 0),
            "matched_speculation": counts.get("matched_speculation", 0),
            "conflict":           counts["conflict"],
            "no_canon_fact":      counts["no_canon_fact"],
            "match_rate_overall":   round(match_rate_overall / 100, 4),
            "match_rate_have_fact": round(match_rate_have_fact / 100, 4),
        },
        "conflicts": [
            {
                "shard":               SHARD_NAME,
                "kind":                c["kind"],
                "subject_name":        c["from_name"],
                "from_id":             c["from_id"],
                "relation":            c["relation"],
                "canon_fact_ids":      c["fact_ids"],
                "shard_value":         {"to_id": c["shard_to_id"], "to_name": c["shard_to_name"]},
                "canon_candidates":    [{"raw": v, "resolves_to": i} for v, i in c["canon_candidates"]],
                "resolution_class":    "unclassified",
                "resolution_status":   "open",
            }
            for c in conflicts
        ],
    }
    with open(CONFLICTS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(conflict_doc, ensure_ascii=False, indent=2))
        f.write("\n")
    print(f"Wrote conflict log -> {CONFLICTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
