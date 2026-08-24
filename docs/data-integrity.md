# Data integrity — `punk_records.json`

Surfaced by D5 (`scripts/audit_page_coverage.py`) on 2026-08-24 and worked up by
hand. **Nothing here has been merged, renamed or deleted.** Every item below is a
recommendation for the maintainer; the file is unchanged.

Why it matters beyond tidiness: a split record makes the coverage checker report
a person as missing from a page they are already on, so the World Government
chart reads as 7 people short when it is not. Records with no entity id cannot be
linked, cross-referenced, or gated by the Shield.

Evidence used, in order of weight:

1. **`name_jp`** — the Japanese name from the wiki infobox. Two records carrying
   the same `name_jp` came from the same infobox.
2. **`first_appearance`** — an identical string, episode number included.
3. **Chapter sets from `appearances.csv`** — whether the two halves ever appear
   in the same chapter.
4. Matching `birthday`, `epithet`, `origin`, `affiliation`.

A note on (3): in all eight split pairs the chapter sets are **disjoint**. That
is consistent with one character recorded under two name forms in different
stretches of the scrape, and it means a merge should **union** the chapter sets,
never sum the `appearances` counts.

---

## A. Split records — the same character held twice

In every pair one record has an entity id, a `slug` and an `aliases` list, and
the other has none of the three. The id-bearing record is the one `entity_index`,
`canon_facts` and `api/v1` already point at, so it is the one to keep.

| # | Keep | Fold in | Same `name_jp` | Same `first_appearance` | Chapter overlap | Recommendation |
|---|---|---|---|---|---|---|
| A1 | **Nerona Imu** `chr:02569` · 32 apps | `Imu` · no id · 3 apps | ネロナ・イム聖 | Ch. 906 | 0 of 41 | **Merge.** `Imu` is already in the kept record's `aliases`. |
| A2 | **Rosward Charlos** `chr:02733` · 8 apps | `Charlos` · no id · 4 apps | ロズワード・チャルロス聖 | Ch. 499 | 0 of 12 | **Merge.** Birthday June 1st on both. |
| A3 | **Rosward Rosward** `chr:02734` · 7 apps | `Rosward` · no id · 4 apps | ロズワード・ロズワード聖 | Ch. 497 | 0 of 11 | **Merge.** Birthday June 28th on both. |
| A4 | **Rosward Shalria** `chr:02735` · 6 apps | `Shalria` · no id · 1 app | ロズワード・シャルリア宮 | Ch. 497 | 0 of 7 | **Merge.** Birthday March 29th on both. |
| A5 | **Gab** `chr:02004` · 5 apps | `Howling Gab` · no id · 1 app | ガブ | Ch. 580 | 0 of 6 | **Merge.** `"Howling" Gab` is the epithet on the kept record. |
| A6 | **Mash** `chr:02428` · 3 apps | `Octopus Mash` · no id · 3 apps | マッシュ | Ch. 204 (cover) | 0 of 6 | **Merge.** Cover-story character; same occupation string. |
| A7 | **Seagull Guns Nozdon** `chr:02793` · 3 apps | `Nozdon` · no id · 4 apps | シーガル・ガンズ・ノズドン | Ch. 0 | 0 of 7 | **Merge.** Note the kept record has *fewer* appearances than the stub. |
| A8 | **Kashigami** `chr:02275` · 2 apps | `Child of Kashigami` · no id · 1 app | カシ神 | Ch. 287 | 0 of 3 | **Merge, with a look first.** Same `name_jp`, same birthday (Nov 4th), same four-god epithet — but "Child of" reads like it could be a separate Shandia figure. Worth one panel check before folding. |

**A1 carries a Shield consequence.** The kept record's name is "Nerona Imu", and
`Nerona` is a Ch. 1086 lexicon term while `Imu` is a Ch. 908 one. Merging is
still safe, because `field_reveals.json` already holds the name ladder:

```json
"Nerona Imu": {"name": [{"ch": 906, "value": "Imu"},
                        {"ch": 1086, "value": "Nerona Imu"}]}
```

Keep the record keyed `Nerona Imu` and let the ladder do the display. Do **not**
rename the record to `Imu` to make the chart read correctly — that would break
the ladder and the `chr:02569` links together.

## B. Alias shadows — the epithet recorded as a second person

Three of the admirals exist twice: once under the birth name and once under the
epithet. Each shadow has **exactly one appearance, all three in Chapter 569** —
a single Marineford chapter that used the epithet form and made the scraper open
a new record. In each case the epithet is *already* in the kept record's
`aliases`, and the `first_appearance` strings are identical to the character.

| # | Keep | Fold in | Shadow's only chapter | Recommendation |
|---|---|---|---|---|
| B1 | **Sakazuki** `chr:02756` · 51 apps | `Akainu` · no id · 1 app | 569 | **Merge.** `Akainu` is already an alias. |
| B2 | **Kuzan** `chr:02352` · 58 apps | `Aokiji` · no id · 1 app | 569 | **Merge.** `Aokiji` is already an alias. |
| B3 | **Borsalino** `chr:01694` · 63 apps | `Kizaru` · no id · 1 app | 569 | **Merge.** `Kizaru` is already an alias. |

These three are not caught by D5's split detector, because it only compares a
name against its own last word. A checker that also compared each record's name
against every other record's `aliases` would have found them.

## C. Same name, two records — one true duplicate

Fourteen name pairs share a display name. Twelve are legitimate: the wiki
disambiguates them and they are genuinely different people (`Kaku` / `Kaku
(Wano)`, `Bjorn` / `Bjorn (Pirate)`, `Cerberus` / `Cerberus (Sword)`, and so on).
Two are not:

| # | Records | Recommendation |
|---|---|---|
| C1 | `Lilith` `chr:02370` · 1 app **and** `Vegapunk/Lilith` `chr:02999` · 44 apps — both named "Lilith", both `Marines (SSG) (Former)`, both first appearing Chapter 1061 | **Merge into `chr:02999`.** The thin record's single appearance is Ch. 1181. Live consequence: the World Government chart's Lilith card currently resolves to `chr:02370`, the 1-appearance record, so the reader lands on a near-empty page. |
| C2 | `Wolf Unit` · 2 apps **and** `Wolf unit` · 1 app — differ only in capitalisation, neither has an id | **Merge into `Wolf Unit`.** See §E: this pair is also the cause of a nondeterministic bake. |

## D. Records with no entity id (86)

They fall into two groups, and only one of them is a defect.

**D1 — 55 records with no `raw_keys` at all.** No infobox was ever scraped for
these, because they are not characters: `Pacifista`, `Ammo Knights`, `Buggy
Pirates`, `Numbers`, `News Coo`, `Kumate Tribe`, `Manticores`, `Going Merry`,
`Susu Susu no Mi`, `Space Pirates`, and the eight `Animal Species/<Saga>` pages.
These are wiki **list** pages the character scraper swept up.

> **Recommendation:** do not assign ids. Add an exclusion to
> `punk_records_scraper.py` for pages with no character infobox, and move the
> existing 55 out of `punk_records.json` — they inflate the record count,
> they appear in character searches, and `Pacifista` (28 appearances) is high
> enough in the appearance ranking to look like a real omission.

**D2 — 31 records that DO have an infobox and simply never got an id.** These are
the real defect. Eleven of them are the split/shadow halves above and disappear
when §A and §B are applied. The remaining twenty are genuine characters:

| Character | Apps | Character | Apps |
|---|---|---|---|
| Tama | 32 | Buckin | 3 |
| Hack (Fish-Man) | 26 | Candelle | 3 |
| Brownbeard | 24 | Dogura | 3 |
| Tenguyama Hitetsu | 8 | Gallant Hippo | 3 |
| Tsuru (Wano) | 8 | Magura | 3 |
| Gyoro | 7 | Lola | 2 |
| Nyon | 7 | Manmayer Gurou | 2 |
| Reuven | 4 | Fighting Bull | 1 |
| Lami | 1 | Master of the Waters | 1 |
| Slime | 1 | Ukkari (Character) | 1 |

> **Recommendation:** run `scripts/assign_ids.py` over these twenty after the
> merges in §A–§C, so no id is spent on a record that is about to be folded away.
> `Tama` at 32 appearances and `Hack (Fish-Man)` at 26 are the two that most
> visibly cannot be cross-referenced today.

## E. Disambiguators stored inside the `name` field

`Bomba (Marine)`, `Ukkari (Character)`, `Hack (Fish-Man)`, `Tsuru (Wano)` and the
rest of the `(…)` records keep the wiki's disambiguation suffix in the `name`
field, which is also what every page prints. The World Government chart now shows
"Bomba (Marine)" and "Ukkari (Character)" to readers, because the plain forms do
not link: `character.html?name=Bomba` resolves to `chr:01687`, a Tontatta of the
Straw Hat Grand Fleet, not to `chr:01688`, the G-5 Marine.

> **Recommendation:** split the field — `name` for display, a separate
> `disambiguator` for the suffix, with the record key unchanged. Pages then print
> "Bomba" and link by id. This is a schema change, so it is the maintainer's call
> rather than a mechanical fix.

**§C2 has a second symptom worth naming.** `bake.py` writes an `aliases-map` into
`prove.html` keyed on lowercased names, so `Wolf Unit` and `Wolf unit` collide on
`"wolf unit"` and whichever is visited last wins. The result is that **running
`bake.py` twice with no source change produces a one-line diff in `prove.html`**.
Merging C2 removes the collision and makes the bake deterministic again.

---

## Suggested order

1. §B (three alias shadows) — lowest risk, alias already present on the keeper.
2. §A1–A7 — merge, union the chapter sets, keep the id-bearing record.
3. §A8 — panel check on "Child of Kashigami" first.
4. §C1, §C2.
5. §D1 — exclusion rule in the scraper, then move the 55 list pages out.
6. §D2 — `scripts/assign_ids.py` over what remains.
7. §E — schema decision.

After §A, §B and §C the World Government chart's coverage rate rises with no
editorial work at all: seven of the seventeen names it still reads as missing
(`Akainu`, `Aokiji`, `Kizaru`, `Nerona Imu`, `Rosward Charlos`, `Rosward
Rosward`, `Rosward Shalria`) are duplicate records of people already on the page.
That would take it from 91% to roughly 94% against a smaller, truer denominator.
