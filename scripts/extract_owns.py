"""Extract owns relationship shard from weapons.json + items.json.

For each weapon, parses the `wielder` field. " → " denotes ownership transfers;
the chain becomes one row per owner with `current` set on the last and
`from_owner` filled on the rest.

For each item, iterates the `users` array and emits one row per user with
`current: true` (items rarely 'transfer' the way named blades do).

Names are resolved via entity_index.json. Only chr: IDs are accepted as the
`from` party (so e.g. "Seraphim" → crew is rejected).

Usage:
    python scripts/extract_owns.py
    python scripts/extract_owns.py --dry-run   # print rows, no writes
"""

import argparse
import json
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEAPONS_PATH    = ROOT / "weapons.json"
ITEMS_PATH      = ROOT / "items.json"
INDEX_PATH      = ROOT / "entity_index.json"
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
PENDING_DIR     = ROOT / "relationships" / "_pending"
OUTPUT_PATH     = PENDING_DIR / "owns.json"

# wielder/users separators encountered in source data
_TRANSFER_SEP = "→"

# Groups, organizations, and narrative annotations that can't become owns edges.
# Silently skipped — not flagged to bootstrap_unresolved.json.
_SKIP_NAMES: frozenset[str] = frozenset({
    # Narrative annotations
    "returned to wano", "lost — historical", "lost - historical",
    "historical figures",
    # Organizations / factions
    "marines", "marines / wg", "world government", "world government / vegapunk",
    "cp0", "cp0 reserve", "impel down", "fishman pirates", "beasts pirates gifters",
    "fishman pirates", "skypieans", "skypiean warriors", "wano commoners",
    "crew of whitebeard", "various pirates",
    "strawhats and other grand line crews", "every grand line ship",
    "sabaody archipelago locals", "roger pirates", "most pirates",
    "the world", "vegapunk research",
})


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict | list) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")


def load_unresolved() -> list[dict]:
    if not UNRESOLVED_PATH.exists():
        return []
    raw = load_json(UNRESOLVED_PATH)
    if isinstance(raw, dict):
        return raw.get("entries", [])
    return raw if isinstance(raw, list) else []


def save_unresolved(entries: list[dict]) -> None:
    save_json(UNRESOLVED_PATH, {"entries": entries})


def resolve_chr(name: str, index: dict) -> str | None:
    """Look up name in entity_index; only return result if it's a chr: ID."""
    eid = index.get(name.lower())
    if eid and eid.startswith("chr:"):
        return eid
    return None


_QUALIFIER_RE = __import__("re").compile(r"\s*\(([^)]+)\)\s*$")


def parse_owner_name(raw: str) -> tuple[str, bool]:
    """Strip a parenthetical qualifier from an owner string.

    Returns (clean_name, is_former). The qualifier becomes is_former=True
    when it contains 'former' / 'formerly' / 'destroyed'. Other
    qualifiers (epithets like 'Whitebeard', disambiguators) are stripped
    silently.

    Examples:
      'Roronoa Zoro (former)'       → ('Roronoa Zoro', True)
      'Edward Newgate (Whitebeard)' → ('Edward Newgate', False)
      'Kouzuki Oden'                → ('Kouzuki Oden', False)
    """
    if not raw:
        return ("", False)
    s = raw.strip()
    m = _QUALIFIER_RE.search(s)
    is_former = False
    if m:
        qualifier = m.group(1).lower().strip()
        if any(w in qualifier for w in ("former", "formerly", "destroyed")):
            is_former = True
        s = s[:m.start()].strip()
    return (s, is_former)


def parse_wielder_chain(wielder: str) -> list[tuple[str, bool]]:
    """Split 'A → B → C (former)' into [('A', False), ('B', False), ('C', True)].

    For compound entries like 'Tashigi (formerly), historical figures' (no arrow
    transfer), takes only the first comma-segment as the owner name — the rest
    is descriptive text, not additional owners.

    Returns list of (clean_name, is_former) tuples. Empty input → [].
    """
    if not wielder:
        return []
    out: list[tuple[str, bool]] = []
    for part in wielder.split(_TRANSFER_SEP):
        # If a segment has no transfer arrow but contains a comma, take only
        # the first comma-segment (rest is usually descriptive, e.g. "historical figures")
        if "," in part and _TRANSFER_SEP not in part:
            part = part.split(",", 1)[0]
        clean, is_former = parse_owner_name(part)
        if clean:
            out.append((clean, is_former))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print rows but do not write any files")
    args = parser.parse_args()

    weapons_data = load_json(WEAPONS_PATH)
    items_data   = load_json(ITEMS_PATH)
    index        = load_json(INDEX_PATH) if INDEX_PATH.exists() else {}

    rows:       list[dict] = []
    unresolved: list[dict] = []
    transfers_found: list[str] = []

    existing_unresolved = load_unresolved()
    existing_keys = {(e["name"], e.get("source", "")) for e in existing_unresolved}

    def _flag_unresolved(name: str, source: str, context: str) -> None:
        if name.lower() in _SKIP_NAMES:
            return  # known non-character; silently ignore
        key = (name, source)
        if key in existing_keys:
            return
        unresolved.append({"name": name, "source": source, "context": context})
        existing_keys.add(key)

    # --- Weapons ----------------------------------------------------------
    for weap in weapons_data.get("weapons", []):
        if not isinstance(weap, dict):
            continue
        weap_id = weap.get("id", "")
        if not weap_id:
            continue
        weap_name = weap.get("name", "")

        chain = parse_wielder_chain(weap.get("wielder", ""))
        if not chain:
            continue

        if len(chain) > 1:
            transfers_found.append(
                f"{weap_name}: {' → '.join(n + (' (former)' if f else '') for n, f in chain)}"
            )

        prev_chr_id: str | None = None
        for i, (owner_name, is_former) in enumerate(chain):
            chr_id = resolve_chr(owner_name, index)
            if chr_id is None:
                _flag_unresolved(
                    owner_name, "weapons.json",
                    f"wielder of {weap_name!r} ({weap_id})",
                )
                prev_chr_id = None
                continue

            is_last = (i == len(chain) - 1)
            # Position-based default: last in chain is current.
            # But explicit '(former)' / '(destroyed)' qualifier overrides.
            current = is_last and not is_former
            row: dict = {
                "from":    chr_id,
                "to":      weap_id,
                "src":     "wiki",
                "current": current,
            }
            if prev_chr_id is not None:
                row["from_owner"] = prev_chr_id
            rows.append(row)
            prev_chr_id = chr_id

    # --- Items ------------------------------------------------------------
    for item in items_data.get("items", []):
        if not isinstance(item, dict):
            continue
        item_id   = item.get("id", "")
        item_name = item.get("name", "")
        users     = item.get("users", [])
        if not item_id or not isinstance(users, list):
            continue

        for user_name in users:
            if not user_name:
                continue
            clean_name, _ = parse_owner_name(user_name)
            chr_id = resolve_chr(clean_name, index)
            if chr_id is None:
                _flag_unresolved(
                    user_name, "items.json",
                    f"user of {item_name!r} ({item_id})",
                )
                continue
            rows.append({
                "from":    chr_id,
                "to":      item_id,
                "src":     "wiki",
                "current": True,
            })

    # --- Report -----------------------------------------------------------
    print(f"Weapons read:    {len(weapons_data.get('weapons', []))}")
    print(f"Items read:      {len(items_data.get('items', []))}")
    print(f"Rows produced:   {len(rows)}")
    print(f"Unresolved:      {len(unresolved)}")
    print(f"Wielder chains:  {len(transfers_found)}")

    if transfers_found:
        print("\nWielder transfer chains found:")
        for t in transfers_found:
            print(f"  • {t}")

    if unresolved:
        print("\nUnresolved owner names:")
        for u in unresolved:
            print(f"  ? {u['name']!r}  ({u['context']})")

    if args.dry_run:
        print("\n-- DRY RUN: no files written --")
        if rows:
            print("\nFirst 5 rows:")
            for r in rows[:5]:
                print(" ", json.dumps(r, ensure_ascii=False))
        return

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    save_json(OUTPUT_PATH, rows)
    print(f"\nWrote {len(rows)} rows -> {OUTPUT_PATH.relative_to(ROOT)}")

    if unresolved:
        all_unresolved = existing_unresolved + unresolved
        save_unresolved(all_unresolved)
        print(f"Appended {len(unresolved)} unresolved -> bootstrap_unresolved.json")

    print("\nNext steps:")
    print("  py scripts/validate_relationships.py --pending --shard owns")


if __name__ == "__main__":
    main()
