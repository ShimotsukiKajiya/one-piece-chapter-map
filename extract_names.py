"""
Pen Name Extractor — adds a `name` field to each entry in sbs_archive.json
without touching anything else. Re-fetches volumes from the wiki and parses
out the pen name (P.N.), keeping all existing fields (category, etc.) intact.

Run:
  py extract_names.py
"""

import requests, json, os, re, sys, time
from difflib import SequenceMatcher

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
ARCHIVE    = os.path.join(DIR, "sbs_archive.json")
CACHE_DIR  = os.path.join(DIR, "cache", "sbs_volume_wikitext")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 1.0

D_MARKER = re.compile(r"(?:'''[﻿\s]*D[\s'’]*:|(?<=\n)D:)\s*")
O_MARKER = re.compile(r"(?:'''[﻿\s]*O[\s'’]*:|(?<=\n)O:)\s*")

# Pen-name patterns Oda's SBS uses (run in priority order)
PN_PATTERNS = [
    # 1. "Pen Name 'NAME'" or 'Pen Name "NAME"' — quoted form
    re.compile(r'Pen\s*Name\s*[:"“]\s*([A-Za-z0-9 _’\'\-]{2,40}?)\s*["”]?\s*$', re.IGNORECASE),
    # 2. "Pen Name NAME" — unquoted, end of line
    re.compile(r'Pen\s*Name\s*[:\s]\s*([A-Za-z0-9 _’\'\-]{2,40}?)\s*[.!?]?\s*$', re.IGNORECASE),
    # 3. Explicit "P.N. NAME" — most reliable
    re.compile(r"P\.?\s*N\.?\s*[:\s]*([A-Za-z0-9 _'\-]{2,40}?)(?=[.,!?\n]|\s*$|\s*'''|\s*\}\}|\s*\[\[)", re.IGNORECASE),
    # 4. "from NAME" / "from Mr/Ms NAME" — typically end of question
    re.compile(r"\bfrom\s+(?:Mr\.?\s+|Ms\.?\s+|M\.?\s+)?([A-Z][A-Za-z0-9 .\-]{1,40}?)(?=\s*[.!?]?\s*$)"),
    # 5. "by NAME" — used in many older volumes
    re.compile(r"\bby\s+([A-Z][A-Za-z0-9_\-]{2,30})\b"),
    # 6. Parenthetical name at the very end:  "(Romy)" / "(M. Misa-san)"
    re.compile(r"\(([A-Z][A-Za-z0-9 .\-]{1,30})\)\s*[.!?]?\s*$"),
    # 7. Trailing standalone capitalized name after "?" / "." / "!"
    #    e.g. "...timeline? Yutaro" or "...question. Sanadacchi"
    re.compile(r"[?!.]\s+([A-Z][A-Za-z]{3,25})\s*$"),
]

# Words that look like names but aren't (filter out false positives)
NAME_BLOCKLIST = {
    'the','this','that','oda','one','by','is','his','her','for','and','but',
    'yes','no','true','false','age','volume','chapter','page','part','line',
    'thanks','thank','please','sensei','san','chan','kun','question',
    'piece','strawhat','luffy','zoro','nami','sanji','usopp','chopper',
    'robin','franky','brook','jinbe','ace','sabo','shanks','kaido','imu',
    'romy',   # (kept since it's a known reader name — actually wait, Romy IS a name)
}
# Remove 'romy' from blocklist — it's a real reader
NAME_BLOCKLIST.discard('romy')


def fetch(vol, use_cache=True):
    """Fetch + cache an SBS volume's wikitext. Returns (text, from_cache)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"vol-{vol}.txt")
    if use_cache and os.path.exists(cache) and os.path.getsize(cache) > 100:
        with open(cache, encoding="utf-8") as f:
            return f.read(), True
    params = {"action":"parse","page":f"SBS_Volume_{vol}",
              "prop":"wikitext","format":"json"}
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200: return None, False
        wt = r.json().get("parse",{}).get("wikitext",{}).get("*")
        if wt:
            with open(cache, "w", encoding="utf-8") as f:
                f.write(wt)
        return wt, False
    except Exception:
        return None, False


def clean(text):
    if not text: return ""
    text = re.sub(r'\[\[(?:File|Image):[^\]]+(?:\|[^\]]+)*\]\]', '', text)
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    return text


def extract_name(question_raw):
    """Try several patterns to find the pen name in the question text."""
    text = clean(question_raw)
    for pat in PN_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group(1).strip(" .,'\"-_")
            # Filter out common false positives
            if name.lower() in NAME_BLOCKLIST: continue
            if len(name) < 2 or len(name) > 40: continue
            # Must contain at least one letter
            if not re.search(r'[A-Za-z]', name): continue
            # Reject if it's mostly digits ("age 8")
            if sum(c.isdigit() for c in name) > len(name) / 2: continue
            return name
    return None


def parse_pairs(wikitext, vol):
    """Return list of (question_clean, name) pairs from a volume."""
    if not wikitext: return []
    d_marks = [(m.start(), m.end()) for m in D_MARKER.finditer(wikitext)]
    o_marks = [(m.start(), m.end()) for m in O_MARKER.finditer(wikitext)]
    if not d_marks or not o_marks: return []

    pairs = []
    for i, (d_start, d_end) in enumerate(d_marks):
        next_o = next(((s,e) for s,e in o_marks if s > d_end), None)
        if not next_o: continue
        next_d_start = d_marks[i+1][0] if i+1 < len(d_marks) else len(wikitext)
        if next_d_start <= next_o[1]: continue
        q_raw = wikitext[d_end:next_o[0]]
        # Remove P.N. line for a cleaner question, keep the name separately
        name = extract_name(q_raw)
        # Clean for matching against archive
        q_clean = clean(q_raw).replace("'''","").replace("''","")
        q_clean = re.sub(r'P\.?\s*N\.?[^.\n]{0,40}', '', q_clean, flags=re.IGNORECASE)
        q_clean = re.sub(r'\s+', ' ', q_clean).strip()
        if q_clean:
            pairs.append((q_clean, name))
    return pairs


def fingerprint(s, n=60):
    """Short normalized prefix for matching."""
    return re.sub(r'\s+', ' ', s.lower())[:n]


def main():
    force = "--force" in sys.argv  # re-process every entry, ignoring existing names

    if not os.path.exists(ARCHIVE):
        print("  ✗ sbs_archive.json missing"); sys.exit(1)

    with open(ARCHIVE, encoding="utf-8") as f:
        archive = json.load(f)

    # Group archive entries by volume
    by_vol = {}
    for entry in archive:
        by_vol.setdefault(entry["volume"], []).append(entry)

    # Skip volumes where every entry already has a name (unless --force)
    if not force:
        skip_vols = {v for v, es in by_vol.items() if all(e.get("name") for e in es)}
    else:
        skip_vols = set()

    print("=" * 55)
    print(f"  Pen Name Extractor — {len(archive)} entries")
    if skip_vols:
        print(f"  Skipping {len(skip_vols)} fully-named volumes (use --force to redo)")
    print("=" * 55); print()

    total_named = 0
    sanada_count = 0
    fetched = cached = 0
    changed = False

    for vol in sorted(by_vol.keys()):
        if vol in skip_vols:
            # Count existing names toward the total but don't process
            for e in by_vol[vol]:
                if e.get("name"):
                    total_named += 1
                    if e["name"].strip().lower() == "sanada": sanada_count += 1
            continue

        entries = by_vol[vol]
        print(f"  Vol {vol:3d}  ({len(entries):2d} entries)…", end=" ", flush=True)

        wikitext, from_cache = fetch(vol)
        if from_cache: cached += 1
        else: fetched += 1
        pairs = parse_pairs(wikitext, vol)

        # Skip already-named entries within a partially-processed volume too
        named_in_vol = 0
        for entry in entries:
            if not force and entry.get("name"):
                named_in_vol += 1
                if entry["name"].strip().lower() == "sanada": sanada_count += 1
                continue

            best = None; best_score = 0
            target_fp = fingerprint(entry["question"])
            for q_clean, name in pairs:
                score = SequenceMatcher(None, target_fp, fingerprint(q_clean)).ratio()
                if score > best_score:
                    best_score = score; best = name
            if best and best_score > 0.5:
                entry["name"] = best
                changed = True
                named_in_vol += 1
                if best.strip().lower() == "sanada":
                    sanada_count += 1

        total_named += named_in_vol
        print(f"named: {named_in_vol}  ({'cached' if from_cache else 'fetched'})")
        if not from_cache: time.sleep(DELAY)

    # Single end-of-run save (was: per-volume rewrite of 1.6MB JSON)
    if changed:
        with open(ARCHIVE, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

    print()
    print(f"  ✓ Named: {total_named} / {len(archive)} entries")
    print(f"  ✓ Volumes — fetched: {fetched} · cached: {cached} · skipped: {len(skip_vols)}")
    print(f"  ✓ Archive {'written' if changed else 'unchanged (no save)'}")
    print(f"  🌟 Sanada appearances: {sanada_count}")
    print("=" * 55)


if __name__ == "__main__":
    main()
