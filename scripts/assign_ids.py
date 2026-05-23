"""Phase 0 bootstrap: assign stable IDs to entity source files.

Reads each source file, adds `id`, `name`, `slug`, `aliases`, and `type` fields
to every entity record that doesn't already have an `id`. Writes back in canonical
JSON form. Idempotent — already-IDed entities are skipped on re-runs.

Usage:
    python scripts/assign_ids.py --target characters
    python scripts/assign_ids.py --target fruits
    python scripts/assign_ids.py --target crews
    python scripts/assign_ids.py --target locations
    python scripts/assign_ids.py --target arcs
    python scripts/assign_ids.py --all
    python scripts/assign_ids.py --dry-run --target characters
"""

import argparse
import json
import re
import sys
import unicodedata
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "entity_registry.json"
ALIASES_PATH = ROOT / "character_aliases.json"

# Zero-width and other invisible Unicode characters that appear as scraping artefacts
_INVISIBLE_RE = re.compile(
    r"[​‌‍‎‏⁠﻿]+"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_invisible(s: str) -> str:
    return _INVISIBLE_RE.sub("", s)


def slugify(name: str) -> str:
    """Produce a lowercase, ASCII-only, hyphen-separated slug."""
    # Take only the first line (devil-fruit names have '\n----' alternates)
    name = name.split("\n")[0].strip()
    # Decompose unicode; strip combining (diacritic) characters
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    name = re.sub(r"-+", "-", name)
    return name or "unknown"


def fmt_id(prefix: str, n: int) -> str:
    return f"{prefix}:{n:05d}"


def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data, dry_run: bool = False) -> None:
    if dry_run:
        return
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")


def load_registry() -> dict:
    return load_json(REGISTRY_PATH)


def save_registry(registry: dict, dry_run: bool = False) -> None:
    save_json(REGISTRY_PATH, registry, dry_run)


def next_id(prefix: str, registry: dict) -> str:
    n = registry["next"][prefix]
    registry["next"][prefix] += 1
    return fmt_id(prefix, n)


def clean_name_parts(raw: str | None) -> list[str]:
    """Split a possibly multi-line field into distinct name strings."""
    if not raw:
        return []
    parts = re.split(r"\n----", raw)
    return [p.strip() for p in parts if p.strip()]


_JUNK_ALIASES = {
    "n/a", "na", "none", "unknown", "-", "–", "—",
    "his own crew", "her own crew",
}

def build_aliases(candidate_strings: list[str | None], canonical: str) -> list[str]:
    """Deduplicated list of aliases, excluding the canonical name and junk values."""
    seen = {canonical.lower()}
    result: list[str] = []
    for raw in candidate_strings:
        for part in clean_name_parts(raw):
            if part.lower() in _JUNK_ALIASES:
                continue
            if part.lower() not in seen:
                seen.add(part.lower())
                result.append(part)
    return result


def unique_slug(base_slug: str, taken: set[str], label: str = "") -> tuple[str, bool]:
    """Return (slug, was_collision). Appends -2, -3, ... on collision."""
    if base_slug not in taken:
        return base_slug, False
    i = 2
    while True:
        candidate = f"{base_slug}-{i}"
        if candidate not in taken:
            print(
                f"  SLUG COLLISION: '{base_slug}' taken - assigned '{candidate}'"
                + (f" for {label!r}" if label else ""),
                file=sys.stderr,
            )
            return candidate, True
        i += 1


# ---------------------------------------------------------------------------
# Load character alias groups from character_aliases.json
# Returns: dict[punk_records_key -> list[extra_alias_strings]]
# ---------------------------------------------------------------------------

def load_char_alias_extras() -> dict[str, list[str]]:
    """
    character_aliases.json structure:
        { "FanName": ["WikiName", "OtherAlias", ...], ... }
    Meaning: FanName, WikiName, OtherAlias are all the same character.

    We build a reverse map: for each punk_records entry key K, what extra
    aliases should be added?
    """
    try:
        raw = load_json(ALIASES_PATH)
    except FileNotFoundError:
        return {}

    # Build groups: each group is a set of all equivalent names
    groups: list[set[str]] = []
    for key, values in raw.items():
        if key.startswith("_"):
            continue
        group = {key} | set(values)
        groups.append(group)

    # For each punk_records name, collect extra aliases from its group
    extras: dict[str, list[str]] = {}
    for group in groups:
        for name in group:
            others = sorted(group - {name})
            if others:
                existing = extras.get(name, [])
                for o in others:
                    if o not in existing:
                        existing.append(o)
                extras[name] = existing
    return extras


# ---------------------------------------------------------------------------
# Target: characters  (punk_records.json)
# ---------------------------------------------------------------------------

def assign_characters(dry_run: bool) -> int:
    path = ROOT / "punk_records.json"
    data: dict = load_json(path)
    registry = load_registry()
    char_extras = load_char_alias_extras()

    # Build a set of "clean" keys (invisible-char variants are duplicates)
    clean_to_original: dict[str, str] = {}
    zws_variants: set[str] = set()
    for key in data:
        clean = strip_invisible(key)
        if clean != key:
            zws_variants.add(key)
        elif clean in clean_to_original:
            # True duplicate — shouldn't happen but flag it
            print(f"  DUPLICATE KEY after cleaning: {key!r}", file=sys.stderr)
        else:
            clean_to_original[clean] = key

    assigned = 0
    skipped = 0
    zws_skipped = 0
    slug_taken: set[str] = set()

    # First pass: collect slugs already assigned (idempotency)
    for key, record in data.items():
        if isinstance(record, dict) and record.get("id") and record.get("slug"):
            slug_taken.add(record["slug"])

    # Second pass: assign
    for key in list(data.keys()):
        record = data[key]
        if not isinstance(record, dict):
            continue

        # Skip ZWS variants — they're artefacts, their names become aliases
        if key in zws_variants:
            clean = strip_invisible(key)
            if dry_run:
                print(f"  [DRY] SKIP ZWS variant {key!r} (alias of {clean!r})")
            else:
                # Add the ZWS key's clean name to the clean entry's aliases
                if clean in data and isinstance(data[clean], dict):
                    existing_aliases = data[clean].get("aliases", [])
                    if key not in existing_aliases and clean not in existing_aliases:
                        pass  # already covered by name field
            zws_skipped += 1
            continue

        if record.get("id"):
            skipped += 1
            continue

        canonical_name = record.get("name_canonical") or record.get("name") or key
        if not canonical_name:
            canonical_name = key

        # Build alias candidate pool
        alias_candidates = [
            key if key != canonical_name else None,
            record.get("name") if record.get("name") != canonical_name else None,
            record.get("name_en"),
            record.get("name_jp"),
            record.get("name_romaji"),
            record.get("epithet"),
        ]
        # Add extras from character_aliases.json (keyed by punk_records key)
        alias_candidates.extend(char_extras.get(key, []))
        # Also check canonical_name in extras
        alias_candidates.extend(char_extras.get(canonical_name, []))

        aliases = build_aliases(alias_candidates, canonical_name)

        base_slug = slugify(canonical_name)
        slug, had_collision = unique_slug(base_slug, slug_taken, label=key)
        slug_taken.add(slug)

        entity_id = next_id("chr", registry)

        if dry_run:
            print(f"  [DRY] {key!r} -> {entity_id}  slug={slug!r}  aliases={len(aliases)}")
            # Roll back the registry increment for dry run
            registry["next"]["chr"] -= 1
            continue

        # Prepend the ID fields to the record (for readability)
        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": aliases,
            "type": "character",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        data[key] = updated
        assigned += 1

    if not dry_run:
        save_json(path, data)
        save_registry(registry)

    print(
        f"characters: {assigned} assigned, {skipped} already had IDs, "
        f"{zws_skipped} ZWS variants skipped"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: fruits  (devil_fruits.json)
# ---------------------------------------------------------------------------

_FRUIT_META_KEYS = {"Akuma no Mi", "Devil Fruit"}


def assign_fruits(dry_run: bool) -> int:
    path = ROOT / "devil_fruits.json"
    data: dict = load_json(path)
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for key, record in data.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for key, record in data.items():
        if not isinstance(record, dict):
            continue
        if key in _FRUIT_META_KEYS:
            continue
        if record.get("id"):
            continue

        canonical_name = clean_name_parts(record.get("name") or key)[0] if (record.get("name") or key) else key

        alias_candidates = [
            key if key != canonical_name else None,
        ]
        for field in ["name", "name_jp", "name_romaji", "name_en", "translation"]:
            alias_candidates.extend(clean_name_parts(record.get(field)))

        aliases = build_aliases(alias_candidates, canonical_name)

        base_slug = slugify(canonical_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=key)
        slug_taken.add(slug)

        entity_id = next_id("fruit", registry)

        if dry_run:
            print(f"  [DRY] {key!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["fruit"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": aliases,
            "type": "fruit",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        data[key] = updated
        assigned += 1

    if not dry_run:
        save_json(path, data)
        save_registry(registry)

    print(
        f"fruits: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: crews  (crews.json)
# ---------------------------------------------------------------------------

def assign_crews(dry_run: bool) -> int:
    path = ROOT / "crews.json"
    data: dict = load_json(path)
    crews_dict: dict = data.get("crews", {})
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for crew_name, record in crews_dict.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for crew_name, record in crews_dict.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            continue

        base_slug = slugify(crew_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=crew_name)
        slug_taken.add(slug)

        entity_id = next_id("crew", registry)

        if dry_run:
            print(f"  [DRY] {crew_name!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["crew"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": crew_name,
            "slug": slug,
            "aliases": [],
            "type": "crew",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        crews_dict[crew_name] = updated
        assigned += 1

    if not dry_run:
        data["crews"] = crews_dict
        save_json(path, data)
        save_registry(registry)

    print(
        f"crews: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: locations  (locations.json)
# ---------------------------------------------------------------------------

def assign_locations(dry_run: bool) -> int:
    path = ROOT / "locations.json"
    data: dict = load_json(path)
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for loc_name, record in data.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for loc_name, record in data.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            continue

        canonical_name = record.get("name") or loc_name

        # name_en is often concatenated garbage; include jp and romaji only
        alias_candidates = [
            loc_name if loc_name != canonical_name else None,
            record.get("name_jp"),
            record.get("name_romaji"),
        ]
        aliases = build_aliases(alias_candidates, canonical_name)

        base_slug = slugify(canonical_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=loc_name)
        slug_taken.add(slug)

        entity_id = next_id("loc", registry)

        if dry_run:
            print(f"  [DRY] {loc_name!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["loc"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": aliases,
            "type": "location",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        data[loc_name] = updated
        assigned += 1

    if not dry_run:
        save_json(path, data)
        save_registry(registry)

    print(
        f"locations: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: arcs  (arcs.json)  — natural-key IDs, no registry
# ---------------------------------------------------------------------------

def assign_arcs(dry_run: bool) -> int:
    path = ROOT / "arcs.json"
    arcs: list = load_json(path)

    assigned = 0
    patched = 0
    skipped = 0

    for arc in arcs:
        if not isinstance(arc, dict):
            continue

        arc_name = arc.get("arc", "")
        saga_name = arc.get("saga", "")
        arc_slug = slugify(arc_name)
        saga_slug = slugify(saga_name)
        arc_id = f"arc:{arc_slug}"
        saga_id = f"saga:{saga_slug}"

        already_has_id = arc.get("id")
        needs_patch = already_has_id and ("name" not in arc or "aliases" not in arc)

        if already_has_id and not needs_patch:
            skipped += 1
            continue

        if dry_run:
            action = "PATCH" if needs_patch else "ASSIGN"
            print(f"  [DRY] {action} {arc_name!r} -> {arc_id}  (saga: {saga_id})")
            continue

        arc["id"] = arc_id
        arc["name"] = arc_name
        arc["slug"] = arc_slug
        arc["aliases"] = []
        arc["saga_id"] = saga_id
        arc["type"] = "arc"

        if needs_patch:
            patched += 1
        else:
            assigned += 1

    if not dry_run:
        save_json(path, arcs)

    print(
        f"arcs: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: weapons  (weapons.json)
# ---------------------------------------------------------------------------

def assign_weapons(dry_run: bool) -> int:
    path = ROOT / "weapons.json"
    data: dict = load_json(path)
    weapons_list: list = data.get("weapons", [])
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for record in weapons_list:
        if isinstance(record, dict) and record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for i, record in enumerate(weapons_list):
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            continue

        canonical_name = record.get("name", "")
        if not canonical_name:
            continue

        base_slug = slugify(canonical_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=canonical_name)
        slug_taken.add(slug)

        entity_id = next_id("weap", registry)

        if dry_run:
            print(f"  [DRY] {canonical_name!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["weap"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": [],
            "type": "weapon",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        weapons_list[i] = updated
        assigned += 1

    if not dry_run:
        data["weapons"] = weapons_list
        save_json(path, data)
        save_registry(registry)

    print(
        f"weapons: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: items  (items.json)
# ---------------------------------------------------------------------------

def assign_items(dry_run: bool) -> int:
    path = ROOT / "items.json"
    data: dict = load_json(path)
    items_list: list = data.get("items", [])
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for record in items_list:
        if isinstance(record, dict) and record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for i, record in enumerate(items_list):
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            continue

        canonical_name = record.get("name", "")
        if not canonical_name:
            continue

        base_slug = slugify(canonical_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=canonical_name)
        slug_taken.add(slug)

        entity_id = next_id("item", registry)

        if dry_run:
            print(f"  [DRY] {canonical_name!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["item"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": [],
            "type": "item",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        items_list[i] = updated
        assigned += 1

    if not dry_run:
        data["items"] = items_list
        save_json(path, data)
        save_registry(registry)

    print(
        f"items: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# Target: ships  (ships.json)  — {ship_name: {id, name, slug, ...}}
# ---------------------------------------------------------------------------

def assign_ships(dry_run: bool) -> int:
    path = ROOT / "ships.json"
    data: dict = load_json(path)
    registry = load_registry()

    assigned = 0
    skipped = 0
    slug_taken: set[str] = set()

    for ship_name, record in data.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            slug_taken.add(record.get("slug", ""))
            skipped += 1

    for ship_name, record in data.items():
        if not isinstance(record, dict):
            continue
        if record.get("id"):
            continue

        canonical_name = record.get("name") or ship_name

        alias_candidates = [
            ship_name if ship_name != canonical_name else None,
            record.get("name_jp"),
            record.get("name_romaji"),
        ]
        aliases = build_aliases(alias_candidates, canonical_name)

        base_slug = slugify(canonical_name)
        slug, _ = unique_slug(base_slug, slug_taken, label=ship_name)
        slug_taken.add(slug)

        entity_id = next_id("ship", registry)

        if dry_run:
            print(f"  [DRY] {ship_name!r} -> {entity_id}  slug={slug!r}")
            registry["next"]["ship"] -= 1
            continue

        updated = {
            "id": entity_id,
            "name": canonical_name,
            "slug": slug,
            "aliases": aliases,
            "type": "ship",
        }
        updated.update({k: v for k, v in record.items() if k not in updated})
        data[ship_name] = updated
        assigned += 1

    if not dry_run:
        save_json(path, data)
        save_registry(registry)

    print(
        f"ships: {assigned} assigned, {skipped} already had IDs"
        + (" [DRY RUN]" if dry_run else "")
    )
    return assigned


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

TARGETS = {
    "characters": assign_characters,
    "fruits": assign_fruits,
    "crews": assign_crews,
    "locations": assign_locations,
    "arcs": assign_arcs,
    "weapons": assign_weapons,
    "items": assign_items,
    "ships": assign_ships,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--target",
        choices=list(TARGETS),
        help="Entity type to assign IDs to",
    )
    group.add_argument("--all", action="store_true", help="Run all targets in order")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be assigned without writing anything",
    )
    args = parser.parse_args()

    targets = list(TARGETS) if args.all else [args.target]

    total = 0
    for target in targets:
        print(f"\n--- {target} ---")
        fn = TARGETS[target]
        total += fn(dry_run=args.dry_run)

    print(f"\nTotal assigned: {total}" + (" [DRY RUN]" if args.dry_run else ""))


if __name__ == "__main__":
    main()
