"""
Publish API — emits a static JSON tree under api/ that other tools can
consume. No backend, no auth, no rate-limits — just versioned static
files that GitHub Pages serves directly.

Endpoints produced:
  api/v1/manifest.json           — index of every endpoint + last-built timestamp
  api/v1/canon_facts.json        — full canonical fact ledger
  api/v1/characters.json         — slim character index (name + key fields)
  api/v1/character/<slug>.json   — full character profile per character
  api/v1/devil_fruits.json       — full DF registry
  api/v1/devil_fruit/<slug>.json — per-fruit profile
  api/v1/sbs.json                — slim SBS index (id_num, vol, q, snippet)
  api/v1/sbs/<num>.json          — per-Q&A full content
  api/v1/theories.json           — full theories list
  api/v1/arcs.json               — arc structure
  api/v1/crews.json              — crew rosters
  api/v1/portraits.json          — character portrait URLs

Usage:
  py publish_api.py             # write everything
  py publish_api.py --dry-run   # report only

The API is read-only and rebuilds on every refresh.
"""
import os, sys, json, re, csv
from datetime import datetime

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR    = os.path.dirname(__file__)
API    = os.path.join(DIR, "api", "v1")
TODAY  = datetime.utcnow().isoformat(timespec="seconds") + "Z"


def slugify(s):
    return re.sub(r'[^\w-]', '_', s).strip('_')[:80]


def write_json(rel_path, data, dry):
    if dry: return 0
    full = os.path.join(API, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    return os.path.getsize(full)


def main():
    dry = "--dry-run" in sys.argv

    print("=" * 60)
    print(f"  Publish API → {API}")
    if dry: print("  DRY RUN")
    print("=" * 60); print()

    if not dry:
        os.makedirs(API, exist_ok=True)

    manifest = {
        "name":         "The Shimotsuki Codex API",
        "version":      "1",
        "license":      "Data: fan project, non-commercial. One Piece © Eiichiro Oda / Shueisha.",
        "generated_on": TODAY,
        "endpoints":    {},
    }
    total_files = 0
    total_bytes = 0

    def serve(rel, data, *, label=None):
        nonlocal total_files, total_bytes
        size = write_json(rel, data, dry)
        manifest["endpoints"][rel] = {
            "label": label or rel,
            "bytes": size,
        }
        total_files += 1
        total_bytes += size

    # ── PRIMARY DATASETS ─────────────────────────────────────
    # Canon facts
    fp = os.path.join(DIR, "canon_facts.json")
    if os.path.exists(fp):
        facts = json.load(open(fp, encoding="utf-8"))
        serve("canon_facts.json", facts, label=f"All {len(facts):,} canon facts")
        # Per-subject grouping for individual lookup
        by_subj = {}
        for f in facts: by_subj.setdefault(f["subject"], []).append(f)
        for subject, subject_facts in by_subj.items():
            serve(f"canon_facts/{slugify(subject)}.json", subject_facts,
                  label=f"Canon facts for {subject}")

    # Characters
    pr_path = os.path.join(DIR, "punk_records.json")
    if os.path.exists(pr_path):
        pr = json.load(open(pr_path, encoding="utf-8"))
        # Slim index for the /characters.json endpoint
        slim = []
        for name, rec in pr.items():
            if not rec.get("found"): continue
            slim.append({
                "name": name,
                "epithet": rec.get("epithet"),
                "affiliation": rec.get("affiliation"),
                "appearances": rec.get("appearances"),
                "bounty_value": rec.get("bounty_value"),
                "devil_fruit_name": rec.get("devil_fruit_name"),
            })
        serve("characters.json", slim, label=f"{len(slim):,} characters (slim)")
        # Per-character full profile
        for name, rec in pr.items():
            if not rec.get("found"): continue
            serve(f"character/{slugify(name)}.json", rec,
                  label=f"Full profile: {name}")

    # Devil Fruits
    df_path = os.path.join(DIR, "devil_fruits.json")
    if os.path.exists(df_path):
        df = json.load(open(df_path, encoding="utf-8"))
        serve("devil_fruits.json", df, label=f"{sum(1 for v in df.values() if isinstance(v, dict) and v.get('found')):,} fruits")
        for name, rec in df.items():
            if isinstance(rec, dict) and rec.get("found"):
                serve(f"devil_fruit/{slugify(name)}.json", rec,
                      label=f"Devil Fruit: {name}")

    # SBS
    sbs_path = os.path.join(DIR, "sbs_archive.json")
    if os.path.exists(sbs_path):
        sbs = json.load(open(sbs_path, encoding="utf-8"))
        # Slim index
        idx = [{"id_num": e.get("id_num"), "volume": e.get("volume"),
                "name": e.get("name"), "category": e.get("category"),
                "snippet": (e.get("question") or "")[:160]}
               for e in sbs if e.get("id_num") is not None]
        serve("sbs.json", idx, label=f"{len(idx):,} SBS Q&As (index)")
        # Per-entry full content
        for e in sbs:
            n = e.get("id_num")
            if n is None: continue
            serve(f"sbs/{str(n).zfill(4)}.json", e,
                  label=f"SBS #{str(n).zfill(4)}")

    # Theories
    th_path = os.path.join(DIR, "theories_import.json")
    if os.path.exists(th_path):
        theories = json.load(open(th_path, encoding="utf-8"))
        serve("theories.json", theories, label=f"{len(theories):,} theories")

    # Arcs
    arcs_path = os.path.join(DIR, "arcs.json")
    if os.path.exists(arcs_path):
        arcs = json.load(open(arcs_path, encoding="utf-8"))
        serve("arcs.json", arcs, label=f"{len(arcs)} arcs")

    # Crews
    crews_path = os.path.join(DIR, "crews.json")
    if os.path.exists(crews_path):
        crews = json.load(open(crews_path, encoding="utf-8"))
        serve("crews.json", crews, label=f"{len((crews.get('crews') or {}))} crews")

    # Portraits
    portraits_path = os.path.join(DIR, "portraits.json")
    if os.path.exists(portraits_path):
        portraits = json.load(open(portraits_path, encoding="utf-8"))
        serve("portraits.json", portraits, label=f"{len(portraits):,} portraits")

    # Cover stories
    cs_path = os.path.join(DIR, "cover_stories.json")
    if os.path.exists(cs_path):
        cs = json.load(open(cs_path, encoding="utf-8"))
        serve("cover_stories.json", cs, label=f"{len(cs)} cover stories")

    # Manifest last (so endpoints are populated)
    if not dry:
        with open(os.path.join(API, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    total_files += 1

    print(f"  ✓ Wrote {total_files:,} JSON files")
    print(f"    Total bytes: {total_bytes / 1024 / 1024:.1f} MB")
    print(f"  Live at: https://shimotsukicodex.com/api/v1/manifest.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
