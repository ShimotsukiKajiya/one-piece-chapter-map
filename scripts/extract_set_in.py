"""Extract set-in relationship shard from arcs.json + locations.json.

For each arc, finds the matching location by slug (direct match first, then
static override table). Arcs with no resolvable location are logged to
bootstrap_unresolved.json for manual triage.

Usage:
    python scripts/extract_set_in.py
    python scripts/extract_set_in.py --dry-run   # print rows, no writes
"""

import argparse
import json
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCS_PATH       = ROOT / "arcs.json"
LOCATIONS_PATH  = ROOT / "locations.json"
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
PENDING_DIR     = ROOT / "relationships" / "_pending"
OUTPUT_PATH     = PENDING_DIR / "set-in.json"

# ---------------------------------------------------------------------------
# Override table: arc slug -> location slug
# Used when the arc slug doesn't directly match any location slug.
# ---------------------------------------------------------------------------

_SLUG_OVERRIDES: dict[str, str] = {
    "romance-dawn":      "foosha-village",        # Luffy's home village
    "whiskey-peak":      "whisky-peak",            # spelling difference only
    "whole-cake-island": "totto-land",             # proper name of the island/nation
    "zou":               "mokomo-dukedom",         # the kingdom on Zou's back
    "reverie":           "pangaea-castle",         # Reverie takes place at Pangaea Castle
    "marineford":        "marine-headquarters",    # Marineford = Marine HQ
    "post-war":          "marine-headquarters",    # continuation at Marineford
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
                        help="Print rows but do not write any files")
    args = parser.parse_args()

    arcs = load_json(ARCS_PATH)
    locations_raw = load_json(LOCATIONS_PATH)

    # Build slug -> loc_id lookup from locations.json
    loc_by_slug: dict[str, str] = {}
    for loc in locations_raw.values():
        slug = loc.get("slug", "")
        lid  = loc.get("id",   "")
        if slug and lid:
            loc_by_slug[slug] = lid

    rows:       list[dict] = []
    unresolved: list[dict] = []

    existing_unresolved = load_unresolved()
    existing_keys = {(e["name"], e.get("source", "")) for e in existing_unresolved}

    for arc in arcs:
        arc_id   = arc["id"]    # arc:slug
        arc_slug = arc["slug"]  # e.g. "romance-dawn"
        arc_name = arc["name"]

        # Try direct slug match, then override table
        loc_slug = arc_slug if arc_slug in loc_by_slug else _SLUG_OVERRIDES.get(arc_slug)
        loc_id   = loc_by_slug.get(loc_slug) if loc_slug else None

        if loc_id is None:
            key = (arc_name, "arcs.json")
            if key not in existing_keys:
                unresolved.append({
                    "name":    arc_name,
                    "source":  "arcs.json",
                    "context": f"set-in: arc {arc_id!r} has no matching location slug in locations.json",
                })
                existing_keys.add(key)
            continue

        rows.append({"from": arc_id, "to": loc_id, "src": "inferred"})

    # Report
    print(f"Arcs read:      {len(arcs)}")
    print(f"Rows produced:  {len(rows)}")
    print(f"Unresolved:     {len(unresolved)}")

    if rows:
        print("\nResolved mappings:")
        for r in rows:
            print(f"  {r['from']:35s} -> {r['to']}")

    if unresolved:
        print("\nUnresolved arcs (no location found):")
        for u in unresolved:
            print(f"  ? {u['name']!r}")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        return

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    save_json(OUTPUT_PATH, rows)
    print(f"\nWrote {len(rows)} rows -> {OUTPUT_PATH.relative_to(ROOT)}")

    if unresolved:
        all_unresolved = existing_unresolved + unresolved
        save_unresolved(all_unresolved)
        print(f"Appended {len(unresolved)} unresolved -> bootstrap_unresolved.json")

    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard set-in")


if __name__ == "__main__":
    main()
