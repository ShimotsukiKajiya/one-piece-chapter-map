"""Hand-curated weapon ownership canon_facts.

Unlike family / first_appearance / devil_fruit_name, there's no clean
auto-extractable source for weapon ownership. This script encodes a
small set of well-attested Meito ownerships with manga chapter
citations, idempotently merged into canon_facts.json.

Used by scripts/link_owns.py as the cross-reference target.

The set is deliberately small (~9 entries) — enough to:
  * surface the Murakumogiri-missing-from-shard parenthetical-resolver
    gap as a real conflict
  * give the major Meito (Yoru, Wado, Enma, etc.) tier=canon promotion
    via cross-link
  * stop short of full coverage; full coverage waits for either a
    proper extractor or a Vivre Card ingest.

Add to ENTRIES below. Each entry must have:
  subject  — character name (canonical, matched against entity_index)
  predicate — always "owns"
  value    — weapon canonical name (matched against entity_index)
  chapter  — manga chapter that confirms ownership
  notes    — short evidence_notes string

Run:
    py extract_weapon_owner_facts.py
    py extract_weapon_owner_facts.py --dry-run
"""
import os, sys, json, re
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
FACTS_PATH = os.path.join(DIR, "canon_facts.json")
TODAY      = date.today().isoformat()
VERIFIER   = "extract_weapon_owner_facts.py v1"

# Hand-curated Meito ownership facts. Each is manga-cited and well-attested.
ENTRIES = [
    {"subject": "Dracule Mihawk",      "value": "Yoru",
     "chapter": 50,
     "notes": "Mihawk's signature black blade, the World's Strongest Sword, shown from his first appearance."},
    {"subject": "Roronoa Zoro",        "value": "Wado Ichimonji",
     "chapter": 5,
     "notes": "Zoro carries Wado from his first appearance — inherited from Kuina."},
    {"subject": "Roronoa Zoro",        "value": "Sandai Kitetsu",
     "chapter": 98,
     "notes": "Acquired in Loguetown — Zoro takes the third cursed blade by daring its curse."},
    {"subject": "Roronoa Zoro",        "value": "Shusui",
     "chapter": 469,
     "notes": "Taken from the corpse of Ryuma at Thriller Bark; later returned to Wano."},
    {"subject": "Roronoa Zoro",        "value": "Enma",
     "chapter": 954,
     "notes": "Hiyori gives Zoro Enma during Wano arc, replacing Shusui."},
    {"subject": "Kouzuki Oden",        "value": "Ame no Habakiri",
     "chapter": 819,
     "notes": "One of Oden's twin meito, used to cut Kaidou."},
    {"subject": "Kouzuki Oden",        "value": "Enma",
     "chapter": 819,
     "notes": "Oden's other twin meito, the only blade besides Ame no Habakiri to wound Kaidou."},
    {"subject": "Kouzuki Momonosuke",  "value": "Ame no Habakiri",
     "chapter": 1037,
     "notes": "Inherited from Oden post-Wano. Family heirloom of the Kouzuki line."},
    {"subject": "Edward Newgate",      "value": "Murakumogiri",
     "chapter": 552,
     "notes": "Whitebeard's massive naginata, used to channel Gura Gura no Mi quake-cracks at Marineford."},
]


def slugify(s):
    return re.sub(r"[^\w]+", "_", s).strip("_")[:80]


def make_fact(subj, value, chapter, notes):
    fact_id = f"owns:{slugify(subj)}:{slugify(value)}"
    return {
        "id":        fact_id,
        "subject":   subj,
        "predicate": "owns",
        "value":     value,
        "tier":      "canon",
        "intent":    "serious",
        "sources":   [{"type": "manga", "chapter": chapter}],
        "evidence_notes": notes,
        "verified_on": TODAY,
        "verified_by": VERIFIER,
    }


def main():
    dry = "--dry-run" in sys.argv

    print("=" * 60)
    print(f"  Weapon Owner Facts — hand-curated Meito ({len(ENTRIES)} entries)")
    print(f"  Output: canon_facts.json")
    print("=" * 60)

    new_facts = [make_fact(e["subject"], e["value"], e["chapter"], e["notes"])
                 for e in ENTRIES]

    print(f"\n  Will add/update {len(new_facts)} canon_facts:")
    for f in new_facts:
        print(f"    {f['subject']:30s} owns {f['value']:25s}  ch:{f['sources'][0]['chapter']}")

    if dry:
        print("\n  (dry run — canon_facts.json not modified)")
        return

    facts = []
    if os.path.exists(FACTS_PATH):
        with open(FACTS_PATH, encoding="utf-8") as f:
            facts = json.load(f)
    by_id = {f["id"]: f for f in facts}

    new_count = 0
    replaced = 0
    for f in new_facts:
        if f["id"] in by_id:
            replaced += 1
        else:
            new_count += 1
        by_id[f["id"]] = f

    merged = list(by_id.values())
    tmp = FACTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(merged, ensure_ascii=False, indent=2))
        f.write("\n")
    os.replace(tmp, FACTS_PATH)

    print(f"\n  ✓ Wrote {FACTS_PATH}")
    print(f"     {new_count} new, {replaced} replaced, {len(merged):,} total")
    print("=" * 60)


if __name__ == "__main__":
    main()
