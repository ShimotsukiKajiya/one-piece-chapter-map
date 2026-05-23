"""
Ships Scraper
Pulls manga ship reference images from One Piece Fandom wiki and saves
them to logo/ships/ so we can use them as design references or directly
as background decorations.

Run:
  py ships_scraper.py
"""

import requests
import json
import os
import sys
import time

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
SHIPS_DIR  = os.path.join(DIR, "logo", "ships")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 1.0

# Curated list of major canon ships across the entire series.
# Each entry: (wiki_page, save_filename)
SHIPS = [
    ("Going_Merry",          "01-going-merry.png"),
    ("Thousand_Sunny",       "02-thousand-sunny.png"),
    ("Moby_Dick",            "03-moby-dick.png"),
    ("Oro_Jackson",          "04-oro-jackson.png"),
    ("Red_Force",            "05-red-force.png"),
    ("Polar_Tang",           "06-polar-tang.png"),
    ("Striker",              "07-striker.png"),
    ("Baratie",              "08-baratie.png"),
    ("Queen_Mama_Chanter",   "09-queen-mama-chanter.png"),
    ("Big_Top",              "10-big-top.png"),
    ("Maxim",                "11-maxim.png"),
    ("Going_Luffy-senpai",   "12-going-luffy-senpai.png"),
    ("Sexy_Foxy",            "13-sexy-foxy.png"),
    ("Numancia_Flamingo",    "14-numancia-flamingo.png"),
    ("Sun_Pirates_Ship",     "15-sun-pirates.png"),
    ("Black_Caravel",        "16-black-caravel.png"),
    ("Saber_of_Xebec",       "17-saber-of-xebec.png"),
    ("Victoria_Punk",        "18-victoria-punk.png"),
    ("Snake's_Head",         "19-snakes-head.png"),
    ("Stansen's_Caravel",    "20-stansens-caravel.png"),
]


def fetch_main_image(page: str) -> str | None:
    """Get the URL of the page's main infobox image."""
    # Get list of images on the page
    params = {
        "action": "parse", "page": page,
        "prop": "images", "format": "json",
    }
    r = requests.get(WIKI_API, params=params,
                     headers={"User-Agent": USER_AGENT}, timeout=20)
    if r.status_code != 200: return None
    data = r.json()
    if "error" in data or "parse" not in data: return None

    images = data["parse"].get("images", [])

    # Heuristic: first image whose name contains the ship name (lower) or 'Infobox'
    page_words = page.lower().replace("_", " ").split()
    candidate = None
    for img in images:
        img_lc = img.lower()
        if "infobox" in img_lc or any(w in img_lc for w in page_words):
            candidate = img; break
    if not candidate and images:
        candidate = images[0]
    if not candidate: return None

    # Resolve the actual URL
    info_params = {
        "action": "query", "titles": f"File:{candidate}",
        "prop": "imageinfo", "iiprop": "url", "format": "json",
    }
    r2 = requests.get(WIKI_API, params=info_params,
                      headers={"User-Agent": USER_AGENT}, timeout=15)
    pages = r2.json().get("query", {}).get("pages", {})
    for p in pages.values():
        for ii in p.get("imageinfo", []):
            return ii.get("url")
    return None


def download(url: str, dest: str) -> bool:
    if not url: return False
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30, stream=True)
        if r.status_code != 200: return False
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        return True
    except Exception as e:
        print(f"    download error: {e}")
        return False


def main():
    os.makedirs(SHIPS_DIR, exist_ok=True)

    print("=" * 55)
    print("  Ships Reference Scraper")
    print(f"  Saving to: {SHIPS_DIR}")
    print(f"  Ships to fetch: {len(SHIPS)}")
    print("=" * 55); print()

    found = 0
    for page, fname in SHIPS:
        dest = os.path.join(SHIPS_DIR, fname)
        if os.path.exists(dest):
            print(f"  {page:30s} → already saved")
            continue
        print(f"  {page:30s} → ", end="", flush=True)

        url = fetch_main_image(page)
        if not url:
            print("no image found")
            time.sleep(DELAY); continue

        if download(url, dest):
            print(f"OK ({fname})")
            found += 1
        else:
            print("download failed")

        time.sleep(DELAY)

    print()
    print(f"  ✓ Downloaded {found} new ships")
    print(f"  ✓ Total in {SHIPS_DIR}: {len(os.listdir(SHIPS_DIR))} files")
    print("=" * 55)


if __name__ == "__main__":
    main()
