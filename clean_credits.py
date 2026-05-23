"""
Strip translator credits / interlang links from SBS answer texts.
Saves the credit text into a separate `credits` field per entry so
the UI can render it as a small attribution bubble between cards.

Run:
  py clean_credits.py --dry
  py clean_credits.py
"""
import json, os, re, sys, shutil

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR     = os.path.dirname(__file__)
ARCHIVE = os.path.join(DIR, "sbs_archive.json")
BACKUP  = os.path.join(DIR, "sbs_archive.precredits.json")

# Translator credit blocks usually start at "Translated by" and run to end
CREDIT_RE  = re.compile(r'\s*Translated by[\s\S]*$', re.IGNORECASE)
# First-occurrence interlanguage prefix anywhere in tail — strip from there to end.
# Lang codes: fr/es/it/tr/ca/pt/de/ru/en/nl/pl/ja/zh
INTERLANG_RE = re.compile(r'\s+(?:fr|es|it|tr|ca|pt|de|ru|en|nl|pl|ja|zh):[A-Za-zЀ-ӿ].*$', re.IGNORECASE)
# Trailing "SBS Volume NN" / "SBS Vol NN" label
SBS_LABEL_RE = re.compile(r'\s+SBS Vol(?:ume)?\s*\d+\s*$', re.IGNORECASE)
# [https://url name] markdown-ish wiki link → keep just `name`
WIKILINK_RE  = re.compile(r'\[https?://\S+\s+([^\]]+)\]')


def cleanup_answer(text):
    """Returns (cleaned_text, credits_text_or_none)."""
    credits = None
    # 1) Extract translator credits FIRST (before interlang strip removes context)
    m = CREDIT_RE.search(text)
    if m:
        credits_raw = m.group(0).strip()
        # Strip wiki url syntax to readable names
        credits = WIKILINK_RE.sub(r'\1', credits_raw)
        # Also strip interlang from the credits text itself
        credits = INTERLANG_RE.sub('', credits).strip()
        text = CREDIT_RE.sub('', text)
    # 2) Strip interlang links from main text (everything after first `<sp>lang:`)
    text = INTERLANG_RE.sub('', text)
    # 3) Strip trailing "SBS Volume NN" label
    text = SBS_LABEL_RE.sub('', text)
    return text.rstrip(), credits


def main():
    dry = "--dry" in sys.argv

    with open(ARCHIVE, encoding="utf-8") as f:
        archive = json.load(f)

    if not dry and not os.path.exists(BACKUP):
        shutil.copy2(ARCHIVE, BACKUP)
        print(f"  ✓ Backup → {BACKUP}")

    print("=" * 55)
    print(f"  Credit Cleaner — {'DRY' if dry else 'APPLY'}")
    print("=" * 55); print()

    changed = 0
    samples = []
    for qa in archive:
        old = qa.get("answer", "")
        new_answer, credits = cleanup_answer(old)
        if new_answer != old or credits:
            changed += 1
            if dry and len(samples) < 3:
                samples.append((qa['volume'], old[-200:], new_answer[-100:], credits))
            qa["answer"] = new_answer
            if credits:
                qa["credits"] = credits

    for vol, before, after, credits in samples:
        print(f"\nVol {vol}:")
        print(f"  BEFORE: ...{before!r}")
        print(f"  AFTER : ...{after!r}")
        print(f"  CREDITS: {credits!r}")

    print()
    print(f"  Cleaned {changed} entries")

    if not dry:
        with open(ARCHIVE, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)
        print(f"  ✓ Wrote → {ARCHIVE}")
    else:
        print("  (dry-run)")
    print("=" * 55)


if __name__ == "__main__":
    main()
