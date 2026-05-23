"""
Form Image Scraper v2 — for each character in character_forms.json,
crawl multiple wiki sources to find form-specific images:

  1. The character's own page                     (e.g. "Monkey D. Luffy")
  2. The character's Gallery sub-page             ("Monkey D. Luffy/Gallery")
  3. The character's associated Devil Fruit page  ("Hito Hito no Mi, Model: Nika")
  4. The Devil Fruit's Gallery sub-page

Then heuristic-match each form name to image filenames. Strict scorer
requires at least one form-specific token (e.g. "Boundman", "Sulong",
"Awakened") in the filename — the base infobox bonus only stacks on
top of a real token match.

Hand-curated overrides in `form_image_overrides.json` always win
(no scoring) — that file is for famous forms the scraper can't reliably
find via heuristic.

Run:
  py form_image_scraper.py            # full run
  py form_image_scraper.py --dry-run  # report matches, don't write
"""
import json, os, re, sys, time
import requests

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
FORMS_PATH      = os.path.join(DIR, "character_forms.json")
OVERRIDES_PATH  = os.path.join(DIR, "form_image_overrides.json")
PUNK_PATH       = os.path.join(DIR, "punk_records.json")
WIKI_API        = "https://onepiece.fandom.com/api.php"
USER_AGENT      = "OnePieceCodexFormScraper/2.0 (fan project)"
DELAY           = 0.4
CDN             = "https://static.wikia.nocookie.net/onepiece/images"

STOP = {"in", "the", "of", "a", "and", "true", "form", "model", "no", "mi", "with", "as"}

def tokens(s):
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return [t for t in s.split() if t and t not in STOP]


def fetch_page_images(title):
    """Return list of {title, url} for all images on a wiki page."""
    out = []
    cont = None
    for _ in range(8):
        params = {
            "action": "query", "prop": "images",
            "titles": title, "imlimit": "200",
            "format": "json", "formatversion": "2",
        }
        if cont: params["imcontinue"] = cont
        try:
            r = requests.get(WIKI_API, params=params,
                             headers={"User-Agent": USER_AGENT}, timeout=20)
            data = r.json()
        except Exception as e:
            print(f"    ✗ {title}: {e}")
            return out
        for page in data.get("query", {}).get("pages", []):
            for im in page.get("images", []):
                t = im.get("title", "")
                if t.startswith("File:") and t.lower().endswith((".png", ".jpg", ".jpeg")):
                    out.append(t[5:])  # strip "File:"
        cont = data.get("continue", {}).get("imcontinue")
        if not cont: break
        time.sleep(0.3)
    return out


def fetch_image_url(filename):
    """Get the actual CDN URL for a wiki image filename via imageinfo."""
    params = {
        "action": "query", "titles": "File:" + filename,
        "prop": "imageinfo", "iiprop": "url",
        "format": "json", "formatversion": "2",
    }
    try:
        r = requests.get(WIKI_API, params=params,
                         headers={"User-Agent": USER_AGENT}, timeout=15)
        data = r.json()
    except Exception:
        return None
    for page in data.get("query", {}).get("pages", []):
        for ii in page.get("imageinfo", []):
            return ii.get("url")
    return None


def score_match(form_name, filename):
    """Heuristic score. CRITICAL: returns 0 unless at least one form-specific
    token matches. Generic "infobox" bonuses only apply ON TOP of token matches."""
    fn = filename.lower().replace("_", " ")
    f_tokens = tokens(form_name)
    if not f_tokens: return 0
    token_score = 0
    for tok in f_tokens:
        if tok in fn:
            token_score += len(tok)
    if token_score == 0:
        return 0  # NO token match → never accept (avoids picking base infobox)
    score = token_score
    # Bonus signals (only stack on top of a real token match)
    if "anime" in fn:    score += 1
    if "infobox" in fn:  score += 3
    if "portrait" in fn: score += 2
    if "manga" in fn:    score -= 1
    if "concept" in fn:  score -= 2
    if "young" in fn or "child" in fn or "flashback" in fn:
        # only discount if the form_name doesn't reference age
        nm_low = form_name.lower()
        if not any(t in nm_low for t in ("child", "elder", "young", "age")):
            score -= 3
    return score


def crawl_sources(char_name, df_name=None):
    """Return a deduped list of image filenames from the character page,
    its Gallery, plus the Devil Fruit page + DF Gallery if known."""
    pages = [char_name, f"{char_name}/Gallery"]
    if df_name:
        pages.append(df_name)
        pages.append(f"{df_name}/Gallery")
    seen = set(); out = []
    for p in pages:
        try:
            ims = fetch_page_images(p)
        except Exception:
            continue
        for im in ims:
            if im not in seen:
                seen.add(im); out.append(im)
        time.sleep(0.25)
    return out


def main():
    args = sys.argv[1:]
    dry    = "--dry-run" in args
    force  = "--force" in args  # re-scrape even forms that already have images

    doc = json.load(open(FORMS_PATH, encoding="utf-8"))
    chars = doc.get("characters", {})
    total = sum(len(c.get("forms", [])) for c in chars.values())

    # Hand-curated overrides — applied first, never overwritten by scraper
    overrides = {}
    if os.path.exists(OVERRIDES_PATH):
        try:
            overrides = json.load(open(OVERRIDES_PATH, encoding="utf-8")).get("overrides", {})
        except Exception:
            pass

    # Devil Fruit lookup from punk_records (so we know which DF page to crawl)
    df_lookup = {}
    if os.path.exists(PUNK_PATH):
        try:
            pr = json.load(open(PUNK_PATH, encoding="utf-8"))
            for n, rec in pr.items():
                if isinstance(rec, dict):
                    df = rec.get("devil_fruit_name")
                    if df: df_lookup[n] = df
        except Exception:
            pass

    matched = 0; overridden = 0; skipped = 0
    print(f"  → {len(chars)} characters, {total} total forms · {len(overrides)} hand overrides · DF lookup: {len(df_lookup)}")

    for name, info in chars.items():
        forms = info.get("forms", [])
        if len(forms) < 2: continue

        # Apply hand overrides FIRST — they're authoritative
        char_overrides = overrides.get(name, {})
        for form in forms:
            if form["name"] in char_overrides:
                fn = char_overrides[form["name"]]
                # Sentinel: __NONE__ means "explicitly clear any auto-match"
                # — the form should fall back to base portrait + filter overlay.
                if fn == "__NONE__":
                    if form.get("image"):
                        del form["image"]
                        overridden += 1
                        print(f"  · {name} :: {form['name']:34s}  [override] cleared")
                    continue
                url = fetch_image_url(fn)
                if url and form.get("image") != url:
                    form["image"] = url
                    overridden += 1
                    print(f"  · {name} :: {form['name']:34s}  [override] ← {fn}")
                    time.sleep(0.2)

        # Skip the heuristic crawl if every non-default form already has an image
        # and we're not forcing a re-scrape.
        needs = [f for f in forms
                 if f.get("kind") != "default" and (force or not f.get("image"))]
        if not needs:
            continue

        print(f"  · {name}  (crawling, {len(needs)} forms need images)")
        try:
            page_images = crawl_sources(name, df_lookup.get(name))
        except Exception as e:
            print(f"    ✗ failed: {e}")
            continue
        if not page_images:
            print(f"    (no images found in any crawled source)")
            continue
        for form in needs:
            if form["name"] in char_overrides: continue
            best = None; best_score = 4
            for fn in page_images:
                s = score_match(form["name"], fn)
                if s > best_score:
                    best_score = s
                    best = fn
            if best:
                url = fetch_image_url(best)
                if url:
                    form["image"] = url
                    matched += 1
                    print(f"      ✓ {form['name']:38s} ← {best}")
                else:
                    skipped += 1
                time.sleep(0.2)
            else:
                skipped += 1

    print()
    print(f"  Heuristic matched: {matched}  ·  Hand-override applied: {overridden}  ·  Skipped: {skipped}")
    if not dry:
        with open(FORMS_PATH, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Wrote {FORMS_PATH}")
    else:
        print("  (dry run — JSON not written)")


if __name__ == "__main__":
    main()
