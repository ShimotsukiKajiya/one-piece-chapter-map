"""
Cache Freshener — invalidate cached wikitext that's gone stale.

Walks every cache directory, asks the wiki for the current `lastrevid` of
each cached page (in batches of 50, ~free), and deletes any cache file
whose stored revid no longer matches. Next scraper run re-fetches them.

Each cache dir gets a `_revids.json` sidecar that maps cached-filename →
last-known-revid. First run populates it; subsequent runs use it as the
freshness reference.

Run:
  py freshen.py            # check all caches, delete stale entries
  py freshen.py --dry-run  # report what would be deleted, change nothing
  py freshen.py --verbose  # also print up-to-date hits
"""

import os, sys, json, requests
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
BATCH_SIZE = 50

# (cache_dir, fn_filename_to_wiki_title) — how to map a cache file name
# back to the wiki page title it represents.
CACHES = [
    # SBS volumes — both extract_names and sbs_scraper share this
    ("cache/sbs_volume_wikitext",
     lambda fn: f"SBS Volume {fn[len('vol-'):-len('.txt')]}"
                 if fn.startswith("vol-") and fn.endswith(".txt") else None),
    # Punk Records — Template:<Name> Tabs Top primary, fallback to <Name> main page
    ("cache/character_wikitext",
     lambda fn: fn[:-len(".txt")].replace("_", " ")
                 if fn.endswith(".txt") else None),
    # Cover stories
    ("cache/cover_stories_wikitext",
     lambda fn: fn[:-len(".txt")].replace("_", " ")
                 if fn.endswith(".txt") else None),
    # SBS images scraper has its own wikitext cache (per volume)
    ("cache/wikitext",
     lambda fn: f"SBS Volume {fn[len('vol-'):-len('.txt')]}"
                 if fn.startswith("vol-") and fn.endswith(".txt") else None),
]


def load_sidecar(cache_dir):
    p = os.path.join(cache_dir, "_revids.json")
    if not os.path.exists(p): return {}
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return {}


def save_sidecar(cache_dir, data):
    p = os.path.join(cache_dir, "_revids.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_revids(titles):
    """Batch-fetch current lastrevid for many wiki pages.
    Returns {title: revid_or_None}."""
    out = {t: None for t in titles}
    for i in range(0, len(titles), BATCH_SIZE):
        batch = titles[i:i + BATCH_SIZE]
        params = {
            "action": "query",
            "prop":   "info",
            "titles": "|".join(batch),
            "redirects": 1,
            "format": "json",
            "formatversion": "2",
        }
        try:
            r = requests.get(WIKI_API, params=params,
                             headers={"User-Agent": USER_AGENT}, timeout=30)
            data = r.json()
        except Exception:
            continue

        # Map normalized/redirected titles back to requested
        chain = {}
        for n in data.get("query", {}).get("normalized", []):
            chain[n["to"]] = n["from"]
        for n in data.get("query", {}).get("redirects", []):
            chain[n["to"]] = n["from"]

        def trace_back(t):
            seen = set(); cur = t
            while cur and cur not in out and cur not in seen:
                seen.add(cur); cur = chain.get(cur)
            return cur

        for page in data.get("query", {}).get("pages", []):
            if page.get("missing"): continue
            requested = trace_back(page.get("title")) or page.get("title")
            if requested in out:
                out[requested] = page.get("lastrevid")
    return out


def process_cache(cache_dir_rel, title_fn, dry, verbose):
    cache_dir = os.path.join(DIR, cache_dir_rel)
    if not os.path.isdir(cache_dir):
        return 0, 0, 0
    sidecar = load_sidecar(cache_dir)
    files = [f for f in os.listdir(cache_dir)
             if f != "_revids.json" and os.path.isfile(os.path.join(cache_dir, f))]
    title_to_file = {}
    for fn in files:
        t = title_fn(fn)
        if t: title_to_file[t] = fn

    if not title_to_file:
        return 0, 0, 0

    print(f"\n  {cache_dir_rel}  ({len(title_to_file)} cached pages)")
    revids = fetch_revids(list(title_to_file.keys()))

    fresh = stale = unknown = 0
    for title, fn in title_to_file.items():
        new_revid = revids.get(title)
        old_revid = sidecar.get(fn)
        if new_revid is None:
            unknown += 1
            if verbose: print(f"    ?  {title}  (no revid returned)")
            continue
        if old_revid is None:
            # First time we've seen this cache file — record current revid,
            # but don't delete (treat as fresh)
            sidecar[fn] = new_revid
            fresh += 1
            if verbose: print(f"    +  {title}  rev={new_revid} (recorded)")
        elif old_revid == new_revid:
            fresh += 1
            if verbose: print(f"    ✓  {title}  rev={new_revid}")
        else:
            stale += 1
            print(f"    ✗  {title}  rev {old_revid} → {new_revid}{' (would delete)' if dry else ' (deleted)'}")
            if not dry:
                try: os.remove(os.path.join(cache_dir, fn))
                except OSError: pass
                sidecar[fn] = new_revid  # next fetch will write fresh content

    if not dry:
        save_sidecar(cache_dir, sidecar)
    return fresh, stale, unknown


def main():
    dry     = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    print("=" * 60)
    print("  Cache Freshener" + ("  (dry run)" if dry else ""))
    print("=" * 60)

    total_fresh = total_stale = total_unknown = 0
    for cache_dir, title_fn in CACHES:
        f, s, u = process_cache(cache_dir, title_fn, dry, verbose)
        total_fresh += f; total_stale += s; total_unknown += u

    print()
    print("=" * 60)
    print(f"  Fresh:   {total_fresh}")
    print(f"  Stale:   {total_stale}{' (would be deleted)' if dry else ' (deleted)'}")
    print(f"  Unknown: {total_unknown}")
    print("=" * 60)

    if dry and total_stale:
        print("  Run again without --dry-run to actually invalidate stale entries.")


if __name__ == "__main__":
    main()
