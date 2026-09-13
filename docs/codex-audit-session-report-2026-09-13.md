# Codex audit session report — 2026-09-13

For the planning chat that wrote `codex-audit-handoff.md`. Written by the local
Claude Code session on `D:\One Piece`. Self-contained: paste the whole file.

**Status in one line:** Prompt 1 (reconcile) is done. Phase 0 (ship the fixes
that already existed locally) is merged, verified and committed, but **not
pushed**. The push is waiting on the maintainer for an account reason (§5).
Prompts 2–5 have **not** been run.

---

## 1. The single most important correction to the handoff

The handoff audited a fresh clone of the public repo's default branch,
`origin/master`. That is what GitHub Pages builds (confirmed:
`gh api repos/.../pages` → source branch `master`). It is **not** where the
maintainer works.

| Branch | What it is |
|---|---|
| `origin/master` | Public, live. Daily bot data refreshes land here. |
| `launch-clean` (local) | Working branch. Pushes to `origin/master`. Had **22 unpushed commits** from the 2026-08-22..24 Spoiler Shield pass. |
| `master` (local only) | Private dev history, ends 2026-05-03. Holds `CLAUDE.md` + the full `docs/`. |
| `wip/2026-05-21-snapshot` (local only) | Full May-21 working state. |

Consequences:

- **The live site does not have the August fixes.** Checked in code on
  `origin/master`: no status gate (Cobra shows "Deceased" to a Ch. 200
  reader), no per-place residence gate (Sanji's page names Germa Kingdom at
  Ch. 50), no settings crew-roster gate (all ten Straw Hats listed at Ch. 50),
  full-series counts on the character index. All fixed on `launch-clean`.
- **Eight audit scripts the handoff didn't know about exist on `launch-clean`
  only:** `audit_leak_behaviour.py` (D2), `audit_blankness.py` (D3),
  `audit_truth_provenance.py` (D4), `audit_page_coverage.py` (D5),
  `audit_ladder_leaks.py`, `audit_external_truth.py`,
  `derive_gate_chapters.py`, `sync_lexicon.py`. Also `lore-gate.js`,
  `status_reveals.json` and `field_reveals.json`.
- **The Section 1 docs are not missing, just on other branches.** 2 of the 26
  are in the working tree (gitignored `docs/conflicts_report.md`,
  `docs/verification_report.md`). The other 24, plus the `canon_link_*`
  reports, exist only on the local `master` / `wip/2026-05-21-snapshot`
  branches, dated 2026-04-26 to 2026-05-21. None were "planned but never
  written". I read every one in full from its newest copy.
- **The current state lives in docs the handoff didn't list:**
  `docs/spoiler-audit-hitlist.md`, `docs/session-report-2026-08-24.md`,
  `docs/live-leak-findings.md`, `docs/data-integrity.md`,
  `docs/curate-triage.md`, `docs/handoff-report.md`,
  `docs/canon-keeper-brief-2026-08-24.md`,
  `docs/planning-session-prompt.md`. I read all of these too.

---

## 2. Prompt 1 — reconciliation of Findings A–E

All four data premises re-verified on **both** branches: `fruit.html:425`
guard; `fruits.html:237/248/265/282` raw `type_canonical`; the four flagship
fruits lack `infobox_image`; all four name pairs exist in `punk_records.json`;
page sizes match (`character.html` 4,303,985 bytes on `launch-clean`).

**One number corrected:** 47 of 158 fruits have a non-empty `infobox_image`,
so **111** lack one, not 108. Possibly empty-string vs absent; for Prompt 4.

### A — shared reveal guard: PARTIALLY TRACKED
- The class is known: `spoiler-surface-map.md:74` (C5 Classification, "✅ Gomu
  Gomu only"), `spoiler-watchlist.md:129`.
- Extending the override to other Mythical/Ancient Zoans was tracked as L17
  (`v1-punchlist.md:169-180`) and marked closed (`CLAUDE.md:86`).
  `FRUIT_REVEALS` in `fruit.html:184` now has **39** entries, not one.
- `fruits.html` was tracked only generally (`spoiler-surface-map.md:184`,
  "index page no gating, TODO"), later gated by debut only (`CLAUDE.md:172`).
- The per-page copy is written into the docs as policy
  (`spoiler-watchlist.md:167`: update "FRUIT_REVEALS map in fruit.html").
  The August report names hand-copied per-page gating as the root cause
  (`session-report-2026-08-24.md:239-243`).
- **Net new:** no doc names `fruits.html`'s type display as a C5 surface. Its
  type **filter** (`:248`) and **sort** (`:265`) also leak, not just the label.
- **Not yet verified live** that the grid shows "Mythical Zoan" at a low
  cutoff. That is Prompt 2's job.

### B — missing fruit artwork: NET NEW
- No doc tracks fruit image coverage (`broad-expand-survey.md:25-26` only lists
  the field). The image docs (L18/L20, silhouette plan) are about images
  leaking, not images missing.
- **A precedent supports the handoff's hypothesis:** on 2026-08-24 the
  external-truth checker found major characters have no infobox on their own
  wiki article; it is transcluded from `Template:<Name> Tabs Top`. Without that
  fallback prominent characters yielded zero fields
  (`spoiler-audit-hitlist.md:497-501`). That was the character parser, not
  `df_scraper.py`. Same mechanism for fruits is unverified.

### C — duplicate characters: PARTIALLY TRACKED, and the docs disagree
- **Brogy/Broggy is tracked in code, not docs.** `validate_ids.py:58-59`
  allowlists the overlap (`chr:01700` / `chr:01701`). `CLAUDE.md:712`
  (Decision #16) demoted 56 such duplicate-key pairs to warnings, "scraper fix
  is the long-term resolution". Symptom visible as a debut mismatch
  (wip `canon_link_report.md:44`: shard Ch. 1181 vs canon Ch. 115).
- **Code contradicts itself:** `bake.py:2486` says "Broggy" and "Brogy" both
  point at `chr:01700`; `validate_ids.py:58` records two ids.
- **MAX Marx/Marks is tracked:** `CLAUDE.md:435` lists it as a spelling-variant
  pair needing a canonical decision, with **Dogra/Dogura** and **Magra/Magura**
  (not in the handoff). `validate_ids.py:84`.
- **The 2026-08-24 dedup pass (`data-integrity.md`) misses all of these.** It
  lists Dogura, Magura and Buckin as separate real characters (`:110-114`) and
  "newly found" the three admiral alias shadows that `CLAUDE.md:109` already
  allowlisted in May. Two dedup passes, two detectors, neither list complete.
- **Buckin/Stussy: not tracked as a pair anywhere. Kept as
  needs-canon-research.** One relevant data point: `curate-triage.md:235` has
  Oda giving Stussy April 24 and `:260` Buckin April 12, which cuts against
  "identical stat block = same record". No conclusion drawn.
- **Hack (Fish-Man)** treated as a legitimate disambiguation
  (`data-integrity.md:111, :128`), matching the handoff.

### D — page weight: PARTIALLY TRACKED (measured, never acted on)
- `page-status.md:27-30` records all three sizes.
- `scripts/ultra_audit.py:334-340` flags >2 MB as INFO and only >5 MB as WARN,
  which is why "~0 errors" coexists with a 4.3 MB page.
- **Net new:** nothing links weight to perceived slowness; no budget or plan.
- **Constraint for any fix:** the site is designed to open over `file://`
  (`bake.py` main prints "no local server needed"), and browsers block
  `fetch()` of local JSON from `file://`. Splitting baked data into lazy JSON
  breaks that. Needs a maintainer decision.

### E — audit tooling scope gap: ALREADY TRACKED, more deeply than the handoff knew
- `session-report-2026-08-24.md:21-30`: leak checkers verify **2.7%** of the
  data a reader sees. `:150-165` proposes a field-value checker, static-chrome
  checker and per-page gating contract.
- `data-integrity.md:72-74`: D5's split detector only compares a name against
  its own last word (`audit_page_coverage.py:227`).
- **Genuinely new:** no image-coverage checker, built or proposed; and the
  "same field, two pages, different answer" framing of Finding A.

### Doc-vs-doc disagreements (signal)
- **Fail-closed vs fail-open.** `spoilerguard-design.md:60-63` + Appendix B say
  missing reveal data hides content. `live-leak-findings.md:60-63`:
  `fieldVisible()` is commented "Undated fields fail OPEN", and
  `field_reveals.json` covers 8 of 1,540 characters. The most important one.
- **Vivre Card tier.** `CLAUDE.md:698` says 🔵 likely;
  `canon-keeper-brief-2026-08-24.md:37` and `handoff-report.md:215-216` say 🟢.
- **"0 conflicts" is stale.** `conflict_log.json` (2026-05-01) and master's
  `canon_link_report.md` (2026-05-02) say 0; wip's `canon_link_report.md`
  (2026-05-21) shows **24** open debut-chapter conflicts, mostly the duplicate
  records (Broggy, Lilith, Imu, Akainu, Aokiji, Charlos, Shalria, Howling Gab).
- Shield coverage quoted as 45/45, 48/48 and 49/49 (`CLAUDE.md:192`, `:86`,
  hitlist `:335`). `page-status.md` says 15 WORKING (`:9`) and 13 (`:21`).

### A trap for Prompt 5 as written
Prompt 5 centralises the guard in `spoiler.js`. But `spoiler.js` loads **after**
pages render, so a guard living there is undefined on first paint
(`spoilerguard-design.md:238-269`). That is why `fruit.html` has boot-safe
helpers, and why `lore-gate.js` was built standalone with no `spoiler.js`
dependency (`spoiler-audit-hitlist.md:211-216`, where `moments.html` failed
open for exactly this reason). The shared helper needs to be boot-safe.

---

## 3. Consolidated issue list (known before Prompts 2–4)

1. **Built but not shipped** — the August pass (§1). Now being shipped (§4).
2. **Known defects, open:** Finding A; `search.js` hardcodes `1188` (7 literals,
   both branches) and renders spoiler name-forms (hitlist item 4);
   `ancient-weapons.html` meta description names Uranus; `marines-wg.html`
   blank below Ch. 4 but linked from Ch. 1; bare "bounty" label on gated index
   cards; `strip_markup()` can't handle nested templates; `prove.html`
   re-bakes nondeterministically (Wolf Unit / Wolf unit).
3. **Data:** duplicate records (§2 C plus `data-integrity.md`'s 13); 55 wiki
   list pages in `punk_records.json`; 20 real characters without ids; 111
   fruits without images; `locations.json` 54/160 undated + 4 absent (so ~half
   of shielded residence rows are dropped); `field_reveals.json` 8/1,540.
4. **Verification gaps:** 2.7% leak-check coverage; no field-value,
   static-chrome, gating-contract, image-coverage or proper dedup checker;
   browser passes hand-driven on 8 of 49 pages.
5. **Needs canon judgement:** Buckin/Stussy; 8 `?` chapters on the WG chart;
   16 combat-style debuts; 189 curate claims (incl. Miss Friday's stored
   birthday vs SBS vol 90); Three-Eyed Tribe; Mantra; Clover's gate; Shanks /
   Dragon / Caesar / Attach; lexicon additions.
6. **Needs a maintainer decision:** merging records in `punk_records.json`
   (scraper-ownership rule); fail-open vs fail-closed; Vivre Card tier;
   `api/v1/` 16 MB ungated; headless browser (playwright); over-hiding
   tolerance; page weight vs `file://`.

### Plan agreed with the maintainer
| # | Phase | Est. sessions (realistic, estimates run 1.5–2× low) |
|---|---|---|
| 0 | Ship what's fixed | 1 (1–2) — **done except the push** |
| 1 | Audits: Prompts 2–4 + Audits 4–5, report-only, **on `launch-clean`** | 2 (3–4) |
| 2 | Triage into fix / design / canon / decision | 1 (1–2) |
| 3 | Isolated fixes (Finding A with a boot-safe design, `search.js`, meta, floor, label, `strip_markup`) | 2 (3–4) |
| 4 | Build verification (5 checkers; playwright if approved) | 4–6 (6–12) |
| 5 | Data coverage (locations, reveal dates, fruit images, portraits, Vivre Card scoping) | 6–10 (10–20) |
| 6 | Canon review (maintainer + Canon Keeper) | 3–5 sittings |
| 7 | Systemic (merges, disambiguator schema, list-page exclusion, ids, page weight) | 4–8 (6–16) |

Context: per the maintainer's strategy the Codex gets ~20% of their time
(EmberStrike is primary), so this is months of work.

---

## 4. Phase 0 — what was done

**Safety:** backup branch `backup/launch-clean-pre-merge-2026-09-13` at
`66065e1` (pre-merge `launch-clean`).

**Before:** ran the full CI suite on unmerged `launch-clean`. `audit.py`,
lexicon sync, gate coverage, D2, D3, D4, D5, ladder leaks, D1 (49/49) all exit
0. Outputs read, not just exit codes: e.g. D2 "0 unprotected · self-test
passed", ladder "58 cutoffs probed". `validate_schemas.py` exits 2 locally
only because `jsonschema` isn't installed on this machine (not a CI check).

**What the bot's 23 commits contained:** data only. Ch. 1191–1192 appearance
rows, `chapter_dates.json`, `canon_facts.json` appearance counts,
`spoiler.js` latest chapter 1190→1192, the data blocks re-baked into HTML, and
`docs/canon-keeper-prompt.md`.

**Merge `03d3448`** (`origin/master` into `launch-clean`), 5 conflicts:
- `canon_facts.json` → origin's. A semantic diff by fact id showed
  `launch-clean`'s side changed only `verified_on` dates. A local `verify.py`
  run on the merged inputs reproduced origin's facts with **0 semantic
  differences** (4,901 facts; 199 canon / 386 likely / 189 ambiguous), so
  origin's file was restored byte-for-byte to avoid key-order churn.
- `character.html`, `conflicts.html`, `prove.html`, `workbench.html` →
  `launch-clean`'s code, data blocks regenerated by `bake.py`. The bake changed
  only those 4 pages, i.e. it reproduced the bot's output everywhere else.
- `docs/canon-keeper-prompt.md` → identical blob on both sides.
- Gitignored `docs/` files backed up before `verify.py` / `find_conflicts.py`
  rewrote them; `curate_queue.json` came back identical.

**After:** the same suite, same exit codes, D3/D5 numbers unchanged, D4 now
current at 2026-09-13.

**Browser (local server, real tab, each probe confirmed the page rendered, no
console errors):**
| Probe | Ch. 200 | Caught up (1192) |
|---|---|---|
| Cobra status | "Status: Alive" | "Status: Deceased" |
| Sanji residence | "East Blue (Baratie)", no Germa/Vinsmoke | full list incl. Germa Kingdom |
| Character index | 219 characters, Luffy 176 apps | 1,484 characters, Luffy 1,009 apps |
| Home chapters stat | — | 1,192 |

**D4 CI blocker found and fixed (`8d75221`).** In a clean worktree (no
gitignored files, as CI checks out), D4 exited 2: it read freshness only from
the gitignored `docs/verification_report.md` / `docs/conflicts_report.md`, so
after the push the daily audit would have gone red every day. Maintainer chose
option A: `scripts/audit_truth_provenance.py` now takes the later of the
report date and a tracked date the bot commits daily — newest `verified_on` in
`canon_facts.json` (stamped by `verify.py`) and `generated_on` baked into
`conflicts.html`. Confirmed those tracked dates equal `chapter_dates.json`'s
on the bot's last three commits. Tested: exit 0 locally and in a clean
checkout; exit 2 when `chapter_dates.json` is a day newer; exit 2 when only
`conflicts.html` is stale.

---

## 5. Not done, and why

- **Not pushed.** Every human push to this repo so far came from
  `ShimotsukiKajiya` (13 pushes, latest 2026-08-22). The only GitHub credential
  on this machine (Git Credential Manager and `gh`) is a different account.
  GitHub's public event feed records the pusher, so pushing from here could
  publicly link that account to the Codex, against the maintainer's
  soft-separate identity strategy. Stopped and handed the maintainer the
  command to push as `ShimotsukiKajiya` themselves. As of writing,
  `origin/master` is still the bot's `99f3660`, `launch-clean` is `8d75221`
  (24 ahead, 0 behind), and the live `settings.js` still lacks the crew gate.
- **Timing:** the bot pushes again daily at 06:00 UTC. A push after that is
  rejected as non-fast-forward and needs the same merge repeated (~10 min).
- **Prompts 2, 3, 4 not run.** They will run report-only on `launch-clean`
  after the push.
- **Prompt 5 not run.** Needs the go-ahead and a boot-safe design (§2).
- Nothing merged, deleted or promoted in any data file.

## 6. Found during Phase 0 (logged, not fixed)

- **Caught-up readers lose the newest 5 chapters on index pages.**
  `effectiveCutoff('public')` always subtracts the buffer
  (`spoiler.js:223`), and `setCaughtUp()` only sets the cutoff
  (`spoiler.js:426-432`). So a reader who pressed "I'm caught up" gets
  `characters.html` filtered at Ch. 1187 (`characters.html:319`): characters
  debuting in the last 5 chapters are absent. `live-leak-findings.md:196`
  says caught-up restores full totals; that is no longer true. Pre-existing,
  not caused by the merge.
- **The bot dropped 6 of 733 SBS image attributions** (Vol. 104) in its
  2026-08-23 run (`d15def6`), though the image files exist and are tracked.
  Already live; likely to recur on Sunday full runs.
- **Local environment:** `jsonschema` not installed, so `validate_schemas.py`
  can't run locally (it's in `requirements.txt`).

## 7. Suggested revisions to the remaining prompts

- **Prompts 2–4:** target `launch-clean`, and say so. Where the live site
  differs (until the push lands), note it beside the finding.
- **Prompt 2:** include sort and filter paths, not just displayed values.
  `FRUIT_REVEALS` already covers 39 fruits; the gap is the other pages.
- **Prompt 3:** seed from `validate_ids.py:48` (`_KNOWN_ALIAS_OVERLAPS`) and
  `data-integrity.md` rather than re-deriving; add Dogra/Dogura and
  Magra/Magura; resolve the `chr:01700` vs `chr:01701` contradiction; keep
  Buckin/Stussy as needs-canon-research.
- **Prompt 4:** use 111, not 108; test the `Template:<Name> Tabs Top`
  transclusion hypothesis against `df_scraper.py` first.
- **Prompt 5:** require the shared guard to be boot-safe (callable before
  `spoiler.js` loads), following the `lore-gate.js` pattern, not a function
  that only exists once `spoiler.js` has loaded.
- **Section 1 of the handoff:** point at the local `master` /
  `wip/2026-05-21-snapshot` branches for the May docs, and add the August docs
  listed in §1 above as the current source of truth.
