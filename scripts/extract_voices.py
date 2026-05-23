"""Extract voice actor relationships from punk_records.json.

Produces relationships/_pending/voices.json — one row per character/VA/language
triple. Voice actor IDs (va:NNNNN) are built lazily from entity_registry.json
the first time a new name is seen.

Shape of each row:
    {
        "from": "va:00001",          # voice actor
        "to":   "chr:02499",         # character
        "lang": "jp",                # "jp" or "en"
        "src":  "wiki",
        "name": "Mayumi Tanaka"      # VA display name, baked in for convenience
    }
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib import query as _q

REGISTRY_PATH = ROOT / "entity_registry.json"
PENDING_DIR   = ROOT / "relationships" / "_pending"

# Characters who are not voice actors (scraper noise in the VA fields)
_SKIP_TOKENS = {
    "n/a", "na", "none", "unknown", "-", "–", "—", "tba", "tbd",
}


def slugify(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    return re.sub(r"-+", "-", name) or "unknown"


def parse_va_names(raw: str) -> list[str]:
    """Split a raw VA string into individual canonical names.

    Handles separators: ';' and '·'.
    Strips qualifiers in parentheses/brackets, episode ranges, role prefixes.
    """
    if not raw:
        return []
    # Normalise separator — replace · with ;
    raw = raw.replace("·", ";")
    parts = [p.strip() for p in raw.split(";")]
    names: list[str] = []
    for part in parts:
        if not part:
            continue
        # Strip role prefix like "Bas: " or "Head: "
        part = re.sub(r"^[A-Za-z][a-z']+:\s*", "", part)
        # Strip everything from first '(' or '[' onward
        base = re.sub(r"\s*[\(\[].*", "", part).strip()
        # Strip trailing episode ranges like " ep. 70-957"
        base = re.sub(r"\s+ep\.\s+[\d\-,+]+$", "", base).strip()
        if not base or base.lower() in _SKIP_TOKENS:
            continue
        # Must look like a name (at least 2 chars, contains a letter)
        if len(base) >= 2 and re.search(r"[A-Za-z　-鿿゠-ヿ]", base):
            names.append(base)
    return names


def load_registry() -> dict:
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_registry(reg: dict) -> None:
    with open(REGISTRY_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main(dry_run: bool = False) -> None:
    pr_path = ROOT / "punk_records.json"
    with open(pr_path, encoding="utf-8") as f:
        records: dict = json.load(f)

    entity_idx = _q._entity_index()   # name.lower() -> id
    name_map   = _q._name_index()     # id -> display name (for va if already assigned)

    registry = load_registry()
    # Ensure va counter exists
    if "va" not in registry.setdefault("next", {}):
        registry["next"]["va"] = 1

    # Build va name -> va:id map from existing registry entries
    # (entity_index maps va names too once we add them)
    va_index: dict[str, str] = {}   # lower(name) -> va:id
    for key, eid in entity_idx.items():
        if eid.startswith("va:"):
            va_index[key] = eid

    # ── pass 1: assign va:IDs for all new names ──────────────────────────────
    new_vas: dict[str, str] = {}   # canonical_name -> va:id
    all_va_canonical: dict[str, str] = {}   # lower(name) -> canonical_name

    for name, rec in records.items():
        if not isinstance(rec, dict):
            continue
        for lang, field in (("jp", "voice_actor_jp"), ("en", "voice_actor_en")):
            for va_name in parse_va_names(rec.get(field) or ""):
                key = va_name.lower()
                if key not in va_index and key not in new_vas:
                    va_id = f"va:{registry['next']['va']:05d}"
                    registry["next"]["va"] += 1   # advance always; save is skipped in dry-run
                    new_vas[va_name] = va_id
                    va_index[key] = va_id
                    all_va_canonical[key] = va_name
                elif key in all_va_canonical:
                    pass  # already registered
                else:
                    all_va_canonical[key] = va_name  # use first canonical form seen

    # ── pass 2: build rows ────────────────────────────────────────────────────
    rows: list[dict] = []
    unresolved_chars: list[str] = []

    for name, rec in records.items():
        if not isinstance(rec, dict):
            continue
        chr_id = entity_idx.get(name.lower())
        if not chr_id or not chr_id.startswith("chr:"):
            unresolved_chars.append(name)
            continue

        for lang, field in (("jp", "voice_actor_jp"), ("en", "voice_actor_en")):
            for va_name in parse_va_names(rec.get(field) or ""):
                key = va_name.lower()
                va_id = va_index.get(key)
                if not va_id:
                    print(f"  WARN unresolved VA: {va_name!r}", file=sys.stderr)
                    continue
                rows.append({
                    "from": va_id,
                    "to":   chr_id,
                    "lang": lang,
                    "src":  "wiki",
                    "name": all_va_canonical.get(key, va_name),
                })

    # ── report ────────────────────────────────────────────────────────────────
    langs = {"jp": 0, "en": 0}
    for r in rows:
        langs[r["lang"]] = langs.get(r["lang"], 0) + 1
    unique_vas = len({r["from"] for r in rows})

    print(f"  Rows:           {len(rows):,}")
    print(f"  JP rows:        {langs['jp']:,}")
    print(f"  EN rows:        {langs['en']:,}")
    print(f"  Unique VAs:     {unique_vas:,}  ({len(new_vas)} new IDs assigned)")
    print(f"  Unresolved chr: {len(unresolved_chars)}")
    if unresolved_chars[:5]:
        print(f"  (sample): {unresolved_chars[:5]}")

    if dry_run:
        print("  [dry-run] no files written")
        return

    # Save updated registry (va counter advanced)
    save_registry(registry)

    # Write pending shard
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PENDING_DIR / "voices.json"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Written: {out_path}")

    # Patch entity_index.json with new va entries
    idx_path = ROOT / "entity_index.json"
    with open(idx_path, encoding="utf-8") as f:
        idx: dict = json.load(f)
    added = 0
    for va_name, va_id in new_vas.items():
        key = va_name.lower()
        if key not in idx:
            idx[key] = va_id
            idx[va_id] = va_id  # self-reference so ID is resolvable
            added += 1
    with open(idx_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(idx, f, ensure_ascii=False)
        f.write("\n")
    print(f"  entity_index.json: +{added} VA entries")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    main(dry_run=args.dry_run)
