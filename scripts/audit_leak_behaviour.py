"""D2 — Behaviour: does the gate actually hide what it should?

`audit_spoiler_coverage.py` checks whether a page LOADS the shield. It reported
100% coverage on pages that were, at that moment, showing Imu and the Mother
Flame to a Chapter-5 reader. Structure is not behaviour.

Three checks, because leaks live in three different places:

  A  STATIC CHROME  — hand-written page copy (headings, intros, filter chips)
     is not entry data and is never touched by the entry filter. Every real
     leak found in the 2026-08 sweep lived here. A term in static copy is a
     leak unless the page is nav-gated at or above that term's chapter, or
     the page opts into runtime scrubbing.

  B  OVER-HIDING    — entries that carry a valid chapter but are dropped anyway
     because their text names an unearned term. Not a leak: the opposite. This
     is what empties pages, and it is the laddering worklist.

  C  SELF-TEST      — assert the gate logic really does exclude a leaking entry.
     Without this the whole checker can pass vacuously, which is exactly what
     happened on its first draft.

Exit codes match audit.py: 0 = clean · 2 = leak found.

Run:
  python scripts/audit_leak_behaviour.py
  python scripts/audit_leak_behaviour.py --verbose
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.gate import (LORE_PAGES, THRESHOLDS, load_lexicon, load_page, visible,
                      entry_text, text_leaks, entry_label, gate_chapter, nav_gates)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Pages whose whole subject is the term — the heading necessarily names it.
# Safe only because the nav gate keeps a below-cutoff reader from being linked
# there. Tracked as accepted residual, not silently ignored.
SELF_NAMING = {
    "haki.html": {"Haki"},
    "awakenings.html": {"Awakening"},
    "poneglyphs.html": {"Poneglyph"},
    "void-century.html": {"Void Century"},
    "ancient-weapons.html": {"Pluton"},
    # The fruit pages are named for the concept, and Ch. 19 is early enough
    # that the term is effectively universal.
    "fruits.html": {"Devil Fruit"},
    "fruit.html": {"Devil Fruit"},
    "characters.html": {"Devil Fruit"},
    "home.html": {"Devil Fruit"},
}


def has_min_ch_handler(raw):
    """Does this page act on data-min-ch at all?

    Either lore-gate.js (site-wide) or a page-local handler — prove.html has its
    own, written before lore-gate.js existed. Missing this produced a false
    positive on the checker's first run."""
    return "lore-gate.js" in raw or "data-min-ch" in re.sub(
        r"<script\b.*?</script>", lambda m: m.group(0), raw) and bool(
        re.search(r"getAttribute\(\s*['\"]data-min-ch", raw))


def static_text(path, drop_min_ch=False):
    """Visible-ish hand-written copy: strip scripts, styles and tags.

    When the page acts on data-min-ch, elements carrying it are removed first —
    the runtime hides them, so they are not reader-facing below their chapter."""
    with open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    if drop_min_ch:
        html = re.sub(r"<(\w+)[^>]*\bdata-min-ch\b[^>]*>.*?</\1>", " ",
                      html, flags=re.S | re.I)
        html = re.sub(r"<\w+[^>]*\bdata-min-ch\b[^>]*/?>", " ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html)


def main():
    verbose = "--verbose" in sys.argv
    lexicon = load_lexicon(ROOT)
    gates = nav_gates(ROOT)

    print("=" * 74)
    print("  D2 — Leak behaviour: what a reader actually sees")
    print("=" * 74)
    print(f"\n  {len(lexicon)} lexicon terms · {len(THRESHOLDS)} thresholds\n")

    # ── C. self-test first, so a vacuous pass is impossible ───────────────
    canary = {"name": "canary", "notes": "mentions Imu deliberately", "gate_chapter": 5}
    if visible([canary], 5, lexicon):
        print("  ✗ SELF-TEST FAILED — a leaking entry was not excluded.")
        print("    The gate logic in lib/gate.py is not filtering. Fix before trusting.\n")
        return 2
    if not visible([{"name": "ok", "notes": "harmless", "gate_chapter": 5}], 5, lexicon):
        print("  ✗ SELF-TEST FAILED — a safe entry was excluded.\n")
        return 2
    print("  ✓ self-test: gate excludes a leaking entry, keeps a safe one\n")

    # ── A. static chrome ──────────────────────────────────────────────────
    # A term in hand-written copy is only a leak if NOTHING covers it. Three
    # things can cover it: a nav gate at or above the term's chapter, runtime
    # scrubbing (lore-gate.js, optionally with data-lore-scrub), or the page
    # being the term's own subject.
    chrome_leaks = []   # nothing protects this — real leak
    chrome_partial = [] # only the blurb-level gate protects it — worth a look
    for fname in sorted(os.listdir(ROOT)):
        if not fname.endswith(".html"):
            continue
        path = os.path.join(ROOT, fname)
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        has_gate_js = "lore-gate.js" in raw
        has_scrub = 'data-lore-scrub="1"' in raw
        text = static_text(path, drop_min_ch=has_min_ch_handler(raw))
        gate = gates.get(fname, 0)
        for term, ch in lexicon:
            if term not in text:
                continue
            if ch <= gate:
                continue                        # nav gate covers it
            if term in SELF_NAMING.get(fname, ()):
                continue                        # accepted residual
            if has_gate_js and has_scrub:
                continue                        # runtime removes leaking blocks
            if has_gate_js:
                chrome_partial.append((fname, term, ch, gate))
            else:
                chrome_leaks.append((fname, term, ch, gate))

    # ── D. wiring ─────────────────────────────────────────────────────────
    # The gap this checker itself fell into: proving the DATA would gate
    # correctly says nothing about whether the page calls a gate at all.
    # Three mechanisms are legitimate — the shared LoreGate filter, a page-local
    # cutoff reader (weapons.html), or a whole-page refusal (awakenings.html
    # hides everything below 783). A page with none of them renders everything.
    unwired = []
    for fname, key, page in LORE_PAGES:
        path = os.path.join(ROOT, page)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            raw = f.read()
        # Every lore page ships a boilerplate stub that reads the cutoff into a
        # data attribute and does nothing with it — the file's own comment calls
        # it "currently a no-op". Counting it as wiring makes this check pass on
        # exactly the pages it exists to catch, so strip it before looking.
        probe = re.sub(r"<script>(?:(?!</script>).)*?dataset\.spoilerCutoff"
                       r"(?:(?!</script>).)*?</script>", " ", raw, flags=re.S)
        if "LoreGate.filter" in probe:
            continue
        if "effectiveCutoff" in probe or "cutoff_chapter" in probe:
            continue
        unwired.append(page)

    # ── B. over-hiding ────────────────────────────────────────────────────
    overhidden = []
    for fname, key, page in LORE_PAGES:
        for e in load_page(ROOT, fname, key):
            ch = gate_chapter(e)
            if ch is None:
                continue
            hit = text_leaks(entry_text(e), ch, lexicon)
            if hit:
                overhidden.append((page, entry_label(e), ch, hit[0], hit[1]))

    print(f"  A  static chrome     {len(chrome_leaks):>3} unprotected · "
          f"{len(chrome_partial)} blurb-gate only")
    print(f"  B  over-hidden       {len(overhidden):>3} entry/entries suppressed by the lexicon")
    print(f"  D  wiring            {len(unwired):>3} lore page(s) with no gate at all")

    if unwired:
        print(f"\n  ✗ UNGATED PAGES — these render every entry to every reader:\n")
        for page in unwired:
            print(f"      {page}")
        print("\n      Fix: wrap the render in LoreGate.filterList(...), or add a"
              "\n      page-level gate.")

    if chrome_leaks:
        print(f"\n  ✗ STATIC CHROME LEAKS — hand-written copy naming an unearned term:\n")
        shown = chrome_leaks if verbose else chrome_leaks[:20]
        for fname, term, ch, gate in shown:
            g = f"nav gate {gate}" if gate else "no nav gate"
            print(f"      {fname:24} '{term}' (safe from {ch}) · {g}")
        if not verbose and len(chrome_leaks) > 20:
            print(f"      … and {len(chrome_leaks) - 20} more (--verbose)")
        print("\n      Fix: gate the page in nav-burger.js, add data-min-ch to the"
              "\n      element, load lore-gate.js, or rewrite the copy.")

    if chrome_partial and verbose:
        print(f"\n  · BLURB-GATE ONLY — protected if the term sits in intro copy,"
              f"\n    unprotected if it sits anywhere else on the page:\n")
        for fname, term, ch, gate in chrome_partial:
            print(f"      {fname:24} '{term}' (safe from {ch})")

    if overhidden:
        print(f"\n  ⚠ OVER-HIDDEN — dated entries the lexicon still suppresses."
              f"\n    These are why pages go blank. Laddering is the fix.\n")
        shown = overhidden if verbose else overhidden[:15]
        for page, label, ch, term, term_ch in shown:
            print(f"      {page:22} {label[:24]:24} dated {ch:>4} but names "
                  f"'{term}' ({term_ch})")
        if not verbose and len(overhidden) > 15:
            print(f"      … and {len(overhidden) - 15} more (--verbose)")

    print()
    return 2 if (chrome_leaks or unwired) else 0


if __name__ == "__main__":
    sys.exit(main())
