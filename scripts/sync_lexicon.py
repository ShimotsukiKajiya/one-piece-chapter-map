"""Sync the leak lexicon from docs/leak-lexicon.json into lore-gate.js.

The lexicon has two consumers: the runtime gate in the browser (lore-gate.js)
and the CI checkers (Python). Keeping two hand-maintained copies guarantees they
drift, and a drifted lexicon means the site hides something the checker thinks is
fine, or vice versa. The JSON is authoritative; this regenerates the JS block
between the LEXICON-START / LEXICON-END markers.

Run:
  python scripts/sync_lexicon.py           # verify only; exit 1 if out of sync
  python scripts/sync_lexicon.py --write   # regenerate the JS block
"""
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON = os.path.join(ROOT, "docs", "leak-lexicon.json")
TARGET = os.path.join(ROOT, "lore-gate.js")

START = "  // LEXICON-START"
END = "  // LEXICON-END"


def load_terms():
    with open(LEXICON, encoding="utf-8") as f:
        doc = json.load(f)
    terms = [(t["term"], int(t["ch"])) for t in doc["terms"]]
    # Longest first so an overlapping shorter term never shadows a longer one.
    terms.sort(key=lambda t: (-len(t[0]), t[0]))
    return terms


def js_literal(s):
    return '"%s"' % s.replace('"', '\\"') if "'" in s else "'%s'" % s


def render(terms):
    lines = [
        START,
        "  // Generated from docs/leak-lexicon.json by scripts/sync_lexicon.py.",
        "  // Do not hand-edit: edit the JSON and re-run the script.",
        "  // Longest terms first, so an overlapping shorter term cannot shadow one.",
        "  var LEXICON = [",
    ]
    row = "   "
    for term, ch in terms:
        piece = " [%s, %d]," % (js_literal(term), ch)
        if len(row) + len(piece) > 78:
            lines.append(row)
            row = "   "
        row += piece
    if row.strip():
        lines.append(row)
    lines[-1] = lines[-1].rstrip(",")
    lines.append("  ];")
    lines.append(END)
    return "\n".join(lines)


def main():
    write = "--write" in sys.argv
    terms = load_terms()

    with open(TARGET, encoding="utf-8", newline="") as f:
        src = f.read()
    nl = "\r\n" if "\r\n" in src else "\n"

    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(src):
        print(f"  ✗ markers not found in {os.path.basename(TARGET)}")
        return 2

    block = render(terms).replace("\n", nl)
    updated = pattern.sub(lambda _: block, src, count=1)

    if updated == src:
        print(f"  ✓ lore-gate.js is in sync with the lexicon ({len(terms)} terms)")
        return 0

    if write:
        with open(TARGET, "w", encoding="utf-8", newline="") as f:
            f.write(updated)
        print(f"  ✓ regenerated lore-gate.js lexicon block ({len(terms)} terms)")
        return 0

    print(f"  ✗ lore-gate.js is OUT OF SYNC with docs/leak-lexicon.json")
    print(f"    run: python scripts/sync_lexicon.py --write")
    return 1


if __name__ == "__main__":
    sys.exit(main())
