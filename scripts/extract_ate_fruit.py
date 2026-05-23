"""Extract ate-fruit relationship shard from devil_fruits.json.

For each fruit with a known current user, resolves the character name to a
chr: ID via entity_index.json and emits one row. Fruits where the wiki records
a previous user (raw_keys contains "previous") are flagged at the end — those
prior-user rows need manual addition.

Chapter is emitted as a ch:N natural-key ID per the schema (e.g. "ch:1").

Usage:
    python scripts/extract_ate_fruit.py
    python scripts/extract_ate_fruit.py --dry-run   # print rows, no writes
"""

import argparse
import json
import re
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRUITS_PATH     = ROOT / "devil_fruits.json"
INDEX_PATH      = ROOT / "entity_index.json"
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
PENDING_DIR     = ROOT / "relationships" / "_pending"
OUTPUT_PATH     = PENDING_DIR / "ate-fruit.json"

_CHAPTER_RE = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)


def _parse_chapter(first_appearance: str) -> str | None:
    """Return 'ch:N' from 'Chapter N; Episode N (Name)', or None."""
    m = _CHAPTER_RE.search(first_appearance)
    return f"ch:{m.group(1)}" if m else None


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

    fruits_data = load_json(FRUITS_PATH)
    index = load_json(INDEX_PATH) if INDEX_PATH.exists() else {}

    rows:            list[dict] = []
    unresolved:      list[dict] = []
    transferred:     list[str]  = []   # fruits with previous users needing manual rows
    skipped_no_user: int        = 0

    existing_unresolved = load_unresolved()
    existing_keys = {(e["name"], e.get("source", "")) for e in existing_unresolved}

    for fruit_name, fruit in fruits_data.items():
        if not isinstance(fruit, dict):
            continue
        if not fruit.get("found", False):
            continue

        user_current = fruit.get("user_current", "").strip()
        if not user_current:
            skipped_no_user += 1
            continue

        fruit_id = fruit.get("id", "")
        if not fruit_id:
            continue

        # Flag transferred fruits for manual follow-up
        if "previous" in fruit.get("raw_keys", []):
            transferred.append(fruit_name)

        # Resolve character name -> chr: ID
        chr_id = index.get(user_current.lower())
        if chr_id is None:
            key = (user_current, "devil_fruits.json")
            if key not in existing_keys:
                unresolved.append({
                    "name":    user_current,
                    "source":  "devil_fruits.json",
                    "context": f"user_current of {fruit_name!r} (fruit: {fruit_id})",
                })
                existing_keys.add(key)
            continue

        chapter = _parse_chapter(fruit.get("first_appearance", ""))

        row: dict = {
            "from":    chr_id,
            "to":      fruit_id,
            "src":     "wiki",
            "current": True,
        }
        if chapter is not None:
            row["chapter"] = chapter

        rows.append(row)

    # Report
    total_found = sum(
        1 for f in fruits_data.values()
        if isinstance(f, dict) and f.get("found", False)
    )
    print(f"Fruits (found=true):  {total_found}")
    print(f"  No current user:    {skipped_no_user}")
    print(f"  Rows produced:      {len(rows)}")
    print(f"  Unresolved names:   {len(unresolved)}")
    print(f"  Transferred fruits: {len(transferred)}  (need manual prior-user rows)")

    if transferred:
        print("\nFruits with previous users — manual rows needed:")
        for name in transferred:
            print(f"  ! {name}")

    if unresolved:
        print("\nUnresolved character names:")
        for u in unresolved:
            print(f"  ? {u['name']!r}  ({u['context']})")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        if rows:
            print("\nFirst 5 rows:")
            for r in rows[:5]:
                print(" ", json.dumps(r, ensure_ascii=False))
        return

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    save_json(OUTPUT_PATH, rows)
    print(f"\nWrote {len(rows)} rows -> {OUTPUT_PATH.relative_to(ROOT)}")

    if unresolved:
        all_unresolved = existing_unresolved + unresolved
        save_unresolved(all_unresolved)
        print(f"Appended {len(unresolved)} unresolved -> bootstrap_unresolved.json")

    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard ate-fruit")


if __name__ == "__main__":
    main()
