"""
One-shot meta-tag adder.

For every .html in the project root:
  - Adds <link rel="canonical" href="https://shimotsukicodex.com/<file>"> if missing.
  - Adds OG/Twitter card tags if missing.

Idempotent: skips files that already have canonical (assumes those were
done deliberately, e.g. home.html / index.html).

Usage:  py add_meta.py
"""
import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://shimotsukicodex.com"
SITE_DESC = ("The Shimotsuki Codex — a free fan-built One Piece reference. "
             "Every chapter mapped, every SBS archived, theories weighed against canon.")
SITE_IMAGE = f"{SITE_URL}/logo/shimotsuki-kajiya-mon.svg"
TWITTER_HANDLE = "@ShimotsukiCodex"

# Files we deliberately leave alone — already have full custom OG tags
SKIP_FILES = {"home.html", "index.html"}

# Files that aren't actual pages (404 lives at /404, not for sharing)
HIDDEN_FILES = {"404.html"}


def extract_title(html: str) -> str:
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    return m.group(1).strip() if m else "The Shimotsuki Codex"


def has_canonical(html: str) -> bool:
    return bool(re.search(r'<link\s+rel=["\']canonical["\']', html, re.IGNORECASE))


def has_og(html: str) -> bool:
    return bool(re.search(r'property=["\']og:title["\']', html, re.IGNORECASE))


def build_meta_block(filename: str, title: str, include_og: bool) -> str:
    url = f"{SITE_URL}/{filename}"
    parts = [f'<link rel="canonical" href="{url}">']

    if include_og:
        # Use the page <title> as og:title; site description as og:description.
        parts += [
            f'<meta property="og:title" content="{title}">',
            f'<meta property="og:description" content="{SITE_DESC}">',
            f'<meta property="og:type" content="website">',
            f'<meta property="og:url" content="{url}">',
            f'<meta property="og:image" content="{SITE_IMAGE}">',
            f'<meta property="og:site_name" content="The Shimotsuki Codex">',
            f'<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:site" content="{TWITTER_HANDLE}">',
            f'<meta name="twitter:title" content="{title}">',
            f'<meta name="twitter:description" content="{SITE_DESC}">',
            f'<meta name="twitter:image" content="{SITE_IMAGE}">',
        ]

    return "  " + "\n  ".join(parts) + "\n"


def patch_file(path: str) -> str:
    """Returns 'added', 'canonical-only', 'skipped-existing', or 'no-head'."""
    fn = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    if has_canonical(html):
        return "skipped-existing"

    title = extract_title(html)
    include_og = not has_og(html) and fn not in HIDDEN_FILES
    block = build_meta_block(fn, title, include_og)

    # Insert just before </head>
    m = re.search(r"</head>", html, re.IGNORECASE)
    if not m:
        return "no-head"

    new_html = html[: m.start()] + block + html[m.start() :]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)

    return "added" if include_og else "canonical-only"


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    print(f"Found {len(files)} HTML files\n")

    counts = {"added": 0, "canonical-only": 0, "skipped-existing": 0, "no-head": 0, "skipped-by-name": 0}
    for fn in files:
        if fn in SKIP_FILES:
            counts["skipped-by-name"] += 1
            print(f"  · {fn:<28} skipped (kept custom OG tags)")
            continue
        result = patch_file(os.path.join(DIR, fn))
        counts[result] += 1
        marker = {"added": "✓", "canonical-only": "+", "skipped-existing": "-", "no-head": "✗"}[result]
        print(f"  {marker} {fn:<28} {result}")

    print()
    for k, v in counts.items():
        if v: print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
