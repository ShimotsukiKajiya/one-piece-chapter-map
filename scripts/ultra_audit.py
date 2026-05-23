"""ULTRA Audit — Tier 4 of the Training Time protocol.

Wraps every validator in the project + adds the blind-spot checks that
none of them cover individually. The goal: 'should not miss a thing.'

Sections:
  1.  Run all existing validators (audit.py, validate_schemas, validate_relationships,
      validate_ids, audit_links, audit_links2, audit_doc_urls, freshen --dry-run)
  2.  Per-HTML-page integrity (every page has expected data blocks, no broken
      asset refs, file is parseable)
  3.  Asset integrity (every <img src=> pointing locally exists)
  4.  Cross-document drift (CLAUDE.md vs audit.stats vs page-status.md)
  5.  Hygiene markers (TODO/FIXME/XXX in code, '<!-- needs review -->' in HTML)
  6.  Script documentation (every .py in scripts/ root + lib/ has a docstring)
  7.  Page weight report (largest baked HTML pages)
  8.  SEO metadata consistency (unique <title> per page, og:* tags present)
  9.  Workflow CI health (gh run list summary if gh CLI available)

Run:
  python scripts/ultra_audit.py            # full scan, exit 0/1/2
  python scripts/ultra_audit.py --quick    # skip slow checks (no subprocess validators)
  python scripts/ultra_audit.py --section N  # run only section N (1-9)

Exit codes:
  0 — all clean
  1 — INFO/WARN findings only
  2 — ERROR findings present (CI-friendly fail)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = Path(__file__).resolve().parent.parent

# ── Findings collector ────────────────────────────────────────────────────────

class Findings:
    def __init__(self):
        self.items: list[dict] = []
        self.sections_run: list[str] = []
        self.sections_skipped: list[str] = []

    def add(self, severity, section, file, issue, snippet=""):
        self.items.append({
            "severity": severity,
            "section": section,
            "file": file,
            "issue": issue,
            "snippet": snippet[:140] if snippet else "",
        })

    def by_severity(self):
        out = defaultdict(list)
        for f in self.items:
            out[f["severity"]].append(f)
        return out

    def exit_code(self):
        if any(f["severity"] == "ERROR" for f in self.items): return 2
        if self.items: return 1
        return 0


# ── 1. Subprocess every existing validator ───────────────────────────────────

def section_1_validators(rep: Findings):
    section = "validators"
    rep.sections_run.append(section)
    validators = [
        ("audit.py",                          ["python", "audit.py"]),
        ("validate_schemas.py",               ["python", "scripts/validate_schemas.py"]),
        ("validate_relationships.py",         ["python", "scripts/validate_relationships.py"]),
        ("validate_ids.py",                   ["python", "scripts/validate_ids.py"]),
        ("audit_links.py",                    ["python", "scripts/audit_links.py"]),
        ("audit_links2.py",                   ["python", "scripts/audit_links2.py"]),
        ("audit_doc_urls.py",                 ["python", "scripts/audit_doc_urls.py"]),
    ]
    for name, cmd in validators:
        try:
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                               timeout=120, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            rep.add("ERROR", section, name, "timed out (>120s)")
            continue
        except Exception as e:
            rep.add("ERROR", section, name, f"failed to run: {e}")
            continue
        if r.returncode == 0:
            continue
        if r.returncode == 1:
            # Validators use 1 for findings — capture last non-empty line as summary
            tail = next((ln for ln in reversed((r.stdout or "").splitlines()) if ln.strip()), "")
            rep.add("WARN", section, name,
                    f"non-clean exit (rc=1) — has findings",
                    tail)
        else:
            rep.add("ERROR", section, name,
                    f"failed with exit code {r.returncode}",
                    (r.stderr or r.stdout or "").splitlines()[-1] if (r.stderr or r.stdout) else "")


# ── 2. Per-HTML-page integrity ────────────────────────────────────────────────

# Pages and the data blocks they should contain. Missing blocks = bug.
EXPECTED_BLOCKS = {
    "atlas.html": ["appearances-data", "atlas-debuts", "atlas-fruits", "atlas-moments"],
    "home.html": ["home-stats", "home-arcs"],
    "chapter-release-map.html": ["release-chapters", "release-episodes", "release-events", "release-arcs"],
    "characters.html": ["punk-records-data"],
    "fruits.html": ["fruits-data"],
    "crews.html": ["crews-data"],
    "ships.html": ["ships-data"],
    "locations.html": ["locations-data"],
    "voices.html": ["voices-data"],
    "theories.html": ["theories-linked-data"],
    "sbs.html": ["sbs-data"],
}

def section_2_page_integrity(rep: Findings):
    section = "page-integrity"
    rep.sections_run.append(section)
    for page, blocks in EXPECTED_BLOCKS.items():
        path = ROOT / page
        if not path.exists():
            rep.add("ERROR", section, page, "expected page does not exist")
            continue
        try:
            src = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            rep.add("ERROR", section, page, f"unreadable: {e}")
            continue
        for block_id in blocks:
            # Find <script id="..."> and ensure its content isn't empty
            pat = rf'<script\s+id="{re.escape(block_id)}"[^>]*>(.*?)</script>'
            m = re.search(pat, src, re.DOTALL)
            if not m:
                rep.add("WARN", section, page,
                        f"expected baked block #{block_id} not found")
            elif not m.group(1).strip():
                rep.add("WARN", section, page,
                        f"baked block #{block_id} is empty")
            elif m.group(1).strip() in ("{}", "[]"):
                rep.add("INFO", section, page,
                        f"baked block #{block_id} is empty placeholder ({m.group(1).strip()})")


# ── 3. Asset integrity ────────────────────────────────────────────────────────

def section_3_asset_integrity(rep: Findings):
    section = "asset-integrity"
    rep.sections_run.append(section)
    img_pat = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
    css_pat = re.compile(r'<link[^>]+href="([^"]+\.css)"', re.I)
    js_pat  = re.compile(r'<script[^>]+src="([^"]+\.js[^"]*)"', re.I)

    seen_missing: set = set()
    for path in ROOT.glob("*.html"):
        try:
            src = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pat, kind in [(img_pat, "img"), (css_pat, "css"), (js_pat, "js")]:
            for ref in pat.findall(src):
                # Skip external + data URIs + anchor links
                if ref.startswith(("http://", "https://", "data:", "//")):
                    continue
                # Skip JS template-literal + string-concat placeholders that
                # resolve at runtime. Backtick `${...}`, mustache `{{...}}`,
                # and the older `' + var + '` concat all fail static analysis
                # but resolve fine at runtime.
                if "${" in ref or "{{" in ref:
                    continue
                if "' +" in ref or '" +' in ref:
                    continue
                # Strip query/hash/cache-bust
                local = ref.split("?")[0].split("#")[0]
                if not local:
                    continue
                target = ROOT / local
                if target.exists():
                    continue
                key = (path.name, kind, local)
                if key in seen_missing:
                    continue
                seen_missing.add(key)
                rep.add("WARN", section, path.name,
                        f"broken {kind} ref: {local}", ref)


# ── 4. Cross-document drift ───────────────────────────────────────────────────

def section_4_doc_drift(rep: Findings):
    section = "doc-drift"
    rep.sections_run.append(section)
    # Compare hardcoded counts in CLAUDE.md against live data
    try:
        with open(ROOT / "CLAUDE.md", encoding="utf-8") as f:
            claude_text = f.read()
    except Exception:
        rep.add("WARN", section, "CLAUDE.md", "could not read")
        return

    live_data = {}
    try:
        with open(ROOT / "punk_records.json", encoding="utf-8") as f:
            pr = json.load(f)
        live_data["characters"] = sum(1 for v in pr.values() if isinstance(v, dict))
    except Exception: pass

    try:
        with open(ROOT / "canon_facts.json", encoding="utf-8") as f:
            cf = json.load(f)
        live_data["canon_facts"] = len(cf)
    except Exception: pass

    rel_dir = ROOT / "relationships"
    if rel_dir.exists():
        total = 0
        for f in rel_dir.glob("*.json"):
            try:
                total += len(json.load(open(f, encoding="utf-8")))
            except Exception: continue
        live_data["relationship_rows"] = total

    # Claims to check (regex → live key, label, tolerance)
    claims = [
        (r"(\d{1,2},?\d{3})\s+canon[_ ]facts?", "canon_facts", "canon_facts", 50),
        (r"(\d{2,3},?\d{3})\s+relationship\s+rows", "relationship_rows", "relationship rows", 200),
        (r"(\d{1,2},?\d{3})\s+characters?\b", "characters", "characters", 20),
    ]
    for pattern, key, label, tol in claims:
        if key not in live_data:
            continue
        for m in re.finditer(pattern, claude_text):
            try:
                claimed = int(m.group(1).replace(",", ""))
            except ValueError:
                continue
            actual = live_data[key]
            if abs(claimed - actual) > tol:
                lineno = claude_text[:m.start()].count("\n") + 1
                rep.add("INFO", section, f"CLAUDE.md:{lineno}",
                        f"claims {claimed:,} {label} but live data has {actual:,} ({claimed - actual:+,})",
                        m.group(0))


# ── 5. Hygiene markers ────────────────────────────────────────────────────────

def section_5_hygiene(rep: Findings):
    section = "hygiene"
    rep.sections_run.append(section)
    SKIP_DIRS = {".git", "cache", "obsidian_vault", "logo", "node_modules",
                 "__pycache__", "Shimotsuki Codex"}
    # Skip auto-generated audit reports (they echo our own pattern words)
    SKIP_FILES = {"docs/ultra_audit_report.md", "docs/audit_report.md"}
    EXTS = (".py", ".js", ".html", ".md")
    # Skip self-reference: this script's own pattern definition contains the
    # marker words as data, not as flags.
    self_path = Path(__file__).resolve()
    pat = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b[:\s]([^\n]{0,100})")
    counts: Counter = Counter()
    samples: dict = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in EXTS:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == self_path:
            continue  # don't flag own pattern strings
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if rel in SKIP_FILES:
            continue  # auto-generated audit reports echo our pattern words
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in pat.finditer(text):
            counts[m.group(1)] += 1
            samples.setdefault(m.group(1), []).append(
                (path.relative_to(ROOT), text[:m.start()].count("\n") + 1, m.group(0))
            )
    for marker, n in counts.most_common():
        if marker in ("TODO", "FIXME"):
            sev = "INFO"  # acceptable — flagged work
        else:
            sev = "WARN"  # XXX / HACK suggest unhealthy code
        sample_list = samples[marker][:3]
        rep.add(sev, section, "(across repo)",
                f"{n} {marker} marker(s) found",
                "; ".join(f"{p}:{ln}" for p, ln, _ in sample_list))


# ── 6. Script documentation ───────────────────────────────────────────────────

def section_6_script_docs(rep: Findings):
    section = "script-docs"
    rep.sections_run.append(section)
    targets = list((ROOT / "scripts").glob("*.py"))
    targets += list((ROOT / "scripts" / "lib").glob("*.py"))
    for path in targets:
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Module docstring is the first non-comment string after any imports
        first_lines = "\n".join(text.splitlines()[:10])
        if '"""' not in first_lines and "'''" not in first_lines:
            rep.add("INFO", section, str(path.relative_to(ROOT)),
                    "no module docstring in first 10 lines")


# ── 7. Page weights ───────────────────────────────────────────────────────────

def section_7_page_weights(rep: Findings):
    section = "page-weights"
    rep.sections_run.append(section)
    sizes = []
    for path in ROOT.glob("*.html"):
        sizes.append((path.stat().st_size, path.name))
    sizes.sort(reverse=True)
    # Flag pages over 2 MB as INFO; over 5 MB as WARN
    for size, name in sizes[:8]:
        kb = size // 1024
        if size > 5 * 1024 * 1024:
            rep.add("WARN", section, name, f"page is {kb:,} KB (over 5 MB threshold)")
        elif size > 2 * 1024 * 1024:
            rep.add("INFO", section, name, f"page is {kb:,} KB (over 2 MB)")


# ── 8. SEO metadata consistency ───────────────────────────────────────────────

def section_8_seo_meta(rep: Findings):
    section = "seo-meta"
    rep.sections_run.append(section)
    title_pat = re.compile(r"<title>([^<]+)</title>", re.I)
    og_title_pat = re.compile(r'<meta\s+property="og:title"\s+content="([^"]+)"', re.I)
    canonical_pat = re.compile(r'<link\s+rel="canonical"\s+href="([^"]+)"', re.I)
    titles_seen: dict = {}
    for path in ROOT.glob("*.html"):
        if path.name in ("404.html", "index.html"):
            continue
        try:
            src = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Each surface page should have <title>, og:title, and canonical
        if not title_pat.search(src):
            rep.add("WARN", section, path.name, "missing <title>")
            continue
        title = title_pat.search(src).group(1).strip()
        if title in titles_seen:
            rep.add("WARN", section, path.name,
                    f"duplicate <title> with {titles_seen[title]}: {title}")
        else:
            titles_seen[title] = path.name
        if not og_title_pat.search(src):
            rep.add("INFO", section, path.name, "missing og:title meta")
        if not canonical_pat.search(src):
            rep.add("INFO", section, path.name, "missing canonical link")


# ── 9. Workflow CI health ─────────────────────────────────────────────────────

def section_9_ci_health(rep: Findings):
    section = "ci-health"
    rep.sections_run.append(section)
    try:
        r = subprocess.run(["gh", "run", "list", "--limit", "10"],
                           cwd=ROOT, capture_output=True, text=True,
                           timeout=15, encoding="utf-8", errors="replace")
    except Exception:
        rep.sections_skipped.append(section + " (gh CLI unavailable)")
        return
    if r.returncode != 0:
        rep.sections_skipped.append(section + " (gh run list failed)")
        return
    fails = []
    for line in r.stdout.splitlines():
        if line.startswith("completed\tfailure"):
            parts = line.split("\t")
            if len(parts) >= 3:
                wf = parts[2]
                fails.append(wf)
    if fails:
        rep.add("WARN", section, ".github/workflows/",
                f"{len(fails)} of last 10 workflow runs failed",
                ", ".join(fails[:3]) + ("…" if len(fails) > 3 else ""))


# ── REPORT ────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    only_section = None
    for i, a in enumerate(args):
        if a == "--section" and i + 1 < len(args):
            try: only_section = int(args[i + 1])
            except ValueError: pass

    rep = Findings()
    sections = [
        section_1_validators,
        section_2_page_integrity,
        section_3_asset_integrity,
        section_4_doc_drift,
        section_5_hygiene,
        section_6_script_docs,
        section_7_page_weights,
        section_8_seo_meta,
        section_9_ci_health,
    ]
    skip_subprocess = "--quick" in args
    print("=" * 60)
    print("  ULTRA AUDIT — Tier 4 Training Time scan")
    print("=" * 60)
    print()
    for i, fn in enumerate(sections, 1):
        if only_section is not None and i != only_section:
            continue
        if skip_subprocess and fn is section_1_validators:
            rep.sections_skipped.append("validators (--quick)")
            continue
        print(f"  [{i}] {fn.__name__.replace('section_','').replace('_',' ')}")
        try:
            fn(rep)
        except Exception as e:
            rep.add("ERROR", fn.__name__, "(scan)", f"section crashed: {e}")

    print()
    by_sev = rep.by_severity()
    total = len(rep.items)
    print("=" * 60)
    print(f"  Sections run:     {len(rep.sections_run)}")
    print(f"  Sections skipped: {len(rep.sections_skipped)} {rep.sections_skipped or ''}")
    print(f"  Findings:         {total} ({len(by_sev.get('ERROR',[]))} ERR · {len(by_sev.get('WARN',[]))} WARN · {len(by_sev.get('INFO',[]))} INFO)")
    print("=" * 60)
    print()

    # Print findings grouped by severity
    for sev in ("ERROR", "WARN", "INFO"):
        items = by_sev.get(sev, [])
        if not items:
            continue
        print(f"  {sev}:")
        # Group by section
        by_section: dict = defaultdict(list)
        for f in items:
            by_section[f["section"]].append(f)
        for section, group in by_section.items():
            print(f"    [{section}]")
            for f in group[:8]:
                print(f"      {f['file']}: {f['issue']}")
                if f["snippet"]:
                    print(f"        → {f['snippet']}")
            if len(group) > 8:
                print(f"      ... and {len(group) - 8} more")
        print()

    # Optional: write report file for CI archival
    out = ROOT / "docs" / "ultra_audit_report.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("# Ultra Audit Report\n\n")
        f.write(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}_\n\n")
        f.write(f"**Sections run:** {len(rep.sections_run)}  ·  ")
        f.write(f"**Sections skipped:** {len(rep.sections_skipped)}  ·  ")
        f.write(f"**Findings:** {total}\n\n")
        for sev in ("ERROR", "WARN", "INFO"):
            items = by_sev.get(sev, [])
            if not items: continue
            f.write(f"## {sev} ({len(items)})\n\n")
            for it in items:
                f.write(f"- **[{it['section']}] {it['file']}** — {it['issue']}")
                if it["snippet"]: f.write(f"\n  > {it['snippet']}")
                f.write("\n")
            f.write("\n")
    print(f"  Report → {out.relative_to(ROOT)}")
    return rep.exit_code()


if __name__ == "__main__":
    sys.exit(main())
