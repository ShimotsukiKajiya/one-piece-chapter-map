"""
Assign stable sequential `id_num` to every SBS Q&A in sbs_archive.json.

Same pattern as assign_theory_numbers.py: existing IDs preserved, new
entries get the next available integer (1, 2, 3, ...). Once assigned,
an id_num NEVER moves — sbs.html#0432 is a permalink forever.

Should run after sbs_scraper.py adds new entries (e.g. when a new
volume drops). Wired into refresh.py.

Run:
  py assign_sbs_ids.py             # assign + write
  py assign_sbs_ids.py --dry-run   # report only
"""
import json, os, sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR  = os.path.dirname(__file__)
PATH = os.path.join(DIR, "sbs_archive.json")


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(PATH):
        print("  ✗ sbs_archive.json not found"); sys.exit(1)

    with open(PATH, encoding="utf-8") as f:
        sbs = json.load(f)

    used = {e["id_num"] for e in sbs if isinstance(e.get("id_num"), int)}
    next_id = (max(used) + 1) if used else 1

    # First-time numbering: sort by (volume, position-within-volume) so
    # IDs follow Oda's actual publication order.
    if not used:
        # Stable order: keep current array order within each volume
        # (the scraper appends in source-document order)
        sbs.sort(key=lambda e: (e.get("volume", 99999), 0))

    assigned = 0
    for e in sbs:
        if not isinstance(e.get("id_num"), int):
            e["id_num"] = next_id
            next_id += 1
            assigned += 1

    print("=" * 55)
    print("  SBS ID Assignment")
    print(f"  Total Q&As       : {len(sbs):,}")
    print(f"  Already had id   : {len(sbs) - assigned:,}")
    print(f"  Newly assigned   : {assigned:,}")
    print(f"  Range            : 1–{next_id - 1}")
    print("=" * 55)

    if assigned and not dry:
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(sbs, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Written → {PATH}")
    elif assigned and dry:
        print("  (dry run — no write)")
    else:
        print("  Nothing to do.")


if __name__ == "__main__":
    main()
