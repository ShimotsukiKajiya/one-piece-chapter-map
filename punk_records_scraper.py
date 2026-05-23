"""
Punk Records — character dossier scraper.

For each character known to the Codex (from appearances.csv), this fetches
their wiki page, parses the {{Character infobox|...}} template, and
extracts structured canon data into punk_records.json.

Modes:
  py punk_records_scraper.py --test           # 5 sample characters, dry-run
  py punk_records_scraper.py --inspect Luffy  # parse one character, print full result
  py punk_records_scraper.py --top 200        # top 200 most-appearing characters
  py punk_records_scraper.py                  # FULL run (every named character)
  py punk_records_scraper.py --gaps           # only characters not yet in punk_records.json

Cache:
  Raw wikitext cached to cache/character_wikitext/{name}.txt — re-parses
  without re-fetching.
"""

import requests, json, os, re, sys, time, csv
from collections import Counter

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

# ── PATHS ────────────────────────────────────────────────────────
DIR        = os.path.dirname(__file__)
CSV_PATH   = os.path.join(DIR, "appearances.csv")
OUTPUT     = os.path.join(DIR, "punk_records.json")
BACKUP     = os.path.join(DIR, "punk_records.backup.json")
CACHE_DIR  = os.path.join(DIR, "cache", "character_wikitext")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.6

# ── INFOBOX FIELD MAP ────────────────────────────────────────────
# Maps wiki Char Box param → our schema field. The wiki uses many
# variants (with/without spaces, plurals, etc.); each canonical key on
# the right may have multiple sources on the left.
FIELDS = {
    # Names
    "jname":           "name_jp",
    "jpname":          "name_jp",
    "rname":           "name_romaji",
    "ename":           "name_en",
    "name":            "name_canonical",
    # Identity
    "epithet":         "epithet",
    "alias":           "epithet",
    "age":             "age",
    "ages":            "age",
    "birthday":        "birthday",
    "birth":           "birthday",
    "height":          "height",
    "weight":          "weight",
    "blood type":      "blood_type",
    "bloodtype":       "blood_type",
    "blood":           "blood_type",
    "status":          "status",
    # Roles
    "occupation":      "occupation",
    "occupations":     "occupation",
    "position":        "occupation",
    "affiliation":     "affiliation",
    "affiliations":    "affiliation",
    "previous affiliation": "affiliation_former",
    # Geography
    "origin":          "origin",
    "residence":       "residence",
    # Debut
    "first":           "first_appearance",
    "debut":           "first_appearance",
    # Devil Fruit
    "dfname":          "devil_fruit_name",
    "dfename":         "devil_fruit_name_en",
    "dfmeaning":       "devil_fruit_translation",
    "dftype":          "devil_fruit_type",
    "df":              "devil_fruit_name",
    # Combat
    "haki":            "haki",
    "weapons":         "weapons",
    # Family
    "family":          "family",
    "relatives":       "family",
    # Bounty
    "bounty":          "bounty",
    "bounties":        "bounty",
    # Visual
    "imagename":       "infobox_image",
    "image":           "infobox_image",
    # Voice actors (less critical but useful)
    "jva":             "voice_actor_jp",
    "funi english va": "voice_actor_en",
    "funi eva":        "voice_actor_en",
    "4kids eva":       "voice_actor_en_4kids",
    "odex eva":        "voice_actor_en_odex",
    "liveaction":      "actor_live_action",
}


def safe_filename(name):
    return re.sub(r'[^\w.\-]', '_', name)[:100]


# ── FETCH ────────────────────────────────────────────────────────
def _api_get(page):
    params = {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200: return None
        data = r.json()
        if "error" in data: return None
        return data.get("parse", {}).get("wikitext", {}).get("*")
    except Exception:
        return None


def _cache_path(name):
    return os.path.join(CACHE_DIR, safe_filename(name) + ".txt")


def _read_cache(name):
    p = _cache_path(name)
    if os.path.exists(p) and os.path.getsize(p) > 100:
        with open(p, encoding="utf-8") as f:
            return f.read()
    return None


def _write_cache(name, wt):
    if not wt: return
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(name), "w", encoding="utf-8") as f:
        f.write(wt)


def fetch_wikitext(name):
    """Single-page fetch with cache. Tabs Top first, then main page fallback."""
    cached = _read_cache(name)
    if cached: return cached
    wt = _api_get(f"Template:{name} Tabs Top")
    if not wt or "{{Char Box" not in wt:
        wt = _api_get(name)
    _write_cache(name, wt)
    return wt


# ── BATCH FETCH ──────────────────────────────────────────────────
# MediaWiki accepts up to 50 titles per `action=query&prop=revisions` call.
# This collapses ~1000 requests → ~20 for a full Punk Records scrape.
BATCH_SIZE = 50


def _api_get_many(titles):
    """Batch wikitext fetch. Returns {title: wikitext_or_None}.

    Auto-follows wiki redirects (e.g. "Brownbeard" → "Chadros Higelyges")
    and stitches the resolved content back under the originally-requested title.
    """
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

    # Build a chain that maps the FINAL resolved title back to what we asked for.
    # The API returns separate `normalized` (case/underscore tweaks) and
    # `redirects` (page-level redirects) blocks. Either may chain.
    chain = {}  # to → from
    for n in data.get("query", {}).get("normalized", []):
        chain[n["to"]] = n["from"]
    for n in data.get("query", {}).get("redirects", []):
        chain[n["to"]] = n["from"]

    def trace_back(title):
        # Walk to → from until we hit one of our requested titles
        seen = set()
        cur = title
        while cur and cur not in out and cur not in seen:
            seen.add(cur)
            cur = chain.get(cur)
        return cur

    for page in data.get("query", {}).get("pages", []):
        title = page.get("title")
        if page.get("missing"): continue
        revs = page.get("revisions") or []
        if not revs: continue
        slot = revs[0].get("slots", {}).get("main", {})
        wt = slot.get("content") or revs[0].get("content") or revs[0].get("*")
        requested = trace_back(title) or title
        if requested in out:
            out[requested] = wt
    return out


def prefetch_wikitext(names, verbose=True):
    """Cache-aware batch prefetch for many characters.

    Strategy:
      1. Skip anything already cached
      2. Batch-fetch Template:<name> Tabs Top in groups of 50
      3. For pages with no Tabs Top (or no Char Box in it), batch-fetch
         the main <name> page as fallback
      4. Write everything to cache and return {name: wikitext_or_None}
    """
    result = {}
    todo = []
    for n in names:
        c = _read_cache(n)
        if c is not None:
            result[n] = c
        else:
            todo.append(n)

    if verbose:
        print(f"  prefetch: {len(result)} cached · {len(todo)} to fetch in batches of {BATCH_SIZE}")

    # Pass 1: Tabs Top templates
    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i:i + BATCH_SIZE]
        title_map = {f"Template:{n} Tabs Top": n for n in batch}
        fetched = _api_get_many(list(title_map.keys()))
        for title, wt in fetched.items():
            n = title_map[title]
            if wt and "{{Char Box" in wt:
                result[n] = wt
                _write_cache(n, wt)
        if verbose:
            done = min(i + BATCH_SIZE, len(todo))
            print(f"    Tabs Top batch {i//BATCH_SIZE + 1}: {done}/{len(todo)}")
        time.sleep(DELAY)

    # Pass 2: main-page fallback for any char with no Tabs Top hit
    fallback = [n for n in todo if n not in result]
    for i in range(0, len(fallback), BATCH_SIZE):
        batch = fallback[i:i + BATCH_SIZE]
        fetched = _api_get_many(batch)
        for n, wt in fetched.items():
            if wt:
                result[n] = wt
                _write_cache(n, wt)
        if verbose:
            done = min(i + BATCH_SIZE, len(fallback))
            print(f"    main-page fallback {i//BATCH_SIZE + 1}: {done}/{len(fallback)}")
        time.sleep(DELAY)

    # Anything still missing
    for n in todo:
        result.setdefault(n, None)
    return result


# ── PARSE INFOBOX ────────────────────────────────────────────────
# Wiki uses {{Char Box | name = ... | jname = ... ...}} — body ends at
# matching }} (need to account for nested templates).
INFOBOX_START_RE = re.compile(r'\{\{Char\s*Box\s*\n?\s*\|', re.IGNORECASE)


def find_char_box(text):
    """Locate {{Char Box ...}} and return its inner body (without the outer braces)."""
    m = INFOBOX_START_RE.search(text)
    if not m:
        return None
    # Find matching }} accounting for nested {{ }}
    depth = 1
    i = m.end()
    while i < len(text) - 1:
        if text[i:i+2] == '{{': depth += 1; i += 2; continue
        if text[i:i+2] == '}}':
            depth -= 1
            if depth == 0:
                # Inner body is from after the opening 'Char Box | ' to here
                inner_start = m.end() - 1   # include leading |
                return text[inner_start:i]
            i += 2; continue
        i += 1
    return None


def _strip_balanced_template(text, name_pattern):
    """Strip {{name...}} including any nested templates by depth-tracking."""
    out = []
    i = 0
    while i < len(text):
        m = re.match(r'\{\{(' + name_pattern + r')\b', text[i:], re.IGNORECASE)
        if m:
            depth = 1
            j = i + m.end()
            while j < len(text) - 1 and depth:
                if text[j:j+2] == '{{': depth += 1; j += 2
                elif text[j:j+2] == '}}': depth -= 1; j += 2
                else: j += 1
            i = j
            continue
        out.append(text[i])
        i += 1
    return ''.join(out)


def clean_value(v):
    """Strip wiki markup from a single field value."""
    if not v: return ""
    # 1) Strip citation templates entirely — {{Qref|...}}, {{Status|...}},
    #    {{Portal|...}}, {{Featured Article|...}}. Depth-aware.
    for tname in ('Qref', 'Status', 'Portal', 'Featured Article', 'See',
                  'For', 'Which volume', 'Reflist', 'References'):
        v = _strip_balanced_template(v, tname)
    # 2) {{B}} = berry symbol → ฿
    v = re.sub(r'\{\{[Bb]\}\}', '฿', v)
    # 3) {{Ruby|main|reading}} → main
    v = re.sub(r'\{\{Ruby\|([^|}]+)\|[^}]+\}\}', r'\1', v)
    # 4) {{Nihongo|english|kanji|romaji|extra}} → english
    v = re.sub(r'\{\{Nihongo\|([^|}]+)(?:\|[^}]*)?\}\}', r'\1', v, flags=re.IGNORECASE)
    # 5) {{W|page|display}} → display, {{W|page}} → page
    v = re.sub(r'\{\{W\|([^|}]+)\|([^}]+)\}\}', r'\2', v, flags=re.IGNORECASE)
    v = re.sub(r'\{\{W\|([^|}]+)\}\}', r'\1', v, flags=re.IGNORECASE)
    # 6) {{N/A}} → N/A
    v = re.sub(r'\{\{[Nn]/[Aa]\}\}', 'N/A', v)
    # 7) Strip [[File:...]] entirely
    v = re.sub(r'\[\[(?:File|Image):[^\]]+(?:\|[^\]]+)*\]\]', '', v, flags=re.IGNORECASE)
    # 8) [[Link|Display]] → Display, [[Link]] → Link
    v = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', v)
    # 9) External wiki links [https://url label] → label
    v = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', v)
    # 10) Strip <ref...>...</ref> and other HTML tags
    v = re.sub(r'<ref[^>]*>.*?</ref>', '', v, flags=re.DOTALL | re.IGNORECASE)
    v = re.sub(r'<ref[^/]*/>', '', v, flags=re.IGNORECASE)
    v = re.sub(r'<br\s*/?>', ' · ', v, flags=re.IGNORECASE)
    v = re.sub(r'<[^>]+>', '', v)
    # 11) Bold/italic
    v = re.sub(r"'''([^']+)'''", r'\1', v)
    v = re.sub(r"''([^']+)''", r'\1', v)
    # 12) Bullet/asterisk leaders
    v = re.sub(r'^\s*\*\s*', '', v, flags=re.MULTILINE)
    # 13) Strip any remaining unmatched stray template fragments (best-effort)
    v = re.sub(r'\{\{[^}]{0,80}\}\}', '', v)
    # 14) Collapse whitespace + excessive separators
    v = re.sub(r'\s*·(?:\s*·)+\s*', ' · ', v)
    v = re.sub(r';\s*·', ';', v)
    v = re.sub(r'\s+', ' ', v).strip(" ·;,")
    return v


def parse_infobox(wikitext):
    """Extract the infobox key/value pairs into a dict."""
    if not wikitext: return None
    body = find_char_box(wikitext)
    if not body:
        return None
    # Split on top-level | — but ignore | inside templates {{...}} or [[...]]
    fields = {}
    depth_curly = depth_square = 0
    cur = []
    pieces = []
    for ch in body:
        if ch == '{':
            depth_curly += 1; cur.append(ch); continue
        if ch == '}':
            depth_curly -= 1; cur.append(ch); continue
        if ch == '[':
            depth_square += 1; cur.append(ch); continue
        if ch == ']':
            depth_square -= 1; cur.append(ch); continue
        if ch == '|' and depth_curly == 0 and depth_square == 0:
            pieces.append(''.join(cur)); cur = []; continue
        cur.append(ch)
    if cur: pieces.append(''.join(cur))

    for p in pieces:
        if '=' not in p: continue
        k, _, v = p.partition('=')
        k = k.strip().lower()
        v = v.strip()
        if k and v:
            fields[k] = v
    return fields


# ── BUILD DOSSIER ────────────────────────────────────────────────
def build_dossier(name, wikitext):
    """Return a structured dossier for one character."""
    raw = parse_infobox(wikitext)
    if not raw:
        return {"name": name, "found": False}

    out = {"name": name, "found": True, "raw_keys": sorted(raw.keys())}
    for src_key, our_key in FIELDS.items():
        if src_key in raw:
            val = clean_value(raw[src_key])
            if val:
                # First match wins for keys that map from multiple sources
                out.setdefault(our_key, val)

    # Bounty: extract LARGEST number (= most recent / current bounty),
    # filtering out small reference numbers (chapter/page citations that
    # might leak through cleanup). Anything >= 1,000 berries is plausible.
    bounty_text = out.get("bounty", "")
    if bounty_text:
        nums = re.findall(r'[\d,]+', bounty_text)
        cleaned = []
        for n in nums:
            try:
                v = int(n.replace(",", ""))
                if v >= 1000:   # plausible bounty floor
                    cleaned.append(v)
            except: pass
        if cleaned:
            out["bounty_value"] = max(cleaned)

    return out


# ── CHARACTER LIST ───────────────────────────────────────────────
def get_character_list():
    """Return ordered list of (name, appearance_count) from appearances.csv."""
    counter = Counter()
    with open(CSV_PATH, encoding="utf-8") as f:
        next(f)  # header
        for line in f:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                name = parts[1].replace('"','').strip()
                if name:
                    counter[name] += 1
    return counter.most_common()


# ── ARCHIVE I/O ──────────────────────────────────────────────────
def load_records():
    if not os.path.exists(OUTPUT):
        return {}
    with open(OUTPUT, encoding="utf-8") as f:
        return json.load(f)

def save_records(records):
    if os.path.exists(OUTPUT) and not os.path.exists(BACKUP):
        import shutil
        shutil.copy2(OUTPUT, BACKUP)
    tmp = OUTPUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, OUTPUT)


# ── INSPECT MODE ─────────────────────────────────────────────────
def inspect_one(name):
    print(f"\n--- {name} ---")
    wt = fetch_wikitext(name)
    if not wt:
        print("  (no wikitext)")
        return
    print(f"  wikitext length: {len(wt)} chars")
    dossier = build_dossier(name, wt)
    print(json.dumps(dossier, ensure_ascii=False, indent=2))


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    args  = sys.argv[1:]
    test  = "--test" in args
    gaps  = "--gaps" in args
    top   = None
    if "--top" in args:
        i = args.index("--top")
        try: top = int(args[i + 1])
        except: pass
    inspect_target = None
    if "--inspect" in args:
        i = args.index("--inspect")
        if i + 1 < len(args):
            inspect_target = " ".join(args[i + 1:]).strip()
            # Strip any flags after
            inspect_target = re.split(r'\s--\w+', inspect_target)[0]

    if inspect_target:
        inspect_one(inspect_target)
        return

    chars = get_character_list()
    if test:
        chars = chars[:5]
    elif top:
        chars = chars[:top]

    print("=" * 60)
    print("  Punk Records — Character Dossier Scraper")
    print(f"  Source: {CSV_PATH}")
    if test:    print(f"  Mode  : TEST (5 sample chars, no save)")
    elif top:   print(f"  Mode  : TOP {top} most-appearing characters")
    elif gaps:  print(f"  Mode  : GAP-FILL (skip already-recorded)")
    else:       print(f"  Mode  : FULL ({len(chars)} characters)")
    print("=" * 60); print()

    records = load_records() if not test else {}

    # Decide what to actually process; --gaps skips already-good records
    targets = []
    skipped = 0
    for name, appearances in chars:
        if gaps and name in records and records[name].get("found"):
            skipped += 1
            continue
        targets.append((name, appearances))

    # Batch-prefetch all wikitext (cache hits are free; misses go in 50-page batches)
    print(f"  Prefetching wikitext for {len(targets)} characters…")
    wt_map = prefetch_wikitext([n for n, _ in targets], verbose=True)
    print()

    found = missing = 0
    for i, (name, appearances) in enumerate(targets, 1):
        wt = wt_map.get(name)
        if not wt:
            missing += 1
            print(f"  [{i:4d}/{len(targets)}] {name:40s} — no wiki page")
            continue

        dossier = build_dossier(name, wt)
        dossier["appearances"] = appearances

        if dossier.get("found"):
            found += 1
            keys_found = len([k for k in dossier if k not in ("name", "found", "raw_keys", "appearances")])
            print(f"  [{i:4d}/{len(targets)}] {name:40s}  {keys_found:2d} fields")
        else:
            missing += 1
            print(f"  [{i:4d}/{len(targets)}] {name:40s} — no infobox")

        records[name] = dossier

        if not test and i % 100 == 0:
            save_records(records)

    if not test:
        save_records(records)

    print()
    print("=" * 60)
    print(f"  Found    : {found}")
    print(f"  No data  : {missing}")
    print(f"  Skipped  : {skipped}")
    print(f"  Total in records: {len(records)}")
    if not test:
        print(f"  Saved → {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
