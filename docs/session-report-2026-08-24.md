# Session report — 2026-08-24

Twelve commits on `launch-clean`, nothing pushed. 72 files, +6,381 / −697.

Eight checks green at the end, as at the start. **CI now runs seven shield
checks rather than six.**

---

## Part 1 — Why the surprises keep coming

This is the part worth reading first, because it is the only finding that
changes how the work should be planned.

I found new classes of error three separate times this session, and each time it
was because I widened where I was looking, not because I looked harder. That is
a diagnosable pattern, not bad luck.

### The measurement

Every automated leak check reads **data files**. Here is what they actually
cover, by volume of data that reaches a reader:

| | KB | Share |
|---|---:|---:|
| Fully leak-checked — D2/D3 via `gate.py`, plus the new ladder checker | 183 | **2.7%** |
| Partially checked — other audits touch the file, but not for leaks | 4,756 | 70.4% |
| No leak checker at all | 1,899 | 26.9% |

**The leak checkers verify 2.7% of the rendered data.**

That is not because anyone was careless. `gate.py`'s `LORE_PAGES` covers thirteen
small, uniform, flat-list JSON files — the ones that are *cheap* to check. The
bulk of what a reader actually sees is not that shape:

| Rendered to readers, no leak checker | KB | Pages |
|---|---:|---:|
| `sbs_archive.json` | 1,119 | 2 |
| `theories_import.json` | 238 | 2 |
| `crews.json` | 237 | 2 |
| `episode_map.json` | 132 | 2 |
| `episode_dates.json` | 116 | 1 |
| `arcs.json`, `families.json`, `release_events.json`, others | ~55 | 1–3 each |

**An important distinction I do not want to overstate:** those pages are *gated*,
they are just not *verified*. `crews.html` has 10 cutoff references,
`families.html` 7, `episodes.html` 3. Every one of them was hand-written, and
nothing tests any of it. So the honest statement is not "the site is
unprotected" — it is:

> **Almost all of the Spoiler Shield is hand-written per-page JavaScript that no
> test exercises. Looking at it by hand is the only verification it has ever had.**

Which is exactly why looking finds things.

### The three widenings, in order

| # | What I widened to | What it cost | What it found |
|---|---|---|---|
| 1 | Rung-stacked lore pages, which `gate.py` cannot parse | ~1 hour, one new script | **3 leaks**, incl. `Haki` (safe at 597 ✓) rendering behind a Ch. 92 ~ gate |
| 2 | Page *code* rather than page *data* | reading one renderer | Tier numbers printed the stored rank, so hidden tiers left countable gaps — a Ch. 300 ~ reader could infer that something outranks the Five Elders |
| 3 | Driving the actual site in a browser | ~1 hour, hand-driven | **3 more leaks**, incl. Sanji's page naming Germa Kingdom (832 ✓) at Ch. 50 |

Each widening hit a surface nothing had ever checked, and each returned findings
immediately. The rate is a property of the aperture, not of the site's quality.

### What follows from that

I can predict where the next findings are, which is the useful part:

1. **`crews.html` / `crew.html`** — 357 rosters, 237 KB, gated by hand, never
   verified. A crew roster is a membership list, which is the same shape as the
   World Government chart where I found 134 missing people and three broken
   links. **Highest-probability next find.**
2. **`sbs_archive.json`** — 1.1 MB, gated by a *volume × 10* heuristic
   (`search.js:197`, and the same heuristic in `character.html`). A heuristic is
   not a gate; it will be wrong at the edges by construction.
3. **`punk_records` fields other than `residence`** — `occupation`,
   `affiliation`, `epithet`, `age` are all multi-segment and all fail open when
   undated. `field_reveals.json` covers **8 characters of 1,540**. I fixed
   `residence` because that is where I caught it leaking; I have no reason to
   believe it was the only one.
4. **`families.json`, `episode_map.json`, `theories_import.json`** — rendered,
   gated by hand, unverified.

**Stop sampling. Enumerate the surface, then drive coverage from the map.** The
concrete proposal is Part 4.

---

## Part 2 — What was done

### Coverage (the original worklist)

- **World Government chart: 29% → 91%.** `marines-wg.json` went from 11 tiers /
  64 members to **19 tiers / 181 members**. Eight tiers added — the Seven
  Warlords had no tier at all, nor did Impel Down, the SSG, Cipher Pol 1–8, the
  judiciary, the civil administration, or the rear-admiral band. The Warlords
  retire through a Ch. 956 ✓ tier rung rather than deletion, so a reader below
  the Levely still sees the system as current.
- **Will of D.: 83% → 100%.** Clou D. Clover and Nefertari D. Lili added.
- Every chapter derived from `chr-debut-map.json` and `punk_records`, taking the
  **later** where they disagree. 23 new `_qa_flags` entries carry the eight
  marked **?**.
- Baseline raised to 0.9101 / 1.0.

### Leaks found and fixed

| # | Leak | Where it lived | Status |
|---|---|---|---|
| 1 | `Haki` (597 ✓) in the Vice Admirals summary behind a Ch. 92 ~ gate | `marines-wg.json` | fixed, laddered 92/597 |
| 2 | `Empty Throne` (908 ✓) in a Ch. 906 ✓ rung | `void-century.json` | fixed, reworded |
| 3 | `Uranus` (906 **?**) in a Ch. 650 ✓ rung | `void-century.json` | fixed, new 906 rung |
| 4 | Tier numbers printed the stored rank, leaving countable gaps | `marines-wg.html` | fixed, counted over visible tiers |
| 5 | `poneglyphs` meta description named "Road, Mother, Rio" | `add_descriptions.py` + page | fixed, 145 chars |
| 6 | Settings crew picker named all ten Straw Hats, on 55 pages | `settings.js` | fixed, gated + `?v=3` |
| 7 | `residence` named places that do not exist yet (73 values, 70 characters) | `character.html` | fixed, per-place gate |
| 8 | Index appearance counts and the sort order used full-series totals | `characters.html` | fixed, gated counts |
| 9 | `Coby` → dead character page; `Bomba` → the wrong Bomba | `marines-wg.json` | fixed |

### Tooling added

- **`scripts/audit_ladder_leaks.py`** — the D2 question on the three rung-stacked
  pages. **Now the seventh CI check**, negative-tested (reintroducing the `Haki`
  leak makes it exit 1 and name the term, chapter and field).
- **`scripts/parse_sbs_positional.py`** — reads the two SBS answers laid out as
  tables, which the ~80-character proximity matcher structurally cannot reach.
  30 candidates emitted, never promoted.
- **`_bake_loc_debut_map()`** in `bake.py` — 193 dated places from
  `locations.json` + `arcs.json`, up from 106.
- `audit_external_truth.py` — promotables grouped by field and cited source;
  drift values no longer truncated mid-word at 44 chars.

### Reports produced (no data changed)

| Document | Contents |
|---|---|
| `docs/data-integrity.md` | 8 split records, 3 alias shadows, 1 true duplicate, 1 casing collision, 86 id-less records classified. Recommendation per record. |
| `docs/curate-triage.md` | All 189 curate claims: **confirm 148 / needs-eyes 8 / reject 33**, with evidence. |
| `docs/external_conflicts.md` | 150 characters sampled: **465 promotable, 8 drift, 0 parse gaps**. |
| `docs/live-leak-findings.md` | The three browser-found leaks, method and limits. |
| `docs/handoff-report.md` | The original worklist report. |

---

## Part 3 — Everything still open

Ordered by what I would do first, with the reasoning attached.

### A. Verification gaps — build the checkers (highest value)

The 2.7% number is the problem. Three checkers would move it a long way, and all
three are pure-Python, no browser:

1. **Field-value checker.** Join every `punk_records` field value against
   `locations.json`, `chr-debut-map.json` and `devil_fruits.json` debut chapters.
   This would have caught leak #7 **and** leak #6 from the data alone, with no
   browser and no luck. Highest value per hour of anything on this list.
2. **Static-chrome checker.** Sweep every `.html` and every shared `.js` for
   lexicon terms in titles, meta descriptions, blurbs, empty states, `<option>`
   lists, `aria-label`s and `alt` text. Would have caught leaks #5 and #6.
3. **Per-page gating contract.** Generalise `audit_ladder_leaks.py`: each page
   declares its data file, its gating shape and its render rule; the checker
   walks it at every threshold. This is what closes `crews.html`, `sbs.html`,
   `families.html` and the rest of the unverified 1.9 MB.

### B. Data coverage — what makes gating possible at all

| Gap | Size | Consequence |
|---|---|---|
| `locations.json` undated | 54 of 160 records, plus Hachinosu / Zou / Mary Geoise / Baltigo **absent entirely** | Only 42% of residence segments are datable, so ~half of shielded readers' residence rows are now dropped. Every date added restores rows. **Do this first — it is pure gain.** |
| `field_reveals.json` | 8 characters of 1,540 | This is the "undated fields fail OPEN" hole. Every character-page field outside those 8 is ungated by default. |
| Vivre Card not ingested | 362 of 465 promotable claims cite it | The Canon Engine reads only SBS text in the repo, so this whole body of Oda-direct evidence is unreachable. Structurally the largest canon gap. |

### C. Editorial decisions waiting on the Keeper

- **`docs/curate-triage.md`** — 148 confirms, 8 needs-eyes, 33 rejects.
  **Miss Friday is not a promotion question**: the Codex stores January 21st,
  SBS vol 90 says June 21st. A stored value disagreeing with Oda.
- **`docs/data-integrity.md`** — merges. Seven of the WG chart's 17 remaining
  gaps are duplicate records; merging lifts coverage to ~94% with no editorial work.
- **`docs/curate_queue_positional.json`** — 30 candidates, not folded in.
- **Four characters I would not place**: Shanks, Dragon, Caesar Clown, Attach.
- **Clou D. Clover's gate (395 ~)** — his D. is Vivre-Card-only, so there is no
  chapter at which a reader learns it. Needs a policy answer, not a number.
- **Three-Eyed Tribe** — `"Goldenweek (?)"` puts a question mark in reader-facing
  text, the exact failure the audit exists to prevent. Plus a Film Red figure on
  a page with no tier marking, and a stale `_qa_flags` note.
- **Mantra rung is inert** — recommend moving it to `combat-styles.html`.

### D. Smaller, known, unfixed

- **`ancient-weapons.html` meta description names `Uranus`** (906 ✓ lexicon term)
  on a page gated at 357. Identical in kind to the poneglyphs leak I fixed; I
  left it because you asked for poneglyphs specifically. One-line fix.
- **`Road Poneglyph` / `Rio Poneglyph` are not lexicon terms**, so that class is
  noticed, not caught.
- **`Seven Warlords` / `Shichibukai` are not lexicon terms**, though the
  lexicon's own `_qa_flags` asks for them.
- **Bare `bounty` label** on gated index cards — a visible empty label is a trace.
- **`marines-wg.html` is blank below Ch. 4 ✓** and has no `minCh` in
  `nav-burger.js`, so the link is live from Chapter 1. D3 cannot see it.
  `will-of-d.html` handles its floor properly with `page_min` — copy that.
- **`strip_markup()` cannot handle nested templates** — Chinjao's
  `{{Nihongo|…{{Ruby|…}}…}}` epithet leaks markup into the drift comparison and
  reports a false drift. Five-line fix, deliberately not applied because it
  changes what the comparison sees across all 465 promotable rows.
- **`prove.html` re-bakes nondeterministically** — `Wolf Unit` / `Wolf unit`
  collide on a lowercased alias key. Fixed by the §data-integrity merge.

### E. Policy questions, not bugs

- **`api/v1/` is 16 MB of ungated JSON** — `characters.json`, `canon_facts.json`,
  `crews.json` all contain late reveals. It is **not** linked from any page and
  **not** in `sitemap.xml`, so it is not a surface a reader trips over. But it is
  a complete bypass of the shield at guessable URLs. Is the API public and
  therefore spoiler-exempt by design? That is a decision, and it should be
  written down either way.
- **`quiz.html` self-declares that its pool ignores the cutoff.** It is greyed in
  the nav (`soon: true`) and carries a warning banner, so this is handled — but
  the page is still served to anyone who types the URL.
- **Meta descriptions on `haki` / `awakenings` / `void-century`** are
  self-consistent with their gates. A client-side shield cannot gate a `<meta>`
  tag; the honest move is one sentence on `about.html` rather than machinery.

---

## Part 4 — The change I would make to how this is planned

Three things, and the first matters most.

**1. Keep a surface inventory, and make coverage of it the metric.**
Not "do the checks pass" but "what fraction of what a reader can see is
verified". Today that is 2.7%. A file listing every rendered surface — data file,
page, gating mechanism, checker — turns "we keep finding things" into "here are
the 14 places we have not looked yet". The map in Part 1 is the first draft of
that file.

**2. Every new page or feature declares its gating contract.**
The three leaks I found in page code all came from gating being re-implemented
by hand per page. `settings.js` was written without the cutoff in mind at all.
A one-line declaration per page — *this page renders X, gated by Y* — is what
makes a generic checker possible.

**3. Decide on a headless browser.**
I declined to add `playwright` because it is a dependency change I should not
make unasked, so my browser pass was **hand-driven across about 8 of 49 gated
pages**. That is why I can tell you what I found but not what I did not. A
headless driver turns that into a sweep of all 49 at a dozen cutoffs, in CI,
overnight. It is the single change that would stop the surprises. **This is
yours to approve.**

One caveat on my own numbers throughout: the location dates measure when a
*place first appears*, not when it is first *named*, so some severity figures
overstate. The Germa, Kuraigana, Weatheria, Torino and G-5 rows do not have that
problem; the Elbaph ones do.
