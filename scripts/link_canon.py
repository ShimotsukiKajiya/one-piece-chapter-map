"""Cross-link relationship-shard rows to canon_facts.json entries.

This is the first step of Phase F (convergence) — see docs/convergence-plan.md.
Tags each shard row with a `tier` and (when matched) an `evidence` pointer
back to the supporting canon_facts entry.

Currently scoped to: `relationships/debuts-in.json` × canon_facts predicate
`first_appearance`. Once this proves out, the same pattern extends to the
other 6 shards.

Match logic:
  * Resolve shard row `from` (chr:N) → canonical name via query.display_name.
  * Find canon_fact with predicate=first_appearance and subject = that name
    (or any of the chr's aliases via entity_index).
  * Compare:
      - Exact: shard.to chapter == fact.value.chapter AND
                shard.appearance_type == fact.value.type
            → tier=canon, match_type=exact, evidence pointer added.
      - Partial: chapter matches but appearance_type differs
            → tier=likely, match_type=partial, conflict logged.
      - Missing: no fact for this subject
            → tier defaults per src (auto-extract → likely).

Usage:
    python scripts/link_canon.py --dry-run    # report only, no writes
    python scripts/link_canon.py              # writes the shard + report
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

# Make scripts/lib importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CANON_FACTS_PATH  = ROOT / "canon_facts.json"
DEBUTS_IN_PATH    = ROOT / "relationships" / "debuts-in.json"
REPORT_PATH       = ROOT / "docs" / "canon_link_report.md"
CONFLICTS_JSON    = ROOT / "docs" / "canon_link_conflicts_debuts-in.json"

# Shard identifier — written into the JSON conflict log so a future
# aggregator can merge across shards. See docs/convergence-plan.md
# §"Conflict-tracking discipline".
SHARD_NAME = "debuts-in"

# Default tier by src — see docs/convergence-plan.md
_DEFAULT_TIER_BY_SRC = {
    "sbs":          "canon",
    "manual":       "canon",
    "auto-extract": "likely",       # manga-derived via wiki ingest
    "wiki":         "speculation",
    "inferred":     "speculation",
}


def default_tier(src: str) -> str:
    return _DEFAULT_TIER_BY_SRC.get(src, "speculation")


def parse_chapter_int(chapter_id: str) -> int | None:
    """'ch:1037' -> 1037; bad input -> None."""
    if not chapter_id.startswith("ch:"):
        return None
    try:
        return int(chapter_id[3:])
    except ValueError:
        return None


def build_first_app_index(canon_facts: list[dict]) -> dict[str, list[dict]]:
    """Map subject_chr_id → list[first_app canon_fact] for that character.

    Multi-value list (not single fact) because alias-collapse puts multiple
    canon_facts under one chr_id: chr:01592 has both first_app:Aokiji
    (ch:569) AND first_app:Kuzan (ch:303), since each name first appeared
    in a different chapter. The shard's debut takes the EARLIEST, so the
    linker needs to consider all candidates and pick the one matching the
    shard's chapter+type.
    """
    idx: dict[str, list[dict]] = {}
    unresolved_subjects: set[str] = set()
    for f in canon_facts:
        if f.get("predicate") != "first_appearance":
            continue
        subj = (f.get("subject") or "").strip()
        if not subj:
            continue
        chr_id = query.resolve_character(subj)
        if chr_id is None:
            unresolved_subjects.add(subj)
            continue
        idx.setdefault(chr_id, []).append(f)
    if unresolved_subjects:
        print(f"  ⚠  {len(unresolved_subjects)} canon_fact subjects didn't resolve to chr: IDs "
              f"(skipped): {sorted(unresolved_subjects)[:3]}…", file=sys.stderr)
    multi = sum(1 for facts in idx.values() if len(facts) > 1)
    if multi:
        print(f"  · {multi} chr_ids have multiple first_app facts (alias-collapse cases) — "
              f"linker tries each candidate.", file=sys.stderr)
    return idx


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats but do not write the shard or report.")
    args = parser.parse_args()

    # Load inputs
    with open(CANON_FACTS_PATH, encoding="utf-8") as f:
        canon_facts = json.load(f)
    with open(DEBUTS_IN_PATH, encoding="utf-8") as f:
        debuts = json.load(f)

    first_app_by_chr = build_first_app_index(canon_facts)

    # Per-row classification + counters
    counts = Counter()
    conflicts: list[dict] = []
    no_fact_examples: list[str] = []
    matched_rows: list[dict] = []

    updated_debuts: list[dict] = []
    for row in debuts:
        chr_id = row["from"]
        # Get the canonical display name for reporting (the chr_id-keyed
        # index makes the lookup itself name-independent).
        name = query.display_name(chr_id)
        candidate_facts = first_app_by_chr.get(chr_id, [])

        # Multi-value match: try each candidate, prefer one with the same
        # chapter+type as the shard row (alias-collapse fix).
        shard_chapter = parse_chapter_int(row.get("to", ""))
        shard_type    = row.get("appearance_type", "")
        fact = None
        partial_fact = None
        for f in candidate_facts:
            v = f.get("value") or {}
            fc = v.get("chapter")
            ft = v.get("type", "")
            if shard_chapter is not None and shard_chapter == fc and shard_type == ft:
                fact = f
                break
            if shard_chapter is not None and shard_chapter == fc and partial_fact is None:
                partial_fact = f
        if fact is None and partial_fact is not None:
            fact = partial_fact  # chapter matches, type doesn't

        # Build the new row, preserving existing fields
        new_row = dict(row)

        if not candidate_facts:
            # No canon fact for this character — keep default tier
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["no_canon_fact"] += 1
            if len(no_fact_examples) < 8:
                no_fact_examples.append(name or chr_id)
        elif fact is None:
            # canon_facts exist for this chr but none match shard's chapter
            # at all → real chapter discrepancy. Pick first as reference,
            # log conflict, keep default tier.
            ref_fact = candidate_facts[0]
            v = ref_fact.get("value") or {}
            fact_chapter = v.get("chapter")
            fact_type    = v.get("type", "")
            new_row["tier"] = default_tier(row.get("src", ""))
            counts["chapter_mismatch"] += 1
            conflicts.append({
                "name":          name,
                "chr_id":        chr_id,
                "shard_chapter": shard_chapter,
                "fact_chapter":  fact_chapter,
                "shard_type":    shard_type,
                "fact_type":     fact_type,
                "fact_id":       ref_fact["id"],
                "kind":          "chapter-mismatch",
            })
        else:
            shard_chapter = parse_chapter_int(row.get("to", ""))
            fact_chapter  = (fact.get("value") or {}).get("chapter")
            fact_type     = (fact.get("value") or {}).get("type", "")

            chapter_ok = shard_chapter is not None and shard_chapter == fact_chapter
            type_ok    = shard_type == fact_type

            if chapter_ok and type_ok:
                new_row["tier"] = "canon"
                new_row["evidence"] = [{
                    "canon_fact_id": fact["id"],
                    "match_type":    "exact",
                }]
                counts["exact_match"] += 1
                matched_rows.append({"name": name, "chr_id": chr_id, "fact_id": fact["id"]})
            elif chapter_ok and not type_ok:
                new_row["tier"] = "likely"
                new_row["evidence"] = [{
                    "canon_fact_id": fact["id"],
                    "match_type":    "partial",
                }]
                counts["partial_match"] += 1
                conflicts.append({
                    "name":        name,
                    "chr_id":      chr_id,
                    "shard_type":  shard_type,
                    "fact_type":   fact_type,
                    "chapter":     shard_chapter,
                    "fact_id":     fact["id"],
                    "kind":        "type-mismatch",
                })
            else:
                # Chapter doesn't match — real conflict, don't claim canon
                new_row["tier"] = default_tier(row.get("src", ""))
                counts["chapter_mismatch"] += 1
                conflicts.append({
                    "name":          name,
                    "chr_id":        chr_id,
                    "shard_chapter": shard_chapter,
                    "fact_chapter":  fact_chapter,
                    "shard_type":    shard_type,
                    "fact_type":     fact_type,
                    "fact_id":       fact["id"],
                    "kind":          "chapter-mismatch",
                })

        updated_debuts.append(new_row)

    # Stats
    total = len(debuts)
    print(f"debuts-in rows:       {total:>5,}")
    print(f"  Exact match (canon):    {counts['exact_match']:>5,}  ({counts['exact_match']/total*100:.1f}%)")
    print(f"  Partial (likely):       {counts['partial_match']:>5,}")
    print(f"  Chapter mismatch:       {counts['chapter_mismatch']:>5,}")
    print(f"  No canon fact found:    {counts['no_canon_fact']:>5,}")

    if no_fact_examples:
        print(f"\nSample subjects with no first_app canon fact:")
        for n in no_fact_examples:
            print(f"  - {n}")

    if conflicts:
        print(f"\nConflicts (first 8):")
        for c in conflicts[:8]:
            if c["kind"] == "type-mismatch":
                print(f"  ! {c['name']!r}: shard says {c['shard_type']}, canon says {c['fact_type']} (both ch {c['chapter']})")
            else:
                print(f"  ! {c['name']!r}: shard says ch{c['shard_chapter']}/{c['shard_type']}, canon says ch{c['fact_chapter']}/{c['fact_type']}")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    # Write updated shard atomically
    out_text = json.dumps(updated_debuts, ensure_ascii=False, indent=2)
    tmp = DEBUTS_IN_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(out_text)
        f.write("\n")
    tmp.replace(DEBUTS_IN_PATH)
    print(f"\nWrote {len(updated_debuts):,} rows -> {DEBUTS_IN_PATH.relative_to(ROOT)}")

    # Write report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = []
    report.append(f"# Canon Link Report — `debuts-in` × `first_appearance`\n")
    report.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n")
    report.append(f"\nFirst convergence pass per [`convergence-plan.md`](convergence-plan.md). ")
    report.append(f"Cross-references each `relationships/debuts-in.json` row against ")
    report.append(f"`canon_facts.json` entries with predicate `first_appearance`.\n\n")
    report.append("## Stats\n\n| Outcome | Count | % |\n|---|---:|---:|\n")
    for label, key in [
        ("Exact match → tier=canon",      "exact_match"),
        ("Partial (chapter ok, type differs) → tier=likely", "partial_match"),
        ("Chapter mismatch → no upgrade", "chapter_mismatch"),
        ("No canon fact for subject → default tier", "no_canon_fact"),
    ]:
        n = counts[key]
        report.append(f"| {label} | {n:,} | {n/total*100:.1f}% |\n")
    report.append(f"\n**Total rows processed:** {total:,}\n")
    report.append(f"**Cross-link rate (canon-confirmed):** {counts['exact_match']/total*100:.1f}%\n")

    if conflicts:
        report.append(f"\n## Conflicts ({len(conflicts)})\n\n")
        report.append("Rows where shard data and canon_facts disagree. Each is a data ")
        report.append("issue worth investigating — either the shard, the canon fact, ")
        report.append("or the source data they derive from is wrong.\n\n")
        for c in conflicts[:50]:
            if c["kind"] == "type-mismatch":
                report.append(f"- **{c['name']}** ({c['chr_id']}): shard `appearance_type=\"{c['shard_type']}\"`, "
                              f"canon `value.type=\"{c['fact_type']}\"` (chapter {c['chapter']}); "
                              f"fact: `{c['fact_id']}`\n")
            else:
                report.append(f"- **{c['name']}** ({c['chr_id']}): shard says ch{c['shard_chapter']}/{c['shard_type']}, "
                              f"canon says ch{c['fact_chapter']}/{c['fact_type']}; fact: `{c['fact_id']}`\n")
        if len(conflicts) > 50:
            report.append(f"\n_…and {len(conflicts) - 50} more._\n")

    if no_fact_examples:
        report.append(f"\n## Subjects without `first_app` canon facts\n\n")
        report.append(f"{counts['no_canon_fact']} debut rows reference characters who don't ")
        report.append(f"have a `first_app:*` entry in `canon_facts.json`. Examples:\n\n")
        for n in no_fact_examples:
            report.append(f"- {n}\n")

    report.append("\n---\n\n*Re-run via `python scripts/link_canon.py`. Re-runs are idempotent.*\n")

    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(report)
    print(f"Wrote report -> {REPORT_PATH.relative_to(ROOT)}")

    # ── Machine-readable conflict log ────────────────────────────────
    # Per the conflict-tracking discipline (see docs/convergence-plan.md
    # §"Conflict-tracking discipline"), every linker writes a structured
    # JSON log alongside its human-readable markdown. A future aggregator
    # (`scripts/aggregate_conflicts.py`) will merge these across shards
    # into one triage surface.
    conflict_doc = {
        "_doc": (
            "Machine-readable conflict log for one cross-link pass. "
            "Shape per docs/convergence-plan.md §Conflict-tracking discipline."
        ),
        "shard":         SHARD_NAME,
        "linker":        "scripts/link_canon.py",
        "linker_target": "first_appearance",
        "generated_on":  datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "total":            total,
            "exact_match":      counts["exact_match"],
            "partial_match":    counts["partial_match"],
            "chapter_mismatch": counts["chapter_mismatch"],
            "no_canon_fact":    counts["no_canon_fact"],
            "match_rate":       round(counts["exact_match"] / total, 4) if total else 0.0,
        },
        "conflicts": [
            {
                "shard":             SHARD_NAME,
                "kind":              c["kind"],
                "subject_name":      c.get("name"),
                "chr_id":            c.get("chr_id"),
                "canon_fact_id":     c.get("fact_id"),
                "shard_chapter":     c.get("shard_chapter") or c.get("chapter"),
                "fact_chapter":      c.get("fact_chapter") or c.get("chapter"),
                "shard_appearance_type": c.get("shard_type"),
                "fact_appearance_type":  c.get("fact_type"),
                # `resolution_class` and `resolution_status` are placeholders.
                # `resolution_class`: auto-resolvable | needs-human | unclassified
                # `resolution_status`: open | acknowledged | resolved | dismissed
                # Future tooling (a triage surface) updates these; the linker
                # does not classify automatically yet — surfacing the data
                # is enough for the first pass.
                "resolution_class":  "unclassified",
                "resolution_status": "open",
            }
            for c in conflicts
        ],
    }
    text = json.dumps(conflict_doc, ensure_ascii=False, indent=2)
    with open(CONFLICTS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")
    print(f"Wrote conflict log -> {CONFLICTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
