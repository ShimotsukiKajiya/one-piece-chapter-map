"""
SBS Images Scraper — POSITIONAL ATTRIBUTION (replaces fuzzy matching)

For each SBS volume page on the wiki, this:
  1. Fetches (or reads cached) wikitext
  2. Tokenizes into a flat sequence of structural events:
       HEADER (==Chapter==), D_OPEN, O_OPEN, FILE, TABLE_OPEN/CLOSE
  3. Walks tokens with a state machine, attributing each File: reference
     to whichever D-block or O-block opened most recently
  4. Emits a list of Q&A pairs in document order with their image filenames
  5. Matches the Nth parsed pair to the Nth archive entry (same source =
     same order). Falls back to fingerprint-anchored alignment on count
     mismatch.
  6. Updates the `images` field of each archive entry with [{path, side}]
     objects pointing to the existing local cache (NEVER re-downloads files
     that are already present)

Run:
  py sbs_images_scraper.py --dry-run         # report what would change, no writes
  py sbs_images_scraper.py --inspect 10      # print parsed pairs of vol 10
  py sbs_images_scraper.py --inspect 10 5    # just pair #5 of vol 10
  py sbs_images_scraper.py --diff            # compare new vs current attribution
  py sbs_images_scraper.py                   # apply for real
"""

import requests, json, os, re, sys, time, shutil
from difflib import SequenceMatcher

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

# ── PATHS ────────────────────────────────────────────────────────
DIR        = os.path.dirname(__file__)
ARCHIVE    = os.path.join(DIR, "sbs_archive.json")
BACKUP     = os.path.join(DIR, "sbs_archive.backup.json")
IMG_ROOT   = os.path.join(DIR, "logo", "sbs-images")
WIKI_API   = "https://onepiece.fandom.com/api.php"
USER_AGENT = "OnePieceTheoryTracker/1.0 (fan project)"
DELAY      = 0.6
THUMB_W    = 600
WIKITEXT_CACHE = os.path.join(DIR, "cache", "wikitext")

# ── REGEX ────────────────────────────────────────────────────────
# Combined token regex. Order matters — most specific first.
TOKEN_RE = re.compile(
    r"(?P<HEADER>==+\s*Chapter[^=\n]+==+)"
    r"|(?P<D_OPEN>(?:'''[﻿\s]*D[\s'’]*:|(?<=\n)D:)\s*)"
    r"|(?P<O_OPEN>(?:'''[﻿\s]*O[\s'’]*:|(?<=\n)O:)\s*)"
    r"|(?P<TABLE_OPEN>\{\|)"
    r"|(?P<TABLE_CLOSE>\|\})"
    r"|(?P<FILE>\[\[\s*(?:File|Image):\s*(?P<FNAME>[^\]\|]+?)\s*(?:\|[^\]]*)?\]\])",
    re.IGNORECASE
)

# Files to skip — pure decoration / chapter chrome
SKIP_FILE_RE = re.compile(
    r"^(?:"
    r"SBS[ _]Vol[ _]\d+[ _]header"        # SBS Vol 60 header.png
    r"|SBS\d+[ _]Header[ _]?\d*"          # SBS60 Header 1.png
    r"|SBS[ _]Vol[ _]\d+[ _]Chap[ _]\d+[ _]header"
    r"|Volume[ _]\d+[ _]header"
    r")",
    re.IGNORECASE
)


# ── CACHE / FETCH ────────────────────────────────────────────────
def load_or_fetch_wikitext(vol):
    """Fetch a volume's wikitext, caching to disk. Returns None on failure."""
    os.makedirs(WIKITEXT_CACHE, exist_ok=True)
    cache_path = os.path.join(WIKITEXT_CACHE, f"vol-{vol}.txt")

    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100:
        with open(cache_path, encoding="utf-8") as f:
            return f.read()

    params = {"action":"parse","page":f"SBS_Volume_{vol}",
              "prop":"wikitext","format":"json"}
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=20)
        if r.status_code != 200: return None
        wt = r.json().get("parse",{}).get("wikitext",{}).get("*")
        if wt:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(wt)
        return wt
    except Exception:
        return None


# ── TOKENIZER + ATTRIBUTOR ───────────────────────────────────────
def attribute_pairs(wikitext):
    """Walk the tokenized wikitext and emit a list of Q&A pairs in order.
    Each pair: { 'q_text': str, 'a_text': str, 'q_files': [str], 'a_files': [str] }
    Implements the positional attribution algorithm."""
    if not wikitext:
        return []

    # Tokenize
    tokens = []
    for m in TOKEN_RE.finditer(wikitext):
        kind = m.lastgroup
        payload = m.group("FNAME") if kind == "FILE" else m.group(0)
        tokens.append((kind, m.start(), m.end(), payload))

    pairs = []
    state         = None          # None | 'Q' | 'A'
    in_table      = 0             # depth (handles nested tables)
    last_was_header = False
    cur_q_files, cur_a_files = [], []
    cur_q_start, cur_a_start = None, None
    # Files that appear AFTER an O but BEFORE the next D belong to the
    # UPCOMING question (often a thumbnail/portrait of the Q's subject)
    pending_q_files = []

    def flush():
        if cur_q_start is None and cur_a_start is None:
            return
        # Build text slices
        q_end = cur_a_start if cur_a_start is not None else len(wikitext)
        q_text = wikitext[cur_q_start:q_end] if cur_q_start is not None else ""
        a_end = next_d_pos[0] if next_d_pos else len(wikitext)
        a_text = wikitext[cur_a_start:a_end] if cur_a_start is not None else ""
        q_clean = clean_text(q_text)
        a_clean = clean_text(a_text)
        # Apply same min-length filter as original scraper to suppress spurious
        # D/O markers (quoted text in answers, false matches in tables, etc.)
        if len(q_clean) < 5 or len(a_clean) < 5:
            return
        pairs.append({
            "q_text":  q_clean,
            "a_text":  a_clean,
            "q_files": list(cur_q_files),
            "a_files": list(cur_a_files),
        })

    # We need to know the "next D" position when emitting, so do a two-pass
    # approach: collect token list with indices, then walk.
    next_d_pos = [None]   # mutable cell

    i = 0
    while i < len(tokens):
        kind, start, end, payload = tokens[i]

        if kind == "HEADER":
            # Headers don't end a pair on their own; they just mark that
            # the next image (if any) is a chapter header decoration.
            last_was_header = True

        elif kind == "D_OPEN":
            # Close the prior pair if we have one in flight
            if cur_q_start is not None or cur_a_start is not None:
                # Find next D position for slicing answer end
                next_d_pos[0] = start
                flush()
            # Start a new Q — pending files (between previous A and this D)
            # belong here on the Q-side
            state = "Q"
            cur_q_files = list(pending_q_files)
            cur_a_files = []
            pending_q_files = []
            cur_q_start = end
            cur_a_start = None
            last_was_header = False

        elif kind == "O_OPEN":
            state = "A"
            cur_a_start = end

        elif kind == "TABLE_OPEN":
            in_table += 1

        elif kind == "TABLE_CLOSE":
            in_table = max(0, in_table - 1)

        elif kind == "FILE":
            fname = payload.strip()
            # Skip headers/chrome
            if SKIP_FILE_RE.match(fname):
                last_was_header = False
                i += 1
                continue

            if state == "Q":
                # Inside a question block — reader-submitted artwork
                cur_q_files.append(fname)
            elif state == "A":
                # If we're inside a wikitext table, the image is part of
                # Oda's tabular answer — never defer.
                if in_table > 0:
                    cur_a_files.append(fname)
                else:
                    # Outside any table — check if file appears in the gap
                    # between answer prose and the next D (= preamble for
                    # upcoming Q, often a portrait of its subject).
                    next_significant = None
                    for j in range(i + 1, len(tokens)):
                        nk = tokens[j][0]
                        if nk in ("D_OPEN", "O_OPEN", "HEADER"):
                            next_significant = nk
                            break
                    if next_significant == "D_OPEN":
                        pending_q_files.append(fname)
                    else:
                        cur_a_files.append(fname)
            elif state is None:
                # Orphan image before any D — could be a decorative header
                # right after a chapter divider, or pre-amble for upcoming Q.
                # If a D follows soon, defer to that Q.
                next_significant = None
                for j in range(i + 1, len(tokens)):
                    nk = tokens[j][0]
                    if nk in ("D_OPEN", "O_OPEN", "HEADER"):
                        next_significant = nk
                        break
                if next_significant == "D_OPEN" and not last_was_header:
                    pending_q_files.append(fname)
                # else skip (decoration)
            last_was_header = False

        i += 1

    # Final flush
    if cur_q_start is not None or cur_a_start is not None:
        next_d_pos[0] = len(wikitext)
        flush()

    return pairs


# ── TEXT HELPERS ─────────────────────────────────────────────────
def clean_text(text):
    if not text: return ""
    text = re.sub(r'\[\[(?:File|Image):[^\]]+(?:\|[^\]]+)*\]\]', '', text)
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\{\{[^}]+\}\}', '', text)
    text = text.replace("'''","").replace("''","")
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fingerprint(s, n=80):
    return re.sub(r'\s+', ' ', (s or '').lower())[:n]


def safe_name(s):
    return re.sub(r'[^\w.\-]', '_', s)[:120]


# ── ARCHIVE I/O ──────────────────────────────────────────────────
def load_archive():
    with open(ARCHIVE, encoding="utf-8") as f:
        return json.load(f)


def save_archive_atomic(archive):
    tmp = ARCHIVE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)
    # Atomic rename
    os.replace(tmp, ARCHIVE)


def ensure_backup():
    if not os.path.exists(BACKUP):
        shutil.copy2(ARCHIVE, BACKUP)
        print(f"  ✓ Created backup → {BACKUP}")


# ── ALIGNMENT ────────────────────────────────────────────────────
def align(pairs, entries):
    """Return list of (entry, pair_or_None) and a diagnostic string.
    Index-based when counts match; fingerprint-anchored otherwise."""
    if len(pairs) == len(entries):
        return list(zip(entries, pairs)), "ok-equal-count"

    # Counts diverge — try greedy fingerprint-anchored alignment
    out = []
    j = 0
    for entry in entries:
        target = fingerprint(entry["question"])
        # Look for a pair matching this entry's question within a small window
        best_j, best_score = None, 0
        window = pairs[j:j + 5] if j < len(pairs) else []
        for k, p in enumerate(window):
            score = SequenceMatcher(None, target, fingerprint(p["q_text"])).ratio()
            if score > best_score:
                best_score, best_j = score, j + k
        if best_j is not None and best_score > 0.7:
            out.append((entry, pairs[best_j]))
            j = best_j + 1
        else:
            out.append((entry, None))
    return out, f"mismatch-{len(pairs)}vs{len(entries)}"


# ── PATH RESOLUTION ──────────────────────────────────────────────
def resolve_local_path(vol, fname):
    """Map a wiki File: filename to its existing cached path. Returns the
    relative web path if file exists, None otherwise. Never downloads."""
    rel  = f"logo/sbs-images/vol-{vol}/{safe_name(fname)}"
    abs_ = os.path.join(DIR, rel.replace("/", os.sep))
    if os.path.exists(abs_) and os.path.getsize(abs_) > 200:
        return rel
    return None


# ── REPORTING ────────────────────────────────────────────────────
def inspect_volume(vol, archive, only_idx=None):
    """Print parsed Q&A pairs of a volume with attributed images."""
    by_vol = {}
    for e in archive: by_vol.setdefault(e["volume"], []).append(e)
    entries = by_vol.get(vol, [])

    wikitext = load_or_fetch_wikitext(vol)
    if not wikitext:
        print(f"  Vol {vol}: no wikitext"); return
    pairs = attribute_pairs(wikitext)
    aligned, diag = align(pairs, entries)

    print(f"Vol {vol}: parsed {len(pairs)} pairs, archive has {len(entries)} entries — {diag}")
    print()

    for idx, (entry, pair) in enumerate(aligned, 1):
        if only_idx is not None and idx != only_idx: continue
        print(f"  [{idx:2d}] Archive Q: {entry['question'][:90]}")
        if pair:
            qf = pair["q_files"] or []
            af = pair["a_files"] or []
            for f in qf:
                local = resolve_local_path(vol, f)
                tag = '[Q-side]' + (' (CACHE MISS)' if not local else '')
                print(f"        {f}  {tag}")
            for f in af:
                local = resolve_local_path(vol, f)
                tag = '[A-side]' + (' (CACHE MISS)' if not local else '')
                print(f"        {f}  {tag}")
            if not qf and not af:
                print(f"        (no images)")
        else:
            print(f"        (no parser match — kept existing)")


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry      = "--dry-run" in args
    diff     = "--diff" in args
    inspect_idx = None
    inspect_vol = None
    if "--inspect" in args:
        i = args.index("--inspect")
        try: inspect_vol = int(args[i + 1])
        except: pass
        try: inspect_idx = int(args[i + 2])
        except: pass

    archive = load_archive()

    # Inspect mode
    if inspect_vol is not None:
        inspect_volume(inspect_vol, archive, inspect_idx)
        return

    by_vol = {}
    for e in archive: by_vol.setdefault(e["volume"], []).append(e)
    vols = sorted(by_vol.keys())

    print("=" * 60)
    print("  SBS Image Attribution — POSITIONAL")
    print(f"  Mode: {'DRY-RUN' if dry else ('DIFF' if diff else 'APPLY')}")
    print(f"  Archive: {len(archive)} entries across {len(vols)} volumes")
    print(f"  Image cache: {IMG_ROOT}")
    print("=" * 60)
    print()

    if not dry and not diff:
        ensure_backup()

    # Stats
    total_pairs_match    = 0   # volumes where parsed count == archive count
    total_pairs_mismatch = 0
    total_attributed     = 0   # entries that gained images
    total_unchanged      = 0
    total_added          = 0
    total_removed        = 0
    total_changed        = 0
    cache_misses         = []

    for vol in vols:
        entries = by_vol[vol]
        wikitext = load_or_fetch_wikitext(vol)
        if not wikitext:
            print(f"  Vol {vol:3d}: no wikitext, skipping")
            continue

        pairs = attribute_pairs(wikitext)
        aligned, diag = align(pairs, entries)

        if diag == "ok-equal-count":
            total_pairs_match += 1
        else:
            total_pairs_mismatch += 1

        v_added = v_removed = v_changed = v_unchanged = v_attrib = 0

        for entry, pair in aligned:
            old_imgs = entry.get("images", [])
            # Normalise old (could be list of strings OR list of {path,side})
            old_paths = set()
            for x in old_imgs:
                if isinstance(x, str): old_paths.add(x)
                elif isinstance(x, dict): old_paths.add(x.get("path",""))

            new_imgs = []
            if pair:
                for f in pair["q_files"]:
                    local = resolve_local_path(vol, f)
                    if local: new_imgs.append({"path": local, "side": "q"})
                    else: cache_misses.append((vol, f))
                for f in pair["a_files"]:
                    local = resolve_local_path(vol, f)
                    if local: new_imgs.append({"path": local, "side": "a"})
                    else: cache_misses.append((vol, f))

            new_paths = {x["path"] for x in new_imgs}
            if new_paths == old_paths:
                v_unchanged += 1
            else:
                added   = new_paths - old_paths
                removed = old_paths - new_paths
                v_added   += len(added)
                v_removed += len(removed)
                if added or removed:
                    v_changed += 1

            if new_imgs:
                v_attrib += 1
                if not dry:
                    entry["images"] = new_imgs
            else:
                # Only clear if we have a confident parser match (pair exists)
                # Otherwise leave existing images alone
                if pair and not dry:
                    entry.pop("images", None)

        total_attributed += v_attrib
        total_added      += v_added
        total_removed    += v_removed
        total_changed    += v_changed
        total_unchanged  += v_unchanged

        flag = "✓" if diag == "ok-equal-count" else "⚠"
        print(f"  Vol {vol:3d}  {flag} pairs:{len(pairs):2d} arch:{len(entries):2d}  "
              f"images:{v_attrib:2d}  Δ {v_changed} (+{v_added}/-{v_removed})")

        # Persist progress every volume in apply mode
        if not dry and not diff:
            save_archive_atomic(archive)

    print()
    print("=" * 60)
    print(f"  Volumes with matching pair counts:  {total_pairs_match}/{len(vols)}")
    print(f"  Volumes with count mismatch:        {total_pairs_mismatch}")
    print(f"  Entries with images attributed:     {total_attributed}/{len(archive)}")
    print(f"  Total path changes:  +{total_added} new  -{total_removed} removed")
    print(f"  Cache misses (referenced but not on disk): {len(cache_misses)}")
    if cache_misses[:5]:
        print(f"    Sample: {cache_misses[:5]}")
    print()
    if dry:
        print("  (dry-run — nothing written)")
    else:
        print(f"  ✓ Wrote → {ARCHIVE}")
        print(f"    Backup at → {BACKUP}")
    print("=" * 60)


if __name__ == "__main__":
    main()
