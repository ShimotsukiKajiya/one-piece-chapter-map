"""Audit URL references across docs, scripts, and pages for staleness.

The internal data audits (audit.py, validate_*.py, audit_links*.py) verify
that data files agree with each other and that internal HTML hrefs resolve.
They are blind to text-content drift in markdown, comments, and human-facing
prose. This script catches that class.

Findings (printed + machine-readable exit code):
  - URLs pointing at deprecated/redirect-target hosts (shimotsukikajiya.github.io
    after the shimotsukicodex.com cutover)
  - "as of YYYY-MM-DD" / "Last surveyed: YYYY-MM-DD" stamps older than 14 days
  - Hardcoded counts in CLAUDE.md that disagree with current canon_facts /
    relationship-shard / punk_records totals (basic checks only)

Run:
  python scripts/audit_doc_urls.py            # report findings, exit 0/1
  python scripts/audit_doc_urls.py --strict   # exit 2 on findings (CI-friendly)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── CONFIG ────────────────────────────────────────────────────────────────────

# (pattern, message, severity) — checked against every line of every scanned file.
DEPRECATED_URL_PATTERNS = [
    (r"shimotsukikajiya\.github\.io",
     "uses old github.io URL — should be shimotsukicodex.com",
     "WARN"),
]

# Files to scan (extensions only — anything outside these is skipped)
EXTS = (".md", ".py", ".html", ".js", ".json", ".xml", ".yml", ".yaml", ".toml")

# Top-level dirs to skip even if they contain matching extensions
SKIP_DIRS = {".git", "cache", "obsidian_vault", "logo", "node_modules",
             "__pycache__", ".github/.cache"}

# Files that LEGITIMATELY mention the github.io URL (e.g. as a redirect-source
# comment) — allowlisted so they don't trigger the deprecated-URL warning.
ALLOWLIST_GITHUB_IO = {
    # Memory file documents the redirect explicitly
    "memory/project_status.md",
    # This audit script itself contains the pattern as data
    "scripts/audit_doc_urls.py",
    # Local Claude Code settings (auto-generated, not site content)
    ".claude/settings.local.json",
}

# Date stamps with per-pattern thresholds.
# A 14-day threshold is too lax — visitors land on a page that says
# "Last refreshed: yesterday" and trust it; if it's actually 5 days old
# the trust is misplaced. Different stamps mean different things, so they
# get different thresholds.
#
# (regex pattern, threshold_days, severity, message_suffix)
DATE_STAMP_RULES = [
    # "Last refreshed" / "Last surveyed" / "_Generated" — these are auto-stamped
    # markers of when a doc was *built* from current data. They should be ≤2
    # days old or the doc is misrepresenting current state.
    (r"Last refreshed:\s+(\d{4}-\d{2}-\d{2})",   2, "WARN",  "auto-build stamp"),
    (r"Last surveyed:\s+(\d{4}-\d{2}-\d{2})",    2, "WARN",  "auto-survey stamp"),
    (r"_Generated\s+(\d{4}-\d{2}-\d{2})",        2, "WARN",  "auto-generated stamp"),
    # "as of YYYY-MM-DD" is human prose claiming current state — same standard.
    (r"\bas of\s+(\d{4}-\d{2}-\d{2})",           2, "WARN",  "'as of' claim"),
    # Session deltas / event dates document a moment in history — they should
    # NOT be flagged as stale; they're meant to age. Allow up to 90 days as a
    # very loose bound that only catches truly forgotten "in flight" docs.
    (r"Session\s+deltas?\s*\((\d{4}-\d{2}-\d{2})", 90, "INFO", "session delta marker"),
]

# Count cross-checks against live data (basic sanity)
COUNT_CHECKS = []  # populated below


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _walk(path):
    for dirpath, dirnames, files in os.walk(path):
        # Prune skipped dirs in-place so os.walk doesn't recurse
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in files:
            if name.endswith(EXTS):
                yield os.path.join(dirpath, name)


def _rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


# ── CHECKS ────────────────────────────────────────────────────────────────────

def check_deprecated_urls(findings):
    for path in _walk(ROOT):
        rel = _rel(path)
        if rel in ALLOWLIST_GITHUB_IO:
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue
        for lineno, line in enumerate(lines, 1):
            for pattern, msg, severity in DEPRECATED_URL_PATTERNS:
                if re.search(pattern, line):
                    findings.append({
                        "severity": severity,
                        "file": rel,
                        "line": lineno,
                        "issue": msg,
                        "snippet": line.strip()[:120],
                    })


def check_stale_date_stamps(findings):
    today = datetime.now(timezone.utc).date()
    for path in _walk(ROOT):
        rel = _rel(path)
        # Only check markdown for stale stamps
        if not rel.endswith(".md"):
            continue
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        for pattern, threshold, severity, suffix in DATE_STAMP_RULES:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    stamp = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                except ValueError:
                    continue
                age = (today - stamp).days
                if age > threshold:
                    lineno = text[:m.start()].count("\n") + 1
                    findings.append({
                        "severity": severity,
                        "file": rel,
                        "line": lineno,
                        "issue": f"{suffix} is {age} days old (>{threshold}d threshold)",
                        "snippet": m.group(0),
                    })


def check_count_drift(findings):
    """Sanity-check that hardcoded counts in CLAUDE.md broadly match live data."""
    try:
        with open(os.path.join(ROOT, "punk_records.json"), encoding="utf-8") as f:
            pr = json.load(f)
        live_chars = sum(1 for v in pr.values() if isinstance(v, dict))
    except Exception:
        return  # can't check without source data

    # Look for hardcoded "1,5xx characters" claims
    claude_path = os.path.join(ROOT, "CLAUDE.md")
    if not os.path.exists(claude_path):
        return
    with open(claude_path, encoding="utf-8") as f:
        text = f.read()
    # Match patterns like "1,537 characters" or "1537 characters"
    for m in re.finditer(r"(\d{1,2},?\d{3})\s+characters\b", text):
        raw = m.group(1).replace(",", "")
        try:
            claimed = int(raw)
        except ValueError:
            continue
        if abs(claimed - live_chars) > 20:
            lineno = text[:m.start()].count("\n") + 1
            findings.append({
                "severity": "INFO",
                "file": "CLAUDE.md",
                "line": lineno,
                "issue": f"claimed {claimed:,} characters but punk_records.json has {live_chars:,} ({claimed - live_chars:+,})",
                "snippet": m.group(0),
            })


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    findings: list[dict] = []
    check_deprecated_urls(findings)
    check_stale_date_stamps(findings)
    check_count_drift(findings)

    print("=" * 60)
    print("  Doc URL & Freshness Audit")
    print("=" * 60)
    print()

    if not findings:
        print("  ✓ No issues found")
        print()
        return 0

    by_severity: dict = {}
    for f in findings:
        by_severity.setdefault(f["severity"], []).append(f)

    for sev in ("ERROR", "WARN", "INFO"):
        items = by_severity.get(sev, [])
        if not items:
            continue
        print(f"  {sev}: {len(items)}")
        for f in items[:25]:
            print(f"    {f['file']}:{f['line']}  {f['issue']}")
            print(f"      → {f['snippet']}")
        if len(items) > 25:
            print(f"    ... and {len(items) - 25} more")
        print()

    print("=" * 60)
    print(f"  Total: {len(findings)} finding(s) across {len({f['file'] for f in findings})} file(s)")
    print("=" * 60)

    if "--strict" in sys.argv and any(f["severity"] in ("ERROR", "WARN") for f in findings):
        return 2
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
