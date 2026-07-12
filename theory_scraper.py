"""
One Piece Theory Scraper
Fetches top community theories from r/OnePiece via Reddit's public JSON API.
No credentials, no app registration, no OAuth — works out of the box.
Outputs: theories_import.json  (load into the Theory Tracker)

Run:
  py theory_scraper.py              # full fetch
  py theory_scraper.py --test       # fetch 25 posts only (quick check)
"""

import requests
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

# ── CONFIG ────────────────────────────────────────────────────────
USER_AGENT    = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Quality gates — adjust freely
MIN_SCORE     = 300     # Minimum upvote score (lower = more results, lower quality)
MAX_AGE_DAYS  = 1460    # Skip theories older than this (1460 = 4 years)
MIN_TEXT_LEN  = 150     # Skip posts with almost no body text
MAX_TEXT_LEN  = 1800    # Truncate very long posts to this many characters
FETCH_LIMIT   = 250     # Max posts to request from Reddit

OUTPUT_FILE   = os.path.join(os.path.dirname(__file__), "theories_import.json")
# ─────────────────────────────────────────────────────────────────

# Regex to find chapter references in post text
CHAPTER_RE = re.compile(
    r'\bch(?:apter)?s?\.?\s*(\d{1,4}(?:\s*[-–]\s*\d{1,4})?)\b',
    re.IGNORECASE,
)


# ── FETCH ────────────────────────────────────────────────────────
def fetch_posts(limit: int) -> list:
    """Fetch theory posts using Reddit's public JSON API — no credentials needed."""
    headers  = {"User-Agent": USER_AGENT}
    posts    = []
    after    = None
    batch_no = 0

    while len(posts) < limit:
        batch_no += 1
        want   = min(100, limit - len(posts))
        params = {
            "q":           'flair:"Theory"',
            "restrict_sr": "true",
            "sort":        "top",
            "t":           "all",
            "limit":       want,
            "type":        "link",
        }
        if after:
            params["after"] = after

        url = "https://www.reddit.com/r/OnePiece/search.json"

        try:
            resp = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=20,
            )
        except requests.exceptions.RequestException as e:
            print(f"  ✗  Network error on batch {batch_no}: {e}")
            break

        if resp.status_code == 429:
            print("  ⚠  Rate limited — waiting 60 seconds…")
            time.sleep(60)
            continue

        if resp.status_code != 200:
            print(f"  ✗  HTTP {resp.status_code} on batch {batch_no}")
            print(f"     {resp.text[:200]}")
            break

        data     = resp.json().get("data", {})
        children = data.get("children", [])
        after    = data.get("after")

        if not children:
            break

        for c in children:
            posts.append(c["data"])

        print(f"    Batch {batch_no}: fetched {len(children)} posts  (total so far: {len(posts)})")

        if not after:
            break

        time.sleep(2)  # be polite — public API is stricter on rate limits

    return posts


# ── TEXT PROCESSING ──────────────────────────────────────────────
def clean_text(text: str, max_len: int) -> str:
    if not text or text in ("[removed]", "[deleted]"):
        return ""
    # Strip Reddit markdown links [label](url) → label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Strip image links
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Collapse excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(' ', 1)[0] + '…'
    return text


def extract_chapters(title: str, body: str) -> str:
    combined = f"{title} {body}"
    seen, refs = set(), []
    for m in CHAPTER_RE.findall(combined):
        m = m.strip()
        if m not in seen:
            seen.add(m)
            refs.append(m)
        if len(refs) >= 4:
            break
    return ", ".join(refs)


# ── FILTERING ────────────────────────────────────────────────────
def process(raw_posts: list) -> list:
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    results = []
    skip    = {"score": 0, "age": 0, "text": 0, "mod": 0}

    for post in raw_posts:
        # Skip mod-distinguished / stickied posts
        if post.get("stickied") or post.get("distinguished"):
            skip["mod"] += 1
            continue

        # Quality gate: upvote score
        if post.get("score", 0) < MIN_SCORE:
            skip["score"] += 1
            continue

        # Quality gate: age
        created_utc = post.get("created_utc", 0)
        created     = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        if created < cutoff:
            skip["age"] += 1
            continue

        # Clean body text
        body  = clean_text(post.get("selftext", ""), MAX_TEXT_LEN)
        title = post.get("title", "").strip()

        # Quality gate: minimum meaningful content
        if len(body) < MIN_TEXT_LEN:
            skip["text"] += 1
            continue

        chapter = extract_chapters(title, body)

        results.append({
            "id":          post.get("id", ""),
            "title":       title,
            "description": body,
            "status":      "active",
            "chapter":     chapter,
            "date":        created.isoformat(),
            "source":      f"https://reddit.com{post.get('permalink', '')}",
            "score":       post.get("score", 0),
            "comments":    post.get("num_comments", 0),
        })

    # Sort highest-score first
    results.sort(key=lambda t: t["score"], reverse=True)

    print(f"  Filtered out: {skip['score']} low-score, {skip['age']} too old, "
          f"{skip['text']} too short, {skip['mod']} mod posts")
    return results


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    test_mode = "--test" in sys.argv
    fetch_n   = 25 if test_mode else FETCH_LIMIT

    print("=" * 55)
    print("  One Piece Theory Scraper")
    if test_mode:
        print("  (test mode — fetching 25 posts; writing to theories_import.test.json,")
        print("   NOT overwriting the live theories_import.json)")
    print("  No login required — using public Reddit API")
    print("=" * 55)
    print()
    print(f"  Fetching top Theory posts from r/OnePiece…")
    raw = fetch_posts(fetch_n)
    print(f"  ✓ Fetched {len(raw)} raw posts")
    print()
    print("  Applying quality gates:")
    print(f"    Min score  ≥ {MIN_SCORE}")
    print(f"    Max age    ≤ {MAX_AGE_DAYS} days")
    print(f"    Min text   ≥ {MIN_TEXT_LEN} characters")
    theories = process(raw)
    print()
    print(f"  ✓ {len(theories)} theories passed — {len(raw) - len(theories)} filtered out")
    print()

    # A failed or empty Reddit fetch must never touch the live archive.
    # (2026-07-12: an HTTP-blocked run wrote 0 theories over the curated
    # 94-entry archive — statuses, analysis and numbering all lost until
    # git restore. Guard added the same day.)
    if not theories:
        print("  ⚠  0 theories fetched — refusing to write; existing archive untouched.")
        sys.exit(1)

    # Test mode writes to a separate file so it can never overwrite the live
    # 94-theory archive. (2026-05-02: this protection added after a --test run
    # accidentally clobbered the live file with only 7 entries.)
    output_path = OUTPUT_FILE.replace(".json", ".test.json") if test_mode else OUTPUT_FILE

    # Merge into the existing archive instead of replacing it. Existing rows
    # own their curated fields (status, analysis, num, chapter edits) — the
    # scraper only refreshes the volatile Reddit counters on them. New posts
    # append with default fields. Rows that fell out of Reddit's top results
    # are kept: dropping them would erase maintainer-reviewed history.
    existing = []
    if not test_mode and os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            existing = []
    by_id = {row.get("id"): row for row in existing if row.get("id")}
    added = updated = 0
    for fresh in theories:
        prev = by_id.get(fresh["id"])
        if prev is not None:
            prev["score"]    = fresh["score"]
            prev["comments"] = fresh["comments"]
            updated += 1
        else:
            existing.append(fresh)
            added += 1
    merged = sorted(existing, key=lambda t: t.get("score", 0), reverse=True)
    print(f"  Merge: {added} new · {updated} refreshed · {len(merged)} total in archive")
    theories = merged

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(theories, f, ensure_ascii=False, indent=2)

    print(f"  Written → {output_path}")
    print()
    if theories:
        print(f"  Score range: {theories[-1]['score']} – {theories[0]['score']} upvotes")
    print()
    print("  Status breakdown:")
    from collections import Counter
    counts = Counter(t["status"] for t in theories)
    for s, n in sorted(counts.items()):
        print(f"    {s:12} {n}")
    print()
    print("  Next: open the Theory Tracker and click")
    print("  'Import JSON' to load and review your theories.")
    print("=" * 55)


if __name__ == "__main__":
    main()
