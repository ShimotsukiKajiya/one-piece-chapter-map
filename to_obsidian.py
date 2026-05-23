"""
Obsidian Vault Exporter — emit the entire Codex as a markdown vault
that opens directly in Obsidian. Every entity becomes a single .md
file with YAML frontmatter; every cross-reference becomes a [[wikilink]]
that Obsidian renders as a clickable graph node.

Layout produced (relative to D:/One Piece/obsidian_vault/):

  index.md                 — vault entry point with surface links
  Characters/<name>.md     — 1,545 character profiles
  DevilFruits/<fruit>.md   — 155 fruit profiles
  SBS/Vol XX/#NNNN.md      — 1,685 Q&As (one file per Q&A)
  Theories/#NNNN.md        — 94 numbered theory entries
  CoverStories/<arc>.md    — 21 cover-story arcs
  Chapters/Ch.NNNN.md      — 1,181 chapter stubs (just appearances)
  CanonFacts/<id>.md       — 4,800+ verified facts (claim ledger)
  README.md                — explainer + tier legend

The vault is regenerated end-to-end on every run (idempotent — not
intended for hand-editing inside Obsidian, since `to_obsidian.py`
overwrites). For collaborative editing see the GitHub repo.

Run:
  py to_obsidian.py             # full export
  py to_obsidian.py --dry-run   # report only
  py to_obsidian.py --skip-chapters   # skip the 1,181 chapter stubs
"""
import json, os, sys, re
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR    = os.path.dirname(__file__)
VAULT  = os.path.join(DIR, "obsidian_vault")
TODAY  = date.today().isoformat()


def _safe_filename(s):
    # Obsidian-safe: no path separators, no [], no #, no ?
    return re.sub(r'[<>:"/\\|?*\[\]#]', '_', s).strip()[:120]


def _link(name, sub_folder=None):
    """Build an Obsidian [[wikilink]]. Optional folder for disambiguation."""
    safe = _safe_filename(name)
    if sub_folder:
        return f"[[{sub_folder}/{safe}|{name}]]"
    return f"[[{safe}|{name}]]"


def _frontmatter(d):
    """YAML frontmatter from a dict. Strings only — keeps it simple."""
    lines = ["---"]
    for k, v in d.items():
        if v is None: continue
        if isinstance(v, list):
            if not v: continue
            lines.append(f"{k}:")
            for item in v: lines.append(f"  - {item}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            s = str(v).replace('"', '\\"')
            if "\n" in s:
                lines.append(f"{k}: |")
                for ln in s.split("\n"): lines.append(f"  {ln}")
            else:
                lines.append(f'{k}: "{s}"')
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── EXPORTERS ───────────────────────────────────────────────────
# ── ORGANISATION HELPERS — derive smart tags ──────────────────
# These power Obsidian's graph filters (Settings → Graph → Groups).
# Add a tag here, create a matching `tag:#X` group in Obsidian, and
# every node carrying that tag will color-clump in the graph view.

PIRATE_KEYWORDS = ("pirate", "yonko", "supernova", "shichibukai", "warlord")
MARINE_KEYWORDS = ("marine", "vice admiral", "admiral", "cipher pol", "cp9", "cp0")
REV_KEYWORDS    = ("revolutionary",)
GOV_KEYWORDS    = ("world government", "celestial dragon", "elders", "im sama")

def derive_character_tags(rec):
    """Build a richer tag list per character so Obsidian groups by faction.
    Tags drop the # prefix (Obsidian frontmatter convention)."""
    tags = ["character"]
    aff = (rec.get("affiliation") or "").lower()
    occ = (rec.get("occupation")  or "").lower()
    blob = aff + " " + occ

    if any(k in blob for k in PIRATE_KEYWORDS): tags.append("pirate")
    if any(k in blob for k in MARINE_KEYWORDS): tags.append("marine")
    if any(k in blob for k in REV_KEYWORDS):    tags.append("revolutionary")
    if any(k in blob for k in GOV_KEYWORDS):    tags.append("world_government")
    if "straw hat pirates" in aff:              tags.append("strawhat")
    if "whitebeard pirates" in aff:             tags.append("whitebeard_crew")
    if "blackbeard pirates" in aff:             tags.append("blackbeard_crew")
    if "red hair pirates" in aff or "red-hair pirates" in aff:
        tags.append("redhair_crew")
    if "big mom pirates" in aff or "charlotte family" in aff:
        tags.append("bigmom_crew")
    if "beasts pirates" in aff:                 tags.append("beasts_crew")
    if "kid pirates" in aff:                    tags.append("kid_crew")
    if "heart pirates" in aff:                  tags.append("heart_crew")
    if "roger pirates" in aff:                  tags.append("roger_crew")

    # Major/side classification by appearance count
    apps = rec.get("appearances") or 0
    if   apps >= 100: tags.append("main_character")
    elif apps >= 20:  tags.append("recurring_character")
    else:             tags.append("minor_character")

    # Devil fruit user
    if rec.get("devil_fruit_name"): tags.append("devil_fruit_user")
    return tags


def export_characters(pr, portraits, canon_facts, dry):
    """One file per character with full profile + cross-links."""
    out_dir = os.path.join(VAULT, "Characters")
    count = 0
    for name, rec in pr.items():
        if not rec.get("found"): continue

        fm = {
            "tags":    derive_character_tags(rec),
            "name":    name,
            "name_jp": rec.get("name_jp"),
            "epithet": rec.get("epithet"),
            "age":     rec.get("age"),
            "birthday":rec.get("birthday"),
            "height":  rec.get("height"),
            "blood":   rec.get("blood_type"),
            "bounty":  rec.get("bounty"),
            "bounty_value": rec.get("bounty_value"),
            "devil_fruit":  rec.get("devil_fruit_name"),
            "affiliation":  rec.get("affiliation"),
            "origin":       rec.get("origin"),
            "first_appearance": rec.get("first_appearance"),
            "appearances":  rec.get("appearances"),
            "verified_on":  TODAY,
        }
        body = []
        body.append(f"# {name}")
        if rec.get("name_jp"):
            body.append(f"_{rec['name_jp']}_  ·  {rec.get('name_romaji', '')}")
        if rec.get("epithet"):
            body.append(f"\n> _\"{rec['epithet']}\"_\n")

        # Portrait
        portrait_url = portraits.get(name, {}).get("thumb") if isinstance(portraits.get(name), dict) else portraits.get(name)
        if portrait_url:
            body.append(f"![Portrait]({portrait_url})\n")

        # Identity table
        body.append("## Identity")
        for label, key in [("Age", "age"), ("Birthday", "birthday"),
                            ("Height", "height"), ("Weight", "weight"),
                            ("Blood", "blood_type"), ("Origin", "origin"),
                            ("Residence", "residence")]:
            v = rec.get(key)
            if v: body.append(f"- **{label}:** {v}")

        # Combat
        body.append("\n## Role & Combat")
        for label, key in [("Occupation", "occupation"),
                            ("Affiliation", "affiliation"),
                            ("Bounty", "bounty"),
                            ("Haki", "haki"), ("Weapons", "weapons")]:
            v = rec.get(key)
            if v: body.append(f"- **{label}:** {v}")

        # Devil Fruit cross-link
        df = rec.get("devil_fruit_name")
        if df:
            body.append(f"- **Devil Fruit:** {_link(df, 'DevilFruits')}")
            if rec.get("devil_fruit_type"):
                body.append(f"- **DF Type:** {rec['devil_fruit_type']}")

        # Cast
        if any(rec.get(k) for k in ("voice_actor_jp", "voice_actor_en", "actor_live_action", "family")):
            body.append("\n## Cast")
            for label, key in [("Family", "family"),
                                ("VA (JP)", "voice_actor_jp"),
                                ("VA (EN)", "voice_actor_en"),
                                ("Live action", "actor_live_action")]:
                v = rec.get(key)
                if v: body.append(f"- **{label}:** {v}")

        # Verified canon facts
        facts = [f for f in canon_facts if f.get("subject") == name]
        if facts:
            body.append("\n## 🟢 Canon Facts")
            for f in facts:
                tier = f.get("tier", "?").upper()
                src = (f.get("sources") or [{}])[0]
                src_str = ""
                if src.get("type") == "sbs":
                    qa = str(src.get("qa_id", "")).zfill(4)
                    src_str = f" — {_link(f'#{qa}', 'SBS')}"
                elif src.get("type") == "manga":
                    ch = src.get("chapter") or src.get("chapter_range")
                    if ch: src_str = f" — {_link(f'Ch.{str(ch).zfill(4)}' if isinstance(ch, int) else f'Ch.{ch}', 'Chapters')}"
                body.append(f"- **{f['predicate']}** = {f['value']}  `{tier}`{src_str}")

        body.append(f"\n---\n_Exported {TODAY} from canon_facts.json + punk_records.json. See [[README]] for tiers._\n")

        path = os.path.join(out_dir, _safe_filename(name) + ".md")
        if not dry:
            write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def derive_fruit_tags(rec):
    tags = ["devil_fruit"]
    t = (rec.get("type_canonical") or rec.get("type") or "").lower()
    if "ancient" in t and "zoan" in t:   tags.extend(["zoan", "ancient_zoan"])
    elif "mythical" in t and "zoan" in t:tags.extend(["zoan", "mythical_zoan"])
    elif "logia" in t:                   tags.append("logia")
    elif "zoan" in t:                    tags.append("zoan")
    elif "paramecia" in t:               tags.append("paramecia")
    if rec.get("awakened") or rec.get("awakening"): tags.append("awakened_fruit")
    return tags


def export_devil_fruits(fruits, dry):
    out_dir = os.path.join(VAULT, "DevilFruits")
    count = 0
    for name, rec in fruits.items():
        if not rec.get("found"): continue
        fm = {
            "tags":    derive_fruit_tags(rec),
            "name":    name,
            "name_en": rec.get("name_en"),
            "name_jp": rec.get("name_jp"),
            "type":    rec.get("type_canonical") or rec.get("type"),
            "user":    rec.get("user_current"),
            "debut_chapter": rec.get("debut_chapter"),
        }
        body = []
        body.append(f"# {name}")
        if rec.get("name_jp"): body.append(f"_{rec['name_jp']}_")
        if rec.get("name_en"): body.append(f'**English:** {rec["name_en"]}')
        if rec.get("translation"): body.append(f'**Translation:** "{rec["translation"]}"')
        body.append(f"\n**Type:** `{rec.get('type_canonical') or rec.get('type', '?')}`\n")

        if rec.get("user_current"):
            users = [u.strip() for u in rec["user_current"].split("·") if u.strip()]
            body.append("## Users")
            for u in users: body.append(f"- {_link(u, 'Characters')}")
        if rec.get("user_previous"):
            body.append("\n## Previous users")
            for u in rec["user_previous"].split("·"):
                u = u.strip()
                if u: body.append(f"- {_link(u, 'Characters')}")

        if rec.get("first_appearance"):
            body.append(f"\n**Debut:** {rec['first_appearance']}")
        if rec.get("debut_chapter"):
            ch_pad = str(rec["debut_chapter"]).zfill(4)
            body.append(f"**Debut chapter:** {_link('Ch.' + ch_pad, 'Chapters')}")

        body.append(f"\n---\n_Exported {TODAY}._\n")
        path = os.path.join(out_dir, _safe_filename(name) + ".md")
        if not dry: write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def export_sbs(sbs, dry):
    """One file per Q&A, organised by volume folder. Uses [[#NNNN]]
    deep-link convention everywhere else in the vault."""
    base = os.path.join(VAULT, "SBS")
    count = 0
    for entry in sbs:
        id_num = entry.get("id_num")
        if id_num is None: continue
        vol = entry.get("volume") or 0
        num = str(id_num).zfill(4)
        fm = {
            "tags":     ["sbs"],
            "id_num":   id_num,
            "volume":   vol,
            "category": entry.get("category"),
            "name":     entry.get("name"),
        }
        body = []
        body.append(f"# SBS Vol {vol} #{num}")
        if entry.get("name"): body.append(f"_From: {entry['name']}_\n")
        body.append("## Reader")
        body.append(entry.get("question", "").strip())
        body.append("\n## Oda")
        body.append(entry.get("answer", "").strip())
        body.append(f"\n---\n_Vol {vol}, entry #{num}._\n")
        # Folder per volume
        path = os.path.join(base, f"Vol {str(vol).zfill(3)}", f"#{num}.md")
        if not dry: write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def export_theories(theories, dry):
    out_dir = os.path.join(VAULT, "Theories")
    count = 0
    for t in theories:
        num = t.get("num")
        if num is None: continue
        num_pad = str(num).zfill(4)
        fm = {
            "tags":   ["theory"],
            "num":    num,
            "status": t.get("status"),
            "title":  t.get("title"),
            "score":  t.get("score"),
        }
        body = []
        body.append(f"# Theory #{num_pad} — {t.get('title', '')}")
        body.append(f"\n**Status:** `{t.get('status', 'active')}`")
        if t.get("chapter"): body.append(f"**Relevant chapters:** {t['chapter']}")
        body.append("")
        body.append(t.get("description", ""))
        a = t.get("analysis")
        if a:
            body.append("\n## Canon Verdict")
            if a.get("reasoning"):    body.append(f"\n{a['reasoning']}")
            if a.get("compelled_by"):
                body.append("\n**Compelled by canon:**")
                for c in a["compelled_by"]: body.append(f"- {c}")
            if a.get("sbs_citations"):
                body.append("\n**Oda's words on this:**")
                for s in a["sbs_citations"]: body.append(f"- {s}")
        if t.get("source"): body.append(f"\n_Source: {t['source']}_")
        body.append(f"\n---\n_Theory #{num_pad}._\n")
        path = os.path.join(out_dir, f"#{num_pad}.md")
        if not dry: write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def export_cover_stories(cs_list, dry):
    out_dir = os.path.join(VAULT, "CoverStories")
    count = 0
    for c in cs_list:
        fm = {
            "tags":     ["cover_story"],
            "name":     c.get("name"),
            "chapters": c.get("chapters", []),
            "range":    c.get("chapter_range"),
        }
        body = []
        body.append(f"# {c.get('name', '?')}")
        body.append(f"\n**Chapter range:** {c.get('chapter_range', '?')}")
        if c.get("summary"): body.append(f"\n{c['summary']}")
        if c.get("chapters"):
            body.append("\n## Chapters")
            for ch in c["chapters"]:
                body.append(f"- {_link(f'Ch.{str(ch).zfill(4)}', 'Chapters')}")
        body.append(f"\n---\n_Exported {TODAY}._\n")
        path = os.path.join(out_dir, _safe_filename(c.get("name", "untitled")) + ".md")
        if not dry: write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def export_chapter_stubs(appearances_by_ch, dry):
    """One short stub per chapter listing the characters that appeared."""
    out_dir = os.path.join(VAULT, "Chapters")
    count = 0
    for ch, items in appearances_by_ch.items():
        ch_pad = str(ch).zfill(4)
        fm = {"tags": ["chapter"], "chapter": ch}
        body = [f"# Chapter {ch}"]
        by_type = {}
        for name, t in items: by_type.setdefault(t, []).append(name)
        for t in ("full", "flashback", "silhouette", "cover"):
            if t in by_type:
                body.append(f"\n## {t.title()}")
                for name in sorted(by_type[t]):
                    body.append(f"- {_link(name, 'Characters')}")
        body.append(f"\n---\n_Chapter {ch}, {len(items)} appearances._\n")
        path = os.path.join(out_dir, f"Ch.{ch_pad}.md")
        if not dry: write(path, _frontmatter(fm) + "\n".join(body))
        count += 1
    return count


def export_mocs(pr, fruits, sbs, theories, arcs, dry):
    """Maps of Content — Obsidian's standard organisation pattern.
    Each MOC is a hub note that links to every member of its category.
    These force tight clusters in the graph view, instead of isolated
    orphan rings."""
    moc_dir = os.path.join(VAULT, "MOCs")
    if not dry: os.makedirs(moc_dir, exist_ok=True)
    written = 0

    # Per-tag character indexes
    by_tag = {}
    for name, rec in pr.items():
        if not rec.get("found"): continue
        for tag in derive_character_tags(rec):
            by_tag.setdefault(tag, []).append(name)

    # MOC: All Characters (alphabetical)
    body = ["# 👤 All Characters\n",
            "_Master index of every character in the Codex._\n"]
    for n in sorted(by_tag.get("character", [])):
        body.append(f"- {_link(n, 'Characters')}")
    if not dry: write(os.path.join(moc_dir, "Characters MOC.md"),
                       _frontmatter({"tags": ["moc"], "topic": "characters"}) + "\n".join(body))
    written += 1

    # MOC: Main characters (top by appearance count)
    if by_tag.get("main_character"):
        body = ["# ⭐ Main Characters\n",
                "_Characters with 100+ chapter appearances._\n"]
        for n in sorted(by_tag["main_character"]):
            body.append(f"- {_link(n, 'Characters')}")
        if not dry: write(os.path.join(moc_dir, "Main Characters MOC.md"),
                           _frontmatter({"tags": ["moc"], "topic": "main_characters"}) + "\n".join(body))
        written += 1

    # MOC: per faction
    factions = [
        ("pirate",         "🏴‍☠️ Pirates"),
        ("marine",         "⚓ Marines"),
        ("revolutionary",  "🔥 Revolutionaries"),
        ("world_government","🏛 World Government"),
        ("strawhat",       "🌾 Straw Hat Pirates"),
        ("whitebeard_crew","💀 Whitebeard Pirates"),
        ("blackbeard_crew","🌑 Blackbeard Pirates"),
        ("redhair_crew",   "🟥 Red-Hair Pirates"),
        ("bigmom_crew",    "🍰 Big Mom Pirates"),
        ("beasts_crew",    "🐉 Beasts Pirates"),
        ("kid_crew",       "⚡ Kid Pirates"),
        ("heart_crew",     "❤️ Heart Pirates"),
        ("roger_crew",     "👑 Roger Pirates"),
    ]
    for tag, title in factions:
        members = by_tag.get(tag, [])
        if not members: continue
        body = [f"# {title}\n",
                f"_{len(members)} member{'s' if len(members) != 1 else ''}._\n"]
        for n in sorted(members):
            body.append(f"- {_link(n, 'Characters')}")
        if not dry: write(os.path.join(moc_dir, f"{title.split(' ', 1)[1]} MOC.md"),
                           _frontmatter({"tags": ["moc", tag], "topic": tag}) + "\n".join(body))
        written += 1

    # MOC: Devil Fruits by type
    by_type = {}
    for name, rec in fruits.items():
        if not isinstance(rec, dict) or not rec.get("found"): continue
        t = rec.get("type_canonical") or "Unknown"
        by_type.setdefault(t, []).append(name)
    for t, names in by_type.items():
        body = [f"# 🍎 {t} Fruits\n",
                f"_{len(names)} fruit{'s' if len(names) != 1 else ''}._\n"]
        for n in sorted(names):
            body.append(f"- {_link(n, 'DevilFruits')}")
        if not dry: write(os.path.join(moc_dir, f"DevilFruits — {t} MOC.md"),
                           _frontmatter({"tags": ["moc", "devil_fruit"], "topic": t}) + "\n".join(body))
        written += 1

    # MOC: per saga (links to every chapter in the saga AND arcs)
    by_saga = {}
    for a in arcs: by_saga.setdefault(a["saga"], []).append(a)
    for saga, sa_arcs in by_saga.items():
        start = min(a["start"] for a in sa_arcs)
        end = max(a["end"] for a in sa_arcs)
        end_str = "ongoing" if end >= 9999 else end
        body = [f"# 📖 {saga} Saga\n",
                f"_Chapters {start}–{end_str}._\n",
                "## Arcs\n"]
        for a in sa_arcs:
            end_a = "ongoing" if a["end"] >= 9999 else a["end"]
            body.append(f"- **{a['arc']}** — Ch. {a['start']}–{end_a}")
        body.append("\n## Chapters\n")
        for ch in range(start, min(end, 1181) + 1):
            body.append(f"- {_link(f'Ch.{str(ch).zfill(4)}', 'Chapters')}")
        if not dry: write(os.path.join(moc_dir, f"Saga — {saga} MOC.md"),
                           _frontmatter({"tags": ["moc", "saga"], "saga": saga,
                                         "chapters_range": f"{start}-{end_str}"}) + "\n".join(body))
        written += 1

    return written


def write_examples(dry):
    """Concrete-workflows note. Three example tasks with click-throughs
    so the user sees the vault's real value, not just its structure."""
    body = """# What Can I Actually Do Here?

> Three concrete workflows the vault is good for. Try one — it's the
> fastest way to see why this is different from just browsing the website.

---

## 🔍 Workflow 1 — "Who is X actually connected to?"

**Question:** Imu was revealed in Chapter 906. Who's actually connected to that character in canon, beyond the obvious?

**Try this now:**

1. Click [[Characters/Imu]]
2. Look at the **right-side panel** → scroll to **"Backlinks"**
3. Every other note that mentions Imu shows up there: SBS theories, the Five Elders, World Government MOC, etc.
4. Now press **`Ctrl + G`** while still on Imu's page → opens the graph zoomed to Imu's neighbourhood
5. Right-click anywhere → **"Open local graph"** → adjust the depth slider

You just discovered every canonical Imu reference in seconds. The website has cross-refs but you have to navigate page-by-page; here it's a single visual.

---

## 🗺 Workflow 2 — "Show me everything in one arc"

**Question:** What happened in the Wano arc, and which characters debuted there?

**Try this now:**

1. Click [[MOCs/Saga — Yonko MOC]]
2. The MOC links to every chapter in the Yonko saga (Zou through Wano) AND every arc subdivision
3. Scroll to the chapters list — click any chapter to see who appeared
4. Or press **`Ctrl + Shift + F`** and search `tag:#chapter Wano` for a different cut

The MOC is the "saga as a single hub note" — pulls the chapter orphans into the dense graph cluster.

---

## 🏴‍☠️ Workflow 3 — "Find characters I forgot existed"

**Question:** I want to dig into the Big Mom Pirates. Who are all 87 of them?

**Try this now:**

1. Click [[MOCs/Big Mom Pirates MOC]]
2. Scrollable list of every member — alphabetical
3. Click any name → full character profile with their bounty, devil fruit, status, family
4. Hit **`Ctrl + Shift + F`** and search `tag:#bigmom_crew tag:#devil_fruit_user` to find only the fruit users

Same trick works for `tag:#strawhat`, `tag:#beasts_crew`, `tag:#marine`, `tag:#paramecia`, etc.

---

## ⚡ Power Move — install **Dataview**

If you want to turn the vault into a real database, install one plugin:

1. Settings (gear icon, bottom-left) → **Community plugins** → **Browse**
2. Search "**Dataview**" → Install → Enable
3. Reload Obsidian

Then create a new note with this content:

````
```dataview
TABLE bounty_value, devil_fruit, affiliation
FROM "Characters"
WHERE bounty_value > 1000000000
SORT bounty_value DESC
LIMIT 20
```
````

You now have a live-updating table of the top 20 billion-berry bounties with their devil fruits. Try variations:

````
```dataview
LIST
FROM "Characters"
WHERE contains(tags, "logia")
```
````

→ every Logia user. Or:

````
```dataview
TABLE birthday, blood
FROM "Characters"
WHERE contains(tags, "strawhat")
```
````

→ every Strawhat's birthday + blood type in one table.

The full query language is documented at [blacksmithgu.github.io/obsidian-dataview](https://blacksmithgu.github.io/obsidian-dataview/).

---

## 🚫 What this vault is NOT for

- **Editing or correcting** — every regen of `to_obsidian.py` overwrites everything. File corrections via the
  [GitHub Issues](https://github.com/ShimotsukiKajiya/one-piece-chapter-map/issues) instead.
- **Casual single lookups** — for "what's Sanji's birthday?", the website is faster.
- **Building theories with citations** — that's what the Workbench on the live site is for.
- **Real-time canon updates** — the vault is regenerated on demand. The live site updates weekly via cron.

---

## 📂 Use the vault AS a library

If you want to write your own notes about One Piece, **make a new vault elsewhere** (e.g. `D:\My OnePiece Notes\`) and reference notes from this vault:

```
This theory hinges on [[../obsidian_vault/Characters/Imu|Imu]]'s reveal in
[[../obsidian_vault/Chapters/Ch.0906|Chapter 906]].
```

Your private theory drafts now cite the canonical Codex without touching it. When the Codex regenerates, your notes stay; your citations stay valid.

---

_Try at least one of the three workflows above. That's where the vault earns its keep._
"""
    if not dry:
        write(os.path.join(VAULT, "What Can I Do Here.md"), body)


def write_obsidian_config(dry):
    """Pre-configure the vault so it's usable on first open:
    - Dark theme + reading-friendly font sizing
    - Graph view groups pre-coloured by tag (Strawhats=gold, Marines=blue, etc.)
    - Welcome.md set as default-open
    - Sensible plugin defaults"""
    cfg_dir = os.path.join(VAULT, ".obsidian")
    if not dry: os.makedirs(cfg_dir, exist_ok=True)

    # Dark theme
    appearance = {
        "theme": "obsidian",
        "translucency": False,
        "interfaceFontFamily": "",
        "textFontFamily": "",
        "monospaceFontFamily": "",
        "baseFontSize": 16,
    }

    # Graph view: pre-coloured groups so the graph self-organises
    # by faction the moment you open it. Each query uses Obsidian's
    # `tag:#X` syntax. Order matters — earlier rules win for nodes
    # that match multiple groups (Strawhats are also pirates → gold wins).
    graph = {
        "collapse-filter": False,
        "search": "",
        "showTags": False,
        "showAttachments": False,
        "hideUnresolved": False,
        "showOrphans": False,
        "collapse-color-groups": False,
        "colorGroups": [
            # Strawhats first — they get the gold treatment
            {"query": "tag:#strawhat",          "color": {"a": 1, "rgb": 16097354}},  # gold
            {"query": "tag:#main_character",    "color": {"a": 1, "rgb": 16170590}},  # gold-bright
            # Crew clusters
            {"query": "tag:#whitebeard_crew",   "color": {"a": 1, "rgb": 13434880}},  # crimson
            {"query": "tag:#blackbeard_crew",   "color": {"a": 1, "rgb": 5266265}},   # dark
            {"query": "tag:#redhair_crew",      "color": {"a": 1, "rgb": 16725555}},  # bright red
            {"query": "tag:#bigmom_crew",       "color": {"a": 1, "rgb": 16737996}},  # pink
            {"query": "tag:#beasts_crew",       "color": {"a": 1, "rgb": 16744192}},  # orange
            {"query": "tag:#kid_crew",          "color": {"a": 1, "rgb": 16776960}},  # yellow
            {"query": "tag:#heart_crew",        "color": {"a": 1, "rgb": 6986239}},   # cyan
            {"query": "tag:#roger_crew",        "color": {"a": 1, "rgb": 16777215}},  # white
            # Factions
            {"query": "tag:#marine",            "color": {"a": 1, "rgb": 4359924}},   # blue
            {"query": "tag:#revolutionary",     "color": {"a": 1, "rgb": 14564178}},  # orange-red
            {"query": "tag:#world_government",  "color": {"a": 1, "rgb": 14893364}},  # khaki
            {"query": "tag:#pirate",            "color": {"a": 1, "rgb": 13391360}},  # darker red
            # Devil fruits by type
            {"query": "tag:#paramecia",         "color": {"a": 1, "rgb": 13134236}},  # rose
            {"query": "tag:#logia",             "color": {"a": 1, "rgb": 15228476}},  # lava
            {"query": "tag:#mythical_zoan",     "color": {"a": 1, "rgb": 11566801}},  # violet
            {"query": "tag:#ancient_zoan",      "color": {"a": 1, "rgb": 13934408}},  # gold-tan
            {"query": "tag:#zoan",              "color": {"a": 1, "rgb": 8156255}},   # green
            # Other entities
            {"query": "tag:#sbs",               "color": {"a": 1, "rgb": 8950459}},   # ink-blue
            {"query": "tag:#theory",            "color": {"a": 1, "rgb": 16737843}},  # orange
            {"query": "tag:#chapter",           "color": {"a": 1, "rgb": 4474194}},   # muted dark
            {"query": "tag:#moc",               "color": {"a": 1, "rgb": 16776960}},  # yellow (hubs)
        ],
        "collapse-display": False,
        "showArrow": False,
        "textFadeMultiplier": 0.5,
        "nodeSizeMultiplier": 1.2,
        "lineSizeMultiplier": 0.8,
        "collapse-forces": False,
        "centerStrength": 0.5,
        "repelStrength": 12,
        "linkStrength": 1,
        "linkDistance": 250,
        "scale": 0.6,
        "close": True,
    }

    # Workspace: open Welcome.md by default
    workspace = {
        "main": {
            "id": "root",
            "type": "split",
            "children": [{
                "id": "welcome-leaf",
                "type": "tabs",
                "children": [{
                    "id": "welcome-tab",
                    "type": "leaf",
                    "state": {
                        "type": "markdown",
                        "state": {
                            "file": "Welcome.md",
                            "mode": "preview",
                            "source": False,
                        },
                    },
                }],
            }],
            "direction": "vertical",
        },
        "left": {
            "id": "left-root", "type": "split", "direction": "horizontal",
            "children": [{
                "id": "left-tabs", "type": "tabs",
                "children": [{
                    "id": "file-explorer", "type": "leaf",
                    "state": {"type": "file-explorer", "state": {"sortOrder": "alphabetical"}},
                }, {
                    "id": "search-leaf", "type": "leaf",
                    "state": {"type": "search", "state": {"query": "", "matchingCase": False, "explainSearch": False, "collapseAll": False, "extraContext": False, "sortOrder": "alphabetical"}},
                }],
                "currentTab": 0,
            }],
            "width": 300,
        },
        "right": {
            "id": "right-root", "type": "split", "direction": "horizontal",
            "children": [{
                "id": "right-tabs", "type": "tabs",
                "children": [{
                    "id": "graph-leaf", "type": "leaf",
                    "state": {"type": "graph", "state": {}},
                }, {
                    "id": "outline-leaf", "type": "leaf",
                    "state": {"type": "outline", "state": {}},
                }],
                "currentTab": 0,
            }],
            "width": 320,
        },
        "active": "welcome-tab",
        "lastOpenFiles": ["Welcome.md", "index.md", "README.md"],
    }

    # Core plugins (default-on for the experience)
    core = [
        "file-explorer", "global-search", "switcher", "graph",
        "backlink", "outgoing-link", "tag-pane", "page-preview",
        "outline", "word-count", "file-recovery", "command-palette",
    ]

    if not dry:
        with open(os.path.join(cfg_dir, "appearance.json"), "w", encoding="utf-8") as f:
            json.dump(appearance, f, indent=2)
        with open(os.path.join(cfg_dir, "graph.json"), "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2)
        with open(os.path.join(cfg_dir, "workspace.json"), "w", encoding="utf-8") as f:
            json.dump(workspace, f, indent=2)
        with open(os.path.join(cfg_dir, "core-plugins.json"), "w", encoding="utf-8") as f:
            json.dump(core, f, indent=2)


def write_welcome(stats, dry):
    body = f"""# Welcome to The Shimotsuki Codex

> _Forging clarity from chaos._ This is your local copy of the Codex —
> {sum(stats.values()):,} markdown files exported from the live data.

---

## ⚡ 60-second tour

You're reading **Welcome.md**, which Obsidian opens by default.

Three things to try right now:

### 1. Open the graph view
Press **`Ctrl + G`** (or `Cmd + G` on Mac).
The graph is **already pre-coloured** for you:
- 🟡 Gold = Strawhats and main characters
- 🔴 Red = Pirates  ·  🔵 Blue = Marines  ·  🟧 Orange = Revolutionaries
- 🍎 Each Devil Fruit type has its own colour
- Hubs (MOC notes) glow yellow

Drag the graph around. Click any node to jump to it.

### 2. Use the file explorer (left panel)
- **`Characters/`** — every named character ({stats.get('characters', 0):,} of them)
- **`DevilFruits/`** — {stats.get('fruits', 0):,} canonical fruits
- **`SBS/`** — {stats.get('sbs', 0):,} of Oda's Q&As, organised by volume
- **`Theories/`** — {stats.get('theories', 0)} curated theories
- **`Chapters/`** — {stats.get('chapters', 0):,} chapter stubs
- **`MOCs/`** — index notes that group everything (start here if lost)

### 3. Search across everything
Press **`Ctrl + Shift + F`** for vault-wide search.
Try: `bounty: 3000000000` to find Luffy, or `tag:#strawhat` to list the crew.

---

## 👉 Start here if you're not sure why this is useful

[[What Can I Do Here|🚀 What Can I Actually Do Here?]] — three concrete
workflows you can try in 60 seconds each. Open this first.

---

## 🗺 Recommended starting points

If you're not sure where to begin, click any of these:

- [[MOCs/Main Characters MOC|⭐ Main Characters]] — the {stats.get('main_chars', '~50')} most-mentioned characters
- [[MOCs/Straw Hat Pirates MOC|🌾 Straw Hat Pirates]] — the crew
- [[MOCs/Saga — Yonko MOC|🐉 Yonko Saga]] — Wano + Whole Cake + Zou + Reverie
- [[Characters/Monkey D. Luffy|👑 Monkey D. Luffy]] — start here for the protagonist
- [[Characters/Imu|👁 Imu]] — start here for endgame intrigue
- [[DevilFruits/Hito Hito no Mi, Model_ Nika|🌞 Nika fruit]] — the lore-shaking Wano reveal
- [[index|📑 Vault index]] — directory of everything
- [[README|📖 Tier legend & how the Codex works]]

---

## 🟢 Tier legend (what the badges mean)

Every fact in the Codex carries a trust tier:

| Tier | Meaning |
|---|---|
| 🟢 **CANON** | Oda direct — manga panel, SBS verbatim |
| 🔵 **LIKELY** | Multiple sources agree, no contradiction |
| 🟣 **SPECULATION** | Wiki only, awaiting verification |
| 🟠 **RUMOUR** | Reddit / fan / unsupported |
| 🔴 **DISPROVEN** | Contradicted by a higher source |

This is enforced by the live Codex's `verify.py`. The vault inherits
the verdicts.

---

## ⚠ Important — don't hand-edit notes here

The vault is **regenerated end-to-end** every time `to_obsidian.py` runs.
Any edits you make inside Obsidian will be overwritten next refresh.

For corrections or additions, use the
[GitHub Issues](https://github.com/ShimotsukiKajiya/one-piece-chapter-map/issues)
on the live Codex.

To regenerate after a data refresh:
```
py to_obsidian.py
```

---

_Vault built {TODAY}. {sum(stats.values()):,} notes total._
"""
    if not dry:
        write(os.path.join(VAULT, "Welcome.md"), body)


def write_readme(stats, dry):
    body = f"""# The Shimotsuki Codex — Obsidian Vault

> Generated {TODAY} from the Codex's canonical data files. Browse with
> Obsidian to use the graph view, backlinks, and search across the
> entire One Piece canon as we have it.

## What's in this vault

| Folder | Count | Source |
|---|---|---|
| `Characters/` | {stats.get('characters', 0):,} | `punk_records.json` (wiki Char Box) |
| `DevilFruits/` | {stats.get('fruits', 0):,} | `devil_fruits.json` (wiki Devil Fruit Box) |
| `SBS/Vol N/` | {stats.get('sbs', 0):,} | `sbs_archive.json` (Oda's Q&As) |
| `Theories/` | {stats.get('theories', 0):,} | `theories_import.json` (curated from r/OnePiece) |
| `CoverStories/` | {stats.get('cover_stories', 0):,} | `cover_stories.json` |
| `Chapters/` | {stats.get('chapters', 0):,} | `appearances.csv` (one stub per chapter) |

## Tier legend

Every claim in the Codex carries a tier badge:

- 🟢 **CANON** — Oda direct (manga panel, SBS verbatim)
- 🔵 **LIKELY** — multiple sources agree, no contradiction
- 🟣 **SPECULATION** — wiki only, awaiting verification
- 🟠 **RUMOUR** — Reddit / fan / unsupported
- 🔴 **DISPROVEN** — contradicted by higher source

## How to use

1. Open this folder as an Obsidian vault (File → Open vault → this folder)
2. Hit `Ctrl/Cmd + G` to open the graph view — every cross-reference is a link
3. Click any character → see all theories, SBS Q&As, chapter appearances
4. Search across the vault with `Ctrl/Cmd + Shift + F`

## Important

This vault is **regenerated end-to-end** on every `to_obsidian.py` run.
Don't hand-edit notes inside Obsidian — your changes will be overwritten.
For corrections, file an issue at the
[GitHub repo](https://github.com/ShimotsukiKajiya/one-piece-chapter-map).
"""
    if not dry: write(os.path.join(VAULT, "README.md"), body)


def write_index(stats, dry):
    body = f"""# Codex Index

The Shimotsuki Codex — Obsidian export, generated {TODAY}.

## Quick links

- 👤 [[Characters]] — {stats.get('characters', 0):,} characters
- 🍎 [[DevilFruits]] — {stats.get('fruits', 0):,} fruits
- 📜 [[SBS]] — {stats.get('sbs', 0):,} Q&As
- 🔥 [[Theories]] — {stats.get('theories', 0):,} curated
- 🏴‍☠️ [[CoverStories]] — {stats.get('cover_stories', 0):,} mini-arcs
- 📖 [[Chapters]] — {stats.get('chapters', 0):,} chapter stubs

## Pinned

- [[Monkey D. Luffy]]
- [[Roronoa Zoro]]
- [[Imu]]

See [[README]] for the tier legend and refresh policy.
"""
    if not dry: write(os.path.join(VAULT, "index.md"), body)


# ── MAIN ────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry  = "--dry-run" in args
    skip_chapters = "--skip-chapters" in args

    print("=" * 60)
    print(f"  Obsidian Vault Exporter")
    print(f"  Output: {VAULT}")
    if dry: print("  DRY RUN — no files written")
    print("=" * 60); print()

    arcs    = json.load(open(os.path.join(DIR, "arcs.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "arcs.json")) else []
    pr      = json.load(open(os.path.join(DIR, "punk_records.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "punk_records.json")) else {}
    facts   = json.load(open(os.path.join(DIR, "canon_facts.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "canon_facts.json")) else []
    sbs     = json.load(open(os.path.join(DIR, "sbs_archive.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "sbs_archive.json")) else []
    theories= json.load(open(os.path.join(DIR, "theories_import.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "theories_import.json")) else []
    cs      = json.load(open(os.path.join(DIR, "cover_stories.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "cover_stories.json")) else []
    fruits  = json.load(open(os.path.join(DIR, "devil_fruits.json"), encoding="utf-8")) if os.path.exists(os.path.join(DIR, "devil_fruits.json")) else {}
    portraits_path = os.path.join(DIR, "portraits.json")
    portraits = json.load(open(portraits_path, encoding="utf-8")) if os.path.exists(portraits_path) else {}

    # Build appearances index from CSV
    appearances_by_ch = {}
    csv_path = os.path.join(DIR, "appearances.csv")
    if os.path.exists(csv_path) and not skip_chapters:
        import csv as _csv
        with open(csv_path, encoding="utf-8") as f:
            for r in _csv.DictReader(f):
                try: ch = int(r["chapter"])
                except (ValueError, KeyError): continue
                appearances_by_ch.setdefault(ch, []).append(
                    (r.get("name", "").strip(), r.get("type", "full").strip())
                )

    if not dry: os.makedirs(VAULT, exist_ok=True)

    stats = {}
    print(f"  Characters…");    stats["characters"]    = export_characters(pr, portraits, facts, dry); print(f"    ✓ {stats['characters']:,}")
    print(f"  Devil Fruits…");  stats["fruits"]        = export_devil_fruits(fruits, dry);              print(f"    ✓ {stats['fruits']:,}")
    print(f"  SBS Q&As…");      stats["sbs"]           = export_sbs(sbs, dry);                          print(f"    ✓ {stats['sbs']:,}")
    print(f"  Theories…");      stats["theories"]      = export_theories(theories, dry);                print(f"    ✓ {stats['theories']:,}")
    print(f"  Cover stories…"); stats["cover_stories"] = export_cover_stories(cs, dry);                 print(f"    ✓ {stats['cover_stories']:,}")
    if not skip_chapters:
        print(f"  Chapters…");  stats["chapters"]      = export_chapter_stubs(appearances_by_ch, dry);  print(f"    ✓ {stats['chapters']:,}")
    print(f"  MOCs…");          stats["mocs"]          = export_mocs(pr, fruits, sbs, theories, arcs, dry); print(f"    ✓ {stats['mocs']:,}")
    print(f"  Welcome + config…")
    # Count main_characters for the welcome blurb
    stats["main_chars"] = sum(1 for r in pr.values()
                               if r.get("found") and (r.get("appearances") or 0) >= 100)
    write_obsidian_config(dry)
    write_welcome(stats, dry)
    write_examples(dry)
    write_readme(stats, dry)
    write_index(stats, dry)
    print(f"    ✓ Welcome.md + What Can I Do Here.md + .obsidian/ pre-configured")

    total = sum(stats.values())
    print()
    print("=" * 60)
    print(f"  ✓ Vault exported: {total:,} markdown files in {VAULT}")
    if not dry:
        print(f"  Open in Obsidian: File → Open vault → {VAULT}")
    print("=" * 60)


if __name__ == "__main__":
    main()
