"""External truth — cross-check Codex claims against the One Piece Wiki.

Every other checker asks whether the Codex agrees with ITSELF. This is the only
one that asks whether it agrees with the outside world.

Two things are compared, and the second matters more:

  DRIFT     -- the Codex's stored value against the wiki's current value. The
               wiki is edited continuously; a scrape from April can be quietly
               wrong by August with nothing in the repo to show it.

  CITATION  -- the wiki records its OWN sourcing in {{Qref}} templates
               (sbs=47|page=66, or vivre card=...). Where the wiki cites Oda for
               a fact the Codex carries as unverified, that is a promotion the
               Canon Engine could not find on its own -- verify.py only sees the
               SBS text the repo already holds.

RULES, per docs/canon-policy.md:
  - reports, never edits. It cannot promote a tier or change a value.
  - where sources disagree it records BOTH, and says so.
  - it is a findings generator for curate.html, not an authority.

Deliberately NOT in the daily CI: it depends on a third-party service, and a
network blip should never fail the build. Run it when you want findings.

Run:
  python scripts/audit_external_truth.py                 # 25 most-prominent
  python scripts/audit_external_truth.py --sample 60
  python scripts/audit_external_truth.py --name "Koby"
"""
import json
import os
import re
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("  ✗ requests not installed — pip install -r requirements.txt")
    sys.exit(1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI_API = "https://onepiece.fandom.com/api.php"
USER_AGENT = "ShimotsukiCodex/1.0 (fan reference project; audit_external_truth.py)"
REPORT = os.path.join(ROOT, "docs", "external_conflicts.md")

# Codex field -> wiki infobox field. The wiki does NOT use the obvious names:
# birthday is "birth", blood_type is "blood type".
FIELD_MAP = {
    "birthday":   "birth",
    "bounty":     "bounty",
    "height":     "height",
    "blood_type": "blood type",
    "origin":     "origin",
    "residence":  "residence",
    "age":        "age",
    "epithet":    "epithet",
    "occupation": "occupation",
}


def jload(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def fetch_wikitext(title, session):
    r = session.get(WIKI_API, params={
        "action": "query", "titles": title, "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "format": "json",
        "redirects": 1,
    }, headers={"User-Agent": USER_AGENT}, timeout=25)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    for page in pages.values():
        if "revisions" not in page:
            return None
        return page["revisions"][0]["slots"]["main"]["*"]
    return None


def infobox_fields(wikitext, title=None, session=None):
    """Pull the Char Box fields, keeping the raw value so Qrefs survive.

    Major characters use tabbed pages, where the article itself carries NO
    infobox -- it is transcluded from "Template:<Name> Tabs Top". Without this
    fallback every prominent character silently yields zero fields, which is
    indistinguishable from "nothing to report" and quietly guts the sample."""
    i = wikitext.find("{{Char Box")
    if i == -1 and title and session:
        try:
            tabs = fetch_wikitext(f"Template:{title} Tabs Top", session)
        except Exception:
            tabs = None
        if tabs:
            i = tabs.find("{{Char Box")
            if i != -1:
                wikitext = tabs
    if i == -1:
        return {}
    block = wikitext[i:i + 4000]
    out = {}
    for m in re.finditer(r"^\|\s*([a-zA-Z0-9_ ]+?)\s*=\s*(.*)$", block, re.M):
        out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def strip_markup(v):
    """Wiki value -> comparable plain text."""
    v = re.sub(r"\{\{Qref[^}]*\}\}", " ", v, flags=re.I)      # citations
    v = re.sub(r"\{\{B\|s\}\}", "", v, flags=re.I)            # berry symbol
    v = re.sub(r"\{\{Nihongo\|([^|}]*)[^}]*\}\}", r"\1", v)   # JP wrappers
    # {{W|Tairō|Great Elder}} links to Wikipedia and DISPLAYS the last
    # parameter. Stripping it wholesale drops real text and reports a
    # difference that does not exist -- it invented a Kin'emon "drift".
    v = re.sub(r"\{\{W\|[^|}]*\|([^}]*)\}\}", r"\1", v, flags=re.I)
    v = re.sub(r"\{\{W\|([^|}]*)\}\}", r"\1", v, flags=re.I)
    v = re.sub(r"\{\{[^}]*\}\}", " ", v)                      # any other template
    v = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", v)   # links
    v = re.sub(r"<[^>]+>", " ", v)                            # html/br
    v = re.sub(r"'{2,}", "", v)                               # bold/italic
    return re.sub(r"\s+", " ", v).strip(" ,;·")


def cited_sources(raw):
    """What the wiki says its own source is, from the Qref templates."""
    found = set()
    for m in re.finditer(r"\{\{Qref([^}]*)\}\}", raw, re.I):
        body = m.group(1).lower()
        if "sbs" in body:
            vol = re.search(r"sbs\s*=\s*(\d+)", body)
            found.add(f"SBS {vol.group(1)}" if vol else "SBS")
        if "vivre" in body:
            found.add("Vivre Card")
        if re.search(r"chap\s*=\s*(\d+)", body):
            found.add("manga ch." + re.search(r"chap\s*=\s*(\d+)", body).group(1))
    return found


def comparable(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def main():
    sample = 25
    if "--sample" in sys.argv:
        sample = int(sys.argv[sys.argv.index("--sample") + 1])
    only = None
    if "--name" in sys.argv:
        only = sys.argv[sys.argv.index("--name") + 1]

    pr = jload("punk_records.json")
    facts = jload("canon_facts.json")

    # subjects the Codex already has Oda-level backing for
    oda_backed = set()
    for f in facts:
        types = {s.get("type") for s in (f.get("sources") or []) if isinstance(s, dict)}
        if types & {"sbs", "vivre_card"}:
            oda_backed.add((f.get("subject"), f.get("predicate")))

    records = [r for r in pr.values() if r.get("name")]
    if only:
        records = [r for r in records if (r.get("name") or "").strip().lower() == only.lower()]
        if not records:
            print(f"  ✗ no record named {only!r}")
            return 1
    else:
        records.sort(key=lambda r: -(r.get("appearances") or 0))
        records = records[:sample]

    print("=" * 76)
    print("  External truth — Codex vs One Piece Wiki")
    print("=" * 76)
    print(f"\n  Checking {len(records)} character(s). Reports only; never edits.\n")

    session = requests.Session()
    drift, promotable, unreachable, no_infobox = [], [], [], []

    for idx, rec in enumerate(records, 1):
        name = (rec.get("name") or "").strip()
        try:
            wt = fetch_wikitext(name, session)
        except Exception as e:
            unreachable.append((name, f"{type(e).__name__}: {e}"[:70]))
            continue
        if not wt:
            unreachable.append((name, "no wiki page"))
            continue

        fields = infobox_fields(wt, name, session)
        if not fields:
            # never let a parse failure read as a clean result
            no_infobox.append(name)
        for codex_field, wiki_field in FIELD_MAP.items():
            ours = rec.get(codex_field)
            raw = fields.get(wiki_field)
            if not ours or not raw:
                continue
            theirs = strip_markup(raw)
            if not theirs:
                continue

            a, b = comparable(str(ours)), comparable(theirs)
            # first segment only -- the Codex stores "16 (debut) · 18 (after
            # timeskip)" where the wiki has the same content differently joined
            if a != b and not (a.startswith(b[:14]) or b.startswith(a[:14])):
                # 44 characters cut most drift rows mid-word, which makes
                # them unreadable and therefore unactionable -- the point
                # of a drift row is to SEE what changed.
                drift.append((name, codex_field, str(ours)[:200], theirs[:200]))

            srcs = cited_sources(raw)
            oda = {s for s in srcs if s.startswith(("SBS", "Vivre"))}
            if oda and (name, codex_field) not in oda_backed:
                promotable.append((name, codex_field, ", ".join(sorted(oda)),
                                   theirs[:34]))

        print(f"  {idx:>3}/{len(records)}  {name[:38]:38} "
              f"{len(fields)} infobox fields")
        time.sleep(1.0)   # be a good citizen

    # ── report ────────────────────────────────────────────────────────────
    print("\n" + "-" * 76)
    print(f"\n  drift (Codex value differs from the wiki)     {len(drift):>4}")
    print(f"  promotable (wiki cites Oda, Codex does not)   {len(promotable):>4}")
    print(f"  unreachable                                   {len(unreachable):>4}")
    print(f"  no infobox found (parse gap, NOT a pass)      {len(no_infobox):>4}")

    lines = ["# External Conflicts — Codex vs One Piece Wiki", "",
             "_Generated by `scripts/audit_external_truth.py`. Reports only —",
             "nothing here has been applied. Where the two disagree, BOTH values",
             "are recorded; deciding between them is a maintainer call._", "",
             f"Sampled **{len(records)}** characters.", ""]

    if promotable:
        # Two axes matter to the maintainer working curate.html: which FIELD a
        # claim is (one decision often settles a whole column) and which Oda
        # source the wiki cites (SBS and Vivre Card are both canon under
        # docs/canon-policy.md, but they are checked in different places).
        def source_class(cite):
            c = (cite or "").lower()
            if "sbs" in c:
                return "SBS"
            if "vivre" in c:
                return "Vivre Card"
            return "other"

        by_field = {}
        for n, f, cite, v in promotable:
            b = by_field.setdefault(f, {"SBS": 0, "Vivre Card": 0, "other": 0})
            b[source_class(cite)] += 1

        lines += ["## Promotable — the wiki cites Oda where the Codex does not", "",
                  "The Canon Engine only sees SBS text already in the repo, so it",
                  "cannot find these. Each is a candidate for curate.html.", "",
                  "### By field and cited source", "",
                  "| Field | SBS | Vivre Card | other | total |", "|---|---:|---:|---:|---:|"]
        for f in sorted(by_field, key=lambda k: -sum(by_field[k].values())):
            b = by_field[f]
            lines.append(f"| {f} | {b['SBS']} | {b['Vivre Card']} | {b['other']} | "
                         f"{sum(b.values())} |")
        lines += ["", "### By cited source", ""]

        for cls in ("SBS", "Vivre Card", "other"):
            rows = [(n, f, c, v) for n, f, c, v in promotable if source_class(c) == cls]
            if not rows:
                continue
            lines += [f"#### Cited to {cls} ({len(rows)})", ""]
            for f in sorted({r[1] for r in rows}):
                sub = [r for r in rows if r[1] == f]
                lines += [f"**{f}** — {len(sub)}", "",
                          "| Character | Wiki cites | Value |", "|---|---|---|"]
                for n, _, c, v in sub:
                    lines.append(f"| {n} | {c} | {v} |")
                lines.append("")

    if drift:
        lines += ["## Drift — stored value differs from the wiki's current value", "",
                  "| Character | Field | Codex | Wiki |", "|---|---|---|---|"]
        for n, f, ours, theirs in drift:
            lines.append(f"| {n} | {f} | {ours} | {theirs} |")
        lines.append("")

    if no_infobox:
        lines += ["## No infobox found — these were NOT checked", "",
                  "A parse gap, not a clean result. Listed so the sample size",
                  "is never overstated.", ""]
        for n in no_infobox:
            lines.append(f"- {n}")
        lines.append("")

    if unreachable:
        lines += ["## Unreachable", ""]
        for n, why in unreachable:
            lines.append(f"- {n} — {why}")
        lines.append("")

    if not (promotable or drift or no_infobox):
        lines += ["## No disagreements found", "",
                  "Every sampled field matched the wiki, and the wiki cited no",
                  "Oda source the Codex was missing.", ""]

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  → docs/external_conflicts.md\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
