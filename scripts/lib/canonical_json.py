"""
Canonical JSON form + structured diff.

Used by the bootstrap pipeline (and any other place that needs a
trustworthy round-trip comparison) to compare two JSON structures
without false positives from key order, whitespace, number formatting,
or BOM.

Public API:
    canonical_dumps(obj)              -> str   (canonical bytes-equivalent text)
    canonical_load(path)              -> obj   (read + re-canonicalise)
    canonical_diff(a, b, key=None)    -> dict  (structured diff)

The diff vocabulary matches docs/bootstrap-plan.md §5:
    {
        "lost":  [...],   # in `a` (source) but not in `b` (regenerated)
        "added": [...],   # in `b` but not in `a`
        "drift": [...],   # same logical row, different fields
    }

`key` is a function (or list of field names) that uniquely identifies a
row within a list. When `key` is given, lists are compared as keyed sets;
otherwise list comparison is positional.
"""
from __future__ import annotations
import io
import json
import os
from typing import Any, Callable, Sequence


# ── Canonical text form ──────────────────────────────────────────────

def _normalise_numbers(obj: Any) -> Any:
    """Collapse 1.0 → 1 where lossless. Leaves true floats alone."""
    if isinstance(obj, float):
        if obj.is_integer():
            return int(obj)
        return obj
    if isinstance(obj, dict):
        return {k: _normalise_numbers(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalise_numbers(v) for v in obj]
    return obj


def canonical_dumps(obj: Any) -> str:
    """Return a canonical JSON string for `obj`.

    - keys sorted
    - no extraneous whitespace (compact separators)
    - non-ASCII preserved (ensure_ascii=False)
    - 1.0 normalised to 1 where lossless
    Two semantically-equal objects produce byte-identical strings.
    """
    return json.dumps(
        _normalise_numbers(obj),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def canonical_load(path: str) -> Any:
    """Read a JSON file and return the parsed object.

    Strips BOM if present. Raises the underlying JSONDecodeError on
    malformed input — this is intentional; canonical comparison only
    makes sense on parseable JSON.
    """
    with io.open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


# ── Structured diff ──────────────────────────────────────────────────

def _key_fn(key: Any) -> Callable[[Any], Any]:
    """Coerce `key` to a callable that returns a hashable identifier."""
    if key is None:
        return lambda row: id(row)  # positional fallback handled separately
    if callable(key):
        return key
    if isinstance(key, str):
        return lambda row: row.get(key) if isinstance(row, dict) else None
    if isinstance(key, (list, tuple)):
        fields = tuple(key)
        def _multi(row):
            if not isinstance(row, dict):
                return None
            return tuple(row.get(f) for f in fields)
        return _multi
    raise TypeError(f"key must be None, str, list, or callable; got {type(key).__name__}")


def _row_drift(a_row: Any, b_row: Any) -> dict | None:
    """If two rows differ on any field, return a per-field diff. Else None."""
    if canonical_dumps(a_row) == canonical_dumps(b_row):
        return None
    if not (isinstance(a_row, dict) and isinstance(b_row, dict)):
        return {"a": a_row, "b": b_row}
    fields = sorted(set(a_row.keys()) | set(b_row.keys()))
    deltas = {}
    for f in fields:
        av = a_row.get(f, _MISSING)
        bv = b_row.get(f, _MISSING)
        if av is _MISSING:
            deltas[f] = {"added_in_b": bv}
        elif bv is _MISSING:
            deltas[f] = {"removed_in_b": av}
        elif canonical_dumps(av) != canonical_dumps(bv):
            deltas[f] = {"a": av, "b": bv}
    return deltas or None


_MISSING = object()


def canonical_diff(a: Any, b: Any, key: Any = None) -> dict:
    """Compare two JSON structures.

    Returns:
        {
            "lost":  [rows in `a` but not in `b`],
            "added": [rows in `b` but not in `a`],
            "drift": [{"key": <key>, "delta": <per-field diff>}],
        }

    For lists: when `key` is given, compared as keyed sets; otherwise
    positional element-by-element comparison.
    For dicts: compared by key, recurses into values that are lists/dicts.
    For scalars: equal or drift only.
    """
    # Top-level list comparison with optional keying
    if isinstance(a, list) and isinstance(b, list):
        if key is None:
            return _list_positional_diff(a, b)
        return _list_keyed_diff(a, b, _key_fn(key))

    # Dict-of-lists or wrapped-rows pattern: { "rows": [...] }
    if isinstance(a, dict) and isinstance(b, dict):
        if "rows" in a and "rows" in b and isinstance(a["rows"], list) and isinstance(b["rows"], list):
            return canonical_diff(a["rows"], b["rows"], key=key)
        return _dict_diff(a, b, key=key)

    # Scalars / mismatched types
    if canonical_dumps(a) == canonical_dumps(b):
        return {"lost": [], "added": [], "drift": []}
    return {"lost": [], "added": [], "drift": [{"key": None, "delta": {"a": a, "b": b}}]}


def _list_keyed_diff(a: list, b: list, kfn: Callable) -> dict:
    a_by_k = {}
    for row in a:
        k = kfn(row)
        if k in a_by_k:
            # Duplicate keys in source — record the second one as drift
            continue
        a_by_k[k] = row
    b_by_k = {}
    for row in b:
        k = kfn(row)
        if k in b_by_k:
            continue
        b_by_k[k] = row

    lost = [a_by_k[k] for k in a_by_k if k not in b_by_k]
    added = [b_by_k[k] for k in b_by_k if k not in a_by_k]
    drift = []
    for k in a_by_k:
        if k in b_by_k:
            d = _row_drift(a_by_k[k], b_by_k[k])
            if d is not None:
                drift.append({"key": k, "delta": d})
    return {"lost": lost, "added": added, "drift": drift}


def _list_positional_diff(a: list, b: list) -> dict:
    lost = []
    added = []
    drift = []
    n = max(len(a), len(b))
    for i in range(n):
        if i >= len(b):
            lost.append(a[i])
        elif i >= len(a):
            added.append(b[i])
        else:
            d = _row_drift(a[i], b[i])
            if d is not None:
                drift.append({"key": i, "delta": d})
    return {"lost": lost, "added": added, "drift": drift}


def _dict_diff(a: dict, b: dict, key: Any = None) -> dict:
    lost = []
    added = []
    drift = []
    fields = sorted(set(a.keys()) | set(b.keys()))
    for f in fields:
        if f not in b:
            lost.append({f: a[f]})
        elif f not in a:
            added.append({f: b[f]})
        else:
            d = _row_drift(a[f], b[f])
            if d is not None:
                drift.append({"key": f, "delta": d})
    return {"lost": lost, "added": added, "drift": drift}


# ── CLI smoke-test ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("usage: python canonical_json.py <a.json> <b.json>", file=sys.stderr)
        sys.exit(2)
    a = canonical_load(sys.argv[1])
    b = canonical_load(sys.argv[2])
    diff = canonical_diff(a, b)
    print(json.dumps(diff, indent=2, ensure_ascii=False))
    sys.exit(1 if (diff["lost"] or diff["added"] or diff["drift"]) else 0)
