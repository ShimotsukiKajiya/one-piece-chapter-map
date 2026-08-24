# Canon Keeper brief — 2026-08-24

The standing role prompt is [`canon-keeper-prompt.md`](canon-keeper-prompt.md).
This is the **task brief for this batch**: paste the block below into a Keeper
chat that already has the standing prompt loaded, or after it if starting fresh.

Everything referenced is committed on `launch-clean`, not pushed. The Keeper
never edits — every item below wants a *judgement*, returned as a list the
Builder can encode.

---

```
A Builder session has finished a large audit pass on The Shimotsuki Codex and
left you decisions to make. Nothing in it has been promoted, merged, or
tier-changed — that is deliberate, and it is your call, not the Builder's.

Read these five files first (raw, from the launch-clean branch):
  docs/session-report-2026-08-24.md   what was done, and what is still open
  docs/curate-triage.md               189 claims, one recommendation each
  docs/data-integrity.md              duplicate/split records in punk_records
  docs/external_conflicts.md          150-character wiki cross-check
  docs/live-leak-findings.md          three leaks found by driving the site

Work the six blocks below IN ORDER. For each, return a decision list the
Builder can act on without re-deriving anything: the claim or record, your
verdict, and the chapter number where one is needed. Mark every chapter you
give with ✓ certain, ~ confident, or ? needs another look.

━━ BLOCK 1 · Chapter numbers the Builder could not derive (8 items) ━━
These gate real content on the World Government chart. Each is a best estimate
flagged ? in marines-wg.json _qa_flags. Confirm or correct:

  Crocodile        126  Warlord seat gated at his debut. When is the seat
                        actually stated on-panel? Fail-late wants the later.
  Marshall D. Teach 441 Warlord appointment, after delivering Ace.
  Buggy             594 Warlord appointment, post-timeskip.
  Gecko Moria       449 Deliberately his Thriller Bark debut, NOT the Ch. 233
                        summit — is he named a Warlord at 233 or not?
  Who's-Who        1020  CP9 past revealed in Wano, not his 977 debut.
  D. Rosinante      767  Debuts 761; his Marine rank lands a few chapters into
                        Law's flashback. Which chapter?
  Seven Warlords     69  The tier gate — Yosaku naming the system. The
                        leak-lexicon carries the same open question.
  Bomba (Marine)    711  Wiki says 652, appearances data says 711.

━━ BLOCK 2 · Two policy questions, not numbers ━━
  1. CLOU D. CLOVER. He is on the Will of D. page gated at Ch. 395 — but the
     D. in his name comes from the Vivre Card, not the manga. There is no
     chapter at which a reader "learns" it, and the page's whole contract is
     "carriers appear when the story reveals the D. in their name". Three
     options: keep 395, raise it, or rule that databook-only carriers do not
     belong on a chapter-gated page at all. Pick one and say why.
  2. THE PUBLIC API. api/v1/ is 16 MB of ungated JSON containing every late
     reveal. It is not linked from any page and not in sitemap.xml, but it is
     a complete bypass of the shield at guessable URLs. Is the API public and
     therefore spoiler-exempt by design? Either answer is fine; it needs to be
     written down.

━━ BLOCK 3 · Curate queue — 189 claims already triaged ━━
docs/curate-triage.md recommends confirm 148 / needs-eyes 8 / reject 33, each
with the evidence snippet from the full SBS answer. Work it in that document's
order. Two that are NOT ordinary promotion questions:

  MISS FRIDAY. The Codex stores her birthday as January 21st. SBS vol 90 q1232
  says, in Oda's own list, "Miss Friday: June 21". That is a stored value
  disagreeing with Oda, not a failed promotion. Adjudicate the VALUE.

  THE 5 NUMBER-PUN BIRTHDAYS (Sai, Baby 5, Chinjao, Boo — SBS vol 83 q1102).
  Oda answers as wordplay: "#Sai> August (8). 13 (Happo Navy, 13th Leader)".
  A machine should not call that confirmed. Read the puns and rule.

Also in that file: 30 NEW candidates in docs/curate_queue_positional.json,
read out of the two SBS answers laid out as positional tables that the
proximity matcher structurally cannot reach. 28 of the 30 reproduce the stored
value exactly and none conflicts, so these are tier promotions, not value
changes. Approve or reject as a block if you are satisfied with the alignment
evidence.

━━ BLOCK 4 · punk_records duplicates — approve the merges ━━
docs/data-integrity.md. Nothing has been merged. Three groups:
  8 split records   (Imu/Nerona Imu, three Rosward pairs, Gab, Mash, Nozdon,
                     Kashigami) — same name_jp, same first_appearance, disjoint
                     chapter sets. "Child of Kashigami" deserves a panel check
                     before folding; the rest look clean.
  3 alias shadows   (Akainu/Sakazuki, Aokiji/Kuzan, Kizaru/Borsalino) — each
                     shadow has exactly ONE appearance and all three are
                     Chapter 569, one Marineford chapter that used the epithet.
  1 duplicate + 1 casing collision (Lilith ×2; Wolf Unit / Wolf unit).

One thing to know before approving the Imu merge: it is safe ONLY because
field_reveals.json already holds the name ladder (906 → "Imu", 1086 → "Nerona
Imu"). Do not let anyone rename the record to "Imu" to make the chart read
right — that breaks the ladder and the chr:02569 links together.

Seven of the World Government chart's 17 remaining coverage gaps are these
duplicates. Merging lifts coverage from 91% to ~94% with no editorial work.

━━ BLOCK 5 · Entries that are wrong, not just undated ━━
  THREE-EYED TRIBE (races.json). Its member list reads:
    ["Nico Olvia (mother of Robin)", "Pudding (latent)",
     "Tot Musica narrator", "Goldenweek (?)"]
    - "Goldenweek (?)" puts a question mark in READER-FACING TEXT. That is the
      exact failure the whole audit exists to prevent; uncertainty belongs in
      _qa_flags.
    - "Tot Musica narrator" is a Film Red figure on a page carrying no tier
      marking. canon-policy scopes movie content to 🔵 at best.
    - Nico Olvia is not of the tribe.
    - gate_chapter is 202, but the `debut` field says Ch. 86 and the _qa_flags
      note describing the problem is stale.
    Rule on the member list and confirm the gate chapter.

  MANTRA (haki.json). Its Ch. 254 rung can never be reached, because
  haki.html is nav-gated at 597. The Builder recommends moving it to
  combat-styles.html, which is ungated and already holds regional styles from
  Ch. 3 to Ch. 1035. Approve or reject.

  FOUR CHARACTERS the Builder declined to place on the World Government chart,
  all needing your judgement rather than a number:
    Shanks       — wiki gives "Knights of God (former)" and "World Nobles
                   (Figarland Family) (former)". Very late, contested.
    Monkey D. Dragon — wiki gives "Marines (defected)". No datable on-panel
                   moment.
    Caesar Clown — "Marines (former)" is his MADS-era work under Vegapunk.
    Attach       — a reporter with a former Marine photography post.

━━ BLOCK 6 · The structural gap, if you have appetite ━━
The wiki cross-check found 465 promotable claims across a 150-character sample.
362 of them cite the VIVRE CARD. The Canon Engine only reads SBS text already
in the repo, so that entire body of Oda-direct evidence is unreachable by the
pipeline — it is the largest canon gap in the project, larger than any single
value in any report.

Question for you: is a Vivre Card ingest worth scoping? If yes, what is the
authoritative source you would trust for it, and what would its citation format
look like under docs/canon-policy.md?

━━ HOW TO RETURN IT ━━
One list per block. For each item: the identifier, your verdict, the chapter
with its ✓ / ~ / ? marker, and one line of reasoning. Where you are unsure, say
unsure — an honest ? costs the Builder nothing, and a wrong ✓ ships.
```

---

## Notes for the maintainer (not part of the paste block)

- The Keeper cannot see `launch-clean` unless it is pushed, or unless you paste
  the documents in. Everything above is committed locally only.
- Blocks 1 and 5 unblock reader-facing content. Blocks 3 and 4 unblock data
  quality. Block 6 is a scoping conversation, not a task.
- If you only have appetite for one: **Block 4**, because it is mechanical, it
  raises the World Government coverage rate for free, and it fixes the
  `prove.html` bake nondeterminism as a side effect.
