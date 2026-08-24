"""Python mirror of the runtime gate in lore-gate.js.

The browser decides what a reader sees; CI has to decide the same thing without
a browser. Because gating is now data-driven (`gate_chapter` written by
derive_gate_chapters.py, plus the shared lexicon), the decision is computable
from the JSON alone — no Playwright, no headless Chrome, runs in a second.

Kept deliberately small and in step with lore-gate.js:
  - an entry is visible when its gate chapter is at or below the cutoff
  - AND none of its text names a lexicon term the reader has not earned
  - an entry with no gate chapter is hidden (fail-late)

If lore-gate.js changes its rules, change them here in the same commit.
"""
import json
import os

# The lore data files, their list key, and the page that renders them.
LORE_PAGES = [
    ("tech.json",            "tech",       "tech.html"),
    ("items.json",           "items",      "items.html"),
    ("materials.json",       "materials",  "materials.html"),
    ("ancient-weapons.json", "weapons",    "ancient-weapons.html"),
    ("poneglyphs.json",      "poneglyphs", "poneglyphs.html"),
    ("races.json",           "races",      "races.html"),
    ("moments.json",         "moments",    "moments.html"),
    ("music.json",           "tracks",     "music.html"),
    ("reverie.json",         "events",     "reverie.html"),
    ("combat-styles.json",   "styles",     "combat-styles.html"),
    ("haki.json",            "haki",       "haki.html"),
    ("awakenings.json",      "awakenings", "awakenings.html"),
    ("weapons.json",         "weapons",    "weapons.html"),
]

# Chapters to probe. Boundary-heavy around the big reveals.
THRESHOLDS = [5, 100, 200, 300, 400, 500, 597, 700, 800, 900, 1000, 1044, 1086, 1190]

CAP = 1190


def load_lexicon(root):
    with open(os.path.join(root, "docs", "leak-lexicon.json"), encoding="utf-8") as f:
        doc = json.load(f)
    terms = [(t["term"], int(t["ch"])) for t in doc["terms"]]
    terms.sort(key=lambda t: (-len(t[0]), t[0]))
    return terms


def load_page(root, fname, key):
    with open(os.path.join(root, fname), encoding="utf-8") as f:
        doc = json.load(f)
    return doc.get(key) or []


def entry_text(entry):
    """Every string the entry could render. Mirrors entryText() in lore-gate.js."""
    parts = []
    for k, v in entry.items():
        if k.startswith("_") or k in ("gate_chapter", "gate_source"):
            continue
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts += [x for x in v if isinstance(x, str)]
    return " ".join(parts)


def gate_chapter(entry):
    for k in ("gate_chapter", "debut_chapter", "chapter", "reveal_chapter", "since"):
        v = entry.get(k)
        if isinstance(v, int) and v > 0:
            return v
    return None


def text_leaks(text, cutoff, lexicon):
    """First lexicon term in `text` that the reader at `cutoff` has not earned."""
    for term, ch in lexicon:
        if ch > cutoff and term in text:
            return term, ch
    return None


def visible(entries, cutoff, lexicon):
    """The entries a reader at `cutoff` sees. Caught-up sees everything."""
    if cutoff >= CAP:
        return list(entries)
    out = []
    for e in entries:
        ch = gate_chapter(e)
        if ch is None or ch > cutoff:
            continue
        if text_leaks(entry_text(e), cutoff, lexicon):
            continue
        out.append(e)
    return out


def entry_label(entry):
    for k in ("name", "title", "user", "fruit"):
        v = entry.get(k)
        if isinstance(v, str) and v:
            return v
    return "?"


def nav_gates(root):
    """page -> minCh currently declared in nav-burger.js."""
    import re
    with open(os.path.join(root, "nav-burger.js"), encoding="utf-8") as f:
        src = f.read()
    out = {}
    for m in re.finditer(r"href:\s*'([a-z0-9.-]+\.html)'[^}]*?minCh:\s*(\d+)", src):
        out[m.group(1)] = int(m.group(2))
    return out
