# Canon Sources Registry

> **The Codex's authority comes from its sources, not from itself.** Every
> claim in any data file must be traceable to one of the sources below.
> Adding a new source requires a new entry here, with documentation,
> verification path, and approval log.

This document is the **single source of truth for what sources we trust**.
If a source isn't listed here, no claim derived from it can be tagged 🟢
canon. Future maintainers (including future-me) cannot add new sources
to the verification pipeline without a corresponding entry in this file.

---

## Source schema

Every registered source has:

| Field | Meaning |
|---|---|
| `id` | Stable short identifier used in citations (e.g. `sbs`, `manga`, `vivre`) |
| `name` | Human-readable name |
| `tier` | Default trust level for an unchallenged claim from this source |
| `coverage` | What kinds of claims it can support |
| `access` | How we get the data (API, manual entry, etc.) |
| `verification` | How we know the data is faithful to the original |
| `citation_format` | How a claim cites this source in `canon_facts.json` |
| `approved_on` | Date the maintainer added this source |
| `approved_by` | Who approved it |

---

## Registered sources

### `manga` — One Piece manga chapters 1–1181 (and ongoing)

- **Tier:** 🟢 canon (Oda's pen — highest authority)
- **Coverage:**
  - Character debut chapters
  - Character appearance per chapter (full / flashback / silhouette / cover)
  - Cover-story arc chapter ranges
  - Bounty announcement chapters
  - Death-event chapters
  - First appearance of named locations, ships, devil fruits
- **What it CANNOT verify (without panel transcripts we don't have):**
  - Verbatim dialogue
  - Visual details (panel composition, expressions)
  - Translation choices
- **Access:** indirectly via the Fandom wiki's chapter pages, scraped by
  `scraper.py` into `appearances.csv`. The wiki community is generally
  reliable for *which* characters appeared in *which* chapters and
  *what type* of appearance — these are objective, easily-verified
  observations that don't require interpretation.
- **Verification:** spot-checked against the Viz official translations
  (which we do not store). Wiki entries for character appearances have
  been ground-truth-stable across years; this is the kind of data the
  wiki gets right.
- **Citation format:** `{"type": "manga", "chapter": 1, "appearance_type": "full"}`
- **Approved on:** 2026-04-26
- **Approved by:** Shimotsuki Kajiya

### `sbs` — SBS Question Corner (Volumes 4–112+)

- **Tier:** 🟢 canon (Oda's direct words)
- **Coverage:**
  - Character ages, birthdays, blood types, heights, weights, favourite foods
  - Family relationships not shown in manga
  - Author commentary on character intent and design
  - Worldbuilding details (geography, currency, weather)
  - Negative confirmations ("X is not Y", "this didn't happen")
  - Hypothetical and humorous side material — clearly tagged as such by Oda
- **What it CANNOT verify:**
  - Plot events not yet revealed in manga (Oda answers around them)
  - Anything Oda has explicitly said is "secret for now"
- **Access:** scraped from Fandom wiki via `sbs_scraper.py` into
  `sbs_archive.json`. Each Q&A has a stable `id_num` for citation.
- **Verification:** SBS text is Oda's direct words translated by the
  community. The wiki transcribes it verbatim from official Viz/Funi
  releases. Translation drift is the only real risk — for important
  claims, prefer the original Japanese text where available.
- **Citation format:** `{"type": "sbs", "volume": 47, "qa_id": "0432"}`
- **Approved on:** 2026-04-26
- **Approved by:** Shimotsuki Kajiya

### `cover_story` — Mini-arc cover-page serials

- **Tier:** 🟢 canon (Oda's pen, side material but in-continuity)
- **Coverage:**
  - Off-screen activities of secondary characters during main arcs
  - Foreshadowing of characters returning later in main story
  - Geographic/political world-state during specific chapter ranges
- **Access:** scraped via `cover_stories_scraper.py` into
  `cover_stories.json`. 21 arcs catalogued.
- **Verification:** chapter-range identification is wiki-derived but
  verifiable from the cover pages themselves; arc summaries are wiki-
  authored and tagged 🔵 likely rather than 🟢 canon.
- **Citation format:** `{"type": "cover_story", "slug": "Buggys_Crew_Adventure_Chronicles"}`
- **Approved on:** 2026-04-26
- **Approved by:** Shimotsuki Kajiya

### `wiki` — Fandom wiki Char Box infoboxes (One Piece Wiki)

- **Tier:** 🟣 speculation (default — must be confirmed by a higher
  source to be promoted)
- **Coverage:** broad first-pass facts (ages, bounties, devil fruits,
  affiliations) — the convenience starting point
- **Why only speculation tier by default:**
  - Speculation creep (fan theories sometimes graduate to "facts")
  - Translation drift across edits
  - Edit wars on contested details
  - Circular citations (wiki cites wiki cites nothing)
  - Lag behind new chapters
- **Access:** scraped via `punk_records_scraper.py` from
  `Template:<Name> Tabs Top` into `punk_records.json`
- **Verification path:** Phase C `verify.py` cross-checks each wiki
  field against `manga` + `sbs` sources; if a primary source confirms,
  the claim is promoted to 🟢 canon with the primary citation. Otherwise
  the claim stays at 🟣.
- **Citation format:** `{"type": "wiki", "page": "Roronoa_Zoro", "field": "bounty"}`
- **Approved on:** 2026-04-26 *(as a starting point only — never as authority)*
- **Approved by:** Shimotsuki Kajiya

### `vivre_card` — Vivre Card Databook

- **Tier:** 🔵 likely (Oda-**supervised** but not Oda-**authored**)
- **Why not canon-by-default:** Vivre Cards are compiled by editorial
  staff under Oda's review. They have been **revised between editions
  without explanation** (e.g. character ages adjusted post-publication)
  and have been **contradicted by the manga itself** in several cases.
  Treat as a strong secondary source, not as authority.
- **Promotion rule:** a Vivre Card claim is promoted to 🟢 canon ONLY
  when corroborated by a higher source (manga panel, SBS Q&A, or Oda
  interview). A bare Vivre Card citation alone stays at 🔵 likely.
- **Coverage:**
  - Per-character: stats, hobbies, favourite foods, family details
  - Officially compiles many SBS-implied facts (cross-cite when present)
- **Access:** ⏳ NOT YET INGESTED — Phase 2 of the source roadmap
- **Verification:** when ingested, will require manual entry from
  scanned databook pages with edition + page citation. Re-verification
  scheduled per edition release.
- **Citation format:** `{"type": "vivre_card", "edition": "Initial 2018", "card_id": "L1"}`
- **Approved on:** 2026-04-26 *(approved as future source; no data ingested yet)*
- **Approved by:** Shimotsuki Kajiya

### `color_walk` — Oda Color Walk art books (Vols 1–10+)

- **Tier:** mixed — depends on the section
  - 🟢 canon for Oda's mini-SBS sections (his direct words)
  - 🔵 likely for editorial captions, design notes, art commentary
    that aren't explicitly Oda-attributed
- **Why split:** the books contain both Oda's direct text and
  editor-written supporting material. Only the former carries the same
  weight as a manga panel.
- **Coverage:**
  - Mini-SBS sections (canon)
  - Author notes on art and character intent (canon if Oda-attributed)
  - Some retroactive clarification of plot details (canon)
- **Access:** ⏳ NOT YET INGESTED — Phase 2
- **Citation format:** `{"type": "color_walk", "volume": 1, "page": 12, "section": "mini_sbs" | "art_notes"}`
- **Approved on:** 2026-04-26 *(as future source; no data ingested yet)*
- **Approved by:** Shimotsuki Kajiya

### `op_magazine` — One Piece Magazine quarterly

- **Tier:** mixed
  - 🟢 canon for new SBS-style Q&As (Oda direct)
  - 🟢 canon for Oda interviews where attributed verbatim
  - 🔵 likely for editorial side-stories, character spotlights, and
    timeline pieces compiled by editorial staff
- **Why mixed:** like Color Walk, the magazine carries both Oda-direct
  content and editorial material. Citation format must distinguish.
- **Access:** ⏳ NOT YET INGESTED — Phase 2
- **Citation format:** `{"type": "op_magazine", "issue": 22, "section": "sbs" | "interview" | "feature"}`
- **Approved on:** 2026-04-26 *(future source)*
- **Approved by:** Shimotsuki Kajiya

### `databook_legacy` — Yellow / Red / Blue / Green / Grand databooks

- **Tier:** 🟣 speculation (older, pre-2010, partially superseded)
- **Why demoted from likely → speculation:** these were the standard
  before Vivre Cards / OP Magazine, and many of their entries have
  since been silently overwritten or contradicted by newer Oda
  material. Anything from a legacy databook needs **active
  re-verification** against current canon before being treated as
  authoritative — its age makes it less trustworthy than newer
  secondary sources.
- **Promotion rule:** legacy databook entries are NOT promoted to
  canon automatically. They serve as starting points for verification
  against SBS / manga / current Vivre Cards.
- **Coverage:** pre-timeskip character facts that may or may not still
  hold; geographic and political background not contradicted by
  later canon
- **Access:** ⏳ NOT YET INGESTED — Phase 3 (low priority)
- **Approved on:** 2026-04-26 *(future source)*
- **Approved by:** Shimotsuki Kajiya

### Notes on extended media in general

A claim from any extended-media source (Vivre Card, Color Walk editorial,
OP Magazine feature, legacy databook, light novel, movie pamphlet) is
**always subject to retroactive contradiction by the manga**. The
verification pipeline must therefore:

1. Default extended-media claims to 🔵 likely, never 🟢 canon, regardless
   of how authoritative the source feels at first glance
2. Re-verify on each refresh against the latest manga + SBS
3. Auto-flag as 🔴 disproven when a higher-tier source contradicts
4. Carry the source EDITION as part of the citation so we can detect
   when a later edition silently revises an earlier claim

Light novels (Ace, Marco, Sabo, Boa, Law) follow the same rule with
an added wrinkle: they're written by other authors under Oda's
supervision, so their internal consistency is good but their canonical
weight is below Oda-authored material. Default 🔵 likely.

### `reddit` — r/OnePiece theory threads

- **Tier:** 🟠 rumour (fan speculation, never canon)
- **Coverage:** Catalogues what theories the community is discussing
- **Access:** scraped via `theory_scraper.py` into `theories_import.json`
- **Critical rule:** content from this source is *never* used to verify
  any claim. Theories are stored as theories — labelled and isolated.
  They cite canon sources to support themselves; they cannot themselves
  be cited as evidence for anything.
- **Citation format:** `{"type": "reddit", "thread_id": "xibwnk"}`
- **Approved on:** 2026-04-26
- **Approved by:** Shimotsuki Kajiya

### `user_submission` — Workbench drafts submitted via GitHub Issue

- **Tier:** 🟠 rumour at submission; promoted to whatever tier the
  cited evidence supports after maintainer review
- **Coverage:** community-built theories with cited evidence chains
- **Access:** GitHub Issues filed via the Workbench's Submit-to-Codex
  button; manually reviewed and merged into `theories_import.json`
- **Verification:** the maintainer reads each submission, checks each
  cited fact against its source, and decides whether to add the
  resulting theory at 🟠/🟣/🔵 tier
- **Citation format:** `{"type": "user_submission", "github_issue": 42}`
- **Approved on:** 2026-04-26
- **Approved by:** Shimotsuki Kajiya

---

## NOT registered (excluded by design)

| Source | Why excluded |
|---|---|
| Filler arcs (Ice Hunter, G-8, etc.) | Anime original — non-canon |
| Most early movies (Z, Strong World, etc.) | Movie-canon only; some events contradict manga |
| Unofficial fan translations | Translation drift introduces errors |
| Discord servers | No persistent citation possible |
| YouTube theory videos | Same content as Reddit theories, less citable |
| Twitter/X posts (other than Oda's own) | Speculation surface, not source |

---

## How to add a new source

A new source enters the registry only via PR:

1. Add an entry to this document in alphabetical order under "Registered sources"
2. Document its tier, coverage, access path, verification, citation format
3. Note `approved_on` and `approved_by` (must be the project maintainer)
4. If the source needs a new scraper, add it as a separate PR with tests
5. Update `audit.py` to verify any claims using the new source carry a
   correctly-formatted citation

---

## Decisions log

| Date | Decision |
|---|---|
| 2026-04-26 | Initial registry adopted. Manga, SBS, Cover Stories, Wiki, Reddit, User Submissions ingested. Vivre Card, Color Walk, OP Magazine, Legacy Databooks approved as future sources but not yet ingested. |
| 2026-04-26 | Wiki demoted to 🟣 speculation by default; only promoted to 🟢 canon when confirmed by a higher source. |
| 2026-04-26 | Reddit and User Submission sources can NEVER be used to verify other claims — only stored as theories. |
