"""Build entity_index.json — the alias-to-ID lookup used at query time.

Walks every entity source file; for each entity record that has an `id` field,
emits entries for: the canonical `name`, the `slug`, and every item in `aliases`.
All keys are lowercased.

Must be re-run after any assign_ids.py run or manual alias update.

Usage:
    python scripts/build_entity_index.py
    python scripts/build_entity_index.py --dry-run   # report stats, don't write
    python scripts/build_entity_index.py --check      # write, then verify integrity
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
INDEX_PATH = ROOT / "entity_index.json"

# ---------------------------------------------------------------------------
# Source file registry
# Each entry: (path, extractor_fn_name)
# Extractor functions yield (name, id) pairs from a loaded JSON blob.
# ---------------------------------------------------------------------------

def _iter_name_dict(data: dict):
    """Source files that are {display_name: {id, name, slug, aliases, ...}}"""
    for _key, record in data.items():
        if isinstance(record, dict) and record.get("id"):
            yield record


def _iter_crews(data: dict):
    """crews.json: {generated_on, crews: {name: {id, ...}}}"""
    for _key, record in data.get("crews", {}).items():
        if isinstance(record, dict) and record.get("id"):
            yield record


def _iter_arc_list(data: list):
    """arcs.json: [{id, arc, slug, ...}, ...]"""
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            yield item


def _iter_weapons(data: dict):
    """weapons.json: {generated_on, _grades, weapons: [{id, name, slug, aliases, ...}, ...]}"""
    for record in data.get("weapons", []):
        if isinstance(record, dict) and record.get("id"):
            yield record


def _iter_items(data: dict):
    """items.json: {generated_on, items: [{id, name, slug, aliases, ...}, ...]}"""
    for record in data.get("items", []):
        if isinstance(record, dict) and record.get("id"):
            yield record


def _iter_voices(data: list):
    """relationships/voices.json: rows of {from: va:id, name: VA-name, ...}.
    Yields synthesised entity-like records so VAs are indexed by name + self-ref."""
    seen: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        va_id = row.get("from", "")
        name  = row.get("name", "")
        if not va_id.startswith("va:") or not name:
            continue
        if va_id in seen:
            continue
        seen.add(va_id)
        yield {"id": va_id, "name": name, "slug": "", "aliases": []}


SOURCES: list[tuple[str, callable]] = [
    ("punk_records.json",            _iter_name_dict),
    ("devil_fruits.json",            _iter_name_dict),
    ("locations.json",               _iter_name_dict),
    ("ships.json",                   _iter_name_dict),
    ("crews.json",                   _iter_crews),
    ("arcs.json",                    _iter_arc_list),
    ("weapons.json",                 _iter_weapons),
    ("items.json",                   _iter_items),
    ("relationships/voices.json",    _iter_voices),
]


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def build_index(verbose: bool = False) -> tuple[dict[str, str], list[str]]:
    """
    Returns (index, collision_messages).
    index: {alias_lower -> entity_id}
    collision_messages: list of human-readable collision descriptions
    """
    index: dict[str, str] = {}
    collisions: list[str] = []

    def _add(key: str, entity_id: str, source_label: str) -> None:
        key = key.strip().lower()
        if not key:
            return
        if key in index:
            if index[key] != entity_id:
                msg = (
                    f"COLLISION: {key!r} -> {index[key]!r} (existing) "
                    f"vs {entity_id!r} ({source_label})"
                )
                collisions.append(msg)
                if verbose:
                    print(f"  {msg}", file=sys.stderr)
        else:
            index[key] = entity_id

    for filename, extractor in SOURCES:
        path = ROOT / filename
        if not path.exists():
            if verbose:
                print(f"  SKIP (not found): {filename}", file=sys.stderr)
            continue

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for record in extractor(data):
            eid = record["id"]
            label = f"{filename}/{eid}"

            # self-reference: ensures every assigned ID is reachable in
            # index.values() even when all its name/alias keys collide
            _add(eid, eid, label)

            # canonical name
            name = record.get("name") or record.get("arc") or ""
            if name:
                _add(name, eid, label)

            # slug (may differ from slugified name)
            slug = record.get("slug", "")
            if slug:
                _add(slug, eid, label)

            # all aliases
            for alias in record.get("aliases", []):
                if alias:
                    _add(alias, eid, label)

            count += 1

        if verbose:
            print(f"  {filename}: {count} entities indexed")

    return index, collisions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report stats without writing entity_index.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Write the index then verify it can be loaded back cleanly",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    print("Building entity index ...")
    index, collisions = build_index(verbose=args.verbose or args.dry_run)

    print(f"  Entries:    {len(index):,}")
    print(f"  Collisions: {len(collisions)}")

    if collisions:
        print("\nCollisions (first 20):")
        for msg in collisions[:20]:
            print(f"  {msg}")
        if len(collisions) > 20:
            print(f"  ... and {len(collisions) - 20} more")

    if args.dry_run:
        print("\n[DRY RUN] entity_index.json not written.")
        return

    text = json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True)
    with open(INDEX_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")

    print(f"\nWritten -> {INDEX_PATH.relative_to(ROOT)}")

    if args.check:
        with open(INDEX_PATH, encoding="utf-8") as f:
            loaded = json.load(f)
        assert len(loaded) == len(index), "Round-trip mismatch!"
        print("Check: OK — index reloads cleanly.")


if __name__ == "__main__":
    main()
