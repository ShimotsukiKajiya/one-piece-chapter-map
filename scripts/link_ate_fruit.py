"""Cross-link `relationships/ate-fruit.json` rows to canon_facts entries.

Second convergence pass per docs/convergence-plan.md (Phase F).
Mirrors scripts/link_canon.py but matches against canon_facts predicate
`devil_fruit_name` (32 facts produced by verify.py v3 from SBS confirmations).

Match logic:
  * Resolve shard.from (chr_id) → canonical name via query.display_name.
  * Find canon_fact with predicate=devil_fruit_name and that subject.
  * canon_fact.value is a string ("Yomi Yomi no Mi" or composite like
    "Gomu Gomu no Mi · (Hito Hito no Mi, Model: Nika)" with " · " separator).
  * Resolve EACH name in the value to a fruit_id via query.resolve.
    If ANY of them matches shard.to → exact match.
  * Mismatch (canon fact has different fruit) → conflict.

Per docs/convergence-plan.md §"Conflict-tracking discipline": writes
docs/canon_link_conflicts_ate-fruit.json (machine-readable) alongside
the markdown report. Ship gate: ≥95% of rows that HAVE a canon fact
should match. (Coverage — what fraction have a canon fact at all — is
a separate measure: canon_facts is thin on devil_fruit_name compared to
the 135 ate-fruit rows, so most rows will have no canon fact and stay
at default tier.)

Usage:
    python scripts/link_ate_fruit.py --dry-run
    python scripts/link_ate_fruit.py
"""
from __future__ import annotations

import argparse
import json
import re
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
ATE_FRUIT_PATH   = ROOT / "relationships" / "ate-fruit.json"
REPORT_PATH      = ROOT / "docs" / "canon_link_report_ate-fruit.md"
CONFLICTS_JSON   = ROOT / "docs" / "canon_link_conflicts_ate-fruit.json"

SHARD_NAME = "ate-fruit"

# Same default-tier-by-src table as link_canon.py.
# TODO: when a 3rd linker arrives, extract this + helpers into scripts/lib/canon_link.py
_DEFAULT_TIER_BY_SRC = {
    "sbs":          "canon",
    "manual":       "canon",
    "auto-extract": "likely",
    "wiki":         "speculation",   # ← ate-fruit uses src=wiki
    "inferred":     "speculation",
}

def default_tier(src: str) -> str:
    return _DEFAULT_TIER_BY_SRC.get(src, "speculation")


def split_fruit_value(value: str) -> list[str]:
    """canon_fact.value can be a single name or a composite like
    'Gomu Gomu no Mi · (Hito Hito no Mi, Model: Nika)'. Split on ' · '
    and strip surrounding parens. Returns the list of candidate fruit
    names; any one matching the shard's fruit_id counts as a match."""
    if not value:
        return []
    parts: list[str] = []
    for chunk in re.split(r"\s+·\s+", value):
        chunk = chunk.strip()
        # Strip enclosing parens if the whole chunk is "(X)"
        if chunk.startswith("(") and chunk.endswith(")"):
            chunk = chunk[1:-1].strip()
        if chunk:
            parts.append(chunk)
    return parts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report only, no writes.")
    args = parser.parse_args()

    with open(CANON_FACTS_PATH, encoding="utf-8") as f:
        canon_facts = json.load(f)
    with open(ATE_FRUIT_PATH, encoding="utf-8") as f:
        ate_fruits = json.load(f)

    # Build subject -> fact for predicate=devil_fruit_name
    # Index by subject_chr_id (not name string) so alias variants resolve
    # cleanly. Same architectural pattern as link_family.py.
    fact_by_chr: dict[str, dict] = {}
    unresolved_subjects: set[str] = set()
    for f in canon_facts:
        if f.get("predicate") != "devil_fruit_name":
            continue
        subj = (f.get("subject") or "").strip()
        if not subj:
            continue
        chr_id_subj = query.resolve_character(subj)
        if chr_id_subj is None:
            unresolved_subjects.add(subj)
            continue
        if chr_id_subj not in fact_by_chr:
            fact_by_chr[chr_id_subj] = f

    if unresolved_subjects:
        print(f"  ⚠  {len(unresolved_subjects)} canon_fact subjects didn't resolve "
              f"to chr: IDs (skipped): {sorted(unresolved_subjects)[:3]}…",
              file=sys.stderr)

    counts = Counter()
    conflicts: list[dict] = []
    updated_rows: list[dict] = []
    no_fact_examples: list[str] = []

    for row in ate_fruits:
        chr_id  = row["from"]
        fruit_id = row["to"]
        name    = query.display_name(chr_id)
        new_row = dict(row)

        fact = fact_by_chr.get(chr_id)

        if fact is None:
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["no_canon_fact"] += 1
            if name and len(no_fact_examples) < 8:
                no_fact_examples.append(name)
            updated_rows.append(new_row)
            continue

        # Resolve each candidate name in the canon_fact value to a fruit_id
        candidates = split_fruit_value(fact.get("value", ""))
        candidate_fruit_ids: list[str | None] = []
        for c in candidates:
            resolved = query.resolve(c, prefix="fruit:")
            candidate_fruit_ids.append(resolved)

        if fruit_id in candidate_fruit_ids:
            # Match — promote tier per the canon_fact's own tier
            # (canon_facts already encode 'canon' vs 'likely' from verify.py)
            promoted_tier = fact.get("tier", "canon")
            new_row["tier"] = promoted_tier
            new_row["evidence"] = [{
                "canon_fact_id": fact["id"],
                "match_type":    "exact",
            }]
            counts["matched"] += 1
            counts[f"matched_{promoted_tier}"] += 1
        else:
            # Conflict — canon fact says a DIFFERENT fruit for this character
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["conflict"] += 1
            conflicts.append({
                "name":              name,
                "chr_id":            chr_id,
                "shard_fruit_id":    fruit_id,
                "shard_fruit_name":  query.display_name(fruit_id),
                "canon_value":       fact.get("value"),
                "canon_resolved_to": candidate_fruit_ids,
                "fact_id":           fact["id"],
                "kind":              "fruit-mismatch",
            })

        updated_rows.append(new_row)

    total = len(ate_fruits)
    have_fact = total - counts["no_canon_fact"]
    match_rate_overall   = (counts["matched"] / total * 100) if total else 0
    match_rate_have_fact = (counts["matched"] / have_fact * 100) if have_fact else 0

    print(f"ate-fruit rows:              {total:>4}")
    print(f"  Have a canon fact:         {have_fact:>4}  ({have_fact/total*100:.1f}% coverage)")
    print(f"  Matched (canon/likely):    {counts['matched']:>4}")
    print(f"    └─ canon-tier:           {counts.get('matched_canon', 0):>4}")
    print(f"    └─ likely-tier:          {counts.get('matched_likely', 0):>4}")
    print(f"  Conflicts:                 {counts['conflict']:>4}")
    print(f"  No canon fact found:       {counts['no_canon_fact']:>4}")
    print(f"  Match rate (of those with a fact):  {match_rate_have_fact:.1f}%")
    print(f"  Match rate (overall):               {match_rate_overall:.1f}%")

    if conflicts:
        print(f"\nConflicts (first 5):")
        for c in conflicts[:5]:
            print(f"  ! {c['name']!r}: shard says {c['shard_fruit_name']} ({c['shard_fruit_id']}), "
                  f"canon says {c['canon_value']!r}")

    if no_fact_examples:
        print(f"\nSample subjects without devil_fruit_name canon facts:")
        for n in no_fact_examples:
            print(f"  - {n}")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    # Write updated shard atomically
    out_text = json.dumps(updated_rows, ensure_ascii=False, indent=2)
    tmp = ATE_FRUIT_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text); f.write("\n")
    tmp.replace(ATE_FRUIT_PATH)
    print(f"\nWrote {len(updated_rows):,} rows -> {ATE_FRUIT_PATH.relative_to(ROOT)}")

    # Markdown report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append(f"# Canon Link Report — `ate-fruit` × `devil_fruit_name`\n\n")
    md.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n")
    md.append(f"Second convergence pass per [`convergence-plan.md`](convergence-plan.md). ")
    md.append(f"Cross-references each `relationships/ate-fruit.json` row against ")
    md.append(f"`canon_facts.json` entries with predicate `devil_fruit_name`.\n\n")
    md.append("## Stats\n\n| Outcome | Count | % |\n|---|---:|---:|\n")
    md.append(f"| Have a canon fact (coverage) | {have_fact} | {have_fact/total*100:.1f}% |\n")
    md.append(f"| Matched (any tier) | {counts['matched']} | {match_rate_overall:.1f}% |\n")
    md.append(f"| └─ matched at canon tier | {counts.get('matched_canon', 0)} | {counts.get('matched_canon', 0)/total*100:.1f}% |\n")
    md.append(f"| └─ matched at likely tier | {counts.get('matched_likely', 0)} | {counts.get('matched_likely', 0)/total*100:.1f}% |\n")
    md.append(f"| Conflicts | {counts['conflict']} | {counts['conflict']/total*100:.1f}% |\n")
    md.append(f"| No canon fact for subject | {counts['no_canon_fact']} | {counts['no_canon_fact']/total*100:.1f}% |\n")
    md.append(f"\n**Total rows:** {total}\n")
    md.append(f"**Match rate (of those with a fact):** {match_rate_have_fact:.1f}%\n\n")
    md.append("> Note: most ate-fruit rows currently have no `devil_fruit_name` canon fact ")
    md.append("(only 32 such facts exist; verify.py v3 will add more as SBS coverage grows). ")
    md.append("These rows correctly stay at default tier (`speculation` since src=`wiki`).\n\n")

    if conflicts:
        md.append(f"## Conflicts ({len(conflicts)})\n\n")
        md.append("Rows where the shard and canon_fact assign different fruits to the same character.\n\n")
        for c in conflicts[:50]:
            md.append(f"- **{c['name']}** ({c['chr_id']}): shard `{c['shard_fruit_name']}` "
                      f"({c['shard_fruit_id']}); canon value `{c['canon_value']!r}`; "
                      f"fact: `{c['fact_id']}`\n")
        if len(conflicts) > 50:
            md.append(f"\n_…and {len(conflicts) - 50} more._\n")

    md.append("\n---\n\n*Re-run via `python scripts/link_ate_fruit.py`. Idempotent.*\n")

    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(md)
    print(f"Wrote report -> {REPORT_PATH.relative_to(ROOT)}")

    # JSON conflict log (per discipline)
    conflict_doc = {
        "_doc": "Machine-readable conflict log for one cross-link pass. Shape per docs/convergence-plan.md §Conflict-tracking discipline.",
        "shard":         SHARD_NAME,
        "linker":        "scripts/link_ate_fruit.py",
        "linker_target": "devil_fruit_name",
        "generated_on":  datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "total":              total,
            "have_canon_fact":    have_fact,
            "matched":            counts["matched"],
            "matched_canon":      counts.get("matched_canon", 0),
            "matched_likely":     counts.get("matched_likely", 0),
            "conflict":           counts["conflict"],
            "no_canon_fact":      counts["no_canon_fact"],
            "match_rate_overall":   round(match_rate_overall / 100, 4),
            "match_rate_have_fact": round(match_rate_have_fact / 100, 4),
        },
        "conflicts": [
            {
                "shard":               SHARD_NAME,
                "kind":                c["kind"],
                "subject_name":        c["name"],
                "chr_id":              c["chr_id"],
                "canon_fact_id":       c["fact_id"],
                "shard_value":         {"fruit_id": c["shard_fruit_id"],
                                         "fruit_name": c["shard_fruit_name"]},
                "fact_value":          {"raw": c["canon_value"],
                                         "resolved_fruit_ids": c["canon_resolved_to"]},
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
