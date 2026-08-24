"""Read the SBS answers that are laid out as a POSITIONAL TABLE.

`verify.py` matches a value to a name inside a ~80-character window. Oda answers
some profile questions as a table instead:

    [Name   · Drake  · Kujaku · Grus   · Koby   ||
     Height · 233 cm · 180 cm · 205 cm · 167 cm ]

"Kujaku" and "180 cm" belong together because they are both the second cell of
their row — but they sit ~180 characters apart, so the proximity matcher
structurally cannot read them, and reads them WRONG if it reaches at all: the
nearest height to the name "Koby" is Grus's.

Bounded on purpose. Of 1,685 archived answers exactly 13 contain a bracketed
`||`-delimited table, and only two of those are name-to-value tables. The rest
are lists of foods, sleep times, Spanish numerals and cover-story arcs, and this
parser deliberately declines them rather than guessing.

Two layouts are read:

  COLUMN-MAJOR — the first row's first cell is "Name". Names run across that
    row; every later row is a field, and cell i of the field row belongs to
    name i.

  ROW-MAJOR — the first row is a header containing "Name". Every later row is
    one character. Header and data rows can differ in width: in Vol. 112 the
    header carries a leading "Image" column that the data rows do not, so rows
    are aligned FROM THE RIGHT, which is where the mismatch is absent.

Output is CANDIDATE CLAIMS, never promotions. Per docs/canon-policy.md nothing
here may change a tier; the maintainer decides in curate.html. Writes
docs/curate_queue_positional.json by default; --append folds the candidates into
docs/curate_queue.json instead.

Run:
  python scripts/parse_sbs_positional.py            # report + write the side file
  python scripts/parse_sbs_positional.py --dry-run  # report only
  python scripts/parse_sbs_positional.py --append   # fold into the main queue
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.resolve import Resolver, normalise

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "docs", "curate_queue.json")
SIDE = os.path.join(ROOT, "docs", "curate_queue_positional.json")

# A bracketed block whose rows are joined by "||".
BLOCK = re.compile(r"\[([^\[\]]{40,4000}?\|\|[^\[\]]{10,4000}?)\]", re.S)

# Table label -> punk_records field. Labels with no Codex field are dropped
# rather than invented: "Favorite Food" and "Image" have nowhere to go.
LABEL_FIELD = {
    "height": "height",
    "age": "age",
    "birthday": "birthday",
    "blood type": "blood_type",
    "occupation": "occupation",
    "rank": "occupation",
    "devil fruit": "devil_fruit_name",
    "birthplace": "origin",
    "origin": "origin",
}

NAME_LABELS = {"name", "names", "character", "characters"}


def clean(cell):
    s = cell.replace("&nbsp;", " ")
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip(" *|·\n\t")


def rows_of(block):
    out = []
    for raw in block.split("||"):
        cells = [clean(c) for c in raw.split("·")]
        cells = [c for c in cells if c != ""]
        if cells:
            out.append(cells)
    return out


def read_column_major(rows):
    """Row 0 is `Name · A · B · C`; later rows are fields."""
    head = rows[0]
    if head[0].strip().lower() not in NAME_LABELS:
        return None
    names = head[1:]
    if len(names) < 2:
        return None
    out = []
    for row in rows[1:]:
        label = row[0].strip().lower()
        field = LABEL_FIELD.get(label)
        values = row[1:]
        if not field:
            continue
        if len(values) != len(names):
            # a ragged field row cannot be aligned by index -- refuse it
            out.append(("__ragged__", label, f"{len(values)} values for "
                                             f"{len(names)} names"))
            continue
        for n, v in zip(names, values):
            out.append((n, field, v))
    return out


def read_row_major(rows):
    """Row 0 is a header containing `Name`; later rows are characters."""
    head = [c.strip().lower() for c in rows[0]]
    if "name" not in head:
        return None
    body = rows[1:]
    if not body:
        return None
    out = []
    for row in body:
        # Header and data rows can differ in width (Vol. 112 drops "Image" from
        # the data rows). The trailing columns are the ones that line up, so
        # align from the right and discard the unmatched head columns.
        k = min(len(row), len(head))
        cols, vals = head[-k:], row[-k:]
        if "name" not in cols:
            out.append(("__ragged__", "row", " · ".join(row)[:70]))
            continue
        name = vals[cols.index("name")]
        for label, v in zip(cols, vals):
            field = LABEL_FIELD.get(label)
            if field and v and v != name:
                out.append((name, field, v))
    return out


def main():
    dry = "--dry-run" in sys.argv
    append = "--append" in sys.argv
    with open(os.path.join(ROOT, "sbs_archive.json"), encoding="utf-8") as f:
        sbs = json.load(f)
    resolver = Resolver(ROOT)

    print("=" * 76)
    print("  SBS positional tables — claims the proximity matcher cannot reach")
    print("=" * 76)

    blocks = declined = 0
    candidates = []
    unresolved = []

    for rec in sbs:
        answer = rec.get("answer") or ""
        for b in BLOCK.finditer(answer):
            blocks += 1
            rows = rows_of(b.group(1))
            if len(rows) < 2:
                declined += 1
                continue
            parsed = read_column_major(rows) or read_row_major(rows)
            if not parsed:
                declined += 1
                continue

            ragged = [p for p in parsed if p[0] == "__ragged__"]
            good = [p for p in parsed if p[0] != "__ragged__"]
            print(f"\n  vol {rec['volume']} q{rec['id_num']} — "
                  f"{len(rows)} rows, {len(good)} candidate claim(s)")
            for _, what, why in ragged:
                print(f"      ⚠ declined row {what!r}: {why}")

            for name, field, value in good:
                canon = resolver.canonical(name)
                if not canon:
                    unresolved.append((rec["volume"], rec["id_num"], name))
                    print(f"      ? {name:<20} {field:<12} {value[:34]:<34} "
                          f"(no punk_records match — dropped)")
                    continue
                print(f"      · {canon:<20} {field:<12} {value[:34]}")
                candidates.append({
                    "claim_id": f"positional:{normalise(canon)}:{field}",
                    "evidence_id": f"sbs:vol{rec['volume']:03d}-q{rec['id_num']:04d}",
                    "subject": canon,
                    "field": field,
                    "value": value,
                    "vol": rec["volume"],
                    "qa_id": rec["id_num"],
                    "snippet": " · ".join(rows[0])[:150],
                    "rule": "positional-table",
                })

    print("\n" + "-" * 76)
    print(f"\n  bracketed ||-tables seen         {blocks:>4}")
    print(f"  declined (not a name/value table) {declined:>4}")
    print(f"  candidate claims                  {len(candidates):>4}")
    print(f"  names with no punk_records match  {len(unresolved):>4}")
    for v, q, n in unresolved:
        print(f"      vol{v} q{q}: {n!r}")

    if dry:
        print("\n  --dry-run: nothing written.\n")
        return 0

    if append:
        with open(QUEUE, encoding="utf-8") as f:
            queue = json.load(f)
        have = {(c["claim_id"], c["evidence_id"]) for c in queue}
        added = [c for c in candidates if (c["claim_id"], c["evidence_id"]) not in have]
        queue += added
        with open(QUEUE, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=1)
        print(f"\n  → {len(added)} appended to docs/curate_queue.json "
              f"(now {len(queue)}). Nothing promoted.\n")
        return 0

    with open(SIDE, "w", encoding="utf-8") as f:
        json.dump(candidates, f, ensure_ascii=False, indent=1)
    print(f"\n  → docs/curate_queue_positional.json ({len(candidates)} claims)."
          f"\n    Review, then fold in with --append. Nothing promoted.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
