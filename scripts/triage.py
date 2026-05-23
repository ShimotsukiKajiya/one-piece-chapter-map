"""Interactive CLI for resolving bootstrap_unresolved.json entries.

When a Tier-1+ extractor can't match a source name to a known entity, it writes
a row to bootstrap_unresolved.json. This script walks those rows one by one and
lets the maintainer decide:

  [number]  Pick a fuzzy-matched suggestion from the entity index
  a         Enter an entity ID manually (alias-of:<id>)
  n         Create a new entity (new-entity)
  d         Discard this name (discard)
  s         Skip for now (leave undecided)
  q         Quit (save decisions made so far)

Decisions are written back to bootstrap_unresolved.json immediately so the
session can be interrupted and resumed safely.

Usage:
    python scripts/triage.py
    python scripts/triage.py --list          # show undecided entries, no prompts
    python scripts/triage.py --stats         # summary of decision progress
"""

import argparse
import json
import sys
import sys
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from datetime import date
from difflib import get_close_matches
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UNRESOLVED_PATH = ROOT / "bootstrap_unresolved.json"
INDEX_PATH = ROOT / "entity_index.json"
REGISTRY_PATH = ROOT / "entity_registry.json"

DECIDED_BY = "manual"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.write("\n")


def load_unresolved() -> list[dict]:
    if not UNRESOLVED_PATH.exists():
        return []
    data = load_json(UNRESOLVED_PATH)
    if isinstance(data, dict):
        return data.get("entries", [])
    return data if isinstance(data, list) else []


def save_unresolved(entries: list[dict]) -> None:
    save_json(UNRESOLVED_PATH, {"entries": entries})


def load_index() -> dict[str, str]:
    if not INDEX_PATH.exists():
        return {}
    return load_json(INDEX_PATH)


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        return {"next": {}}
    return load_json(REGISTRY_PATH)


def save_registry(registry: dict) -> None:
    save_json(REGISTRY_PATH, registry)


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------

def suggest(name: str, index: dict[str, str], n: int = 8) -> list[tuple[str, str]]:
    """Return up to n (alias, entity_id) suggestions for the given name."""
    query = name.lower().strip()
    all_aliases = list(index.keys())
    matches = get_close_matches(query, all_aliases, n=n, cutoff=0.5)
    # Also include prefix matches not caught by difflib
    prefix_matches = [a for a in all_aliases if a.startswith(query[:4])][:4]
    combined = dict.fromkeys(matches + prefix_matches)  # preserve order, dedup
    return [(alias, index[alias]) for alias in list(combined)[:n]]


# ---------------------------------------------------------------------------
# Decision recording
# ---------------------------------------------------------------------------

def record_decision(entry: dict, decision: str) -> None:
    entry["decision"] = decision
    entry["decided_by"] = DECIDED_BY
    entry["decided_on"] = date.today().isoformat()


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

DIVIDER = "─" * 60


def print_entry(entry: dict, idx: int, total: int) -> None:
    print(f"\n{DIVIDER}")
    print(f"  [{idx}/{total}]  {entry['name']!r}")
    print(f"  Source:  {entry.get('source', '?')}")
    if entry.get("context"):
        print(f"  Context: {entry['context']}")
    if entry.get("decision"):
        print(f"  (already decided: {entry['decision']})")


def print_suggestions(suggestions: list[tuple[str, str]]) -> None:
    if not suggestions:
        print("  No close matches found in entity index.")
        return
    print("\n  Suggestions:")
    for i, (alias, eid) in enumerate(suggestions, 1):
        print(f"    {i})  {alias!r}  ->  {eid}")


def print_help() -> None:
    print(
        "\n  Commands:\n"
        "    1-9   Pick suggestion by number\n"
        "    a     Enter an entity ID manually  (alias-of:<id>)\n"
        "    n     Mark as new entity            (new-entity)\n"
        "    d     Discard (not a real entity)   (discard)\n"
        "    s     Skip for now\n"
        "    ?     Show this help\n"
        "    q     Quit and save\n"
    )


# ---------------------------------------------------------------------------
# Main triage loop
# ---------------------------------------------------------------------------

def triage(entries: list[dict], index: dict[str, str]) -> int:
    undecided = [e for e in entries if not e.get("decision")]
    total = len(undecided)

    if total == 0:
        print("All entries are already decided. Nothing to triage.")
        return 0

    print(f"\n{total} undecided entries. Type ? for help.\n")
    decided_this_session = 0

    for idx, entry in enumerate(undecided, 1):
        suggestions = suggest(entry["name"], index)
        print_entry(entry, idx, total)
        print_suggestions(suggestions)

        while True:
            try:
                raw = input("\n  > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nInterrupted — saving progress.")
                return decided_this_session

            if not raw:
                continue

            cmd = raw.lower()

            if cmd == "?":
                print_help()
                continue

            if cmd == "q":
                print(f"\nSaving and quitting. Decided {decided_this_session} this session.")
                return decided_this_session

            if cmd == "s":
                print("  -> Skipped.")
                break

            if cmd == "n":
                record_decision(entry, "new-entity")
                print("  -> new-entity")
                decided_this_session += 1
                break

            if cmd == "d":
                record_decision(entry, "discard")
                print("  -> discard")
                decided_this_session += 1
                break

            if cmd == "a":
                try:
                    eid = input("  Entity ID (e.g. chr:00042): ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\nInterrupted.")
                    return decided_this_session
                if eid:
                    record_decision(entry, f"alias-of:{eid}")
                    print(f"  -> alias-of:{eid}")
                    decided_this_session += 1
                    break
                print("  (empty — try again)")
                continue

            # Numeric pick from suggestions
            if cmd.isdigit():
                n = int(cmd)
                if 1 <= n <= len(suggestions):
                    alias, eid = suggestions[n - 1]
                    record_decision(entry, f"alias-of:{eid}")
                    print(f"  -> alias-of:{eid}  (via {alias!r})")
                    decided_this_session += 1
                    break
                print(f"  Number out of range (1–{len(suggestions)}). Try again.")
                continue

            print(f"  Unknown command {raw!r}. Type ? for help.")

        # Save after every decision so interruption doesn't lose work
        save_unresolved(entries)

    print(f"\n{DIVIDER}")
    print(f"Session complete. Decided {decided_this_session} / {total} entries.")
    return decided_this_session


# ---------------------------------------------------------------------------
# --list and --stats modes
# ---------------------------------------------------------------------------

def cmd_list(entries: list[dict]) -> None:
    undecided = [e for e in entries if not e.get("decision")]
    print(f"Undecided entries: {len(undecided)} / {len(entries)} total\n")
    for e in undecided:
        print(f"  {e['name']!r}  ({e.get('source', '?')})")


def cmd_stats(entries: list[dict]) -> None:
    from collections import Counter
    decisions = Counter(
        e.get("decision", "<undecided>") for e in entries
    )
    total = len(entries)
    undecided = decisions.pop("<undecided>", 0)
    print(f"Total entries:  {total}")
    print(f"Undecided:      {undecided}")
    for decision, count in sorted(decisions.items()):
        print(f"  {decision}: {count}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List undecided entries")
    parser.add_argument("--stats", action="store_true", help="Show decision stats")
    args = parser.parse_args()

    entries = load_unresolved()

    if not entries:
        print("bootstrap_unresolved.json is empty or not found.")
        print("Extractors (Tier 1+) populate this file during extraction runs.")
        sys.exit(0)

    if args.list:
        cmd_list(entries)
        return

    if args.stats:
        cmd_stats(entries)
        return

    # Load index for fuzzy matching
    index = load_index()
    if not index:
        print(
            "Warning: entity_index.json not found or empty.\n"
            "Suggestions will be unavailable. Run build_entity_index.py first.\n",
            file=sys.stderr,
        )

    triage(entries, index)


if __name__ == "__main__":
    main()
