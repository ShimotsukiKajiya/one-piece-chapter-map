"""
design_standardize.py — Standardize logo text and apply page-hero treatment
across all Shimotsuki Codex HTML pages.

Changes per file:
  1. Logo h1: "One Piece" → "The Shimotsuki Codex"
  2. logo-sub: strip " · The Shimotsuki Codex" suffix
  3. Pages with page-title h2 + page-sub p: wrap in .page-hero + add .gold-rule
"""

import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root

# Leave completely untouched
SKIP = {'home.html', 'index.html', '404.html', 'corrections.html'}

# Pages where hero wrapping would break layout — logo fix only
# (complex full-page tools or pages with no standard page-title h2)
LOGO_ONLY = {
    'atlas.html', 'sbs.html', 'quiz.html', 'theories.html',
    'characters.html', 'character.html', 'workbench.html', 'curate.html',
    'covers.html', 'crew.html', 'ship.html', 'fruit.html', 'location.html',
    'conflicts.html', 'prove.html',
}


def fix_logo(html: str) -> tuple[str, list[str]]:
    changes = []

    # 1. h1 logo text
    if '<h1>One Piece</h1>' in html:
        html = html.replace('<h1>One Piece</h1>', '<h1>The Shimotsuki Codex</h1>')
        changes.append('logo h1')

    # 2. logo-sub: strip " · The Shimotsuki Codex" suffix
    new_html = re.sub(
        r'(<span class="logo-sub">)(.*?) · The Shimotsuki Codex(</span>)',
        r'\1\2\3',
        html
    )
    if new_html != html:
        html = new_html
        changes.append('logo-sub')

    return html, changes


def wrap_hero(html: str) -> tuple[str, list[str]]:
    changes = []

    # Skip if already has a page-hero wrapper
    if 'class="page-hero"' in html:
        return html, changes

    # Match h2.page-title optionally followed by p.page-sub
    # Pattern A: title + sub both present
    pattern_a = re.compile(
        r'[ \t]*(<h2 class="page-title">[^<]*</h2>)[ \t]*\r?\n'
        r'[ \t]*(<p class="page-sub">[^<]*</p>)',
        re.MULTILINE
    )

    def replace_a(m):
        h2 = m.group(1)
        p  = m.group(2)
        return (
            f'<div class="page-hero">\n'
            f'  {h2}\n'
            f'  {p}\n'
            f'  <div class="gold-rule"></div>\n'
            f'</div>'
        )

    new_html = pattern_a.sub(replace_a, html)
    if new_html != html:
        html = new_html
        changes.append('page-hero (title+sub)')
        return html, changes

    # Pattern B: title only (no page-sub)
    count = html.count('<h2 class="page-title">')
    if count == 1:
        pattern_b = re.compile(
            r'[ \t]*(<h2 class="page-title">[^<]*</h2>)',
            re.MULTILINE
        )
        new_html = pattern_b.sub(
            lambda m: (
                f'<div class="page-hero">\n'
                f'  {m.group(1)}\n'
                f'  <div class="gold-rule"></div>\n'
                f'</div>'
            ),
            html,
            count=1,
        )
        if new_html != html:
            html = new_html
            changes.append('page-hero (title only)')

    # Pattern C: newer lore pages — h2.title + p.blurb (content may have nested tags)
    if 'class="page-hero"' not in html:
        pattern_c = re.compile(
            r'[ \t]*(<h2 class="title">.*?</h2>)[ \t]*\r?\n'
            r'[ \t]*(<p class="blurb">.*?</p>)',
            re.DOTALL
        )
        new_html = pattern_c.sub(
            lambda m: (
                f'<div class="page-hero">\n'
                f'  {m.group(1)}\n'
                f'  {m.group(2)}\n'
                f'  <div class="gold-rule"></div>\n'
                f'</div>'
            ),
            html,
        )
        if new_html != html:
            html = new_html
            changes.append('page-hero (title+blurb)')

    return html, changes


def process_file(path: str, filename: str) -> tuple[bool, str]:
    with open(path, encoding='utf-8') as f:
        html = f.read()

    original = html
    all_changes = []

    html, logo_changes = fix_logo(html)
    all_changes.extend(logo_changes)

    if filename not in LOGO_ONLY:
        html, hero_changes = wrap_hero(html)
        all_changes.extend(hero_changes)

    if html == original:
        return False, 'no changes'

    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)

    return True, ', '.join(all_changes)


def main():
    html_files = sorted(
        f for f in os.listdir(DIR)
        if f.endswith('.html') and f not in SKIP
    )

    changed, skipped = [], []

    for filename in html_files:
        path = os.path.join(DIR, filename)
        was_changed, reason = process_file(path, filename)
        if was_changed:
            changed.append((filename, reason))
            print(f'  ✓ {filename}: {reason}')
        else:
            skipped.append(filename)

    print(f'\n{len(changed)} files updated, {len(skipped)} unchanged.')
    if skipped:
        print(f'  Unchanged: {", ".join(skipped)}')


if __name__ == '__main__':
    main()
