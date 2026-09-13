"""D4 — Truth: what is the Codex's confidence actually resting on?

Two jobs, both about honesty rather than correctness.

  STALENESS — the Canon Engine (verify.py, find_conflicts.py) is only meaningful
  against the data it last ran on. Before this check, verification was reported
  as current while sitting a full data refresh behind, and nothing surfaced it.
  Fails if the data is newer than the last verification run.

  PROVENANCE — 4,501 facts carry the 🟢 canon tier, which reads as "Oda
  confirmed this". Most of them are mechanically derived appearance counts from
  a wiki-sourced chapter list. That is a reasonable thing to tag canon, but the
  distinction should be visible in a report rather than implied by a badge, so
  nobody (including future-me) overstates what the Codex can prove.

Exit codes match audit.py: 0 = clean · 2 = verification is stale.

Run:
  python scripts/audit_truth_provenance.py
"""
import collections
import io
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Reader-facing infobox fields and where their values come from.
WIKI_ONLY_FIELDS = ("occupation", "epithet", "bounty", "residence", "origin",
                    "birthday", "height", "blood_type", "age", "status")


def jload(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def report_date(path, pattern):
    try:
        txt = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
    except OSError:
        return None
    m = re.search(pattern, txt)
    return m.group(1) if m else None


def main():
    facts = jload("canon_facts.json")
    pr = jload("punk_records.json")
    chapters = jload("chapter_dates.json")

    print("=" * 74)
    print("  D4 — Truth provenance: what the tiers actually rest on")
    print("=" * 74)

    # ── staleness ─────────────────────────────────────────────────────────
    # The two reports are gitignored, so a CI checkout never has them and this
    # check failed there every day. Read the dates the refresh bot commits as
    # well: verify.py stamps verified_on on every fact it matches, and bake.py
    # copies find_conflicts.py's generated_on into conflicts.html. Take the later
    # of tracked and report so a local run that skipped the bake still counts.
    data_on = chapters.get("generated_on")
    verified_on = max(filter(None, (
        max((f.get("verified_on") or "" for f in facts), default="") or None,
        report_date("docs/verification_report.md",
                    r"Verification Report — (\d{4}-\d{2}-\d{2})"),
    )), default=None)
    conflicts_on = max(filter(None, (
        report_date("conflicts.html", r'"generated_on": "(\d{4}-\d{2}-\d{2})"'),
        report_date("docs/conflicts_report.md", r"(\d{4}-\d{2}-\d{2})"),
    )), default=None)

    print(f"\n  data generated      {data_on}   (latest chapter "
          f"{chapters.get('latest_chapter')})")
    print(f"  last verification   {verified_on}")
    print(f"  last conflict scan  {conflicts_on}")

    stale = []
    for label, when in (("verification", verified_on), ("conflict scan", conflicts_on)):
        if not when or (data_on and when < data_on):
            stale.append(label)

    # ── provenance ────────────────────────────────────────────────────────
    by_src = collections.Counter()
    tier_src = collections.Counter()
    sbs_subjects = set()
    for f in facts:
        types = tuple(sorted({s.get("type") for s in (f.get("sources") or [])
                              if isinstance(s, dict)}))
        by_src[types] += 1
        tier_src[(types, f.get("tier"))] += 1
        if "sbs" in types:
            sbs_subjects.add(f.get("subject"))

    total = len(facts)
    oda = sum(n for t, n in by_src.items() if "sbs" in t or "vivre_card" in t)
    derived = sum(n for t, n in by_src.items() if t == ("manga",))

    print(f"\n  facts total                     {total:>6,}")
    print(f"    ├─ derived from appearances    {derived:>6,}  "
          f"({100*derived//total}%)  mechanical counts, tagged canon")
    print(f"    └─ cross-checked against Oda   {oda:>6,}  "
          f"({100*oda//total}%)  SBS or Vivre Card")

    chars = len(pr)
    print(f"\n  characters                      {chars:>6,}")
    print(f"    └─ with ≥1 Oda-verified fact   {len(sbs_subjects):>6,}  "
          f"({100*len(sbs_subjects)//chars}%)")

    print(f"\n  tier × source")
    for (types, tier), n in tier_src.most_common(8):
        print(f"    {str(types):24} {str(tier):12} {n:>6,}")

    # ── what the reader sees ──────────────────────────────────────────────
    field_counts = collections.Counter()
    for rec in pr.values():
        for fld in WIKI_ONLY_FIELDS:
            if rec.get(fld):
                field_counts[fld] += 1
    print(f"\n  reader-facing infobox fields sourced from the wiki scrape")
    print(f"  (🔵 LIKELY at best — shown with SPEC badges, not 🟢 canon):")
    for fld, n in field_counts.most_common():
        print(f"    {fld:14} {n:>5,} records")

    # ── curate backlog ────────────────────────────────────────────────────
    # verify.py routes ambiguous matches to curate.html for a human decision.
    # Triaged here so the maintainer knows whether the queue is worth a session
    # before opening it — most of it is one recurring, easily-confirmed shape.
    try:
        queue = jload("docs/curate_queue.json")
    except OSError:
        queue = []
    if queue:
        def nums(s):
            return set(re.findall(r"\d{2,}", str(s)))

        coincidence = confirmable = review = 0
        by_field = collections.Counter()
        for row in queue:
            snippet = str(row.get("snippet") or "")
            value = str(row.get("value") or "")
            field = row.get("field")
            by_field[field] += 1
            # the matched digits also appear as a Chapter/Volume reference:
            # the proximity rule matched a citation, not a claim
            refs = set(re.findall(r"(?:Chapter|Chapters|Vol\.?|Volume|page|P\.)\s*(\d{2,})",
                                  snippet, re.I))
            subject = str(row.get("subject") or "")
            named = bool(subject) and subject.split()[-1].lower() in snippet.lower()
            if nums(value) & refs:
                coincidence += 1
            elif named and field == "birthday":
                confirmable += 1
            else:
                review += 1

        print(f"\n  curate queue                    {len(queue):>6,}  awaiting a human decision")
        print(f"    ├─ likely confirmable          {confirmable:>6,}  "
              f"birthday + subject named in the same SBS answer")
        print(f"    ├─ likely digit coincidence    {coincidence:>6,}  "
              f"value matched a Chapter/Vol reference")
        print(f"    └─ needs a real look           {review:>6,}")
        print(f"    fields: " + ", ".join(f"{k} {v}" for k, v in by_field.most_common(5)))
        print(f"    → review in curate.html; this script never promotes a tier itself")

    print("\n  " + "-" * 70)
    print("\n  Honest summary: the Codex can currently claim INTERNALLY CONSISTENT")
    print("  and CORRECTLY TIERED. It cannot yet claim INDEPENDENTLY VERIFIED —")
    print("  most of what a reader sees is wiki-derived, and only "
          f"{100*len(sbs_subjects)//chars}% of characters")
    print("  have a single fact confirmed in Oda's own words.")

    if stale:
        print(f"\n  ✗ STALE: {', '.join(stale)} predates the current data ({data_on}).")
        print(f"    Run: python verify.py && python find_conflicts.py\n")
        return 2

    print("\n  ✓ Verification and conflict scan are current with the data.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
