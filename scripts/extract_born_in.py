"""
extract_born_in.py — character → location (born-in shard)

Sources punk_records.json `origin` field. Resolves to loc: IDs using a
loc-only matcher that avoids entity_index collisions (e.g. "arabasta"
resolves to crew:00570 there but we want loc:00276 here).

Resolution strategy (in order):
  1. Exact match in loc_lookup (name, slug, aliases → loc: ID)
  2. Sub-location extraction: "Sea (Sub-location)" → try Sub-location first,
     fall back to Sea region
  3. Parenthetical variants: "X; Y" or "X, Y" inside parentheses — try each part
  4. Log unresolved to bootstrap_unresolved.json
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── load data ────────────────────────────────────────────────────────────────

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

records   = load_json(ROOT / "punk_records.json")
locs_data = load_json(ROOT / "locations.json")
unresolved_path = ROOT / "bootstrap_unresolved.json"
try:
    _unresolved_doc = load_json(unresolved_path)
    unresolved = _unresolved_doc.get("entries", _unresolved_doc) if isinstance(_unresolved_doc, dict) else _unresolved_doc
except FileNotFoundError:
    _unresolved_doc = {"entries": []}
    unresolved = _unresolved_doc["entries"]

# ── build loc-only lookup ────────────────────────────────────────────────────

def _build_loc_lookup(locs):
    """Name/alias → loc: ID. Avoids entity_index crew/arc collisions."""
    lookup = {}
    for entry in locs.values():
        lid = entry["id"]
        for key in [entry["name"], entry["slug"]] + entry.get("aliases", []):
            k = key.strip().lower()
            if k and k not in lookup:
                lookup[k] = lid
        # self-ref
        lookup[lid] = lid
    return lookup

loc_lookup = _build_loc_lookup(locs_data)

# ── chr_id helper ────────────────────────────────────────────────────────────

def chr_id_for(record):
    return record.get("id")

# ── origin resolution ────────────────────────────────────────────────────────

_PAREN_RE = re.compile(r"^(.+?)\s*\((.+)\)\s*$")

def _try(key):
    """Try each of several spellings."""
    k = key.strip().lower()
    return loc_lookup.get(k)

def _resolve_sub(inner):
    """Try to resolve an inner fragment that may contain ; or , separators."""
    # Try whole inner first
    hit = _try(inner)
    if hit:
        return hit, inner
    # Try semicolon-split parts
    for part in re.split(r"[;,]", inner):
        part = part.strip()
        hit = _try(part)
        if hit:
            return hit, part
    return None, None

def resolve_origin(origin):
    """
    Returns (loc_id, resolved_via, matched_fragment) or (None, None, None).
    resolved_via: 'exact' | 'sub-location' | 'sea-region'
    """
    origin = origin.strip()

    # 1. exact match
    hit = _try(origin)
    if hit:
        return hit, "exact", origin

    # 2. parenthetical: "Sea (Sub-location ...)"
    m = _PAREN_RE.match(origin)
    if m:
        sea_part = m.group(1).strip()
        sub_part = m.group(2).strip()

        # 2a. try sub-location (specific wins over sea region)
        sub_id, sub_frag = _resolve_sub(sub_part)
        if sub_id:
            return sub_id, "sub-location", sub_frag

        # 2b. fall back to sea region
        sea_id = _try(sea_part)
        if sea_id:
            return sea_id, "sea-region", sea_part

    return None, None, None

# ── extract rows ─────────────────────────────────────────────────────────────

rows = []
origin_stats = Counter()
unresolved_new = {}

for name, rec in records.items():
    origin = rec.get("origin", "").strip()
    if not origin:
        continue

    chr_id = chr_id_for(rec)
    if not chr_id:
        continue

    loc_id, resolved_via, fragment = resolve_origin(origin)
    origin_stats[resolved_via or "unresolved"] += 1

    if not loc_id:
        key = f"born_in:{name}"
        if key not in {e.get("key") for e in unresolved_new.values()}:
            unresolved_new[key] = {
                "key":            key,
                "shard":          "born-in",
                "kind":           "unresolved_location",
                "name":           name,
                "chr_id":         chr_id,
                "origin_raw":     origin,
                "resolution":     "open",
                "added_by":       "extract_born_in.py",
                "added_on":       datetime.utcnow().strftime("%Y-%m-%d"),
            }
        continue

    rows.append({
        "from":         chr_id,
        "to":           loc_id,
        "src":          "wiki",
        "origin_raw":   origin,
        "resolved_via": resolved_via,
    })

# ── stats ─────────────────────────────────────────────────────────────────────

total = sum(origin_stats.values()) + len(unresolved_new)
matched = sum(v for k, v in origin_stats.items() if k != "unresolved")
match_rate = matched / total if total else 0.0

print(f"Total chars with origin:  {total}")
print(f"  exact:        {origin_stats['exact']}")
print(f"  sub-location: {origin_stats['sub-location']}")
print(f"  sea-region:   {origin_stats['sea-region']}")
print(f"  unresolved:   {len(unresolved_new)}")
print(f"Match rate:     {match_rate:.1%}  ({matched}/{total})")
print(f"Rows to emit:   {len(rows)}")

# ── gate check ───────────────────────────────────────────────────────────────

if "--dry-run" in sys.argv:
    if unresolved_new:
        print("\nUnresolved:")
        for e in unresolved_new.values():
            print(f"  {e['chr_id']}  {e['name']!r}  origin={e['origin_raw']!r}")
    sys.exit(0)

if match_rate < 0.95:
    print(f"\n[ABORT] match rate {match_rate:.1%} below 95% gate. Fix the linker, not the data.")
    sys.exit(1)

# ── write shard ──────────────────────────────────────────────────────────────

out_path = ROOT / "relationships" / "born-in.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
print(f"\nWrote {len(rows)} rows -> {out_path}")

# ── update bootstrap_unresolved.json ─────────────────────────────────────────

if unresolved_new:
    existing_keys = {e.get("key") for e in unresolved if isinstance(e, dict)}
    added = 0
    for entry in unresolved_new.values():
        if entry["key"] not in existing_keys:
            unresolved.append(entry)
            added += 1
    if isinstance(_unresolved_doc, dict):
        _unresolved_doc["entries"] = unresolved
        with open(unresolved_path, "w", encoding="utf-8") as f:
            json.dump(_unresolved_doc, f, ensure_ascii=False, indent=2)
    else:
        with open(unresolved_path, "w", encoding="utf-8") as f:
            json.dump(unresolved, f, ensure_ascii=False, indent=2)
    print(f"Added {added} new unresolved entries -> bootstrap_unresolved.json")
