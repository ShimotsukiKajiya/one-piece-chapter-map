"""
The Codex — Coherence & Sanity Auditor

Read-only audit of every data file in the Codex. Flags inconsistencies,
broken references, suspicious values, and gaps. Writes a Markdown report
to docs/audit_report.md and exits with a non-zero code if any HARD error
is found (so CI can fail on real breakage).

Run:
  py audit.py             # write report + exit code
  py audit.py --verbose   # also print details to console
  py audit.py --strict    # treat WARN as ERROR
"""

import sys, os, json, csv, re
from collections import Counter, defaultdict
from datetime import datetime

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
REPORT_PATH = os.path.join(DIR, "docs", "audit_report.md")

# ── PATHS ────────────────────────────────────────────────────────
DATA = {
    "appearances": "appearances.csv",
    "sbs":         "sbs_archive.json",
    "theories":    "theories_import.json",
    "covers":      "volume_covers.json",
    "cover_stories": "cover_stories.json",
    "punk_records": "punk_records.json",
    "canon_facts":  "canon_facts.json",
}

# Severity levels
ERR = "ERROR"
WARN = "WARN"
INFO = "INFO"

# ── REPORT ───────────────────────────────────────────────────────
class Report:
    def __init__(self):
        self.findings = []   # (severity, section, message)
        self.stats    = {}   # name → value
    def add(self, sev, section, msg):
        self.findings.append((sev, section, msg))
    def stat(self, name, value):
        self.stats[name] = value
    def by_severity(self):
        c = Counter(f[0] for f in self.findings)
        return c
    def render_md(self):
        c = self.by_severity()
        out = []
        out.append(f"# Codex Audit Report\n")
        out.append(f"_Generated {datetime.now().isoformat(timespec='seconds')}_\n")
        out.append(f"\n**Summary:** {c.get(ERR,0)} errors · {c.get(WARN,0)} warnings · {c.get(INFO,0)} info\n")

        out.append("\n## Stats\n\n| Metric | Value |\n|---|---|")
        for k, v in self.stats.items():
            out.append(f"| {k} | {v:,} |" if isinstance(v, int) else f"| {k} | {v} |")

        # Group findings by section
        by_section = defaultdict(list)
        for sev, sec, msg in self.findings:
            by_section[sec].append((sev, msg))

        out.append("\n## Findings\n")
        for sec in sorted(by_section.keys()):
            out.append(f"\n### {sec}\n")
            for sev, msg in by_section[sec]:
                icon = "🔴" if sev == ERR else ("🟡" if sev == WARN else "ℹ")
                out.append(f"- {icon} **{sev}** — {msg}")

        if not self.findings:
            out.append("\n_No issues found._\n")
        return "\n".join(out) + "\n"


# ── LOADERS ──────────────────────────────────────────────────────
def load_csv(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── CHECKS ───────────────────────────────────────────────────────
def check_appearances(rep, data):
    rows = load_csv(data["appearances"])
    chapters = set(); chars = set(); types = Counter()
    bad_chapter = bad_type = 0
    for r in rows:
        try:
            ch = int(r["chapter"])
            if ch < 1 or ch > 1500: bad_chapter += 1
            chapters.add(ch)
        except:
            bad_chapter += 1
        if r.get("name", "").strip():
            chars.add(r["name"].strip())
        t = r.get("type", "").strip().lower()
        types[t] += 1
        if t not in {"full","flashback","silhouette","cover"}:
            bad_type += 1

    rep.stat("Appearance rows", len(rows))
    rep.stat("Unique chapters", len(chapters))
    rep.stat("Unique characters", len(chars))

    # Check for chapter gaps (any chapter from 1 to max missing?)
    if chapters:
        mx = max(chapters)
        missing = [c for c in range(1, mx + 1) if c not in chapters]
        if missing:
            rep.add(WARN, "appearances",
                f"{len(missing)} chapter(s) missing in 1..{mx}: {missing[:8]}{'…' if len(missing)>8 else ''}")
    if bad_chapter:
        rep.add(ERR, "appearances", f"{bad_chapter} rows with bad chapter numbers")
    if bad_type:
        rep.add(WARN, "appearances",
            f"{bad_type} rows with unrecognised type (expect full/flashback/silhouette/cover)")
    rep.stat("Appearance type breakdown", " · ".join(f"{k}:{v}" for k,v in types.most_common()))

    return chars, chapters


def check_appearances_shard(rep, csv_chars, csv_chapters, csv_total):
    """Recompute the same metrics from relationships/appears-in.json via query.py.

    Reports SHARD_* stats and a diff vs the CSV-derived numbers. Skips silently
    if the shard isn't built yet — the CSV check is still authoritative.
    """
    sys.path.insert(0, os.path.join(DIR, "scripts"))
    try:
        from lib import query
    except Exception as e:
        rep.add(WARN, "appearances_shard", f"query layer unavailable: {e}")
        return

    try:
        shard_total    = query.appearances_count()
        shard_chapters = query.unique_chapters()
        shard_chars    = query.unique_characters()
        shard_types    = query.appearance_type_breakdown()
    except FileNotFoundError:
        rep.add(INFO, "appearances_shard", "relationships/appears-in.json not built — skipping shard parity check")
        return
    except Exception as e:
        rep.add(WARN, "appearances_shard", f"shard read failed: {e}")
        return

    rep.stat("SHARD Appearance rows",     shard_total)
    rep.stat("SHARD Unique chapters",     len(shard_chapters))
    rep.stat("SHARD Unique characters",   len(shard_chars))
    rep.stat("SHARD Appearance type breakdown",
             " · ".join(f"{k}:{v}" for k, v in shard_types.most_common()))

    # Diff vs CSV-derived numbers
    row_delta  = csv_total - shard_total
    char_delta = len(csv_chars) - len(shard_chars)
    chap_delta = len(csv_chapters) - len(shard_chapters)
    rep.stat("PARITY rows lost (CSV → shard)",       row_delta)
    rep.stat("PARITY characters lost (CSV → shard)", char_delta)
    rep.stat("PARITY chapters lost (CSV → shard)",   chap_delta)

    # Surface as findings, not just stats — these are what we want to react to
    sev = INFO if row_delta == 0 else WARN
    rep.add(sev, "appearances_shard",
            f"shard has {row_delta} fewer rows / {char_delta} fewer characters / {chap_delta} fewer chapters than CSV")


def check_sbs(rep, data):
    sbs = load_json(data["sbs"])
    rep.stat("SBS Q&As total", len(sbs))

    vols = sorted({s["volume"] for s in sbs})
    rep.stat("SBS volumes covered", len(vols))
    rep.stat("SBS volume range", f"{min(vols)}–{max(vols)}")

    # Known legitimately-empty volumes
    known_gaps = {11, 26, 46}
    found_gaps = sorted(set(range(min(vols), max(vols)+1)) - set(vols))
    unexpected_gaps = [v for v in found_gaps if v not in known_gaps]
    if unexpected_gaps:
        rep.add(WARN, "sbs", f"unexpected volume gaps: {unexpected_gaps}")

    # Empty Q or A
    bad = [s for s in sbs if not s.get("question","").strip() or not s.get("answer","").strip()]
    if bad:
        rep.add(ERR, "sbs", f"{len(bad)} entries with empty question or answer")

    # Missing required fields
    missing_id   = sum(1 for s in sbs if "id_num" not in s)
    missing_cat  = sum(1 for s in sbs if not s.get("category"))
    if missing_id:
        rep.add(ERR, "sbs", f"{missing_id} entries missing id_num — re-run id assignment")
    if missing_cat:
        rep.add(WARN, "sbs", f"{missing_cat} entries not categorised — re-run sbs_categorizer.py")

    # Detect leftover wikitable garbage
    table_leak = sum(1 for s in sbs if "{|" in s.get("answer","") or "|}" in s.get("answer",""))
    if table_leak:
        rep.add(ERR, "sbs", f"{table_leak} answers still contain wikitable syntax — re-run clean_wikitables.py")

    # Detect interlang link leaks
    interlang = sum(1 for s in sbs if re.search(r'\b(?:fr|es|it|tr|ca|pt|de|ru|en|nl|pl|ja|zh):[A-Za-zЀ-ӿ]', s.get("answer","")))
    if interlang:
        rep.add(WARN, "sbs", f"{interlang} answers may have leaked interlang links — re-run clean_credits.py")

    return sbs


def check_punk(rep, data, known_chars):
    if not os.path.exists(data["punk_records"]):
        rep.add(INFO, "punk_records", "punk_records.json not present yet")
        return
    pr = load_json(data["punk_records"])
    rep.stat("Punk Records total", len(pr))

    found = sum(1 for r in pr.values() if r.get("found"))
    rep.stat("Punk Records with infobox", found)

    # Major characters that should have data
    EXPECTED_MAJOR = ["Monkey D. Luffy", "Roronoa Zoro", "Nami", "Sanji",
                      "Usopp", "Tony Tony Chopper", "Nico Robin", "Franky",
                      "Brook", "Jinbe", "Portgas D. Ace", "Sabo",
                      "Edward Newgate", "Gol D. Roger"]
    for name in EXPECTED_MAJOR:
        rec = pr.get(name)
        if not rec:
            rep.add(ERR, "punk_records", f"missing entry for major character: {name}")
        elif not rec.get("found"):
            rep.add(WARN, "punk_records", f"{name} fetched but no infobox parsed")
        elif not rec.get("bounty") and not rec.get("status") == "Deceased":
            rep.add(WARN, "punk_records", f"{name} has no bounty data — may be stale")

    # Punk Records entries with no corresponding appearance? (orphans)
    orphans = [n for n in pr if n not in known_chars]
    if orphans:
        rep.add(INFO, "punk_records",
            f"{len(orphans)} Punk Records entries not in appearances.csv (probably non-canon or alt names): {orphans[:5]}{'…' if len(orphans)>5 else ''}")


def check_first_app_authority(rep, data):
    """Find characters whose canon_facts first_appearance disagrees with the
    wiki-scraped punk_records first_appearance. Bug class caught by this:
    pages reading the CSV-derived chain (appearances.csv → canon_facts →
    debuts-in shard) for characters whose CSV row is incomplete and far later
    than their real wiki debut. Lilith / Broggy / Joy Boy are the canonical
    examples — CSV row at Ch.1181 vs wiki debut Ch.1061 / Ch.115 / Ch.628.
    """
    if not os.path.exists(data["punk_records"]):
        return
    if not os.path.exists(data["canon_facts"]):
        return
    import re as _re
    _ch_pat = _re.compile(r"Chapter\s+(\d+)", _re.I)

    pr = load_json(data["punk_records"])
    cf = load_json(data["canon_facts"])

    # canon_facts first_app: subject_lower → chapter int
    cf_first = {}
    for f in cf:
        if f.get("predicate") != "first_appearance":
            continue
        v = f.get("value", {})
        if isinstance(v, dict) and "chapter" in v:
            cf_first[f["subject"].lower()] = v["chapter"]

    csv_later = []   # CSV row is later than wiki → CSV is missing earlier rows
    csv_earlier = []  # CSV row is earlier than wiki → CSV caught an earlier cameo/cover/flashback
    for k, v in pr.items():
        if not isinstance(v, dict):
            continue
        fa = v.get("first_appearance", "")
        if not fa:
            continue
        m = _ch_pat.search(fa)
        if not m:
            continue
        try:
            wiki_ch = int(m.group(1))
        except ValueError:
            continue
        if wiki_ch <= 0:
            continue
        cf_ch = cf_first.get(k.lower())
        if not cf_ch:
            continue
        diff = cf_ch - wiki_ch
        if abs(diff) < 5:
            continue
        if diff > 0:
            csv_later.append((k, wiki_ch, cf_ch, diff))
        else:
            csv_earlier.append((k, wiki_ch, cf_ch, diff))

    rep.stat("first_app: CSV-later vs wiki (real gaps)", len(csv_later))
    rep.stat("first_app: CSV-earlier than wiki (cover/flashback caught)", len(csv_earlier))

    if csv_later:
        # WARN: these are actionable — CSV is missing earlier appearances
        csv_later.sort(key=lambda x: -x[3])
        worst = csv_later[:5]
        sample = "; ".join(f"{n} wiki=Ch.{w} csv=Ch.{c}" for n, w, c, _ in worst)
        rep.add(WARN, "first_app_authority",
                f"{len(csv_later)} character(s) have CSV row LATER than wiki first_appearance "
                f"by ≥5 chapters — the CSV is missing earlier rows. Bake functions that show "
                f"'debut' should prefer punk_records.json `first_appearance` over the CSV-derived "
                f"shard (atlas already does this; check other consumers). Worst: {sample}")

    if csv_earlier:
        # INFO: these are usually a definition difference, not a data bug
        rep.add(INFO, "first_app_authority",
                f"{len(csv_earlier)} character(s) have CSV row EARLIER than wiki first_appearance "
                f"by ≥5 chapters. Usually NOT a bug — CSV catches covers/silhouettes/flashbacks "
                f"that wiki excludes from 'first appearance' (e.g. Nami Ch.1 cover vs Ch.8 first scene; "
                f"Blackbeard Ch.133 cover-story mention vs Ch.223 formal debut).")


def check_theories(rep, data):
    if not os.path.exists(data["theories"]): return
    th = load_json(data["theories"])
    rep.stat("Theories total", len(th))

    statuses = Counter(t.get("status","unknown") for t in th)
    rep.stat("Theory status breakdown",
             " · ".join(f"{k}:{v}" for k,v in statuses.most_common()))

    no_analysis = sum(1 for t in th if not t.get("analysis"))
    if no_analysis:
        rep.add(WARN, "theories", f"{no_analysis} theories have no analysis — re-run theory_analyzer.py")


def check_covers(rep, data):
    if os.path.exists(data["covers"]):
        vc = load_json(data["covers"])
        rep.stat("Volume covers", len(vc))

    if os.path.exists(data["cover_stories"]):
        cs = load_json(data["cover_stories"])
        rep.stat("Cover stories", len(cs))
        empty_chapters = [c["name"] for c in cs if not c.get("chapters")]
        if empty_chapters:
            rep.add(WARN, "cover_stories", f"{len(empty_chapters)} cover stories parsed 0 chapters: {empty_chapters}")


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    verbose = "--verbose" in sys.argv
    strict  = "--strict" in sys.argv

    paths = {k: os.path.join(DIR, v) for k, v in DATA.items()}
    rep = Report()

    # Run checks
    chars, chapters = check_appearances(rep, paths)
    check_appearances_shard(rep, chars, chapters, rep.stats.get("Appearance rows", 0))
    check_sbs(rep, paths)
    check_punk(rep, paths, chars)
    check_first_app_authority(rep, paths)
    check_theories(rep, paths)
    check_covers(rep, paths)

    # Write report
    os.makedirs(os.path.join(DIR, "docs"), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(rep.render_md())

    # Console summary
    c = rep.by_severity()
    print("=" * 60)
    print(f"  Codex Audit  ·  {c.get(ERR,0)} errors · {c.get(WARN,0)} warnings · {c.get(INFO,0)} info")
    print(f"  Report → {REPORT_PATH}")
    print("=" * 60)

    if verbose or c.get(ERR, 0):
        print()
        for sev, sec, msg in rep.findings:
            if sev == ERR or verbose:
                icon = "🔴" if sev == ERR else ("🟡" if sev == WARN else "ℹ")
                print(f"  {icon} [{sec}] {msg}")

    # Exit code
    if c.get(ERR, 0):
        sys.exit(2)
    if strict and c.get(WARN, 0):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
