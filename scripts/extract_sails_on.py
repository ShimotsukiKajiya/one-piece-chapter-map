"""
extract_sails_on.py — character → ship (sails-on shard)

Sources ships.json `affiliation` field, resolves to crew: IDs, then looks up
all member-of edges for that crew to emit chr → ship edges.

Special handling:
- Straw Hat Pirates → Going Merry (current=False) + Thousand Sunny (current=True)
- Multi-ship crews (Marines, Baroque Works) → emit for all ships, no current flag
- Single-ship crews → emit with current=True for current members

Gate: nothing blocking on match rate; all rows are resolvable by definition
(we only emit rows where both chr: and ship: IDs are resolved).
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

# ── load data ──────────────────────────────────────────────────────────────

ships       = load_json(ROOT / "ships.json")
idx         = load_json(ROOT / "entity_index.json")
member_rows = load_json(ROOT / "relationships" / "member-of.json")

# ── index member-of by crew ────────────────────────────────────────────────

crew_to_members: dict[str, list[dict]] = {}
for row in member_rows:
    crew_id = row.get("to", "")
    if crew_id not in crew_to_members:
        crew_to_members[crew_id] = []
    crew_to_members[crew_id].append(row)

# ── group ships by crew ────────────────────────────────────────────────────

crew_to_ships: dict[str, list[dict]] = {}
for ship_name, rec in ships.items():
    ship_id = rec.get("id")
    if not ship_id:
        continue
    aff = rec.get("affiliation", "").strip()
    if not aff:
        continue
    crew_id = idx.get(aff.lower())
    if not crew_id or not crew_id.startswith("crew:"):
        continue
    if crew_id not in crew_to_ships:
        crew_to_ships[crew_id] = []
    crew_to_ships[crew_id].append(rec)

# ── static overrides: crews whose members have time-split ship assignments ──
# Format: crew_id -> [(ship_id, current, note)]
# Used when the simple affiliation→members fanout is too coarse.
STRAW_HAT_CREW = "crew:00452"
GOING_MERRY    = "ship:00041"
THOUSAND_SUNNY = "ship:00042"

_STRAW_HAT_OVERRIDE = [
    (GOING_MERRY,    False, "Pre-Enies Lobby flagship (Ch.41–430)"),
    (THOUSAND_SUNNY, True,  "Current flagship (Ch.435+)"),
]

# ── emit rows ──────────────────────────────────────────────────────────────

rows = []
crew_stats = {}
skipped_multi = []

for crew_id, ship_list in crew_to_ships.items():
    members = crew_to_members.get(crew_id, [])
    if not members:
        continue

    # Straw Hat Pirates: time-split override
    if crew_id == STRAW_HAT_CREW:
        for member_row in members:
            chr_id = member_row.get("from")
            if not chr_id:
                continue
            for ship_id, current, note in _STRAW_HAT_OVERRIDE:
                rows.append({
                    "from":    chr_id,
                    "to":      ship_id,
                    "src":     "inferred",
                    "current": current,
                    "note":    note,
                })
        crew_stats[crew_id] = len(members) * 2
        continue

    # Multi-ship crews (Marines, Baroque Works): emit all, no current flag
    if len(ship_list) > 1:
        ship_names = [s["name"] for s in ship_list]
        skipped_multi.append((crew_id, ship_names))
        for member_row in members:
            chr_id = member_row.get("from")
            if not chr_id:
                continue
            for ship_rec in ship_list:
                rows.append({
                    "from": chr_id,
                    "to":   ship_rec["id"],
                    "src":  "inferred",
                    "note": f"Fleet ship ({ship_rec['name']})",
                })
        crew_stats[crew_id] = len(members) * len(ship_list)
        continue

    # Single-ship crew: straightforward
    ship_rec = ship_list[0]
    ship_id  = ship_rec["id"]
    for member_row in members:
        chr_id = member_row.get("from")
        if not chr_id:
            continue
        current = bool(member_row.get("current", False))
        rows.append({
            "from":    chr_id,
            "to":      ship_id,
            "src":     "inferred",
            "current": current,
        })
    crew_stats[crew_id] = len(members)

# ── stats ──────────────────────────────────────────────────────────────────

total_chars = len({r["from"] for r in rows})
total_ships = len({r["to"] for r in rows})

print(f"Rows emitted:       {len(rows)}")
print(f"Unique characters:  {total_chars}")
print(f"Unique ships:       {total_ships}")
print(f"Crews covered:      {len(crew_stats)}")
if skipped_multi:
    print(f"\nMulti-ship fleets (emitted all combinations):")
    for crew_id, names in skipped_multi:
        print(f"  {crew_id}: {names}")

if "--dry-run" in sys.argv:
    print("\nSample rows:")
    for r in rows[:8]:
        print(" ", r)
    sys.exit(0)

# ── write shard ────────────────────────────────────────────────────────────

out_path = ROOT / "relationships" / "sails-on.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
print(f"\nWrote {len(rows)} rows -> {out_path}")
