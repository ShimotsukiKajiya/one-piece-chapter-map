"""
Add <meta name="description"> to pages that don't have one.

Each description is short (under 160 chars), specific to the page's role,
and ends in the same neutral footer phrase to keep voice consistent.

Idempotent: skips files that already have a description meta.

Usage:  py add_descriptions.py
"""
import os
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))

# Page-specific descriptions. Keep each under 160 chars including the
# trailing site phrase that the regex appends if the dict value is short.
DESCRIPTIONS = {
    "about.html":         "About the Shimotsuki Codex — what it is, how it works, the Canon Engine trust tiers, and how to contribute.",
    "ancient-weapons.html":"Pluton, Poseidon, Uranus — the three Ancient Weapons of One Piece, with every canon mention, debut chapter, and known users.",
    "arcs.html":          "Every One Piece story arc grouped by saga. Click any arc to filter the Chapter Atlas to its chapters.",
    "atlas.html":         "Chapter Atlas — every One Piece chapter as a coloured square. Click any character to highlight every chapter they appear in.",
    "awakenings.html":    "Awakened Devil Fruit users in One Piece — every confirmed awakening, the user, the fruit type, and the chapter it was revealed.",
    "bounties.html":      "Bounty Wall — every Marine bounty in One Piece pinned as a wanted poster. Filter by crew, era, or amount.",
    "character.html":     "Character profile in the Shimotsuki Codex — appearances, devil fruit, crew, voice cast, debut chapter, and cited canon facts.",
    "characters.html":    "Punk Records — 1,500+ One Piece characters with portraits, devil fruits, crews, bounties, and chapter-by-chapter appearance data.",
    "combat-styles.html": "Combat styles in One Piece — Rokushiki, Black Leg, Santoryu, Fishman Karate and more, with practitioners and signature techniques.",
    "compare.html":       "Compare One Piece characters side by side — bounties, fruits, crews, debut chapters, and appearance counts.",
    "conflicts.html":     "Major conflicts in One Piece — wars, raids, and arc-defining battles with chapter ranges and outcomes.",
    "corrections.html":   "Corrections Inbox — live feed of reader-submitted fixes for SBS Q&As, character data, and theory verdicts via GitHub Issues.",
    "covers.html":        "Cover Compendium — Oda's mini-arcs that run on chapter title pages, ordered chronologically with chapter ranges.",
    "crew.html":          "Crew profile in the Shimotsuki Codex — full roster, ship, jolly roger, bounty totals, allies, and current status.",
    "crews.html":         "358 crews and organisations in One Piece — Marines, pirates, revolutionaries, civilian factions, with rosters and affiliations.",
    "curate.html":        "Curate canon facts for the Shimotsuki Codex — submit verified claims with sources to grow the trust-tiered reference layer.",
    "episodes.html":      "Manga ↔ Anime cross-reference — every One Piece arc with its chapter range, episode range, and any filler interruptions.",
    "families.html":      "One Piece family trees — 52 hand-curated bloodlines and adoptive bonds with chapter citations and collapsible branches.",
    "fruit.html":         "Devil Fruit profile — type, current and former users, named techniques, awakening status, and debut chapter.",
    "fruits.html":        "Devil Fruit Codex — 155 One Piece devil fruits, type-coded (Paramecia, Logia, Zoan, Mythical, Ancient), with users and abilities.",
    "haki.html":          "The three forms of Haki in One Piece — Observation, Armament, Conqueror's — with notable users, advanced applications, and debut.",
    "heatmap.html":       "Canon Density Heatmap — every chapter colour-graded by how many verified canon facts attach to it. Click any chapter for its facts.",
    "heights.html":       "Height Wall — One Piece characters at scale, sorted by canonical height from giants down to the smallest tribes.",
    "items.html":         "Items and consumables in One Piece — SMILE fruits, Energy Steroids, Rumble Balls, and other artefacts with effects and users.",
    "jolly-rogers.html":  "Jolly Rogers of every named One Piece pirate crew — designs, era, captain, and chapter of debut.",
    "location.html":      "Location profile in the Shimotsuki Codex — arcs visited, key events, debut chapter, and characters who debuted there.",
    "locations.html":     "57 islands, kingdoms, and cities in One Piece — grouped by region (East Blue, Grand Line, New World) with arcs and chapter refs.",
    "marines-wg.html":    "Marines and World Government — every named officer, agency, Cipher Pol unit, and Celestial Dragon in One Piece, with ranks and arcs.",
    "materials.html":     "Materials in One Piece — Sea Stone, Adam Wood, Wapometal, Pyrobloin, and other rare substances with sources and uses.",
    "moments.html":       "Iconic moments in One Piece — Oda's chapter title pages, the great speeches, the cries, the fights, anchored to chapter and arc.",
    "music.html":         "One Piece music and songs — Bink's Sake, Soldier Song, Brook's compositions, and other in-canon music with debut chapters.",
    "news.html":          "What's new in the Shimotsuki Codex — recent data updates, new pages, and feature releases.",
    "poneglyphs.html":    "The Poneglyphs of One Piece — Road, Mother, Rio — every confirmed location, holder, and what each one says.",
    "prove.html":         "Prove an Idea — claim tester returns CONFIRMED / LIKELY / UNKNOWN / CONTRADICTED with cited evidence from One Piece canon.",
    "punk-records.html":  "Punk Records — 1,500+ One Piece characters with portraits, stats, and cross-links to every chapter they appear in.",
    "quiz.html":          "Trivia Trial — One Piece quiz generated from chapter appearance data and curated facts about devil fruits, epithets, and canon.",
    "races.html":         "Races and tribes in One Piece — Fishmen, Mink, Giants, Skypieans, Lunarians, Buccaneers, and every other race with notable members.",
    "reverie.html":       "Reverie and major world events in One Piece — the Levely, the World Conscription, Marineford, Wano, with chapter ranges and outcomes.",
    "sagas.html":         "All One Piece sagas grouped by era — East Blue through to the current Final Saga — with chapter ranges and arc lists.",
    "sbs-topics.html":    "SBS by Topic — every Oda Q&A bucketed by subject (devil fruits, character ages, world building) for faster browse.",
    "sbs.html":           "SBS Vault — every Q&A Oda has ever answered, searchable by character, topic, or volume, with auto-linked references.",
    "ship.html":          "Ship profile in the Shimotsuki Codex — class, captain, crew, debut chapter, and current status.",
    "ships.html":         "Every named ship in One Piece — Going Merry, Thousand Sunny, Moby Dick, Red Force, with classes, captains, and arcs.",
    "tech.html":          "Technology and artefacts in One Piece — Den Den Mushi, Cipher Pol gear, Vegapunk inventions, with chapters of debut and users.",
    "theories.html":      "Theory Forge — top fan theories weighed against actual One Piece canon. Verdicts: Active, Confirmed, Debunked, Partial, with citations.",
    "timeline.html":      "Story Timeline — vertical scroll through every saga and arc with notable canon events, character debuts, and chapter anchors.",
    "tools.html":         "Tools in the Shimotsuki Codex — Trivia Trial, Curate, and other interactive references for One Piece readers.",
    "voices.html":        "One Piece voice cast — Japanese, English, and other dub actors, the characters they play, and their arcs.",
    "void-century.html":  "The Void Century — what canon actually says about the 100-year gap, the Ancient Kingdom, Joy Boy, and the Will of D.",
    "weapons.html":       "Weapons and Meito of One Piece — the 12 Supreme Grade swords, named blades, firearms, and other notable weapons by chapter.",
    "will-of-d.html":     "The Will of D. — every confirmed bearer, what canon says about the Will, and Oda's SBS replies on the topic.",
    "workbench.html":     "Theory Workbench — build your own One Piece theory with cited Fact Cards from anywhere in the Codex. Drafts saved in your browser.",
    "world-map.html":     "Interactive One Piece world map — click any island to see its arcs, debut chapter, and characters introduced there.",
    "404.html":           "This page wandered off the chart. Try the Codex home or the menu to get back on course.",
}

# Don't touch these — they already have hand-tuned descriptions
SKIP_FILES = {"home.html", "index.html", "punk-records.html", "families.html", "lore.html", "tools.html"}


def has_description(html: str) -> bool:
    return bool(re.search(r'<meta\s+name=["\']description["\']', html, re.IGNORECASE))


def patch_file(path: str) -> str:
    fn = os.path.basename(path)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    if has_description(html):
        return "skipped-existing"

    desc = DESCRIPTIONS.get(fn)
    if not desc:
        return "no-mapping"

    # Insert after the <title> tag for clean placement
    m = re.search(r"</title>", html, re.IGNORECASE)
    if not m:
        return "no-title"

    insertion = f'\n<meta name="description" content="{desc}">'
    new_html = html[: m.end()] + insertion + html[m.end() :]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return "added"


def main():
    files = sorted(f for f in os.listdir(DIR) if f.endswith(".html"))
    counts = {"added": 0, "skipped-existing": 0, "no-mapping": 0, "no-title": 0, "skipped-by-name": 0}
    for fn in files:
        if fn in SKIP_FILES:
            counts["skipped-by-name"] += 1
            print(f"  · {fn:<28} skipped (kept custom description)")
            continue
        result = patch_file(os.path.join(DIR, fn))
        counts[result] += 1
        marker = {"added": "✓", "skipped-existing": "-", "no-mapping": "?", "no-title": "✗"}[result]
        print(f"  {marker} {fn:<28} {result}")

    print()
    for k, v in counts.items():
        if v: print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
