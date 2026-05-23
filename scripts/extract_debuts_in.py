"""Extract debuts-in relationship shard from appearances.csv.

Per character, takes the row with the smallest chapter number — that row's
appearance_type is preserved as the debut type. One row per unique character.

Reuses the same name-resolution helper as extract_appears_in.py
(invisible-Unicode tolerant, accepts only chr: IDs from entity_index).

Skips unresolved-name aggregation: extract_appears_in.py already covers it
from the same source.

Usage:
    python scripts/extract_debuts_in.py
    python scripts/extract_debuts_in.py --dry-run   # print stats, no writes
"""

import argparse
import csv
import json
import re
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPEARANCES_PATH = ROOT / "appearances.csv"
INDEX_PATH       = ROOT / "entity_index.json"
PENDING_DIR      = ROOT / "relationships" / "_pending"
OUTPUT_PATH      = PENDING_DIR / "debuts-in.json"

_INVISIBLE_RE = re.compile(r"[​‌‍‎‏⁠﻿]+")


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict | list) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")


def resolve_chr(name: str, index: dict) -> str | None:
    key = name.lower()
    eid = index.get(key)
    if eid is None:
        cleaned = _INVISIBLE_RE.sub("", key).strip()
        if cleaned and cleaned != key:
            eid = index.get(cleaned)
    if eid and eid.startswith("chr:"):
        return eid
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print stats but do not write any files")
    args = parser.parse_args()

    index = load_json(INDEX_PATH) if INDEX_PATH.exists() else {}

    # name -> (chapter, appearance_type) of earliest appearance
    debut_by_name: dict[str, tuple[int, str]] = {}
    rows_read = 0

    with open(APPEARANCES_PATH, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows_read += 1
            chapter_str = r.get("chapter", "").strip()
            name        = r.get("name", "").strip()
            ap_type     = r.get("type", "").strip()
            if not chapter_str or not name or not ap_type:
                continue
            try:
                chapter = int(chapter_str)
            except ValueError:
                continue

            existing = debut_by_name.get(name)
            if existing is None or chapter < existing[0]:
                debut_by_name[name] = (chapter, ap_type)

    rows: list[dict] = []
    unresolved_names: list[str] = []

    for name, (chapter, ap_type) in debut_by_name.items():
        chr_id = resolve_chr(name, index)
        if chr_id is None:
            unresolved_names.append(name)
            continue
        rows.append({
            "from":            chr_id,
            "to":              f"ch:{chapter}",
            "src":             "auto-extract",
            "appearance_type": ap_type,
        })

    print(f"CSV rows read:     {rows_read:>5,}")
    print(f"Unique characters: {len(debut_by_name):>5,}")
    print(f"Resolved debuts:   {len(rows):>5,}")
    print(f"Unresolved:        {len(unresolved_names):>5,}")
    print(f"Resolution rate:   {len(rows) / max(len(debut_by_name), 1) * 100:>5.1f}%")

    if unresolved_names:
        print("\nUnresolved names (covered by appears-in extractor's aggregation):")
        for n in unresolved_names:
            print(f"  ? {n}")

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
    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard debuts-in")


if __name__ == "__main__":
    main()
