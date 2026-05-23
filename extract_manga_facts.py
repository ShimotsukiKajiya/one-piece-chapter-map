"""
Extract Manga Facts — derives unambiguous, citable canon facts from
appearances.csv and saves them to canon_facts.json.

This is the first concrete step in the Canon Engine: turn the things we
*know* from the manga (because they're observed across the entire wiki
community and easily verified) into structured FACTS with full source
citation. Each fact carries:

  - subject (the entity the fact is about)
  - predicate (what kind of fact)
  - value (the fact itself)
  - tier (🟢 canon — derived from manga source)
  - sources (one or more citations following docs/canon-sources.md)
  - verified_on / verified_by

Facts derived in this first pass (all from `appearances.csv`):

  1. first_appearance      — earliest chapter a character appeared
  2. total_appearance_count — how many distinct chapters they appeared in
  3. flashback_count       — chapters where they appeared in flashback
  4. cover_appearance_count — chapter cover-page appearances

These are 🟢 canon because:
  - The data point is objective (X appeared in chapter Y, yes/no)
  - The wiki community is reliable on chapter-by-chapter character
    inventories (it's the kind of data fan wikis get right)
  - Each fact cites the specific chapter(s) it derives from

Run:
  py extract_manga_facts.py             # build/update canon_facts.json
  py extract_manga_facts.py --dry-run   # report only, write nothing
  py extract_manga_facts.py --verbose   # show progress per character
"""

import csv, json, os, sys
from collections import defaultdict
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
APP_PATH   = os.path.join(DIR, "appearances.csv")
OUT_PATH   = os.path.join(DIR, "canon_facts.json")

VERIFIER   = "extract_manga_facts.py v1"
TODAY      = date.today().isoformat()


def load_appearances():
    if not os.path.exists(APP_PATH):
        print("  ✗ appearances.csv not found — run scraper.py first")
        sys.exit(1)
    rows = []
    with open(APP_PATH, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try: ch = int(r["chapter"])
            except (ValueError, KeyError): continue
            name = (r.get("name") or "").strip()
            if not name: continue
            rows.append((name, ch, (r.get("type") or "full").strip().lower()))
    return rows


def make_fact(fact_id, subject, predicate, value, sources, evidence_notes=""):
    """Construct a canonical fact record per docs/canon-sources.md schema."""
    return {
        "id":        fact_id,
        "subject":   subject,
        "predicate": predicate,
        "value":     value,
        "tier":      "canon",
        "sources":   sources,
        "evidence_notes": evidence_notes,
        "verified_on":   TODAY,
        "verified_by":   VERIFIER,
    }


def _load_wiki_first_appearance():
    """Build {name_lower: chapter} from punk_records.json `first_appearance`.

    Wiki-scraped, authoritative for "what chapter does this character debut in".
    Used to override CSV-derived first appearance when the CSV is missing
    earlier rows (e.g. Lilith CSV-only-row=Ch.1181 but wiki=Ch.1061;
    Broggy CSV-only-row=Ch.1181 flashback but wiki=Ch.115). 13 such cases
    surfaced by `audit.py check_first_app_authority` as of 2026-05-02.
    """
    import re as _re
    pr_path = os.path.join(os.path.dirname(__file__), "punk_records.json")
    if not os.path.exists(pr_path):
        return {}
    try:
        with open(pr_path, encoding="utf-8") as f:
            pr = json.load(f)
    except Exception:
        return {}
    ch_pat = _re.compile(r"Chapter\s+(\d+)", _re.I)
    out = {}
    for k, v in pr.items():
        if not isinstance(v, dict):
            continue
        fa = v.get("first_appearance", "")
        m = ch_pat.search(fa) if fa else None
        if not m:
            continue
        try:
            ch = int(m.group(1))
        except ValueError:
            continue
        if ch > 0:
            out[k.lower()] = ch
    return out


def derive_facts(rows):
    """Walk appearances and derive per-character facts."""
    by_char = defaultdict(list)
    for name, ch, typ in rows:
        by_char[name].append((ch, typ))

    # Load wiki first_appearance lookup once for cross-checking CSV values.
    wiki_first = _load_wiki_first_appearance()

    facts = []
    for name in sorted(by_char.keys()):
        appearances = by_char[name]
        chapters_full      = sorted({c for c, t in appearances if t == "full"})
        chapters_flashback = sorted({c for c, t in appearances if t == "flashback"})
        chapters_cover     = sorted({c for c, t in appearances if t == "cover"})
        chapters_silhouette = sorted({c for c, t in appearances if t == "silhouette"})
        all_chapters       = sorted({c for c, _ in appearances})

        # ── FACT 1: first appearance ───────────────────────────────
        # The earliest chapter where this character appears — preferring wiki
        # `first_appearance` field over CSV-derived earliest row when they
        # disagree by ≥5 chapters AND wiki is earlier (the CSV is missing
        # earlier rows). When wiki is LATER than CSV, keep CSV — it's just
        # a definition difference (CSV catches covers/silhouettes wiki
        # excludes from "first appearance"; e.g. Nami Ch.1 cover vs Ch.8
        # first scene). See docs/glossary.md "C2. Sources of truth".
        if all_chapters:
            csv_first_ch   = all_chapters[0]
            csv_first_type = next(t for c, t in appearances if c == csv_first_ch)
            wiki_ch        = wiki_first.get(name.lower())
            authority_note = ""

            if wiki_ch and wiki_ch < csv_first_ch and (csv_first_ch - wiki_ch) >= 5:
                # Wiki says earlier — CSV is incomplete. Defer to wiki.
                # Source citation reflects wiki as the primary authority — using
                # the misleading CSV chapter as "manga" source would propagate
                # the bug into bake_heatmap and any other consumer that reads
                # the manga citation rather than fact["value"]["chapter"].
                first_ch   = wiki_ch
                first_type = "full"  # wiki convention; formal debut
                authority_note = (
                    f" Wiki first_appearance overrides CSV "
                    f"(wiki=Ch.{wiki_ch}, csv=Ch.{csv_first_ch}, "
                    f"+{csv_first_ch - wiki_ch} chapters of CSV gap)."
                )
                sources = [
                    {"type": "manga", "chapter": wiki_ch, "appearance_type": "full"},
                    {"type": "wiki",  "page": name, "chapter": wiki_ch,
                     "field": "first_appearance"},
                ]
            else:
                first_ch   = csv_first_ch
                first_type = csv_first_type
                sources = [{"type": "manga", "chapter": csv_first_ch,
                            "appearance_type": csv_first_type}]

            slug = name.replace(" ", "_").replace(".", "")
            facts.append(make_fact(
                fact_id   = f"first_app:{slug}",
                subject   = name,
                predicate = "first_appearance",
                value     = {"chapter": first_ch, "type": first_type},
                sources   = sources,
                evidence_notes=(f"Derived from appearances.csv — "
                                f"{name} first appears in Chapter {first_ch} "
                                f"({first_type})." + authority_note),
            ))

        # ── FACT 2: total appearance count ─────────────────────────
        if all_chapters:
            slug = name.replace(" ", "_").replace(".", "")
            facts.append(make_fact(
                fact_id   = f"total_app:{slug}",
                subject   = name,
                predicate = "total_appearance_count",
                value     = len(all_chapters),
                # Cite the FULL list of chapters as the source; large but
                # complete. Down the line we may compress to a range
                # representation if the file size becomes a concern.
                sources   = [{"type": "manga",
                              "chapters": all_chapters,
                              "summary": f"{len(all_chapters)} distinct chapters"}],
                evidence_notes=(f"{name} appears in {len(all_chapters)} "
                                f"distinct chapters across the manga"),
            ))

        # ── FACT 3: flashback presence ─────────────────────────────
        if chapters_flashback:
            slug = name.replace(" ", "_").replace(".", "")
            facts.append(make_fact(
                fact_id   = f"flashback_count:{slug}",
                subject   = name,
                predicate = "flashback_count",
                value     = len(chapters_flashback),
                sources   = [{"type": "manga",
                              "chapters": chapters_flashback,
                              "appearance_type": "flashback"}],
                evidence_notes=(f"{name} appears in flashback in "
                                f"{len(chapters_flashback)} chapter(s)"),
            ))

        # ── FACT 4: cover-page appearances ─────────────────────────
        if chapters_cover:
            slug = name.replace(" ", "_").replace(".", "")
            facts.append(make_fact(
                fact_id   = f"cover_count:{slug}",
                subject   = name,
                predicate = "cover_appearance_count",
                value     = len(chapters_cover),
                sources   = [{"type": "manga",
                              "chapters": chapters_cover,
                              "appearance_type": "cover"}],
                evidence_notes=(f"{name} appears on chapter covers "
                                f"{len(chapters_cover)} time(s)"),
            ))

        # ── FACT 5: silhouette appearances ─────────────────────────
        if chapters_silhouette:
            slug = name.replace(" ", "_").replace(".", "")
            facts.append(make_fact(
                fact_id   = f"silhouette_count:{slug}",
                subject   = name,
                predicate = "silhouette_appearance_count",
                value     = len(chapters_silhouette),
                sources   = [{"type": "manga",
                              "chapters": chapters_silhouette,
                              "appearance_type": "silhouette"}],
                evidence_notes=(f"{name} appears in silhouette "
                                f"{len(chapters_silhouette)} time(s)"),
            ))

    return facts


def main():
    dry     = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv

    print("=" * 60)
    print("  Manga Facts Extractor — Phase B groundwork")
    print(f"  Source: appearances.csv  (manga, 🟢 canon tier)")
    print(f"  Output: canon_facts.json")
    print("=" * 60); print()

    rows = load_appearances()
    print(f"  Loaded {len(rows):,} appearance rows")

    facts = derive_facts(rows)

    # Stats
    by_pred = defaultdict(int)
    by_subj = set()
    for f in facts:
        by_pred[f["predicate"]] += 1
        by_subj.add(f["subject"])

    print()
    print(f"  Derived {len(facts):,} canon facts about {len(by_subj):,} characters:")
    for pred in sorted(by_pred):
        print(f"    {pred:35s} {by_pred[pred]:>5,}")

    if verbose:
        print()
        for f in facts[:5]:
            print(f"  · {f['id']}: {f['subject']} {f['predicate']} = {f['value']}")
        print(f"  · … (+{len(facts)-5:,} more)")

    if dry:
        print()
        print("  (dry run — nothing written)")
        return

    # Load-merge instead of wholesale overwrite. This script used to
    # truncate canon_facts.json to only its own derived facts — wiping
    # everything verify.py, ingest_manual_source.py, and the family
    # extractor had added. The merge preserves those other facts.
    # Replacement by stable ID keeps re-runs idempotent for our own facts.
    existing: list = []
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"  ⚠  Could not read existing {OUT_PATH} for merge: {e}")
            existing = []

    by_id = {f["id"]: f for f in existing}
    new_count = 0
    replaced = 0
    for f in facts:
        if f["id"] in by_id:
            replaced += 1
        else:
            new_count += 1
        by_id[f["id"]] = f

    merged = list(by_id.values())
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    size_kb = os.path.getsize(OUT_PATH) // 1024
    print()
    print(f"  ✓ Wrote {len(merged):,} facts → {OUT_PATH}  ({size_kb:,} KB)")
    print(f"    {new_count} new, {replaced} replaced, "
          f"{len(merged) - new_count - replaced} preserved from other extractors")
    print("=" * 60)


if __name__ == "__main__":
    main()
