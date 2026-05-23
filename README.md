# The Shimotsuki Codex

*Forging clarity from chaos.* A free, fan-built reference for One Piece —
1,181 chapters, 1,685 SBS Q&As, 1,546 characters, every theory weighed
against canon.

**[→ Open the Codex](https://shimotsukicodex.com/)**

Static site. No backend, no tracking, no ads. Loads from `file://` too.

---

## What's inside

| Surface | What it does |
|---|---|
| **Home** | Landing page + dynamic stats |
| **Chapter Atlas** | Every chapter as a colour grid; click any character to highlight all their appearances (`atlas.html`) |
| **SBS Vault** | All 1,685 Q&As across 107 volumes — searchable, categorised, with inline panels (`sbs.html`) |
| **Theory Forge** | Reddit theories analysed against canon via Claude + SBS (`theories.html`) |
| **Cover Compendium** | The 22 cover-story arcs Oda runs on chapter title pages (`covers.html`) |
| **Punk Records** | Character index + individual profiles with manga-canon section (`characters.html`, `character.html`) |
| **Workbench / Prove** | Build a theory with citations · run any claim through the canon engine (`workbench.html`, `prove.html`) |
| **Plus** | Crews, ships, locations, families, devil fruit codex, awakenings, haki, bounty wall, world map, voice cast, timeline, trivia trial, and ~30 more lore surfaces |

Full surface inventory in `docs/audit_report.md` after running `py audit.py`.

## Canon engine

Every fact carries a tier badge:

| Tier | Source standard |
|---|---|
| 🟢 CANON | Oda direct (manga, SBS verbatim with proximity, no negation) |
| 🔵 LIKELY | Wiki + SBS digit-group / normalised match within proximity |
| 🟣 SPECULATION | Wiki only, unverified |
| 🟠 RUMOUR | Reddit / fan / unsupported |
| 🔴 DISPROVEN | Contradicted by higher source |

See `docs/canon-policy.md` and `docs/canon-sources.md` for the full
source registry and the verifier's matching rules.

## How updates work

Local data refresh:

```
py refresh.py            # full pipeline
py refresh.py --quick    # incremental (skip slow scrapes)
py bake.py               # re-bake JSON into HTML pages
```

Cloud (GitHub Actions): weekly cron runs `refresh.py` every Sunday
at 06:00 UTC. Manual trigger via the Actions tab.

All scrapers are incremental and cached — first cold run ~30 min,
warm runs are seconds. Cache lives under `cache/` (gitignored).

## Contributing

Submissions via GitHub Issues (templates pre-filled with required fields):

- **Suggest a theory** — for Theory Forge inclusion (needs source citation)
- **SBS correction** — typos, mistranslations, missing Q&As
- **Submit a correction** — facts that conflict with canon

Reviewed weekly. Larger structural changes via PR welcome.

## Licence

- **Code** (HTML, CSS, JS, Python) — [MIT](LICENSE)
- **Curated content** (theory analyses, tier classifications, editorial
  notes, hand-built compilations, the SpoilerGuard system design and
  spoiler taxonomy) — [CC BY-NC 4.0](LICENSE-DATA.md)
- **One Piece itself** (characters, story, art, SBS text) —
  © Eiichiro Oda / Shueisha. This is a non-commercial fan project.
- **Wiki-derived data** — CC BY-SA 3.0 (Fandom community contributions).

**Names "Shimotsuki Codex" and "SpoilerGuard"** are reserved for use by
this project. Fork the code freely; please don't use these names for your
derivative without permission.

See [NOTICE.md](NOTICE.md) for the full IP map (what's mine, what's
Oda's, what you can do with what).

If you represent Shueisha or Toei and wish content removed, open an issue.
The project will respond in good faith.

## Follow

- X / Twitter: [@ShimotsukiCodex](https://x.com/ShimotsukiCodex)
- Bluesky: [@shimotsukicodex.bsky.social](https://bsky.app/profile/shimotsukicodex.bsky.social)
- Reddit: [u/ShimotsukiCodex](https://reddit.com/u/ShimotsukiCodex)

## Built with

Plain HTML/CSS/JS · Python 3 for the data pipeline · Claude (Anthropic)
for the SBS categoriser and theory analyser · the One Piece Fandom wiki
for raw character data · 28+ years of Oda's storytelling. Thanks also to
[Library of Ohara](https://thelibraryofohara.com/) (Artur) for SBS
translations and [Grand Line Review](https://www.youtube.com/@GrandLineReview)
(Liam) for canon-research inspiration.
