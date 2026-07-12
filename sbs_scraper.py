"""
SBS Scraper
Pulls every Q&A from Oda's SBS sections (one per tankoubon volume) via the
Fandom MediaWiki API. Saves to sbs_archive.json — a permanent, reusable
canon database for theory verification.

SBS = "Question Corner" — Oda's direct answers to fan questions.
These are CANON and the gold standard for debunking/confirming theories.

Run:
  py sbs_scraper.py                # full archive (volumes 4 → 110+)
  py sbs_scraper.py --test         # first 5 volumes only
  py sbs_scraper.py --resume       # continue where you left off
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

# ── CONFIG ────────────────────────────────────────────────────────
USER_AGENT  = "OnePieceTheoryTracker/1.0 (fan project)"
WIKI_API    = "https://onepiece.fandom.com/api.php"

START_VOLUME = 4      # SBS started in volume 4
END_VOLUME   = 112    # floor; --gaps probes a few past this for new releases
PROBE_AHEAD  = 3
DELAY        = 1.0    # seconds between requests

DIR           = os.path.dirname(__file__)
OUTPUT_FILE   = os.path.join(DIR, "sbs_archive.json")
PROGRESS_FILE = os.path.join(DIR, "sbs_progress.json")
# Shared cache with extract_names.py — both scripts fetch SBS_Volume_N
CACHE_DIR     = os.path.join(DIR, "cache", "sbs_volume_wikitext")
# ─────────────────────────────────────────────────────────────────


# ── FETCH ────────────────────────────────────────────────────────
def fetch_volume(vol: int, use_cache: bool = True):
    """Fetch raw wikitext for SBS Volume N. Returns (text_or_None, from_cache)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, f"vol-{vol}.txt")
    if use_cache and os.path.exists(cache) and os.path.getsize(cache) > 100:
        with open(cache, encoding="utf-8") as f:
            return f.read(), True

    params = {
        "action": "parse",
        "page":   f"SBS_Volume_{vol}",
        "prop":   "wikitext",
        "format": "json",
    }
    try:
        resp = requests.get(WIKI_API, params=params,
                            headers={"User-Agent": USER_AGENT}, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"    ✗ Network error vol {vol}: {e}")
        return None, False

    if resp.status_code != 200:
        return None, False

    data = resp.json()
    if "error" in data:
        return None, False

    wt = data.get("parse", {}).get("wikitext", {}).get("*")
    if wt:
        with open(cache, "w", encoding="utf-8") as f:
            f.write(wt)
    return wt, False


# ── PARSE ────────────────────────────────────────────────────────
# SBS pages use bolded D: (Dokusha = Reader) and O: (Oda) markers.
# Two observed formats:
#   Format A:  '''D: question text here.'''
#              '''O:''' answer text here.
#   Format B:  '''D:'''
#              [[File:...]] P.N. SomeName then question text
#              '''O:''' answer text
#
# Strategy: locate every '''D: and '''O: marker, pair them sequentially,
# and slice out the question/answer text between them.

# Allow optional BOM/whitespace between ''' and D/O, and allow apostrophes
# between the letter and the colon (handles both '''D:''' and '''D''':)
D_MARKER_RE = re.compile(r"(?:'''[﻿\s]*D[\s'’]*:|(?<=\n)D:)\s*")
O_MARKER_RE = re.compile(r"(?:'''[﻿\s]*O[\s'’]*:|(?<=\n)O:)\s*")


def clean_wikitext(text: str) -> str:
    """Strip wiki markup, keep readable plaintext."""
    if not text:
        return ""
    # Remove file/image embeds first (they have inner brackets)
    text = re.sub(r'\[\[(?:File|Image):[^\]]+(?:\|[^\]]+)*\]\]', '', text)
    # [[Link|Display]] → Display, [[Link]] → Link
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)
    # Strip ref tags
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^/]*/>', '', text)
    # Strip other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove SBS-specific templates
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    # Strip stray bold/italic markers (matched or unmatched)
    text = text.replace("'''", "").replace("''", "")
    # Strip section headers
    text = re.sub(r'==+[^=]+==+', '', text)
    # Strip P.N. / Pen Name prefixes — these are reader pen names, not the question
    text = re.sub(r'P\.N\.\s*[^\n]+?(?=\s|$)', '', text, count=1)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_qa(wikitext: str, vol: int) -> list:
    """Extract all Q/A pairs from one SBS volume's wikitext."""
    if not wikitext:
        return []

    d_marks = [(m.start(), m.end()) for m in D_MARKER_RE.finditer(wikitext)]
    o_marks = [(m.start(), m.end()) for m in O_MARKER_RE.finditer(wikitext)]

    if not d_marks or not o_marks:
        return []

    qas = []
    for i, (d_start, d_end) in enumerate(d_marks):
        # Find first O marker that comes after this D
        next_o = next(((s, e) for s, e in o_marks if s > d_end), None)
        if not next_o:
            continue

        # End of answer = start of next D marker (or end of text)
        next_d_start = d_marks[i + 1][0] if i + 1 < len(d_marks) else len(wikitext)
        if next_d_start <= next_o[1]:
            continue   # malformed ordering

        question = clean_wikitext(wikitext[d_end:next_o[0]])
        answer   = clean_wikitext(wikitext[next_o[1]:next_d_start])

        if question and answer and len(question) > 4 and len(answer) > 4:
            qas.append({"volume": vol, "question": question, "answer": answer})

    return qas


# ── PROGRESS ─────────────────────────────────────────────────────
def load_progress() -> int:
    if not os.path.exists(PROGRESS_FILE):
        return START_VOLUME
    try:
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f).get("next_volume", START_VOLUME)
    except: return START_VOLUME


def save_progress(next_vol: int):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"next_volume": next_vol}, f)


def load_archive() -> list:
    if not os.path.exists(OUTPUT_FILE):
        return []
    try:
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    except: return []


def save_archive(archive: list):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    test_mode = "--test" in sys.argv
    resume    = "--resume" in sys.argv
    gaps_mode = "--gaps"   in sys.argv

    archive = load_archive() if (resume or gaps_mode) else []

    if gaps_mode:
        # Find which volumes already have at least one Q&A
        have = {entry["volume"] for entry in archive}
        # Auto-extend: probe a few past the highest known volume in case
        # new tankoubon released since last refresh
        known_max = max(have, default=END_VOLUME)
        end_floor = max(END_VOLUME, known_max + PROBE_AHEAD)
        volumes = [v for v in range(START_VOLUME, end_floor + 1) if v not in have]
        print("=" * 55)
        print("  SBS Archive Scraper — Gap-Fill Mode")
        print(f"  Existing archive: {len(archive)} Q&As across {len(have)} volumes")
        print(f"  Missing volumes : {len(volumes)}")
        if volumes:
            print(f"  Will fetch       : {volumes}")
        print("=" * 55)
        print()
    else:
        start = load_progress() if resume else START_VOLUME
        end   = (start + 5)     if test_mode else END_VOLUME
        volumes = list(range(start, end + 1))
        print("=" * 55)
        print("  SBS Archive Scraper")
        print(f"  Volumes: {start} → {end}")
        if test_mode: print("  (test mode — 5 volumes only)")
        if resume:    print(f"  (resuming from volume {start})")
        print("=" * 55)
        print()

    found = 0
    fetched = cached = 0
    changed = False

    for vol in volumes:
        print(f"  Volume {vol}…", end=" ", flush=True)
        wikitext, from_cache = fetch_volume(vol)

        if wikitext is None:
            print("not found (volume may not exist yet)")
            if not from_cache: time.sleep(DELAY)
            continue

        if from_cache: cached += 1
        else: fetched += 1

        qas = parse_qa(wikitext, vol)

        if not qas:
            # Disambiguate: is the SBS page genuinely empty (a wiki stub waiting
            # for community transcription, common for the most recent volume),
            # or did the parser actually fail on a different page format?
            is_stub = "{{Stub}}" in wikitext or "{{stub}}" in wikitext.lower()
            no_chapter_headings = "Chapter " not in wikitext
            if is_stub:
                print(f"no Q&A — page is a wiki STUB (community hasn't transcribed yet)  ({'cached' if from_cache else 'fetched'})")
            elif no_chapter_headings:
                print(f"no Q&A — no chapter headings found (volume may not have SBS)  ({'cached' if from_cache else 'fetched'})")
            else:
                print(f"no Q&A parsed (chapters found but Q&A regex didn't match — parser may need update)  ({'cached' if from_cache else 'fetched'})")
        else:
            archive.extend(qas)
            found += len(qas)
            changed = True
            print(f"{len(qas)} Q&A extracted  ({'cached' if from_cache else 'fetched'})")

        save_progress(vol + 1)
        if not from_cache: time.sleep(DELAY)

    # Single end-of-run save instead of per-volume rewrite of the whole archive
    if changed:
        save_archive(archive)

    print()
    print(f"  ✓ Total Q&A in archive: {len(archive)}")
    print(f"  ✓ Added this run: {found}  (fetched {fetched} · cached {cached})")
    if changed:
        print(f"  Written → {OUTPUT_FILE}")
    else:
        print(f"  Archive unchanged")
    print("=" * 55)


if __name__ == "__main__":
    main()
