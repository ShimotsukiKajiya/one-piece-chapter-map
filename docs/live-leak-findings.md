# Live leak findings — driving the site in a browser, 2026-08-24

Every check in CI reads **data**. This pass drove the actual pages at real
cutoffs and read what a reader would see. Three leaks turned up that no checker
looks for, because none of them lives in the lore JSON the lexicon guards.

**All three are now fixed** (commits `6b62ec4`, `6b63a76`, `9a2ea58`), and each
section below records what changed and what it cost. The findings are kept in
full rather than deleted — the *reason* each leak existed is the part worth
keeping, because all three lived in page code and character records rather than
in the lore JSON the lexicon guards, which is why D1–D5 and the ladder checker
were all structurally blind to them.

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

## 1. `residence` leaked places that do not exist yet — FIXED

**Severity was: high. It is on the most-read page type in the site.**

What it looked like. At Ch. 50, `character.html?name=Sanji` rendered:

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

**The real fix**, and the one taken. `residence` is now gated **per place**
rather than truncated to its first segment, because "keep the first" is a guess
that still leaked Nami's Oykot Kingdom and Smoker's G-5. A segment survives only
if every place named in it can be dated and has been reached — brackets checked
as well as the outer name, since `Grand Line (Whole Cake Island)` is safe
outside and a Ch. 825 reveal inside.

A new `loc-debut-map` block on `character.html`, baked by `_bake_loc_debut_map()`,
supplies the dates from two sources already in the repo: `locations.json`
`first_appearance`, and `arcs.json` start chapters — an arc is named for the
place it visits, and its start is at or after that place is first named, so
using it is fail-late. Lower of the two wins. **193 places**, up from 106.

**What it costs, stated plainly.** Undatable places are dropped rather than kept,
because the page's own banner promises it omits "details the Codex can't yet
date" and the undatable set includes Hachinosu, Mary Geoise and the Flower
Capital. Only 42% of residence segments are datable, so **roughly half of
shielded readers' residence rows disappear**. The cure is more coverage in
`locations.json` — 54 of its 160 records carry no date, and Hachinosu, Zou,
Mary Geoise and Baltigo are absent from it entirely — not a looser gate.

Verified in the browser: at Ch. 50 Sanji reads `East Blue (Baratie)` and Zoro
reads `Shimotsuki Village`; at Ch. 600 Sanji gains Momoiro Island (523) and
still withholds Germa; caught-up is unchanged, full annotations and all.

**Caveat on these numbers.** `locations.json` dates when a *place first appears*,
not when it is first *named*. Several rows overstate on that account — the
Elbaph ones especially, since Dorry and Brogy name their homeland at Little
Garden long before Elbaph is shown. The Germa, Kuraigana, Weatheria, Torino and
G-5 rows do not have that problem.

---

## 2. The settings panel named the whole Straw Hat crew — FIXED

**Severity was: high, and it is on 55 pages.**

What it looked like. `settings.js` rendered the crew-theme picker as a hardcoded
`<option>` list:

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

**Fixed.** The list is built by `renderCrewOptions()` from a `CREW_ROSTER` whose
chapters come from `chr-debut-map.json`, not from memory. Robin is the one
deliberate override: she debuts at 114 ✓ as Miss All Sunday and "Robin" is a
Ch. 218 ✓ reveal per the name ladder in `field_reveals.json`, so fail-late takes
218. Rebuilt on every panel open and again immediately after the reader changes
their cutoff in that same panel, so it never needs a reload. A crew theme the
reader has already selected stays listed even if their cutoff later drops below
that debut — it is their own setting, and hiding it would break the theme rather
than protect them. Removal is traceless: no counter, no placeholder, no gap.

All 55 pages were bumped to `settings.js?v=3`. Without that bump the fix could
never have reached a reader — the trap `settings.js` was already on record for.

Verified: Ch. 50 shows 5 options, Ch. 220 shows 6, Ch. 530 shows 9, caught-up
shows 10. The one-off gaps at 220 and 530 are the shield's own 5-chapter safety
buffer holding Robin and Jinbe back, which is correct.

---

## 3. Appearance counts disagreed between profile and index — FIXED

**Severity was: low for the number, higher for the sort order it drove.**

At the same Ch. 50 cutoff:

- `character.html?name=Roronoa Zoro` — "Appearances: **46**" (gated correctly)
- `characters.html` — "Roronoa Zoro … **795** appearances" (full-series total)

The index also shows "Monkey D. Luffy … 1012 appearances". One of the two is
wrong for a shielded reader, and it is the index.

**The sort was the worse half.** "Most appearances" is the default sort, so the
ORDER leaked how prominent a character eventually becomes — Kaya and Jango buried
under people who matter 700 chapters later.

**Fixed.** `apps(c)` returns a count of distinct chapters at or below the
reader's cutoff, computed from `appearances.csv` — the same file `index.html`
and `character.html` already fetch, so it is usually warm. It feeds the count,
the sort and the "Major (50+ apps)" filter alike. Loaded before the first paint,
because rendering the full totals and correcting them a moment later would flash
the very number this hides. Fails closed: if the fetch fails the count is
omitted, never the full total. Skipped entirely when caught up, so that reader
pays no extra request.

Verified: Ch. 50 gives Luffy 45 / Zoro 42 / Nami 36 / Kuro 17, ordered by who
matters *so far*; caught-up restores 1012 / 832 / 795 and issues no CSV request.

Profile and index can still differ by a few chapters — 46 against 42 here. That
is the shield's own `auto` mode relaxing the buffer on detail pages and holding
it strict on indexes. Deliberate, so it has not been forced equal.

A related cosmetic point on the same cards, **not fixed**: the `bounty` label
renders with no value when the bounty is gated, leaving a bare word "bounty" in
the card text. Correct suppression, but a visible empty label is a trace — the
traceless-omission rule would remove the label with the value.

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

## Still open

1. **`locations.json` coverage.** 54 of 160 records carry no date, and
   Hachinosu, Zou, Mary Geoise and Baltigo are not in the file at all. Every
   date added there restores a residence row that fix 1 currently drops. This is
   the single highest-value follow-up.
2. **A checker for this class.** All three leaks lived in **page code and
   character records**, not in the lore JSON the lexicon guards, so D1–D5 and
   `audit_ladder_leaks.py` were all structurally blind to them. A checker that
   joins `punk_records` field values against `locations.json` / `chr-debut-map.json`
   would have caught findings 1 and 2 from the data alone.
3. **The bare `bounty` label** on gated index cards (§3).
4. **The rest of the 49 gated pages.** This was a hand-driven sample of about
   eight. The method's limits in the section above have not changed.
