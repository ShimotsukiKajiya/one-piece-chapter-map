"""Extract family relationship shard from families.json.

Reads families.json, maps relation strings to the family_relation schema enum,
resolves character names to chr: IDs via entity_index.json, and writes rows to
relationships/_pending/family.json.

Unresolved names are appended to bootstrap_unresolved.json for triage.
Rows with non-family relation types (satellite, rival, mentor, sovereign) are
skipped with a logged warning — they belong in other shards.

Usage:
    python scripts/extract_family.py
    python scripts/extract_family.py --dry-run   # print rows, no writes
"""

import argparse
import json
import re
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAMILIES_PATH   = ROOT / "families.json"
INDEX_PATH      = ROOT / "entity_index.json"
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
PENDING_DIR     = ROOT / "relationships" / "_pending"
OUTPUT_PATH     = PENDING_DIR / "family.json"

# ---------------------------------------------------------------------------
# Relation mapping: families.json strings -> schema enum values
# ---------------------------------------------------------------------------

_RELATION_MAP: dict[str, str | None] = {
    # gendered preferred — schema v2 (2026-05-01) added father/mother/etc.
    # so we no longer collapse gender at extract time.
    "father":      "father",
    "mother":      "mother",
    "grandfather": "grandfather",
    "grandmother": "grandmother",
    "son":         "son",
    "daughter":    "daughter",
    "brother":     "brother",
    "sister":      "sister",
    "wife":        "wife",
    "husband":     "husband",
    "uncle":       "uncle",
    "aunt":        "aunt",
    "nephew":      "nephew",
    "niece":       "niece",
    # gender-neutral — used when source doesn't specify
    "parent":      "parent",
    "child":       "child",
    "sibling":     "sibling",
    "grandparent": "grandparent",
    "grandchild":  "grandchild",
    "spouse":      "spouse",
    "partner":     "partner",
    "lover":       "partner",
    "cousin":      "cousin",
    "in-law":      "in-law",
    "ancestor":    "ancestor",
    "descendant":  "descendant",
    # adoptive (gendered preferred — schema v2)
    "adoptive father":   "adoptive-father",
    "adoptive mother":   "adoptive-mother",
    "adoptive son":      "adoptive-son",
    "adoptive daughter": "adoptive-daughter",
    "adoptive brother":  "adoptive-brother",
    "adoptive sister":   "adoptive-sister",
    # sworn / guardian
    "sworn brother":        "sworn-brother",
    "sworn sister":         "sworn-sister",
    "guardian":             "guardian",
    "guardian (childhood)": "guardian",
    # explicitly skipped (not family relations — belong in trains-with etc.)
    "alleged son":       None,
    "rival (childhood)": None,
    "mentor":            None,
    "sovereign of":      None,
    "satellite":         None,
}


def _parse_chapter(source: str) -> tuple[int | None, str | None]:
    """Return (chapter_int, note_str) from a source string like 'Chapter 432'."""
    m = re.match(r"Chapter\s+(\d+)", source, re.IGNORECASE)
    if m:
        return int(m.group(1)), None
    return None, source  # non-chapter source → goes in note


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
                        help="Print rows but do not write any files")
    args = parser.parse_args()

    # Load inputs
    families = load_json(FAMILIES_PATH)
    edges    = families.get("edges", [])
    index    = load_json(INDEX_PATH) if INDEX_PATH.exists() else {}

    rows:       list[dict] = []
    unresolved: list[dict] = []
    skipped:    list[str]  = []

    existing_unresolved = load_unresolved()
    existing_keys = {(e["name"], e.get("source", "")) for e in existing_unresolved}

    for edge in edges:
        from_name = edge.get("from", "").strip()
        to_name   = edge.get("to",   "").strip()
        relation  = edge.get("relation", "").strip().lower()
        source    = edge.get("source", "")

        # Map relation
        if relation not in _RELATION_MAP:
            skipped.append(f"Unknown relation {relation!r} ({from_name} -> {to_name})")
            continue
        mapped = _RELATION_MAP[relation]
        if mapped is None:
            skipped.append(f"Skipped relation {relation!r} ({from_name} -> {to_name})")
            continue

        # Resolve IDs
        from_id = index.get(from_name.lower())
        to_id   = index.get(to_name.lower())

        for name, role in [(from_name, "from"), (to_name, "to")]:
            resolved_id = index.get(name.lower())
            if resolved_id is None:
                key = (name, "families.json")
                if key not in existing_keys:
                    unresolved.append({
                        "name":   name,
                        "source": "families.json",
                        "context": f"{role} in edge: {from_name} --[{relation}]--> {to_name}",
                    })
                    existing_keys.add(key)

        if from_id is None or to_id is None:
            continue  # will retry after triage

        # Parse source
        chapter, note = _parse_chapter(source)

        row: dict = {
            "from":     from_id,
            "to":       to_id,
            "src":      "manual",
            "relation": mapped,
        }
        if chapter is not None:
            row["chapter"] = chapter
        if note is not None:
            row["note"] = note

        rows.append(row)

    # Report
    print(f"Edges read:     {len(edges)}")
    print(f"Rows produced:  {len(rows)}")
    print(f"Unresolved:     {len(unresolved)}")
    print(f"Skipped:        {len(skipped)}")

    if skipped:
        print("\nSkipped:")
        for msg in skipped:
            print(f"  - {msg}")

    if unresolved:
        print("\nUnresolved names:")
        for u in unresolved:
            print(f"  ? {u['name']!r}  ({u['context']})")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        if rows:
            print("\nFirst 5 rows:")
            for r in rows[:5]:
                print(" ", json.dumps(r, ensure_ascii=False))
        return

    # Write pending shard
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    save_json(OUTPUT_PATH, rows)
    print(f"\nWrote {len(rows)} rows -> {OUTPUT_PATH.relative_to(ROOT)}")

    # Append new unresolved entries
    if unresolved:
        all_unresolved = existing_unresolved + unresolved
        save_unresolved(all_unresolved)
        print(f"Appended {len(unresolved)} unresolved -> bootstrap_unresolved.json")

    print("\nNext steps:")
    print("  py scripts/triage.py                           # resolve unresolved names")
    print("  py scripts/validate_relationships.py --pending  # validate shard")
    print("  py scripts/validate_relationships.py --shard family --pending  # same, targeted")


if __name__ == "__main__":
    main()
