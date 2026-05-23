"""
Volume Covers Scraper
Fetches the tankoubon cover image URL for each volume from the Fandom wiki
and saves to volume_covers.json — used by sbs.html to show covers in
volume headers.

Run:
  py covers_scraper.py        # scrape all volumes
  py covers_scraper.py --test # first 5 only
"""

import requests
import json
import os
import re
import sys
import time

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(__file__)
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.8

START_VOLUME = 1
END_VOLUME   = 112
PROBE_AHEAD  = 3   # how many volumes past the known max to probe each run

OUTPUT_FILE = os.path.join(DIR, "volume_covers.json")


def fetch_cover_url(vol: int) -> str | None:
    """Fetch the cover image URL for a tankoubon volume page."""
    # Use parse + images to get image filenames on the page
    params = {
        "action": "parse",
        "page":   f"Volume_{vol}",
        "prop":   "images|wikitext",
        "format": "json",
    }
    try:
        resp = requests.get(WIKI_API, params=params,
                            headers={"User-Agent": USER_AGENT}, timeout=20)
    except Exception as e:
        print(f"    ✗ vol {vol} network error: {e}")
        return None

    if resp.status_code != 200:
        return None

    data = resp.json()
    if "error" in data or "parse" not in data:
        return None

    wikitext = data["parse"].get("wikitext", {}).get("*", "")
    images   = data["parse"].get("images", [])

    # Try to find the cover image — wikitext has |image=Volume X.png style
    cover_match = re.search(r'\|image\s*=\s*([^\|\n]+)', wikitext)
    if cover_match:
        candidate = cover_match.group(1).strip()
    else:
        # Fall back: first image whose name starts with Volume
        candidate = next((i for i in images if i.lower().startswith("volume")), None)

    if not candidate:
        return None

    # Now resolve the full URL via imageinfo API
    info_params = {
        "action":  "query",
        "titles":  f"File:{candidate}",
        "prop":    "imageinfo",
        "iiprop":  "url",
        "format":  "json",
    }
    try:
        info_resp = requests.get(WIKI_API, params=info_params,
                                 headers={"User-Agent": USER_AGENT}, timeout=15)
        pages = info_resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            for ii in page.get("imageinfo", []):
                return ii.get("url")
    except Exception:
        pass

    return None


def main():
    test = "--test" in sys.argv
    gaps = "--gaps" in sys.argv  # alias — covers_scraper is already gap-aware

    # Load existing if any
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            covers = json.load(f)
    else:
        covers = {}

    # Auto-extend: probe a few volumes past the highest known one so new
    # tankoubon get picked up without needing to bump END_VOLUME by hand.
    known_max = max((int(k) for k in covers.keys()), default=0)
    end = max(END_VOLUME, known_max + PROBE_AHEAD)
    if test: end = START_VOLUME + 5

    print("=" * 55)
    print("  Volume Covers Scraper")
    print(f"  Volumes: {START_VOLUME} → {end}  ({len(covers)} cached)")
    if test: print("  (test mode — 5 volumes only)")
    if gaps: print("  (--gaps mode — same as default; covers is gap-aware)")
    print("=" * 55)
    print()

    found = 0
    for vol in range(START_VOLUME, end + 1):
        if str(vol) in covers and covers[str(vol)]:
            print(f"  Vol {vol:3d} → already cached")
            continue

        print(f"  Vol {vol:3d} → fetching…", end=" ", flush=True)
        url = fetch_cover_url(vol)
        if url:
            covers[str(vol)] = url
            found += 1
            print("OK")
        else:
            print("not found")

        # Save after each so progress isn't lost
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(covers, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY)

    print()
    print(f"  ✓ Total covers in archive: {len(covers)}")
    print(f"  ✓ Added this run: {found}")
    print(f"  Written → {OUTPUT_FILE}")
    print("=" * 55)


if __name__ == "__main__":
    main()
