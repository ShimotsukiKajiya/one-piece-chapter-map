"""
Check internal HTML links for broken refs.

Scans every .html file for href="something.html" or href="something.html#anchor"
and verifies the target file exists in the project root. Reports broken refs
with the source file and line number.

Skips:
  - external URLs (http://, https://, mailto:, #anchors only)
  - empty href / javascript: / data: schemes

Usage:  py check_links.py
"""
import os
import re
import sys
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))

HREF_RE = re.compile(r'href=["\']([^"\']+?)["\']', re.IGNORECASE)


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    existing = set(files)
    broken = defaultdict(list)  # target → [ (source, line_num, full_href) ]
    total_internal = 0

    for src in files:
        path = os.path.join(DIR, src)
        with open(path, encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                for href in HREF_RE.findall(line):
                    # External / non-html
                    if href.startswith(("http://", "https://", "mailto:", "javascript:", "data:", "#", "tel:")):
                        continue
                    # Strip fragment
                    target = href.split("#", 1)[0].split("?", 1)[0]
                    if not target:
                        continue
                    # Only check .html targets (skip .css, .js, .json, images, manifest, etc.)
                    if not target.endswith(".html"):
                        continue
                    total_internal += 1
                    if target not in existing:
                        broken[target].append((src, line_num, href))

    print(f"Scanned {len(files)} HTML files, {total_internal} internal HTML links\n")

    if not broken:
        print("  ✓ All internal HTML links resolve.")
        return

    print(f"  ✗ {sum(len(v) for v in broken.values())} broken refs to {len(broken)} missing targets:\n")
    for target, refs in sorted(broken.items()):
        print(f"  → {target}  (referenced {len(refs)}×)")
        for src, line_num, href in refs[:5]:
            print(f"      {src}:{line_num}  {href}")
        if len(refs) > 5:
            print(f"      … and {len(refs) - 5} more")
        print()


if __name__ == "__main__":
    main()
