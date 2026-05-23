"""
Publish RSS — emit a feed.xml summarising recent commits to the data
files. Lets people subscribe to "what got verified this week" via any
RSS reader.

Output: feed.xml at repo root (served by GitHub Pages).

Run:
  py publish_rss.py
"""
import os, sys, subprocess, html, re
from datetime import datetime, timezone

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(__file__)
OUT = os.path.join(DIR, "feed.xml")
SITE = "https://shimotsukicodex.com"
REPO = "https://github.com/ShimotsukiKajiya/one-piece-chapter-map"

# Files whose changes are worth announcing
WATCH = ("appearances.csv", "sbs_archive.json", "theories_import.json",
         "punk_records.json", "canon_facts.json", "devil_fruits.json",
         "cover_stories.json", "volume_covers.json", "arcs.json",
         "crews.json", "portraits.json")


def main():
    # Get last 30 commits touching any watched file
    try:
        out = subprocess.check_output(
            ["git", "log", "-30", "--pretty=format:%H||%aI||%s||%an", "--", *WATCH],
            cwd=DIR, encoding="utf-8"
        )
    except subprocess.CalledProcessError as e:
        print(f"  ✗ git log failed: {e}")
        sys.exit(1)

    items = []
    for line in out.strip().split("\n"):
        if not line: continue
        parts = line.split("||", 3)
        if len(parts) < 4: continue
        sha, iso, title, author = parts
        # Skip merge commits
        if title.startswith("Merge "): continue
        items.append({
            "sha":     sha[:8],
            "url":     f"{REPO}/commit/{sha}",
            "title":   title,
            "author":  author,
            "iso":     iso,
            "rfc822":  datetime.fromisoformat(iso).strftime("%a, %d %b %Y %H:%M:%S %z"),
        })

    if not items:
        print("  ✗ no relevant commits")
        return

    rss_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        '  <channel>',
        f'    <title>The Shimotsuki Codex — canon updates</title>',
        f'    <link>{SITE}/</link>',
        f'    <description>What got scraped, verified, or curated this week. Auto-generated from git history.</description>',
        f'    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>',
        f'    <language>en</language>',
    ]
    for it in items:
        rss_lines.extend([
            '    <item>',
            f'      <title>{html.escape(it["title"])}</title>',
            f'      <link>{html.escape(it["url"])}</link>',
            f'      <guid isPermaLink="true">{html.escape(it["url"])}</guid>',
            f'      <pubDate>{it["rfc822"]}</pubDate>',
            f'      <author>{html.escape(it["author"])}</author>',
            f'      <description>{html.escape(it["title"])} (commit {it["sha"]})</description>',
            '    </item>',
        ])
    rss_lines.extend(["  </channel>", "</rss>"])

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(rss_lines))
    print(f"  ✓ Wrote {OUT}  ({len(items)} items)")
    print(f"    Subscribe: {SITE}/feed.xml")


if __name__ == "__main__":
    main()
