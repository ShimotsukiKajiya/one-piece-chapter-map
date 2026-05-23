"""
Character Name Normalizer
Reads character_aliases.json and applies it to appearances.csv, folding
alternate names into a single canonical name.

Backup: appearances.csv.bak (created on first run if not present)

Run:
  py normalize_chars.py            # apply normalisation
  py normalize_chars.py --dry      # report what would change without writing
  py normalize_chars.py --restore  # restore from .bak
"""

import csv, json, os, sys, shutil
from collections import Counter

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
CSV_FILE   = os.path.join(DIR, "appearances.csv")
BACKUP     = CSV_FILE + ".bak"
ALIAS_FILE = os.path.join(DIR, "character_aliases.json")


def main():
    dry     = "--dry"     in sys.argv
    restore = "--restore" in sys.argv

    if restore:
        if not os.path.exists(BACKUP):
            print("  ✗ No backup found"); sys.exit(1)
        shutil.copy2(BACKUP, CSV_FILE)
        print(f"  ✓ Restored {CSV_FILE} from backup")
        return

    with open(ALIAS_FILE, encoding="utf-8") as f:
        aliases = json.load(f)
    aliases.pop("_comment", None)

    # Build lookup: lowercased-alias → canonical
    lookup = {}
    for canonical, alts in aliases.items():
        for alt in alts:
            lookup[alt.lower().strip()] = canonical
        # Also map canonical to itself (no-op but safe)
        lookup[canonical.lower().strip()] = canonical

    # Read CSV
    with open(CSV_FILE, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    name_idx = [h.lower() for h in header].index("name")

    # Track changes
    changes = Counter()
    for row in rows[1:]:
        name = row[name_idx].strip()
        canonical = lookup.get(name.lower().strip())
        if canonical and canonical != name:
            changes[(name, canonical)] += 1
            row[name_idx] = canonical

    # Report
    print("=" * 55)
    print(f"  Character Normalizer  ({'DRY RUN' if dry else 'apply'})")
    print(f"  Aliases configured: {sum(len(v) for v in aliases.values())}")
    print(f"  Rows changed: {sum(changes.values())}")
    print("=" * 55); print()

    if changes:
        print("  Folds:")
        for (orig, new), n in sorted(changes.items(), key=lambda x: -x[1]):
            print(f"    {orig:30s} → {new:30s}  ({n} rows)")

    if dry:
        print()
        print("  (dry-run — no changes written)")
        return

    # Backup once
    if not os.path.exists(BACKUP):
        shutil.copy2(CSV_FILE, BACKUP)
        print(f"  ✓ Backup → {BACKUP}")

    # Write
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerows(rows)
    print(f"  ✓ Updated {CSV_FILE}")
    print()
    print("  Run `py bake.py csv` to update index.html + quiz.html with the new data.")


if __name__ == "__main__":
    main()
