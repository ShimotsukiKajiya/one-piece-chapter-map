"""Validate entity ID fields across all source files.

Checks:
  - Required fields (id, name, slug, aliases, type) are present
  - id matches expected format for its prefix
  - Numeric IDs don't exceed the registry counter
  - No two entities share a slug within the same type
  - No two entities share a case-insensitive alias globally

Run before any bake. Failures should block promotion.

Usage:
    python scripts/validate_ids.py
    python scripts/validate_ids.py --strict    # exit 1 on any warning too
"""

import argparse
import json
import re
import sys
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "entity_registry.json"

# ID pattern: prefix:NNNNN (numeric) or prefix:slug-string (natural-key)
_ID_RE = re.compile(r"^([a-z]+):([a-z0-9][a-z0-9\-]*)$")
_NUMERIC_SUFFIX_RE = re.compile(r"^\d{5}$")
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")

# Types with natural-key IDs (no registry counter check)
_NATURAL_KEY_PREFIXES = {"ch", "ep", "vol", "sbs", "theory", "saga", "arc"}

# Aliases that are not meaningful identifiers — skip collision checks for these
_JUNK_ALIASES = {
    "n/a", "na", "none", "unknown", "-", "–", "—",
    "his own crew", "her own crew",
}

# Known within-type alias overlaps — demoted to warnings, not errors.
# These come from duplicate wiki keys in scraper-owned source files (punk_records.json).
# TODO: fix punk_records_scraper.py to deduplicate these at source.
# Format: frozenset({alias_lower, entity_id_a, entity_id_b})
_KNOWN_ALIAS_OVERLAPS: set[frozenset] = {
    frozenset({'"gang"',                                         "chr:01732", "chr:01733"}),
    frozenset({'"nyaban brothers"',                              "chr:01707", "chr:02806"}),
    frozenset({"akainu",                                         "chr:01564", "chr:02756"}),
    frozenset({"aokiji",                                         "chr:01592", "chr:02352"}),
    frozenset({"bjorn",                                          "chr:01663", "chr:01664"}),
    frozenset({"blackbeard",                                     "chr:02346", "chr:02426"}),
    frozenset({"bomba",                                          "chr:01687", "chr:01688"}),
    frozenset({"bonba",                                          "chr:01687", "chr:01688"}),
    frozenset({"borsalino",                                      "chr:01694", "chr:02307"}),
    frozenset({"brogy (viz, odex); broggy (funimation, formerly viz)", "chr:01700", "chr:01701"}),
    frozenset({"brogy the red ogre",                             "chr:01700", "chr:01701"}),
    frozenset({"burogī",                                    "chr:01700", "chr:01701"}),
    frozenset({"byorun",                                         "chr:01663", "chr:01664"}),
    frozenset({"cerberus",                                       "chr:01744", "chr:01745"}),
    frozenset({"dogura",                                         "chr:01918", "chr:01919"}),
    frozenset({"ganryu",                                         "chr:02017", "chr:02018"}),
    frozenset({"ganryū",                                    "chr:02017", "chr:02018"}),
    frozenset({"hack",                                           "chr:02085", "chr:02086"}),
    frozenset({"hakku",                                          "chr:02085", "chr:02086"}),
    frozenset({"hanji",                                          "chr:02099", "chr:02100"}),
    frozenset({"hera",                                           "chr:02121", "chr:02122"}),
    frozenset({"hiro gomon",                                     "chr:02141", "chr:02490"}),
    frozenset({"hiro gōmon",                                "chr:02141", "chr:02490"}),
    frozenset({"ikkaku",                                         "chr:02178", "chr:02179"}),
    frozenset({"imu",                                            "chr:02180", "chr:02569"}),
    frozenset({"imu-sama",                                       "chr:02180", "chr:02569"}),
    frozenset({"kaku",                                           "chr:02256", "chr:02257"}),
    frozenset({"keruberosu",                                     "chr:01744", "chr:01745"}),
    frozenset({"kizaru",                                         "chr:01694", "chr:02307"}),
    frozenset({"kuzan",                                          "chr:01592", "chr:02352"}),
    frozenset({"lilith",                                         "chr:02370", "chr:02999"}),
    frozenset({"lola",                                           "chr:02381", "chr:02382"}),
    frozenset({"macro",                                          "chr:02393", "chr:02394"}),
    frozenset({"magura",                                         "chr:02399", "chr:02400"}),
    frozenset({"makkusu mākusu",                            "chr:02389", "chr:02390"}),
    frozenset({"max marx",                                       "chr:02389", "chr:02390"}),
    frozenset({"max マークス",                   "chr:02389", "chr:02390"}),
    frozenset({"nerona imu",                                     "chr:02180", "chr:02569"}),
    frozenset({"ririsu",                                         "chr:02370", "chr:02999"}),
    frozenset({"risky brothers",                                 "chr:02714", "chr:02715"}),
    frozenset({"risukī kyōdai",                        "chr:02714", "chr:02715"}),
    frozenset({"saint imu",                                      "chr:02180", "chr:02569"}),
    frozenset({"sakazuki",                                       "chr:01564", "chr:02756"}),
    frozenset({"tama",                                           "chr:02900", "chr:02901"}),
    frozenset({"tori",                                           "chr:01657", "chr:02942"}),
    frozenset({"tsuru",                                          "chr:02958", "chr:02962"}),
    frozenset({"wolf unit",                                      "chr:03037", "chr:03038"}),
    frozenset({"ケルベロス",                "chr:01744", "chr:01745"}),
    frozenset({"トリ",                                   "chr:01657", "chr:02942"}),
    frozenset({"ハック",                             "chr:02085", "chr:02086"}),
    frozenset({"ヒロ★ゴーモン",    "chr:02141", "chr:02490"}),
    frozenset({"ビョルン",                      "chr:01663", "chr:01664"}),
    frozenset({"ブロギー",                      "chr:01700", "chr:01701"}),
    frozenset({"ボンバ",                             "chr:01687", "chr:01688"}),
    frozenset({"リスキー兄弟",          "chr:02714", "chr:02715"}),
    frozenset({"悪",                                         "chr:02370", "chr:02999"}),
}

# ---------------------------------------------------------------------------
# Source iterators (same pattern as build_entity_index.py)
# ---------------------------------------------------------------------------

def _iter_name_dict(data: dict, source: str):
    for key, record in data.items():
        if isinstance(record, dict) and record.get("id"):
            yield source, key, record


def _iter_crews(data: dict, source: str):
    for key, record in data.get("crews", {}).items():
        if isinstance(record, dict) and record.get("id"):
            yield source, key, record


def _iter_arc_list(data: list, source: str):
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            yield source, item.get("arc", "?"), item


SOURCES = [
    ("punk_records.json",  _iter_name_dict),
    ("devil_fruits.json",  _iter_name_dict),
    ("locations.json",     _iter_name_dict),
    ("crews.json",         _iter_crews),
    ("arcs.json",          _iter_arc_list),
]

REQUIRED_FIELDS = ("id", "name", "slug", "aliases", "type")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate(registry: dict, verbose: bool = False) -> tuple[list[str], list[str]]:
    """
    Returns (errors, warnings).
    errors   — must be zero for a clean bake
    warnings — informational, non-blocking
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Track for uniqueness checks
    slug_by_type: dict[str, dict[str, str]] = {}     # type -> slug -> entity_id
    alias_global: dict[str, tuple[str, str]] = {}     # alias_lower -> (entity_id, entity_type)

    def _err(msg: str) -> None:
        errors.append(msg)
        if verbose:
            print(f"  ERROR: {msg}", file=sys.stderr)

    def _warn(msg: str) -> None:
        warnings.append(msg)
        if verbose:
            print(f"  WARN:  {msg}", file=sys.stderr)

    def _check_alias(alias: str, entity_id: str, entity_type: str, label: str) -> None:
        key = alias.strip().lower()
        if not key:
            return
        if key in _JUNK_ALIASES:
            return
        if key in alias_global:
            prev_id, prev_type = alias_global[key]
            if prev_id != entity_id:
                if prev_type == entity_type:
                    if frozenset({key, prev_id, entity_id}) in _KNOWN_ALIAS_OVERLAPS:
                        _warn(
                            f"Known overlap (allowlisted) within type {entity_type!r}: "
                            f"{alias!r} shared by {prev_id!r} and {entity_id!r}"
                        )
                    else:
                        _err(
                            f"Alias collision within type {entity_type!r}: "
                            f"{alias!r} shared by {prev_id!r} and {entity_id!r} ({label})"
                        )
                else:
                    # Different types (arc vs location, crew vs character, etc.) — warn only
                    _warn(
                        f"Cross-type alias overlap ({prev_type}/{entity_type}): "
                        f"{alias!r} -> {prev_id!r} and {entity_id!r} ({label})"
                    )
        else:
            alias_global[key] = (entity_id, entity_type)

    for filename, extractor in SOURCES:
        path = ROOT / filename
        if not path.exists():
            _warn(f"{filename} not found - skipped")
            continue

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for source, key, record in extractor(data, filename):
            label = f"{source}/{key}"

            # Required fields
            for field in REQUIRED_FIELDS:
                if field not in record:
                    _err(f"Missing required field {field!r}: {label}")

            entity_id = record.get("id", "")

            # ID format
            m = _ID_RE.match(entity_id)
            if not m:
                _err(f"Bad id format {entity_id!r}: {label}")
                continue
            prefix, suffix = m.group(1), m.group(2)

            # Numeric IDs: suffix must be 5-digit and within registry
            if prefix not in _NATURAL_KEY_PREFIXES:
                if not _NUMERIC_SUFFIX_RE.match(suffix):
                    _err(f"Numeric id {entity_id!r} suffix must be 5 digits: {label}")
                else:
                    n = int(suffix)
                    limit = registry.get("next", {}).get(prefix)
                    if limit is None:
                        _warn(f"Unknown prefix {prefix!r} (not in registry): {label}")
                    elif n >= limit:
                        _err(
                            f"id {entity_id!r} exceeds registry counter {limit} "
                            f"for prefix {prefix!r}: {label}"
                        )

            # Slug format
            slug = record.get("slug", "")
            if slug and not _SLUG_RE.match(slug):
                _err(f"Invalid slug {slug!r}: {label}")

            # Slug uniqueness within type
            etype = record.get("type", prefix)
            if slug:
                type_slugs = slug_by_type.setdefault(etype, {})
                if slug in type_slugs and type_slugs[slug] != entity_id:
                    _err(
                        f"Slug collision within type {etype!r}: "
                        f"{slug!r} used by {type_slugs[slug]!r} and {entity_id!r}"
                    )
                else:
                    type_slugs[slug] = entity_id

            # Alias uniqueness (global, case-insensitive)
            name = record.get("name", key)
            _check_alias(name, entity_id, etype, label)
            if slug:
                _check_alias(slug, entity_id, etype, label)
            for alias in record.get("aliases", []):
                _check_alias(alias, entity_id, etype, label)

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on warnings too")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print("ERROR: entity_registry.json not found. Run assign_ids.py first.", file=sys.stderr)
        sys.exit(1)

    with open(REGISTRY_PATH, encoding="utf-8") as f:
        registry = json.load(f)

    print("Validating entity IDs ...")
    errors, warnings = validate(registry, verbose=args.verbose)

    print(f"  Errors:   {len(errors)}")
    print(f"  Warnings: {len(warnings)}")

    if errors:
        print("\nErrors:")
        for msg in errors:
            print(f"  ✗ {msg}")

    if warnings and (args.verbose or args.strict):
        print("\nWarnings:")
        for msg in warnings:
            print(f"  ⚠ {msg}")

    if errors or (args.strict and warnings):
        sys.exit(1)

    print("\nOK")


if __name__ == "__main__":
    main()
