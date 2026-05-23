"""
Jolly Rogers Scraper — for each crew in crews.json, fetch the crew's
wiki page and find the Jolly Roger image (the crew flag).

Strategy: each crew's wiki page has an image like "<Crew Name>'s Jolly Roger.png"
or similar pattern. We scan the page's image list and score-match.

Run: py jolly_rogers_scraper.py
"""
import json, os, re, sys, time, requests

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
CREWS_PATH = os.path.join(DIR, "crews.json")
OUT_PATH   = os.path.join(DIR, "jolly_rogers.json")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceCodexJollyRogerScraper/1.0"
DELAY      = 0.4


def fetch_page_images(title):
    out = []
    cont = None
    for _ in range(8):
        params = {
            "action": "query", "prop": "images",
            "titles": title, "imlimit": "500",
            "format": "json", "formatversion": "2",
        }
        if cont: params["imcontinue"] = cont
        try:
            r = requests.get(WIKI_API, params=params,
                             headers={"User-Agent": USER_AGENT}, timeout=20)
            data = r.json()
        except Exception:
            return out
        for page in data.get("query", {}).get("pages", []):
            for im in page.get("images", []):
                t = im.get("title", "")
                if t.startswith("File:") and t.lower().endswith((".png", ".jpg", ".svg")):
                    out.append(t[5:])
        cont = data.get("continue", {}).get("imcontinue")
        if not cont: break
        time.sleep(0.3)
    return out


def fetch_image_url(filename):
    params = {
        "action": "query", "titles": "File:" + filename,
        "prop": "imageinfo", "iiprop": "url",
        "format": "json", "formatversion": "2",
    }
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=15)
        data = r.json()
    except Exception:
        return None
    for page in data.get("query", {}).get("pages", []):
        for ii in page.get("imageinfo", []):
            return ii.get("url")
    return None


def score_jolly_roger(crew_name, filename):
    """Score how likely a filename is a Jolly Roger for the given crew."""
    fn = filename.lower().replace("_", " ")
    cn = crew_name.lower()
    score = 0
    # Strong signals — must contain Jolly Roger / flag / Jolly_Rogers
    if "jolly roger" in fn or "jolly_roger" in fn: score += 20
    if "flag" in fn: score += 6
    if "skull" in fn: score += 3
    if "mark" in fn: score += 2
    if "symbol" in fn: score += 4
    # Crew name match (longer = more discriminating)
    crew_tokens = [t for t in cn.split() if len(t) >= 3 and t not in ("the","of","and","pirates")]
    for t in crew_tokens:
        if t in fn: score += len(t)
    # Penalise wrong contexts
    if "manga" in fn: score -= 1
    if "concept" in fn: score -= 2
    return score


def main():
    if not os.path.exists(CREWS_PATH):
        print("  ✗ crews.json not found"); return
    crews = json.load(open(CREWS_PATH, encoding="utf-8")).get("crews", {})

    existing = {}
    if os.path.exists(OUT_PATH):
        try: existing = json.load(open(OUT_PATH, encoding="utf-8")).get("rogers", {})
        except Exception: pass

    out = dict(existing)
    print(f"  → {len(crews)} crews to scan · {len(existing)} already cached")
    matched = 0
    for cname in sorted(crews.keys()):
        if cname in out and out[cname].get("url"):
            continue
        try:
            images = fetch_page_images(cname)
        except Exception as e:
            print(f"  ✗ {cname}: {e}")
            continue
        if not images:
            time.sleep(DELAY); continue
        best = None; best_score = 8
        for fn in images:
            s = score_jolly_roger(cname, fn)
            if s > best_score:
                best_score = s; best = fn
        if best:
            url = fetch_image_url(best)
            if url:
                out[cname] = {"filename": best, "url": url}
                matched += 1
                print(f"  ✓ {cname[:48]:50s} ← {best}")
                time.sleep(0.2)
        time.sleep(DELAY)

    print()
    print(f"  Matched: {matched}  ·  Total: {len(out)}")
    json.dump({"_doc": "Jolly Rogers per crew, scraped from wiki.", "rogers": out},
              open(OUT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"  ✓ {OUT_PATH}")


if __name__ == "__main__":
    main()
