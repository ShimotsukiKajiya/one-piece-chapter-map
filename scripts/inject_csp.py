"""
inject_csp.py — Add a Content-Security-Policy meta tag to every HTML
page that doesn't already have one.

GitHub Pages can't set custom HTTP headers, so a `<meta http-equiv="CSP">`
tag is the only way to apply CSP on this stack. Some directives
(frame-ancestors, sandbox, report-uri) are silently ignored in meta
form — for those, we rely on JS frame-busting in nav-burger.js.

The policy permits:
  - Inline <script> and <style> blocks (the site is built around them)
  - Images over HTTPS from anywhere (wiki, Wikimedia, etc.) + data: URIs
  - AJAX only to api.github.com (corrections.html issue fetch)
  - Form submissions to self or github.com (workbench issue prefill)

The policy blocks:
  - External <script src=> from random domains
  - object/embed plugins
  - <base> tag injection (base-uri 'self')
  - Mixed-content HTTP resources (default-src 'self' + img-src https:)
"""
import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Single-line CSP — kept compact for readability of the head section.
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.github.com; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self' https://github.com"
)

CSP_TAG = (
    f'<meta http-equiv="Content-Security-Policy" content="{CSP}">'
)

# Insert immediately after the <meta charset=...> line so the policy
# applies before any other resources are referenced.
CHARSET_RE = re.compile(
    r'(<meta\s+charset=["\']?utf-?8["\']?\s*/?>)',
    re.IGNORECASE,
)


def inject(html: str) -> tuple[str, bool]:
    if 'http-equiv="Content-Security-Policy"' in html:
        return html, False  # already present
    m = CHARSET_RE.search(html)
    if not m:
        return html, False  # can't find anchor; skip
    insertion = m.group(0) + "\n" + CSP_TAG
    return html[:m.start()] + insertion + html[m.end():], True


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    added, already, skipped = 0, 0, 0
    for fn in files:
        path = os.path.join(DIR, fn)
        with open(path, encoding="utf-8") as f:
            html = f.read()
        new_html, changed = inject(html)
        if changed:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_html)
            added += 1
            print(f"  + {fn}")
        elif 'http-equiv="Content-Security-Policy"' in html:
            already += 1
        else:
            skipped += 1
            print(f"  ! {fn} (no <meta charset> anchor — skipped)")
    print(f"\n  added: {added}  already: {already}  skipped: {skipped}")


if __name__ == "__main__":
    main()
