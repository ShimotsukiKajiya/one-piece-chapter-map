"""
The Codex — Curator / Refresh Pipeline

Runs the full data refresh end-to-end:
  scrape → clean → bake → audit → (optional) commit + push

Designed to be safe to run unattended (e.g. weekly via the cloud schedule).
Each stage is a subprocess so a crash in one doesn't take the rest down.

Run:
  py refresh.py                # full pipeline, no git
  py refresh.py --commit       # also commit changed data files
  py refresh.py --push         # commit + push (implies --commit)
  py refresh.py --skip-scrape  # only re-clean + bake + audit
  py refresh.py --quick        # skip the long scrapers (punk + sbs images)
  py refresh.py --parallel 2   # run scraper stages 2-at-a-time (faster)
  py refresh.py --force-bake   # re-bake even if inputs unchanged
  py refresh.py --dry-run      # print stages, run nothing
"""

import sys, os, subprocess, time, hashlib, json
from datetime import datetime

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass


# ── BAKE SKIP-IF-UNCHANGED ──────────────────────────────────────
# Hash the data files bake consumes; if nothing changed since last bake,
# skip the bake stage. Saves a few seconds per refresh and removes
# noise from "everything is identical" weekly runs.
BAKE_INPUTS = [
    "appearances.csv", "sbs_archive.json", "volume_covers.json",
    "cover_stories.json", "punk_records.json",
    "portraits.json", "canon_facts.json", "theories_import.json",
]
BAKE_MANIFEST = "cache/bake_manifest.json"


def _hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def bake_inputs_unchanged(root):
    manifest_path = os.path.join(root, BAKE_MANIFEST)
    if not os.path.exists(manifest_path): return False
    try:
        old = json.load(open(manifest_path, encoding="utf-8"))
    except Exception:
        return False
    for f in BAKE_INPUTS:
        p = os.path.join(root, f)
        if not os.path.exists(p): continue
        if old.get(f) != _hash_file(p): return False
    return True


def write_bake_manifest(root):
    manifest_path = os.path.join(root, BAKE_MANIFEST)
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    out = {}
    for f in BAKE_INPUTS:
        p = os.path.join(root, f)
        if os.path.exists(p): out[f] = _hash_file(p)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

DIR = os.path.dirname(os.path.abspath(__file__))
PY  = sys.executable

# (label, script, args, tags) — tags: "scrape" "clean" "bake" "audit" "long"
STAGES = [
    ("Chapter scraper",      "scraper.py",              ["--update"],{"scrape"}),
    ("Cover scraper",        "covers_scraper.py",       [],          {"scrape"}),  # gap-aware by default
    ("Cover stories",        "cover_stories_scraper.py",["--gaps"],  {"scrape"}),
    ("SBS scraper",          "sbs_scraper.py",          ["--gaps"],  {"scrape"}),
    ("SBS image attribution","sbs_images_scraper.py",   [],          {"scrape", "long"}),
    ("Theory scraper",       "theory_scraper.py",       [],          {"scrape"}),
    ("Punk Records (gaps)",  "punk_records_scraper.py", ["--gaps"],  {"scrape", "long"}),
    ("Form image scraper",   "form_image_scraper.py",   [],          {"scrape"}),
    ("Name extraction",      "extract_names.py",        [],          {"clean"}),
    ("Clean credits",        "clean_credits.py",        [],          {"clean"}),
    ("Clean wikitables",     "clean_wikitables.py",     [],          {"clean"}),
    ("SBS categoriser",      "sbs_categorizer.py",      [],          {"clean", "ai"}),
    ("Theory analyser",      "theory_analyzer.py",      [],          {"clean", "ai"}),
    ("Theory numbers",       "assign_theory_numbers.py",[],          {"clean"}),
    ("SBS IDs",              "assign_sbs_ids.py",       [],          {"clean"}),
    ("Manga facts",          "extract_manga_facts.py",  [],          {"clean"}),
    ("Manual sources",       "ingest_manual_source.py", [],          {"clean"}),
    ("Verify wiki vs SBS",   "verify.py",               [],          {"clean"}),
    ("Find conflicts",       "find_conflicts.py",       [],          {"clean"}),
    ("Bake site",            "bake.py",                 [],          {"bake"}),
    ("Audit",                "audit.py",                [],          {"audit"}),
]


def run(label, script, args, dry, capture=False):
    """Run a stage. If capture=True, return (rc, dt, output) instead of streaming."""
    path = os.path.join(DIR, script)
    if not os.path.exists(path):
        msg = f"  ⚠  skip — {script} not found"
        return (0, 0.0, msg) if capture else 0
    cmd = [PY, path, *args]
    if not capture:
        print(f"\n▶ {label}  ({script} {' '.join(args)})")
    if dry:
        return (0, 0.0, "") if capture else 0
    t0 = time.time()
    try:
        if capture:
            proc = subprocess.run(cmd, cwd=DIR, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8", errors="replace")
            rc, out = proc.returncode, proc.stdout
        else:
            rc = subprocess.call(cmd, cwd=DIR)
            out = ""
    except KeyboardInterrupt:
        print("  ⛔ interrupted")
        return (130, 0.0, "") if capture else 130
    dt = time.time() - t0
    status = "✓" if rc == 0 else f"✗ rc={rc}"
    if not capture:
        print(f"  {status}  ({dt:.1f}s)")
    return (rc, dt, out) if capture else rc


def run_parallel(stages, dry, max_workers):
    """Run independent stages concurrently. Output is captured then printed
    in completion order so logs stay readable."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    print(f"\n  (running {len(stages)} scraper stages in parallel, max {max_workers})")
    failed = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(run, lbl, sc, ar, dry, True): lbl
                   for (lbl, sc, ar, _) in stages}
        for fut in as_completed(futures):
            label = futures[fut]
            rc, dt, out = fut.result()
            status = "✓" if rc == 0 else f"✗ rc={rc}"
            print(f"\n▶ {label}  {status}  ({dt:.1f}s)")
            if out: print(out.rstrip())
            if rc != 0: failed.append(label)
    return failed


def git(args, dry):
    cmd = ["git", *args]
    print(f"\n$ {' '.join(cmd)}")
    if dry: return 0
    return subprocess.call(cmd, cwd=DIR)


def main():
    a = sys.argv[1:]
    dry         = "--dry-run" in a
    skip_scrape = "--skip-scrape" in a
    quick       = "--quick" in a
    do_commit   = "--commit" in a or "--push" in a
    do_push     = "--push" in a

    print(f"=== Codex Refresh — {datetime.now().isoformat(timespec='seconds')} ===")
    if dry: print("(dry run)")

    failed = []
    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    force_bake  = "--force-bake" in a
    parallel    = 1
    if "--parallel" in a:
        try: parallel = int(a[a.index("--parallel") + 1])
        except (ValueError, IndexError): parallel = 2

    # Split stages by phase so parallel only applies to scrapers
    scrape_stages, other_stages = [], []
    for entry in STAGES:
        label, script, args_, tags = entry
        if skip_scrape and "scrape" in tags: continue
        if quick and "long" in tags: continue
        if "ai" in tags and not has_api_key:
            other_stages.append(("__skipped__", entry, "ANTHROPIC_API_KEY not set"))
            continue
        (scrape_stages if "scrape" in tags else other_stages).append(entry)

    # Phase 1: scrapers (optionally parallel)
    if scrape_stages:
        if parallel > 1:
            failed.extend(run_parallel(scrape_stages, dry, parallel))
        else:
            for label, script, args_, tags in scrape_stages:
                rc = run(label, script, args_, dry)
                if rc != 0: failed.append(label)

    # Phase 2: cleaners → bake → audit (always sequential)
    for entry in other_stages:
        if isinstance(entry, tuple) and entry[0] == "__skipped__":
            _, (label, *_), reason = entry
            print(f"\n▶ {label}  (skipped — {reason})")
            continue
        label, script, args_, tags = entry
        if "bake" in tags and not force_bake and bake_inputs_unchanged(DIR):
            print(f"\n▶ {label}  (skipped — inputs unchanged since last bake)")
            continue
        rc = run(label, script, args_, dry)
        if "bake" in tags and rc == 0 and not dry:
            write_bake_manifest(DIR)
        if rc != 0 and "audit" not in tags:
            failed.append(label)

    print("\n" + "=" * 60)
    if failed:
        print(f"  ⚠  {len(failed)} stage(s) failed: {', '.join(failed)}")
    else:
        print("  ✓  all stages completed")
    print("=" * 60)

    if do_commit and not failed:
        # Stage data files only (not code)
        DATA_FILES = [
            "appearances.csv", "sbs_archive.json", "theories_import.json",
            "volume_covers.json", "cover_stories.json", "punk_records.json",
            "ships.json", "characters.json",
            "docs/audit_report.md",
        ]
        existing = [f for f in DATA_FILES if os.path.exists(os.path.join(DIR, f))]
        # Also stage baked output dir if present
        if os.path.isdir(os.path.join(DIR, "baked")):
            existing.append("baked")

        git(["add", *existing], dry)
        msg = f"chore(data): weekly refresh {datetime.now().strftime('%Y-%m-%d')}"
        rc = git(["commit", "-m", msg], dry)
        if rc != 0:
            print("  (nothing to commit, or commit failed)")
        elif do_push:
            git(["push"], dry)

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
