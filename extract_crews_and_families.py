"""
Extract Crews + Families — derives two structured graphs from the
free-text `affiliation` and `family` fields in punk_records.json.

No new scrape. Just parsing what we already have, with minimal
heuristics so we keep precision high.

Outputs:
  crews.json     — { "Straw Hat Pirates": {members: [{name,
                     status:"current"|"former"|"sworn"}, ...],
                     count: N}, ... }
  families.json  — list of edges:
                   { from: "X", to: "Y", relation: "father" }

Run:
  py extract_crews_and_families.py
  py extract_crews_and_families.py --dry-run
"""
import json, os, re, sys
from collections import defaultdict
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
PUNK_PATH  = os.path.join(DIR, "punk_records.json")
CREWS_PATH = os.path.join(DIR, "crews.json")
FAMILIES_PATH = os.path.join(DIR, "families.json")

TODAY = date.today().isoformat()


def parse_affiliation(text):
    """Return list of (crew_name, status). Statuses inferred from
    parentheticals: '(former)' → 'former', '(sworn)' → 'sworn',
    nothing → 'current'."""
    if not text: return []
    out = []
    # Split on top-level semicolons (safe — no nested structure observed)
    for chunk in str(text).split(";"):
        chunk = chunk.strip()
        if not chunk: continue
        # Status from parenthetical at end, e.g. "Whitebeard Pirates (former)"
        m = re.search(r"\s*\(([^)]+)\)\s*$", chunk)
        status = "current"
        if m:
            qualifier = m.group(1).lower().strip()
            if any(w in qualifier for w in ("former", "previous", "ex-", "disbanded")):
                status = "former"
            elif "sworn" in qualifier:
                status = "sworn"
            elif any(w in qualifier for w in ("temporary", "temp")):
                status = "temporary"
            elif "alleged" in qualifier:
                status = "alleged"
            else:
                # Keep the qualifier as flavor (e.g. "descended", "guest")
                status = qualifier
            chunk = chunk[:m.start()].strip()
        # Normalize: strip trailing punctuation, collapse whitespace
        chunk = re.sub(r"\s+", " ", chunk).strip(",.;")
        if chunk and len(chunk) >= 3:
            out.append((chunk, status))
    return out


def parse_family(text):
    """Return list of (related_name, relation). Family text often looks
    like "Monkey D. Dragon (father); Monkey D. Garp (grandfather);
    Portgas D. Ace (sworn brother)". """
    if not text: return []
    out = []
    for chunk in re.split(r"[;]", str(text)):
        chunk = chunk.strip()
        if not chunk: continue
        m = re.search(r"\s*\(([^)]+)\)\s*$", chunk)
        relation = ""
        if m:
            relation = m.group(1).strip()
            chunk = chunk[:m.start()].strip()
        # Drop wiki-style citations or "X et al" cruft
        chunk = re.sub(r"\s+", " ", chunk).strip(",.;")
        if chunk and len(chunk) >= 2:
            out.append((chunk, relation))
    return out


def main():
    dry = "--dry-run" in sys.argv
    if not os.path.exists(PUNK_PATH):
        print("  ✗ punk_records.json missing"); sys.exit(1)
    pr = json.load(open(PUNK_PATH, encoding="utf-8"))

    crews = defaultdict(list)
    family_edges = []

    for name, rec in pr.items():
        if not rec.get("found"): continue

        # Crews
        for crew, status in parse_affiliation(rec.get("affiliation")):
            crews[crew].append({"name": name, "status": status})

        # Families
        for relative, relation in parse_family(rec.get("family")):
            family_edges.append({
                "from":     name,
                "to":       relative,
                "relation": relation,
            })

    # Compact crews into the final shape
    crews_out = {}
    for crew, members in crews.items():
        # Dedupe (some chars listed twice)
        seen = set(); unique = []
        for m in members:
            key = (m["name"], m["status"])
            if key not in seen:
                seen.add(key); unique.append(m)
        crews_out[crew] = {
            "members": unique,
            "count":   len(unique),
            "current_count": sum(1 for m in unique if m["status"] == "current"),
        }

    # Preserve any IDs that assign_ids.py has already assigned. crews.json
    # is now ID-keyed downstream (relationships/member-of.json references
    # crew:NNNNN), so wholesale overwrite would silently break every shard.
    # We merge the regenerated member data INTO the existing record shape.
    existing_crews: dict = {}
    if os.path.exists(CREWS_PATH):
        try:
            with open(CREWS_PATH, encoding="utf-8") as f:
                existing_doc = json.load(f)
            existing_crews = existing_doc.get("crews", {})
        except Exception as e:
            print(f"  ⚠  Could not read existing {CREWS_PATH} for ID merge: {e}")
            existing_crews = {}

    preserved_id_count = 0
    for crew_name, fresh in crews_out.items():
        old = existing_crews.get(crew_name)
        if isinstance(old, dict) and old.get("id"):
            # Keep ID-bearing fields from the prior version, refresh the rest
            for field in ("id", "name", "slug", "aliases", "type"):
                if field in old:
                    fresh[field] = old[field]
            preserved_id_count += 1
    print(f"  IDs preserved      : {preserved_id_count:,} / {len(crews_out):,} crews")

    print("=" * 60)
    print(f"  Extract Crews + Families")
    print(f"  Characters scanned : {sum(1 for r in pr.values() if r.get('found')):,}")
    print(f"  Crews discovered   : {len(crews_out):,}")
    print(f"  Family edges       : {len(family_edges):,}")
    print("=" * 60)
    # Top 10 by member count
    top = sorted(crews_out.items(), key=lambda kv: -kv[1]["count"])[:10]
    print("\n  Top 10 crews by member count:")
    for name, info in top:
        print(f"    {info['count']:4d}  {name}")
    print()

    if dry:
        print("  (dry run — not written)")
        return

    with open(CREWS_PATH, "w", encoding="utf-8") as f:
        json.dump({"generated_on": TODAY, "crews": crews_out}, f,
                  ensure_ascii=False, indent=2)
    print(f"  ✓ {CREWS_PATH}")

    # NOTE 2026-05-01: families.json write removed.
    # That file is now hand-curated (its `_doc` says so explicitly) — Wiki
    # Char Box doesn't carry a family field, so this script's parse_family()
    # was producing 0 edges and the write would silently wipe ~50 hand-curated
    # edges + the assigned IDs. The script's purpose narrowed to crews only.
    # If we ever want auto-extracted families again, build a separate script
    # that writes to a different path and merges, never overwrites, families.json.
    if family_edges:
        print(f"  ⚠  Computed {len(family_edges)} family edges but NOT writing —")
        print(f"     families.json is hand-curated. Edges discarded:")
        for e in family_edges[:5]:
            print(f"     - {e['from']} -[{e['relation']}]-> {e['to']}")
        if len(family_edges) > 5:
            print(f"     ... and {len(family_edges) - 5} more")


if __name__ == "__main__":
    main()
