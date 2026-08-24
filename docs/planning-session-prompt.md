# Planning session prompt

Paste the block below to open a **planning** session on the Codex. It produces a
plan document and nothing else — no code, no data, no "while I was in there".

Why this exists: the 2026-08-24 audit ran as a chain of fixes, where each finding
licensed the next action without the maintainer choosing. The work was sound and
the leaks were real, but the shape was wrong — it consumed a day and ended with
more open findings than it started with. This prompt breaks that shape by
separating *deciding what to do* from *doing it*.

---

```
You are opening a PLANNING session on The Shimotsuki Codex (D:\One Piece,
branch launch-clean, live at shimotsukicodex.com). A fan-built One Piece
reference whose defining feature is the Spoiler Shield: readers set a chapter
cutoff and the site shows only what a reader at that chapter could know.

━━ THE ONE HARD RULE ━━
You may not change anything. No code, no data, no bake, no commit, no "quick
one-line fix while I'm here". Read-only tools and analysis only.

Your entire output is a plan document at docs/plan-<topic>-<date>.md, plus the
questions you need me to answer. If you find something alarming mid-session,
WRITE IT DOWN as a finding with a severity — do not fix it. A fix you slip in
un-chosen is the exact failure this session exists to stop.

The one exception: throwaway measurement scripts in the scratchpad are fine and
encouraged. Measuring is planning. Just don't leave anything in the repo.

━━ WHERE THINGS STAND ━━
Read these first. They are the output of the last session and they are the
inputs to yours — do not re-derive what they already establish:

  docs/session-report-2026-08-24.md   what was done; the 2.7% coverage finding;
                                      everything still open, ranked
  docs/live-leak-findings.md          three leaks found by driving the site
  docs/data-integrity.md              punk_records duplicates, nothing merged
  docs/curate-triage.md               189 curate claims, one verdict each
  docs/handoff-report.md              the coverage/audit pass
  docs/canon-keeper-brief-2026-08-24.md  what is waiting on editorial judgement

The headline you are planning against: THE LEAK CHECKERS VERIFY 2.7% OF THE
DATA THAT REACHES A READER. Thirteen small flat-list JSON files are covered
because they were cheap to check. The 1.9 MB a reader actually spends time on
-- sbs_archive, crews, theories, episode_map, families -- has no leak checker
at all. Those pages are GATED (hand-written per-page JS) but not VERIFIED.
Keep that distinction; do not say "unprotected" when you mean "untested".

Eight checks currently exit 0: the six in .github/workflows/audit.yml, plus
audit_spoiler_coverage.py and the newly added audit_ladder_leaks.py.

━━ START BY CHALLENGING THE PREMISE ━━
Before planning anything, spend real effort on this: is the 2.7% framing
correct? Recompute it your own way. Check whether the "covered / partially
checked / unchecked" split holds up, whether volume-of-data is even the right
denominator, and whether the predicted next-findings (crews.html, the SBS
volume x 10 heuristic, punk_records fields other than residence) are the right
bets. If the previous session's diagnosis was wrong or overstated, say so
plainly and plan against your own. I would rather find that out now.

━━ WHAT THE PLAN MUST CONTAIN ━━
Not a wish list. For each proposed piece of work:

  WHAT IT CLOSES     the specific surface or gap, named from the inventory
  EVIDENCE           why we believe it is needed -- a measurement, not a hunch.
                     If you cannot evidence it, mark it SPECULATIVE and rank it
                     below everything evidenced.
  SIZE               S / M / L, and what "L" means in sessions. Say when you
                     are guessing; the last session's estimates ran under.
  RISK               what could break, and what would tell us it broke
  DEPENDS ON         other work, an editorial decision, or a tool decision
  DONE LOOKS LIKE    the check that proves it, ideally automated. "I looked and
                     it seemed fine" is not done.
  IF WE DON'T        the honest cost of skipping it, including "nothing much"

Then order the work, and be willing to say that something well-evidenced still
should not be done yet.

━━ THE SHAPE I WANT OUT OF THIS ━━
Three or four SLICES, each independently shippable and each small enough to
finish in one session with time to verify. For each slice: what I approve, what
you would do, and what you would report back. I want to choose a slice, not
approve a programme.

Explicitly separate:
  - work that BUILDS VERIFICATION (checkers, coverage measurement)
  - work that FIXES KNOWN DEFECTS (the open list in the session report)
  - work that ADDS DATA COVERAGE (locations.json dates, field_reveals, Vivre Card)
  - work that NEEDS A HUMAN DECISION (the Canon Keeper brief)
These have different risk profiles and should not be interleaved in one slice.

━━ DECISIONS YOU NEED FROM ME -- ASK, DO NOT ASSUME ━━
Surface these as explicit questions at the top of the plan. Known ones:

  1. HEADLESS BROWSER. The last browser pass was hand-driven across 8 of 49
     gated pages, which is why it can say what it found but not what it missed.
     playwright would make it a CI sweep of all 49 at a dozen cutoffs. It is a
     dependency change. Worth it? What does it cost to run and maintain?
  2. api/v1/ is 16 MB of ungated JSON at guessable URLs -- not linked, not in
     sitemap.xml. Public and therefore spoiler-exempt by design, or a hole?
  3. The residence gate now drops ~half of shielded readers' residence rows,
     because only 42% of places are datable. Is that the right trade, or should
     the gate loosen until locations.json coverage improves?
  4. How much over-hiding is acceptable generally? Fail-late is the stated rule,
     but nobody has said where it stops being worth it.

Add any others you find. A question I have not been asked is worse than a
question I answer with "your call".

━━ HOW TO WORK ━━
- Measure before you claim. Scratchpad scripts, real numbers, stated method.
- State the aperture of every measurement: how many of how many, sampled how.
- Distinguish what you verified from what you inferred. Every chapter number
  you assert carries a marker: OK certain, ~ confident, ? needs QA.
- If something is fine, say it is fine. A plan that finds everything broken is
  as useless as one that finds nothing.
- Do not pad. If the honest plan is two slices, give me two.
- Check in with me before going deep on any one thread. If a thread looks like
  it will eat the session, come back and ask whether it is worth it first.

Traps that will distort your estimates if you do not know them -- these are
paid-for, do not rediscover them:
  - The lore JSONs are BAKED into the HTML. Any data change means
    derive -> bake.py -> verify. Estimate accordingly.
  - Changing a shipped asset needs a ?v= bump in every HTML file that loads it
    (settings.js is on 55 pages). A fix without it never reaches a reader.
  - character.html runs a synchronous first render far above its helper block;
    a let/const declared with the helpers is in its temporal dead zone.
  - The site frame-busts by design (nav-burger.js:17), so iframe-based test
    harnesses do not work. That is why the last browser pass was manual.
  - resolveRungs() in lore-gate.js and resolve_rungs() in scripts/lib/gate.py
    must change together.
  - bake.py currently re-bakes prove.html nondeterministically (a Wolf Unit /
    Wolf unit casing collision), so a one-line diff there is noise, not a change.

━━ WHEN YOU ARE DONE ━━
Write docs/plan-<topic>-<date>.md, commit ONLY that file, and give me:
  - the questions you need answered, at the top
  - the slices, in the order you would do them
  - what you would NOT do, and why
  - anything in the previous session's findings you think is wrong or overstated

Then stop. Do not start a slice.
```

---

## Notes for me (not part of the paste block)

- The prompt is deliberately read-only. If a planning session finds something
  urgent, the right move is a finding with a severity, and a separate decision
  from me about whether to interrupt the plan.
- "Challenge the premise" is in there on purpose. The 2.7% figure and the
  next-findings predictions are one session's analysis; they should be stress
  tested before a programme of work is built on them.
- Swap `<topic>` for the actual scope if I want a narrower plan — e.g.
  `plan-verification-2026-08-25.md` for just the checker question. A narrower
  prompt gives a better plan than "plan everything".
