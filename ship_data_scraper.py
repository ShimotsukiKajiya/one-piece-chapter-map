"""
Ship Data Scraper — pulls every named canon ship's structured data from
the wiki and saves it to ships.json. Mirrors df_scraper.py /
location_scraper.py: batched MediaWiki API, redirect resolution, local
wikitext cache.

For each ship:
  - name (en, jp, romaji)
  - type (caravel / brig / galleon / etc.)
  - affiliation (which crew it belongs to)
  - captain
  - shipwright (who built it)
  - debut chapter
  - status (active / destroyed / dormant)
  - height / length / weight / classification

Run:
  py ship_data_scraper.py             # full run
  py ship_data_scraper.py --gaps
"""
import requests, json, os, sys, time, re

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
OUT_PATH   = os.path.join(DIR, "ships.json")
CACHE_DIR  = os.path.join(DIR, "cache", "ship_wikitext")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.6
BATCH_SIZE = 50

SHIP_CATEGORIES = [
    "Category:Ships",
    "Category:Pirate_Ships",
    "Category:Marine_Ships",
    "Category:Government_Ships",
    "Category:Civilian_Ships",
]

FIELDS = {
    "jname":       "name_jp",
    "rname":       "name_romaji",
    "ename":       "name_en",
    "name":        "name_canonical",
    "type":        "type",
    "classification": "classification",
    "affiliation": "affiliation",
    "crew":        "affiliation",
    "captain":     "captain",
    "shipwright":  "shipwright",
    "first":       "first_appearance",
    "debut":       "first_appearance",
    "status":      "status",
    "fate":        "status",
    "image":       "infobox_image",
    "imagename":   "infobox_image",
    "height":      "height",
    "length":      "length",
}

INFOBOX_START_RE = re.compile(r'\{\{\s*Ship\s*Box\s*\n?\s*\|', re.IGNORECASE)


def safe(name): return re.sub(r'[^\w.\-]', '_', name)[:100]


def fetch_list_of_ships():
    print("  Fetching canon Ships across categories…")
    candidates = set()
    for cat in SHIP_CATEGORIES:
        before = len(candidates)
        params = {"action":"query","list":"categorymembers","cmtitle":cat,
                  "cmlimit":"500","format":"json"}
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
                    if title.startswith(("Category:","File:","Talk:","User:","Template:")): continue
                    if title.startswith("List of"): continue
                    candidates.add(title)
                cont = data.get("continue", {}).get("cmcontinue")
                if not cont: break
                time.sleep(0.3)
        except Exception as e:
            print(f"    ✗ {cat}: {e}"); continue
        print(f"    {cat:38s} +{len(candidates) - before}")
    return sorted(candidates)


def _api_get_many(titles):
    if not titles: return {}
    out = {t: None for t in titles}
    params = {"action":"query","prop":"revisions","rvprop":"content","rvslots":"main",
              "titles":"|".join(titles),"redirects":1,"format":"json","formatversion":"2"}
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=30)
        if r.status_code != 200: return out
        data = r.json()
    except Exception: return out
    chain = {}
    for n in data.get("query", {}).get("normalized", []): chain[n["to"]] = n["from"]
    for n in data.get("query", {}).get("redirects", []):  chain[n["to"]] = n["from"]
    requested = set(titles)
    def trace_back(t):
        seen = set(); cur = t
        while cur and cur not in requested and cur not in seen:
            seen.add(cur); cur = chain.get(cur)
        return cur
    for page in data.get("query", {}).get("pages", []):
        title = page.get("title")
        if page.get("missing"): continue
        revs = page.get("revisions") or []
        if not revs: continue
        slot = revs[0].get("slots", {}).get("main", {})
        wt = slot.get("content") or revs[0].get("content")
        req = trace_back(title) or title
        if req in out: out[req] = wt
    return out


def prefetch(names):
    os.makedirs(CACHE_DIR, exist_ok=True)
    out = {}; todo = []
    for n in names:
        p = os.path.join(CACHE_DIR, safe(n) + ".txt")
        if os.path.exists(p) and os.path.getsize(p) > 100:
            out[n] = open(p, encoding="utf-8").read()
        else: todo.append(n)
    print(f"  prefetch: {len(out)} cached · {len(todo)} to fetch")
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i+BATCH_SIZE]
        fetched = _api_get_many(batch)
        for n, wt in fetched.items():
            if wt:
                out[n] = wt
                with open(os.path.join(CACHE_DIR, safe(n)+".txt"), "w", encoding="utf-8") as f:
                    f.write(wt)
        print(f"    batch {i//BATCH_SIZE+1}: {min(i+BATCH_SIZE, len(todo))}/{len(todo)}")
        time.sleep(DELAY)
    for n in todo: out.setdefault(n, None)
    return out


def find_infobox(text):
    m = INFOBOX_START_RE.search(text)
    if not m: return None
    start = m.start(); depth = 0; i = start
    while i < len(text):
        if text[i:i+2] == "{{": depth += 1; i += 2
        elif text[i:i+2] == "}}":
            depth -= 1; i += 2
            if depth == 0: return text[start+2:i-2]
        else: i += 1
    return None


def split_top(body):
    parts = []; cur = []; b = l = 0
    for ch in body:
        if ch == "{" or ch == "[": b += (ch == "{"); l += (ch == "[")
        if ch == "}" or ch == "]": b -= (ch == "}"); l -= (ch == "]")
        if ch == "|" and b == 0 and l == 0:
            parts.append("".join(cur)); cur = []
        else: cur.append(ch)
    parts.append("".join(cur))
    return parts


def clean(v):
    if not v: return ""
    v = v.strip()
    while True:
        new = re.sub(r"\{\{[^{}]*\}\}", "", v)
        if new == v: break
        v = new
    v = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", v)
    v = re.sub(r"<ref[^>]*>.*?</ref>", "", v, flags=re.DOTALL)
    v = re.sub(r"<[^>]+>", "", v)
    v = re.sub(r"'''([^']+)'''", r"\1", v)
    v = re.sub(r"''([^']+)''", r"\1", v)
    return v.strip(" ;,")


def build(name, wt):
    rec = {"name": name, "found": False}
    if not wt: return rec
    body = find_infobox(wt)
    if not body: return rec
    rec["found"] = True
    parts = split_top(body)
    for part in parts[1:]:
        if "=" not in part: continue
        k, _, v = part.partition("=")
        k = k.strip().lower(); v = clean(v)
        if not v: continue
        target = FIELDS.get(k)
        if target:
            if target in rec and rec[target] != v:
                rec[target] = f"{rec[target]} · {v}"
            else: rec[target] = v
    fa = rec.get("first_appearance", "")
    m = re.search(r"Chapter\s+(\d{1,4})", fa)
    if m: rec["debut_chapter"] = int(m.group(1))
    return rec


def main():
    args = sys.argv[1:]
    test = "--test" in args
    gaps = "--gaps" in args
    titles = fetch_list_of_ships()
    print(f"  Found {len(titles)} candidate ship pages")
    if test: titles = titles[:5]
    existing = {}
    if os.path.exists(OUT_PATH):
        try: existing = json.load(open(OUT_PATH, encoding="utf-8"))
        except Exception: pass
    targets = [t for t in titles if t not in existing or not existing[t].get("found")] if gaps else titles
    print("=" * 60)
    print(f"  Ship Data Scraper")
    print(f"  Candidates: {len(titles)} · Existing: {len(existing)} · Targets: {len(targets)}")
    print("=" * 60); print()
    if not targets: print("  Nothing to do."); return
    wt_map = prefetch(targets)
    print()
    found = missing = 0
    for i, name in enumerate(targets, 1):
        wt = wt_map.get(name)
        rec = build(name, wt)
        existing[name] = rec
        if rec.get("found"):
            found += 1
            t = rec.get("type") or "?"
            cap = rec.get("captain") or rec.get("affiliation") or "—"
            print(f"  [{i:4d}/{len(targets)}] {name[:45]:45s}  {t[:18]:18s}  {cap[:35]}")
        else:
            missing += 1
    if not test:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    print()
    print("=" * 60)
    print(f"  Found: {found}  ·  No data: {missing}  ·  Total: {len(existing)}")
    if not test: print(f"  → {OUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
