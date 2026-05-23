# What's New — Auto-build session

Built while you were AFK. All committed and pushed to GitHub.

## ✨ Big features

### 1. SBS Categorization
Every one of the 1,659 Q&As is now sorted into 10 buckets via Claude Haiku:

| Category | Count |
|---|---|
| 😄 Jokes | 544 |
| 👤 Characters | 406 |
| ✍ Oda Personal | 261 |
| 🎨 Design Process | 211 |
| 🗺 Worldbuilding | 123 |
| 🍎 Devil Fruits | 58 |
| 🍖 Food Trivia | 35 |
| 📖 Cover Stories | 7 |
| 💰 Bounties | 4 |
| Other | 10 |

Each Q&A shows a small category badge. Filter chips at the top let you see only one type — click "Devil Fruits" to see every fruit-related thing Oda's ever said.

**Cost:** ~$0.18 (well under your $5 budget)

### 2. Volume Cover Thumbnails
110 of 112 tankoubon covers scraped from the wiki and shown next to each volume header. Visual transformation — your eye latches onto covers immediately.

### 3. Silver-Bullet Matcher (the original goal!)
The theory analyzer now searches the SBS archive for canon evidence **before** calling Claude. When Oda has spoken on a topic, his actual quotes are passed to Claude as authoritative evidence, and the verdict cites them in a new "🎯 Oda spoke on this (SBS)" section on each theory card.

Re-ran all 94 theories with this new logic — much stronger verdicts now grounded in actual canon, not Reddit speculation.

### 4. Surprise Me + Stats + Favorites
- **🎲 Surprise me** button — random Q&A
- **📊 Most discussed** panel — top 12 characters with mention counts, click any to filter
- **❤ Favorite** heart on every Q&A — saved to localStorage, filter by favorites in the chips bar
- **Keyboard shortcuts** — `/` focus search, `r` random, `Esc` clear

## 🛠 New tools

| File | Purpose |
|---|---|
| `covers_scraper.py` | Pulls volume cover URLs via MediaWiki imageinfo API |
| `sbs_categorizer.py` | Batch-categorizes SBS via Claude Haiku (20 per call to save cost) |
| `bake.py` | Updated to handle covers + categories alongside SBS data |
| `theory_analyzer.py` | Now searches SBS archive first, passes hits to Claude |

## 📋 Workflow updates

When new SBS volumes drop:
```
py sbs_scraper.py --gaps      # fetch new volumes
py sbs_categorizer.py         # categorize new entries only
py covers_scraper.py          # add new covers
py bake.py                    # bake into HTML pages
git add -A && git commit -m "..." && git push
```

When new theories come in:
```
py theory_scraper.py          # pull from Reddit
py theory_analyzer.py         # silver-bullet analysis (uses SBS)
```

## 🐟 Pending — your turn

**Save the Oda PNG to `logo/oda-avatar.png`:**
1. https://onepiece.fandom.com/wiki/Eiichiro_Oda
2. Right-click his fish avatar (top-right portrait box) → Save image as
3. Save to `D:\One Piece\logo\oda-avatar.png`
4. Refresh sbs.html — empty cream circles fill in

Until you do, the page falls back to the SVG fish-mask doodle.

## 💰 API usage this session
- SBS categorization: ~$0.18
- Theory re-analysis (94 theories with SBS context): ~$0.10–0.15
- **Total: roughly $0.30**

You should still have ~$4.70 in credit.
