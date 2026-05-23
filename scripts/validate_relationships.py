"""Validate relationship shards against schemas and the entity index.

Skeleton for Phase 0 — grows as shards land in Tier 1+.
Currently validates:
  - JSON is loadable and is a list
  - Each row has `from`, `to`, `src` fields
  - `from` and `to` resolve in entity_index.json (if the index exists)
  - No within-shard duplicate (from, to) pairs (for shards where that would be invalid)

When no shard files exist yet (pre-Tier 1), exits cleanly with a note.

Usage:
    python scripts/validate_relationships.py
    python scripts/validate_relationships.py --shard ate-fruit
    python scripts/validate_relationships.py --pending   # check _pending/ dir instead
"""

import argparse
import json
import sys
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REL_DIR = ROOT / "relationships"
PENDING_DIR = REL_DIR / "_pending"
INDEX_PATH = ROOT / "entity_index.json"

# Shards where (from, to) must be globally unique — prevents reverse-of-existing rows
_UNIQUE_PAIR_SHARDS = {"family"}

# Required fields per row (all shards)
_REQUIRED_ROW_FIELDS = ("from", "to", "src")


def load_index() -> dict[str, str] | None:
    if not INDEX_PATH.exists():
        return None
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def validate_shard(
    path: Path,
    index: dict[str, str] | None,
    verbose: bool = False,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    shard_name = path.stem

    try:
        with open(path, encoding="utf-8") as f:
            rows = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{path.name}: invalid JSON — {e}")
        return errors, warnings

    if not isinstance(rows, list):
        errors.append(f"{path.name}: top-level must be a list, got {type(rows).__name__}")
        return errors, warnings

    seen_pairs: set[tuple[str, str]] = set()
    known_ids: set[str] = set(index.values()) if index is not None else set()

    for i, row in enumerate(rows):
        label = f"{path.name}[{i}]"

        if not isinstance(row, dict):
            errors.append(f"{label}: row must be an object")
            continue

        for field in _REQUIRED_ROW_FIELDS:
            if field not in row:
                errors.append(f"{label}: missing required field {field!r}")

        from_id = row.get("from", "")
        to_id = row.get("to", "")

        # Entity resolution (if index exists) — check against ID values, not alias keys
        if index is not None:
            if from_id and from_id not in known_ids and not _is_natural_key(from_id):
                errors.append(f"{label}: 'from' {from_id!r} not in entity_index")
            if to_id and to_id not in known_ids and not _is_natural_key(to_id):
                errors.append(f"{label}: 'to' {to_id!r} not in entity_index")

        # Duplicate pair check
        if shard_name in _UNIQUE_PAIR_SHARDS:
            pair = (from_id, to_id)
            reverse = (to_id, from_id)
            if pair in seen_pairs:
                errors.append(f"{label}: duplicate (from, to) pair {pair}")
            elif reverse in seen_pairs:
                errors.append(
                    f"{label}: reverse pair already exists — "
                    f"family.json stores each relationship once"
                )
            seen_pairs.add(pair)

    if verbose:
        status = "OK" if not errors else f"{len(errors)} error(s)"
        print(f"  {path.name}: {len(rows)} rows — {status}")

    return errors, warnings


def _is_natural_key(entity_id: str) -> bool:
    """Natural-key IDs (ch:, ep:, sbs:, arc:, etc.) may not be in the index yet."""
    natural_prefixes = {"ch:", "ep:", "vol:", "sbs:", "theory:", "saga:", "arc:"}
    return any(entity_id.startswith(p) for p in natural_prefixes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", help="Validate a specific shard by name (e.g. ate-fruit)")
    parser.add_argument("--pending", action="store_true", help="Check _pending/ dir")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    target_dir = PENDING_DIR if args.pending else REL_DIR

    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"{'_pending/' if args.pending else 'relationships/'} directory created (empty).")
        print("No shards to validate yet. Run extractors in Tier 1 to populate.")
        sys.exit(0)

    if args.shard:
        paths = [target_dir / f"{args.shard}.json"]
        paths = [p for p in paths if p.exists()]
        if not paths:
            print(f"Shard file not found: {args.shard}.json in {target_dir}")
            sys.exit(1)
    else:
        paths = sorted(target_dir.glob("*.json"))

    if not paths:
        print(
            f"No .json files in {'_pending/' if args.pending else 'relationships/'}. "
            "Nothing to validate."
        )
        sys.exit(0)

    print(f"Loading entity index ... ", end="")
    index = load_index()
    if index is None:
        print("not found (entity resolution skipped)")
    else:
        print(f"{len(index):,} entries")

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for path in paths:
        errors, warnings = validate_shard(path, index, verbose=args.verbose)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    print(f"\nShards checked: {len(paths)}")
    print(f"Errors:         {len(all_errors)}")
    print(f"Warnings:       {len(all_warnings)}")

    if all_errors:
        print("\nErrors:")
        for msg in all_errors:
            print(f"  ✗ {msg}")
        sys.exit(1)

    print("\nOK")


if __name__ == "__main__":
    main()
