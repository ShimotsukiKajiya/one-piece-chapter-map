"""Derive a gate chapter for every curated lore entry.

The Spoiler Shield can only hide an entry precisely if it knows the chapter the
reader learns about it. Most lore files already carry one (`debut`, `chapter`,
`debut_chapter`, ...) but under several different key names and formats, and a
few carry none at all. Before this script, entries it could not date were hidden
from every reader forever -- `combat-styles` rendered nothing at any chapter and
`music` showed 2 of 18 tracks to anyone not caught up.

This writes a normalised `gate_chapter` (plus `gate_source`, so the derivation is
auditable) into each entry, in priority order:

  1. explicit   -- the file's own chapter field, e.g. "Ch. 655" or 818
  2. episode    -- "Episode 48" resolved via episode_map.json (fail-late: the
                   LAST chapter the episode adapted)
  3. user       -- earliest debut of any named user/wielder, from punk_records
  4. none       -- left undated and reported as a worklist item

Idempotent: safe to re-run after every data refresh.

Run:
  python scripts/derive_gate_chapters.py            # report only, no writes
  python scripts/derive_gate_chapters.py --write    # write gate_chapter back
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.resolve import Resolver

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# file -> (list key, explicit chapter field or None)
SPECS = [
    ("tech.json",            "tech",        "debut"),
    ("items.json",           "items",       "debut"),
    ("materials.json",       "materials",   "debut"),
    ("ancient-weapons.json", "weapons",     "debut"),
    ("poneglyphs.json",      "poneglyphs",  "debut_chapter"),
    ("races.json",           "races",       "debut"),
    ("moments.json",         "moments",     "chapter"),
    ("music.json",           "tracks",      "debut"),
    ("reverie.json",         "events",      "chapter_start"),
    # combat-styles carried no chapter field, so gates were derived from each
    # technique's USER -- which dates the technique to the user's debut and is
    # simply wrong for anything they learn later. Ifrit Jambe (Wano) inherited
    # Sanji's Ch. 43. An explicit `debut` per technique is the fix.
    ("combat-styles.json",   "styles",      "debut"),
    ("haki.json",            "haki",        "debut_chapter"),
    ("awakenings.json",      "awakenings",  "awakening_chapter"),
    ("weapons.json",         "weapons",     "reveal_chapter"),
]

# Fields that may name a character the entry depends on.
USER_FIELDS = ("users", "user", "wielder", "wielders", "performers", "members", "holder",
               "current_holder", "participants")

# Non-canon films carry no chapter. Gate them at roughly the chapter that was
# current on release -- fail-late, and flagged for maintainer QA.
FILM_GATES = {"2019": 960, "2022": 1060, "2016": 840, "2012": 660, "2009": 560}


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return json.load(f)


def build_debut_map():
    """name -> first-appearance chapter, from punk_records."""
    pr = load("punk_records.json")
    out = {}
    for rec in pr.values():
        m = re.search(r"Chapter (\d+)", str(rec.get("first_appearance") or ""))
        if m:
            out[(rec.get("name") or "").strip()] = int(m.group(1))
    return out


def build_episode_map():
    """episode number -> last chapter that episode adapted (fail-late).

    Filler episodes adapt no chapter at all, so they are absent. `resolve_episode`
    falls back to the nearest EARLIER adapting episode, which is the most a reader
    at that point in the anime could have seen."""
    em = load("episode_map.json")
    out = {}
    for e in em.get("episodes", []):
        chs = [c for c in (e.get("chapters") or []) if isinstance(c, int)]
        if chs:
            out[e["ep"]] = max(chs)
    return out


def resolve_episode(ep, ep_map):
    """Episode -> chapter. Filler episodes adapt nothing, so fall back to the
    nearest LATER adapting episode: fail-late, per docs/canon-policy. Falling
    back to the earlier neighbour would surface the entry sooner, which is the
    unsafe direction."""
    if ep in ep_map:
        return ep_map[ep], "episode"
    later = [e for e in ep_map if e > ep]
    if later:
        return ep_map[min(later)], "episode-filler"
    earlier = [e for e in ep_map if e < ep]
    if earlier:
        return ep_map[max(earlier)], "episode-filler"
    return None, None


def explicit_chapter(value, ep_map):
    """Parse a chapter out of the entry's own field. Returns (chapter, source)."""
    if value is None:
        return None, None
    if isinstance(value, int):
        return (value, "explicit") if value > 0 else (None, None)

    s = str(value)

    film = re.search(r"film[^0-9]*(\d{4})", s, re.I)
    if film:
        return FILM_GATES.get(film.group(1)), "film-qa"

    ep = re.search(r"episode\s*(\d+)", s, re.I)
    if ep and not re.search(r"\bch\b|chapter", s, re.I):
        return resolve_episode(int(ep.group(1)), ep_map)

    m = re.search(r"(\d{1,4})", s)
    if m:
        return int(m.group(1)), "explicit"
    return None, None


def user_chapter(entry, resolver):
    """Earliest debut among any characters this entry names.

    Goes through entity_index (11,893 aliases) rather than exact-matching, so
    "Vinsmoke Sanji", "Zeff (former)" and "Sakazuki (Akainu)" all resolve."""
    names = []
    for field in USER_FIELDS:
        v = entry.get(field)
        if isinstance(v, str):
            names.append(v)
        elif isinstance(v, list):
            names += [x for x in v if isinstance(x, str)]
    return resolver.earliest_debut(names)


def load_lexicon():
    with open(os.path.join(ROOT, "docs", "leak-lexicon.json"), encoding="utf-8") as f:
        terms = [(t["term"], int(t["ch"])) for t in json.load(f)["terms"]]
    terms.sort(key=lambda t: (-len(t[0]), t[0]))
    return terms


def entry_text(entry):
    parts = []
    for k, v in entry.items():
        if k.startswith("_") or k in ("gate_chapter", "gate_source"):
            continue
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts += [x for x in v if isinstance(x, str)]
    return " ".join(parts)


def raise_for_text(entry, lexicon):
    """An entry cannot be shown before the reader can read its own description.

    Deriving a technique's chapter from its USER'S debut assumes the technique
    existed when the user did, which is false -- "Diable Jambe" inherited
    Sanji's Ch. 43 and "King of Hell" inherited Zoro's Ch. 3. Where the text
    names a term the reader has not met, the gate rises to that term's chapter.

    Fail-late and mechanical: no editorial judgement, no guessing. Laddering can
    later bring an entry back EARLIER with a rung written for that chapter, but
    that is an enhancement, not a correction."""
    ch = entry.get("gate_chapter")
    if ch is None:
        return None
    text = entry_text(entry)
    needed = ch
    blocker = None
    for term, tch in lexicon:
        if tch > needed and term in text:
            needed, blocker = tch, term
    if needed > ch:
        return needed, blocker
    return None


def main():
    write = "--write" in sys.argv
    resolver = Resolver(ROOT)
    ep_map = build_episode_map()
    lexicon = load_lexicon()
    raised = []

    print("=" * 70)
    print("  Derive gate chapters for curated lore entries")
    print("=" * 70)
    print(f"\n  {'file':22} {'n':>3}  {'explicit':>8} {'episode':>7} {'user':>5} {'film':>4} {'NONE':>5}  first")
    print("  " + "-" * 68)

    undated_all = []
    total_undated = 0

    for fname, key, ck in SPECS:
        doc = load(fname)
        items = doc.get(key) or []
        counts = {"explicit": 0, "episode": 0, "episode-filler": 0, "user": 0, "film-qa": 0, "none": 0}
        gates = []

        for e in items:
            # A laddered entry governs its own gate: the lowest rung is the
            # chapter it first appears, and the rung system already keeps each
            # wording safe for its own chapter. Re-deriving from the base
            # fields would recompute a gate from the LATEST wording and raise
            # it back over the ladder, silently undoing the laddering work on
            # the next refresh.
            rungs = e.get("rungs")
            if isinstance(rungs, list) and rungs:
                chs = [r["ch"] for r in rungs if isinstance(r.get("ch"), int)]
                if chs:
                    e["gate_chapter"] = min(chs)
                    e["gate_source"] = "rung"
                    counts["explicit"] += 1
                    gates.append(min(chs))
                    continue

            ch, src = explicit_chapter(e.get(ck) if ck else None, ep_map)
            if ch is None:
                ch = user_chapter(e, resolver)
                src = "user" if ch is not None else None
            if ch is None:
                counts["none"] += 1
                undated_all.append((fname, e.get("name") or e.get("title") or "?"))
            else:
                counts[src if src in counts else "explicit"] += 1
                e["gate_chapter"] = ch
                e["gate_source"] = src
                bump = raise_for_text(e, lexicon)
                if bump:
                    new_ch, blocker = bump
                    raised.append((fname, e.get("name") or e.get("title") or "?",
                                   ch, new_ch, blocker))
                    e["gate_chapter"] = new_ch
                    e["gate_source"] = src + "+text"
                    ch = new_ch
                gates.append(ch)

        first = min(gates) if gates else None
        total_undated += counts["none"]
        eps = counts["episode"] + counts["episode-filler"]
        print(f"  {fname:22} {len(items):>3}  {counts['explicit']:>8} {eps:>7} "
              f"{counts['user']:>5} {counts['film-qa']:>4} {counts['none']:>5}  {first}")

        if write:
            with open(os.path.join(ROOT, fname), "w", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write("\n")

    print("\n  " + "-" * 68)

    if raised:
        print(f"\n  RAISED ({len(raised)}) — gate moved up because the entry's own text"
              f"\n  names something the reader could not yet have met:\n")
        for fname, name, was, now, blocker in raised:
            print(f"    {name[:32]:32} {was:>4} → {now:>4}   ('{blocker}')")
        print("\n    These are candidates for laddering: a rung written for the"
              "\n    earlier chapter would bring them back without the later term.")

    if undated_all:
        print(f"\n  STILL UNDATED ({total_undated}) -- these stay hidden from shielded readers:")
        for fname, name in undated_all:
            print(f"    {fname:22} {name[:46]}")
    else:
        print("\n  Every entry has a gate chapter.")

    print(f"\n  {'WROTE gate_chapter into source files.' if write else 'Dry run -- pass --write to apply.'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
