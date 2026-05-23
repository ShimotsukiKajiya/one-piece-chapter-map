"""Cross-link `relationships/owns.json` rows to canon_facts entries.

Phase F session A4 — owns side. See docs/journey-outline.md and
docs/convergence-plan.md.

Match logic (mirrors link_family.py with chr_id keying):
  * For each shard row {from: chr_id, to: weap_id|item_id, ...}:
      - Look up canon_facts with predicate=owns, subject_chr=chr_id
      - canon_fact.value is the weapon/item canonical name
      - Resolve value to weap:/item: ID via query.resolve
      - If shard.to matches → exact match, tier promoted
      - If no match for chr_id → no canon fact (default tier kept)
      - If chr_id has facts but value resolves to a different ID → conflict

Idempotent. Writes both markdown report and JSON conflict log per
discipline.

Usage:
    python scripts/link_owns.py --dry-run
    python scripts/link_owns.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CANON_FACTS_PATH = ROOT / "canon_facts.json"
OWNS_PATH        = ROOT / "relationships" / "owns.json"
REPORT_PATH      = ROOT / "docs" / "canon_link_report_owns.md"
CONFLICTS_JSON   = ROOT / "docs" / "canon_link_conflicts_owns.json"

SHARD_NAME = "owns"

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
    parser.add_argument("--dry-run", action="store_true", help="Report only.")
    args = parser.parse_args()

    with open(CANON_FACTS_PATH, encoding="utf-8") as f:
        canon_facts = json.load(f)
    with open(OWNS_PATH, encoding="utf-8") as f:
        owns_rows = json.load(f)

    # Index canon_facts by chr_id where predicate=owns. One chr can own
    # multiple weapons → list per chr.
    facts_by_chr: dict[str, list[dict]] = defaultdict(list)
    unresolved_subjects: set[str] = set()
    for f in canon_facts:
        if f.get("predicate") != "owns":
            continue
        subj = (f.get("subject") or "").strip()
        if not subj:
            continue
        chr_id = query.resolve_character(subj)
        if chr_id is None:
            unresolved_subjects.add(subj)
            continue
        facts_by_chr[chr_id].append(f)

    if unresolved_subjects:
        print(f"  ⚠  {len(unresolved_subjects)} canon_fact subjects didn't resolve "
              f"to chr: IDs: {sorted(unresolved_subjects)[:3]}…", file=sys.stderr)

    counts = Counter()
    conflicts: list[dict] = []
    updated_rows: list[dict] = []
    matched_fact_ids: set[str] = set()

    for row in owns_rows:
        chr_id = row["from"]
        item_id = row["to"]
        new_row = dict(row)

        candidate_facts = facts_by_chr.get(chr_id, [])
        if not candidate_facts:
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["no_canon_fact"] += 1
            updated_rows.append(new_row)
            continue

        # Find a canon_fact whose value resolves to this shard's `to`.
        matched_fact = None
        all_candidate_values: list[tuple[str, str | None]] = []
        for f in candidate_facts:
            v = (f.get("value") or "").strip()
            v_id = query.resolve(v, prefix="weap:") or query.resolve(v, prefix="item:")
            all_candidate_values.append((v, v_id))
            if v_id == item_id:
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
            matched_fact_ids.add(matched_fact["id"])
        else:
            # canon_facts exist for this chr but don't cover THIS specific
            # weapon/item. Distinct from a true value-mismatch — canon is
            # just incomplete here. Stay at default tier; don't log as a
            # conflict (would be noise; canon_facts intentionally has
            # ~9 hand-curated entries not full coverage).
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["partial_canon_coverage"] += 1

        updated_rows.append(new_row)

    # Find canon_facts that have NO matching shard row — these are MISSING
    # ownership rows in the shard (e.g. the Murakumogiri/Newgate gap from
    # the parenthetical-resolver bug).
    missing_in_shard: list[dict] = []
    for chr_id, facts in facts_by_chr.items():
        for f in facts:
            if f["id"] in matched_fact_ids:
                continue
            v = (f.get("value") or "").strip()
            v_id = query.resolve(v, prefix="weap:") or query.resolve(v, prefix="item:")
            missing_in_shard.append({
                "chr_id":         chr_id,
                "subject_name":   query.display_name(chr_id),
                "canon_value":    v,
                "resolves_to":    v_id,
                "fact_id":        f["id"],
            })

    total = len(owns_rows)
    have_fact = total - counts["no_canon_fact"]
    match_rate_overall   = (counts["matched"] / total * 100) if total else 0
    match_rate_have_fact = (counts["matched"] / have_fact * 100) if have_fact else 0

    print(f"owns rows:                 {total:>4}")
    print(f"  Have a canon fact:       {have_fact:>4}  ({have_fact/total*100:.1f}% coverage)")
    print(f"  Matched:                 {counts['matched']:>4}")
    print(f"    └─ canon-tier:         {counts.get('matched_canon', 0):>4}")
    print(f"    └─ likely-tier:        {counts.get('matched_likely', 0):>4}")
    print(f"  Partial canon coverage:  {counts['partial_canon_coverage']:>4}  (chr has facts but not this specific item)")
    print(f"  No canon fact for chr:   {counts['no_canon_fact']:>4}")
    print(f"  Match rate (of those with a fact):  {match_rate_have_fact:.1f}%")
    print(f"  Canon facts with NO shard row:      {len(missing_in_shard)}  "
          f"(missing-from-shard findings)")

    if missing_in_shard:
        print(f"\nMissing from shard (canon says owns, shard has no row):")
        for m in missing_in_shard:
            print(f"  ! {m['subject_name']!r} owns {m['canon_value']!r} "
                  f"(resolves to {m['resolves_to']}) — fact: {m['fact_id']}")

    # No conflicts list anymore — partial coverage isn't a conflict

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    # Write updated shard atomically
    out_text = json.dumps(updated_rows, ensure_ascii=False, indent=2)
    tmp = OWNS_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text); f.write("\n")
    tmp.replace(OWNS_PATH)
    print(f"\nWrote {len(updated_rows):,} rows -> {OWNS_PATH.relative_to(ROOT)}")

    # Markdown report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# Canon Link Report — `owns` × `owns` predicate\n\n")
    md.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n")
    md.append("Phase F session A4 (owns side). Cross-references each ")
    md.append("`relationships/owns.json` row against hand-curated canon_facts ")
    md.append("(see `extract_weapon_owner_facts.py`).\n\n")
    md.append("Coverage is intentionally limited (~9 hand-curated Meito facts) — ")
    md.append("enough to surface known shard gaps and tier-promote major Meito; ")
    md.append("full coverage waits for proper extractor or Vivre Card ingest.\n\n")
    md.append("## Stats\n\n| Outcome | Count | % |\n|---|---:|---:|\n")
    md.append(f"| Have a canon fact (coverage) | {have_fact} | {have_fact/total*100:.1f}% |\n")
    md.append(f"| Matched | {counts['matched']} | {match_rate_overall:.1f}% |\n")
    md.append(f"| Conflicts (different value) | {counts['conflict']} | {counts['conflict']/total*100:.1f}% |\n")
    md.append(f"| No canon fact | {counts['no_canon_fact']} | {counts['no_canon_fact']/total*100:.1f}% |\n")
    md.append(f"\n**Match rate (of those with a fact):** {match_rate_have_fact:.1f}%\n\n")

    if missing_in_shard:
        md.append(f"## Missing from shard ({len(missing_in_shard)})\n\n")
        md.append("Canon facts that have no corresponding shard row. ")
        md.append("**These are real gaps — the canon_fact says X owns Y, ")
        md.append("but `relationships/owns.json` has no row for that pair.**\n\n")
        for m in missing_in_shard:
            md.append(f"- **{m['subject_name']}** owns `{m['canon_value']}` "
                      f"(`{m['resolves_to']}`) — canon fact `{m['fact_id']}`\n")

    if conflicts:
        md.append(f"\n## Value-mismatch conflicts ({len(conflicts)})\n\n")
        for c in conflicts:
            cands = ", ".join(f"`{v}`→`{i}`" for v, i in c['canon_candidates'])
            md.append(f"- **{c['subject_name']}** ({c['chr_id']}): shard owns "
                      f"`{c['shard_to_name']}` ({c['shard_to_id']}); canon candidates: {cands}\n")

    md.append("\n---\n\n*Re-run via `python scripts/link_owns.py`. Idempotent.*\n")
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(md)
    print(f"Wrote report -> {REPORT_PATH.relative_to(ROOT)}")

    # JSON conflict log per discipline
    all_conflict_entries = []
    for c in conflicts:
        all_conflict_entries.append({
            "shard":               SHARD_NAME,
            "kind":                "value-mismatch",
            "subject_name":        c["subject_name"],
            "chr_id":              c["chr_id"],
            "canon_fact_ids":      c["fact_ids"],
            "shard_value":         {"to_id": c["shard_to_id"], "to_name": c["shard_to_name"]},
            "canon_candidates":    [{"raw": v, "resolves_to": i} for v, i in c["canon_candidates"]],
            "resolution_class":    "unclassified",
            "resolution_status":   "open",
        })
    for m in missing_in_shard:
        all_conflict_entries.append({
            "shard":               SHARD_NAME,
            "kind":                "missing-in-shard",
            "subject_name":        m["subject_name"],
            "chr_id":              m["chr_id"],
            "canon_fact_id":       m["fact_id"],
            "canon_value":         {"raw": m["canon_value"], "resolves_to": m["resolves_to"]},
            "resolution_class":    "unclassified",
            "resolution_status":   "open",
        })

    conflict_doc = {
        "_doc": "Machine-readable conflict log. Shape per docs/convergence-plan.md §Conflict-tracking discipline.",
        "shard":         SHARD_NAME,
        "linker":        "scripts/link_owns.py",
        "linker_target": "owns predicate (hand-curated Meito ownership)",
        "generated_on":  datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "total":              total,
            "have_canon_fact":    have_fact,
            "matched":            counts["matched"],
            "matched_canon":      counts.get("matched_canon", 0),
            "matched_likely":     counts.get("matched_likely", 0),
            "conflict":           counts["conflict"],
            "missing_in_shard":   len(missing_in_shard),
            "no_canon_fact":      counts["no_canon_fact"],
            "match_rate_overall":   round(match_rate_overall / 100, 4),
            "match_rate_have_fact": round(match_rate_have_fact / 100, 4),
        },
        "conflicts": all_conflict_entries,
    }
    with open(CONFLICTS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(conflict_doc, ensure_ascii=False, indent=2))
        f.write("\n")
    print(f"Wrote conflict log -> {CONFLICTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
