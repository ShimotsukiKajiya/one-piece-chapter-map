"""
Portrait Scraper — quick first pass at character images for Punk Records.

For each character with `found:true` in punk_records.json, asks the wiki
for the page's representative image (the MediaWiki `pageimages` API,
which returns whatever the wiki itself uses as the page thumbnail —
usually the Char Box infobox image).

Batches 50 characters per HTTP request and resolves wiki redirects so
nicknames like "Brownbeard" follow through to "Chadros Higelyges". Saves
to portraits.json keyed by canonical name:

  { "Monkey D. Luffy": { "thumb": "https://...200px.jpg", "source": "..." }, ... }

Run:
  py portrait_scraper.py             # gap-fill (default — only fetch missing)
  py portrait_scraper.py --refresh   # re-fetch even existing entries
  py portrait_scraper.py --top 200   # only top-N most-appearing characters
  py portrait_scraper.py --test      # dry-run on 5 chars, no save
"""
import requests, json, os, sys, time

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
PUNK_PATH  = os.path.join(DIR, "punk_records.json")
OUT_PATH   = os.path.join(DIR, "portraits.json")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.6
BATCH_SIZE = 50
THUMB_SIZE = 240


def load_records():
    if not os.path.exists(PUNK_PATH):
        print("  ✗ punk_records.json not found — run punk_records_scraper.py first")
        sys.exit(1)
    with open(PUNK_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_portraits():
    if not os.path.exists(OUT_PATH): return {}
    try: return json.load(open(OUT_PATH, encoding="utf-8"))
    except Exception: return {}


def save_portraits(p):
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=2)


def fetch_batch(names):
    """Returns {name: {thumb, source}} for the batch. Missing entries omitted."""
    out = {}
    params = {
        "action":      "query",
        "prop":        "pageimages",
        "piprop":      "thumbnail|name",
        "pithumbsize": THUMB_SIZE,
        "titles":      "|".join(names),
        "redirects":   1,
        "format":      "json",
        "formatversion": "2",
    }
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code != 200: return out
        data = r.json()
    except Exception as e:
        print(f"    ✗ batch error: {e}")
        return out

    # Map normalized + redirected titles back to what we requested
    chain = {}
    for n in data.get("query", {}).get("normalized", []):
        chain[n["to"]] = n["from"]
    for n in data.get("query", {}).get("redirects", []):
        chain[n["to"]] = n["from"]

    requested_set = set(names)
    def trace_back(t):
        seen = set(); cur = t
        while cur and cur not in requested_set and cur not in seen:
            seen.add(cur); cur = chain.get(cur)
        return cur

    for page in data.get("query", {}).get("pages", []):
        title = page.get("title")
        thumb = page.get("thumbnail", {})
        if not thumb: continue
        url = thumb.get("source")
        if not url: continue
        requested = trace_back(title) or title
        if requested in requested_set:
            out[requested] = {
                "thumb":  url,
                "width":  thumb.get("width"),
                "height": thumb.get("height"),
                "wiki_page_image": page.get("pageimage"),
            }
    return out


def main():
    args = sys.argv[1:]
    test    = "--test" in args
    refresh = "--refresh" in args
    top = None
    if "--top" in args:
        i = args.index("--top")
        try: top = int(args[i + 1])
        except: pass

    records = load_records()
    existing = load_portraits()

    # Pick targets — characters with found:true, sorted by appearance count desc
    candidates = [
        (name, rec.get("appearances", 0))
        for name, rec in records.items()
        if rec.get("found")
    ]
    candidates.sort(key=lambda x: -(x[1] or 0))
    if top: candidates = candidates[:top]

    if refresh:
        targets = [n for n, _ in candidates]
    else:
        targets = [n for n, _ in candidates if n not in existing]

    if test: targets = targets[:5]

    print("=" * 60)
    print("  Portrait Scraper")
    print(f"  Records w/ found:true : {len(candidates)}")
    print(f"  Existing portraits    : {len(existing)}")
    print(f"  To fetch this run     : {len(targets)}{' (TEST — no save)' if test else ''}")
    print(f"  Batches               : {(len(targets) + BATCH_SIZE - 1) // BATCH_SIZE}")
    print("=" * 60); print()

    if not targets:
        print("  Nothing to do.")
        return

    fetched = 0
    for i in range(0, len(targets), BATCH_SIZE):
        batch = targets[i:i + BATCH_SIZE]
        result = fetch_batch(batch)
        if not test:
            existing.update(result)
        fetched += len(result)
        end = min(i + BATCH_SIZE, len(targets))
        print(f"  batch {i//BATCH_SIZE + 1:>3} ({end:>4}/{len(targets)}): "
              f"got {len(result)}/{len(batch)} thumbnails")
        # Periodic save in case of long run
        if not test and (i // BATCH_SIZE) % 5 == 4:
            save_portraits(existing)
        time.sleep(DELAY)

    if not test:
        save_portraits(existing)

    print()
    print("=" * 60)
    print(f"  ✓ Fetched {fetched} new portraits  (total: {len(existing)})")
    if not test: print(f"  → {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
