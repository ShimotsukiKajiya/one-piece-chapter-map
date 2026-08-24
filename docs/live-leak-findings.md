# Live leak findings — driving the site in a browser, 2026-08-24

Every check in CI reads **data**. This pass drove the actual pages at real
cutoffs and read what a reader would see. Three leaks turned up that no checker
looks for, because none of them lives in the lore JSON the lexicon guards.

**Nothing here is fixed.** These are findings.

## Method, and its limits

The site frame-busts by design (`nav-burger.js:17`, anti-clickjacking), so an
iframe harness is impossible — the first attempt navigated the top window. No
`playwright`/`selenium`/`puppeteer` is installed and adding one is a dependency
change, so this was **one navigation per page per cutoff, by hand**.

That makes it a **sample, not a sweep**: ~8 pages at Ch. 50, plus spot checks at
Ch. 300 and Ch. 600. 49 pages are gated; most were not visited. Absence of a
finding on an unvisited page means nothing.

Measurement stripped `script`/`style`/`template`/`link` before reading text —
otherwise `textContent` reads the hidden `<script type="application/json">` data
blocks — and every probe recorded a "painted element" count so an unrendered
page could not be mistaken for a clean one.

---

## 1. Character infobox `residence` leaks places that do not exist yet

**Severity: high. It is on the most-read page type in the site.**

At Ch. 50, `character.html?name=Sanji` renders:

> Residence: East Blue (Baratie); **Germa Kingdom**; Momoiro Island — SPEC Wiki

Germa Kingdom is a Whole Cake Island reveal. `locations.json` dates it to
**Ch. 832 ✓** — the repo's own data. A reader who has just met Sanji at the
Baratie is told he is connected to Germa, 789 chapters early. Verified in the
browser at Ch. 50 **and** at Ch. 600.

Same class, same page type:

| Character | Shows | Place debuts | Reader's chapter | Apps |
|---|---|---:|---:|---:|
| Sanji | Germa Kingdom | 832 ✓ | 43 | 770 |
| Roronoa Zoro | Kuraigana Island | 524 ✓ | 3 | 790 |
| Monkey D. Luffy | Mt. Colubo | 582 ✓ | 1 | 1006 |
| Tony Tony Chopper | Torino Kingdom | 524 ✓ | 134 | 698 |
| Nami | Weatheria | 523 ✓ | 8 | 826 |
| Smoker / Tashigi | G-5 | 681 ✓ | 97 / 96 | 85 / 78 |

### Why it happens

`character.html` gates infobox fields in two steps, and neither catches this:

1. `fieldVisible()` hides a field only when `field_reveals.json` carries an
   explicit chapter for that character *and* field. Its own comment says
   **"Undated fields fail OPEN"** — and `field_reveals.json` covers **8
   characters** out of 1,540.
2. `scrubLate()` is the cross-cutting mitigation. It strips late parentheticals
   (`(former)`, `(after timeskip)`) and, for multi-segment values, keeps only
   the first segment — **but it splits on `·` (middle dot) only.**

`residence` is semicolon-delimited. So:

```
stored        East Blue (Baratie) (former); Germa Kingdom (former); Momoiro Island (former, temporary)
scrubLate()   East Blue (Baratie); Germa Kingdom; Momoiro Island     <-- rendered at Ch. 50
```

The scrubber removed the three `(former)` annotations, which is what it was
written to do, and kept all three places, which is the gap.

### What a fix buys, honestly

Adding `;` to the separator list in `scrubLate()` is one line:

| Leak severity | today | with `;` added |
|---|---:|---:|
| any gap | 73 | 61 |
| gap ≥ 100 chapters | 43 | 33 |
| gap ≥ 300 chapters | 31 | 24 |

It kills the worst cases — Sanji/Germa, Zoro/Kuraigana, Luffy/Mt. Colubo,
Chopper/Torino all resolve to a correct first entry. **It does not close the
class**, because the wiki does not order residences chronologically: Nami's
first listed residence is Oykot Kingdom (Ch. 77 ✓, she debuts at 8), Smoker's is
G-5 (Ch. 681 ✓, he debuts at 97). First-segment-only is a heuristic, not a gate.

**The real fix** is to gate `residence` per place against `locations.json`, which
already holds a `debut_chapter` for 106 locations. That is a feature, not a
one-liner, and it is the maintainer's call.

**Caveat on these numbers.** `locations.json` dates when a *place first appears*,
not when it is first *named*. Several rows overstate on that account — the
Elbaph ones especially, since Dorry and Brogy name their homeland at Little
Garden long before Elbaph is shown. The Germa, Kuraigana, Weatheria, Torino and
G-5 rows do not have that problem.

---

## 2. The settings panel names the whole Straw Hat crew, at every chapter

**Severity: high, and it is on 55 pages.**

`settings.js` renders a crew-theme picker as a hardcoded `<option>` list:

```
🎩 Luffy · 🗡 Zoro · 🍊 Nami · 🎯 Usopp · 🚬 Sanji ·
🦌 Chopper · 📚 Robin · 🤖 Franky · 🎻 Brook · 🐠 Jinbe
```

Confirmed rendered at Ch. 50. A reader who knows five Straw Hats opens Settings
and is handed the final roster — including that the crew ends up with a reindeer,
an archaeologist, a cyborg, a skeleton and a fish-man. Debuts: Robin 114 ✓,
Chopper 134 ✓, Franky 329 ✓, Brook 442 ✓, Jinbe 528 ✓. At Ch. 50, **five of the
ten have not appeared.**

`settings.js` reads the cutoff for the shield controls it draws, and never
applies it to this list.

The leak-lexicon policy names this surface explicitly: *"a term must not appear
in ANY reader-facing surface below its chapter: page copy, entry text, nav
labels, section counts, **settings panel**, page titles, meta descriptions."*

Fix: filter the options by debut chapter against the effective cutoff. Note the
trap already recorded in the audit — **`settings.js` is cache-busted (`?v=2`)
across 55 pages, so a fix has to bump every one of them to `?v=3` or it will
never reach a reader.**

---

## 3. Appearance counts are gated on the profile and ungated on the index

**Severity: low, but it is an inconsistency, not a judgement call.**

At the same Ch. 50 cutoff:

- `character.html?name=Roronoa Zoro` — "Appearances: **46**" (gated correctly)
- `characters.html` — "Roronoa Zoro … **795** appearances" (full-series total)

The index also shows "Monkey D. Luffy … 1012 appearances". One of the two is
wrong for a shielded reader, and it is the index.

A related cosmetic point on the same cards: the `bounty` label renders with no
value when the bounty is gated, leaving a bare word "bounty" in the card text.
Correct suppression, but a visible empty label is a trace — the traceless-omission
rule would remove the label with the value.

---

## What was verified working

Tested at Ch. 50 unless noted. All rendered (painted-element counts recorded),
and no lexicon term appeared above its first-safe chapter on any of them.

| Page | Behaviour |
|---|---|
| `character.html` (Zoro, Sanji) | Honest banner: *"omits everything revealed after Ch. 50, plus details the Codex can't yet date."* Facts limited to Ch. 2 and Ch. 5. Bounty, status and family all correctly suppressed; Sanji's **Vinsmoke** name never appears. |
| `characters.html` | **88 of 1,540** characters shown — filtered to those who have debuted. |
| `will-of-d.html` | Correctly sealed. Zero carrier cards and an honest notice: *"The mystery this page tracks has not yet surfaced in your reading. It first gets its name in Chapter 154 — keep going."* |
| `moments.html` | Two moments, both Ch. 1. No chapter number above the cutoff anywhere. |
| `home.html` | "Today in Canon" showed *Romance Dawn Arc · Ch. 5*, chapter-appropriate. |
| Burger nav | **10 of 11** gated pages hidden from the menu at Ch. 50. `items.html` shows, correctly — its gate is Ch. 9. |
| `marines-wg.html` | Ch. 300: TIER 00–08, no gaps. Caught-up: TIER 00–18, 178 members. |

The onboarding overlay does say *"Set cutoff to the latest published chapter
(Ch. 1190)"*, and `home.html` shows a **1,190 Chapters** stat. Both tell a Ch. 50
reader how long the series is. That is inherent to offering a cutoff control at
all, and it is not a story beat — noted rather than filed as a leak.

---

## Recommended order

1. **`settings.js` crew picker** — widest blast radius, on 55 pages, and the
   leak is the crew roster itself. Remember the `?v=` bump.
2. **`scrubLate()` `;` split** — one line, kills the worst residence leaks.
3. **`residence` gated per place against `locations.json`** — the actual fix for
   the class.
4. **Appearance count on `characters.html`** — make it agree with the profile.
5. A checker for this class. All three findings live in **page code and
   character records**, not in the lore JSON the lexicon guards, so D1–D5 and
   the ladder checker are all structurally blind to them.
