"""Populate `reveal_chapter` on every row of canon_facts.json.

The Spoiler Shield (spoiler.js) filters items by reveal_chapter ≤ user cutoff.
This script ensures every canon fact carries that field, so the gate can run.

Population strategy (in order — first match wins):
  1. Manual override from docs/reveal_overrides.json — always wins.
  2. For first_appearance facts: reveal_chapter = value.chapter (trivial).
  3. For other facts with a `manga` source citation: use sources[manga].chapter.
  4. For SBS-sourced facts: SBS volume → chapter range; use the volume's last
     chapter (sourced from the volumes table baked into chapter_dates.json).
  5. Otherwise: fall back to subject's first-appearance chapter (assume the
     fact is "trivia about a known character" — safe at debut). If subject
     also has no first-appearance fact: leave reveal_chapter NULL (fail-closed
     in the gate; the fact will never be shown).

The output is canon_facts.json with reveal_chapter filled in.

Run:
  python extract_reveal_chapter.py            # populate + write
  python extract_reveal_chapter.py --report   # just report coverage, don't write
"""
import json
import os
import sys
from collections import Counter

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = os.path.dirname(os.path.abspath(__file__))


# ── HELPERS ───────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_subject_debut_map(facts):
    """{subject_lower: chapter} from first_appearance facts."""
    out = {}
    for f in facts:
        if f.get("predicate") != "first_appearance":
            continue
        v = f.get("value", {})
        if isinstance(v, dict) and isinstance(v.get("chapter"), int):
            out[f["subject"].lower()] = v["chapter"]
    return out


def build_volume_chapter_map():
    """{volume_int: last_chapter_in_volume} from chapter_dates.json."""
    cd_path = os.path.join(ROOT, "chapter_dates.json")
    if not os.path.exists(cd_path):
        return {}
    cd = load_json(cd_path)
    out = {}
    for v in cd.get("volumes", []):
        try:
            out[int(v["volume"])] = int(v["last_ch"])
        except (KeyError, ValueError, TypeError):
            continue
    return out


def load_overrides():
    """Returns list of {match, reveal_chapter, note}."""
    path = os.path.join(ROOT, "docs", "reveal_overrides.json")
    if not os.path.exists(path):
        return []
    return load_json(path).get("overrides", [])


def fact_matches_override(fact, match):
    """Does the fact satisfy this override's match block?"""
    if "fact_id" in match:
        return fact.get("id") == match["fact_id"]
    if "subject" in match:
        if fact.get("subject", "").lower() != match["subject"].lower():
            return False
        if "predicate" in match:
            return fact.get("predicate") == match["predicate"]
        return True  # subject-only override: catch-all for that subject
    return False


def derive_reveal_chapter(fact, debuts, vol_to_ch, overrides):
    """Apply the strategy in order. Return chapter int or None."""

    # 1. Manual overrides (most-specific first: fact_id, then subject+predicate, then subject-only)
    # Sort: most-specific match wins. We do this by checking specificity score.
    candidates = []
    for o in overrides:
        if fact_matches_override(fact, o.get("match", {})):
            spec = 0
            m = o.get("match", {})
            if "fact_id" in m: spec += 100
            if "subject" in m: spec += 10
            if "predicate" in m: spec += 1
            candidates.append((spec, o))
    if candidates:
        candidates.sort(key=lambda c: -c[0])
        return candidates[0][1]["reveal_chapter"]

    # 2. first_appearance: trivially the value's chapter
    if fact.get("predicate") == "first_appearance":
        v = fact.get("value", {})
        if isinstance(v, dict) and isinstance(v.get("chapter"), int):
            return v["chapter"]

    # 3. manga-sourced fact: use the source citation's chapter
    sources = fact.get("sources", []) or []
    for s in sources:
        if s.get("type") == "manga" and isinstance(s.get("chapter"), int):
            return s["chapter"]

    # 4. SBS-sourced fact: use the volume's last chapter (most-conservative)
    for s in sources:
        if s.get("type") == "sbs" and isinstance(s.get("volume"), int):
            ch = vol_to_ch.get(s["volume"])
            if ch:
                return ch

    # 5. Fall back to subject's first-appearance chapter (trivia is safe at debut)
    subj = fact.get("subject", "").lower()
    if subj in debuts:
        return debuts[subj]

    # No determination possible — fail-closed.
    return None


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    report_only = "--report" in args

    cf_path = os.path.join(ROOT, "canon_facts.json")
    facts = load_json(cf_path)
    debuts = build_subject_debut_map(facts)
    vol_to_ch = build_volume_chapter_map()
    overrides = load_overrides()

    print("=" * 60)
    print("  Populating reveal_chapter on canon_facts.json")
    print("=" * 60)
    print(f"  Source rows:        {len(facts):,}")
    print(f"  Subject debut map:  {len(debuts):,} subjects with first_appearance")
    print(f"  Volume→chapter map: {len(vol_to_ch):,} volumes")
    print(f"  Manual overrides:   {len(overrides)}")
    print()

    counters = Counter()  # tally of reveal_chapter source per fact
    for f in facts:
        # Skip if already populated and we're not forcing
        if "reveal_chapter" in f and f["reveal_chapter"] is not None:
            counters["preserved"] += 1
            continue

        rc = derive_reveal_chapter(f, debuts, vol_to_ch, overrides)
        if rc is None:
            f["reveal_chapter"] = None
            counters["null_fail_closed"] += 1
        else:
            f["reveal_chapter"] = rc
            # Tally how this row got its value
            if any(fact_matches_override(f, o.get("match", {})) for o in overrides):
                counters["override"] += 1
            elif f.get("predicate") == "first_appearance":
                counters["first_appearance"] += 1
            elif any(s.get("type") == "manga" for s in f.get("sources", [])):
                counters["manga_source"] += 1
            elif any(s.get("type") == "sbs" for s in f.get("sources", [])):
                counters["sbs_volume"] += 1
            else:
                counters["subject_debut"] += 1

    populated = sum(1 for f in facts if f.get("reveal_chapter") is not None)
    coverage = (populated / len(facts) * 100) if facts else 0

    print(f"  Populated:    {populated:,} / {len(facts):,}  ({coverage:.1f}%)")
    print()
    print("  Source breakdown:")
    for k, v in counters.most_common():
        print(f"    {k:25} {v:>6,}")
    print()

    if not report_only:
        with open(cf_path, "w", encoding="utf-8") as f:
            json.dump(facts, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Wrote → {cf_path}")
    else:
        print("  (--report mode: file not written)")
    print("=" * 60)
    return 0 if counters["null_fail_closed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
