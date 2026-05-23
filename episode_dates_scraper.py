"""Generate per-episode air date estimates from anime season boundaries.

Source: Wikipedia "List of One Piece episodes" — season start/end dates.
These are EXACT for each season's first and last episode.
Within-season episodes are linearly distributed (typically 7-day weekly cadence,
with occasional 14-day intervals during anime breaks averaged out).

Output: episode_dates.json
"""
import json
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")

# Wikipedia season table — exact start/end Japanese broadcast dates per season
# (season_number, first_ep, last_ep, "YYYY-MM-DD" start, "YYYY-MM-DD" end)
SEASONS = [
    (1,  1,    61,   "1999-10-20", "2001-03-07"),
    (2,  62,   77,   "2001-03-21", "2001-08-19"),
    (3,  78,   92,   "2001-08-26", "2001-12-09"),
    (4,  93,   130,  "2001-12-16", "2002-10-27"),
    (5,  131,  143,  "2002-11-03", "2003-02-02"),
    (6,  144,  195,  "2003-02-09", "2004-06-13"),
    (7,  196,  228,  "2004-06-20", "2005-03-27"),
    (8,  229,  263,  "2005-04-17", "2006-04-30"),
    (9,  264,  336,  "2006-05-21", "2007-12-23"),
    (10, 337,  381,  "2008-01-06", "2008-12-14"),
    (11, 382,  407,  "2008-12-21", "2009-06-28"),
    (12, 408,  421,  "2009-07-05", "2009-10-11"),
    (13, 422,  456,  "2009-10-18", "2010-06-20"),
    (14, 457,  516,  "2010-06-27", "2011-09-25"),
    (15, 517,  578,  "2011-10-02", "2012-12-23"),
    (16, 579,  628,  "2013-01-06", "2014-01-12"),
    (17, 629,  746,  "2014-01-19", "2016-06-19"),
    (18, 747,  782,  "2016-06-26", "2017-04-02"),
    (19, 783,  891,  "2017-04-09", "2019-06-30"),
    (20, 892,  1088, "2019-07-07", "2023-12-17"),
    (21, 1089, 1155, "2024-01-07", "2025-12-28"),
    # Season 22 (Elbaph) — started 2026-04-05; 4 episodes aired so far (1156-1159)
    # End date will keep moving as more episodes air; updated each Standard Training pass.
    (22, 1156, 1159, "2026-04-05", "2026-04-26"),
]


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def fmt_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def main() -> None:
    episodes: dict[str, dict] = {}

    for (season, first, last, start, end) in SEASONS:
        sd = parse_date(start)
        ed = parse_date(end)
        n = last - first + 1
        if n == 1:
            episodes[str(first)] = {"date": fmt_date(sd), "season": season, "approximate": False}
            continue
        span = (ed - sd).days
        for i, ep in enumerate(range(first, last + 1)):
            if i == 0:
                d = sd
            elif i == n - 1:
                d = ed
            else:
                d = sd + timedelta(days=round(span * i / (n - 1)))
            exact = (i == 0 or i == n - 1)
            episodes[str(ep)] = {
                "date": fmt_date(d),
                "season": season,
                "approximate": not exact,
            }

    out = {
        "_doc": (
            "Per-episode air date estimates. Season boundaries (seasons[].start_date "
            "and end_date) are EXACT — first/last episode of each season are anchored "
            "to those dates. Within-season episodes are linearly distributed and "
            "flagged approximate=true. Season 1 episode 1 = 1999-10-20 (TX broadcast). "
            "Anime took a long break between Season 21 (end 2025-12-28) and Season 22 "
            "(start 2026-04-05) which is reflected as a gap in the timeline."
        ),
        "generated_on": datetime.now().strftime("%Y-%m-%d"),
        "anchor_episode1": "1999-10-20",
        "max_episode": SEASONS[-1][2],
        "seasons": [
            {"season": s, "first_ep": f, "last_ep": l, "start_date": st, "end_date": en}
            for (s, f, l, st, en) in SEASONS
        ],
        "episodes": episodes,
    }

    with open("episode_dates.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    n_exact = sum(1 for v in episodes.values() if not v["approximate"])
    print(f"episode_dates.json: {len(episodes)} episodes · {n_exact} exact · {len(SEASONS)} season anchors")
    print(f"Date range: {episodes['1']['date']} → {episodes[str(SEASONS[-1][2])]['date']}")


if __name__ == "__main__":
    main()
