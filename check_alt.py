"""
Check <img> tags for missing alt attributes.

Reports each <img> without an alt= or with alt="". A missing alt is a
real a11y issue (screen readers announce the URL). An empty alt is OK
for decorative images but flagged here for review.

Usage:  py check_alt.py
"""
import os
import re
import sys
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))
IMG_RE = re.compile(r"<img\b([^>]*)>", re.IGNORECASE)
ALT_RE = re.compile(r'\balt\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)
SRC_RE = re.compile(r'\bsrc\s*=\s*["\']([^"\']*)["\']', re.IGNORECASE)


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    missing = defaultdict(list)  # file → [ (line, src) ]
    empty   = defaultdict(list)
    total = 0

    for fn in files:
        path = os.path.join(DIR, fn)
        with open(path, encoding="utf-8") as f:
            content = f.read()

        for m in IMG_RE.finditer(content):
            attrs = m.group(1)
            line = content[: m.start()].count("\n") + 1
            src_m = SRC_RE.search(attrs)
            src = src_m.group(1) if src_m else "(no src)"
            # Skip JS-templated images that won't have alt at parse time
            if "${" in src or "{{" in src:
                continue
            total += 1
            alt_m = ALT_RE.search(attrs)
            if alt_m is None:
                missing[fn].append((line, src))
            elif alt_m.group(1).strip() == "":
                empty[fn].append((line, src))

    print(f"Scanned {len(files)} HTML files, {total} static <img> tags\n")

    print(f"  Missing alt: {sum(len(v) for v in missing.values())}")
    for fn, items in sorted(missing.items()):
        print(f"    {fn}  ({len(items)}×)")
        for line, src in items[:3]:
            print(f"      {fn}:{line}  src={src}")
        if len(items) > 3:
            print(f"      … +{len(items) - 3}")

    print(f"\n  Empty alt (review):  {sum(len(v) for v in empty.values())}")
    for fn, items in sorted(empty.items()):
        if len(items) <= 3:
            for line, src in items:
                print(f"    {fn}:{line}  src={src}")
        else:
            print(f"    {fn}  ({len(items)}×)")


if __name__ == "__main__":
    main()
