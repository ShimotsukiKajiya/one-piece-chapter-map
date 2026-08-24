# Handoff report — 2026-08-24

**No check went from 0 to non-zero.** All six CI checks were green before and are
green after, D1 is green, and the ladder-leak checker added since is green too.
CI now runs seven shield checks rather than six.

**Read this first, because it is the surprise of the run.** Three live spoiler
leaks were found on pages the six checks structurally cannot see. `gate.py`'s
`LORE_PAGES` holds only pages whose data is a **flat list of entries**. The three
laddered pages — `marines-wg.json`, `will-of-d.json`, `void-century.json` — store
rung stacks instead, so **both D2 (leak behaviour) and D3 (blankness) skip them
entirely**. That is where all three leaks were sitting, and one of them had a
Ch. 597 ✓ term rendering behind a Ch. 92 ~ gate.

A fourth leak was in the page code rather than the data: `marines-wg.html`
printed the stored tier rank, so hidden tiers left **countable gaps** in the tier
numbering.

---

## Suite status — the checks and their exit codes, before and after

| Check | Script | Before | After |
|---|---|---:|---:|
| lexicon in sync | `scripts/sync_lexicon.py` | 0 | 0 |
| every entry has a gate chapter | `scripts/derive_gate_chapters.py` | 0 | 0 |
| D2 leak behaviour | `scripts/audit_leak_behaviour.py` | 0 | 0 |
| D3 blankness | `scripts/audit_blankness.py` | 0 | 0 |
| D4 truth provenance | `scripts/audit_truth_provenance.py` | 0 | 0 |
| D5 page coverage | `scripts/audit_page_coverage.py` | 0 | 0 |
| ladder leaks **(added to CI)** | `scripts/audit_ladder_leaks.py` | *(did not exist)* | 0 |

The daily audit now runs **seven** shield checks, not six. The ladder-leak
checker found **3 leaks** on its first run; all three are fixed and it exits 0.
Its CI step was proved not to be a no-op: reintroducing the `Haki` leak makes it
exit 1 and name the term, the chapter and the field, and restoring returns it
to 0. `coverage` was also added to the failure echo — D5 was in the `if`
condition but missing from the message, so a coverage-only failure printed no
reason.

Also run, not in CI:

| Check | Before | After |
|---|---:|---:|
| D1 structure — `scripts/audit_spoiler_coverage.py` | 0 (49/49 pages) | 0 (49/49 pages) |
| `scripts/audit_external_truth.py` (network) | 0 | 0 |

D5 briefly exited **2** mid-run, correctly: I raised the baseline to 91%, then
pulled a member off the chart, and it caught the 91% → 90% drop as a regression.
The member went back on under a corrected name and D5 returned to 0. Baseline now
records 0.9101 / 1.0.

`bake.py` ran after every data change, and the pages were checked in a real
browser at Ch. 300 ~ and caught-up.

---

## 1. Coverage — tiers and members added

### Marines & World Government: 29% → **91%** (55 → 172 of 189)

`marines-wg.json` went from 11 tiers / 64 members to **19 tiers / 181 members**.
Eight tiers added, 117 members added, one member renamed.

**New tiers.** Chapter, marker, and the reason for the chapter:

| Tier | Gate | Mk | Derivation |
|---|---:|:--:|---|
| The Seven Warlords of the Sea | 69 | **?** | Yosaku naming the system. The lexicon's own `_qa_flags` carries the same open question, and there is no `Warlord`/`Shichibukai` term in `terms` to check it against. |
| — retirement rung | 956 | ✓ | The Levely abolishes the system. Implemented as a **second tier rung**, not `maxCh`: the page renderer honours `maxCh` on members only, so a rung stack is what actually retires a tier. A reader below 956 still sees the system as current. |
| Impel Down | 525 | ~ | First chapter the prison is depicted. It is named in dialogue earlier — fail-late. |
| Special Science Group (SSG) | 1061 | ~ | The reader meets the unit as a body on Egghead. The name lands earlier at the Levely — fail-late. |
| Cipher Pol (Units 1–8) | 362 | ~ | First non-CP9 unit shown (Jerry, CP6). |
| Judicial Authority | 164 / 353 | ~ | Two rungs. 164 is the Marine Headquarters Court; the 353 rung adds Enies Lobby, so the island's name is not printed to a Ch. 164 reader. |
| Government Administration | 79 | ~ | The Government orphanage. |
| Rear Admirals & Commodores | 75 | ~ | First commodore shown. |
| Marine Officers & Base Personnel | 4 | ~ | The 153rd Branch ranks. |

**Members.** Every one is gated at a chapter derived from `chr-debut-map.json`
(built from `appearances.csv`) cross-checked against `punk_records`
`first_appearance`, taking the **later** of the two where they disagree. The
convention, stated so you can audit it:

- **✓** the two sources agree and the post is the character's whole identity —
  no later "actually he was X" twist is possible.
- **~** the sources agree, but the rank could be stated a beat after the debut
  panel. Most Marines are here.
- **?** the sources disagree, or belonging is a later reveal than the debut.

Everything marked **?** or set by fail-late is in `marines-wg.json` `_qa_flags`
— thirty entries, twenty-three of them new. The ones that most want your eye:

| Member | Gate | Mk | Why |
|---|---:|:--:|---|
| Crocodile | 126 | **?** | Gated at his debut. His Warlord seat is stated on-panel at some point in Arabasta and I could not date it from the repo. Fail-late would raise this. |
| Marshall D. Teach | 441 | **?** | Appointed as payment for Ace. Not derivable from data. |
| Buggy | 594 | **?** | Post-timeskip appointment. Not derivable from data. |
| Gecko Moria | 449 | **?** | Deliberately his Thriller Bark debut, **not** the 233 ✓ Warlord summit — I am not certain he is named there, so fail-late. |
| Trafalgar D. Water Law | 763 | ✓ | Deliberately **not** his ~594 appointment. The card prints his name, and `Trafalgar D. Water Law` is a 763 ✓ lexicon term. Gating at 763 hides him from 594–762 readers and is the only form that does not leak. |
| Who's-Who | 1020 | **?** | His CP9 past is a Wano reveal, not his 977 ✓ debut. |
| Donquixote Rosinante | 767 | **?** | Debuts 761 ✓; his Marine rank lands a few chapters into Law's flashback. |
| Bell-mère | 78 | ~ | Debuts 77 ✓; her Marine service is told inside the same flashback. |
| Jaguar D. Saul | 393 / 1066 | ✓ | Both chapters taken from `will-of-d.json`, so the two pages agree by construction. |
| Nefertari D. Lili | 1086 | ~ | Silhouette and name land 1084 ~; 1086 is fail-late. |
| Bomba (Marine) | 711 | **?** | Wiki says 652, appearances data says 711. 711 used. |

**What I did NOT add, and why** — 17 names remain missing, and only four of them
are editorial:

| Not added | Count | Why |
|---|---:|---|
| `Akainu`, `Aokiji`, `Kizaru`, `Nerona Imu`, `Rosward Charlos`, `Rosward Rosward`, `Rosward Shalria` | 7 | **Duplicate records of people already on the chart.** Adding them would print the same person twice. Merge recommendations in `docs/data-integrity.md`; the coverage rate rises on its own once they are merged. |
| `Hattori`, `Funkfreed`, `Cerberus` | 3 | A pet pigeon, a sword, and a sword. The line I drew: a jailer beast **holds a post** in the institution and is in; a character's pet or weapon is not. Say if you want that line drawn elsewhere. |
| `Ain`, `Binz`, `Diez Barrels` | 3 | Movie-only. `docs/canon-policy.md` excludes non-canon movie content. `belongs_wg()` in the D5 checker has no filter for it, so they will keep reporting as missing. |
| `Shanks` | 1 | The wiki gives him `Knights of God (former)` and `World Nobles (Figarland Family) (former)`. That is a very late and contested reveal and I will not place a Yonko in the World Nobles tier on a wiki affiliation string. **Yours.** |
| `Monkey D. Dragon` | 1 | Wiki says `Marines (defected)`. No on-panel chapter I could date. **Yours.** |
| `Caesar Clown` | 1 | `Marines (former)` is his MADS-era work under Vegapunk. Listing him in the current science unit would misrepresent him. **Yours.** |
| `Attach` | 1 | A newspaper reporter with a former Marine photography post and no datable reveal chapter. |

### Will of D.: 83% → **100%** (10 → 12 of 12)

- **Clou D. Clover** — gated **395 ~**. Read the flag on this one: **the D. in his
  name is not a manga reveal at all.** It comes from the Vivre Card, so there is
  no chapter at which a reader "learns" it, and the page's whole contract is
  "the gate is when the reader learns the D. is in the name". 395 ✓ is the
  chapter that completes everything the manga tells about him. Your call: keep
  395, raise it, or rule that databook-only carriers do not belong on a
  chapter-gated page at all. I added him because you asked for him, and flagged
  it rather than quietly picking a number.
- **Nefertari D. Lili** — gated **1086 ~**, fail-late over her 1084 ~ silhouette.
  Also added to the World Nobles tier on the WG chart as one of the Twenty.

### Three lexicon leaks fixed on the way — all pre-existing

| Page | Term | Safe at | Was rendering from | Fix |
|---|---|---:|---:|---|
| `marines-wg.json` | `Haki` | 597 ✓ | 92 ~ | Vice Admirals tier summary said "Most carry Devil Fruits or proven Haki". Split into a 92 rung without the term and a 597 rung with it. |
| `void-century.json` | `Empty Throne` | 908 ✓ | 906 ✓ | The Ch. 906 rung printed "The Empty Throne" as its display name *and* in its text. Reworded to withhold it; the 908 rung still carries it. |
| `void-century.json` | `Uranus` | 906 **?** | 650 ✓ | The Ch. 650 rung named Uranus. It now withholds the name and a new 906 rung supplies it. **The lexicon marks 906 `qa`.** If 650 is really where Uranus is first named aloud, this over-hides one word for 256 chapters — correct the lexicon and the rung together. |

`scripts/audit_ladder_leaks.py` is new and asks the D2 question on those three
pages the way each page's own renderer resolves rungs. Reporting only, not wired
into CI — wiring it in is your call and is item 4 in the open decisions below.

### One leak in page code, not data

`marines-wg.html` rendered `TIER ${t.rank}` — the **stored** rank. A hidden tier
therefore left a visible gap: a reader at Ch. 300 ~ saw the chart open at
**TIER 01**, with no TIER 00, which tells them something outranks the Five
Elders. That is the Imu reveal, inferable 600 chapters early from a number.
Tier numbers are now counted over **visible** tiers. Verified in the browser: at
Ch. 300 ~ the chart runs TIER 00–08 with no gaps; caught-up it runs 00–18.

---

## 2. Data integrity — recommendation per record, nothing merged

Full working in **`docs/data-integrity.md`**. `punk_records.json` is untouched.

The evidence that settles most of it: in every suspected split pair the two
records share `name_jp`, share `first_appearance` down to the episode number,
and their chapter sets from `appearances.csv` are **disjoint**. One of the two
has an entity id, a `slug` and an `aliases` list; the other has none of the
three.

| Group | Count | Recommendation |
|---|---:|---|
| **A. Split records** — `Imu`/`Nerona Imu`, the three `Rosward` pairs, `Gab`/`Howling Gab`, `Mash`/`Octopus Mash`, `Nozdon`/`Seagull Guns Nozdon`, `Kashigami`/`Child of Kashigami` | 8 | **Merge into the id-bearing record**, unioning the chapter sets — never summing the appearance counts. `Child of Kashigami` deserves one panel check first. |
| **B. Alias shadows** — `Akainu`/`Sakazuki`, `Aokiji`/`Kuzan`, `Kizaru`/`Borsalino` | 3 | **Merge.** Each shadow has exactly one appearance and **all three are Chapter 569 ✓** — one Marineford chapter that used the epithet form and made the scraper open a new record. The epithet is already in the keeper's `aliases`. D5's split detector cannot see these because it only compares a name against its own last word. |
| **C. True duplicate** — `Lilith` `chr:02370` (1 app) and `Vegapunk/Lilith` `chr:02999` (44 apps) | 1 | **Merge into `chr:02999`.** Live consequence: the WG chart's Lilith card currently resolves to the 1-appearance record, so the reader lands on a near-empty page. |
| **C2. Casing collision** — `Wolf Unit` / `Wolf unit` | 1 | **Merge.** This is also why **running `bake.py` twice with no source change produces a one-line diff in `prove.html`**: the `aliases-map` is keyed on lowercased names and the two collide. |
| **D1. No entity id, no infobox** | 55 | **Do not assign ids.** These are wiki *list* pages, not characters — `Pacifista`, `Buggy Pirates`, `Numbers`, `News Coo`, the eight `Animal Species/<Saga>` pages. Add a scraper exclusion and move them out. `Pacifista` at 28 appearances currently reads as a real omission. |
| **D2. No entity id, has an infobox** | 31 | **Real defect.** Eleven vanish when A–C are applied; the other twenty are genuine characters — `Tama` (32 apps) and `Hack (Fish-Man)` (26) are the two that most visibly cannot be cross-referenced. Run `scripts/assign_ids.py` **after** the merges. |
| **E. Disambiguator inside `name`** — `Bomba (Marine)`, `Ukkari (Character)`, `Hack (Fish-Man)`, `Tsuru (Wano)` | — | Split `name` from a `disambiguator` field. Schema change, so it is yours. Until then the chart prints the suffix — see §5. |

**A1 has a Shield consequence worth knowing before you merge.** The keeper's name
is `Nerona Imu`, and `Nerona` is a 1086 ✓ lexicon term while `Imu` is 908 ✓.
Merging is still safe **only because** `field_reveals.json` already holds the
name ladder (906 → "Imu", 1086 → "Nerona Imu"). Do not rename the record to
`Imu` to make the chart read right — that breaks the ladder and the `chr:02569`
links at the same time.

---

## 3. External truth

`python scripts/audit_external_truth.py --sample 150`

| | |
|---|---:|
| Characters sampled | **150** of 1,540 records (~10%) |
| Promotable — wiki cites Oda, Codex does not | **465** |
| Drift — stored value differs from the wiki's current value | **8** |
| Unreachable | **0** |
| **No infobox found — a parse gap, NOT a pass** | **0** |

Nothing was applied. Output is `docs/external_conflicts.md`, and I extended the
report writer so the promotable set is grouped **by field** and **by cited
source**, as asked:

| Field | SBS | Vivre Card | other | total |
|---|---:|---:|---:|---:|
| origin | 1 | 97 | 0 | 98 |
| blood_type | 9 | 88 | 0 | 97 |
| height | 12 | 80 | 0 | 92 |
| age | 20 | 53 | 0 | 73 |
| birthday | 48 | 11 | 0 | 59 |
| bounty | 0 | 17 | 0 | 17 |
| residence | 7 | 5 | 0 | 12 |
| epithet | 0 | 9 | 0 | 9 |
| occupation | 6 | 2 | 0 | 8 |
| **total** | **103** | **362** | **0** | **465** |

The shape of that table is the finding. **Vivre Card carries 78% of it**, and
`bounty`, `epithet` and `origin` are almost entirely Vivre Card. Both sources are
🟢 canon under `docs/canon-policy.md`, but the Canon Engine only reads SBS text
in the repo, so the Vivre Card column is a body of Oda-direct evidence the
pipeline has no path to at all — 362 claims that will never surface without a
Vivre Card ingest. That is a bigger structural gap than any single value here.

### The 8 drift findings, in full

Read the classification before the table: **only two are the wiki learning
something new, and one of the eight is a bug in our own parser.**

| # | Character | Field | Codex holds | Wiki now holds | What it actually is |
|---|---|---|---|---|---|
| 1 | **Brook** | residence | Florian Triangle (former); Namakura Island (former, temporary) | **Esperia Kingdom (former);** Florian Triangle (former); Namakura Island (former, temporary) | **Real drift.** The wiki gained a leading entry from an Elbaph reveal that postdates the April scrape. This is the same finding the 25-character sample surfaced, confirmed at 150. |
| 2 | **Bellamy** | occupation | Dyer; Pirate Captain (former) | Dyer; **Pirate (former);** Pirate Captain (former) | **Real drift.** The wiki gained an item the Codex does not have. |
| 3 | **Hyougoro** | residence | Flower Capital **(former)**; Udon, Wano Country | Flower Capital; Udon, Wano Country **(former)** | **Real disagreement, and the Codex looks stale.** The `(former)` has moved from one place to the other — that is a claim about where he lives *now*, not a formatting difference. Worth deciding. |
| 4 | **Camie** | residence | Mermaid Cove (Coral Hill) | Coral Hill (Mermaid Cove) | **Possibly real.** The nesting is inverted — one of the two is wrong about which place contains which. Cheap to settle, and it is a fact, not a format. |
| 5 | **Chinjao** | epithet | Don Chinjao; "Chinjao the Drill" | `Don Chinjao・チンジャオ\|Don Chinjao}};` "Chinjao the Drill" | **Not drift — a bug in `strip_markup()`.** See below. |
| 6 | **Sabo** | age | 10 **(flashback, debut)** · 22 (after timeskip) | 10 (debut) 22 (after timeskip) | Formatting. The Codex adds "flashback," and uses `·` as a separator. No disagreement of fact. |
| 7 | **Marco** | occupation | 1st Division Commander (former); Doctor; Apprentice (former) | Doctor; 1st Division Commander (former); Apprentice (former) | Ordering only. Same three items. |
| 8 | **Neptune** | epithet | God of the Sea; Great Knight of the Sea | "Sea God"; "Great Knight of the Sea" | Translation variant plus quote marks. |

So: **2 real content changes** (1, 2), **2 worth a decision** (3, 4), **3 noise**
(6, 7, 8), **1 tooling bug** (5).

### The parse gap — finding #5 is ours, not the wiki's

`strip_markup()` uses non-nesting regexes, and Chinjao's raw epithet nests:

```
{{Nihongo|Don Chinjao|{{Ruby|首領|ドン}}・チンジャオ|Don Chinjao}};<br />…
```

`\{\{Nihongo\|([^|}]*)[^|}]*\}\}` cannot span the inner `{{Ruby|…}}`, and the
generic `\{\{[^}]*\}\}` fallback stops at the **inner** `}}` — so the tail
`・チンジャオ|Don Chinjao}}` survives into the comparison and reports as drift.

**Recommendation:** collapse innermost templates first, repeatedly, before the
specific handlers — `re.sub(r"\{\{[^{}]*\}\}", " ", v)` in a loop until the
string stops changing. I have not applied it: it changes what the comparison
*sees* across all 465 promotable rows as well as the drift rows, and that is a
semantic change to a checker rather than a formatting one. It is a five-line fix
whenever you want it.

**The other headline number: `no infobox found` is 0.** That is the field that
would quietly overstate the sample size, and it is clean — all 150 characters
were genuinely compared, and `unreachable` is 0 as well.


---

## 4. Curate triage

Full table of all 189 claims, with the evidence snippet for each, in
**`docs/curate-triage.md`**. Ordered reject → needs-eyes → confirm, and the
confirms are grouped by the SBS answer they cite, because Oda answers birthdays
in long lists and one read settles a whole block. Nothing promoted;
`curate_queue.json` and `punk_records.json` are both untouched.

| Recommendation | Count |
|---|---:|
| confirm | **148** |
| needs-eyes | **8** |
| reject | **33** |

The queue stores only a ~150-character window around each match, which is why 53
claims read as "needs a real look". Re-reading the **whole cited SBS answer** out
of `sbs_archive.json` settles most of them. **All 189 citations resolved** — none
rests on a missing source.

Four rules did the work: subject named under **any** form Oda uses (he writes
*Kizaru*, not *Borsalino*); value **anchored to its unit**; matched digits not in
a citation; and the `canon-policy` Case 5 dodge filter.

**The ones I am least sure about**

- **The 8 needs-eyes are the honest residue, and 5 of them are one problem**:
  SBS vol 83 q1102 answers birthdays as number-puns — *"#Sai> August (8). 13
  (Happo Navy, 13th Leader)"*. Month and day are both there but the gloss sits
  between them. A machine should not call that confirmed; reading the pun is the
  point of the answer.
- **Miss Friday is not a promotion question at all.** The Codex stores
  **January 21st**. SBS vol 90 q1232 says, in Oda's own list, *"Miss Friday:
  **June 21**"*. That is a **stored value disagreeing with Oda** — reject the
  promotion, then look at the value. The queue matched the digits `1-2-1` in the
  gloss, which is how a wrong value and a right citation ended up in one row.
- **The 33 rejects are the weakest part of this pass.** A reject says the
  *evidence* does not support the claim on *this citation* — it never says the
  stored value is wrong, and it does not go looking for a better citation. Most
  are bounties: the queue matched things like "100 Gomu Gomus" and "Chapter 366"
  against ฿100,000,000 and ฿366,000,000.
- **`Candy`** matched the words "Candy Day" inside someone else's birthday gloss.
  Its near neighbour — a subject name matching a reader's `P.N.` pen-name
  signature, which is how `Yuki` got in — is now detected as a class.
- **The 9 height confirms** rest on a cm figure stated next to the subject's
  name. One of them, **Kujaku 180 cm**, comes from a positional table my
  proximity rule had no right to read correctly. It happens to be right — see
  below — but it was luck, not method.

### The positional-table parser (worklist item 5)

`scripts/parse_sbs_positional.py`. Of 1,685 archived answers, **exactly 13**
contain a bracketed `||` table and **2** are name-to-value tables. The other 11
are lists of foods, sleep times, Spanish numerals and cover-story arcs, and the
parser **declines** them rather than guessing. Two layouts are read: column-major
(Vol. 110 ✓ — names run across the first row) and row-major (Vol. 112 ✓ — one
character per row, aligned **from the right** because the header carries a
leading `Image` column the data rows do not).

**30 candidates emitted** to `docs/curate_queue_positional.json`. They are not
folded into the main queue — `--append` does that when you want them — and
nothing is promoted either way.

**28 of the 30 reproduce the stored value exactly and none conflicts.** That is
the evidence the alignment is right: a one-column slip would scramble the heights
and the conflicts would be obvious. The two that "differ" are occupation wording
(Drake's SWORD role, Gerd's "Ship's Doctor" against a stored "Doctor"). So these
are **tier promotions, not value changes** — the Codex already holds the right
numbers, wiki-derived, and this is Oda's own words arriving to back them.

**Three claims were dropped.** The Vol. 110 ✓ table names `Grus`, and
`lib/resolve.py` cannot reach the record `Prince Grus`: its looseners strip a
leading family name from the *input*, so a short query against a longer record
name has no rule to meet it. His rank, age and height are all in that table and
all currently unreachable. Same mismatch class as Koby/Coby.

---

## 5. Anything you changed that I should re-check

**Chapters marked `?` — assert nothing without checking these.** Crocodile 126,
Marshall D. Teach 441, Buggy 594, Gecko Moria 449, Who's-Who 1020, Donquixote
Rosinante 767, Bomba 711, and the Seven Warlords tier gate at 69. All eight are
in `marines-wg.json` `_qa_flags` with the reasoning.

**Chapters marked `~` set by fail-late** — over-hiding, not leaking, if wrong:
Impel Down 525, SSG 1061, Cipher Pol 362, Judicial 164, Government
Administration 79, Rear Admirals 75, Marine Officers 4, Bell-mère 78,
Nefertari D. Lili 1086, Clou D. Clover 395.

**Two reader-facing name changes on the WG chart.** Both were broken links:

- **`Coby` → `Koby`.** `punk_records` keys him as `Koby`, so
  `character.html?name=Coby` returned *"No record for Coby"*. I verified that in
  the browser. `Coby` stays on the record as the Funimation/4Kids alias. **If the
  house form is Coby, revert this and add the alias instead** — only
  `marines-wg.json` (2 uses) and `bounty_poster_styles.json` (1) use that
  spelling anywhere.
- **`Bomba` → `Bomba (Marine)`.** Two records display the name `Bomba`, and the
  card resolved to `chr:01687`, a Tontatta of the Straw Hat Grand Fleet, instead
  of `chr:01688`, the G-5 Marine. The disambiguator is ugly in reader text and I
  would rather fix it in `punk_records` (§2 E) than on the page. `Ukkari
  (Character)` has the same shape and reads worse.

After these, every member card on the chart resolves to a real record except the
collective **"The Five Elders"** card and **Manmayer Gurou**, who has no entity
id at all.

**Two rewrites of existing reader text** — check the register:
`void-century.json`'s Ch. 906 ✓ throne rung and Ch. 650 ✓ Ancient Weapons rung,
plus a new Ch. 906 **?** rung on the latter.

**Tier ordering on the WG chart is an editorial call I made.** New tiers were
inserted in hierarchy order, and the three late/standalone institutions — SSG,
Impel Down, the Seven Warlords — were appended after the Marine chain, so the
Warlords render last. `rank` is now purely cosmetic since numbering is computed
at render time, so reordering is free if you want it different.

**`scripts/audit_external_truth.py` changed in two ways**: the report writer now
groups promotables by field and source, and drift values are truncated at 200
characters instead of 44 — at 44 most rows were cut mid-word and could not be
acted on.

**Not re-checked by me**: I did not read every one of the 148 confirms
individually — I spot-checked 14 at random plus all 9 height confirms, and the
rest rest on the rule. I did not verify any chapter number against the manga
itself; every number here is derived from repo data or explicitly marked `?`.

---

## 6. What you did NOT do, and why

- **The 17 remaining WG coverage gaps** — itemised in §1. Seven are duplicate
  records (yours to merge, not mine to double-print), three are pets and swords,
  three are movie-only, and four are genuine editorial calls I will not make for
  you: Shanks, Dragon, Caesar Clown, Attach.
- **95% ship gate not reached** — 91%. It is not reachable honestly until the §2
  merges land. After A, B and C the same 172 names would score ~94% against a
  smaller, truer denominator; the last few are the pets and the movie characters.
- **Nothing merged in `punk_records.json`.** Recommendation per record only, as
  instructed.
- **Nothing promoted from any queue.** No tier changed anywhere.
- **`--append` not run** on the positional parser; its 30 candidates sit in
  their own file.
- **Did not add `Seven Warlords` / `Shichibukai` to the lexicon**, though the
  lexicon's own `_qa_flags` says *"Warlord 69 is the Shichibukai system being
  named by Yosaku. Confirm"* and there is no such term in `terms`. Adding one
  means re-syncing `lore-gate.js` and cache-busting it, and I would not touch
  the shield's runtime on a coverage pass. **Recommended below.**
- ~~**Did not wire `audit_ladder_leaks.py` into CI.**~~ **Done on request** — it
  is now the seventh shield step in `.github/workflows/audit.yml`, and it was
  negative-tested rather than assumed.
- **Did not fix the `prove.html` bake nondeterminism** — the fix is the §2 C2
  merge, which is a `punk_records` edit.
- **Did not extend `lib/resolve.py`** for the `Grus`/`Prince Grus` class. It is
  shared by every audit script and a looser matcher there could quietly change
  D5's numbers.
- **Sampled 150 of 1,540 records** in the external check (~10%). The 465
  promotable and 8 drift findings are a 10% sample, not a census.
- **Did not verify anything against the manga.** Every chapter is derived from
  `chr-debut-map.json`, `punk_records`, `will-of-d.json` or `docs/leak-lexicon.json`,
  or is marked `?`.

---

## Open decisions — recommendations, not decisions (worklist item 6)

### 1. The inert Mantra rung

`haki.json`'s Mantra entry has rungs at **254 ✓** and **597 ✓**, but
`nav-burger.js` gates `haki.html` at **minCh 597**, so the 254 rung can never be
reached by a reader who has not already earned the page. It is dead code that
reads as coverage.

**Recommendation: move Mantra to `combat-styles.html`**, which is ungated and
already holds regional and named styles at chapters from 3 ✓ to 1035 ✓ —
Octopus Pot Rosary sits there at 69 ✓, so a 254 ✓ entry is completely at home.
Mantra is Skypiea's own name for a Skypiea ability; a Ch. 254 reader meets it as
a regional technique, which is exactly what that page is for. Leave a Mantra
entry on `haki.html` gated at 597 ✓ as the cross-reference.

The alternative — lowering `haki.html`'s nav gate — is wrong. The page's *title*
is the spoiler, and `Haki` is a 597 ✓ lexicon term; nothing about the page can
be shown early without leaking the word.

### 2. The Three-Eyed Tribe entry

Worse than the flag says, and one part of it is a live instance of the rule this
whole audit exists to enforce.

- `gate_chapter` is **202**, not 86 — `gate_source` is `explicit+text`. The
  `_qa_flags` note saying it derives from a member's debut is **stale**; the
  `debut` field still reads "Ch. 86". Fix the flag or the field, they disagree.
- The member list is `["Nico Olvia (mother of Robin)", "Pudding (latent)",
  "Tot Musica narrator", "Goldenweek (?)"]`. **`"Goldenweek (?)"` puts a question
  mark in reader-facing text** — the exact failure mode as the thirteen
  `(QA: chapter approximate)` strings. `"(latent)"` is doing the same job more
  quietly.
- `Tot Musica narrator` is a Film Red figure. `docs/canon-policy.md` scopes movie
  content to 🔵 movie-canon at best, and this page carries no tier marking.
- `Nico Olvia` is the one you already flagged.

**Recommendation:** reduce the list to what canon supports — Charlotte Pudding,
without "(latent)" — and move Olvia, Goldenweek and the Film Red figure into
`_qa_flags` as candidates with the reason for each. Then confirm 202 against the
chapter the tribe is actually named. Do not delete the entry: the race is real
and the page would lose a row.

### 3. Four pages leak their subject in `<title>` and `<meta name="description">`

True, and **`poneglyphs.html` is much the worst of the four** — worse than the
title:

| Page | nav minCh | `<title>` | `description` |
|---|---:|---|---|
| `poneglyphs` | 218 | "Poneglyphs" — safe, term is 202 ✓ | **"Road, Mother, Rio"** — Road Poneglyphs and the Rio Poneglyph are hundreds of chapters later, and neither is in the lexicon so nothing catches it |
| `haki` | 597 | "Haki Codex" — the term itself, 597 ✓ | "Observation, Armament, Conqueror's" — consistent with the 597 gate |
| `awakenings` | 783 | "Awakenings" — 783 ✓ | consistent with the gate |
| `void-century` | 395 | "The Void Century" — 395 ✓ | consistent with the gate |

Three of the four are self-consistent: the title names the term at the chapter
the page is gated to. The nav gate hides the link, but the page stays reachable
by URL and by search, and the tab title renders before any JavaScript runs.

**Recommendation, in order of cost:**

1. ~~**Rewrite the `poneglyphs` description now.**~~ **Done on request.** It now
   reads *"The Poneglyphs of One Piece — indestructible stones of ancient text,
   with every confirmed location and holder, shown only as far as your
   chapter."* — 145 characters, naming nothing later than `Poneglyphs` itself,
   which is first safe at 202 ✓ and is already in the page title. Changed in
   `add_descriptions.py` (the source of truth for the dict), in the page, and in
   the `og:`/`twitter:` copies, verified in sync and surviving a re-bake.
   **Still open:** adding `Road Poneglyph` and `Rio Poneglyph` to
   `docs/leak-lexicon.json` so this class is *caught* rather than noticed. That
   means re-syncing `lore-gate.js` and cache-busting it, so it is still yours.
2. **Accept the other three as a known, bounded limit** and say so on
   `about.html`. A client-side shield cannot gate a `<meta>` tag, and the
   honest position — *"page titles and search descriptions are not shielded"* —
   costs one sentence and is true.
3. **Only if you want it properly solved:** pre-render neutral titles and
   descriptions at bake time and let the page set the real `document.title`
   after the cutoff is known. That fixes search and the tab, at the cost of the
   pages showing generic titles to crawlers. It is a real change to `bake.py`
   and I would not do it without you asking.

### 4. ~~Wire `scripts/audit_ladder_leaks.py` into the daily audit~~ — done

`LORE_PAGES` is a flat structure, the three laddered pages are not, and **both D2
and D3 skip all three** — which is why a Ch. 597 ✓ term sat behind a Ch. 92 ~
gate with every check green. It is now the seventh shield step in
`.github/workflows/audit.yml`, negative-tested.

**Still open, and the reason this section stays here.** **`marines-wg.html` is
blank for a reader below Ch. 4 ✓**, and the page has no `minCh` in `nav-burger.js`, so the link is live from Chapter 1. D3
does not see it. `void-century.html` is blank below Ch. 193 ✓ but is nav-gated at
395, so only a direct URL reaches it. `will-of-d.html` handles its floor properly
with `page_min` 154 ✓ and a sealed notice — that is the pattern the other two
should copy.
