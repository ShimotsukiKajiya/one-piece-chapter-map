"""
Ingest Manual Source — append hand-entered claims from extended-media
sources (Vivre Card, Color Walk, OP Magazine, legacy databooks) into
canon_facts.json.

Per docs/canon-sources.md, extended-media sources are 🔵 LIKELY by
default — never auto-promoted to canon. Each ingested claim carries:

  - tier: "likely"  (the appropriate skepticism for revisable media)
  - source citation per the registered schema (with edition for Vivre
    Card so we can detect later silent revisions)
  - verified_on / verified_by

The pipeline:
  1. Maintainer creates / appends to a JSON file in data_manual/ named
     after the source (e.g. data_manual/vivre_card_initial_2018.json)
  2. Each entry is { subject, predicate, value, source_ref, notes }
  3. Run `py ingest_manual_source.py` — script validates every entry
     against canon-sources.md (source_type must be registered) and
     appends to canon_facts.json with stable IDs
  4. Running again is idempotent: existing claims with the same ID
     are replaced (so you can correct typos by editing the JSON)

Why a manual flow rather than scraping
- Vivre Cards are not available on a scrape-able wiki page.
- Color Walks would require copyright-violating image OCR.
- OP Magazine is paywalled.
- The honest answer is: maintainer transcribes, system ingests +
  cites + tiers appropriately.

Run:
  py ingest_manual_source.py             # ingest all data_manual/*.json
  py ingest_manual_source.py --file <p>  # ingest a single file
  py ingest_manual_source.py --dry-run   # validate + report, no write
  py ingest_manual_source.py --new vivre_card  # scaffold a starter file
"""
import os, sys, json, re
from datetime import date
from collections import defaultdict

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
MANUAL_DIR = os.path.join(DIR, "data_manual")
FACTS_PATH = os.path.join(DIR, "canon_facts.json")

VERIFIER = "ingest_manual_source.py v1"
TODAY    = date.today().isoformat()

# Source registry — must match docs/canon-sources.md. Adding a new source
# here without updating that doc will be flagged by audit.py.
REGISTERED_SOURCES = {
    "vivre_card":     {"default_tier": "likely",
                        "required_fields": ["edition"],
                        "id_prefix": "vivre"},
    "color_walk":     {"default_tier": "likely",
                        "required_fields": ["volume", "page", "section"],
                        "id_prefix": "cwalk"},
    "color_walk_oda": {"default_tier": "canon",
                        "required_fields": ["volume", "page"],
                        "id_prefix": "cwalk_oda",
                        "note": "Use only for explicitly Oda-attributed text."},
    "op_magazine_sbs": {"default_tier": "canon",
                        "required_fields": ["issue", "qa_id"],
                        "id_prefix": "opmag_sbs",
                        "note": "Reserved for OP Magazine SBS-format Q&As (Oda direct)."},
    "op_magazine":    {"default_tier": "likely",
                        "required_fields": ["issue", "section"],
                        "id_prefix": "opmag"},
    "databook_legacy":{"default_tier": "speculation",
                        "required_fields": ["book", "page"],
                        "id_prefix": "legacy",
                        "note": "Yellow/Red/Blue/Green/Grand. Stays at SPEC unless re-verified."},
    "light_novel":    {"default_tier": "likely",
                        "required_fields": ["title", "chapter"],
                        "id_prefix": "novel"},
}


def slugify(s):
    return re.sub(r"[^\w]+", "_", s).strip("_")[:80]


def validate_entry(e, source_type, file_label):
    """Return (errors_list, fact_dict_or_None)."""
    errs = []
    if source_type not in REGISTERED_SOURCES:
        errs.append(f"unknown source_type '{source_type}' "
                    f"(must be one of {list(REGISTERED_SOURCES)})")
        return errs, None

    spec = REGISTERED_SOURCES[source_type]
    for required_top in ("subject", "predicate", "value"):
        if not e.get(required_top):
            errs.append(f"missing required top-level field: {required_top}")

    src_ref = e.get("source_ref") or {}
    if not isinstance(src_ref, dict):
        errs.append("source_ref must be an object with the source's "
                    f"required fields ({spec['required_fields']})")
        return errs, None
    for rf in spec["required_fields"]:
        if rf not in src_ref:
            errs.append(f"source_ref missing required field for "
                        f"{source_type}: {rf}")

    if errs: return errs, None

    subject = e["subject"]
    predicate = e["predicate"]
    # Allow per-entry tier override but never UPGRADE above the source's
    # default — that would defeat the point of source-tier discipline.
    declared = e.get("tier")
    default_tier = spec["default_tier"]
    if declared in ("canon", "likely", "speculation", "rumour", "disproven"):
        # Tier rank: canon=4 > likely=3 > spec=2 > rumour=1 > disproven=0
        rank = {"canon":4, "likely":3, "speculation":2, "rumour":1, "disproven":0}
        if rank.get(declared, 2) > rank.get(default_tier, 2):
            errs.append(f"declared tier '{declared}' is stronger than "
                        f"source default '{default_tier}'. Use the source's "
                        f"default or weaker.")
            return errs, None
        tier = declared
    else:
        tier = default_tier

    # Stable ID
    src_key = "_".join(str(src_ref.get(rf, "")) for rf in spec["required_fields"])
    claim_id = f"manual:{spec['id_prefix']}:{slugify(subject)}:{slugify(predicate)}:{slugify(src_key)}"

    fact = {
        "id":        claim_id,
        "subject":   subject,
        "predicate": predicate,
        "value":     e["value"],
        "tier":      tier,
        "intent":    e.get("intent", "serious"),
        "sources":   [
            {"type": source_type, **src_ref},
        ],
        "evidence_notes": e.get("notes", "") or
            f"Hand-entered from {source_type} ({src_key}). File: {file_label}.",
        "verified_on": TODAY,
        "verified_by": VERIFIER,
    }
    return [], fact


def scaffold(source_type):
    if source_type not in REGISTERED_SOURCES:
        print(f"  ✗ unknown source_type '{source_type}'")
        sys.exit(1)
    spec = REGISTERED_SOURCES[source_type]
    os.makedirs(MANUAL_DIR, exist_ok=True)
    path = os.path.join(MANUAL_DIR, f"{source_type}_TEMPLATE.json")
    template = {
        "source_type": source_type,
        "default_tier": spec["default_tier"],
        "_doc": (f"Each entry needs: subject, predicate, value, "
                 f"source_ref (with required fields: {spec['required_fields']}), "
                 f"and optional notes. Tier defaults to "
                 f"'{spec['default_tier']}' per canon-sources.md."),
        "entries": [
            {
                "subject":   "Roronoa Zoro",
                "predicate": "favorite_food",
                "value":     "white rice + sea king meat",
                "source_ref": {rf: ("EXAMPLE_" + rf.upper()) for rf in spec["required_fields"]},
                "notes":     "Replace EXAMPLE_X values with the real source location.",
            },
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Scaffolded {path}")
    print(f"    Edit it, then run `py ingest_manual_source.py`.")


def main():
    args = sys.argv[1:]
    dry  = "--dry-run" in args
    if "--new" in args:
        i = args.index("--new")
        scaffold(args[i + 1] if i + 1 < len(args) else "vivre_card")
        return
    files = []
    if "--file" in args:
        i = args.index("--file")
        files = [args[i + 1]]
    else:
        if not os.path.isdir(MANUAL_DIR):
            print(f"  ⚠ {MANUAL_DIR} doesn't exist yet.")
            print(f"    Run: py ingest_manual_source.py --new vivre_card")
            return
        files = [os.path.join(MANUAL_DIR, f)
                 for f in sorted(os.listdir(MANUAL_DIR))
                 if f.endswith(".json") and not f.endswith("_TEMPLATE.json")]
    if not files:
        print("  Nothing to ingest. Use --new <source_type> to scaffold a starter file.")
        return

    facts = json.load(open(FACTS_PATH, encoding="utf-8")) if os.path.exists(FACTS_PATH) else []
    facts_by_id = {f["id"]: f for f in facts}

    print("=" * 60)
    print(f"  Ingest manual sources  ({len(files)} file(s))")
    print(f"  Mode: {'DRY RUN' if dry else 'WRITE'}")
    print("=" * 60); print()

    total_added  = 0
    total_failed = 0
    by_source    = defaultdict(int)

    for path in files:
        if not os.path.exists(path):
            print(f"  ✗ {path} not found"); continue
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  ✗ {path}: invalid JSON ({e})"); total_failed += 1; continue
        source_type = doc.get("source_type")
        entries = doc.get("entries") or []
        label = os.path.basename(path)
        print(f"  · {label}: {len(entries)} entries  source_type={source_type}")

        for i, e in enumerate(entries):
            errs, fact = validate_entry(e, source_type, label)
            if errs:
                total_failed += 1
                for err in errs: print(f"      ✗ entry #{i+1}: {err}")
                continue
            facts_by_id[fact["id"]] = fact
            total_added += 1
            by_source[source_type] += 1

    print()
    print(f"  ✓ Validated + ingested : {total_added}")
    if total_failed: print(f"  ✗ Validation failures   : {total_failed}")
    if by_source:
        print(f"  By source:")
        for s, n in by_source.items(): print(f"    {s:20s} {n:>4}")

    if dry:
        print("  (dry run — canon_facts.json not modified)")
        return

    if total_added:
        merged = list(facts_by_id.values())
        with open(FACTS_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Wrote canon_facts.json  ({len(merged):,} total facts)")
    print("=" * 60)


if __name__ == "__main__":
    main()
