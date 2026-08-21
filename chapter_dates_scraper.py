"""Generate chapter publication date estimates from volume tankōbon dates.

Source data:
  - Volume tankōbon release dates from Wikipedia (List of One Piece chapters)
    These are EXACT (Japanese release dates).
  - Anchor: Chapter 1 was first published in Weekly Shonen Jump on 1997-07-22.

Method:
  - For each volume, the last chapter is anchored to the volume release date.
  - Earlier chapters in that volume are back-interpolated weekly (7 days apart),
    minus the volume's printing lead-time. We use a simpler model: assume each
    chapter is 7 days before the next one, walking back from chapter N to N-1.
  - This gives ±1 week accuracy per chapter, which is ideal for a release-map
    visualisation. Volume markers will be exact (drawn from this same data).

Output: chapter_dates.json
  {
    "_doc": "...",
    "anchor_chapter1": "1997-07-22",
    "generated_on": "...",
    "volumes": [{"volume": 1, "release_date": "...", "first_ch": 1, "last_ch": 8}, ...],
    "chapters": {"1": {"date": "1997-07-22", "approximate": false}, ...}
  }
"""
import json
import os
import sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8")

# Volume table — sourced from Wikipedia (en) "List of One Piece chapters"
# Format: (volume_number, "YYYY-MM-DD" tankōbon release, first_chapter, last_chapter)
VOLUMES = [
    (1, "1997-12-24", 1, 8), (2, "1998-04-03", 9, 17), (3, "1998-06-04", 18, 26),
    (4, "1998-08-04", 27, 35), (5, "1998-10-02", 36, 44), (6, "1998-12-03", 45, 53),
    (7, "1999-03-04", 54, 62), (8, "1999-04-30", 63, 71), (9, "1999-07-02", 72, 81),
    (10, "1999-10-04", 82, 90), (11, "1999-12-02", 91, 99), (12, "2000-02-02", 100, 108),
    (13, "2000-04-28", 109, 117), (14, "2000-07-04", 118, 126), (15, "2000-09-04", 127, 136),
    (16, "2000-12-04", 137, 145), (17, "2001-02-02", 146, 155), (18, "2001-04-04", 156, 166),
    (19, "2001-07-04", 167, 176), (20, "2001-09-04", 177, 186),
    (21, "2001-12-04", 187, 195), (22, "2002-02-04", 196, 205), (23, "2002-04-04", 206, 216),
    (24, "2002-07-04", 217, 226), (25, "2002-09-04", 227, 236), (26, "2002-12-04", 237, 246),
    (27, "2003-02-04", 247, 255), (28, "2003-05-01", 256, 264), (29, "2003-07-04", 265, 275),
    (30, "2003-10-03", 276, 285), (31, "2003-12-19", 286, 295), (32, "2004-03-04", 296, 305),
    (33, "2004-06-04", 306, 316), (34, "2004-08-04", 317, 327), (35, "2004-11-04", 328, 337),
    (36, "2005-02-04", 338, 346), (37, "2005-04-28", 347, 357), (38, "2005-07-04", 358, 367),
    (39, "2005-11-04", 368, 377), (40, "2005-12-26", 378, 388),
    (41, "2006-04-04", 389, 399), (42, "2006-07-04", 400, 409), (43, "2006-09-04", 410, 419),
    (44, "2006-12-04", 420, 430), (45, "2007-03-02", 431, 440), (46, "2007-07-04", 441, 449),
    (47, "2007-09-04", 450, 459), (48, "2007-12-04", 460, 470), (49, "2008-03-04", 471, 481),
    (50, "2008-06-04", 482, 491), (51, "2008-09-04", 492, 502), (52, "2008-12-04", 503, 512),
    (53, "2009-03-04", 513, 522), (54, "2009-06-04", 523, 532), (55, "2009-09-04", 533, 541),
    (56, "2009-12-04", 542, 551), (57, "2010-03-04", 552, 562), (58, "2010-06-04", 563, 573),
    (59, "2010-08-04", 574, 584), (60, "2010-11-04", 585, 594),
    (61, "2011-02-04", 595, 603), (62, "2011-05-02", 604, 614), (63, "2011-08-04", 615, 626),
    (64, "2011-11-04", 627, 636), (65, "2012-02-03", 637, 646), (66, "2012-05-02", 647, 656),
    (67, "2012-08-03", 657, 667), (68, "2012-11-02", 668, 678), (69, "2013-03-04", 679, 690),
    (70, "2013-06-04", 691, 700), (71, "2013-08-02", 701, 711), (72, "2013-11-01", 712, 721),
    (73, "2014-03-04", 722, 731), (74, "2014-06-04", 732, 742), (75, "2014-09-04", 743, 752),
    (76, "2014-12-27", 753, 763), (77, "2015-04-03", 764, 775), (78, "2015-07-03", 776, 785),
    (79, "2015-10-03", 786, 795), (80, "2015-12-28", 796, 806),
    (81, "2016-04-04", 807, 816), (82, "2016-07-04", 817, 827), (83, "2016-11-04", 828, 838),
    (84, "2017-02-03", 839, 848), (85, "2017-05-02", 849, 858), (86, "2017-08-04", 859, 869),
    (87, "2017-11-02", 870, 879), (88, "2018-03-02", 880, 889), (89, "2018-06-04", 890, 900),
    (90, "2018-09-04", 901, 910), (91, "2018-12-04", 911, 921), (92, "2019-03-04", 922, 931),
    (93, "2019-07-04", 932, 942), (94, "2019-10-04", 943, 953), (95, "2019-12-28", 954, 964),
    (96, "2020-04-03", 965, 974), (97, "2020-09-16", 975, 984), (98, "2021-02-04", 985, 994),
    (99, "2021-06-04", 995, 1004), (100, "2021-09-03", 1005, 1015),
    (101, "2021-12-03", 1016, 1025), (102, "2022-04-04", 1026, 1035), (103, "2022-08-04", 1036, 1046),
    (104, "2022-11-04", 1047, 1055), (105, "2023-03-03", 1056, 1065), (106, "2023-07-04", 1066, 1076),
    (107, "2023-11-02", 1077, 1088), (108, "2024-03-04", 1089, 1100), (109, "2024-07-04", 1101, 1110),
    (110, "2024-11-01", 1111, 1121), (111, "2025-03-04", 1122, 1133), (112, "2025-07-04", 1134, 1144),
    (113, "2025-11-04", 1145, 1155), (114, "2026-03-04", 1156, 1166),
]

# Anchor: chapter 1 was first published in Weekly Shonen Jump on this date
ANCHOR_CH1_DATE = "1997-07-22"

# Known WSJ issue dates for chapters published past the latest tankobon.
# Japanese issue dates (Manga Plus publishes the day before, on the Sunday).
# Oda's 2026 cadence is roughly three chapters then a break week, so a flat
# weekly walk drifts badly here; these pins keep the frontier honest. Add a
# row whenever a new chapter lands and the estimate can be replaced by fact.
FRONTIER_DATES = {
    1170: "2026-01-05", 1171: "2026-01-19", 1172: "2026-02-02",
    1173: "2026-02-09", 1174: "2026-02-16", 1175: "2026-03-02",
    1176: "2026-03-09", 1177: "2026-03-23", 1178: "2026-03-30",
    1179: "2026-04-06", 1180: "2026-04-20", 1181: "2026-04-27",
    1182: "2026-05-11", 1183: "2026-05-25", 1184: "2026-06-01",
    1185: "2026-06-15", 1186: "2026-06-29", 1187: "2026-07-06",
    1188: "2026-07-13", 1189: "2026-07-27", 1190: "2026-08-10",
    1191: "2026-08-24",
}

# Average days between chapters across 2026 (36 chapters, 12 author breaks and
# 4 magazine holidays across the year). Used only past the newest pin.
FRONTIER_CADENCE_DAYS = 10

# Last known chapter (post latest tankōbon, in WSJ but not yet collected).
# This is a FLOOR — main() raises it to the max chapter in appearances.csv
# (the chapter scraper's ground truth) so this file stays current without
# hand-bumping every week.
LATEST_CHAPTER = 1181


def _latest_scraped_chapter() -> int:
    """Max chapter present in appearances.csv, or the LATEST_CHAPTER floor."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "appearances.csv")
    best = LATEST_CHAPTER
    try:
        with open(path, encoding="utf-8") as f:
            next(f, None)  # header
            for line in f:
                ch = line.split(",", 1)[0]
                if ch.isdigit() and int(ch) > best:
                    best = int(ch)
    except OSError:
        pass
    return best


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def fmt_date(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def main() -> None:
    global LATEST_CHAPTER
    LATEST_CHAPTER = _latest_scraped_chapter()
    chapters: dict[str, dict] = {}

    anchor_ch1 = parse_date(ANCHOR_CH1_DATE)

    # 1. Forward-interpolate from chapter 1 using 7-day cadence
    # This gives an initial estimate; volume anchors will refine end-of-volume
    # estimates and we re-distribute within each volume so the LAST chapter of
    # the volume is roughly 6 weeks before the tankōbon release date (typical
    # collection lead-time is ~5-6 weeks in Japan).
    LEAD_DAYS = 42  # tankōbon released ~6 weeks after the last chapter's WSJ issue

    # Build per-chapter date by walking volumes
    last_ch_done = 0
    last_date_done = None  # WSJ date for last_ch_done

    for (vol, rel, first, last) in VOLUMES:
        rel_d = parse_date(rel)
        # Estimated WSJ date for the LAST chapter of this volume
        last_wsj = rel_d - timedelta(days=LEAD_DAYS)

        # Date for the FIRST chapter of this volume:
        #   - If we have a previous chapter date, the first chapter is 7 days after
        #   - Otherwise (volume 1), use the anchor for chapter 1
        if last_ch_done == 0:
            # Volume 1 — first chapter is the WSJ anchor
            first_wsj = anchor_ch1
        else:
            first_wsj = last_date_done + timedelta(days=7)

        n_chapters = last - first + 1
        if n_chapters == 1:
            # Single chapter volume (rare)
            chapters[str(first)] = {"date": fmt_date(last_wsj), "volume": vol, "approximate": True}
        else:
            # Distribute evenly between first_wsj and last_wsj
            total_span = (last_wsj - first_wsj).days
            for i, ch in enumerate(range(first, last + 1)):
                if i == 0:
                    d = first_wsj
                elif i == n_chapters - 1:
                    d = last_wsj
                else:
                    # Linear distribution
                    d = first_wsj + timedelta(days=round(total_span * i / (n_chapters - 1)))
                # Chapter 1 is exact (anchor); volume-end chapters are anchored too
                exact = (ch == 1) or (ch == last)
                chapters[str(ch)] = {
                    "date": fmt_date(d),
                    "volume": vol,
                    "approximate": not exact,
                }

        last_ch_done = last
        last_date_done = last_wsj

    # 2. Chapters past the last tankobon.
    #
    # Anything in FRONTIER_DATES is a real WSJ issue date and is written exact.
    # Everything else is bounded by whatever real anchors sit either side of it,
    # so break weeks get absorbed instead of accumulating as drift.
    if last_ch_done < LATEST_CHAPTER and last_date_done is not None:
        pins = {ch: parse_date(v) for ch, v in FRONTIER_DATES.items()
                if last_ch_done < ch <= LATEST_CHAPTER}

        # Walk each run of unpinned chapters between two known points.
        anchor_ch, anchor_d = last_ch_done, last_date_done
        for ch in range(last_ch_done + 1, LATEST_CHAPTER + 1):
            if ch in pins:
                span_ch = ch - anchor_ch
                span_days = (pins[ch] - anchor_d).days
                gap_chs = list(range(anchor_ch + 1, ch))
                if span_days <= 0:
                    # The previous anchor is not credible (a flat 6-week tankobon
                    # lead badly underestimates break-heavy volumes). Trust the
                    # pin and walk backwards from it at the observed cadence.
                    for j, gap_ch in enumerate(reversed(gap_chs), start=1):
                        d = pins[ch] - timedelta(days=FRONTIER_CADENCE_DAYS * j)
                        chapters[str(gap_ch)] = {
                            "date": fmt_date(d), "volume": None, "approximate": True,
                        }
                else:
                    # Spread the run across the real elapsed time between anchors
                    for i, gap_ch in enumerate(gap_chs, start=1):
                        d = anchor_d + timedelta(days=round(span_days * i / span_ch))
                        chapters[str(gap_ch)] = {
                            "date": fmt_date(d), "volume": None, "approximate": True,
                        }
                chapters[str(ch)] = {
                    "date": fmt_date(pins[ch]), "volume": None, "approximate": False,
                }
                anchor_ch, anchor_d = ch, pins[ch]

        # Past the newest anchor there is nothing left to interpolate against,
        # so step at the observed cadence rather than a flat week.
        for ch in range(anchor_ch + 1, LATEST_CHAPTER + 1):
            if str(ch) in chapters:
                continue
            d = anchor_d + timedelta(days=FRONTIER_CADENCE_DAYS * (ch - anchor_ch))
            chapters[str(ch)] = {"date": fmt_date(d), "volume": None, "approximate": True}

    # 3. Monotonicity sweep -- a reader scrolling the release map must never
    # see chapter N+1 dated before chapter N. Walk from the newest chapter back;
    # wherever the previous chapter is dated on or after this one, pull it back
    # to a plausible slot and stop calling it exact.
    HARD = {1} | set(FRONTIER_DATES)
    adjusted = 0
    for ch in range(LATEST_CHAPTER, 1, -1):
        cur, prev = chapters.get(str(ch)), chapters.get(str(ch - 1))
        if not cur or not prev:
            continue
        if parse_date(prev["date"]) < parse_date(cur["date"]):
            continue
        if (ch - 1) in HARD:
            # Two hard anchors disagree -- that is a data error worth shouting about
            print(f"  WARNING: pinned Ch.{ch - 1} ({prev['date']}) is not before "
                  f"Ch.{ch} ({cur['date']}) -- check FRONTIER_DATES")
            continue
        prev["date"] = fmt_date(parse_date(cur["date"]) - timedelta(days=7))
        prev["approximate"] = True
        adjusted += 1
    if adjusted:
        print(f"  Monotonicity sweep adjusted {adjusted} estimated chapter date(s)")

    out = {
        "_doc": (
            "Per-chapter publication date estimates. "
            "Volume release dates (volumes[].release_date) are EXACT — sourced from "
            "Wikipedia 'List of One Piece chapters'. Per-chapter dates are interpolated "
            "weekly between volume anchors with a ~6-week tankōbon lead-time, so the "
            "LAST chapter of each volume is dated to its WSJ issue (also exact) and "
            "earlier chapters in the volume are linearly distributed back. "
            "Chapter 1's anchor is 1997-07-22 (WSJ Issue #34, 1997). "
            "Chapters past the latest tankōbon are pinned to real WSJ issue dates "
            "where FRONTIER_DATES knows them (approximate=false); chapters between "
            "two known anchors are spread across the real elapsed time so break "
            "weeks are absorbed rather than accumulated. Only chapters newer than "
            "the last pin are extrapolated, at the observed ~10-day 2026 cadence, "
            "and those may still drift by a week or so until a pin catches up."
        ),
        "generated_on": datetime.now().strftime("%Y-%m-%d"),
        "anchor_chapter1": ANCHOR_CH1_DATE,
        "tankobon_lead_days": LEAD_DAYS,
        "latest_chapter": LATEST_CHAPTER,
        "volumes": [
            {"volume": v, "release_date": r, "first_ch": fc, "last_ch": lc}
            for (v, r, fc, lc) in VOLUMES
        ],
        "chapters": chapters,
    }

    with open("chapter_dates.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    n_exact = sum(1 for v in chapters.values() if not v["approximate"])
    print(f"chapter_dates.json: {len(chapters)} chapters · {n_exact} exact · {len(VOLUMES)} volume anchors")
    print(f"Date range: {chapters['1']['date']} → {chapters[str(LATEST_CHAPTER)]['date']}")


if __name__ == "__main__":
    main()
