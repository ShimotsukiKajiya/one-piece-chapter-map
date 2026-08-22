"""
Unified baker — embeds all data files directly into their HTML pages so
every page works opened locally (file://), on GitHub Pages, or anywhere,
with zero setup. No local server, no fetch issues.

Bakes:
  appearances.csv   →  atlas.html   (Chapter Map)
  appearances.csv   →  quiz.html    (Character Quiz)
  sbs_archive.json  →  sbs.html     (SBS Archive)

Run:
  py bake.py            # bake everything
  py bake.py sbs        # bake only SBS
  py bake.py csv        # bake only appearances data into the two pages
"""

import json
import os
import sys
from collections import Counter

# Force UTF-8 output on Windows so check marks / arrows don't crash CMD
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR = os.path.dirname(__file__)


# ── BAKE HELPERS ─────────────────────────────────────────────────
def bake_block(html_path: str, marker_id: str, payload: str) -> tuple[bool, int]:
    """Find <script id="MARKER_ID" ...>...</script> in html_path and replace its
    contents with payload. Returns (success, new_file_size_kb)."""
    if not os.path.exists(html_path):
        print(f"  ✗ {os.path.basename(html_path)} not found")
        return False, 0

    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    open_tag_marker = f'id="{marker_id}"'
    open_tag_pos    = html.find(open_tag_marker)
    if open_tag_pos == -1:
        print(f"  ✗ {os.path.basename(html_path)}: marker id=\"{marker_id}\" not found")
        return False, 0

    # Find the > that closes the opening <script> tag
    open_tag_end = html.find(">", open_tag_pos)
    if open_tag_end == -1:
        print(f"  ✗ {os.path.basename(html_path)}: malformed script tag")
        return False, 0
    open_tag_end += 1  # advance past the >

    # Find the matching </script>
    close_tag_pos = html.find("</script>", open_tag_end)
    if close_tag_pos == -1:
        print(f"  ✗ {os.path.basename(html_path)}: </script> not found after marker")
        return False, 0

    new_html = html[:open_tag_end] + "\n" + payload + "\n" + html[close_tag_pos:]

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)

    return True, len(new_html) // 1024


# ── BAKERS ───────────────────────────────────────────────────────
def bake_sbs():
    archive_path = os.path.join(DIR, "sbs_archive.json")
    covers_path  = os.path.join(DIR, "volume_covers.json")
    html_path    = os.path.join(DIR, "sbs.html")

    if not os.path.exists(archive_path):
        print("  ✗ sbs_archive.json not found — run sbs_scraper.py first")
        return

    with open(archive_path, encoding="utf-8") as f:
        archive = json.load(f)

    payload = json.dumps(archive, ensure_ascii=False, separators=(',', ':'))
    ok, size = bake_block(html_path, "sbs-data", payload)
    if ok:
        cat_count = sum(1 for q in archive if q.get("category"))
        print(f"  ✓ sbs.html      ← {len(archive):>5,} Q&As     ({size} KB)  [categorized: {cat_count}]")

    # Bake volume covers into both sbs.html (vol headers) and covers.html (per-arc thumbs)
    if os.path.exists(covers_path):
        with open(covers_path, encoding="utf-8") as f:
            covers = json.load(f)
        cov_payload = json.dumps(covers, ensure_ascii=False, separators=(',', ':'))
        for page in ("sbs.html", "covers.html"):
            page_path = os.path.join(DIR, page)
            if not os.path.exists(page_path): continue
            ok2, _ = bake_block(page_path, "covers-data", cov_payload)
            if ok2:
                print(f"  ✓ {page:<13} ← {len(covers):>5,} covers")


def bake_csv():
    csv_path = os.path.join(DIR, "appearances.csv")
    if not os.path.exists(csv_path):
        print("  ✗ appearances.csv not found — run scraper.py first")
        return

    with open(csv_path, encoding="utf-8") as f:
        csv_text = f.read().strip()

    rows = csv_text.count("\n")  # rough row count

    for page in ("atlas.html", "quiz.html"):
        html_path = os.path.join(DIR, page)
        ok, size = bake_block(html_path, "appearances-data", csv_text)
        if ok:
            print(f"  ✓ {page:<13} ← {rows:>5,} rows     ({size} KB)")

    # Cover stories → bake into both atlas.html and covers.html
    cs_path = os.path.join(DIR, "cover_stories.json")
    if os.path.exists(cs_path):
        with open(cs_path, encoding="utf-8") as f:
            cs_text = f.read().strip()
        cs_data = json.loads(cs_text)
        for page in ("atlas.html", "covers.html"):
            html_path = os.path.join(DIR, page)
            if not os.path.exists(html_path): continue
            ok, _ = bake_block(html_path, "cover-stories-data", cs_text)
            if ok:
                print(f"  ✓ {page:<13} ← {len(cs_data):>5,} cover stories")


# ── PUNK RECORDS (character profiles) ──────────────────────────
PUNK_FIELDS_PUBLIC = [
    "name", "name_jp", "name_romaji", "epithet", "found", "appearances",
    "age", "birthday", "height", "weight", "blood_type", "status",
    "occupation", "affiliation", "first_appearance",
    "origin", "residence",
    "devil_fruit_name", "devil_fruit_type", "haki", "weapons",
    "family", "bounty", "bounty_value",
    "voice_actor_jp", "voice_actor_en", "actor_live_action",
    # L18+L20 v2: era-aware portrait gate. Each entry is
    # {from_ch:int, url:str, label?:str}; CodexSpoiler.pickPortrait picks
    # the latest entry whose from_ch <= the user's effective cutoff.
    "era_portraits",
]


def _compact_punk_records(raw):
    """Drop debug fields + stub entries we don't want to surface."""
    out = []
    for name, rec in raw.items():
        # Keep stubs only if they have appearances — they show as "no record" page
        if not rec.get("found") and not rec.get("appearances"):
            continue
        slim = {k: rec[k] for k in PUNK_FIELDS_PUBLIC if rec.get(k)}
        slim["name"] = name
        out.append(slim)
    return out


def _build_appearances_index(csv_path, names):
    """Per-character list of {chapter, type} from appearances.csv.
    Limited to characters in `names` to keep payload size sane."""
    import csv as _csv
    name_set = set(names)
    out = {}
    if not os.path.exists(csv_path): return out
    with open(csv_path, encoding="utf-8") as f:
        reader = _csv.DictReader(f)
        for row in reader:
            n = row.get("name", "").strip()
            if n not in name_set: continue
            try: ch = int(row["chapter"])
            except (ValueError, KeyError): continue
            out.setdefault(n, []).append({"chapter": ch, "type": row.get("type", "full")})
    # Sort each character's list by chapter for nicer display
    for n in out: out[n].sort(key=lambda r: r["chapter"])
    return out


import re as _re

# Curated short-name → canonical aliases. Most One Piece characters
# go by 1–2 nicknames. We match against ANY alias with word boundaries
# (so "Ace" won't hit "place" / "pace" / "Acerola"). Add freely.
NAME_ALIASES = {
    "Monkey D. Luffy":     ["Luffy"],
    "Roronoa Zoro":        ["Zoro"],
    "Vinsmoke Sanji":      ["Sanji"],
    "Tony Tony Chopper":   ["Chopper"],
    "Nico Robin":          ["Robin"],
    "Brook":               ["Soul King"],
    "Jinbe":               ["Jimbei"],
    "Portgas D. Ace":      ["Ace", "Fire Fist Ace"],
    "Sabo":                [],   # already 4 chars, word-boundary safe
    "Edward Newgate":      ["Whitebeard", "Pops"],
    "Marshall D. Teach":   ["Blackbeard", "Teach"],
    "Gol D. Roger":        ["Roger", "Gold Roger"],
    "Monkey D. Dragon":    ["Dragon"],
    "Monkey D. Garp":      ["Garp"],
    "Trafalgar D. Water Law": ["Trafalgar Law", "Law"],
    "Eustass Kid":         ["Kid", "Eustass"],
    "Bartholomew Kuma":    ["Kuma"],
    "Donquixote Doflamingo": ["Doflamingo", "Joker"],
    "Charlotte Linlin":    ["Big Mom"],
    "Kaidou":              ["Kaido"],
    "Shanks":              ["Red-Haired Shanks", "Akagami"],
    "Imu":                 ["Im"],
    "Vegapunk":            ["Dr. Vegapunk"],
    "Boa Hancock":         ["Hancock"],
    "Crocodile":           [],
    "Buggy":               ["Buggy the Clown"],
    "Mihawk":              ["Dracule Mihawk", "Hawk Eyes"],
    "Yamato":              [],
    "Nico Olvia":          ["Olvia"],
    "Tama":                ["O-Tama"],   # disambig from word "tama"

    # ── Sprint 1 expansion: every major figure who goes by an alias ──
    # Marines (full Admiral / vice-admiral roster + nicknames)
    "Sakazuki":            ["Akainu", "Fleet Admiral Akainu"],
    "Borsalino":           ["Kizaru"],
    "Kuzan":               ["Aokiji"],
    "Issho":               ["Fujitora", "Admiral Fujitora"],
    "Aramaki":             ["Ryokugyu", "Green Bull", "Greenbull"],
    "Sengoku":             ["Buddha Sengoku"],
    "Smoker":              ["White Hunter", "Smoker the White Hunter"],
    "Tashigi":             [],
    "Koby":                ["Coby"],
    "Helmeppo":            [],
    "Vergo":               [],
    "Z":                   ["Zephyr"],
    "Tsuru":               ["Great Staff Officer Tsuru"],

    # Yonko + Emperors
    "Buggy":               ["Buggy the Clown", "Buggy the Star Clown"],

    # Worst Generation / Supernovas
    "Jewelry Bonney":      ["Bonney"],
    "Capone Bege":         ["Bege", "Gang Bege"],
    "Scratchmen Apoo":     ["Apoo", "Roar of the Sea"],
    "Basil Hawkins":       ["Hawkins", "Magician"],
    "X Drake":             ["Drake"],
    "Killer":              ["Massacre Soldier"],
    "Urouge":              ["Mad Monk"],

    # Strawhat allies / former crews
    "Nefertari Vivi":      ["Vivi", "Princess Vivi"],
    "Karoo":               ["Carue"],
    "Pell":                ["Pell the Falcon"],
    "Igaram":              ["Mr. 8"],
    "Camie":               [],
    "Pappag":              ["Papagg"],

    # Whitebeard Pirates
    "Marco":               ["Marco the Phoenix"],
    "Jozu":                ["Diamond Jozu"],
    "Vista":               ["Flower Sword Vista"],
    "Thatch":              [],
    "Izou":                ["Izo"],

    # Blackbeard Pirates
    "Jesus Burgess":       ["Burgess"],
    "Van Augur":           ["Augur"],
    "Doc Q":               [],
    "Lafitte":             [],

    # Big Mom Pirates / Charlotte family (top-level)
    "Charlotte Katakuri":  ["Katakuri"],
    "Charlotte Cracker":   ["Cracker"],
    "Charlotte Smoothie":  ["Smoothie"],
    "Charlotte Perospero": ["Perospero"],
    "Charlotte Pudding":   ["Pudding"],
    "Charlotte Lola":      ["Lola"],
    "Charlotte Brulee":    ["Brulee", "Brûlée"],
    "Charlotte Daifuku":   ["Daifuku"],
    "Charlotte Oven":      ["Oven"],

    # Beasts Pirates / Wano
    "King":                ["King the Wildfire", "Alber"],
    "Queen":               ["Queen the Plague"],
    "Jack":                ["Jack the Drought"],
    "Kouzuki Oden":        ["Oden", "Lord Oden"],
    "Kouzuki Momonosuke":  ["Momonosuke", "Momo"],
    "Kouzuki Hiyori":      ["Hiyori", "Komurasaki"],
    "Kouzuki Toki":        ["Toki"],
    "Yamato":              ["Oden Jr"],

    # Revolutionary Army
    "Sabo":                ["Flame Emperor", "Lucy"],
    "Koala":               [],
    "Hack":                [],
    "Ivankov":             ["Iva", "Emporio Ivankov"],
    "Inazuma":             [],
    "Bartholomew Kuma":    ["Kuma", "Tyrant Kuma", "Tyrant"],
    "Morley":              [],

    # World Government / Cipher Pol
    "Rob Lucci":           ["Lucci"],
    "Kaku":                [],
    "Jabra":               [],
    "Kalifa":              [],
    "Blueno":              [],
    "Spandam":             [],
    "Spandine":            [],
    "Rob Lucci":           ["Lucci"],
    "Stussy":              ["Stüssy"],

    # Vegapunk satellites
    "Vegapunk Lilith":     ["Lilith", "Punk-01"],
    "Vegapunk Edison":     ["Edison", "Punk-02"],
    "Vegapunk Pythagoras": ["Pythagoras", "Punk-03"],
    "Vegapunk Atlas":      ["Atlas", "Punk-04"],
    "Vegapunk Shaka":      ["Shaka", "Punk-05"],
    "Vegapunk York":       ["York", "Punk-06"],

    # Donquixote Family
    "Donquixote Rosinante":["Rosinante", "Corazon", "Cora-san", "Corasan"],
    "Trebol":              [],
    "Pica":                [],
    "Diamante":            [],
    "Vergo":               [],

    # Roger Pirates
    "Silvers Rayleigh":    ["Rayleigh", "Dark King Rayleigh", "Dark King"],
    "Scopper Gaban":       ["Gaban"],
    "Crocus":              [],
    "Shanks":              ["Red-Haired Shanks", "Akagami", "Red-Haired"],
    "Buggy":               ["Buggy the Clown", "Buggy the Star Clown"],

    # Notable individuals
    "Crocodile":           ["Sir Crocodile", "Mr. 0"],
    "Daz Bonez":           ["Mr. 1"],
    "Bentham":             ["Mr. 2", "Bon Clay", "Bon Kurei"],
    "Galdino":             ["Mr. 3"],
    "Babe":                ["Mr. 4"],
    "Marianne":            ["Miss Merry Christmas"],
    "Drophy":              ["Miss Doublefinger"],
    "Zala":                ["Miss Doublefinger"],
    "Paula":               ["Miss Doublefinger"],
    "Boa Sandersonia":     ["Sandersonia"],
    "Boa Marigold":        ["Marigold"],
    "Magellan":            ["Warden Magellan"],
    "Hannyabal":           [],
    "Saldeath":            [],
    "Enel":                ["Eneru", "God Enel"],
    "Wapol":               [],
    "Kureha":              ["Doctorine"],
    "Hiriluk":             ["Dr. Hiriluk"],
    "Bellamy":             ["Bellamy the Hyena"],
    "Foxy":                ["Silver Fox Foxy"],
    "Pagaya":              [],
    "Shyarly":             [],

    # Mythological / lore
    "Joy Boy":              ["Joyboy"],
    "Sun God Nika":         ["Nika"],
    "Five Elders":          ["Gorosei"],

    # Skypiea / Sky Islands
    "Conis":               [],
    "Aisa":                [],
    "Wyper":               [],
    "Gan Fall":            ["Sky Knight"],

    # Fishman Island
    "Otohime":             ["Queen Otohime"],
    "Neptune":             ["King Neptune", "Neptune of the Sea"],
    "Shirahoshi":          ["Princess Shirahoshi", "Mermaid Princess"],
    "Hody Jones":          ["Hody"],
    "Vander Decken IX":    ["Vander Decken", "Decken"],

    # Dressrosa
    "Riku Doldo III":      ["King Riku", "King Riku Doldo III", "Riku Doldo"],
    "Rebecca":             [],
    "Kyros":               [],
    "Viola":               ["Violet"],
    "Diamante":            [],

    # Wano specific
    "Kawamatsu":           [],
    "Inuarashi":           ["Duke Inuarashi"],
    "Nekomamushi":         ["Cat Viper", "Nekomamushi the Cat Viper"],
    "Carrot":              [],
    "Pedro":               ["Pedro the Tree Climber"],

    # Alabasta
    "Cobra":               ["Nefertari Cobra", "King Cobra"],
    "Chaka":               [],

    # Marineford-era
    "Squard":              [],
    "Edward Weevil":       ["Weevil"],
    "Whitey Bay":          [],

    # Egghead / Final saga
    "Bonney":              ["Jewelry Bonney"],
    "Saturn":              ["Saint Jaygarcia Saturn", "Jaygarcia Saturn"],
    "Imu":                 ["Im", "Im-sama", "Imu-sama", "Im sama"],
}


def _name_pattern(name, extras=()):
    """Compile a case-insensitive regex matching the canonical name OR any
    listed alias, with word boundaries on each side. Word boundaries mean
    'Ace' will hit 'Ace returns' but never 'place'."""
    parts = [name] + list(extras)
    # Sort longest-first so 'Monkey D. Luffy' matches before 'Luffy' would
    parts.sort(key=len, reverse=True)
    # Each part: escape, allow flexible whitespace between words, anchor
    # with word boundaries. The dot in 'Monkey D. Luffy' is escaped so it
    # only matches a literal period.
    alts = "|".join(_re.escape(p) for p in parts)
    return _re.compile(rf"\b(?:{alts})\b", _re.IGNORECASE)


def _build_sbs_index(sbs_path, names, max_per_char=20):
    """Per-character list of {volume, id, snippet} for SBS Q&As mentioning them.
    Uses word-boundary regex + curated aliases — far less noisy than substring."""
    if not os.path.exists(sbs_path): return {}
    with open(sbs_path, encoding="utf-8") as f:
        sbs = json.load(f)
    # Pre-build the corpus once
    docs = []
    for entry in sbs:
        text = (entry.get("question", "") or "") + " " + (entry.get("answer", "") or "")
        docs.append((entry, text))

    out = {}
    for n in names:
        aliases = NAME_ALIASES.get(n, ())
        # Skip names that are too short AND have no curated aliases — they'd
        # be either ambiguous or generic words ("Tama" without "O-Tama" alias)
        if len(n) < 4 and not aliases: continue
        # Names that are common English words (3-letter ones especially)
        # need an alias to be safe; if none provided, skip
        if len(n) < 3: continue

        pat = _name_pattern(n, aliases)
        hits = []
        for entry, text in docs:
            if pat.search(text):
                snippet = (entry.get("question", "") or "")[:160]
                hits.append({
                    "volume":  entry.get("volume"),
                    "id":      entry.get("id_num"),
                    "snippet": snippet,
                })
                if len(hits) >= max_per_char: break
        if hits: out[n] = hits
    return out


def _build_theory_index(th_path, names, max_per_char=10):
    """Per-character list of {id, title, status} for theories mentioning them.
    Same word-boundary + alias treatment as the SBS index."""
    if not os.path.exists(th_path): return {}
    with open(th_path, encoding="utf-8") as f:
        theories = json.load(f)
    docs = []
    for i, t in enumerate(theories):
        text = (t.get("title", "") + " " + (t.get("description") or "") +
                " " + (t.get("body") or ""))
        docs.append((i, t, text))

    out = {}
    for n in names:
        aliases = NAME_ALIASES.get(n, ())
        if len(n) < 4 and not aliases: continue
        if len(n) < 3: continue

        pat = _name_pattern(n, aliases)
        hits = []
        for i, t, text in docs:
            if pat.search(text):
                num = t.get("num")
                hits.append({"id": i, "num": num,
                             "title": t.get("title", "")[:100],
                             "status": t.get("status", "active")})
                if len(hits) >= max_per_char: break
        if hits: out[n] = hits
    return out



def _build_shards_index(records):
    """Return a name-keyed dict of character shard dossiers for character.html.

    Each dossier is query.character_dossier() output, with _display names
    pre-resolved on every cross-reference ID so the JS renderer can show
    human-readable labels without a separate entity-index fetch.
    Returns {} when the entity_index or query layer is unavailable.
    """
    scripts_dir = os.path.join(DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from lib import query as _q
    except ImportError:
        print("  ⚠ scripts/lib/query.py not found — skipping shard dossiers")
        return {}

    idx_path = os.path.join(DIR, "entity_index.json")
    if not os.path.exists(idx_path):
        print("  ⚠ entity_index.json not found — skipping shard dossiers")
        return {}
    with open(idx_path, encoding="utf-8") as f:
        entity_index = json.load(f)

    name_map = _q._name_index()   # id → display name

    out = {}
    for rec in records:
        name   = rec["name"]
        chr_id = entity_index.get(name.lower())
        if not chr_id or not chr_id.startswith("chr:"):
            continue
        try:
            dossier = _q.character_dossier(chr_id)
            # Rows come back as references shared by every dossier that
            # mentions them; annotating in place lets the LAST character
            # baked overwrite _display for everyone (Luffy's sworn-brother
            # rows read "Monkey D. Luffy" because Ace and Sabo bake after
            # him). Copy each row before touching it.
            for _k, _v in list(dossier.items()):
                if isinstance(_v, list):
                    dossier[_k] = [dict(r) if isinstance(r, dict) else r for r in _v]
            # Annotate cross-referenced IDs with display names so JS can show
            # human-readable labels without a client-side entity-index lookup.
            for key in ("fruits", "owns", "crews"):
                for row in dossier.get(key, []):
                    dn = name_map.get(row.get("to"))
                    if dn:
                        row["_display"] = dn
                    dn2 = name_map.get(row.get("from_owner"))
                    if dn2:
                        row["_display_from"] = dn2
            for row in dossier.get("family", []):
                other_id = row.get("to") if row.get("from") == chr_id else row.get("from")
                dn = name_map.get(other_id) if other_id else None
                if dn:
                    row["_display"] = dn
            # voices: _display is the VA name (already in row.name; also in name_map)
            for row in dossier.get("voices", []):
                if not row.get("_display"):
                    row["_display"] = row.get("name") or name_map.get(row.get("from"))
            # trains-with: annotate the other character's display name
            for row in dossier.get("trained_by", []):   # from=trainer, to=chr
                dn = name_map.get(row.get("from"))
                if dn:
                    row["_display"] = dn
            for row in dossier.get("trained", []):      # from=chr, to=trainee
                dn = name_map.get(row.get("to"))
                if dn:
                    row["_display"] = dn
            # born-in: annotate location display name
            for row in dossier.get("born_in", []):
                dn = name_map.get(row.get("to"))
                if dn:
                    row["_display"] = dn
            # sails-on: annotate ship display name
            for row in dossier.get("sails_on", []):
                dn = name_map.get(row.get("to"))
                if dn:
                    row["_display"] = dn
            out[name] = dossier
        except Exception as exc:
            pass   # silently skip — the page degrades gracefully without shards
    return out

def bake_punk():
    pr_path  = os.path.join(DIR, "punk_records.json")
    csv_path = os.path.join(DIR, "appearances.csv")
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    th_path  = os.path.join(DIR, "theories_import.json")
    portraits_path = os.path.join(DIR, "portraits.json")
    if not os.path.exists(pr_path):
        print("  ✗ punk_records.json not found — run punk_records_scraper.py first")
        return

    with open(pr_path, encoding="utf-8") as f:
        raw = json.load(f)

    records = _compact_punk_records(raw)
    names = [r["name"] for r in records]

    # Inject appearance counts into each record (used by characters.html badges)
    csv_apps = _build_appearances_index(csv_path, names)
    for r in records:
        if r["name"] in csv_apps:
            r["appearances"] = len(csv_apps[r["name"]])

    # Annotate chr_id for ?id= routing in characters.html / character.html
    eidx_path = os.path.join(DIR, "entity_index.json")
    if os.path.exists(eidx_path):
        eidx = json.load(open(eidx_path, encoding="utf-8"))
        for r in records:
            cid = eidx.get(r["name"].lower())
            if cid and cid.startswith("chr:"):
                r["chr_id"] = cid

    payload = json.dumps(records, ensure_ascii=False, separators=(',', ':'))

    # Bake into both characters.html (index) and character.html (profile)
    for page in ("characters.html", "character.html"):
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        ok, size = bake_block(path, "punk-records-data", payload)
        if ok:
            print(f"  ✓ {page:<15} ← {len(records):>5,} characters  ({size} KB)")

    # ── CANON FACTS (manga-derived, 🟢 tier with source citations) ──
    # Group facts by subject for fast O(1) lookup in the profile renderer.
    facts_path = os.path.join(DIR, "canon_facts.json")
    if os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as f:
            facts_list = json.load(f)
        facts_by_subject = {}
        for fact in facts_list:
            facts_by_subject.setdefault(fact["subject"], []).append(fact)
        # Slim the per-fact payload — drop the full chapters list from
        # `total_appearance_count` because we already have it in
        # appearances.csv (lazy-fetched). Keep the citation summary.
        for subj, facts in facts_by_subject.items():
            for f in facts:
                if f["predicate"] == "total_appearance_count":
                    for src in f.get("sources", []):
                        if "chapters" in src and len(src["chapters"]) > 5:
                            src["chapter_range"] = f"{min(src['chapters'])}-{max(src['chapters'])}"
                            del src["chapters"]
        char_path = os.path.join(DIR, "character.html")
        if os.path.exists(char_path):
            facts_payload = json.dumps(facts_by_subject, ensure_ascii=False, separators=(",", ":"))
            ok, size = bake_block(char_path, "canon-facts-data", facts_payload)
            if ok:
                print(f"  ✓ character.html  ← {sum(len(v) for v in facts_by_subject.values()):,} canon facts  ({size} KB)")

    # Bake portraits — slim {name: thumb_url} map shared by both pages.
    # Upgrade scrape-time thumbnails (80-114px wide, blurry on the 160px
    # profile portrait) to 300px-wide variants for crisp display + retina.
    if os.path.exists(portraits_path):
        with open(portraits_path, encoding="utf-8") as f:
            portraits_full = json.load(f)
        portraits_slim = {n: _resolve_portrait(n, p["thumb"]) for n, p in portraits_full.items()
                          if isinstance(p, dict) and p.get("thumb")}
        portrait_payload = json.dumps(portraits_slim, ensure_ascii=False, separators=(',', ':'))
        for page in ("characters.html", "character.html", "crew.html"):
            path = os.path.join(DIR, page)
            if not os.path.exists(path): continue
            ok, size = bake_block(path, "portraits-data", portrait_payload)
            if ok:
                print(f"  ✓ {page:<15} ← {len(portraits_slim):>5,} portraits  ({size} KB)")

    # Cross-reference indexes — only character.html needs them (profile page).
    # Note: per-character appearances are NOT baked here. character.html
    # lazy-fetches appearances.csv on demand instead — saves ~1.5MB of HTML
    # and reuses the cached CSV that index.html already loaded.
    char_path = os.path.join(DIR, "character.html")
    if os.path.exists(char_path):
        # Empty out any previously-baked appearances-index so old data isn't shipped
        bake_block(char_path, "appearances-index", "{}")

        sbs_idx = _build_sbs_index(sbs_path, names)
        sbs_payload = json.dumps(sbs_idx, ensure_ascii=False, separators=(',', ':'))
        bake_block(char_path, "sbs-index", sbs_payload)
        print(f"  ✓ character.html  ← {len(sbs_idx):>5,} SBS cross-refs")

        # Theory Forge pulled 2026-07-13 — bake an EMPTY theory index so the
        # "Theories mentioning X" section stays dark and no spoiler-laden
        # theory titles land in character.html source. Restore _build_theory_index
        # here when Theory Forge relinks.
        bake_block(char_path, "theory-index", "{}")
        print(f"  ·  character.html  ← theory cross-refs disabled (Theory Forge pulled)")
        # ── SHARD DOSSIERS (tier-tagged relationship graph) ─────────────────
        shards = _build_shards_index(records)
        if shards:
            shards_payload = json.dumps(shards, ensure_ascii=False, separators=(",", ":"))
            ok, size = bake_block(char_path, "shards-data", shards_payload)
            if ok:
                print(f"  ✓ character.html  ← {len(shards):,} shard dossiers  ({size} KB)")


# ── WORKBENCH (unified citation index) ─────────────────────────
# Builds a single flat list of citable Fact Cards for the Theory Workbench.
# Each card: { id, type, title, subtitle, href, tokens } — tokens are a
# pre-lowered search blob for instant client-side autocomplete.
def _build_workbench_index():
    cards = []

    # Characters (whole-card level)
    pr_path = os.path.join(DIR, "punk_records.json")
    if os.path.exists(pr_path):
        with open(pr_path, encoding="utf-8") as f:
            pr = json.load(f)
        for name, rec in pr.items():
            if not rec.get("found"): continue
            subtitle_bits = []
            if rec.get("epithet"):    subtitle_bits.append(rec["epithet"])
            if rec.get("affiliation"): subtitle_bits.append(rec["affiliation"].split(";")[0].strip())
            cards.append({
                "id":    f"char:{name}",
                "type":  "character",
                "title": name,
                "subtitle": " · ".join(subtitle_bits)[:120],
                "href":  f"character.html?name={name}",
                "tokens": (name + " " + (rec.get("name_jp", "") or "") +
                           " " + (rec.get("epithet", "") or "")).lower(),
            })

    # SBS Q&As (one per entry)
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    if os.path.exists(sbs_path):
        with open(sbs_path, encoding="utf-8") as f:
            sbs = json.load(f)
        for qa in sbs:
            id_num = qa.get("id_num")
            if id_num is None: continue
            num_pad = str(id_num).zfill(4)
            q = (qa.get("question") or "").strip()
            cards.append({
                "id":    f"sbs:{num_pad}",
                "type":  "sbs",
                "title": (q[:120] + ("…" if len(q) > 120 else "")),
                "subtitle": f"SBS Vol {qa.get('volume')} · #{num_pad}" +
                            (f" · {qa.get('name')}" if qa.get('name') else ""),
                "href":  f"sbs.html#{num_pad}",
                "tokens": (q + " " + (qa.get("answer") or "")).lower()[:600],
            })

    # Theories (curated only — uses stable num)
    th_path = os.path.join(DIR, "theories_import.json")
    if os.path.exists(th_path):
        with open(th_path, encoding="utf-8") as f:
            theories = json.load(f)
        for t in theories:
            num = t.get("num")
            if num is None: continue
            num_pad = str(num).zfill(4)
            cards.append({
                "id":    f"theory:{num_pad}",
                "type":  "theory",
                "title": t.get("title", ""),
                "subtitle": f"Theory #{num_pad} · {t.get('status', 'active')}",
                "href":  f"theories.html#theory-{num_pad}",
                "tokens": (t.get("title", "") + " " +
                           (t.get("description") or "")).lower()[:400],
            })

    # Cover stories
    cs_path = os.path.join(DIR, "cover_stories.json")
    if os.path.exists(cs_path):
        with open(cs_path, encoding="utf-8") as f:
            cs = json.load(f)
        for c in cs:
            cards.append({
                "id":    f"coverstory:{c.get('slug', c['name'])}",
                "type":  "coverstory",
                "title": c["name"],
                "subtitle": f"Cover-story · {c.get('chapter_range', '?')}",
                "href":  f"covers.html#{c.get('slug', c['name'])}",
                "tokens": (c["name"] + " " + (c.get("summary") or "")).lower()[:400],
            })

    return cards


# ── PROSE AUTO-LINKER (Phase A of Canon Engine) ───────────────
# Walks already-baked text and adds <a> tags around recognised references.
# Three CSS classes apply different visual treatments based on WHO said
# the surrounding sentence:
#   .cite-canon    — gold solid underline   — Oda's text (highest trust)
#   .cite-context  — grey faint dotted      — Reader's question (navigation only)
#   .cite-theory   — ink-blue solid         — Theory body (speculation context)
#
# This is a READ-ONLY pass: it cannot create or modify any data record.
# See docs/canon-policy.md for the full firewall.

# Pre-build a name → href + canonical-name map for fast linking
def _build_linker_index():
    """Returns (compiled_regex, lookup_dict).
    The regex matches any character canonical-name OR alias; the dict maps
    each matched form back to the canonical href."""
    pr_path = os.path.join(DIR, "punk_records.json")
    if not os.path.exists(pr_path): return None, {}
    with open(pr_path, encoding="utf-8") as f:
        pr = json.load(f)
    # Only link to characters with a real profile (found:true)
    canonical_names = [n for n, rec in pr.items() if rec.get("found")]

    pattern_parts = []
    lookup = {}
    for cname in canonical_names:
        forms = [cname] + list(NAME_ALIASES.get(cname, ()))
        for f in forms:
            # Skip super-short forms (≤2 chars) — too noisy even with \b
            if len(f) < 3: continue
            lookup[f.lower()] = cname
            pattern_parts.append(_re.escape(f))

    if not pattern_parts: return None, lookup
    # Sort longest-first so 'Monkey D. Luffy' matches before 'Luffy' would
    pattern_parts.sort(key=len, reverse=True)

    # Combined regex: character names OR SBS Vol N references
    chars_alt = "|".join(pattern_parts)
    full = (
        r"(?P<sbs>\bSBS\s+Vol(?:ume)?\.?\s+(?P<sbs_num>\d{1,3})\b)"
        r"|"
        r"(?P<vol>\bVol(?:ume)?\.?\s+(?P<vol_num>\d{1,3})\b)"
        r"|"
        rf"(?P<char>\b(?:{chars_alt})\b)"
    )
    return _re.compile(full, _re.IGNORECASE), lookup


def linkify(text, css_class, idx):
    """Walk text, replace recognised refs with <a> tags. css_class is one
    of cite-canon | cite-context | cite-theory. idx is (pattern, lookup)
    from _build_linker_index. Returns linked HTML-safe string."""
    if not text or not idx[0]: return text
    pattern, lookup = idx

    def repl(m):
        if m.group("sbs"):
            num = m.group("sbs_num").zfill(2)
            return (f'<a class="{css_class}" href="sbs.html?vol={num}" '
                    f'title="Jump to SBS Volume {int(num)}">{m.group(0)}</a>')
        if m.group("vol"):
            num = m.group("vol_num")
            return (f'<a class="{css_class}" href="sbs.html?vol={num.zfill(2)}" '
                    f'title="Open Volume {num}">{m.group(0)}</a>')
        if m.group("char"):
            matched = m.group("char")
            cname = lookup.get(matched.lower())
            if not cname: return matched
            href = "character.html?name=" + _url_quote(cname)
            return (f'<a class="{css_class}" href="{href}" '
                    f'title="Open {cname}">{matched}</a>')
        return m.group(0)

    return pattern.sub(repl, text)


def _url_quote(s):
    import urllib.parse as _u
    return _u.quote(s, safe="")


def bake_linkified_sbs():
    """Re-walk sbs_archive.json and emit a sbs-linked-data block.
    Each entry gets `question_html` and `answer_html` with auto-links applied."""
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    if not os.path.exists(sbs_path): return
    with open(sbs_path, encoding="utf-8") as f:
        sbs = json.load(f)
    idx = _build_linker_index()
    if not idx[0]:
        print("  ✗ linker index empty (no Punk Records?) — skipping linkify")
        return

    linked_count = 0
    out = []
    for qa in sbs:
        q_html = linkify(qa.get("question", ""), "cite-context", idx)
        a_html = linkify(qa.get("answer",   ""), "cite-canon",   idx)
        if q_html != qa.get("question") or a_html != qa.get("answer"):
            linked_count += 1
        # Slim: only ship id_num + the linked HTML versions
        out.append({
            "id_num":      qa.get("id_num"),
            "question_html": q_html,
            "answer_html":   a_html,
        })

    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    page = "sbs.html"
    path = os.path.join(DIR, page)
    if not os.path.exists(path): return
    ok, size = bake_block(path, "sbs-linked-data", payload)
    if ok:
        print(f"  ✓ {page:<13} ← linkified {linked_count:,} of {len(sbs):,} Q&As  ({size} KB)")


def bake_linkified_theories():
    """Same treatment for theory bodies."""
    th_path = os.path.join(DIR, "theories_import.json")
    if not os.path.exists(th_path): return
    with open(th_path, encoding="utf-8") as f:
        theories = json.load(f)
    idx = _build_linker_index()
    if not idx[0]: return

    linked_count = 0
    out = []
    for t in theories:
        title_html = linkify(t.get("title", ""), "cite-theory", idx)
        desc_html  = linkify(t.get("description", ""), "cite-theory", idx)
        if title_html != t.get("title") or desc_html != t.get("description"):
            linked_count += 1
        out.append({
            "num":        t.get("num"),
            "id":         t.get("id"),
            "title_html": title_html,
            "description_html": desc_html,
        })

    payload = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    page = "theories.html"
    path = os.path.join(DIR, page)
    if not os.path.exists(path): return
    ok, size = bake_block(path, "theories-linked-data", payload)
    if ok:
        print(f"  ✓ {page:<13} <- linkified {linked_count:,} of {len(theories):,} theories  ({size} KB)")

    # Also bake cites shard data into theories.html (keyed by theory num)
    cites_path = os.path.join(DIR, "relationships", "cites.json")
    if os.path.exists(cites_path):
        with open(cites_path, encoding="utf-8") as f:
            cites_rows = json.load(f)
        cites_by_num = {}
        for row in cites_rows:
            theory_id = row.get("from", "")
            if theory_id.startswith("theory:"):
                try:
                    num = int(theory_id.replace("theory:", ""))
                    cites_by_num.setdefault(num, []).append({
                        "to":     row.get("to"),
                        "stance": row.get("stance"),
                    })
                except ValueError:
                    pass
        cites_payload = json.dumps(cites_by_num, ensure_ascii=False, separators=(",", ":"))
        bake_block(path, "theories-cites-data", cites_payload)


def bake_awakenings():
    src = os.path.join(DIR, "awakenings.json")
    page = os.path.join(DIR, "awakenings.html")
    if not (os.path.exists(src) and os.path.exists(page)): return
    payload = open(src, encoding="utf-8").read()
    ok, size = bake_block(page, "awakenings-data", payload)
    if ok:
        try:
            n = len(json.loads(payload).get("awakenings", []))
            print(f"  ✓ awakenings.html ← {n:>3} awakenings ({size} KB)")
        except Exception: pass


def bake_timeline_events():
    src = os.path.join(DIR, "timeline_events.json")
    page = os.path.join(DIR, "timeline.html")
    if not (os.path.exists(src) and os.path.exists(page)): return
    payload = open(src, encoding="utf-8").read()
    ok, size = bake_block(page, "events-data", payload)
    if ok:
        try:
            n = len(json.loads(payload).get("events", []))
            print(f"  ✓ timeline.html  ← {n:>3} curated events ({size} KB)")
        except Exception: pass


def bake_ships():
    src = os.path.join(DIR, "ships.json")
    if not os.path.exists(src): return
    payload = open(src, encoding="utf-8").read()
    for page in ("ships.html", "ship.html"):
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        ok, size = bake_block(path, "ships-data", payload)
        if ok:
            try:
                n = sum(1 for v in json.loads(payload).values() if isinstance(v, dict) and v.get("found"))
                print(f"  ✓ {page:<13} ← {n:>4} ships ({size} KB)")
            except Exception: pass

    _bake_ship_sails("ship.html")

    # Bake per-ship crew counts into ships.html for the index cards
    sails_path = os.path.join(DIR, "relationships", "sails-on.json")
    ships_html = os.path.join(DIR, "ships.html")
    if os.path.exists(sails_path) and os.path.exists(ships_html):
        with open(sails_path, encoding="utf-8") as f:
            sails_rows = json.load(f)
        counts: dict[str, int] = {}
        for row in sails_rows:
            ship_id = row.get("to", "")
            if ship_id.startswith("ship:"):
                counts[ship_id] = counts.get(ship_id, 0) + 1
        bake_block(ships_html, "ship-crew-counts",
                   json.dumps(counts, ensure_ascii=False, separators=(",", ":")))


def _bake_ship_sails(page_name):
    """Bake sails-on shard data (by ship ID) into ship.html as ship-sails-data."""
    page = os.path.join(DIR, page_name)
    if not os.path.exists(page):
        return
    sails_path = os.path.join(DIR, "relationships", "sails-on.json")
    if not os.path.exists(sails_path):
        return

    scripts_dir = os.path.join(DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from lib import query as _q
    except ImportError:
        return

    chr_name_map = _q._name_index()

    # name -> debut chapter, so ship.html can hide not-yet-debuted crew
    _debut_of = {}
    _pr_path = os.path.join(DIR, "punk_records.json")
    if os.path.exists(_pr_path):
        with open(_pr_path, encoding="utf-8") as f:
            for _nm, _rec in json.load(f).items():
                if isinstance(_rec, dict):
                    _fa = _rec.get("first_appearance") or ""
                    _m = _re.search(r"Chapter\s+(\d+)", _fa, _re.I) if _fa else None
                    if _m:
                        _debut_of[_nm] = int(_m.group(1))

    with open(sails_path, encoding="utf-8") as f:
        sails_rows = json.load(f)

    by_ship = {}
    for row in sails_rows:
        ship_id = row.get("to", "")
        if not ship_id.startswith("ship:"):
            continue
        entry = {
            "from":     row.get("from"),
            "current":  row.get("current"),
            "_display": chr_name_map.get(row.get("from", "")),
        }
        _d = _debut_of.get(entry["_display"] or "")
        if _d:
            entry["_debut"] = _d
        if row.get("note"):
            entry["note"] = row["note"]
        by_ship.setdefault(ship_id, []).append(entry)

    payload = json.dumps(by_ship, ensure_ascii=False, separators=(",", ":"))
    ok, size = bake_block(page, "ship-sails-data", payload)
    if ok:
        total = sum(len(v) for v in by_ship.values())
        print(f"  ✓ {page_name:<13} ← {total:>4} sails-on rows / {len(by_ship)} ships  ({size} KB)")


def _bake_weapon_owns(page_name):
    """Bake owns shard data (by weapon ID) into weapons.html as weapon-owns-data."""
    page = os.path.join(DIR, page_name)
    if not os.path.exists(page):
        return
    owns_path = os.path.join(DIR, "relationships", "owns.json")
    if not os.path.exists(owns_path):
        return

    scripts_dir = os.path.join(DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from lib import query as _q
    except ImportError:
        return

    chr_name_map = _q._name_index()

    with open(owns_path, encoding="utf-8") as f:
        owns_rows = json.load(f)

    by_weapon = {}
    for row in owns_rows:
        weap_id = row.get("to", "")
        if not weap_id.startswith("weap:"):
            continue
        entry = {
            "from":       row.get("from"),
            "current":    row.get("current", False),
            "tier":       row.get("tier", "speculation"),
            "_display":   chr_name_map.get(row.get("from", "")),
        }
        if row.get("from_owner"):
            entry["from_owner"]         = row["from_owner"]
            entry["_display_from_owner"] = chr_name_map.get(row["from_owner"])
        by_weapon.setdefault(weap_id, []).append(entry)

    payload = json.dumps(by_weapon, ensure_ascii=False, separators=(",", ":"))
    bake_block(page, "weapon-owns-data", payload)


def _build_location_shards_index():
    """Return a loc_id-keyed dict of shard data for location.html.

    Each entry has:
      arcs:       set-in rows where to==loc_id (annotated with arc _display)
      born_here:  born-in rows where to==loc_id (annotated with chr _display)
    Returns {} when query layer or shards are unavailable.
    """
    scripts_dir = os.path.join(DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from lib import query as _q
    except ImportError:
        return {}

    arcs_data = os.path.join(DIR, "arcs.json")
    if not os.path.exists(arcs_data):
        return {}
    with open(arcs_data, encoding="utf-8") as f:
        arcs_raw = json.load(f)
    arc_name_map = {}
    arc_start_map = {}
    arc_list = arcs_raw if isinstance(arcs_raw, list) else list(arcs_raw.values())
    for a in arc_list:
        if isinstance(a, dict):
            aid = a.get("id") or a.get("arc_id")
            if aid:
                arc_name_map[aid] = a.get("name", aid)
                if isinstance(a.get("start"), int):
                    arc_start_map[aid] = a["start"]

    chr_name_map = _q._name_index()

    # name -> debut chapter so location.html can hide not-yet-debuted natives
    _debut_of = {}
    _pr_path = os.path.join(DIR, "punk_records.json")
    if os.path.exists(_pr_path):
        import re as _re2
        with open(_pr_path, encoding="utf-8") as f:
            for _nm, _rec in json.load(f).items():
                if isinstance(_rec, dict):
                    _fa = _rec.get("first_appearance") or ""
                    _m = _re2.search(r"Chapter\s+(\d+)", _fa, _re2.I) if _fa else None
                    if _m:
                        _debut_of[_nm] = int(_m.group(1))

    set_in_by_loc  = _q.by_to("set-in")
    born_in_by_loc = _q.by_to("born-in")

    out = {}
    for loc_id in set(list(set_in_by_loc.keys()) + list(born_in_by_loc.keys())):
        arcs_rows  = [dict(r) for r in set_in_by_loc.get(loc_id, [])]
        born_rows  = [dict(r) for r in born_in_by_loc.get(loc_id, [])]
        for row in arcs_rows:
            dn = arc_name_map.get(row.get("from"))
            if dn:
                row["_display"] = dn
            # Arc start chapter -- location.html hides not-yet-reached arcs
            # (their names are spoilers in themselves; unknown fails closed)
            _st = arc_start_map.get(row.get("from"))
            if _st:
                row["_start"] = _st
        for row in born_rows:
            dn = chr_name_map.get(row.get("from"))
            if dn:
                row["_display"] = dn
            _d = _debut_of.get(dn or "")
            if _d:
                row["_debut"] = _d
        out[loc_id] = {"arcs": arcs_rows, "born_here": born_rows}
    return out


def _bake_location_counts(page_name):
    """Bake per-location born-in + set-in counts into locations.html as location-counts."""
    page = os.path.join(DIR, page_name)
    if not os.path.exists(page):
        return
    loc_shards = _build_location_shards_index()
    if not loc_shards:
        return
    counts = {
        loc_id: {
            "born": len(data.get("born_here", [])),
            "arcs": len(data.get("arcs", [])),
        }
        for loc_id, data in loc_shards.items()
        if len(data.get("born_here", [])) > 0 or len(data.get("arcs", [])) > 0
    }
    # sorted(): built from set-backed lookups, so an unsorted dump reshuffles
    # identical data every run and the scheduled refresh commits pure churn.
    counts = dict(sorted(counts.items()))
    payload = json.dumps(counts, ensure_ascii=False, separators=(",", ":"))
    ok, size = bake_block(page, "location-counts", payload)
    if ok:
        total_born = sum(v["born"] for v in counts.values())
        total_arcs = sum(v["arcs"] for v in counts.values())
        print(f"  ✓ {page_name:<14} ← {len(counts):>3} locs w/ counts ({total_born} born · {total_arcs} arcs)")


def bake_locations():
    src = os.path.join(DIR, "locations.json")
    if not os.path.exists(src): return
    payload = open(src, encoding="utf-8").read()
    for page in ("locations.html", "location.html"):
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        ok, size = bake_block(path, "locations-data", payload)
        if ok:
            try:
                n = sum(1 for v in json.loads(payload).values() if isinstance(v, dict) and v.get("found"))
                print(f"  ✓ {page:<14} <- {n:>4} locations ({size} KB)")
            except Exception: pass
    # Bake location shards data into location.html only
    loc_html = os.path.join(DIR, "location.html")
    if os.path.exists(loc_html):
        loc_shards = _build_location_shards_index()
        if loc_shards:
            # sorted() for byte-stable output -- see the note on location-counts
            loc_shards = dict(sorted(loc_shards.items()))
            shards_payload = json.dumps(loc_shards, ensure_ascii=False, separators=(",", ":"))
            bake_block(loc_html, "location-shards-data", shards_payload)
    # Bake born-in + set-in counts per location into locations.html
    _bake_location_counts("locations.html")


def bake_compare():
    """Compare page needs: punk_records (slim), portraits, canon_facts."""
    page = os.path.join(DIR, "compare.html")
    pr_path = os.path.join(DIR, "punk_records.json")
    portraits_path = os.path.join(DIR, "portraits.json")
    facts_path = os.path.join(DIR, "canon_facts.json")
    if not (os.path.exists(page) and os.path.exists(pr_path)): return
    with open(pr_path, encoding="utf-8") as f: pr = json.load(f)
    slim = []
    for name, rec in pr.items():
        if not rec.get("found"): continue
        slim.append({k: rec.get(k) for k in (
            "epithet","age","birthday","height","blood_type","origin","bounty",
            "devil_fruit_name","affiliation","occupation","first_appearance","appearances"
        ) if rec.get(k)})
        slim[-1]["name"] = name
    bake_block(page, "punk-records-data",
               json.dumps(slim, ensure_ascii=False, separators=(",", ":")))
    if os.path.exists(portraits_path):
        with open(portraits_path, encoding="utf-8") as f: p = json.load(f)
        slim_p = {n: v["thumb"] for n, v in p.items() if isinstance(v, dict) and v.get("thumb")}
        bake_block(page, "portraits-data",
                   json.dumps(slim_p, ensure_ascii=False, separators=(",", ":")))
    if os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as f: facts = json.load(f)
        by_subj = {}
        for fact in facts:
            if fact.get("tier") == "canon":
                by_subj.setdefault(fact["subject"], []).append({
                    "predicate": fact["predicate"], "tier": "canon"})
        bake_block(page, "canon-facts-data",
                   json.dumps(by_subj, ensure_ascii=False, separators=(",", ":")))
    print(f"  ✓ compare.html  ← {len(slim):>4} characters")


def bake_families():
    src = os.path.join(DIR, "families.json")
    page = os.path.join(DIR, "families.html")
    if not (os.path.exists(src) and os.path.exists(page)): return
    payload = open(src, encoding="utf-8").read()
    ok, size = bake_block(page, "families-data", payload)
    if ok:
        try:
            n = len(json.loads(payload).get("edges", []))
            print(f"  ✓ families.html ← {n:>4} edges ({size} KB)")
        except Exception: pass


import re as _re_for_rank
def _rank_from_occupation(occ):
    """Map an occupation string to a numeric rank for crew ordering.
    Lower = higher in command. Captain/Fleet Admiral=0, officer roles=2-5, generic=9.
    Uses the first semicolon-separated segment as the current/primary role so that
    '(former)' qualifiers in later segments don't suppress the live rank."""
    if not occ: return 9
    s = occ.lower()
    # First segment = current primary role (avoids "(former)" in later segments)
    first = _re_for_rank.split(r"\s*[;·]\s*", occ, maxsplit=1)[0].lower().strip()
    # Neutralise ALL parenthetical captain qualifiers in the first-segment check
    cap_clean = _re_for_rank.sub(r"\bcaptain\s*\([^)]*\)", "__exfmrcptn__", first)
    cap_clean = _re_for_rank.sub(r"former\s+captain", "__exfmrcptn__", cap_clean)
    if "fleet admiral" in first or "fleet commander" in first: return 0
    if "captain" in cap_clean: return 0
    if "first mate" in first or "right-hand" in first or "right hand" in first: return 1
    if "second-in-command" in first or "vice captain" in first: return 1
    if "vice admiral" in first: return 1
    if "rear admiral" in first: return 2
    if "admiral" in first: return 1          # plain Admiral (not fleet/vice/rear — checked above)
    if "commander" in first: return 1
    if "commodore" in first: return 3
    # Role-based ranks — use full string; these are structural, not rank titles
    if "navigator" in s:    return 3
    if "cook" in s or "chef" in s: return 3
    if "doctor" in s or "physician" in s: return 3
    if "shipwright" in s:   return 3
    if "musician" in s:     return 3
    if "sniper" in s or "marksman" in s: return 3
    if "swordsman" in s:    return 2
    if "helmsman" in s:     return 4
    if "archaeologist" in s or "scholar" in s: return 4
    if "quartermaster" in s: return 4
    if "scientist" in s or "engineer" in s: return 4
    if "officer" in s or "lieutenant" in s: return 5
    if "rookie" in s or "apprentice" in s: return 7
    return 9


# Universal status-tier priority: lower = higher in the hierarchy.
# Crew-agnostic — works for every crew that uses these status strings in crews.json.
STATUS_PRIORITY = {
    # Top brass
    "captain": 0, "governor-general": 0, "fleet admiral": 0,
    # Sweet Commanders / All-Stars / equivalent elite
    "sweet commander": 10, "all-star": 10, "all stars": 10,
    "tobiroppo": 20, "tobi roppo": 20, "flying six": 20,
    # Mid-elite
    "headliner": 30, "headliners": 30,
    "armored division": 35,
    "numbers": 38,
    "gifter": 40, "gifters": 40, "pleasure": 42, "pleasures": 42, "waiter": 44, "waiters": 44,
    # Subordinate / allied
    "ssg": 25,
    "pacifista": 45,
    "tontatta pirates": 50,
    "kawamatsu": 55,
    # Family / squad groupings (mid)
    "gorgon sisters": 50,
    "kurozumi family": 50,
    "donquixote family": 50,
    "rosward family": 50, "shepherd family": 50, "figarland family": 50,
    "rimoshifu family": 50, "satchels family": 50, "manmayer family": 50,
    "nerona family": 50, "nefertari family": 50, "davy family": 50,
    "ryugu kingdom": 55,
    "mysterious four": 50,
    "tontatta pirates": 50,
    "saruyama alliance": 55,
    "masira pirates": 55, "shoujou pirates": 55,
    "perona": 55,
    "inuarashi musketeer squad": 55,
    "north army": 55, "south army": 55, "east army": 55, "west army": 55,
    "recon squad": 55, "espionage": 55, "sword": 55, "secret": 60,
    # Special branches / units
    "153rd branch": 50, "g-14": 50, "gr 66": 50,
    "black cage corps": 50, "enies lobby": 50, "high town": 50,
    "zambai's company union": 55,
    "double agent": 60, "ruse": 65,
    "undercover": 85,
    # Common tail buckets
    "current": 60, "temporary": 70, "semi-retired": 75,
    "former": 80, "resigned": 82, "retired": 84, "dissolved": 86,
    "defected": 88, "revoked": 90, "post mortem": 92, "descended": 92,
    "illegitimate": 60,
    "shimotsuki ushimaru": 60,
}


def _status_priority(status):
    if not status: return 60
    return STATUS_PRIORITY.get(status.lower().strip(), 60)


def _pretty_status(s):
    if not s: return "Members"
    s = s.strip()
    # Special-case the lowercase compound forms
    aliases = {
        "tobiroppo": "Tobi Roppo (Flying Six)",
        "armored division": "Armored Division",
        "numbers": "Numbers",
        "ssg": "SSG (Seraphim)",
        "153rd branch": "153rd Branch",
        "g-14": "G-14",
        "gr 66": "GR 66",
        "current": "Members",
        "former": "Former",
        "defected": "Defected",
        "undercover": "Undercover",
        "pacifista": "Pacifista",
    }
    if s.lower() in aliases: return aliases[s.lower()]
    return " ".join(w.capitalize() for w in s.split())


def bake_crews():
    src = os.path.join(DIR, "crews.json")
    if not os.path.exists(src): return
    crews_doc = json.load(open(src, encoding="utf-8"))
    pr_path = os.path.join(DIR, "punk_records.json")
    pr = json.load(open(pr_path, encoding="utf-8")) if os.path.exists(pr_path) else {}
    # Hand-curated tier overrides (the gold-standard layer)
    hier_path = os.path.join(DIR, "crew_hierarchies.json")
    hierarchies = {}
    if os.path.exists(hier_path):
        try:
            hierarchies = json.load(open(hier_path, encoding="utf-8")).get("crews", {})
        except Exception:
            hierarchies = {}

    # Build crew → [ships] reverse index from ships.json affiliation field.
    # Affiliation may have multiple crews split by ';' or ' · '.
    ships_by_crew = {}
    ships_path = os.path.join(DIR, "ships.json")
    if os.path.exists(ships_path):
        try:
            ship_data = json.load(open(ships_path, encoding="utf-8"))
            # Merge hand-curated supplement (famous ships not picked up by the wiki scraper)
            sup_path = os.path.join(DIR, "ships_supplement.json")
            if os.path.exists(sup_path):
                try:
                    sup = json.load(open(sup_path, encoding="utf-8")).get("ships", {})
                    for sn, sr in sup.items():
                        # Don't overwrite scraped data; only add missing
                        if sn not in ship_data or not ship_data[sn].get("found"):
                            ship_data[sn] = sr
                except Exception:
                    pass
            for sname, srec in ship_data.items():
                if not isinstance(srec, dict) or not srec.get("found"): continue
                aff = (srec.get("affiliation", "") or "").strip()
                if not aff: continue
                for crew in _re_for_rank.split(r"\s*[;·]\s*", aff):
                    crew = crew.strip()
                    if not crew: continue
                    ships_by_crew.setdefault(crew, []).append({
                        "name": sname,
                        "debut_chapter": srec.get("debut_chapter"),
                        "status": srec.get("status", ""),
                    })
            # Sort each crew's ships by debut chapter (earliest first)
            for crew in ships_by_crew:
                ships_by_crew[crew].sort(key=lambda s: (s.get("debut_chapter") or 99999, s["name"]))
        except Exception:
            pass

    # Attach ships per crew (by name match)
    for cname, c in crews_doc.get("crews", {}).items():
        if cname in ships_by_crew:
            c["ships"] = ships_by_crew[cname]

    # Load entity_index for chr: / ship: ID resolution
    eidx_path = os.path.join(DIR, "entity_index.json")
    entity_index_raw = {}
    if os.path.exists(eidx_path):
        try:
            entity_index_raw = json.load(open(eidx_path, encoding="utf-8"))
        except Exception:
            pass

    # Build ship name → ship_id map from ships.json
    ship_id_map = {}
    if os.path.exists(ships_path):
        try:
            for sname, srec in json.load(open(ships_path, encoding="utf-8")).items():
                if isinstance(srec, dict) and srec.get("id"):
                    ship_id_map[sname] = srec["id"]
        except Exception:
            pass

    # Enrich each member with role + rank + tier + chr_id; ships with ship_id
    for cname, c in crews_doc.get("crews", {}).items():
        # Annotate ships with ship_id for ?id= routing
        for s in c.get("ships", []):
            sid = ship_id_map.get(s["name"])
            if sid:
                s["ship_id"] = sid

        # Build name → (label, priority) map from curated hierarchy if present
        curated = {}
        for tier in (hierarchies.get(cname, {}) or {}).get("tiers", []):
            for n in tier.get("members", []):
                # First match wins per character (curated order is authoritative)
                if n not in curated:
                    curated[n] = (tier.get("label", ""), int(tier.get("priority", 60)))

        for m in c.get("members", []):
            rec = pr.get(m["name"], {})
            occ = rec.get("occupation", "") or ""
            m["role"] = occ
            m["rank"] = _rank_from_occupation(occ)
            # Debut chapter so crew.html can hide not-yet-debuted members
            # from shielded readers (join dates aren't in the data).
            _fa = rec.get("first_appearance") or ""
            _m = _re.search(r"Chapter\s+(\d+)", _fa, _re.I) if _fa else None
            if _m:
                m["debut"] = int(_m.group(1))
            # Annotate chr_id for ?id= routing
            chr_id = entity_index_raw.get(m["name"].lower())
            if chr_id and chr_id.startswith("chr:"):
                m["chr_id"] = chr_id
            # Tier — curated wins, then status, then default
            if m["name"] in curated:
                label, prio = curated[m["name"]]
                m["tier_label"] = label
                m["tier_priority"] = prio
                m["tier_source"] = "curated"
                # Curated rank-0 tiers also force rank 0 (so the captain star shows)
                if prio == 0:
                    m["rank"] = 0
            else:
                status_lc = (m.get("status") or "").lower().strip()
                m["tier_label"] = _pretty_status(m.get("status"))
                m["tier_priority"] = _status_priority(m.get("status"))
                m["tier_source"] = "status"
            # If member is the named captain field of the crew, force rank 0
            if c.get("captain") and m["name"] in c["captain"]:
                m["rank"] = 0
    payload = json.dumps(crews_doc, ensure_ascii=False)
    for page in ("crews.html", "crew.html"):
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        ok, size = bake_block(path, "crews-data", payload)
        if ok:
            n = len(crews_doc.get("crews", {}))
            print(f"  ✓ {page:<13} ← {n:>4} crews · rank-enriched ({size} KB)")


def _upgrade_portrait_url(url, target_width=300):
    """Upgrade a wikia thumbnail URL to a higher-resolution variant."""
    if not url: return url
    if "/scale-to-width-down/" in url:
        return _re_for_rank.sub(r"/scale-to-width-down/\d+", f"/scale-to-width-down/{target_width}", url)
    # No scale segment yet — splice one in before the query string
    base = url.split("?")[0]
    qs = url[len(base):]
    if "/revision/latest" in base and "/scale-to-width-down/" not in base:
        base = base.replace("/revision/latest", f"/revision/latest/scale-to-width-down/{target_width}", 1)
    return base + qs


_PORTRAIT_OVERRIDE_URLS = None
def _portrait_override_urls():
    global _PORTRAIT_OVERRIDE_URLS
    if _PORTRAIT_OVERRIDE_URLS is not None:
        return _PORTRAIT_OVERRIDE_URLS
    _PORTRAIT_OVERRIDE_URLS = {}
    path = os.path.join(DIR, "portrait_overrides.json")
    if not os.path.exists(path): return _PORTRAIT_OVERRIDE_URLS
    try:
        import requests
    except ImportError:
        return _PORTRAIT_OVERRIDE_URLS
    try:
        doc = json.load(open(path, encoding="utf-8")).get("overrides", {})
    except Exception:
        return _PORTRAIT_OVERRIDE_URLS
    for name, filename in doc.items():
        if not filename: continue
        try:
            r = requests.get("https://onepiece.fandom.com/api.php",
                params={"action":"query","titles":"File:"+filename,
                        "prop":"imageinfo","iiprop":"url",
                        "format":"json","formatversion":"2"},
                headers={"User-Agent":"OPCodexBaker/1.0"},
                timeout=10)
            data = r.json()
            for page in data.get("query", {}).get("pages", []):
                for ii in page.get("imageinfo", []):
                    url = ii.get("url")
                    if url:
                        _PORTRAIT_OVERRIDE_URLS[name] = url
                        break
        except Exception:
            pass
    return _PORTRAIT_OVERRIDE_URLS


def _resolve_portrait(name, original_url):
    """Hand-override (if present) wins over the auto-scraped portrait;
    both end up at 300px for crisp display."""
    overrides = _portrait_override_urls()
    if name in overrides:
        return _upgrade_portrait_url(overrides[name])
    return _upgrade_portrait_url(original_url)


def bake_simple_codex(page, slot_id, data_file):
    """Generic bake for lightweight codex pages — copies a JSON file into a
    <script id="..."> block. Silently returns if either file is missing."""
    pp = os.path.join(DIR, page)
    df = os.path.join(DIR, data_file)
    if not (os.path.exists(pp) and os.path.exists(df)): return
    payload = open(df, encoding="utf-8").read().strip()
    ok, size = bake_block(pp, slot_id, payload)
    if ok: print(f"  ✓ {page:<22} ← {data_file}  ({size} KB)")


def _bake_chr_id_map(page_name, source_json_path):
    """For a LORE page: extract all strings from the source JSON, resolve those
    that match chr: IDs in entity_index, bake the resulting {name: chr_id} map
    into the page as the 'chr-id-map' block.

    The companion chr-link-upgrader.js then reads this at runtime to upgrade
    character.html?name= links → character.html?id= without touching each
    page's render() function.
    """
    page = os.path.join(DIR, page_name)
    src  = source_json_path if os.path.isabs(source_json_path) else os.path.join(DIR, source_json_path)
    if not (os.path.exists(page) and os.path.exists(src)):
        return
    eidx_path = os.path.join(DIR, "entity_index.json")
    if not os.path.exists(eidx_path):
        return
    eidx = json.load(open(eidx_path, encoding="utf-8"))
    data = json.load(open(src, encoding="utf-8"))

    # Walk every string value recursively; filter to plausible display names
    candidates: set[str] = set()
    _BAD_PREFIXES = ('_', 'Ch.', 'http', 'file:', '©', '{', '<')

    def _walk(obj):
        if isinstance(obj, str):
            s = obj.strip()
            if 3 <= len(s) <= 60 and not s.startswith(_BAD_PREFIXES):
                candidates.add(s)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k not in ('_doc', 'generated_on'):
                    _walk(v)

    _walk(data)

    # sorted(): candidates is a set, so unsorted iteration reshuffles this
    # block on every run and every scheduled refresh commits pure churn.
    chr_map = {}
    for name in sorted(candidates):
        eid = eidx.get(name.lower())
        if eid and eid.startswith("chr:"):
            chr_map[name] = eid

    if not chr_map:
        return
    payload = json.dumps(chr_map, ensure_ascii=False, separators=(",", ":"))
    ok, _ = bake_block(page, "chr-id-map", payload)
    if ok:
        print(f"  ✓ {page_name:<22} ← {len(chr_map)} chr IDs mapped")


def _bake_lore_chr_ids():
    """Bake chr-id-map blocks into all LORE pages that have character links."""
    lore_pages = [
        ("haki.html",            "haki.json"),
        ("poneglyphs.html",      "poneglyphs.json"),
        ("void-century.html",    "void-century.json"),
        ("will-of-d.html",       "will-of-d.json"),
        ("ancient-weapons.html", "ancient-weapons.json"),
        ("marines-wg.html",      "marines-wg.json"),
        ("combat-styles.html",   "combat-styles.json"),
        ("reverie.html",         "reverie.json"),
        ("races.html",           "races.json"),
        ("materials.html",       "materials.json"),
        ("items.html",           "items.json"),
        ("tech.html",            "tech.json"),
        ("awakenings.html",      "awakenings.json"),
    ]
    for page, src in lore_pages:
        _bake_chr_id_map(page, src)


def bake_character_forms():
    """Bake character_forms.json into pages that show portraits, so forms.js can read it."""
    src = os.path.join(DIR, "character_forms.json")
    if not os.path.exists(src): return
    payload = open(src, encoding="utf-8").read()
    pages = ("character.html", "characters.html", "crew.html", "heights.html", "compare.html", "home.html")
    n_baked = 0
    for page in pages:
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        # Insert empty slot if page doesn't have one
        text = open(path, encoding="utf-8").read()
        if 'id="character-forms"' not in text:
            slot = '<script id="character-forms" type="application/json">{}</script>\n'
            # Insert before the first <script src= ... > or before </body>
            for marker in ('<script src="settings.js">', '<script src="search.js">', '</body>'):
                if marker in text:
                    text = text.replace(marker, slot + marker, 1)
                    break
            open(path, "w", encoding="utf-8").write(text)
        ok, size = bake_block(path, "character-forms", payload)
        if ok: n_baked += 1
    try:
        n_chars = len(json.loads(payload).get("characters", {}))
    except Exception:
        n_chars = 0
    print(f"  ✓ character forms ← {n_chars} characters baked into {n_baked} pages")


def bake_heights():
    """Bake heights {name: raw_height_string} + portraits into heights.html."""
    page = os.path.join(DIR, "heights.html")
    if not os.path.exists(page): return
    pr_path = os.path.join(DIR, "punk_records.json")
    if not os.path.exists(pr_path): return
    pr = json.load(open(pr_path, encoding="utf-8"))
    heights = {}
    for name, rec in pr.items():
        if not isinstance(rec, dict): continue
        h = (rec.get("height") or "").strip()
        if h: heights[name] = h
    payload = json.dumps(heights, ensure_ascii=False, separators=(',', ':'))
    ok, size = bake_block(page, "height-data", payload)
    if ok:
        print(f"  ✓ heights.html  ← {len(heights):>4} characters with height  ({size} KB)")
    # Also bake portraits into heights.html
    portraits_path = os.path.join(DIR, "portraits.json")
    if os.path.exists(portraits_path):
        portraits_full = json.load(open(portraits_path, encoding="utf-8"))
        portraits_slim = {n: _resolve_portrait(n, p["thumb"]) for n, p in portraits_full.items()
                          if isinstance(p, dict) and p.get("thumb")}
        ppayload = json.dumps(portraits_slim, ensure_ascii=False, separators=(',', ':'))
        bake_block(page, "portraits-data", ppayload)


def bake_voices():
    """Build VA -> [characters] index for voices.html.

    Enriches with chr: IDs from entity_index when available.
    Each character entry is {n: name, id: chr_id_or_null}.
    """
    page = os.path.join(DIR, "voices.html")
    if not os.path.exists(page): return
    pr_path = os.path.join(DIR, "punk_records.json")
    if not os.path.exists(pr_path): return
    pr = json.load(open(pr_path, encoding="utf-8"))

    # Build chr_name -> chr_id from entity_index
    idx_path = os.path.join(DIR, "entity_index.json")
    name_to_id = {}
    if os.path.exists(idx_path):
        idx = json.load(open(idx_path, encoding="utf-8"))
        for k, v in idx.items():
            if isinstance(v, str) and v.startswith("chr:"):
                name_to_id[k] = v

    jp, en = {}, {}
    for name, rec in pr.items():
        if not isinstance(rec, dict): continue
        chr_id = name_to_id.get(name.lower()) or rec.get("id")
        entry = {"n": name, "id": chr_id}
        for raw_va in (rec.get("voice_actor_jp", "") or "").split(";"):
            va = raw_va.strip()
            if not va: continue
            jp.setdefault(va, [])
            if not any(e["n"] == name for e in jp[va]):
                jp[va].append(entry)
        for raw_va in (rec.get("voice_actor_en", "") or "").split(";"):
            va = raw_va.strip()
            if not va: continue
            en.setdefault(va, [])
            if not any(e["n"] == name for e in en[va]):
                en[va].append(entry)
    # Sort each role list alphabetically for stable rendering
    for d in (jp, en):
        for k in list(d.keys()):
            d[k] = sorted(d[k], key=lambda e: e["n"])
    payload = json.dumps({"jp": jp, "en": en}, ensure_ascii=False, separators=(",", ":"))
    ok, size = bake_block(page, "voices-data", payload)
    if ok:
        n_jp = sum(1 for k in jp if k.lower() != "unknown")
        n_en = sum(1 for k in en if k.lower() != "unknown")
        m_jp = sum(1 for k, v in jp.items() if k.lower() != "unknown" and len(v) > 1)
        m_en = sum(1 for k, v in en.items() if k.lower() != "unknown" and len(v) > 1)
        print(f"  ✓ voices.html   <- {n_jp:>4} JP / {n_en:>4} EN VAs · {m_jp} / {m_en} multi-role  ({size} KB)")
def bake_timeline():
    """Timeline page reuses arcs + canon_facts (already baked elsewhere)."""
    page = os.path.join(DIR, "timeline.html")
    if not os.path.exists(page): return
    arcs_path = os.path.join(DIR, "arcs.json")
    facts_path = os.path.join(DIR, "canon_facts.json")
    if os.path.exists(arcs_path):
        bake_block(page, "arcs-data", open(arcs_path, encoding="utf-8").read())
    if os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as f:
            facts_list = json.load(f)
        # Slim — only first_appearance facts (timeline only uses those)
        slim = {}
        for fact in facts_list:
            if fact.get("predicate") == "first_appearance":
                slim.setdefault(fact["subject"], []).append({
                    "predicate": fact["predicate"],
                    "value":     fact["value"],
                })
        bake_block(page, "canon-facts-data",
                   json.dumps(slim, ensure_ascii=False, separators=(',', ':')))
    print(f"  ✓ timeline.html ← arcs + first-appearance facts")


def bake_heatmap():
    page = os.path.join(DIR, "heatmap.html")
    facts_path = os.path.join(DIR, "canon_facts.json")
    if not (os.path.exists(page) and os.path.exists(facts_path)): return
    with open(facts_path, encoding="utf-8") as f:
        facts_list = json.load(f)
    # Slim — only the manga-source citations matter for the heatmap
    slim = {}
    for fact in facts_list:
        for s in (fact.get("sources") or []):
            if s.get("type") == "manga" and isinstance(s.get("chapter"), int):
                slim.setdefault(fact["subject"], []).append({
                    "predicate": fact["predicate"],
                    "sources": [{"type": "manga", "chapter": s["chapter"]}],
                })
                break  # one per fact is enough
    payload = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    ok, size = bake_block(page, "canon-facts-data", payload)
    if ok: print(f"  ✓ heatmap.html  ← {len(slim):,} char-fact maps ({size} KB)")


def bake_sbs_topics():
    page = os.path.join(DIR, "sbs-topics.html")
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    if not (os.path.exists(page) and os.path.exists(sbs_path)): return
    with open(sbs_path, encoding="utf-8") as f:
        sbs = json.load(f)
    # Slim — only fields needed for topic browsing
    slim = [{"id_num": e.get("id_num"), "volume": e.get("volume"),
             "category": e.get("category"),
             "question": (e.get("question") or "")[:200]}
            for e in sbs if e.get("id_num") is not None]
    payload = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    ok, size = bake_block(page, "sbs-data", payload)
    if ok: print(f"  ✓ sbs-topics.html ← {len(slim):,} Q&As (slim, {size} KB)")


def bake_arcs():
    src = os.path.join(DIR, "arcs.json")
    page = os.path.join(DIR, "arcs.html")
    if not (os.path.exists(src) and os.path.exists(page)): return
    payload = open(src, encoding="utf-8").read()
    ok, size = bake_block(page, "arcs-data", payload)
    if ok:
        try:
            n = len(json.loads(payload))
            print(f"  ✓ arcs.html     ← {n:>4} arcs ({size} KB)")
        except Exception: pass


def bake_bounties():
    """Bake punk-records + portraits + canon-facts into the bounty wall."""
    pr_path = os.path.join(DIR, "punk_records.json")
    portraits_path = os.path.join(DIR, "portraits.json")
    facts_path = os.path.join(DIR, "canon_facts.json")
    page = os.path.join(DIR, "bounties.html")
    if not os.path.exists(page) or not os.path.exists(pr_path): return

    with open(pr_path, encoding="utf-8") as f:
        pr = json.load(f)
    # Slim punk records to just what the wall renders (saves ~80% payload)
    slim = []
    for name, rec in pr.items():
        if not rec.get("found"): continue
        if not rec.get("bounty") and not rec.get("bounty_value"): continue
        slim.append({
            "name":         name,
            "epithet":      rec.get("epithet"),
            "affiliation":  rec.get("affiliation"),
            "bounty":       rec.get("bounty"),
            "bounty_value": rec.get("bounty_value"),
            "first_appearance": rec.get("first_appearance"),
        })
    payload = json.dumps(slim, ensure_ascii=False, separators=(',', ':'))
    ok, size = bake_block(page, "punk-records-data", payload)
    if ok: print(f"  ✓ bounties.html ← {len(slim):>4} bounties  ({size} KB)")

    if os.path.exists(portraits_path):
        with open(portraits_path, encoding="utf-8") as f:
            portraits_full = json.load(f)
        portraits_slim = {n: _resolve_portrait(n, p["thumb"]) for n, p in portraits_full.items()
                          if isinstance(p, dict) and p.get("thumb")}
        # Only include portraits for the bountied characters (cuts ~600KB)
        bountied_names = {s["name"] for s in slim}
        relevant_portraits = {n: u for n, u in portraits_slim.items() if n in bountied_names}
        bake_block(page, "portraits-data",
                   json.dumps(relevant_portraits, ensure_ascii=False, separators=(',', ':')))

    if os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as f:
            facts_list = json.load(f)
        # Only first_appearance facts for bountied chars (for chronological sort)
        bountied = {s["name"] for s in slim}
        facts_by_subj = {}
        for fact in facts_list:
            if fact.get("subject") in bountied and fact.get("predicate") == "first_appearance":
                facts_by_subj.setdefault(fact["subject"], []).append(fact)
        bake_block(page, "canon-facts-data",
                   json.dumps(facts_by_subj, ensure_ascii=False, separators=(',', ':')))


def _build_eaters_index():
    """Return a fruit_id-keyed dict of eater rows from the ate-fruit shard.

    Each row is annotated with _display (character display name) so the JS
    renderer can show human-readable labels without a separate lookup.
    Returns {} if the shard or query layer is unavailable.
    """
    scripts_dir = os.path.join(DIR, "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        from lib import query as _q
    except ImportError:
        return {}
    shard_path = os.path.join(DIR, "relationships", "ate-fruit.json")
    if not os.path.exists(shard_path):
        return {}
    name_map = _q._name_index()   # id -> display name
    out = {}
    try:
        rows = _q.by_to("ate-fruit")   # fruit_id -> [rows]
    except Exception:
        return {}
    for fruit_id, fruit_rows in rows.items():
        annotated = []
        for row in fruit_rows:
            r = dict(row)
            dn = name_map.get(r.get("from"))
            if dn:
                r["_display"] = dn
            annotated.append(r)
        out[fruit_id] = annotated
    return out


def bake_fruits():
    src = os.path.join(DIR, "devil_fruits.json")
    if not os.path.exists(src): return
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    for page in ("fruits.html", "fruit.html"):
        path = os.path.join(DIR, page)
        if not os.path.exists(path): continue
        ok, size = bake_block(path, "fruits-data", payload)
        if ok:
            n = sum(1 for v in data.values() if isinstance(v, dict) and v.get("found"))
            print(f"  ✓ {page:<13} ← {n:>4} fruits  ({size} KB)")

    # Bake eaters index into fruit.html only (individual profile page)
    fruit_page = os.path.join(DIR, "fruit.html")
    if os.path.exists(fruit_page):
        eaters = _build_eaters_index()
        if eaters:
            ep = json.dumps(eaters, ensure_ascii=False, separators=(',', ':'))
            ok, size = bake_block(fruit_page, "eaters-data", ep)
            if ok:
                total = sum(len(v) for v in eaters.values())
                print(f"  ✓ fruit.html     ← {total:>4} eater rows  ({size} KB)")

    # Bake current-eater chr: links into fruits.html (index page cards)
    fruits_page = os.path.join(DIR, "fruits.html")
    if os.path.exists(fruits_page):
        eaters = _build_eaters_index()
        current_map = {}
        for fruit_id, rows in eaters.items():
            # prefer current=True rows; fall back to any row if no explicit current flag
            current_rows = [r for r in rows if r.get("current") is not False]
            if not current_rows:
                current_rows = rows
            if current_rows:
                r = current_rows[0]
                current_map[fruit_id] = {"id": r.get("from"), "name": r.get("_display", r.get("from"))}
        if current_map:
            cp = json.dumps(current_map, ensure_ascii=False, separators=(",", ":"))
            ok, _ = bake_block(fruits_page, "fruit-current-eaters", cp)
            if ok:
                print(f"  ✓ fruits.html    ← {len(current_map):>4} current eater links")


def bake_conflicts():
    src = os.path.join(DIR, "docs", "conflicts.json")
    page = os.path.join(DIR, "conflicts.html")
    if not (os.path.exists(src) and os.path.exists(page)): return
    with open(src, encoding="utf-8") as f:
        payload = f.read()
    ok, size = bake_block(page, "conflicts-data", payload)
    if ok:
        try:
            n = json.loads(payload).get("total", 0)
            print(f"  ✓ conflicts.html  ← {n:,} conflict(s) ({size} KB)")
        except Exception:
            print(f"  ✓ conflicts.html  ← (payload baked, {size} KB)")


def bake_workbench():
    cards = _build_workbench_index()
    payload = json.dumps(cards, ensure_ascii=False, separators=(',', ':'))

    page = "workbench.html"
    path = os.path.join(DIR, page)
    if not os.path.exists(path):
        return

    ok, size = bake_block(path, "workbench-cards", payload)
    if ok:
        by_type = Counter(c["type"] for c in cards)
        print(f"  ✓ {page:<15} ← {len(cards):>5,} cards  ({size} KB)")
        print(f"    breakdown: " + " · ".join(f"{k}:{v}" for k, v in by_type.most_common()))

    # Phase D: bake canon_facts (subject-keyed) into workbench + prove pages
    facts_path = os.path.join(DIR, "canon_facts.json")
    if os.path.exists(facts_path):
        with open(facts_path, encoding="utf-8") as f:
            facts_list = json.load(f)
        facts_by_subject = {}
        for fact in facts_list:
            facts_by_subject.setdefault(fact["subject"], []).append(fact)
        # Slim — drop bulky chapter lists from total_appearance_count
        for subj, facts in facts_by_subject.items():
            for f in facts:
                if f.get("predicate") == "total_appearance_count":
                    for src in f.get("sources", []):
                        if "chapters" in src and len(src["chapters"]) > 5:
                            src["chapter_range"] = f"{min(src['chapters'])}-{max(src['chapters'])}"
                            del src["chapters"]
        wb_facts_payload = json.dumps(facts_by_subject, ensure_ascii=False, separators=(",", ":"))
        ok2, size2 = bake_block(path, "canon-facts-data", wb_facts_payload)
        if ok2:
            print(f"  ✓ {page:<15} ← canon facts for Inspect ({size2} KB)")

        # Same payload also into prove.html (the standalone tester)
        prove_path = os.path.join(DIR, "prove.html")
        if os.path.exists(prove_path):
            ok3, size3 = bake_block(prove_path, "canon-facts-data", wb_facts_payload)
            if ok3:
                print(f"  ✓ prove.html      ← canon facts ({size3} KB)")
            # Build alias map: lowercase variant → canonical CANON_FACTS key.
            # Lets users type "Kaido", "Big Mom", "Whitebeard" etc and have
            # them resolve to the keyed subject ("Kaidou", "Charlotte Linlin", "Edward Newgate").
            fact_keys = set(facts_by_subject.keys())
            alias_map = {k.lower(): k for k in fact_keys}  # self-map first
            ca_path = os.path.join(DIR, "character_aliases.json")
            if os.path.exists(ca_path):
                with open(ca_path, encoding="utf-8") as f:
                    ca = json.load(f)
                for canonical, aliases in ca.items():
                    if canonical.startswith("_"):
                        continue
                    # Find which name in (canonical, *aliases) is the actual fact key
                    candidates = [canonical] + list(aliases)
                    target = next((c for c in candidates if c in fact_keys), None)
                    if not target:
                        # Try case-insensitive match
                        lc_keys = {k.lower(): k for k in fact_keys}
                        target = next((lc_keys[c.lower()] for c in candidates if c.lower() in lc_keys), None)
                    if not target:
                        continue
                    for variant in candidates:
                        alias_map[variant.lower()] = target
            # Sorted so the block is byte-stable: alias_map is populated via
            # set-backed lookups, so an unsorted dump reshuffles identical data
            # every run and every scheduled refresh commits pure churn.
            alias_map = dict(sorted(alias_map.items()))
            alias_payload = json.dumps(alias_map, ensure_ascii=False, separators=(",", ":"))
            ok_a, size_a = bake_block(prove_path, "aliases-map", alias_payload)
            if ok_a:
                print(f"  ✓ prove.html      ← {len(alias_map):,} alias mappings ({size_a} KB)")
            # Bake the character names list for autocomplete — canonical
            # keys plus any aliases we resolved, so users see both.
            extra_aliases = [k for k in alias_map.keys() if alias_map[k].lower() != k]
            extra_proper = sorted({k.title() if k.islower() else k for k in extra_aliases})
            chars_list = sorted(set(fact_keys) | set(extra_proper))
            chars_payload = json.dumps(chars_list, ensure_ascii=False, separators=(",", ":"))
            ok4, size4 = bake_block(prove_path, "characters-list", chars_payload)
            if ok4:
                print(f"  ✓ prove.html      ← {len(chars_list):,} character names ({size4} KB)")


def _bake_home_stats():
    """Bake pre-computed stats into home.html as home-stats JSON block.

    Replaces the async-fetch + localStorage cascade with instant baked values.
    The existing async fetches remain as background refresh but no longer race
    the initial render — visitors see real numbers on first load.
    """
    page = os.path.join(DIR, "home.html")
    if not os.path.exists(page):
        return

    import csv as _csv_mod

    def _fmt(n): return f"{n:,}"

    stats = {}

    # appearances.csv → chapters, chars, rows
    csv_path = os.path.join(DIR, "appearances.csv")
    if os.path.exists(csv_path):
        chapters, chars, rows = set(), set(), 0
        with open(csv_path, encoding="utf-8") as f:
            reader = _csv_mod.DictReader(f)
            for row in reader:
                rows += 1
                try: chapters.add(int(row["chapter"]))
                except (KeyError, ValueError): pass
                n = row.get("name", "").strip()
                if n: chars.add(n)
        stats["chapters"] = _fmt(len(chapters))
        stats["fsMap"] = (f"<strong>{_fmt(rows)}</strong> appearance entries"
                          f" · <strong>{_fmt(len(chars))}</strong> characters")

    # sbs_archive.json
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    if os.path.exists(sbs_path):
        with open(sbs_path, encoding="utf-8") as f:
            sbs = json.load(f)
        vols = len({s.get("volume") for s in sbs if s.get("volume")})
        cats = len({s.get("category") for s in sbs if s.get("category")})
        stats["sbs"]        = _fmt(len(sbs))
        stats["sbs_volumes"] = str(vols)
        stats["fsSbs"] = (f"<strong>{_fmt(len(sbs))}</strong> Q&amp;A"
                          f" · <strong>{vols}</strong> volumes"
                          f" · <strong>{cats}</strong> categories")

    # theories_import.json
    # Theory Forge pulled from the public surface 2026-07-13 — no longer
    # baked into home-stats (the home tile + feature card were removed).

    # punk_records.json
    pr_path = os.path.join(DIR, "punk_records.json")
    if os.path.exists(pr_path):
        with open(pr_path, encoding="utf-8") as f:
            pr = json.load(f)
        pr_recs = [r for r in pr.values() if isinstance(r, dict)]
        pr_total = len(pr_recs)
        pr_found = sum(1 for r in pr_recs if r.get("found"))
        stats["characters"] = _fmt(pr_total)
        stats["fsPunk"] = (f"<strong>{_fmt(pr_total)}</strong> characters"
                           f" · <strong>{_fmt(pr_found)}</strong> with full canon data")

    # awakenings.json
    aw_path = os.path.join(DIR, "awakenings.json")
    if os.path.exists(aw_path):
        with open(aw_path, encoding="utf-8") as f:
            aw = json.load(f)
        n_aw = len(aw.get("awakenings", []))
        stats["fsAwakenings"] = f"<strong>{n_aw}</strong> awakenings tracked · type-coded"

    # workbench card count
    try:
        cards = _build_workbench_index()
        stats["fsWorkbench"] = (f"<strong>{_fmt(len(cards))}</strong>"
                                f" Fact Cards across SBS · characters · theories · covers")
    except Exception:
        pass

    # ships.json
    ships_path = os.path.join(DIR, "ships.json")
    if os.path.exists(ships_path):
        with open(ships_path, encoding="utf-8") as f:
            ships_j = json.load(f)
        ships_found = sum(1 for v in ships_j.values() if isinstance(v, dict) and v.get("found"))
        stats["ships"]   = _fmt(ships_found)
        stats["fsShips"] = f"<strong>{ships_found}</strong> named canon ships"

    # voices — count unique JP / EN VAs from punk_records
    if os.path.exists(pr_path):
        if "pr" not in dir():
            with open(pr_path, encoding="utf-8") as f:
                pr = json.load(f)
        jp_vas, en_vas = set(), set()
        for rec in pr.values():
            if not isinstance(rec, dict): continue
            for va in (rec.get("voice_actor_jp") or "").split(";"):
                va = va.strip()
                if va and va.lower() != "unknown": jp_vas.add(va)
            for va in (rec.get("voice_actor_en") or "").split(";"):
                va = va.strip()
                if va and va.lower() != "unknown": en_vas.add(va)
        stats["voices"]   = _fmt(len(jp_vas) + len(en_vas))
        stats["fsVoices"] = (f"<strong>{len(jp_vas)}</strong> JP"
                             f" · <strong>{len(en_vas)}</strong> EN voice actors")

    # locations.json
    loc_path = os.path.join(DIR, "locations.json")
    if os.path.exists(loc_path):
        with open(loc_path, encoding="utf-8") as f:
            locs = json.load(f)
        locs_found = sum(1 for v in locs.values() if isinstance(v, dict) and v.get("found"))
        stats["locations"] = _fmt(locs_found)
        stats["fsLocs"]    = f"<strong>{locs_found}</strong> locations across the seas"

    # crews.json
    crews_path = os.path.join(DIR, "crews.json")
    if os.path.exists(crews_path):
        with open(crews_path, encoding="utf-8") as f:
            crews_j = json.load(f)
        crews_count = len(crews_j.get("crews", {}))
        stats["crews"] = _fmt(crews_count)

    payload = json.dumps(stats, ensure_ascii=False, separators=(",", ":"))
    ok, size = bake_block(page, "home-stats", payload)
    if ok:
        print(f"  ✓ home.html     <- {len(stats)} stat fields baked ({size} KB)")

    # Sync the static fallbacks that sit inside the stat tiles. JS overwrites
    # these from the block above the moment it runs, but crawlers and link
    # previews read the raw HTML -- leaving them stale publishes wrong numbers.
    _sync_home_stat_fallbacks(page, stats)


# Which hardcoded span maps to which baked stat field.
_HOME_STAT_IDS = {
    "s-chapters":  "chapters",
    "s-characters": "characters",
    "s-sbs":       "sbs",
    "s-crews":     "crews",
    "s-ships":     "ships",
    "s-locations": "locations",
    "s-voices":    "voices",
}


def _sync_home_stat_fallbacks(page, stats):
    """Rewrite <div id="s-xxx">NNN</div> in place to match the baked stats."""
    import re
    try:
        with open(page, encoding="utf-8") as f:
            html = f.read()
    except OSError:
        return

    changed = 0
    for el_id, field in _HOME_STAT_IDS.items():
        value = stats.get(field)
        if not value:
            continue
        pattern = re.compile(r'(id="%s"[^>]*>)([^<]*)(</)' % re.escape(el_id))
        m = pattern.search(html)
        if not m or m.group(2) == value:
            continue
        html = html[:m.start(2)] + value + html[m.end(2):]
        changed += 1

    if changed:
        with open(page, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  ✓ home.html     <- {changed} static stat fallback(s) synced")


def _bake_chr_debut_map_for_gating():
    """Generate chr-debut-map.json — slim {name: debut_chapter} sourced from
    punk_records.json `first_appearance`. Loaded by spoiler.js for site-wide
    per-character gating on index pages that render character names without
    embedding per-row debut info (crews, ships, locations, voices, families,
    bounties, heights, compare, workbench, jolly-rogers).
    """
    pr_path = os.path.join(DIR, "punk_records.json")
    out_path = os.path.join(DIR, "chr-debut-map.json")
    if not os.path.exists(pr_path):
        return
    import re as _re
    pat = _re.compile(r"Chapter\s+(\d+)", _re.I)
    with open(pr_path, encoding="utf-8") as f:
        pr = json.load(f)
    out = {}
    for k, v in pr.items():
        if not isinstance(v, dict):
            continue
        fa = v.get("first_appearance", "")
        m = pat.search(fa) if fa else None
        if not m:
            continue
        try:
            ch = int(m.group(1))
        except ValueError:
            continue
        if ch > 0:
            out[k] = ch
            ne = v.get("name_en")
            if ne and ne != k:
                clean = ne.split(";")[0].strip()
                if clean and clean not in out:
                    out[clean] = ch
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = os.path.getsize(out_path) // 1024
    print(f"  ✓ chr-debut-map.json     <- {len(out)} names baked ({size_kb} KB)")


def _bake_spoiler_latest():
    """Sync spoiler.js LATEST_PUBLISHED_CHAPTER to the max chapter in
    appearances.csv. This constant is the Spoiler Shield's caught-up clamp
    ("I'm caught up" button, cutoff top-bound); before this pass it was a
    hand-bumped literal and went stale the week after every release.
    """
    csv_path = os.path.join(DIR, "appearances.csv")
    js_path  = os.path.join(DIR, "spoiler.js")
    if not (os.path.exists(csv_path) and os.path.exists(js_path)):
        return
    latest = 0
    with open(csv_path, encoding="utf-8") as f:
        next(f, None)  # header
        for line in f:
            ch = line.split(",", 1)[0]
            if ch.isdigit() and int(ch) > latest:
                latest = int(ch)
    if latest <= 0:
        return
    import re as _re
    with open(js_path, encoding="utf-8") as f:
        js = f.read()
    pat = _re.compile(r"(const LATEST_PUBLISHED_CHAPTER = )(\d+)(;)")
    m = pat.search(js)
    if not m:
        print("  ⚠ spoiler.js: LATEST_PUBLISHED_CHAPTER line not found — skipped")
        return
    old = int(m.group(2))
    if old == latest:
        print(f"  = spoiler.js             LATEST_PUBLISHED_CHAPTER already {latest}")
        return
    if latest < old:
        # appearances.csv should only ever grow; a lower max means the CSV is
        # damaged/truncated — never wind the clamp backwards off bad data.
        print(f"  ⚠ spoiler.js: csv max {latest} < current {old} — refusing to lower")
        return
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(pat.sub(rf"\g<1>{latest}\g<3>", js, count=1))
    print(f"  ✓ spoiler.js             LATEST_PUBLISHED_CHAPTER {old} -> {latest}")


def _bake_home_arc_ranges():
    """Bake compact arc-range lookup into home.html as home-arcs JSON block.

    Array of {n, s, e} objects — arc name, start chapter, end chapter.
    Used by the Today in Canon card to show which arc a chapter belongs to.
    """
    page = os.path.join(DIR, "home.html")
    arcs_path = os.path.join(DIR, "arcs.json")
    if not os.path.exists(page) or not os.path.exists(arcs_path):
        return
    with open(arcs_path, encoding="utf-8") as f:
        arcs = json.load(f)
    compact = [{"n": a["name"], "s": a["start"], "e": a["end"]} for a in arcs
               if isinstance(a, dict) and "name" in a]
    payload = json.dumps(compact, separators=(",", ":"))
    ok, size = bake_block(page, "home-arcs", payload)
    if ok:
        print(f"  ✓ home.html     <- arc ranges baked ({len(compact)} arcs, {size} KB)")


def _bake_atlas_events():
    """Bake chapter event maps into atlas.html (debuts, devil fruits, iconic moments).

    Three blocks: atlas-debuts, atlas-fruits, atlas-moments.
    Each is a {chapterNumber: [string, ...]} JSON object.
    """
    page = os.path.join(DIR, "atlas.html")
    if not os.path.exists(page):
        return

    # id → canonical name from punk_records
    pr_path = os.path.join(DIR, "punk_records.json")
    id_to_name: dict = {}
    if os.path.exists(pr_path):
        with open(pr_path, encoding="utf-8") as f:
            pr = json.load(f)
        for k, v in pr.items():
            if isinstance(v, dict) and v.get("id"):
                raw = v.get("name_en") or v.get("name") or k
                id_to_name[v["id"]] = raw.split(";")[0].strip()

    # fruit id → name from entity_index (first short ascii alias)
    eidx_path = os.path.join(DIR, "entity_index.json")
    fruit_id_to_name: dict = {}
    if os.path.exists(eidx_path):
        with open(eidx_path, encoding="utf-8") as f:
            eidx = json.load(f)
        for alias, eid in eidx.items():
            if isinstance(eid, str) and eid.startswith("fruit:") and eid not in fruit_id_to_name:
                if not alias.startswith("fruit:") and alias.isascii() and len(alias) > 3:
                    fruit_id_to_name[eid] = alias

    # Debut map: chapter → [name, ...]
    # Source: punk_records.json `first_appearance` field (wiki-scraped, authoritative).
    # We deliberately do NOT use relationships/debuts-in.json here — that shard is
    # derived from appearances.csv via canon_facts, and the CSV has incomplete
    # coverage for ~52 characters whose only CSV row is a much later chapter
    # (e.g. Lilith CSV-row=Ch.1181 but real wiki debut=Ch.1061; Broggy CSV-row=Ch.1181
    # flashback but real debut=Ch.116 Little Garden). Wiki first_appearance is the
    # source of truth for "what chapter does this character debut in".
    import re as _re
    _ch_pat = _re.compile(r"Chapter\s+(\d+)", _re.I)
    # Strip wiki-style trailing parentheticals like " (VIZ, Odex)", " (anime)", " (artificial)" etc.
    _paren_pat = _re.compile(r"\s*\([^)]*\)\s*$")
    debut_map: dict = {}
    if os.path.exists(pr_path):
        # Use a set per chapter to dedupe characters that appear under multiple
        # punk_records keys (e.g. "Broggy" and "Brogy" both pointing at chr:01700).
        seen_per_chapter: dict = {}
        for k, rec in pr.items():
            if not isinstance(rec, dict):
                continue
            fa = rec.get("first_appearance", "")
            if not fa:
                continue
            m = _ch_pat.search(fa)
            if not m:
                continue
            try:
                ch = int(m.group(1))
            except ValueError:
                continue
            if ch <= 0:
                continue
            raw = rec.get("name_en") or rec.get("name") or k
            name = raw.split(";")[0].strip()
            # Strip wiki-style trailing parentheticals
            name = _paren_pat.sub("", name).strip()
            # Prefer the record key if it's cleaner (no parentheses or slashes)
            if "/" in name or "(" in name:
                if "/" not in k and "(" not in k:
                    name = k
            if not name:
                continue
            seen = seen_per_chapter.setdefault(ch, set())
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            debut_map.setdefault(ch, []).append(name)
        debut_map = {k: v[:8] for k, v in debut_map.items()}

    # Fruit map: chapter → ["Name — fruit_name", ...]
    ate_path = os.path.join(DIR, "relationships", "ate-fruit.json")
    fruit_map: dict = {}
    if os.path.exists(ate_path):
        with open(ate_path, encoding="utf-8") as f:
            ate = json.load(f)
        for r in ate:
            ch_raw = str(r.get("chapter", ""))
            if not ch_raw.startswith("ch:"):
                continue
            try:
                ch = int(ch_raw[3:])
            except ValueError:
                continue
            if ch <= 0:
                continue
            char_name = id_to_name.get(r["from"], r["from"])
            fruit_name = fruit_id_to_name.get(r["to"], r["to"])
            fruit_map.setdefault(ch, []).append(f"{char_name} — {fruit_name}")

    # Moments map: chapter → [title, ...]
    moments_path = os.path.join(DIR, "moments.json")
    moment_map: dict = {}
    if os.path.exists(moments_path):
        with open(moments_path, encoding="utf-8") as f:
            moments_data = json.load(f)
        for m in moments_data.get("moments", []):
            ch = m.get("chapter")
            if ch:
                moment_map.setdefault(ch, []).append(m["title"])

    def _bake(block_id: str, data: dict) -> None:
        payload = json.dumps({str(k): v for k, v in data.items()},
                             ensure_ascii=False, separators=(",", ":"))
        ok, size = bake_block(page, block_id, payload)
        if ok:
            print(f"  ✓ atlas.html    <- {block_id} baked ({len(data)} chapters, {size} KB)")

    _bake("atlas-debuts",  debut_map)
    _bake("atlas-fruits",  fruit_map)
    _bake("atlas-moments", moment_map)


def _bake_release_map():
    """Bake chapter_dates.json + episode_dates.json + release_events.json + arc summary
    into the four data blocks on chapter-release-map.html.
    """
    page = os.path.join(DIR, "chapter-release-map.html")
    if not os.path.exists(page):
        return

    def _bake_kv(block_id: str, data) -> None:
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        ok, size = bake_block(page, block_id, payload)
        if ok:
            print(f"  ✓ chapter-release-map.html <- {block_id} baked ({size} KB)")

    # Chapter dates (compact: chapter -> {date, volume, approximate})
    cd_path = os.path.join(DIR, "chapter_dates.json")
    if os.path.exists(cd_path):
        with open(cd_path, encoding="utf-8") as f:
            cd = json.load(f)
        # Slim shape: keep only date + volume + approximate flag per chapter
        slim_chapters = {
            ch: {"date": v["date"], "volume": v.get("volume"), "approximate": v.get("approximate", False)}
            for ch, v in cd.get("chapters", {}).items()
        }
        _bake_kv("release-chapters", slim_chapters)

    # Episode dates
    ed_path = os.path.join(DIR, "episode_dates.json")
    if os.path.exists(ed_path):
        with open(ed_path, encoding="utf-8") as f:
            ed = json.load(f)
        slim_episodes = {
            ep: {"date": v["date"], "season": v.get("season"), "approximate": v.get("approximate", False)}
            for ep, v in ed.get("episodes", {}).items()
        }
        _bake_kv("release-episodes", slim_episodes)

    # Events (films + milestones + sagas etc.)
    rev_path = os.path.join(DIR, "release_events.json")
    if os.path.exists(rev_path):
        with open(rev_path, encoding="utf-8") as f:
            rev = json.load(f)
        _bake_kv("release-events", {"events": rev.get("events", []), "kinds": rev.get("kinds", {})})

    # Arc summary (just name + start/end chapters)
    arcs_path = os.path.join(DIR, "arcs.json")
    if os.path.exists(arcs_path):
        with open(arcs_path, encoding="utf-8") as f:
            arcs = json.load(f)
        compact = [
            {"name": a["name"], "start": a["start"], "end": a["end"]}
            for a in arcs if isinstance(a, dict) and "name" in a
        ]
        _bake_kv("release-arcs", compact)


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    targets = [t.lower() for t in sys.argv[1:]]
    do_sbs  = (not targets) or "sbs" in targets
    do_csv  = (not targets) or "csv" in targets
    do_punk = (not targets) or "punk" in targets or "characters" in targets
    do_wb   = (not targets) or "workbench" in targets

    print("=" * 55)
    print("  Bake — embedding data into HTML pages")
    print("=" * 55)
    print()

    if do_csv:  bake_csv()
    if do_sbs:  bake_sbs()
    if do_punk: bake_punk()
    if do_wb:   bake_workbench()
    bake_arcs()       # always run — small + cheap
    bake_fruits()     # always run — small + cheap
    bake_bounties()   # always run — small + cheap
    bake_conflicts()  # always run — small + cheap
    bake_crews()      # always run — small + cheap
    bake_voices()     # voice actor index from punk_records
    bake_heights()    # height wall data
    bake_character_forms()  # character_forms.json → all pages with portraits
    # Lightweight codex pages
    bake_simple_codex("sagas.html",         "sagas-data",   "sagas.json")
    bake_simple_codex("will-of-d.html",     "will-data",    "will-of-d.json")
    bake_simple_codex("jolly-rogers.html",  "rogers-data",  "jolly_rogers.json")
    bake_simple_codex("jolly-rogers.html",  "crews-data",   "crews.json")
    bake_simple_codex("haki.html",            "haki-data",      "haki.json")
    bake_simple_codex("combat-styles.html",   "combat-data",    "combat-styles.json")
    bake_simple_codex("races.html",           "races-data",     "races.json")
    bake_simple_codex("items.html",           "items-data",     "items.json")
    bake_simple_codex("materials.html",       "materials-data", "materials.json")
    bake_simple_codex("tech.html",            "tech-data",      "tech.json")
    bake_simple_codex("weapons.html",         "weapons-data",   "weapons.json")
    _bake_weapon_owns("weapons.html")
    bake_simple_codex("ancient-weapons.html", "ancient-data",   "ancient-weapons.json")
    bake_simple_codex("marines-wg.html",      "marines-data",   "marines-wg.json")
    bake_simple_codex("poneglyphs.html",      "poneglyphs-data","poneglyphs.json")
    bake_simple_codex("void-century.html",    "void-data",      "void-century.json")
    bake_simple_codex("bounties.html",        "poster-styles-data", "bounty_poster_styles.json")
    bake_simple_codex("reverie.html",         "reverie-data",   "reverie.json")
    bake_simple_codex("music.html",           "music-data",     "music.json")
    bake_simple_codex("moments.html",         "moments-data",   "moments.json")
    bake_simple_codex("episodes.html",        "episodes-data",  "episodes.json")
    bake_timeline()   # always run — small + cheap
    bake_heatmap()    # always run — small + cheap
    bake_sbs_topics() # always run — small + cheap
    bake_locations()  # always run — small + cheap
    bake_families()   # always run — small + cheap
    bake_compare()    # always run — small + cheap
    bake_ships()      # always run — small + cheap
    bake_awakenings() # always run — small + cheap
    bake_timeline_events() # always run — small + cheap
    _bake_lore_chr_ids()  # chr-id-map blocks for LORE pages (enables chr-link-upgrader.js)
    _bake_home_stats()        # pre-computed stats → home.html (instant display, no async flicker)
    _bake_home_arc_ranges()   # arc chapter ranges → Today in Canon context line
    _bake_chr_debut_map_for_gating()  # name→debut map → Spoiler Shield filter helper on index pages
    _bake_spoiler_latest()    # sync spoiler.js caught-up clamp to latest scraped chapter
    _bake_atlas_events()      # chapter event maps → atlas.html (debuts, fruits, moments)
    _bake_release_map()       # release-date timeline → chapter-release-map.html

    # Linkify must run AFTER bake_punk (uses Punk Records to build the index)
    if do_sbs:  bake_linkified_sbs()
    if (not targets) or "theories" in targets: bake_linkified_theories()

    print()
    print("  All pages now self-contained — open directly in browser,")
    print("  no local server needed.")
    print("=" * 55)


if __name__ == "__main__":
    main()
