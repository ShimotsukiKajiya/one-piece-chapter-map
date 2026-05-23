"""
Devil Fruit Scraper — pulls every canon Devil Fruit's data from the wiki
and saves it to devil_fruits.json. Mirrors the architecture of
punk_records_scraper.py: batched MediaWiki API, redirect resolution,
local wikitext cache.

For each fruit:
  - name (English, Japanese, romanised)
  - meaning / translation
  - type (Paramecia / Zoan / Logia / Mythical Zoan / Ancient Zoan)
  - current user / former users
  - awakening status
  - debut chapter
  - infobox image (we only store the wiki filename — fetch URLs separately
    via portrait_scraper.py if/when we want fruit thumbnails baked)

Run:
  py df_scraper.py             # full run
  py df_scraper.py --gaps      # only fruits not yet in devil_fruits.json
  py df_scraper.py --test      # 5 sample fruits, dry-run
"""
import requests, json, os, sys, time, re

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
OUT_PATH   = os.path.join(DIR, "devil_fruits.json")
CACHE_DIR  = os.path.join(DIR, "cache", "df_wikitext")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.6
BATCH_SIZE = 50

# Field map: wiki Devil Fruit infobox param → our schema field
FIELDS = {
    "jname":          "name_jp",
    "ename":          "name_en",
    "rname":          "name_romaji",
    "name":           "name_canonical",
    "meaning":        "translation",
    "translation":    "translation",
    "type":           "type",
    "category":       "type",
    "user":           "user_current",
    "users":          "user_history",
    "previous user":  "user_previous",
    "previous users": "user_previous",
    "former user":    "user_previous",
    "former users":   "user_previous",
    "first":          "first_appearance",
    "debut":          "first_appearance",
    "creator":        "creator",
    "english name":   "name_en",
    "japanese name":  "name_jp",
    "awakened":       "awakened",
    "awakening":      "awakening",
    "image":          "infobox_image",
    "imagename":      "infobox_image",
}

INFOBOX_START_RE = re.compile(r'\{\{\s*Devil\s*Fruit\s*Box\s*\n?\s*\|', re.IGNORECASE)


def safe(name):
    return re.sub(r'[^\w.\-]', '_', name)[:100]


DF_CATEGORIES = [
    "Category:Paramecia",
    "Category:Logia",
    "Category:Zoan",
    "Category:Mythical_Zoan",
    "Category:Ancient_Zoan",
    "Category:Artificial_Devil_Fruits",
    "Category:Awakened_Devil_Fruits",
    "Category:Canon_Devil_Fruits",
]


def fetch_list_of_fruits():
    """Walk every Devil Fruit category to enumerate every named fruit."""
    print("  Fetching canon Devil Fruits across categories…")
    candidates = set()
    for cat in DF_CATEGORIES:
        before = len(candidates)
        params = {
            "action":  "query",
            "list":    "categorymembers",
            "cmtitle": cat,
            "cmlimit": "500",
            "format":  "json",
        }
        try:
            cont = None
            for _ in range(20):
                p = dict(params)
                if cont: p["cmcontinue"] = cont
                r = requests.get(WIKI_API, params=p,
                                 headers={"User-Agent": USER_AGENT}, timeout=20)
                data = r.json()
                for m in data.get("query", {}).get("categorymembers", []):
                    title = m.get("title", "")
                    if title.startswith(("Category:", "File:", "Talk:", "User:")): continue
                    # Heuristic: a real fruit page contains "no Mi" OR "Fruit" in title
                    if " no Mi" in title or "Fruit" in title:
                        candidates.add(title)
                cont = data.get("continue", {}).get("cmcontinue")
                if not cont: break
                time.sleep(0.3)
        except Exception as e:
            print(f"    ✗ {cat}: {e}")
            continue
        added = len(candidates) - before
        print(f"    {cat:40s} +{added}")
    return sorted(candidates)


# ── BATCH FETCH (mirrors punk_records_scraper.py pattern) ───────
def _api_get_many(titles):
    if not titles: return {}
    out = {t: None for t in titles}
    params = {
        "action":    "query",
        "prop":      "revisions",
        "rvprop":    "content",
        "rvslots":   "main",
        "titles":    "|".join(titles),
        "redirects": 1,
        "format":    "json",
        "formatversion": "2",
    }
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code != 200: return out
        data = r.json()
    except Exception:
        return out

    chain = {}
    for n in data.get("query", {}).get("normalized", []): chain[n["to"]] = n["from"]
    for n in data.get("query", {}).get("redirects", []):  chain[n["to"]] = n["from"]
    requested_set = set(titles)
    def trace_back(t):
        seen = set(); cur = t
        while cur and cur not in requested_set and cur not in seen:
            seen.add(cur); cur = chain.get(cur)
        return cur

    for page in data.get("query", {}).get("pages", []):
        title = page.get("title")
        if page.get("missing"): continue
        revs = page.get("revisions") or []
        if not revs: continue
        slot = revs[0].get("slots", {}).get("main", {})
        wt = slot.get("content") or revs[0].get("content")
        requested = trace_back(title) or title
        if requested in out:
            out[requested] = wt
    return out


def _cache_path(name):
    return os.path.join(CACHE_DIR, safe(name) + ".txt")


def prefetch(names):
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = {}
    todo = []
    for n in names:
        p = _cache_path(n)
        if os.path.exists(p) and os.path.getsize(p) > 100:
            out[n] = open(p, encoding="utf-8").read()
        else:
            todo.append(n)
    print(f"  prefetch: {len(out)} cached · {len(todo)} to fetch")

    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i + BATCH_SIZE]
        fetched = _api_get_many(batch)
        for n, wt in fetched.items():
            if wt:
                out[n] = wt
                with open(_cache_path(n), "w", encoding="utf-8") as f:
                    f.write(wt)
        end = min(i + BATCH_SIZE, len(todo))
        print(f"    batch {i//BATCH_SIZE + 1}: {end}/{len(todo)}")
        time.sleep(DELAY)
    for n in todo: out.setdefault(n, None)
    return out


# ── INFOBOX PARSE ───────────────────────────────────────────────
def find_infobox(text):
    m = INFOBOX_START_RE.search(text)
    if not m: return None
    start = m.start()
    depth = 0; i = start
    while i < len(text):
        if text[i:i+2] == "{{": depth += 1; i += 2
        elif text[i:i+2] == "}}":
            depth -= 1; i += 2
            if depth == 0: return text[start+2:i-2]
        else: i += 1
    return None


def split_top_level(body):
    parts = []; cur = []; depth_b = depth_l = 0
    for ch in body:
        if ch == "{" or ch == "[": depth_b += (ch == "{"); depth_l += (ch == "[")
        if ch == "}" or ch == "]": depth_b -= (ch == "}"); depth_l -= (ch == "]")
        if ch == "|" and depth_b == 0 and depth_l == 0:
            parts.append("".join(cur)); cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def clean_value(v):
    if not v: return ""
    v = v.strip()
    # Strip nested templates aggressively (we lose some content but it's safer)
    while True:
        new = re.sub(r"\{\{[^{}]*\}\}", "", v)
        if new == v: break
        v = new
    # [[Link|Display]] → Display; [[Page]] → Page
    v = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", v)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.DOTALL)
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"'''([^']+)'''", r"\1", v)
    v = re.sub(r"''([^']+)''", r"\1", v)
    return v.strip(" ;,")


def build_record(name, wt):
    rec = {"name": name, "found": False, "raw_keys": []}
    if not wt: return rec
    body = find_infobox(wt)
    if not body: return rec
    rec["found"] = True
    parts = split_top_level(body)
    for part in parts[1:]:  # skip the leading "Devil Fruit Infobox"
        if "=" not in part: continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        v = clean_value(v)
        if not v: continue
        rec["raw_keys"].append(k)
        target = FIELDS.get(k)
        if target:
            # Multi-value fields can appear (users, etc.) — separate with " · "
            if target in rec and rec[target] != v:
                rec[target] = f"{rec[target]} · {v}"
            else:
                rec[target] = v

    # Derive debut chapter as int if first_appearance contains "Chapter N"
    fa = rec.get("first_appearance", "")
    m = re.search(r"Chapter\s+(\d{1,4})", fa)
    if m: rec["debut_chapter"] = int(m.group(1))

    # Type normalisation — always lowercased canonical form
    t = (rec.get("type") or "").lower()
    if "ancient" in t and "zoan" in t: rec["type_canonical"] = "Ancient Zoan"
    elif "mythical" in t and "zoan" in t: rec["type_canonical"] = "Mythical Zoan"
    elif "logia" in t:    rec["type_canonical"] = "Logia"
    elif "zoan" in t:     rec["type_canonical"] = "Zoan"
    elif "paramecia" in t:rec["type_canonical"] = "Paramecia"
    return rec


# ── MAIN ────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    test = "--test" in args
    gaps = "--gaps" in args

    titles = fetch_list_of_fruits()
    print(f"  Found {len(titles)} candidate Devil Fruit pages")

    if test: titles = titles[:5]

    existing = {}
    if os.path.exists(OUT_PATH):
        try: existing = json.load(open(OUT_PATH, encoding="utf-8"))
        except Exception: pass

    if gaps:
        targets = [t for t in titles if t not in existing or not existing[t].get("found")]
    else:
        targets = titles

    print("=" * 60)
    print(f"  Devil Fruit Scraper")
    print(f"  Total candidates : {len(titles)}")
    print(f"  Existing records : {len(existing)}")
    print(f"  Targets this run : {len(targets)}{' (TEST)' if test else ''}")
    print("=" * 60); print()

    if not targets:
        print("  Nothing to do.")
        return

    wt_map = prefetch(targets)
    print()
    found = missing = 0
    for i, name in enumerate(targets, 1):
        wt = wt_map.get(name)
        rec = build_record(name, wt)
        existing[name] = rec
        if rec.get("found"):
            found += 1
            t = rec.get("type_canonical") or rec.get("type") or "?"
            print(f"  [{i:4d}/{len(targets)}] {name[:50]:50s}  {t}")
        else:
            missing += 1
            print(f"  [{i:4d}/{len(targets)}] {name[:50]:50s}  — no infobox")

    if not test:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"  Found    : {found}")
    print(f"  No data  : {missing}")
    print(f"  Total    : {len(existing)}")
    if not test: print(f"  → {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
