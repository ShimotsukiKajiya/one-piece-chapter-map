"""Extract theory citation edges from theories_import.json.

Produces relationships/_pending/cites.json — one row per theory/evidence pair.

Evidence sources:
  1. theory.chapter field  — comma/space-separated chapter numbers → ch:N
  2. theory.analysis.sbs_citations — tries to parse 'Vol N:' patterns → sbs:volNNN

Stance heuristic (from journey-outline.md):
  confirmed → supports
  partial   → supports
  debunked  → refutes
  active    → mentions
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PENDING_DIR = ROOT / "relationships" / "_pending"

STANCE_MAP = {
    "confirmed": "supports",
    "partial":   "supports",
    "debunked":  "refutes",
    "active":    "mentions",
}


def theory_id(num: int) -> str:
    return f"theory:{num:04d}"


def parse_chapters(raw: str) -> list[str]:
    """Extract chapter IDs from a comma/space-separated string."""
    ids = []
    for tok in re.split(r"[\s,;]+", raw.strip()):
        tok = tok.strip()
        if re.fullmatch(r"\d{1,4}", tok):
            ids.append(f"ch:{tok}")
    return ids


def parse_sbs_volumes(citations: list[str]) -> list[str]:
    """Try to extract 'Vol N' volume numbers from free-form citation strings."""
    ids = []
    for cite in citations:
        m = re.search(r"\bVol\.?\s*(\d+)\b", cite, re.IGNORECASE)
        if m:
            vol = int(m.group(1))
            ids.append(f"sbs:vol{vol:03d}")
    return ids


def main() -> None:
    src = ROOT / "theories_import.json"
    with open(src, encoding="utf-8") as f:
        raw = json.load(f)
    theories = raw if isinstance(raw, list) else raw.get("theories", [])

    rows: list[dict] = []
    seen: set[tuple] = set()   # dedup (from, to) pairs

    for t in theories:
        num = t.get("num")
        if num is None:
            continue
        status = t.get("status", "active")
        stance = STANCE_MAP.get(status, "mentions")
        tid = theory_id(num)

        # Chapter references
        for ch_id in parse_chapters(t.get("chapter") or ""):
            key = (tid, ch_id)
            if key not in seen:
                seen.add(key)
                rows.append({
                    "from":   tid,
                    "to":     ch_id,
                    "src":    "inferred",
                    "stance": stance,
                })

        # SBS citations are free-form text — we can't reliably extract valid
        # sbs:volNNN-qNNNN IDs without question numbers. Skip for now; a future
        # pass with structured SBS citation data would populate these.

    # Stats
    from_ch  = sum(1 for r in rows if r["to"].startswith("ch:"))
    from_sbs = sum(1 for r in rows if r["to"].startswith("sbs:"))
    by_stance = {}
    for r in rows:
        by_stance[r["stance"]] = by_stance.get(r["stance"], 0) + 1
    theories_covered = len({r["from"] for r in rows})

    print(f"  Rows:              {len(rows)}")
    print(f"  → chapter refs:    {from_ch}")
    print(f"  → SBS vol refs:    {from_sbs}")
    print(f"  Theories covered:  {theories_covered} / {len(theories)}")
    print(f"  Stance breakdown:  {by_stance}")

    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    out = PENDING_DIR / "cites.json"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  Written: {out}")


if __name__ == "__main__":
    main()
