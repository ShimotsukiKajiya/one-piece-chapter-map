"""
SBS Categorizer
Adds a `category` field to every Q&A in sbs_archive.json using Claude Haiku.

Categories: character, devil-fruit, worldbuilding, bounties, author-personal,
            cover-stories, jokes, food-trivia, design-process, other

Run:
  py sbs_categorizer.py              # categorize all uncategorized
  py sbs_categorizer.py --recategorize  # redo all
  py sbs_categorizer.py --limit 20   # test first 20
"""

import anthropic
import json
import os
import sys
import time

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL    = "claude-haiku-4-5"
DELAY    = 0.3
BATCH    = 20   # Q&As per API call (saves cost vs one-at-a-time)

DIR        = os.path.dirname(__file__)
INPUT_FILE = os.path.join(DIR, "sbs_archive.json")

VALID_CATS = {
    "character", "devil-fruit", "worldbuilding", "bounties",
    "author-personal", "cover-stories", "jokes", "food-trivia",
    "design-process", "other",
}

SYSTEM_PROMPT = """You categorize One Piece SBS Q&A entries into one of these categories:

- character: about specific characters' lives, ages, relationships, backstories, or trivia
- devil-fruit: about devil fruit mechanics, specific fruits, or awakenings
- worldbuilding: about world geography, races, history, organizations, lore
- bounties: about bounty amounts, mechanics, or rankings
- author-personal: Oda's personal life, opinions, hobbies, work routine, or self-deprecating jokes
- cover-stories: about cover story arcs (Buggy's adventures, CP9, Enel on the moon, etc.)
- jokes: pure comedy / absurd Q&As with no actual content
- food-trivia: anything about food, cooking, what characters eat
- design-process: how Oda designed characters, ships, animals, or visual elements
- other: doesn't fit any above

You will receive a JSON array of Q&A objects each with `id` (you assign 0..N) and `q` and `a` text. Return ONLY a JSON array of objects with `id` and `category`. No prose, no markdown."""


def categorize_batch(client, batch):
    payload = json.dumps([
        {"id": i, "q": qa["question"][:300], "a": qa["answer"][:400]}
        for i, qa in enumerate(batch)
    ], ensure_ascii=False)

    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": payload}],
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"): raw = raw[4:]
        raw = raw.strip()

    results = json.loads(raw)
    out = {}
    for item in results:
        cat = item.get("category", "other")
        if cat not in VALID_CATS: cat = "other"
        out[item["id"]] = cat
    return out


def main():
    if not API_KEY:
        print("  ✗ ANTHROPIC_API_KEY not set"); sys.exit(1)

    if not os.path.exists(INPUT_FILE):
        print("  ✗ sbs_archive.json not found"); sys.exit(1)

    recat = "--recategorize" in sys.argv
    limit = None
    for i, arg in enumerate(sys.argv):
        if arg == "--limit" and i + 1 < len(sys.argv):
            try: limit = int(sys.argv[i+1])
            except: pass

    with open(INPUT_FILE, encoding="utf-8") as f:
        archive = json.load(f)

    todo_idx = [i for i, qa in enumerate(archive) if recat or "category" not in qa]
    if limit: todo_idx = todo_idx[:limit]

    print("=" * 55)
    print(f"  SBS Categorizer  ({MODEL})")
    print(f"  To categorize: {len(todo_idx)} of {len(archive)}")
    print("=" * 55); print()

    client = anthropic.Anthropic(api_key=API_KEY)
    done = errors = 0

    for batch_start in range(0, len(todo_idx), BATCH):
        idx_batch = todo_idx[batch_start:batch_start + BATCH]
        batch = [archive[i] for i in idx_batch]

        print(f"  Batch {batch_start//BATCH + 1}: {len(batch)} entries…", end=" ", flush=True)

        try:
            results = categorize_batch(client, batch)
            for local_i, archive_i in enumerate(idx_batch):
                cat = results.get(local_i, "other")
                archive[archive_i]["category"] = cat
            done += len(batch)
            print("OK")
        except Exception as e:
            errors += 1
            print(f"ERROR: {str(e)[:80]}")

        # Save progress after each batch
        with open(INPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(archive, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY)

    print()
    print(f"  ✓ Categorized: {done}    Errors: {errors}")

    # Stats
    from collections import Counter
    counts = Counter(qa.get("category", "?") for qa in archive)
    print()
    print("  Category breakdown:")
    for cat, n in counts.most_common():
        print(f"    {cat:18} {n}")
    print("=" * 55)


if __name__ == "__main__":
    main()
