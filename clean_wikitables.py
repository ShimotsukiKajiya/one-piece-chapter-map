"""
Clean wikitable syntax from answer texts in sbs_archive.json.

The original SBS scraper left raw wikitext like
  {| class="wikitable" !Image !Name !Occupation |- |Hajrudin |Captain ...
in some answer texts. This converts those tables to readable lists.

Run:
  py clean_wikitables.py --dry    # preview
  py clean_wikitables.py          # apply
"""
import json, os, re, sys, shutil

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR     = os.path.dirname(__file__)
ARCHIVE = os.path.join(DIR, "sbs_archive.json")
BACKUP  = os.path.join(DIR, "sbs_archive.preclean.json")

TABLE_RE = re.compile(r"\{\|.*?\|\}", re.DOTALL)


def cleanup_table(table_block):
    """Convert one {| ... |} block to readable text."""
    inner = table_block[2:-2]    # strip {| and |}

    # Strip ALL HTML-like attributes (class, style, id, border, etc.)
    inner = re.sub(r'\b\w+="[^"]*"', '', inner)

    # Step 1: normalise row separator |- (and any number of dashes) → §ROW§
    inner = re.sub(r'\|-+', '§ROW§', inner)
    # Step 2: cell separators on same line (|| and !!) → §CELL§
    inner = re.sub(r'\|\|+', '§CELL§', inner)
    inner = re.sub(r'!!+',  '§CELL§', inner)
    # Step 3: any remaining single | or ! that starts a cell. These look like
    # `\s|cell` or `\n|cell` or `^|cell`. Use a permissive pattern.
    inner = re.sub(r'(?:^|\s)\|(?=\S)',  '§CELL§', inner, flags=re.MULTILINE)
    inner = re.sub(r'(?:^|\s)!(?=\S)',   '§CELL§', inner, flags=re.MULTILINE)

    # Step 4: split into rows then cells
    cleaned_rows = []
    for row in inner.split('§ROW§'):
        row = row.strip()
        if not row: continue
        cells = [c.strip(" \t\n|!§") for c in row.split('§CELL§')]
        cells = [c for c in cells if c]
        if not cells: continue
        cleaned_rows.append(" · ".join(cells))

    if not cleaned_rows:
        return ""
    # Join rows with " | " — keeps it inline-friendly
    return "[" + "  ||  ".join(cleaned_rows) + "]"


def clean_answer(text):
    """Replace each wikitable block with its cleaned-text version."""
    return TABLE_RE.sub(lambda m: cleanup_table(m.group(0)), text)


def main():
    dry = "--dry" in sys.argv

    with open(ARCHIVE, encoding="utf-8") as f:
        archive = json.load(f)

    if not dry:
        if not os.path.exists(BACKUP):
            shutil.copy2(ARCHIVE, BACKUP)
            print(f"  ✓ Backup → {BACKUP}")

    print("=" * 55)
    print(f"  Wikitable Cleaner — {'DRY' if dry else 'APPLY'}")
    print("=" * 55); print()

    changed = 0
    for qa in archive:
        if "{|" not in qa.get("answer", ""): continue
        old = qa["answer"]
        new = clean_answer(old)
        if old != new:
            changed += 1
            if dry and changed <= 3:
                print(f"\nVol {qa['volume']}:")
                print(f"  BEFORE: {old[:200]}…")
                print(f"  AFTER : {new[:200]}…")
            qa["answer"] = new

    print()
    print(f"  Cleaned {changed} answer texts")

    if not dry:
        with open(ARCHIVE, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Wrote → {ARCHIVE}")
    else:
        print("  (dry-run — nothing written)")
    print("=" * 55)


if __name__ == "__main__":
    main()
