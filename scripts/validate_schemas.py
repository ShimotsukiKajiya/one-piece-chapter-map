"""
Validate Codex data files against JSON Schemas in schemas/.

Usage:
    python scripts/validate_schemas.py            # validate everything
    python scripts/validate_schemas.py --self     # only check the schemas themselves are valid
    python scripts/validate_schemas.py --target canon_facts
    python scripts/validate_schemas.py --target relationships/family

Exit code 0 = all clean, 1 = at least one validation error, 2 = usage error.

Loads every schema in schemas/ into a jsonschema Registry so $refs to
_common.json resolve correctly across files.
"""
from __future__ import annotations
import json
import os
import sys
from glob import glob

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

try:
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7
except ImportError:
    print("✗ jsonschema not installed. Run: python -m pip install jsonschema", file=sys.stderr)
    sys.exit(2)


DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMAS_DIR = os.path.join(DIR, "schemas")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_registry():
    """Load every schema into a Registry keyed by relative path.

    Refs in schema files use forms like:
        "_common.json#/$defs/entity_id"
        "../_common.json#/$defs/entity_id"
    Both forms resolve via the keys below.
    """
    resources = {}
    for path in glob(os.path.join(SCHEMAS_DIR, "**", "*.json"), recursive=True):
        rel = os.path.relpath(path, SCHEMAS_DIR).replace(os.sep, "/")
        schema = load_json(path)
        resource = Resource(contents=schema, specification=DRAFT7)

        # Register under multiple keys so $refs resolve from any depth
        keys = {rel}
        if rel.startswith("relationships/"):
            # A schema in relationships/foo.json refs ../_common.json
            keys.add("../" + os.path.basename(rel))
        # And just the filename for one-up refs from common
        keys.add(os.path.basename(rel))
        # And the $id if present
        if "$id" in schema:
            keys.add(schema["$id"])

        for k in keys:
            resources.setdefault(k, resource)
    return Registry().with_resources((k, r) for k, r in resources.items())


def validator_for(schema_path, registry):
    schema = load_json(schema_path)
    return Draft7Validator(schema, registry=registry)


def validate_self(registry):
    """Each schema must itself be valid Draft-07."""
    errors = []
    for path in sorted(glob(os.path.join(SCHEMAS_DIR, "**", "*.json"), recursive=True)):
        try:
            schema = load_json(path)
            Draft7Validator.check_schema(schema)
        except Exception as e:
            rel = os.path.relpath(path, DIR)
            errors.append((rel, str(e)))
    return errors


# Targets: each maps a logical name to (data_path_or_glob, schema_path, item_extractor).
# item_extractor takes the parsed file and returns an iterable of (item_id, item_dict).
def _list_extractor(data, name):
    return [(f"{name}[{i}]", x) for i, x in enumerate(data)] if isinstance(data, list) else []


def _shard_extractor(data, name):
    rows = data.get("rows") if isinstance(data, dict) else data
    return [(f"{name}[{i}]", x) for i, x in enumerate(rows or [])]


def _decisions_extractor(data, name):
    rows = (data or {}).get("decisions", [])
    return [(f"{name}.decisions[{i}]", x) for i, x in enumerate(rows)]


TARGETS = {
    "canon_facts": {
        "data":   os.path.join(DIR, "canon_facts.json"),
        "schema": os.path.join(SCHEMAS_DIR, "canon_fact.json"),
        "extract": _list_extractor,
        "optional": False,
    },
    "curate_decisions": {
        "data":   os.path.join(DIR, "docs", "curate_decisions.json"),
        "schema": os.path.join(SCHEMAS_DIR, "curate_decision.json"),
        "extract": _decisions_extractor,
        "optional": True,
    },
}

# Relationships: one target per shard, all using the relationship schema for that type.
for shard_path in sorted(glob(os.path.join(SCHEMAS_DIR, "relationships", "*.json"))):
    name = "relationships/" + os.path.splitext(os.path.basename(shard_path))[0]
    TARGETS[name] = {
        "data":   os.path.join(DIR, "relationships", os.path.basename(shard_path)),
        "schema": shard_path,
        "extract": _shard_extractor,
        "optional": True,  # shards may not exist yet (pre-bootstrap)
    }


def validate_target(name, spec, registry, verbose=False):
    data_path = spec["data"]
    if not os.path.exists(data_path):
        if spec.get("optional"):
            return ("skip", f"  · {name}: data file not present (skipped)")
        return ("error", f"  ✗ {name}: data file missing — {data_path}")

    try:
        data = load_json(data_path)
    except Exception as e:
        return ("error", f"  ✗ {name}: cannot parse — {e}")

    items = spec["extract"](data, name)
    if not items:
        return ("ok", f"  ✓ {name}: empty (0 rows)")

    validator = validator_for(spec["schema"], registry)
    errors = []
    for item_id, item in items:
        for err in validator.iter_errors(item):
            path = "/".join(str(p) for p in err.absolute_path) or "<root>"
            errors.append(f"    {item_id} {path}: {err.message}")

    if errors:
        msg = f"  ✗ {name}: {len(errors)} error(s) in {len(items)} row(s)\n" + "\n".join(errors[:20])
        if len(errors) > 20:
            msg += f"\n    … and {len(errors) - 20} more"
        return ("error", msg)
    return ("ok", f"  ✓ {name}: {len(items)} row(s) valid")


def main():
    args = sys.argv[1:]
    self_only = "--self" in args
    targets_filter = None
    if "--target" in args:
        i = args.index("--target")
        if i + 1 >= len(args):
            print("✗ --target requires a value", file=sys.stderr)
            sys.exit(2)
        targets_filter = args[i + 1]

    print("=" * 60)
    print("  Schema validation")
    print("=" * 60)

    registry = build_registry()
    schema_count = len(list(glob(os.path.join(SCHEMAS_DIR, "**", "*.json"), recursive=True)))

    # Step 1: schemas are valid draft-07
    print(f"\n  Self-check ({schema_count} schemas):")
    self_errors = validate_self(registry)
    if self_errors:
        for rel, err in self_errors:
            print(f"    ✗ {rel}: {err}")
        print(f"\n  ✗ {len(self_errors)} schema(s) invalid. Fix these before validating data.")
        sys.exit(1)
    print(f"    ✓ all schemas are valid Draft-07")

    if self_only:
        print()
        sys.exit(0)

    # Step 2: validate data files
    print(f"\n  Data files:")
    overall_ok = True
    for name, spec in sorted(TARGETS.items()):
        if targets_filter and not name.startswith(targets_filter):
            continue
        status, msg = validate_target(name, spec, registry)
        print(msg)
        if status == "error":
            overall_ok = False

    print()
    print("=" * 60)
    if overall_ok:
        print("  ✓ all clean")
        sys.exit(0)
    else:
        print("  ✗ at least one target failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
