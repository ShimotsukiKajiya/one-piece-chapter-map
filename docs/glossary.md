# Shimotsuki Codex — Glossary

*Reference for the terms, scripts, files, and concepts used across this project. Skim by section, search by Ctrl-F.*

Conventions: every term lives near its file when relevant. **File:** points at where the thing actually exists. **Producer of:** / **Consumer of:** maps each script to the files it owns or reads.

---

## A. Pipeline scripts (the verbs)

### `bake.py`
The build script. Reads JSON sources and writes self-contained HTML files (`*.html` in repo root) by injecting data into `<script id="…-data" type="application/json">` blocks. Re-runs in seconds. Pages built this way work without a server — open the HTML directly in a browser. Run after any data file change. **File:** [bake.py](../bake.py). **Producer of:** all baked HTML surface pages.

### `refresh.py`
The full pipeline: scrape → verify → bake → audit. Run weekly via cron. `refresh.py --quick` skips the slow scrapes (uses existing data) and is the safe re-run during a session. **File:** [refresh.py](../refresh.py).

### Scrapers (`scraper.py`, `sbs_scraper.py`, `punk_records_scraper.py`, `theory_scraper.py`, etc.)
One scraper per source. Each scraper owns one data file — no other script writes to it. Scrapers fetch from the One Piece Fandom wiki and Reddit. **Files:** repo root.

### `verify.py`
The canon verifier. Compares every claim in `punk_records.json` against `sbs_archive.json` and the manga, intent-aware (serious / confirmation / jocular / ambiguous / dodge). Promotes claims to higher tiers based on agreement; flags conflicts. v3 is the current version. **Free path** runs at $0; `--ai` opens an AI disambiguation pass (~$1–3/run, manual only). **File:** [verify.py](../verify.py).

### `prove.py`
"Prove this single claim." Pass a string; it queries `canon_facts.json` + `sbs_archive.json` for direct evidence. Use during discussion of a specific claim. **File:** [prove.py](../prove.py).

### `audit.py`
Read-only health check. Counts rows, summarises shards, parity-checks CSV vs shards, lists warnings/errors. Output: [docs/audit_report.md](audit_report.md). **File:** [audit.py](../audit.py).

### `find_conflicts.py`
Scans `canon_facts.json` for contradictions (same predicate on same character with disagreeing values). Output: [docs/conflicts_report.md](conflicts_report.md). Note: distinct from the **canon-link aggregator** (which checks shard ↔ fact agreement). **File:** [find_conflicts.py](../find_conflicts.py).

### `scripts/validate_schemas.py`
Validates every data file against its JSON Schema. `--self` only checks the schemas. `--target X` validates one file. **Should block any future bake** if validation fails. **File:** [scripts/validate_schemas.py](../scripts/validate_schemas.py).

### `scripts/validate_relationships.py`
Verifies every `from`/`to` ID in every relationship shard resolves in `entity_index.json`. 0 errors required before promotion. **File:** [scripts/validate_relationships.py](../scripts/validate_relationships.py).

### `scripts/validate_ids.py`
Checks `entity_index.json` for collisions and orphan IDs. Allowlists known cross-type overlaps. **File:** [scripts/validate_ids.py](../scripts/validate_ids.py).

### `scripts/extract_*.py`
One extractor per relationship shard. Reads source data, resolves names → IDs, writes `relationships/_pending/<shard>.json`. Promotion to `relationships/<shard>.json` happens manually after a round-trip diff. Examples: `extract_family.py`, `extract_member_of.py`, `extract_appears_in.py`, `extract_born_in.py`, `extract_sails_on.py`, `extract_owns.py`. **Folder:** [scripts/](../scripts/).

### `scripts/assign_ids.py`
Assigns numeric IDs (`chr:`, `crew:`, `loc:`, `ship:`, etc.) to entity records that don't have one yet. Increments the per-type counter in `entity_registry.json`. Run when new records appear in a source file. **File:** [scripts/assign_ids.py](../scripts/assign_ids.py).

### `scripts/build_entity_index.py`
Rebuilds `entity_index.json` from scratch by walking every entity source file. Yields name → ID and slug → ID mappings, plus self-references (`idx[id] = id`) so cross-type IDs are addressable. **Idempotent** — must be safe to re-run any time. **File:** [scripts/build_entity_index.py](../scripts/build_entity_index.py).

### AI scripts (`sbs_categorizer.py`, `theory_analyzer.py`)
Paid Anthropic API helpers for SBS categorisation and Reddit theory analysis. **Always opt-in, manual, local only.** Never run in CI; `ANTHROPIC_API_KEY` is not in cron. Cost: $0.05–$0.10/pass. **Files:** repo root.

---

## B. Architecture layers (the four-layer model)

### L1 — Entity records
Per-entity JSON files: `punk_records.json` (characters), `devil_fruits.json`, `crews.json`, `locations.json`, `weapons.json`, `items.json`, `ships.json`, `arcs.json`. Each record carries `id`, `name`, `slug`, `aliases`. The "what exists" layer.

### L2 — Canon facts
`canon_facts.json` — ~4,876 rows, every fact tier-tagged with a source citation. Claims like "Luffy's height is 174 cm (post-timeskip), source: Vivre Card 2018". The "what's known and how strongly" layer.

### L3 — Relationship shards
`relationships/*.json` — 12 typed graph files (family, member-of, ate-fruit, appears-in, debuts-in, owns, voices, trains-with, set-in, born-in, cites, sails-on). Total: 34,088 edges. The "what connects to what" layer.

### L4 — Tier-aware integrated rendering
The HTML pages: tier badges per fact, clickable entity click-through, spoiler engine, shards-data panels per page. Cross-links L1 + L2 + L3 visually. **In progress** — character.html is fully migrated, others vary.

### The four-layer model
Combined, L1+L2+L3+L4 gives an interconnected, tier-aware, spoiler-aware Codex. Any one layer alone is wiki noise; the combination is the differentiator. See [CLAUDE.md](../CLAUDE.md) for the per-layer status table.

---

## C. Data files (the nouns)

### `punk_records.json`
The character master record. Owned by `punk_records_scraper.py` + maintained by `verify.py`. Every character's wiki ingest, with origin, age, debut, voice actors, etc. **~1,537 records.**

### `canon_facts.json`
Promoted facts with source citations. Read/append-only by named producers (`verify.py`, `extract_manga_facts.py`, manual). Validated by [schemas/canon_fact.json](../schemas/canon_fact.json). **~4,876 rows.**

### `sbs_archive.json`
Oda's SBS Q&As verbatim. Owned by `sbs_scraper.py` + cleaning scripts. **~1,685 Q&As**, vols 4–113.

### `appearances.csv`
Per-chapter appearance log. Owned by `scraper.py`. **~26,775 rows.** The L3 `appears-in` shard is its successor.

### Entity sources (`devil_fruits.json`, `crews.json`, `weapons.json`, `items.json`, `locations.json`, `ships.json`, `arcs.json`)
One per entity type. Each has its scraper. Each row has `id`, `name`, `slug`, `aliases`.

### `theories_import.json`
Reddit/fan theories scraped by `theory_scraper.py`. **94 theories** with status field (active/debunked/partial/confirmed). Never merged into character profiles.

### `cover_stories.json`
21 cover-story arcs. Not a source for character claims.

### `entity_index.json`
The alias resolver: `{name_lowercase: entity_id}`. Built by `scripts/build_entity_index.py`. ~11,898 entries. Includes self-references so IDs themselves are addressable.

### `entity_registry.json`
Monotonic ID counters per entity type (chr.next, crew.next, ship.next, etc.). **Never decrement.** **File:** [entity_registry.json](../entity_registry.json).

### `bootstrap_unresolved.json`
Names that an extractor couldn't resolve to an entity ID. Triaged manually: alias-of / new-entity / discard. Carries forward across sessions. **48 entries currently** (3 born-in + 45 stale parenthetical-needing).

### `relationships/*.json` (the 12 shards)
The graph layer. One file per relationship type. Each row has at minimum `from`, `to`, `src`. See [docs/relationship-types.md](relationship-types.md) for the full schema per shard.

### `schemas/*.json`
JSON Schema (Draft-07) contracts for every validated file. 18 schemas total. Cross-file `$ref`s resolve through a `referencing.Registry`. **Folder:** [schemas/](../schemas/).

### `docs/curate_decisions.json`
The decision ledger. Maintainer's recorded "approve / reject / defer" verdicts on curate-queue items. `verify.py` reads it on each run to suppress already-decided ambiguities. **File:** [docs/curate_decisions.json](curate_decisions.json).

### `docs/curate_queue.json`
Ambiguous SBS matches awaiting human review. Surfaced in [curate.html](../curate.html). **184 entries.**

---

## C2. Sources of truth — pick the right file for the question

When a page or script needs to answer a question about One Piece data, exactly one file is authoritative. This is the master map. Wire pages and bakes to read from the **authoritative** column directly. Don't pipe through derived files unless you actively want the derived view.

| Question | Authoritative source | Why | Common wrong-source bug |
|---|---|---|---|
| **What chapter does X debut?** | `punk_records.json` `first_appearance` field (wiki) | Wiki editors hand-curate this; the field reads "Chapter N; Episode M". Most reliable per-character debut claim. | Reading `relationships/debuts-in.json` (CSV-derived) misses ~46 characters whose CSV row is far later than their real wiki debut (Lilith CSV=Ch.1181 vs wiki=Ch.1061; Broggy CSV=Ch.1181 flashback vs wiki=Ch.115). |
| **What chapters does X appear in?** | `appearances.csv` (per-panel log) | Only fact-grade source for full per-panel listings, including flashback / cover / silhouette breakdown. | Wiki only has aggregate counts; reading wiki for "all appearances" gives wrong numbers. |
| **What's the verified canon claim about X?** | `canon_facts.json` (with sources) | Tier-tagged + sourced. Read the row for tier + source citation, not just the value. | Reading raw `punk_records.json` field gives un-tiered wiki text. Always read the canon_facts.json view if you care about confidence. |
| **Who is in crew Y?** | `crews.json` (current snapshot) + `relationships/member-of.json` (full edge list with role/since/until/current) | crews.json gives "today's roster"; member-of has the historical edges. | Reading `appearances.csv` to infer membership — appearances ≠ membership. |
| **What entities does X own?** | `relationships/owns.json` | Has `since`/`until`/`current`/`from_owner` fields; full ownership chains. | Reading `weapons.json.wielder` text is fine for one-off display, but loses the chain. |
| **What devil fruit did X eat?** | `relationships/ate-fruit.json` (current=true rows) for live state, all rows for historical | `current` flag handles transferred fruits (Mera Mera: Ace dies → Sabo). | Reading `devil_fruits.json.user_current` only gives the *current* eater, not history. |
| **What family relationships does X have?** | `relationships/family.json` | Bidirectional, stored once (not duplicated per direction). Includes `relation` enum (parent/child/sibling/spouse/sworn-sibling/guardian etc.). | Reading `families.json` directly works for the tree renderer but isn't the L3 canonical form. |
| **What's verified about ship Z?** | `ships.json` for the entity record + `relationships/sails-on.json` for crew connections | ships.json has `id`/`slug`/`aliases`/`affiliation`; sails-on links characters to ships across crew membership and time. | Reading appearance data for ships — there is no per-panel ship log. |
| **Where was X born?** | `relationships/born-in.json` (origin location) | Sub-location-resolved (e.g. "Grand Line (Wano Country)" → loc:00200). | Reading `punk_records.origin` raw text — the shard already does sub-location resolution. |
| **Who voices X?** | `relationships/voices.json` (`lang`/`since`/`until` fields) | Tracks JP+EN, recasts, multiple roles per VA. | Reading `punk_records.voice_actor_jp` text — loses recast history. |
| **What canonical name maps to ID Y?** | `entity_index.json` for *name → ID*, `scripts/lib/query.display_name(id)` for *ID → name* | Single resolver point; handles aliases, invisible-Unicode artifacts. | Building your own lookup table per script — duplicated logic, divergent results. |
| **Is claim X canon?** | `canon_facts.json` row tier + `verify.py --report` | Tier system is `🟢 / 🔵 / 🟣 / 🟠 / 🔴`; sources documented per row. | Reading wiki text and assuming canon — wiki is 🟣 by default. |

### Authority hierarchy (when sources disagree)

1. **Manga** (highest) — Oda's pen, direct
2. **SBS verbatim** with proximity to question — Oda's pen, indirect
3. **Vivre Card / Color Walk Oda / op_magazine_sbs** (🟢 secondary)
4. **Wiki `first_appearance` and similar pinned fields** — community-curated, treat as 🔵 likely
5. **CSV-derived shards** (debuts-in, appears-in totals) — derived, treat as 🟣 unless cross-linked
6. **Reddit / theories** — 🟠, never overrides higher

When two sources disagree, the higher tier wins. The Lilith debug case was a CSV (5) saying Ch.1181 vs wiki (4) saying Ch.1061 — wiki wins, fixed in `_bake_atlas_events()`.

### Where to look first when debugging

| Symptom | First file to check | Then |
|---|---|---|
| Wrong character debut chapter | `punk_records.json` `first_appearance` | `query.first_appearance(name)` |
| Wrong appearance count | `appearances.csv` (raw) | `query.character_dossier(chr_id).appearance_count` |
| Wrong tier on a claim | `canon_facts.json` row's `tier` + `sources` | `verify.py --report` to re-check |
| Page shows wrong character link | `entity_index.json` for the alias key | Check `chr-link-upgrader.js` is wired with `chr-id-map` |
| Audit warning about parity | `docs/audit_report.md` | Cross-reference shard vs CSV in `audit.py` `check_appearances_shard` |

---

## D. Tier system (the canon-policy axis)

### 🟢 Canon (gold)
Direct from Oda: manga, SBS verbatim, Vivre Card, Color Walk, Oda interview. Promoted via `verify.py` auto + human sign-off, OR manually via curate.html. **Highest confidence.**

### 🔵 Likely (ink-blue)
Multiple secondary sources agree, no contradiction. Auto-promoted by `verify.py`; no sign-off needed.

### 🟣 Speculation (violet, dotted)
Wiki-only, one secondary source, unverified. **Default tier for all wiki ingest.**

### 🟠 Rumour (orange, dashed)
Reddit / fan / community theory. Stored in `theories_import.json` only — never reaches character profiles unless promoted.

### 🔴 Disproven (red, strikethrough)
Contradicted by a higher-tier source. Auto-flagged by `verify.py`; kept on record as evidence of the contradiction.

### Tier badges (UI)
Visual indicator next to each fact on a tier-aware page. Class names: `tier-canon`, `tier-likely`, `tier-speculation`, `tier-rumour`, `tier-disproven`. Currently rendered on character.html and selectively elsewhere.

### Promotion
The act of moving a fact from a lower tier to a higher one. Auto for likely → canon when `verify.py` confirms; **always requires maintainer sign-off** for the final 🟢 canon stamp. The wire-up between curate.html "approve" button and the tier-flip in canon_facts.json is **NOT yet built** — see decision ledger `_status.NOT_yet_wired`.

---

## E. Identifier formats

### Numeric IDs (5-digit zero-padded)
`chr:NNNNN` (characters), `fruit:NNNNN`, `crew:NNNNN`, `loc:NNNNN`, `weap:NNNNN`, `item:NNNNN`, `ship:NNNNN`, `va:NNNNN` (voice actors). Stable forever; counters in `entity_registry.json`. **Never decrement, never reuse.**

### Natural-key IDs
`ch:NNNN` (chapters: `ch:1180`), `sbs:volNNN-qNNNN` (SBS Q&As: `sbs:vol078-q0042`), `theory:NNN` (`theory:042`), `arc:slug` (`arc:wano-country`), `saga:slug`. Derived from the underlying data, not from a counter.

### Self-reference
`entity_index.json` includes `idx[id] = id` for every assigned entity. Lets cross-type lookups resolve (e.g. `Funkfreed` is both `chr:02000` and `weap:00014`; the ID itself is always reachable as a key).

### Slug
Lowercase ASCII, hyphen-separated, no diacritics. URL-safe form of an entity name. Used in `?id=` URL params and as a stable filename component.

---

## F. Concepts (the meta-vocabulary)

### Round-trip diff
The promotion gate for relationship shards. After an extractor runs, comparing the canonical-JSON form of `_pending/<shard>.json` against the source-derived expected set must yield `Lost rows = 0`. Prevents silent data loss during extraction. Helper: [scripts/lib/canonical_json.py](../scripts/lib/canonical_json.py).

### Match rate gate
The minimum resolution rate before an extractor's output is promoted. Most shards have a 95% gate (`extract_born_in.py` exits with error below 95%). Below the gate: fix the linker, not the data — symptomatic data shouldn't drive the bar down.

### Cross-link / canon-link
The agreement check between an L3 shard row and an L2 canon fact. If the shard says "Robin debuts in ch:114" and canon_facts has the same claim, that's a pass. Run by 5 `link_*.py` scripts. 0 conflicts as of last check.

### Multi-fact conflict
A find_conflicts.py finding where the same predicate has multiple values from different sources (e.g. "Luffy height: 172/174 (progression)" vs "174 (post-timeskip)"). Often a false positive — one fact is a subset of the other.

### Curate queue
Ambiguous SBS-to-character matches that `verify.py` couldn't auto-promote. Maintainer reviews via [curate.html](../curate.html). Backed by [docs/curate_queue.json](curate_queue.json).

### Curate ledger
The persistent record of maintainer decisions on the curate queue. Each row: `{evidence_id, decision, decided_on}`. `verify.py` reads on every run to skip already-decided ambiguities. **File:** [docs/curate_decisions.json](curate_decisions.json).

### Schema (Draft-07)
JSON Schema is the contract for every validated data file. Stored in [schemas/](../schemas/). `referencing.Registry` resolves cross-file `$ref`s. Validates structure, not semantics — semantic checks live in the validators.

### Spoiler engine
Client-side feature in character.html that hides facts after a user-set chapter cutoff. Uses localStorage to persist the cutoff. Each fact carries a `since_chapter` so the engine knows when to reveal.

### Spoiler cutoff
The integer chapter number above which content is hidden. Set per-user in the page UI; persisted in localStorage.

### Entity click-through
The pattern where any entity reference (chr:, fruit:, crew:, loc:, ship:, etc.) in baked HTML becomes a link to that entity's detail page. Implemented as `entityLink(id)` in character.html and elsewhere. The basis of "the interconnected codex".

### Shards-data block
A `<script id="shards-data" type="application/json">…</script>` block embedded in a baked page. Holds the shard rows that page consumes. Lets pages render shard data without a fetch.

### Dossier (`character_dossier`)
Cross-shard join: given a `chr:` ID, returns appearances + debut + fruit + crews + family + voices + trainers/trainees + birthplace, etc. ~9 shards combined. **File:** [scripts/lib/query.py](../scripts/lib/query.py).

### `by_from` / `by_to` indexes
Lazy O(n)-build, O(1)-lookup grouping by `from` field or `to` field of any shard. Beats per-call full-scan by orders of magnitude on appears-in (26.7k rows). Built on first call by `query.py`.

### Stance badges
Visual indicator on `theories.html`: each cited chapter shows whether it **supports**, **refutes**, or just **mentions** the theory. Sourced from the `cites` shard's `stance` field.

### Producer / consumer
A discipline rule: each data file is owned by exactly one named script (the **producer**), and any number of scripts can read from it (**consumers**). Hard rule: no script writes to another script's file.

---

## G. Process & cadence

### Cron (GitHub Actions)
Weekly run, Sundays 06:00 UTC. Executes `refresh.py --quick`. Free pipeline only — no AI scripts, no `ANTHROPIC_API_KEY`. Workflow file: [.github/workflows/](../.github/workflows/).

### Phase 0 bootstrap
The foundational ID-and-index work: `assign_ids.py`, `build_entity_index.py`, `validate_ids.py`, `validate_relationships.py`. Shipped 2026-04-30. Required before any relationship shard could exist.

### Phases A–E (canon engine)
The L2 buildout: extract manga facts, ingest sources, verify v3, find conflicts, curate UI. All shipped before Phase F began.

### Phase F (convergence)
The L4 buildout. Acts I–IV, all closed:
- **Act I:** 5 cross-link scripts, 0 conflicts, conflict aggregator
- **Act II:** character.html fully migrated
- **Act III:** voices/trains-with/cites shards, fruit/crew page routing
- **Act IV:** born-in/sails-on shards, location/theories/weapons/voices migrations, ship IDs

### Training Time
The named gap-check protocol. Three levels: **Quick** (~5 min, start of session), **Standard** (~20 min, end of work block), **Full Training Run** (~45 min, end of an Act). Catches stale docs, broken validators, accumulated unresolved entries. **File:** [memory/helm_check_protocol.md](../../helm_check_protocol.md) (in personal memory).

### Session deltas
The dated changelog blocks in [CLAUDE.md](../CLAUDE.md). Each session appends a "files added / files modified / what shipped" table. Lets future sessions reconstruct context.

### Decision ledger
Same as **curate ledger** — see section F.

---

## H. External sources

### Wiki (Fandom)
The One Piece Fandom wiki (`onepiece.fandom.com`). Source for entity records and most ingest. **Default tier: 🟣 speculation.** Promoted via `verify.py` corroboration.

### SBS
Oda's Q&A column at the back of each tankōbon volume. Treated as Oda-direct canon when claims are stated seriously. Tier 🟢. Stored in [sbs_archive.json](../sbs_archive.json).

### Vivre Card
Official trading-card data set with character stats (height, age, etc.). **Tier 🔵 likely** — has been revised between editions and contradicted by manga; needs SBS/manga corroboration to reach 🟢.

### Color Walk
Oda's published art-book series with annotations. Tier 🟢 when Oda annotates directly.

### Manga (chapters)
Direct chapter content. Highest authority. Citations carry chapter numbers (`ch:1180`).

### Reddit theories
Source for `theories_import.json`. Always **🟠 rumour**. Never auto-merged into character profiles. User submissions go via GitHub Issues, not auto-accepted.

### Filler arcs
Anime-only, non-canon. **Excluded entirely** — not stored, not linked, not cited.

---

## I. Blockers & exclusions

### NLP-blocked
Used of the `mentions` shard. Free-text mention extraction would need real NLP over SBS and theory bodies. Deferred indefinitely.

### No-source-data blocked
Used of the `forged-by` shard. `weapons.json` has no smith fields; can't be extracted. Only ~3 confident manual rows known (Kozaburo → Wado/Enma).

### AI auto-promotion (forbidden)
`verify.py --ai` and other AI scripts output to the **curate queue** only — never auto-promote to 🟢 canon. Human sign-off always required.

### Auto-acceptance of user submissions (forbidden)
User-submitted theories or facts route via GitHub Issues. Maintainer reads, verifies sources, merges manually. No auto-accept path exists.

### Cost discipline ($0 default)
Every feature has a free path. Paid AI scripts are manual-only, local-only, never in CI. New feature proposals requiring paid AI in the default path are rejected.

---

## See also

- [CLAUDE.md](../CLAUDE.md) — current state, session deltas, suggested next sessions
- [docs/page-status.md](page-status.md) — honest per-page status across all 56 HTML pages
- [docs/canon-policy.md](canon-policy.md) — full tier-promotion rules and Oda-intent interpretation
- [docs/canon-sources.md](canon-sources.md) — source registry with per-source tier defaults
- [docs/id-system.md](id-system.md) — ID format spec
- [docs/relationship-types.md](relationship-types.md) — per-shard schema
- [docs/bootstrap-plan.md](bootstrap-plan.md) — shard migration sequence
- [docs/convergence-plan.md](convergence-plan.md) — Phase F status
- [docs/journey-outline.md](journey-outline.md) — strategic path
- [memory/helm_check_protocol.md](../../helm_check_protocol.md) — Training Time protocol
