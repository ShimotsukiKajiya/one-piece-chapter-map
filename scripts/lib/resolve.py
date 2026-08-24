"""Character-name resolution over the Codex's alias index.

Curated lore files name characters loosely -- "Vinsmoke Sanji", "Zeff (former)",
"Sakazuki (Akainu)", "Kawamatsu the Kappa" -- while `punk_records.json` keys on a
single canonical form ("Sanji", "Zeff", "Sakazuki", "Kawamatsu"). Exact matching
silently fails on these, which is how entries ended up undatable and therefore
hidden from every reader.

`entity_index.json` already holds 11,893 alias -> entity-id mappings for exactly
this problem. This module is the shared way to use it, so every audit script
resolves names the same way rather than each inventing its own matcher.

Also fixes the name-form mismatch class found in the 2026-08 audit
(Koby/Coby, Fukurou/Fukuro, T Bone/T-Bone, Nerona Imu/Imu).

    from lib.resolve import Resolver
    r = Resolver(root)
    r.debut_chapter("Vinsmoke Sanji")   # -> 1
    r.canonical("Sakazuki (Akainu)")    # -> "Sakazuki"
"""
import json
import os
import re
import unicodedata


def normalise(s):
    """Casefold, strip diacritics and punctuation. 'T-Bone' == 'T Bone'."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _variants(name):
    """Progressively looser forms of a name, most specific first."""
    seen, out = set(), []

    def add(v):
        v = (v or "").strip(" .,-–—")
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)

    add(name)
    # "Zeff (former)" / "Sakazuki (Akainu)" -> "Zeff" / "Sakazuki"
    add(re.sub(r"\s*\([^)]*\)", "", name))
    # "Kawamatsu the Kappa" -> "Kawamatsu"
    add(re.split(r"\s+the\s+", name, flags=re.I)[0])
    # "Rob Lucci, CP9" -> "Rob Lucci"
    add(name.split(",")[0])
    # strip a leading family name: "Vinsmoke Sanji" -> "Sanji"
    parts = re.sub(r"\s*\([^)]*\)", "", name).split()
    if len(parts) > 1:
        add(parts[-1])
    return out


class Resolver:
    def __init__(self, root):
        self.root = root
        with open(os.path.join(root, "entity_index.json"), encoding="utf-8") as f:
            raw_index = json.load(f)
        with open(os.path.join(root, "punk_records.json"), encoding="utf-8") as f:
            pr = json.load(f)

        # alias (normalised) -> entity id
        self.index = {normalise(k): v for k, v in raw_index.items() if isinstance(v, str)}

        self.by_id = {}
        self.by_name = {}
        self.debut = {}
        for rec in pr.values():
            name = (rec.get("name") or "").strip()
            if not name:
                continue
            if rec.get("id"):
                self.by_id[rec["id"]] = name
            self.by_name[normalise(name)] = name
            m = re.search(r"Chapter (\d+)", str(rec.get("first_appearance") or ""))
            if m:
                self.debut[name] = int(m.group(1))

    def canonical(self, name):
        """Loose name -> canonical punk_records name, or None."""
        if not name:
            return None
        for v in _variants(name):
            key = normalise(v)
            hit = self._lookup(key)
            if hit:
                return hit
            # Romanisation split: the site writes "Coby", the records say
            # "Koby". Same for other c/k transliterations. Only tried after an
            # exact miss, so it can never override a real match.
            swapped = key.replace("c", "k")
            if swapped != key:
                hit = self._lookup(swapped)
                if hit:
                    return hit
        return None

    def _lookup(self, key):
        # direct record name first -- cheapest and least ambiguous
        if key in self.by_name:
            return self.by_name[key]
        ent = self.index.get(key)
        if ent and ent in self.by_id:
            return self.by_id[ent]
        return None

    def debut_chapter(self, name):
        """Loose name -> that character's first-appearance chapter, or None."""
        canon = self.canonical(name)
        return self.debut.get(canon) if canon else None

    def earliest_debut(self, names):
        """Earliest debut among several loosely-written names."""
        chs = [c for c in (self.debut_chapter(n) for n in names or []) if c]
        return min(chs) if chs else None
