"""Per-crew membership parity between crews.json (current bake source) and
relationships/member-of.json (shard) via query.py.

For each crew, builds two member lists:
  (a) from crews.json: [{name, current_bool}, ...]
  (b) from member-of shard via query.crew_dossier + display_name lookup
And reports per-crew diffs.

This is the actual rendering-layer test for the member-of shard: does the
shard reproduce what bake_crews would render? If not, we want to find out
where, why, and what to do about it.

Run:
  py scripts/compare_crews_membership.py            # summary
  py scripts/compare_crews_membership.py --verbose  # per-diff detail
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
CREWS_PATH = ROOT / "crews.json"

_LEFT_STATUSES = {
    "former", "defected", "resigned", "dissolved", "retired",
    "revoked", "post mortem", "descended",
}


def source_members(crew: dict) -> list[tuple[str, bool]]:
    """(name, current_bool) tuples derived from crews.json directly."""
    out = []
    for m in crew.get("members", []):
        if not isinstance(m, dict):
            continue
        name   = (m.get("name") or "").strip()
        status = (m.get("status") or "").strip().lower()
        if not name:
            continue
        out.append((name, status not in _LEFT_STATUSES))
    return out


def shard_members(crew_id: str) -> list[tuple[str, bool]]:
    """(name, current_bool) tuples derived from the shard via query.py."""
    out = []
    for m in query.members_of(crew_id):
        chr_id = m.get("from")
        name = query.display_name(chr_id) if chr_id else None
        if not name:
            continue
        out.append((name, bool(m.get("current"))))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show per-diff details, not just summary")
    parser.add_argument("--max-diffs", type=int, default=10,
                        help="When verbose, show at most N diffs")
    args = parser.parse_args()

    with open(CREWS_PATH, encoding="utf-8") as f:
        crews_doc = json.load(f)
    crews = crews_doc.get("crews", {})

    crews_total      = 0
    perfect_match    = 0
    name_only_diffs  = 0
    status_only_diffs = 0
    mixed_diffs      = 0
    diff_examples: list[dict] = []

    for crew_name, crew in crews.items():
        if not isinstance(crew, dict):
            continue
        crew_id = crew.get("id", "")
        if not crew_id:
            continue
        crews_total += 1

        src = set(source_members(crew))
        shd = set(shard_members(crew_id))
        if src == shd:
            perfect_match += 1
            continue

        # Compare on name set first
        src_names = {n for n, _ in src}
        shd_names = {n for n, _ in shd}
        names_differ = src_names != shd_names
        # Compare on full (name, current) pairs
        same_name_status_diffs = (
            (src - shd) | (shd - src)
        ) - (
            {(n, c) for n, c in (src - shd) if n not in shd_names}
            | {(n, c) for n, c in (shd - src) if n not in src_names}
        )
        statuses_differ = bool(same_name_status_diffs)

        if names_differ and statuses_differ:
            mixed_diffs += 1
        elif names_differ:
            name_only_diffs += 1
        else:
            status_only_diffs += 1

        if len(diff_examples) < args.max_diffs:
            diff_examples.append({
                "crew":          crew_name,
                "crew_id":       crew_id,
                "in_source_only": sorted(src - shd),
                "in_shard_only":  sorted(shd - src),
            })

    # Summary
    print(f"Crews compared:        {crews_total}")
    print(f"Perfect matches:       {perfect_match}  ({perfect_match/crews_total*100:.1f}%)")
    print(f"Name-set differs:      {name_only_diffs}")
    print(f"Current-flag differs:  {status_only_diffs}")
    print(f"Both differ:           {mixed_diffs}")

    if args.verbose and diff_examples:
        print(f"\nFirst {len(diff_examples)} diffs:")
        for d in diff_examples:
            print(f"\n  {d['crew']!r} ({d['crew_id']})")
            if d["in_source_only"]:
                print(f"    In source only ({len(d['in_source_only'])}):")
                for n, c in d["in_source_only"]:
                    print(f"      {'✓' if c else '✗'} {n}")
            if d["in_shard_only"]:
                print(f"    In shard only ({len(d['in_shard_only'])}):")
                for n, c in d["in_shard_only"]:
                    print(f"      {'✓' if c else '✗'} {n}")


if __name__ == "__main__":
    main()
