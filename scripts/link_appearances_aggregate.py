"""Aggregate cross-validation: appears-in shard ⨯ canon_fact appearance counts.

Phase F session A3 per docs/journey-outline.md. Different shape from the
previous three linkers — instead of per-row tier propagation, this one
sums shard rows per character and compares against the canon_fact value
for that character.

Why this is the strongest convergence proof yet
-----------------------------------------------
Both sides derive INDEPENDENTLY from appearances.csv:
  * relationships/appears-in.json — built by scripts/extract_appears_in.py
  * canon_facts.json `total_appearance_count` etc. — built by extract_manga_facts.py
If they disagree, ONE of them has a bug or the underlying CSV has been
re-scraped between their runs. If they agree, both extractors are
validated against each other.

Predicates checked
------------------
  total_appearance_count       count of distinct chapters per chr
  flashback_count              count of distinct chapters with type=flashback
  cover_appearance_count       count of distinct chapters with type=cover
  silhouette_appearance_count  count of distinct chapters with type=silhouette

We do NOT modify appears-in.json — this is a validator, not a tier
propagator. Per-row tier on 26.7k rows is mostly noise (every row would
say "tier=canon" since they all derive from the same manga source); the
useful question is "do the sums agree?"

Outputs:
  docs/canon_link_report_appears-in.md       human-readable
  docs/canon_link_conflicts_appears-in.json  machine-readable, per
                                              discipline in convergence-plan.md

Usage:
    python scripts/link_appearances_aggregate.py --dry-run
    python scripts/link_appearances_aggregate.py
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
APPEARS_IN_PATH  = ROOT / "relationships" / "appears-in.json"
REPORT_PATH      = ROOT / "docs" / "canon_link_report_appears-in.md"
CONFLICTS_JSON   = ROOT / "docs" / "canon_link_conflicts_appears-in.json"

SHARD_NAME = "appears-in"

# (canon_fact predicate, appearance_type filter for shard rows)
PREDICATES = [
    ("total_appearance_count",       None),         # all rows
    ("flashback_count",              "flashback"),
    ("cover_appearance_count",       "cover"),
    ("silhouette_appearance_count",  "silhouette"),
]


def parse_chapter_int(s: str) -> int | None:
    if not s.startswith("ch:"):
        return None
    try:
        return int(s[3:])
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only.")
    args = parser.parse_args()

    with open(CANON_FACTS_PATH, encoding="utf-8") as f:
        canon_facts = json.load(f)
    with open(APPEARS_IN_PATH, encoding="utf-8") as f:
        appears_rows = json.load(f)

    # Index canon_facts by (chr_id, predicate) → LIST of facts.
    # Multi-value because alias-collapse: chr:01592 has both
    # total_app:Aokiji (value=1, just Aokiji-named appearances) AND
    # total_app:Kuzan (value=58). The shard correctly unifies these
    # under one chr_id, so its count is 59. To match, the canon side
    # must SUM across all aliases of the same chr_id.
    facts_by_chr_pred: dict[tuple[str, str], list[dict]] = defaultdict(list)
    unresolved_subjects: set[str] = set()
    target_predicates = {p for p, _ in PREDICATES}
    for f in canon_facts:
        pred = f.get("predicate", "")
        if pred not in target_predicates:
            continue
        subj = (f.get("subject") or "").strip()
        if not subj:
            continue
        chr_id = query.resolve_character(subj)
        if chr_id is None:
            unresolved_subjects.add(subj)
            continue
        facts_by_chr_pred[(chr_id, pred)].append(f)

    if unresolved_subjects:
        print(f"  ⚠  {len(unresolved_subjects)} canon_fact subjects didn't resolve "
              f"to chr: IDs: {sorted(unresolved_subjects)[:3]}…", file=sys.stderr)

    # Aggregate shard rows: for each chr_id, distinct chapter sets per type.
    # We use sets because the canon_fact counts are "distinct chapters",
    # not "distinct (chapter, type) rows".
    chr_chapters: dict[str, set[int]] = defaultdict(set)
    chr_chapters_by_type: dict[tuple[str, str], set[int]] = defaultdict(set)

    for row in appears_rows:
        chr_id = row.get("from")
        chap_int = parse_chapter_int(row.get("to", ""))
        ap_type = row.get("appearance_type", "")
        if not chr_id or chap_int is None or not ap_type:
            continue
        chr_chapters[chr_id].add(chap_int)
        chr_chapters_by_type[(chr_id, ap_type)].add(chap_int)

    # Per-predicate validation
    summary: dict[str, dict] = {}
    conflicts_per_pred: dict[str, list[dict]] = {p: [] for p, _ in PREDICATES}
    no_canon_per_pred: dict[str, int] = {p: 0 for p, _ in PREDICATES}

    for predicate, type_filter in PREDICATES:
        agree = 0
        disagree = 0
        no_canon = 0
        # All chr_ids present on either side (shard-side or canon-side)
        if type_filter is None:
            shard_chr_ids = set(chr_chapters.keys())
        else:
            shard_chr_ids = {c for (c, t) in chr_chapters_by_type if t == type_filter}
        canon_chr_ids = {chr_id for (chr_id, p) in facts_by_chr_pred if p == predicate}

        all_chr = shard_chr_ids | canon_chr_ids

        for chr_id in all_chr:
            shard_count = (
                len(chr_chapters.get(chr_id, set()))
                if type_filter is None
                else len(chr_chapters_by_type.get((chr_id, type_filter), set()))
            )
            facts = facts_by_chr_pred.get((chr_id, predicate), [])
            if not facts:
                if shard_count > 0:
                    no_canon += 1
                continue
            # Sum across all alias canon_facts for this chr (so chr:01592's
            # total = total_app:Aokiji + total_app:Kuzan = 1 + 58 = 59,
            # matching shard's unified count).
            canon_count = sum(f.get("value", 0) for f in facts)
            ref_fact_id = facts[0]["id"]

            if shard_count == canon_count:
                agree += 1
            else:
                disagree += 1
                conflicts_per_pred[predicate].append({
                    "chr_id":       chr_id,
                    "subject_name": query.display_name(chr_id),
                    "shard_count":  shard_count,
                    "canon_count":  canon_count,
                    "delta":        shard_count - canon_count,
                    "fact_id":      ref_fact_id,
                    "fact_count":   len(facts),
                })

        no_canon_per_pred[predicate] = no_canon
        total_with_fact = agree + disagree
        agreement_rate = (agree / total_with_fact * 100) if total_with_fact else 0
        summary[predicate] = {
            "agree":             agree,
            "disagree":          disagree,
            "no_canon_fact":     no_canon,
            "total_with_fact":   total_with_fact,
            "agreement_rate":    agreement_rate,
        }

    # Print summary
    print(f"\nAppearances aggregate cross-validation\n")
    print(f"{'predicate':<32} {'agree':>7} {'disagree':>9} {'no-fact':>8} {'rate':>8}")
    print("-" * 70)
    for p, _ in PREDICATES:
        s = summary[p]
        print(f"{p:<32} {s['agree']:>7,} {s['disagree']:>9,} {s['no_canon_fact']:>8,} "
              f"{s['agreement_rate']:>7.1f}%")

    # Sample biggest deltas per predicate
    print(f"\nLargest deltas (top 5 per predicate):")
    for p, _ in PREDICATES:
        if conflicts_per_pred[p]:
            top = sorted(conflicts_per_pred[p], key=lambda c: abs(c["delta"]), reverse=True)[:5]
            print(f"\n  {p}:")
            for c in top:
                print(f"    {c['subject_name']:<30s} shard={c['shard_count']:>4}  "
                      f"canon={c['canon_count']:>4}  Δ={c['delta']:+}")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    # Markdown report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    md = []
    md.append("# Canon Link Report — `appears-in` aggregate cross-validation\n\n")
    md.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n\n")
    md.append("Aggregate cross-check per [`convergence-plan.md`](convergence-plan.md). ")
    md.append("Both sides derive independently from `appearances.csv`:\n\n")
    md.append("- shard side: per-row counts from `relationships/appears-in.json`\n")
    md.append("- canon side: `total_appearance_count` and per-type counts in `canon_facts.json`\n\n")
    md.append("Disagreement indicates either a divergent re-scrape between the two ")
    md.append("extractors, a counting bug in one of them, or a real data quality issue ")
    md.append("worth investigating.\n\n")

    md.append("## Stats per predicate\n\n")
    md.append("| Predicate | Agree | Disagree | No canon fact | Agreement rate |\n")
    md.append("|---|---:|---:|---:|---:|\n")
    for p, _ in PREDICATES:
        s = summary[p]
        md.append(f"| {p} | {s['agree']:,} | {s['disagree']:,} | {s['no_canon_fact']:,} | "
                  f"{s['agreement_rate']:.1f}% |\n")

    for p, _ in PREDICATES:
        if conflicts_per_pred[p]:
            md.append(f"\n## Disagreements: {p} ({len(conflicts_per_pred[p])})\n\n")
            top = sorted(conflicts_per_pred[p], key=lambda c: abs(c["delta"]), reverse=True)
            md.append("| Character | Shard count | Canon count | Δ | canon_fact_id |\n")
            md.append("|---|---:|---:|---:|---|\n")
            for c in top[:50]:
                md.append(f"| {c['subject_name']} ({c['chr_id']}) | {c['shard_count']:,} | "
                          f"{c['canon_count']:,} | {c['delta']:+,} | `{c['fact_id']}` |\n")
            if len(top) > 50:
                md.append(f"\n_…and {len(top) - 50} more._\n")

    md.append("\n---\n\n*Re-run via `python scripts/link_appearances_aggregate.py`. Idempotent (no shard mutation).*\n")
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(md)
    print(f"\nWrote report -> {REPORT_PATH.relative_to(ROOT)}")

    # JSON conflict log per discipline
    all_conflicts = []
    for p, _ in PREDICATES:
        for c in conflicts_per_pred[p]:
            all_conflicts.append({
                "shard":             SHARD_NAME,
                "kind":              "count-mismatch",
                "predicate":         p,
                "subject_name":      c["subject_name"],
                "chr_id":            c["chr_id"],
                "canon_fact_id":     c["fact_id"],
                "shard_count":       c["shard_count"],
                "canon_count":       c["canon_count"],
                "delta":             c["delta"],
                "resolution_class":  "unclassified",
                "resolution_status": "open",
            })

    overall_total_with_fact = sum(s["total_with_fact"] for s in summary.values())
    overall_agree           = sum(s["agree"] for s in summary.values())
    overall_rate = (overall_agree / overall_total_with_fact) if overall_total_with_fact else 0

    conflict_doc = {
        "_doc": "Machine-readable aggregate cross-validation log. Shape per docs/convergence-plan.md §Conflict-tracking discipline.",
        "shard":         SHARD_NAME,
        "linker":        "scripts/link_appearances_aggregate.py",
        "linker_target": "appearance count predicates (total/flashback/cover/silhouette)",
        "generated_on":  datetime.now().isoformat(timespec="seconds"),
        "stats": {
            "per_predicate": {
                p: {
                    "agree":           summary[p]["agree"],
                    "disagree":        summary[p]["disagree"],
                    "no_canon_fact":   summary[p]["no_canon_fact"],
                    "total_with_fact": summary[p]["total_with_fact"],
                    "agreement_rate":  round(summary[p]["agreement_rate"] / 100, 4),
                }
                for p, _ in PREDICATES
            },
            "overall_agreement_rate": round(overall_rate, 4),
        },
        "conflicts": all_conflicts,
    }
    with open(CONFLICTS_JSON, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(conflict_doc, ensure_ascii=False, indent=2))
        f.write("\n")
    print(f"Wrote conflict log -> {CONFLICTS_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
