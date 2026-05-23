"""Extract member-of relationship shard from crews.json.

For each crew, iterates its members list and emits one row per member.
The source has only `name` + `status` per member — schema fields `since`,
`until`, and `tier` are not in the data and are omitted. `current` is derived
from status. Substatus values (e.g. "tobiroppo", "armored division") become
the optional `role` field.

Uses the shared `query.resolve_character` helper, which is invisible-Unicode
tolerant and rejects non-chr: IDs (so Seraphim-the-crew won't masquerade as
Seraphim-the-weapon, etc.).

Usage:
    python scripts/extract_member_of.py
    python scripts/extract_member_of.py --dry-run
"""

import argparse
import json
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from collections import Counter
from pathlib import Path

# Make the lib package importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CREWS_PATH      = ROOT / "crews.json"
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
PENDING_DIR     = ROOT / "relationships" / "_pending"
OUTPUT_PATH     = PENDING_DIR / "member-of.json"

# Status values that mean "no longer a member". Anything else (including
# substatus role names like "tobiroppo", "armored division") is treated as
# a current member with the status string captured as `role`.
_LEFT_STATUSES = {
    "former", "defected", "resigned", "dissolved", "retired",
    "revoked", "post mortem", "descended",
}


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict | list) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")


def load_unresolved() -> list[dict]:
    if not UNRESOLVED_PATH.exists():
        return []
    raw = load_json(UNRESOLVED_PATH)
    if isinstance(raw, dict):
        return raw.get("entries", [])
    return raw if isinstance(raw, list) else []


def save_unresolved(entries: list[dict]) -> None:
    save_json(UNRESOLVED_PATH, {"entries": entries})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats but do not write any files")
    args = parser.parse_args()

    data = load_json(CREWS_PATH)
    crews = data.get("crews", {})

    rows: list[dict] = []
    # name -> (count, sample_crew) so we don't blow up unresolved file with dupes
    unresolved_agg: dict[str, dict] = {}
    status_breakdown: Counter[str] = Counter()
    crews_with_members = 0
    members_seen = 0

    for crew_name, crew in crews.items():
        if not isinstance(crew, dict):
            continue
        crew_id = crew.get("id", "")
        if not crew_id or not crew_id.startswith("crew:"):
            continue
        members = crew.get("members", [])
        if not isinstance(members, list) or not members:
            continue
        crews_with_members += 1

        for m in members:
            if not isinstance(m, dict):
                continue
            mname  = (m.get("name")   or "").strip()
            status = (m.get("status") or "").strip().lower()
            if not mname:
                continue
            members_seen += 1
            status_breakdown[status] += 1

            chr_id = query.resolve_character(mname)
            if chr_id is None:
                agg = unresolved_agg.get(mname)
                if agg is None:
                    unresolved_agg[mname] = {"count": 1, "sample_crew": crew_name}
                else:
                    agg["count"] += 1
                continue

            row: dict = {
                "from":    chr_id,
                "to":      crew_id,
                "src":     "wiki",
                "current": status not in _LEFT_STATUSES,
            }
            if status and status not in ("current",) and status not in _LEFT_STATUSES:
                row["role"] = status
            rows.append(row)

    # Build aggregated unresolved entries
    unresolved_sorted = sorted(unresolved_agg.items(),
                               key=lambda kv: (-kv[1]["count"], kv[0]))
    new_unresolved = [
        {
            "name":       name,
            "source":     "crews.json",
            "context":    f"member of {info['sample_crew']!r} (and {info['count']-1} other crew(s))" if info["count"] > 1
                          else f"member of {info['sample_crew']!r}",
            "occurrences": info["count"],
        }
        for name, info in unresolved_sorted
    ]

    print(f"Crews with members:    {crews_with_members:>5,} / {len(crews):,}")
    print(f"Member entries seen:   {members_seen:>5,}")
    print(f"Rows produced:         {len(rows):>5,}")
    print(f"Unique unresolved:     {len(unresolved_agg):>5,}")
    if members_seen:
        print(f"Resolution rate:       {len(rows) / members_seen * 100:>5.1f}%")

    print("\nStatus breakdown (top 15):")
    for st, n in status_breakdown.most_common(15):
        print(f"  {n:>5,}  {st!r}")

    if unresolved_agg:
        print(f"\nTop 15 unresolved member names (by occurrences):")
        for name, info in unresolved_sorted[:15]:
            print(f"  {info['count']:>3}× {name}  (e.g. in {info['sample_crew']})")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        if rows:
            print("\nFirst 3 rows:")
            for r in rows[:3]:
                print(" ", json.dumps(r, ensure_ascii=False))
        return

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    save_json(OUTPUT_PATH, rows)
    print(f"\nWrote {len(rows):,} rows -> {OUTPUT_PATH.relative_to(ROOT)}")

    if new_unresolved:
        existing = load_unresolved()
        existing_keys = {(e["name"], e.get("source", "")) for e in existing}
        added = [u for u in new_unresolved if (u["name"], u["source"]) not in existing_keys]
        if added:
            save_unresolved(existing + added)
            print(f"Appended {len(added):,} unresolved name summaries -> bootstrap_unresolved.json")

    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard member-of")


if __name__ == "__main__":
    main()
