"""Query layer over the relationship shards.

A thin functional API for reading from `relationships/*.json` without callers
needing to know the file shape or do their own JSON I/O. Used by audit.py and
will be the entry point for any future server-side consumer migration.

Lazy-loads each shard on first access; subsequent calls hit a module-level
cache (cleared by `clear_cache()` if a caller ever needs to force a re-read).

This file is intentionally small — it should grow as real consumers reveal
which queries they actually need, not by speculation.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RELATIONSHIPS_DIR = ROOT / "relationships"
INDEX_PATH        = ROOT / "entity_index.json"

_CACHE: dict[str, list[dict]] = {}
_INDEX_CACHE: dict[str, dict[str, list[dict]]] = {}
_ENTITY_INDEX: dict[str, str] | None = None

# Invisible Unicode that occasionally trails scraper-sourced names
_INVISIBLE_RE = re.compile(r"[​‌‍‎‏⁠﻿]+")


def clear_cache() -> None:
    global _ENTITY_INDEX
    _CACHE.clear()
    _INDEX_CACHE.clear()
    _ENTITY_INDEX = None


def _entity_index() -> dict[str, str]:
    global _ENTITY_INDEX
    if _ENTITY_INDEX is None:
        with open(INDEX_PATH, encoding="utf-8") as f:
            _ENTITY_INDEX = json.load(f)
    return _ENTITY_INDEX


def resolve(name: str, prefix: str | None = None) -> str | None:
    """Look up a name (or alias) in entity_index. Returns the entity ID, or None.

    Tries the lowercased input first; on miss, retries with invisible Unicode
    stripped (LRM, ZWJ, BOM, etc.) — these turn up as scraper artefacts.
    If `prefix` is given (e.g. "chr:"), only returns IDs starting with it;
    otherwise any resolved ID is returned.
    """
    idx = _entity_index()
    key = name.lower()
    eid = idx.get(key)
    if eid is None:
        cleaned = _INVISIBLE_RE.sub("", key).strip()
        if cleaned and cleaned != key:
            eid = idx.get(cleaned)
    if eid is None:
        return None
    if prefix and not eid.startswith(prefix):
        return None
    return eid


def resolve_character(name: str) -> str | None:
    """Resolve a name to a chr: ID specifically (rejects crew/fruit/etc.)."""
    return resolve(name, prefix="chr:")


# ── reverse name lookup: ID → canonical display name ─────────────────

# Each source file's canonical name lives at entity["name"]; this map is
# built lazily on first access.
_NAME_CACHE: dict[str, str] | None = None

# (filename, accessor) pairs — accessor yields entity dicts with id+name
_NAME_SOURCES: list[tuple[str, str]] = [
    ("punk_records.json", "name_dict"),
    ("devil_fruits.json", "name_dict"),
    ("locations.json",    "name_dict"),
    ("crews.json",        "crews_inner"),
    ("arcs.json",         "arc_list"),
    ("weapons.json",      "weapons_inner"),
    ("items.json",        "items_inner"),
    ("ships.json",        "name_dict"),
]


def _walk_for_names(path: Path, kind: str):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if kind == "name_dict":
        for rec in data.values():
            if isinstance(rec, dict) and rec.get("id") and rec.get("name"):
                yield rec
    elif kind == "crews_inner":
        for rec in data.get("crews", {}).values():
            if isinstance(rec, dict) and rec.get("id") and rec.get("name"):
                yield rec
    elif kind == "arc_list":
        for rec in data:
            if isinstance(rec, dict) and rec.get("id") and rec.get("name"):
                yield rec
    elif kind == "weapons_inner":
        for rec in data.get("weapons", []):
            if isinstance(rec, dict) and rec.get("id") and rec.get("name"):
                yield rec
    elif kind == "items_inner":
        for rec in data.get("items", []):
            if isinstance(rec, dict) and rec.get("id") and rec.get("name"):
                yield rec


def _name_index() -> dict[str, str]:
    global _NAME_CACHE
    if _NAME_CACHE is None:
        out: dict[str, str] = {}
        for fname, kind in _NAME_SOURCES:
            path = ROOT / fname
            if not path.exists():
                continue
            for rec in _walk_for_names(path, kind):
                out[rec["id"]] = rec["name"]
        _NAME_CACHE = out
    return _NAME_CACHE


def display_name(eid: str) -> str | None:
    """Canonical display name for an entity ID, or None if unknown."""
    return _name_index().get(eid)


# ── first_appearance: wiki-authoritative chapter for a character ─────

_FIRST_APP_CACHE: dict[str, int] | None = None
_CH_PAT = re.compile(r"Chapter\s+(\d+)", re.I)


def _first_app_index() -> dict[str, int]:
    """{lower(record_key): chapter} from punk_records.json `first_appearance`.

    Wiki-scraped, authoritative. Multiple punk_records keys (e.g. "Broggy"
    + "Brogy") may resolve to the same character — both end up in this
    map, which is fine because the lookup is by name string.
    """
    global _FIRST_APP_CACHE
    if _FIRST_APP_CACHE is not None:
        return _FIRST_APP_CACHE
    pr_path = ROOT / "punk_records.json"
    out: dict[str, int] = {}
    if pr_path.exists():
        with open(pr_path, encoding="utf-8") as f:
            pr = json.load(f)
        for k, v in pr.items():
            if not isinstance(v, dict):
                continue
            fa = v.get("first_appearance", "")
            m = _CH_PAT.search(fa) if fa else None
            if not m:
                continue
            try:
                ch = int(m.group(1))
            except ValueError:
                continue
            if ch > 0:
                out[k.lower()] = ch
    _FIRST_APP_CACHE = out
    return out


def first_appearance(name: str) -> int | None:
    """Chapter number of a character's first appearance.

    Source priority (wiki is more authoritative than CSV-derived):
      1. punk_records.json `first_appearance` field (wiki scrape)
      2. canon_facts.json first_app:* row (derived from appearances.csv)
      3. None if neither has it

    Use this anywhere you want a single answer to 'when does X debut?'.
    Replaces the brittle pattern of reading the debuts-in shard, which
    inherits CSV gaps — see audit.py check_first_app_authority.
    """
    idx = _first_app_index()
    ch = idx.get(name.lower())
    if ch is not None:
        return ch
    # Fallback: scan canon_facts for a matching first_app row
    cf_path = ROOT / "canon_facts.json"
    if not cf_path.exists():
        return None
    with open(cf_path, encoding="utf-8") as f:
        cf = json.load(f)
    target = name.lower()
    for fact in cf:
        if fact.get("predicate") != "first_appearance":
            continue
        if fact.get("subject", "").lower() != target:
            continue
        v = fact.get("value", {})
        if isinstance(v, dict) and "chapter" in v:
            try:
                return int(v["chapter"])
            except (TypeError, ValueError):
                pass
    return None


def load_shard(name: str) -> list[dict]:
    """Return the rows of relationships/<name>.json (cached)."""
    if name not in _CACHE:
        path = RELATIONSHIPS_DIR / f"{name}.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise TypeError(f"{path} top-level must be a list, got {type(data).__name__}")
        _CACHE[name] = data
    return _CACHE[name]


# ── appears-in queries ────────────────────────────────────────────────

def _chapter_int(chapter_id: str) -> int | None:
    """'ch:1037' -> 1037; bad input -> None."""
    if not chapter_id.startswith("ch:"):
        return None
    try:
        return int(chapter_id[3:])
    except ValueError:
        return None


def appearances_count() -> int:
    return len(load_shard("appears-in"))


def unique_chapters() -> set[int]:
    """Distinct chapter integers referenced by appears-in rows."""
    out: set[int] = set()
    for row in load_shard("appears-in"):
        n = _chapter_int(row["to"])
        if n is not None:
            out.add(n)
    return out


def unique_characters() -> set[str]:
    """Distinct chr: IDs referenced as `from` in appears-in."""
    return {row["from"] for row in load_shard("appears-in")}


def appearance_type_breakdown() -> Counter:
    """Counter of appearance_type values across all appears-in rows."""
    return Counter(row["appearance_type"] for row in load_shard("appears-in"))


# ── indexed access (lazy, cached) ─────────────────────────────────────

def by_from(shard_name: str) -> dict[str, list[dict]]:
    """Group a shard's rows by `from` field. Cached per shard.

    O(n) one-time build; O(1) subsequent lookups. For shards scanned
    repeatedly per character (dossier-style queries), this beats the naive
    full-scan-per-call by orders of magnitude on appears-in (26.7k rows).
    """
    key = f"by_from:{shard_name}"
    if key not in _INDEX_CACHE:
        idx: dict[str, list[dict]] = defaultdict(list)
        for row in load_shard(shard_name):
            idx[row["from"]].append(row)
        _INDEX_CACHE[key] = dict(idx)
    return _INDEX_CACHE[key]


# ── cross-shard joins ─────────────────────────────────────────────────

def character_dossier(chr_id: str) -> dict:
    """Everything the shards know about a single character.

    Pulls from 10 shards: appears-in (count), debuts-in (chapter), ate-fruit,
    owns, family, voices (VA rows where chr is the `to`), trains-with
    (bidirectional: trained_by = rows where chr is `to`, trained = rows where
    chr is `from`), born-in (origin location), sails-on (ships sailed on).

    Returns a dict; empty fields stay empty (no None placeholders).
    """
    appears        = by_from("appears-in").get(chr_id, [])
    debuts         = by_from("debuts-in").get(chr_id, [])
    fruits         = by_from("ate-fruit").get(chr_id, [])
    owns_          = by_from("owns").get(chr_id, [])
    crews_         = by_from("member-of").get(chr_id, [])
    trained_       = by_from("trains-with").get(chr_id, [])   # chr trained others
    born_in_       = by_from("born-in").get(chr_id, [])
    sails_on_      = by_from("sails-on").get(chr_id, [])
    family         = [
        r for r in load_shard("family")
        if r.get("from") == chr_id or r.get("to") == chr_id
    ]
    voices_        = by_to("voices").get(chr_id, [])           # VAs who voiced chr
    trained_by_    = by_to("trains-with").get(chr_id, [])      # trainers of chr
    out: dict = {
        "id":               chr_id,
        "appearance_count": len(appears),
        "fruits":           fruits,
        "owns":             owns_,
        "crews":            crews_,
        "family":           family,
        "voices":           voices_,
        "trained_by":       trained_by_,
        "trained":          trained_,
        "born_in":          born_in_,
        "sails_on":         sails_on_,
    }
    if debuts:
        out["debut"] = {
            "chapter":         debuts[0]["to"],
            "appearance_type": debuts[0].get("appearance_type"),
        }
    return out


def crews_of(chr_id: str) -> list[dict]:
    """All member-of edges for a character (current + past affiliations)."""
    return by_from("member-of").get(chr_id, [])


# ── reverse-direction indexed access ──────────────────────────────────

def by_to(shard_name: str) -> dict[str, list[dict]]:
    """Group rows by `to` field. Mirror of by_from for reverse-direction queries.

    Lets us answer 'who points at this entity?' — e.g. members of a crew,
    owners of a weapon, character who debuted in a chapter.
    """
    key = f"by_to:{shard_name}"
    if key not in _INDEX_CACHE:
        idx: dict[str, list[dict]] = defaultdict(list)
        for row in load_shard(shard_name):
            idx[row["to"]].append(row)
        _INDEX_CACHE[key] = dict(idx)
    return _INDEX_CACHE[key]


def members_of(crew_id: str) -> list[dict]:
    """All member-of edges pointing at a crew (current + past members)."""
    return by_to("member-of").get(crew_id, [])


def owners_of(weapon_or_item_id: str) -> list[dict]:
    """All owns edges pointing at a weapon or item (full ownership chain)."""
    return by_to("owns").get(weapon_or_item_id, [])


def eaters_of(fruit_id: str) -> list[dict]:
    """All ate-fruit edges pointing at a fruit. Usually one row (current eater)."""
    return by_to("ate-fruit").get(fruit_id, [])


def family_of(chr_id: str) -> list[dict]:
    """All family edges where the character is on either side. Family is
    bidirectional; the character may appear as `from` or `to`."""
    return [
        r for r in load_shard("family")
        if r.get("from") == chr_id or r.get("to") == chr_id
    ]


def chapter_appearances(chapter_id: str) -> list[dict]:
    """All characters appearing in a given chapter (any appearance_type)."""
    return by_to("appears-in").get(chapter_id, [])


def chapter_debuts(chapter_id: str) -> list[dict]:
    """Characters whose first appearance is this chapter."""
    return by_to("debuts-in").get(chapter_id, [])


# ── more cross-shard joins ────────────────────────────────────────────

def crew_dossier(crew_id: str) -> dict:
    """Everything the shards know about a crew. Inverse view of character_dossier."""
    member_edges = members_of(crew_id)
    return {
        "id":             crew_id,
        "members":        member_edges,
        "current_count":  sum(1 for m in member_edges if m.get("current")),
        "former_count":   sum(1 for m in member_edges if not m.get("current")),
    }


def fruit_dossier(fruit_id: str) -> dict:
    """Who ate this fruit, current and historical (current rows only for now —
    transferred-fruit prior-user rows are queued for manual addition)."""
    return {
        "id":     fruit_id,
        "eaters": eaters_of(fruit_id),
    }


def weapon_dossier(weap_or_item_id: str) -> dict:
    """Ownership history for a weapon or item — full chain (current + former)."""
    edges = owners_of(weap_or_item_id)
    return {
        "id":           weap_or_item_id,
        "owners":       edges,
        "current_owner": next((e["from"] for e in edges if e.get("current")), None),
    }
