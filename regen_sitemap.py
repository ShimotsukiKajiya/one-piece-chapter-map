"""
Regenerate sitemap.xml from the actual list of .html files in the repo.

Excludes 404.html. Priority tiers:
  index.html        1.00
  home.html         0.95
  atlas / characters 0.92
  punk-records       0.90
  sbs / theories     0.88
  everything else    0.70

Lastmod is set to today's date.

Usage:  py regen_sitemap.py
"""
import os
import sys
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://shimotsukicodex.com"

PRIORITIES = {
    "index.html":      "1.0",
    "home.html":       "0.95",
    "atlas.html":      "0.92",
    "characters.html": "0.92",
    "punk-records.html": "0.9",
    "sbs.html":        "0.88",
    "theories.html":   "0.88",
}
DEFAULT_PRIORITY = "0.7"

EXCLUDE = {"404.html"}


def main():
    files = sorted(
        f for f in os.listdir(DIR)
        if f.endswith(".html") and f not in EXCLUDE
    )
    today = date.today().isoformat()

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for f in files:
        prio = PRIORITIES.get(f, DEFAULT_PRIORITY)
        lines.append(
            f'  <url><loc>{SITE_URL}/{f}</loc>'
            f'<lastmod>{today}</lastmod>'
            f'<priority>{prio}</priority>'
            f'<changefreq>weekly</changefreq></url>'
        )
    lines.append('</urlset>')
    lines.append('')

    out_path = os.path.join(DIR, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  ✓ sitemap.xml regenerated: {len(files)} URLs · lastmod {today}")


if __name__ == "__main__":
    main()
