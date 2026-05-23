"""
Sync og:description and twitter:description to match each page's
<meta name="description"> content.

Pages were given page-specific meta descriptions in a prior pass, but
the og:description / twitter:description tags still hold the boilerplate
site description from when the OG block was first added. This script
copies the page-specific description into those OG/Twitter tags so
social shares show the right context.

Usage:  py sync_og_desc.py
"""
import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))

DESC_RE   = re.compile(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', re.IGNORECASE)
OGDESC_RE = re.compile(r'(<meta\s+property=["\']og:description["\']\s+content=)["\']([^"\']*)["\']', re.IGNORECASE)
TWDESC_RE = re.compile(r'(<meta\s+name=["\']twitter:description["\']\s+content=)["\']([^"\']*)["\']', re.IGNORECASE)


def patch_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        html = f.read()

    desc_m = DESC_RE.search(html)
    if not desc_m:
        return "no-description"
    desc = desc_m.group(1)

    new_html, og_count = OGDESC_RE.subn(rf'\g<1>"{desc}"', html)
    new_html, tw_count = TWDESC_RE.subn(rf'\g<1>"{desc}"', new_html)

    if og_count == 0 and tw_count == 0:
        return "no-og-tags"
    if new_html == html:
        return "already-synced"

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return f"synced (og:{og_count}, tw:{tw_count})"


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    counts = {"synced": 0, "no-description": 0, "no-og-tags": 0, "already-synced": 0}
    for fn in files:
        result = patch_file(os.path.join(DIR, fn))
        key = "synced" if result.startswith("synced") else result
        counts[key] += 1
        marker = "✓" if key == "synced" else "·"
        print(f"  {marker} {fn:<28} {result}")

    print()
    for k, v in counts.items():
        if v: print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
