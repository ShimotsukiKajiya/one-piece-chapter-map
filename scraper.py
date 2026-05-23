"""
One Piece Chapter Appearance Scraper
Fetches character appearance data from the One Piece Fandom wiki via MediaWiki API.
Outputs: appearances.csv  (chapter, name, type)
         scraper_progress.json  (checkpoint for resuming)

Commands:
  py scraper.py            Full run from scratch (or resume from checkpoint)
  py scraper.py --update   Append only new chapters since last run (~seconds)
  py scraper.py --reset    Delete data and start completely fresh
"""

import requests
import json
import csv
import time
import os
import re
import sys

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE        = "https://onepiece.fandom.com/api.php"
OUTPUT_FILE     = os.path.join(os.path.dirname(__file__), "appearances.csv")
CHECKPOINT_FILE = os.path.join(os.path.dirname(__file__), "scraper_progress.json")
TOTAL_CHAPTERS  = 1181   # Floor; --update auto-probes a few past this for new releases
PROBE_AHEAD     = 5      # In --update mode, try this many past TOTAL_CHAPTERS
DELAY           = 1.1    # Seconds between requests — do not lower below 1.0
CHECKPOINT_EVERY = 25    # Save progress every N chapters

# Invisible Unicode that the wiki occasionally embeds in link text (LRM, ZWJ,
# ZWNJ, BOM, etc.). Stripped from name on capture so downstream lookups don't
# silently mismatch "Bentham" vs "Bentham‎".
_INVISIBLE_RE = re.compile(r"[​‌‍‎‏⁠﻿]+")
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "OnePieceFanProject/1.0 (educational, non-commercial)"}

# Matches ==Characters== or ===Characters in Order of Appearance=== etc.
CHAR_SECTION_RE = re.compile(r'=+\s*Characters[^=\n]*=+', re.IGNORECASE)

# Matches [[Target]] or [[Target|Display]] — captures the target part only
LINK_RE = re.compile(r'\[\[([^\|\]\[#\n]+?)(?:[#\|][^\]]*?)?\]\]')

# Prefixes that indicate a non-character wiki link
SKIP_PREFIXES = (
    'File:', 'Image:', 'Category:', 'Template:', 'Talk:', 'User:',
    'w:', 'Wikipedia:', 'Help:', 'Special:',
)


def load_checkpoint() -> int:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, encoding='utf-8') as f:
                return int(json.load(f).get('next_chapter', 1))
        except Exception:
            pass
    return 1


def save_checkpoint(next_chapter: int):
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({'next_chapter': next_chapter}, f)


def get_wikitext(chapter_num: int) -> str | None:
    params = {
        'action': 'parse',
        'page':   f'Chapter_{chapter_num}',
        'prop':   'wikitext',
        'format': 'json',
    }
    try:
        resp = requests.get(API_BASE, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if 'parse' not in data:
            return None  # Page does not exist
        return data['parse']['wikitext']['*']
    except requests.exceptions.RequestException as e:
        print(f"    Network error: {e}")
        return None
    except (KeyError, ValueError) as e:
        print(f"    Parse error: {e}")
        return None


def determine_type(line: str) -> str:
    """Detect appearance qualifier from wikitext line."""
    lower = line.lower()
    if 'flashback' in lower:
        return 'flashback'
    if 'silhouette' in lower:
        return 'silhouette'
    # "cover story", "cover page", "cover only"
    if 'cover' in lower:
        return 'cover'
    return 'full'


def extract_characters(wikitext: str, chapter_num: int) -> list[dict]:
    """
    Extract character appearances from the ===Characters=== section of wikitext.
    Returns a list of dicts: { chapter, name, type }
    """
    results = []

    # Find the Characters section
    match = CHAR_SECTION_RE.search(wikitext)
    if not match:
        return results

    section = wikitext[match.end():]

    # Trim to end of section (next top-level == heading)
    next_section = re.search(r'\n={2}[^=]', section)
    if next_section:
        section = section[:next_section.start()]

    seen: set[tuple] = set()

    for line in section.splitlines():
        stripped = line.strip()

        # Only process bullet list lines (* or **)
        if not stripped.startswith('*'):
            continue

        app_type = determine_type(stripped)

        for name in LINK_RE.findall(stripped):
            name = _INVISIBLE_RE.sub("", name).strip()
            if not name:
                continue
            # Skip non-character links
            if any(name.startswith(p) for p in SKIP_PREFIXES):
                continue
            # Skip very short tokens that are likely wikitext artefacts
            if len(name) < 2:
                continue

            key = (name, app_type)
            if key not in seen:
                seen.add(key)
                results.append({'chapter': chapter_num, 'name': name, 'type': app_type})

    return results


def last_scraped_chapter() -> int:
    """Read the highest chapter number already in appearances.csv."""
    if not os.path.exists(OUTPUT_FILE):
        return 0
    last = 0
    with open(OUTPUT_FILE, encoding='utf-8') as f:
        for line in f:
            try:
                ch = int(line.split(',')[0])
                if ch > last:
                    last = ch
            except ValueError:
                pass
    return last


def run(start_chapter: int, label: str):
    fresh_start = start_chapter == 1 and not os.path.exists(OUTPUT_FILE)
    remaining   = TOTAL_CHAPTERS - start_chapter + 1
    eta_min     = remaining * DELAY / 60

    print("=" * 60)
    print(f"  One Piece Appearance Scraper  [{label}]")
    print("=" * 60)
    print(f"  Starting at : Chapter {start_chapter}")
    print(f"  Target      : Chapter {TOTAL_CHAPTERS}")
    print(f"  Chapters    : {remaining}")
    print(f"  Est. time   : {eta_min:.0f}–{eta_min*1.2:.0f} minutes")
    print(f"  Output      : {OUTPUT_FILE}")
    print()
    print("  Press Ctrl+C to pause — safe to stop at any time.")
    print("=" * 60)
    print()

    file_mode = 'w' if fresh_start else 'a'
    ch = start_chapter

    try:
        with open(OUTPUT_FILE, file_mode, newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['chapter', 'name', 'type'])
            if fresh_start:
                writer.writeheader()

            for ch in range(start_chapter, TOTAL_CHAPTERS + 1):
                sys.stdout.write(f"  Ch {ch:>4}/{TOTAL_CHAPTERS} ... ")
                sys.stdout.flush()

                wikitext = get_wikitext(ch)
                if wikitext:
                    rows = extract_characters(wikitext, ch)
                    writer.writerows(rows)
                    csvfile.flush()
                    print(f"{len(rows):>3} characters")
                else:
                    print("  —  (skipped, no wiki page)")

                if ch % CHECKPOINT_EVERY == 0:
                    save_checkpoint(ch + 1)

                time.sleep(DELAY)

    except KeyboardInterrupt:
        print("\n\n  Paused. Progress saved.")
        save_checkpoint(ch)
        print(f"  Resume by running this script again (will start at Ch {ch}).")
        sys.exit(0)

    save_checkpoint(TOTAL_CHAPTERS + 1)
    print()
    print("=" * 60)
    print(f"  Done! Output: {OUTPUT_FILE}")
    print(f"  Now run: git add appearances.csv && git commit -m 'Update appearances' && git push")
    print("=" * 60)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''

    if mode == '--reset':
        for f in [OUTPUT_FILE, CHECKPOINT_FILE]:
            if os.path.exists(f):
                os.remove(f)
                print(f"  Deleted {f}")
        print("  Ready for a fresh run. Run: py scraper.py")
        return

    if mode == '--update':
        global TOTAL_CHAPTERS
        last = last_scraped_chapter()
        # Probe a few past the known floor in case Oda dropped new chapters
        TOTAL_CHAPTERS = max(TOTAL_CHAPTERS, last) + PROBE_AHEAD
        if last == 0:
            print("  No existing data found — running full scrape instead.")
            run(1, 'full run')
        else:
            print(f"  Existing data goes up to Chapter {last}. Probing {last + 1}–{TOTAL_CHAPTERS}.")
            run(last + 1, 'update')
        return

    # Default: resume from checkpoint or start fresh
    run(load_checkpoint(), 'full run')


if __name__ == '__main__':
    main()
