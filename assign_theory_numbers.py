"""
Assign stable sequential numeric IDs (`num`) to every entry in
theories_import.json. Existing `num` values are preserved; new ones get
the next available integer.

Idempotent — safe to re-run after any scrape. Numbers, once assigned, never
move, so anchors like `theory-0042` and citations like "Theory #0042"
remain stable forever.

Run:
  py assign_theory_numbers.py            # assign + write
  py assign_theory_numbers.py --dry-run  # report only
"""
import json, os, sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR  = os.path.dirname(__file__)
PATH = os.path.join(DIR, "theories_import.json")


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(PATH):
        print("  ✗ theories_import.json not found"); sys.exit(1)

    with open(PATH, encoding="utf-8") as f:
        theories = json.load(f)

    used = {t["num"] for t in theories if isinstance(t.get("num"), int)}
    next_num = (max(used) + 1) if used else 1

    # Sort by date ascending for first-time numbering — earliest theories
    # get lowest numbers. Once `num` exists, sort doesn't affect numbering.
    if not used:
        theories.sort(key=lambda t: t.get("date", ""))

    assigned = 0
    for t in theories:
        if not isinstance(t.get("num"), int):
            t["num"] = next_num
            next_num += 1
            assigned += 1

    print("=" * 55)
    print("  Theory Number Assignment")
    print(f"  Total theories: {len(theories)}")
    print(f"  Already had num: {len(theories) - assigned}")
    print(f"  Newly assigned : {assigned}")
    print(f"  Range          : 1–{next_num - 1}")
    print("=" * 55)

    if assigned and not dry:
        # Re-sort to keep file stable: by num ascending
        theories.sort(key=lambda t: t["num"])
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(theories, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Written → {PATH}")
    elif assigned and dry:
        print("  (dry run — no write)")
    else:
        print("  Nothing to do.")


if __name__ == "__main__":
    main()
