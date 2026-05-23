"""Extract appears-in relationship shard from appearances.csv.

For each row in appearances.csv, resolves the character name to a chr: ID and
emits one row per appearance. The biggest table in the project (~26.7k rows).

Unresolved names are aggregated (count + first chapter) and appended to
bootstrap_unresolved.json as a single entry per name — not one per appearance.

Usage:
    python scripts/extract_appears_in.py
    python scripts/extract_appears_in.py --dry-run   # print stats, no writes
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
UNRESOLVED_PATH  = ROOT / "bootstrap_unresolved.json"
PENDING_DIR      = ROOT / "relationships" / "_pending"
OUTPUT_PATH      = PENDING_DIR / "appears-in.json"


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


# Invisible Unicode that sometimes trails CSV-scraped names (LRM, ZWJ, etc.)
_INVISIBLE_RE = re.compile(r"[​‌‍‎‏⁠﻿]+")


def resolve_chr(name: str, index: dict) -> str | None:
    """Look up name in entity_index; only return result if it's a chr: ID.

    Tries the raw lowercased name first, then a version with invisible
    Unicode stripped (LRM, ZWJ, BOM, etc.) — appearances.csv occasionally
    has these as scraping artefacts.
    """
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

    rows: list[dict] = []
    # name -> {count, first_chapter}
    unresolved_agg: dict[str, dict] = {}
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

            chr_id = resolve_chr(name, index)
            if chr_id is None:
                agg = unresolved_agg.get(name)
                if agg is None:
                    unresolved_agg[name] = {"count": 1, "first_chapter": chapter}
                else:
                    agg["count"] += 1
                    if chapter < agg["first_chapter"]:
                        agg["first_chapter"] = chapter
                continue

            rows.append({
                "from":            chr_id,
                "to":              f"ch:{chapter}",
                "src":             "auto-extract",
                "appearance_type": ap_type,
            })

    # Build unresolved entries (sorted by count descending for triage usefulness)
    unresolved_sorted = sorted(
        unresolved_agg.items(), key=lambda kv: (-kv[1]["count"], kv[0])
    )
    new_unresolved = [
        {
            "name":             name,
            "source":           "appearances.csv",
            "context":          f"unresolved character — {info['count']} appearance(s), first in chapter {info['first_chapter']}",
            "appearance_count": info["count"],
            "first_chapter":    info["first_chapter"],
        }
        for name, info in unresolved_sorted
    ]

    # Report
    total_unresolved_appearances = sum(info["count"] for info in unresolved_agg.values())
    print(f"CSV rows read:          {rows_read:>6,}")
    print(f"Resolved rows:          {len(rows):>6,}")
    print(f"Unresolved appearances: {total_unresolved_appearances:>6,}")
    print(f"Unique unresolved names:{len(unresolved_agg):>6,}")
    print(f"Resolution rate:        {len(rows) / max(rows_read, 1) * 100:>5.1f}%")

    if unresolved_agg:
        print("\nTop 20 unresolved names (by appearance count):")
        for name, info in unresolved_sorted[:20]:
            print(f"  {info['count']:>4}× ch:{info['first_chapter']:>4} — {name}")

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
        # De-dup against existing unresolved entries by (name, source) key
        existing = load_unresolved()
        existing_keys = {(e["name"], e.get("source", "")) for e in existing}
        added = [u for u in new_unresolved if (u["name"], u["source"]) not in existing_keys]
        if added:
            save_unresolved(existing + added)
            print(f"Appended {len(added):,} unresolved name summaries -> bootstrap_unresolved.json")
        else:
            print("No new unresolved entries to append.")

    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard appears-in")


if __name__ == "__main__":
    main()
