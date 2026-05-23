"""
Cover Stories Scraper
Pulls the list of One Piece cover-story arcs from the Fandom wiki and
saves the metadata to cover_stories.json.

Each entry: { name, slug, chapters: [list of chapter numbers],
              chapter_range: "X-Y", featured: [characters], color, summary }

Run:
  py cover_stories_scraper.py
"""
import requests, json, os, re, sys, time

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
OUT        = os.path.join(DIR, "cover_stories.json")
CACHE_DIR  = os.path.join(DIR, "cache", "cover_stories_wikitext")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.8


def _safe(s): return re.sub(r'[^\w.\-]', '_', s)[:100]

# Known cover-story arc pages on the wiki — manually curated since the
# wiki's "Cover Stories" page lists them in nice order
COVER_STORIES = [
    # Verified against https://onepiece.fandom.com/wiki/Short-Term_Focused_Cover_Page_Serials
    # Pass exact page titles (with spaces); the API resolves them.
    ("Buggy's Crew Adventure Chronicles",                       "Buggy's Crew Adventure Chronicles"),
    ("Diary of Koby-Meppo",                                      "Diary of Koby-Meppo"),
    ("Jango's Dance Paradise",                                   "Jango's Dance Paradise"),
    ("Hatchan's Sea-Floor Stroll",                               "Hatchan's Sea-Floor Stroll"),
    ("Wapol's Omnivorous Hurrah",                                "Wapol's Omnivorous Hurrah"),
    ("Ace's Great Blackbeard Search",                            "Ace's Great Blackbeard Search"),
    ("Gedatsu's Accidental Blue-Sea Life",                       "Gedatsu's Accidental Blue-Sea Life"),
    ("Miss Goldenweek's \"Operation: Meet Baroque Works\"", "Miss Goldenweek's \"Operation: Meet Baroque Works\""),
    ("Enel's Great Space Operations",                            "Enel's Great Space Operations"),
    ("CP9's Independent Report",                                 "CP9's Independent Report"),
    ("Straw Hat's Separation Serial",                            "Straw Hat's Separation Serial"),
    ("From the Decks of the World",                              "From the Decks of the World"),
    ("Caribou's Kehihihihi in the New World",                    "Caribou's Kehihihihi in the New World"),
    ("Solo Journey of Jinbe, Knight of the Sea",                 "Solo Journey of Jinbe, Knight of the Sea"),
    ("From the Decks of the World: The 500,000,000 Man Arc",     "From the Decks of the World: The 500,000,000 Man Arc"),
    ("The Stories of the Self-Proclaimed Straw Hat Grand Fleet", "The Stories of the Self-Proclaimed Straw Hat Grand Fleet"),
    ("\"Gang\" Bege's Oh My Family",                            "\"Gang\" Bege's Oh My Family"),
    ("Germa 66's Ahh... An Emotionless Excursion",               "Germa 66's Ahh... An Emotionless Excursion"),
    ("Oni Child Yamato's Golden Harvest Surrogate Pilgrimage",   "Oni Child Yamato's Golden Harvest Surrogate Pilgrimage"),
    # Standalone short series
    # (Spa Island was here but it's a non-canon anime arc, not a cover story — removed)
    ("Where They Are Now",                                       "Where They Are Now"),
    ("Vivi's Adventure",                                          "Vivi's Adventure"),
]

# Distinct colors for highlighting in the chapter map
COLORS = [
    "#ff6b1a", "#4dbbff", "#ffd700", "#ff66cc", "#88ddff", "#ff8855",
    "#aa44ff", "#44dd88", "#ff4466", "#66ddaa", "#bb88ff", "#ffcc44",
    "#ff5588", "#5588ff", "#ddaa44", "#44aabb", "#cc66ff", "#ffaa66",
    "#88ff66", "#dd44ff", "#66ffaa", "#ff7799", "#aabb44", "#cc88aa",
]


def fetch_wikitext(slug, use_cache=True):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, _safe(slug) + ".txt")
    if use_cache and os.path.exists(cache) and os.path.getsize(cache) > 100:
        with open(cache, encoding="utf-8") as f:
            return f.read(), True   # (text, from_cache)
    params = {"action":"parse","page":slug,"prop":"wikitext","format":"json"}
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent":USER_AGENT}, timeout=20)
        wt = r.json().get("parse",{}).get("wikitext",{}).get("*")
        if wt:
            with open(cache, "w", encoding="utf-8") as f:
                f.write(wt)
        return wt, False
    except Exception:
        return None, False


def parse_chapters(wikitext):
    """Find chapter ranges referenced in the wikitext.
    Returns sorted unique list of chapter numbers."""
    if not wikitext: return []
    chapters = set()

    # Match [[Chapter NNN]], Chapter NNN, ch.NNN style refs
    for m in re.finditer(r'\[\[Chapter\s+(\d{1,4})\]\]', wikitext, re.IGNORECASE):
        chapters.add(int(m.group(1)))
    for m in re.finditer(r'\b[Cc]hapter\s+(\d{1,4})(?!\d)', wikitext):
        chapters.add(int(m.group(1)))
    # Match ranges like "Chapters 95-119" or "Chapter 95 to 119"
    for m in re.finditer(r'[Cc]hapters?\s+(\d{1,4})\s*(?:[-–to]+\s*)(\d{1,4})', wikitext):
        a, b = int(m.group(1)), int(m.group(2))
        if abs(b - a) < 200:        # sanity
            chapters.update(range(min(a,b), max(a,b) + 1))
    return sorted(chapters)


def parse_first_paragraph(wikitext):
    """Extract first ~2 sentences of plain prose for a one-line summary."""
    if not wikitext: return ""
    # Strip everything after first heading
    text = wikitext.split("\n==", 1)[0]
    # Strip wiki markup
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    text = re.sub(r'\[\[(?:File|Image):[^\]]+(?:\|[^\]]+)*\]\]', '', text)
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r"'''([^']+)'''", r'\1', text)
    text = re.sub(r"''([^']+)''", r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Take first 2 sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary = " ".join(sentences[:2])
    return summary[:400]


def main():
    gaps_only = "--gaps" in sys.argv
    no_cache  = "--no-cache" in sys.argv

    # Existing data (used by --gaps and as a base to merge into)
    existing = {}
    if os.path.exists(OUT):
        try:
            existing = {e["slug"]: e for e in json.load(open(OUT, encoding="utf-8"))}
        except Exception: pass

    print("=" * 60)
    print("  Cover Stories Scraper" + (" (--gaps)" if gaps_only else ""))
    print(f"  {len(COVER_STORIES)} cover stories  ·  {len(existing)} already on disk")
    print("=" * 60); print()

    out = []
    fetched = cached = skipped = 0
    for i, (name, slug) in enumerate(COVER_STORIES):
        color = COLORS[i % len(COLORS)]
        if gaps_only and slug in existing and existing[slug].get("chapters"):
            out.append(existing[slug])
            skipped += 1
            continue
        print(f"  {name[:50]:50s}…", end=" ", flush=True)
        wikitext, from_cache = fetch_wikitext(slug, use_cache=not no_cache)
        if not wikitext:
            print("not found")
            if not from_cache: time.sleep(DELAY)
            continue

        chapters = parse_chapters(wikitext)
        summary  = parse_first_paragraph(wikitext)
        ch_range = f"{chapters[0]}–{chapters[-1]}" if chapters else "?"

        out.append({
            "name":     name,
            "slug":     slug,
            "color":    color,
            "chapters": chapters,
            "chapter_range": ch_range,
            "summary":  summary,
        })
        if from_cache:
            cached += 1
            print(f"{len(chapters):3d} chapters  {ch_range}  (cached)")
        else:
            fetched += 1
            print(f"{len(chapters):3d} chapters  {ch_range}")
            time.sleep(DELAY)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print()
    print(f"  ✓ Wrote {len(out)} cover stories  (fetched {fetched} · cached {cached} · skipped {skipped})")
    print(f"  → {OUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
