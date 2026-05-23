# Canon Policy — what counts, what doesn't, what gets saved where

This document is the law for what enters the Codex's data files.
Future maintainers (including future-me) must not deviate from it
without an explicit decision recorded here.

---

## How Oda's style is interpreted (the four canon cases + dodge filter)

Oda communicates in several different registers in SBS. The verifier
recognises four valid canon cases and one rejection case:

### Case 1 — Direct statement (default)
Oda plainly states the value in his answer.
- **Detection:** value appears verbatim in the answer + character name
  within sentence proximity (~80 chars) + no negation word in the 30
  chars before the value
- **Tier:** 🟢 CANON
- **Intent:** `serious`
- **Example:** Q: "What's Sanji's birthday?" A: "Sanji was born March 2."

### Case 2 — Reader-proposed, Oda-agreed
The reader proposes a value in the question and Oda confirms it.
- **Detection:** value appears in the QUESTION + answer opens with a
  confirmation word (Yes / Correct / Exactly / That's right / Indeed
  / Precisely / "はい" / "正解" / etc) within the first ~30 chars
- **Tier:** 🟢 CANON
- **Intent:** `confirmation`
- **Example:** Q: "Is Yamato's birthday March 5?" A: "Yes! That's right."
- **Why this counts:** the reader did the proposing, but Oda's "yes" is
  the canon authority. Same epistemic weight as Case 1.

### Case 3 — Joke (still on record)
Oda answers but signals it's a joke. The fact stays on record —
suppressing it would erase part of the SBS — but it's tagged so
readers know how to read it.
- **Detection:** value matches per Case 1 or 2, AND a joke marker
  appears in the answer: `lol`, `haha`, `(joke)`, `(笑)`, `kidding`,
  `just kidding`, certain emoji (😂😆😅🤣😄)
- **Tier:** 🟢 CANON
- **Intent:** `jocular`
- **UI:** small 😄 next to the CANON badge with tooltip
  "Oda said this as a joke — but on the record"
- **Example:** Q: "What does Sanji bleed?" A: "Curry. lol"

### Case 4 — Sarcastic / ambiguous confirmation
Oda confirms or denies via tone rather than literal words. **Pure
regex cannot reliably parse sarcasm.**
- **Detection:** match present but no clear case 1/2/3 signal, OR
  digit-group-only match (no exact value match)
- **Tier:** 🔵 LIKELY by default
- **Intent:** `ambiguous`
- **Surfaces in:** `curate.html` for human review — the maintainer
  can manually upgrade to CANON via the curate UI
- **Why not auto-promote:** false confirmations would silently
  contaminate the canon ledger. Better to be honest about uncertainty.

### Case 5 — Dodged (rejected, never promoted)
Oda explicitly refuses to confirm or stays vague.
- **Detection:** dodge phrase within ~80 chars of the value match:
  "won't say", "secret for now", "you'll see", "wait and see",
  "is a secret", "hmm…", "stay tuned"
- **Tier:** REJECTED — fact is not added to the ledger at all
- **Why:** absence of evidence is not evidence; Oda dodging means
  there's no canon claim here. Field stays at 🟣 SPEC if it was
  already wiki-derived.
- **Example:** Q: "Who is Imu?" A: "Hmm… that's a secret for now."

### Confirmation language list (extend as we observe new patterns)
English: yes, yeah, yep, yup, correct, exactly, that's right, right,
indeed, precisely, good guess, good catch, nice catch, you got it.
Japanese: はい (hai), そう (sou), そうです (sou desu), 正解 (seikai),
当たり (atari).

### Dodge phrase list (extend as we observe new patterns)
"can't say", "won't say", "won't reveal", "not telling", "secret for
now", "that's a secret", "is a secret", "you'll see", "wait and see",
"please wait", "stay tuned", "hmm…".

---

## The five tiers (for any claim)

| Tier | Definition |
|---|---|
| 🟢 **Canon** | At least one Oda-direct source: SBS Q&A, manga panel reference, Vivre Card entry, Color Walk note, Oda interview |
| 🔵 **Highly likely** | Multiple secondary sources agree, no contradiction, plausibly derivable from canon (ages math, family relationships implied across panels) |
| 🟣 **Speculation** | One secondary source OR fan-derived; no Oda confirmation; consistent with canon but unverified |
| 🟠 **Rumour** | Reddit theory / fan analysis / databook trivia without Oda backing |
| 🔴 **Disproven** | Contradicted by a higher-tier source — kept on record so the same wrong claim can't re-surface unflagged |

---

## Source registry

The full, authoritative list of every source the Codex trusts is in
[`docs/canon-sources.md`](canon-sources.md). Every source has its own
schema entry: id, tier, coverage, access path, verification method,
citation format, and approval log.

**No claim can be tagged 🟢 canon unless it cites a source registered
there.** Adding a new source requires a PR amending the registry.

The summary hierarchy below is a quick reference; the registry is the
binding document.

## Source hierarchy (what carries which tier on its own)

| Source | Default tier of an unchallenged claim from it |
|---|---|
| Manga panel (Oda's pen) | 🟢 canon |
| SBS Q&A (Oda's words) | 🟢 canon |
| Vivre Card / Vivre Mark | 🟢 canon |
| Color Walk (Oda commentary) | 🟢 canon |
| One Piece Magazine SBS | 🟢 canon |
| Older databooks (Yellow/Red/Blue/Green/Grand) | 🔵 highly likely |
| Light novels (officially licensed) | 🔵 highly likely |
| Movie pamphlets / Stampede / Z / Red etc | 🔵 highly likely (movie-canon scope only) |
| Wiki Char Box infobox | 🟣 speculation **unless** confirmed by a higher source |
| Wiki trivia sections | 🟣 speculation |
| Reddit theories | 🟠 rumour |
| Fan analyses / YouTube videos | 🟠 rumour |
| Filler / anime-only episodes | not stored at all (excluded by design) |

When two sources of equal tier disagree, the claim is held at one tier
lower until the conflict is resolved.

---

## What goes where (data file ownership)

| File | Contains | Who can write |
|---|---|---|
| `appearances.csv` | Character × chapter × type | `scraper.py` only (manga-panel scrape) |
| `sbs_archive.json` | Oda Q&As | `sbs_scraper.py` + cleaning scripts |
| `theories_import.json` | Reddit theories with status & analysis | `theory_scraper.py`, `theory_analyzer.py`, `assign_theory_numbers.py` |
| `cover_stories.json` | Mini-arc metadata | `cover_stories_scraper.py` |
| `volume_covers.json` | Volume cover art URLs | `covers_scraper.py` |
| `punk_records.json` | Character claims (tiered, sourced) | `punk_records_scraper.py` (wiki ingest) + `verify.py` (Phase C: SBS cross-check) |
| `portraits.json` | Character portrait URLs | `portrait_scraper.py` |
| User-submitted theories | GitHub Issues → curated into `theories_import.json` | **You only**, via Issue review |

**Nothing modifies a character's claims except the named scraper for
that claim's source.** No theory analysis ever writes to Punk Records.
No user submission ever bypasses your review.

---

## What auto-linker can and cannot do

The auto-linker (introduced Phase A) operates at *bake time* on text
already in the data files. It walks rendered prose and adds `<a href>`
tags around recognised terms (character names, SBS Vol N references).

**The auto-linker:**
- ✅ Adds navigation links to existing text
- ✅ Uses tier-appropriate CSS classes so the visual grammar reflects
     the source's trust level
- ❌ Cannot create or modify any data record
- ❌ Cannot promote a claim's tier
- ❌ Cannot accept user input

A link from a reader's question to a character profile **is navigation
only**, not endorsement of the surrounding sentence.

---

## What requires manual review

These actions never happen automatically. They always require a human
(currently you) reviewing in GitHub:

1. Adding a new theory to `theories_import.json` from a user submission
2. Promoting a claim from 🟣/🟠 → 🟢 canon (Phase C will propose
   promotions; you approve them)
3. Resolving a 🔴 disproven flag (Phase E will surface conflicts; you
   adjudicate)
4. Adding a new source type to the hierarchy above
5. Modifying this policy document itself

---

## What gets removed

- ❌ Filler-arc characters / events (anime-only)
- ❌ Non-canon movie content tagged as such (most early movies)
- ❌ Theories that contradict resolved canon (auto-flagged Phase C, you
  review and either mark disproven or remove)
- ❌ Spam / abuse / off-topic submissions (rejected at GitHub Issue stage)

---

## Decisions log

| Date | Decision |
|---|---|
| 2026-04-26 | Canon Engine roadmap adopted. Five-tier system defined. Wiki demoted to "speculation unless confirmed." |
| 2026-04-26 | Violet chosen for speculation tier (gold/yellow too close to canon-gold). |
| 2026-04-26 | User submissions stay routed via GitHub Issues. No backend / DB / auth. |
