# Spoiler & Coverage Hit List — audit of 2026-08-22

Audited against the live site at data currency **Ch. 1190**, gate driven across
20 thresholds from Ch. 5 to caught-up.

## The one-line diagnosis

**The Shield's architecture is sound. Its data coverage is not.**

Proof, from a single page at one cutoff — Portgas D. Ace at effective Ch. 540:

| Field | Reveal ch | Behaviour |
|---|---|---|
| Father — Gol D. Roger | 551 | ✅ correctly hidden |
| Mother — Portgas D. Rouge | 551 | ✅ correctly hidden |
| Status — "Deceased" | 574 | ❌ **leaked** |
| Devil Fruit — "Mera Mera no Mi **(former)**" | 574 | ❌ **leaked** |

Relationships carry `reveal_chapter` and gate perfectly. Infobox fields carry
nothing and are rendered raw. Every fix below is fundamentally *attach a chapter*,
not *rewrite the gate*.

---

## P0 — leaks a reader hits on ordinary use

### 1. ~~`status` is never gated — 136 characters~~ ✅ FIXED 2026-08-22
`character.html:1438` maps `{"1":"Alive","2":"Deceased","3":"Unknown"}` and renders
it unconditionally. 136 records carry `"2"`.

Verified live: **Nefertari Cobra shows "Status: Deceased" at Ch. 200** — a Ch. 1085 ✓
event, on the page a reader opens *during Alabasta*.

Blast radius (reveal − debut): Cobra **943** · Saturn **892** · Vegapunk 425 ·
Ace 420 · Whitebeard 417 · Kanjuro 329.

**FIXED.** New `status_reveals.json` (61 dated entries) + bake block
`status-reveals-data` + `statusAtCutoff()` in `character.html`. Rules:
caught-up shows the stored value; non-Deceased is ungated; dated + cutoff >= ch
shows "Deceased", below it shows "Alive"; **undated omits the row entirely** —
never asserts. Supports an optional `rungs` ladder for presumed-dead-then-alive.

Verified: 17/17 boundary cases pass. Cobra reads "Alive" at Ch. 200 and
"Deceased" at 1085; Ace flips exactly at 574. No console errors.

Remaining: **76 minor characters still undated** — their status row is omitted
while shielded. Safe but incomplete; see `_qa_flags` in status_reveals.json.
Also flagged there: Mjosgard is marked deceased but appears alive at the Reverie
(suspected punk_records error), and T Bone / Guernika have no confident chapter.

### 2. ~~Infobox fields gate on debut, not reveal~~ ✅ FIXED 2026-08-22
Verified live — Law at Ch. 505 (debut 498):
- `Trafalgar D. Water Law` (763 ✓) in **H1, breadcrumb, and browser tab title**
- Residence `Flevance` (762 ~) — the entire Dressrosa backstory
- `Polar Tang` (~659), origin `North Blue`

**Fix:** per-field reveal chapters on name/aliases, residence, origin, occupation,
bounty. Highest blast radius first.

### 3. ~~Possession/quantity suffixes leak by implication~~ ✅ FIXED 2026-08-22
`(former)` on a Devil Fruit implies loss; `(young)` on a VA credit implies a
childhood flashback exists; `(deposed)`, `(defected)`, `(current)` all date themselves.

**FIXED** by a cross-cutting scrubber (`scrubLate`) rather than per-character data.
While shielded it strips parentheticals containing *at death · after timeskip ·
former · deceased · later · current · young · adult · debut*, and collapses
multi-segment values to the first segment. Applied to age, height, weight,
occupation, epithet, bounty, residence, origin, devil fruit — and, separately,
to voice-actor credits so "(young)" no longer implies a childhood flashback.

Verified: "Mera Mera no Mi (former)" → "Mera Mera no Mi"; Absalom's
"34 (debut) · 36 (after timeskip, at death)" → "34".

Also fixed here: the citation label **"SBS (later volume)"** now reads plain
**"SBS"**. The old string hid the volume number but still announced that a later
volume existed — the leak it was meant to prevent.

### 4. Search returns spoiler name-forms
`search.js:166` filters on `debut > cutoff`. Law passes at Ch. 500 and is rendered
as **"Trafalgar D. Water Law"**. Verified live.

**Fix:** search must render the name-form valid at the cutoff, not the stored form.

---

## P1 — structural leaks that let a reader infer what's hidden

### 5. Tier numbers are absolute, so gaps are countable
`marines-wg` renders fixed `TIER 00…10`. At Ch. 5 a reader sees only `TIER 10` and
learns the hierarchy is exactly ten deep. At Ch. 1085 the missing `02` reveals a
secret order ranked directly below the Gorosei and above the World Nobles.

**Fix:** compute tier numbers over visible tiers at render time.

### 6. "N placements are still classified" — **confirmed leak**
Ch. 5 → "63 placements". Ch. 597 → "30 placements". A reader can diff two cutoffs
and measure exactly how much story is ahead, and where.

**Fix:** drop the count. "Some ranks and placements are still classified to you."

### 7. Only 1 of 45 nav items is chapter-gated
At Ch. 5 the burger menu shows **Poneglyphs · Void Century · Will of D. ·
Awakenings · Haki Codex · Ancient Weapons**. Reverie (`minCh: 903`) hides correctly —
the mechanism works and is simply unused.

**Fix:** add `minCh` — Will of D. 154 ✓ · Ancient Weapons ~193 ? · Poneglyphs ~202 ? ·
Void Century 395 ~ · Awakenings ~530 ~ · Haki 597 ✓. Fail late on all.

### 8. Nine pages never load the Shield
`404 · about · corrections · curate · index · lore · news · punk-records · tools`.
`about.html:404` names "Void Century, Joy Boy, and the Ancient Kingdom"; `lore.html`
links "Void Century" by label.

**Fix:** load `spoiler.js` on all reader-facing pages; gate prose mentions.


---

## P2 — content correctness

### 9. 13 maintainer QA notes shipped to production
`(QA: chapter approximate)` etc. baked into `marines-wg.html` reader text — Kong,
Tsuru, Momonga, Onigumo, Stussy, Coby, Garling, Shamrock, Gunko, Sommers, Killingham,
Saturn, Lucci.

**Fix:** move to `_qa_flags`. Add a build assertion that fails on `QA:` in reader text.

### 10. World Government page — four missing institutions
| Missing | Members |
|---|---|
| **Seven Warlords** | 11 — needs a tier rung retiring it at abolition, Ch. 956 ✓ |
| **SSG / Vegapunk satellites** | Vegapunk, Shaka, Lilith, Atlas, Edison, Pythagoras, York |
| **Impel Down** | Magellan, Hannyabal, Sadi, Domino, jailer beasts |
| **Judicial / Enies Lobby** | Baskerville, Spandine |

Plus ~11 named Vice Admirals (Doberman, Bogard, Comil, Lacroix, Lonz, Brannew,
Kujaku…), CP0 agents (Guernika, Maha, Joseph, Hattori, Funkfreed), and three former
Marines of real story weight — **Rosinante, Jaguar D. Saul, Bell-mère**.

### 11. Will of D. is missing two carriers
**Clou D. Clover** (manga + anime — maintainer-confirmed 2026-08-22) and
**Nefertari D. Lili** (1084 ~). Page holds 10 of 12 known carriers.

### 12. Imu rung for 1189–1191 unwritten
Flagged in `_qa_flags`; data now runs to 1190, so the gap is live.

### 13. Name-form mismatches break gating
`Koby`/`Coby` · `Fukurou`/`Fukurō` · `T Bone`/`T-Bone` · `Nerona Imu`/`Imu`.
A name that doesn't resolve in `chr-debut-map.json` **cannot be gated** — it fails open.

---

## P3 — hygiene

### 14. Stale hardcoded chapter constant
`1188` hardcoded in `search.js` (×5) and `nav-burger.js` (×1); `spoiler.js` has 1190.
`search.js:36` **hard-caps any cutoff at 1188** — caught-up readers silently lose
Ch. 1189–1190 from search. Single source of truth needed.

### 15. `canon_facts.json` — 61 of 4,901 facts carry `reveal_chapter` (1.2%)
Zero coverage on occupation, epithet, bounty, origin, birthday. Since `isSafe` is
fail-closed, any surface routed through it would show almost nothing.

### 16. Sitemap and nav gaps
Absent from sitemap: `theories · families · quiz · chapter-release-map`.
Unreachable from nav: `lore · tools · punk-records · conflicts · curate`.

### 17. Banner overstates the gate
Says "Chapter 597"; applies 592 (`cutoff − buffer`). Safe direction, inaccurate sentence.

---

## Working correctly — do not regress

- `isSafe()` fail-closed on missing `reveal_chapter`
- Relationship gating (Ace's parentage at 551)
- `maxCh` rung retirement (Coby migrating Branch Captains → SWORD)
- Devil-fruit field dating (Law's Ope Ope no Mi at 504)
- `minCh` nav gating (Reverie at 903)
- Hard top-bound at `LATEST_PUBLISHED_CHAPTER`
- **Quiz quarantine** — self-declares its pool is unsafe and stays unlinked. Correct call.

---

## Full-site sweep — 2026-08-24

All 58 pages swept at Ch. 5 with an automated harness, not by sampling.

### Method correction (important)

The first harness read `innerText` across an iframe boundary, where it silently
degrades to `textContent` — which **includes `<script type="application/json">`
data blocks**. It therefore reported the entire baked corpus as "visible" on
every data-heavy page. Three alarming findings from that run were false:

| Claimed | Truth |
|---|---|
| atlas.html leaked 614,000 chars | Renders 2,292. Correctly gated. |
| home.html leaked Imu / Nika / Gear 5 | Only "Yonko" leaked. |
| bounties.html leaked Rocks D. Xebec / Law / Oden | Correctly gated. |

Caught by comparing atlas in an iframe (614K) against a real tab (1,411).
**Any harness must strip script/style before measuring, and an absence-of-leaks
result is worthless unless the page is confirmed to have rendered.**

### Root cause of the real leaks

Every genuine leak was a hand-written prose page or a curated lore JSON whose
entries carry a chapter that was never gated on. Two mechanisms were at fault:

1. The page-scoped hook at the bottom of each lore page was a **documented
   no-op** ("Currently a no-op for pages whose data shape needs more work").
2. `spoiler.js` loads **after** those pages render, so `CodexSpoiler` was
   undefined at render time. `moments.html` did gate — on
   `typeof CodexSpoiler !== 'undefined' ? ... : Infinity` — and so **failed
   open**, showing every moment to every reader.

### Fixes shipped

- **`lore-gate.js`** (new) — standalone gate that does not depend on
  `spoiler.js`. Debut gate + lexicon gate + `data-min-ch` attribute gate +
  intro-blurb gate + opt-in prose scrub (`<body data-lore-scrub="1">`).
  Fail-late throughout. Self-installing on DOM ready.
- Entry gating wired on tech, items, materials, ancient-weapons, poneglyphs,
  races, music, moments, reverie (debut chapters) and combat-styles
  (text-only — that file carries no chapters, so a debut gate would empty it).
- **Nav**: `minCh` added to Poneglyphs 218 ?, Void Century 395 ~, Will of D.
  154, Awakenings 530 ~, Haki Codex 597, Ancient Weapons 218 ?. Section counts
  now count only visible items — gating them without that would have created a
  countable-omission leak. Also fixed a pre-existing undercount (Punk Records
  said 11, actually 16).
- **`settings.js`**: theme label named Haki to every reader. Reworded.
- Cache-busting: `nav-burger.js?v=35`, `settings.js?v=2` (previously
  unversioned, so the fix could never have shipped), `lore-gate.js?v=5`.

### Result

58/58 pages clean at Ch. 5 except four **self-referential titles** —
`haki.html`, `awakenings.html`, `poneglyphs.html`, `void-century.html` name
their own subject in the page heading. All four are now hidden from the nav, so
a reader below the cutoff is never linked to them; reaching one needs a typed
URL. Their `<meta name="description">` leaks the same word and **cannot be
gated client-side at all** — search engines read it directly. Accepted residual.

Caught-up restore verified: entry counts match source JSON exactly (tech 16/16,
items 21/21, materials 11/11, ancient-weapons 3/3, poneglyphs 10/10,
moments 27/27, reverie 8/8). No content loss.

---

## Phases 0–1 shipped — 2026-08-24

Following the five-dimension plan. The audit now has a definition and a runner.

### What "audit" means here

| # | Dimension | Question | Checker |
|---|---|---|---|
| D1 | Structure | Is the gate wired into the page? | `scripts/audit_spoiler_coverage.py` |
| D2 | Behaviour | Does the page hide what it should? | `scripts/audit_leak_behaviour.py` |
| D3 | Completeness | Does the page still say anything? | `scripts/audit_blankness.py` |
| D4 | Truth | Are the claims correct? | Canon Engine — Phase 2, not yet re-run |
| D5 | Coverage | Is everything that belongs present? | Phase 4, not yet built |

### Phase 0 — derivation

`scripts/derive_gate_chapters.py` normalises a `gate_chapter` onto every curated
lore entry: explicit field → episode-to-chapter → earliest debut of a named user.
Resolution goes through `entity_index.json` (11,893 aliases) via the new shared
`scripts/lib/resolve.py`, which also closes the Koby/Coby, T-Bone/T Bone and
Fukurou/Fukuro name-form class.

**216 entries across 13 files — 100% dated**, from a starting point where three
files were largely undatable:

| File | Before | After |
|---|---|---|
| `combat-styles.json` | 0/16 — rendered nothing at ANY chapter | 16/16 |
| `music.json` | 4/18 — 2 tracks visible to anyone not caught up | 18/18 |
| `awakenings.json` | 17/29 | 29/29 |

Filler episodes resolve to the nearest LATER adapting episode (fail-late; the
first draft used the earlier neighbour, which surfaces content sooner).

### Phase 0 — nav gates, derived not guessed

`max(first-content-chapter, term-safety-chapter)`. `ancient-weapons` was gated at
218 by guesswork; its first content is Ch. 357. Added derived gates for weapons
(50), items (9), tech (90), materials (145) so no reader can reach an empty page.

`awakenings` moved 530 → **783**: the page carries its own whole-page gate at 783
on the reasoning that awakening as a *mechanic* is Doflamingo's reveal. That is
later than the lexicon's 530, and fail-late defers to it. The lexicon was
corrected to match.

### Phase 1 — one lexicon, two consumers

`docs/leak-lexicon.json` is now authoritative (32 terms, each with a confidence
marker and 3 flagged for QA). `scripts/sync_lexicon.py` regenerates the block in
`lore-gate.js` between markers and fails in CI if they drift.

### Phase 1 — CI

`.github/workflows/audit.yml` gains four steps: lexicon sync, gate-chapter
coverage, D2 and D3. Any failure fails the job, which feeds the existing
deduped issue-filing step. All pure-Python — gating is data-driven, so no
browser is needed in CI.

### Two bugs found in the checkers themselves

Worth recording, because both would have produced false confidence:

1. **The first D2 was circular.** It asked whether the *filtered* set contained
   leaks — but the filter removes them by construction, so it could never fail.
   A deliberately seeded leak passed. D2 now runs a self-test first: it asserts
   the gate excludes a leaking canary and keeps a safe one, so a vacuous pass is
   impossible.
2. **The wiring check accepted a no-op.** Every lore page ships a boilerplate
   stub that reads the cutoff into a data attribute and does nothing — the
   file's own comment calls it "currently a no-op". Counting it as wiring made
   the check pass on exactly the pages it existed to catch. It now strips the
   stub before looking, which immediately caught `haki.html` rendering all 7
   entries ungated. Now wired.

### Verified

- D2 clean (0 unprotected chrome leaks, 0 unwired pages); seeded leak → exit 2,
  restore → exit 0
- D3 clean — every reachable page shows at least one entry
- Browser agrees with the checker: combat-styles renders 1 card (Santoryu, Ch. 3)
  at effective Ch. 5, where it previously rendered none at any chapter; music
  renders 4 Episode-1 themes
- Caught-up restore exact: music 18/18, tech 16/16, items 21/21, materials 11/11,
  combat-styles 16/16, poneglyphs 10/10, moments 27/27
- `audit.py` 0 errors, spoiler coverage 49/49, lexicon in sync

### Still open

- **25 dated entries are suppressed by the lexicon** rather than shown in an
  earlier form. This is the laddering worklist (Phase 3) and the remaining cause
  of thin pages.
- Phase 2 (re-run the Canon Engine) and Phase 4 (coverage, external truth) not
  started.
- **Derivation must be followed by `bake.py`** — the lore JSONs are baked into
  the HTML, so deriving without re-baking leaves pages serving stale data. Cost
  one confusing debug cycle.
