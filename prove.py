"""
Prove — Phase D of the Canon Engine. Free path (no AI).

Generalised proving engine. Takes a claim (structured or free-text)
and returns a structured verdict with all supporting and contradicting
evidence found across registered canon sources.

Usage as a CLI:
  py prove.py "Roronoa Zoro's birthday is November 11"
  py prove.py --subject "Roronoa Zoro" --field birthday --value "November 11"
  py prove.py --json '{"subject":"Nami","predicate":"blood_type","value":"X"}'

Usage as a library:
  from prove import prove
  result = prove({"subject": "Nami", "predicate": "blood_type", "value": "X"})
  # → {"verdict": "confirmed",
  #    "supporting": [...],
  #    "contradicting": [],
  #    "context": [...],
  #    "tier_recommendation": "canon"}

Verdict values:
  confirmed     — at least one CANON-tier source supports, none contradict
  likely        — only LIKELY-tier sources support, none contradict
  contradicted  — at least one source explicitly contradicts (negation
                  near value, or different value for same subject+predicate)
  unknown       — no qualifying evidence either way
"""
import os, sys, json, re
from collections import defaultdict
from datetime import date

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DIR        = os.path.dirname(__file__)
PUNK_PATH  = os.path.join(DIR, "punk_records.json")
SBS_PATH   = os.path.join(DIR, "sbs_archive.json")
FACTS_PATH = os.path.join(DIR, "canon_facts.json")

sys.path.insert(0, DIR)
try:
    from bake import NAME_ALIASES   # type: ignore
except Exception:
    NAME_ALIASES = {}

try:
    # Reuse all the verifier's pattern matching — single source of truth
    from verify import (
        name_pattern, normalised_candidates, proximity_match,
        digit_proximity_match, detect_dodge_near, detect_negation_near,
        detect_jocular, detect_confirmation,
        SENTENCE_PROXIMITY, PARAGRAPH_PROXIMITY,
    )
except Exception as e:
    print(f"  ✗ failed to import verify.py helpers: {e}")
    sys.exit(1)


# ── DATA LOADERS (cached at module level) ───────────────────────
_facts = None
_sbs   = None
_punk  = None
def _load_facts():
    global _facts
    if _facts is None:
        if os.path.exists(FACTS_PATH):
            _facts = json.load(open(FACTS_PATH, encoding="utf-8"))
        else:
            _facts = []
    return _facts
def _load_sbs():
    global _sbs
    if _sbs is None:
        if os.path.exists(SBS_PATH):
            _sbs = json.load(open(SBS_PATH, encoding="utf-8"))
        else:
            _sbs = []
    return _sbs
def _load_punk():
    global _punk
    if _punk is None:
        if os.path.exists(PUNK_PATH):
            _punk = json.load(open(PUNK_PATH, encoding="utf-8"))
        else:
            _punk = {}
    return _punk


# ── FREE-TEXT PARSER ────────────────────────────────────────────
# Lightweight extractor that turns "Roronoa Zoro's birthday is November 11"
# into {subject: "Roronoa Zoro", predicate: "birthday", value: "November 11"}
# Conservative: returns None if it can't confidently identify all three.

PREDICATE_KEYWORDS = {
    "birthday":          ["birthday", "born on", "date of birth"],
    "age":               ["age", "years old", "is years"],
    "height":            ["height", "tall", "cm"],
    "weight":            ["weight", "weighs", "kg"],
    "blood_type":        ["blood type", "blood is"],
    "bounty":            ["bounty", "wanted"],
    "devil_fruit_name":  ["devil fruit", "ate the", "fruit user"],
    "epithet":           ["epithet", "known as", "called"],
    "occupation":        ["occupation", "job is", "is a "],
    "origin":            ["origin", "from ", "born in"],
    "first_appearance":  ["first appears", "debut", "introduced in"],
}


def parse_claim(text):
    """Best-effort parse of free-text claim into {subject, predicate, value}."""
    text = text.strip()
    if not text: return None

    # Find subject — try every known character name (longest first)
    pr = _load_punk()
    candidates = sorted(
        [n for n in pr.keys()] +
        [a for n, aliases in NAME_ALIASES.items() for a in aliases],
        key=len, reverse=True
    )
    subject = None
    for c in candidates:
        if len(c) < 3: continue
        if re.search(rf"\b{re.escape(c)}\b", text, re.IGNORECASE):
            # Map alias back to canonical
            for canon, aliases in NAME_ALIASES.items():
                if c.lower() == canon.lower() or c.lower() in [a.lower() for a in aliases]:
                    subject = canon; break
            if not subject: subject = c
            break
    if not subject: return None

    # Find predicate
    text_lc = text.lower()
    predicate = None
    for pred, keywords in PREDICATE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lc:
                predicate = pred; break
        if predicate: break
    if not predicate: return None

    # Value is everything after the predicate keyword (heuristic)
    # For numbers / dates, grab the relevant pattern
    value = None
    if predicate in ("age", "weight"):
        m = re.search(r"\d+(?:\.\d+)?", text)
        if m: value = m.group(0)
    elif predicate == "birthday":
        m = re.search(r"(January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?",
                      text, re.IGNORECASE)
        if m: value = m.group(0)
    elif predicate == "height":
        m = re.search(r"\d+\s*(?:cm|m|ft|')", text, re.IGNORECASE)
        if m: value = m.group(0)
    elif predicate == "blood_type":
        m = re.search(r"\b([ABOXSF]+(?:\s*\(?(?:RH[+-])?\)?))?\b", text)
        if m and m.group(0): value = m.group(0).strip()
    elif predicate == "bounty":
        m = re.search(r"[\d,]+(?:\.\d+)?\s*(?:billion|million|berries?|berr?y|฿)?",
                      text, re.IGNORECASE)
        if m: value = m.group(0).strip()
    if value is None:
        # Fallback: grab the chunk after the first predicate keyword
        for kw in PREDICATE_KEYWORDS[predicate]:
            idx = text_lc.find(kw)
            if idx >= 0:
                tail = text[idx + len(kw):].strip(" :=is\"'")
                # Take the first substantial phrase
                tail = re.split(r"[.!?,;]", tail)[0].strip()
                if tail: value = tail; break
    if not value: return None

    return {"subject": subject, "predicate": predicate, "value": value}


# ── PROVING CORE ────────────────────────────────────────────────
def prove(claim, deep=True):
    """Prove a claim against canon sources.

    `claim` may be a dict {subject, predicate, value} or a string
    (in which case parse_claim is invoked first).

    Returns:
      {
        "claim":      <the structured claim>,
        "verdict":    "confirmed" | "likely" | "contradicted" | "unknown",
        "supporting": [...evidence dicts...],
        "contradicting": [...evidence dicts...],
        "context":    [...evidence dicts...],
        "tier_recommendation": "canon" | "likely" | "speculation" | "rumour",
        "evidence_count": N,
      }
    """
    if isinstance(claim, str):
        parsed = parse_claim(claim)
        if not parsed:
            return {
                "claim": {"raw": claim},
                "verdict": "unparseable",
                "supporting": [], "contradicting": [], "context": [],
                "tier_recommendation": "speculation",
                "evidence_count": 0,
                "note": "Couldn't extract subject + predicate + value from text. "
                        "Pass a structured {subject, predicate, value} instead.",
            }
        claim = parsed

    subject = claim.get("subject", "")
    predicate = claim.get("predicate", "")
    value = str(claim.get("value", "")).strip()

    supporting = []
    contradicting = []
    context = []

    # ── Step 1: Existing canon_facts for this subject + predicate ──
    facts = _load_facts()
    relevant_facts = [f for f in facts if f.get("subject") == subject
                                       and f.get("predicate") == predicate]
    for f in relevant_facts:
        # Match value (verbatim or normalised)
        f_value = str(f.get("value", "")).strip()
        if f_value == value or value in normalised_candidates(f_value) or \
           f_value in normalised_candidates(value):
            supporting.append({
                "source_type": "canon_facts",
                "tier":  f.get("tier"),
                "intent": f.get("intent", "serious"),
                "value": f_value,
                "citations": f.get("sources", []),
                "evidence_notes": f.get("evidence_notes", ""),
            })
        else:
            # Same predicate, different value → potential contradiction
            contradicting.append({
                "source_type": "canon_facts",
                "tier":  f.get("tier"),
                "intent": f.get("intent", "serious"),
                "value": f_value,
                "citations": f.get("sources", []),
                "evidence_notes": f.get("evidence_notes", ""),
                "conflict_type": "different_value",
            })

    # ── Step 2 (optional, deeper): scan SBS for additional mentions ──
    if deep and subject and value:
        pat = name_pattern(subject, NAME_ALIASES.get(subject, ()))
        if pat:
            for entry in _load_sbs():
                question = entry.get("question") or ""
                answer   = entry.get("answer") or ""
                text = question + " ║ " + answer
                # Quick filter: character name must appear
                if not pat.search(text): continue

                # Verbatim + sentence proximity = strong support
                m = proximity_match(text, value, pat, SENTENCE_PROXIMITY)
                if m and not detect_dodge_near(text, m["value_pos"], m["value_end"]):
                    if detect_negation_near(text, m["value_pos"], m["value_end"]):
                        contradicting.append({
                            "source_type": "sbs",
                            "volume":   entry.get("volume"),
                            "qa_id":    entry.get("id_num"),
                            "snippet":  m["snippet"],
                            "conflict_type": "negation_near_value",
                        })
                    else:
                        intent = "jocular" if detect_jocular(answer) else \
                                 ("confirmation" if detect_confirmation(question, answer, value, pat) else "serious")
                        supporting.append({
                            "source_type": "sbs",
                            "volume":   entry.get("volume"),
                            "qa_id":    entry.get("id_num"),
                            "snippet":  m["snippet"],
                            "intent":   intent,
                            "match_type": "verbatim_sentence",
                        })
                    continue
                # Confirmation pattern
                if detect_confirmation(question, answer, value, pat):
                    supporting.append({
                        "source_type": "sbs",
                        "volume":   entry.get("volume"),
                        "qa_id":    entry.get("id_num"),
                        "snippet":  (answer or "")[:200],
                        "intent":   "confirmation",
                        "match_type": "reader_proposed",
                    })
                    continue
                # Paragraph-proximity = context
                m = proximity_match(text, value, pat, PARAGRAPH_PROXIMITY)
                if m and not detect_dodge_near(text, m["value_pos"], m["value_end"]):
                    context.append({
                        "source_type": "sbs",
                        "volume":   entry.get("volume"),
                        "qa_id":    entry.get("id_num"),
                        "snippet":  m["snippet"],
                        "match_type": "paragraph_proximity",
                    })

    # Cap context to keep responses tight
    context = context[:8]

    # ── Step 3: Compute verdict + tier recommendation ──
    canon_support = [s for s in supporting if s.get("tier") == "canon"
                                            or s.get("match_type") == "verbatim_sentence"
                                            or s.get("match_type") == "reader_proposed"]
    likely_support = [s for s in supporting if s.get("tier") == "likely"]
    canon_contra = [c for c in contradicting if c.get("tier") == "canon"
                                              or c.get("conflict_type") == "negation_near_value"]

    if canon_contra:
        verdict = "contradicted"
        tier_rec = "disproven"
    elif canon_support:
        verdict = "confirmed"
        tier_rec = "canon"
    elif likely_support or supporting:
        verdict = "likely"
        tier_rec = "likely"
    elif context:
        verdict = "unknown"
        tier_rec = "speculation"
    else:
        verdict = "unknown"
        tier_rec = "speculation"

    return {
        "claim": claim,
        "verdict": verdict,
        "supporting":     supporting,
        "contradicting":  contradicting,
        "context":        context,
        "tier_recommendation": tier_rec,
        "evidence_count": len(supporting) + len(contradicting) + len(context),
    }


# ── CLI ─────────────────────────────────────────────────────────
def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    claim = None
    if "--json" in args:
        i = args.index("--json")
        claim = json.loads(args[i + 1])
    elif "--subject" in args:
        get = lambda flag: args[args.index(flag) + 1] if flag in args else None
        claim = {
            "subject":   get("--subject"),
            "predicate": get("--field"),
            "value":     get("--value"),
        }
    else:
        # Free text — concatenate remaining args
        claim = " ".join(a for a in args if not a.startswith("--"))

    result = prove(claim)
    print("=" * 60)
    print("  PROVE — Canon Engine claim verification")
    print("=" * 60)
    print(f"  Claim   : {result['claim']}")
    print(f"  Verdict : {result['verdict'].upper()}")
    print(f"  Tier rec: {result['tier_recommendation']}")
    print()
    print(f"  Supporting evidence: {len(result['supporting'])}")
    for s in result["supporting"][:5]:
        srcname = s.get("source_type")
        if srcname == "sbs":
            print(f"    + SBS Vol {s.get('volume')} #{str(s.get('qa_id') or '?').zfill(4)}: "
                  f"{s.get('snippet','')[:80]}…")
        else:
            print(f"    + {srcname}: tier={s.get('tier')} value={s.get('value')}")
    print()
    if result["contradicting"]:
        print(f"  CONTRADICTING evidence: {len(result['contradicting'])}")
        for c in result["contradicting"][:5]:
            print(f"    - {c.get('source_type')}: {c.get('conflict_type', 'see snippet')}")
            if c.get("snippet"): print(f"      \"{c['snippet'][:80]}…\"")
            if c.get("value"):   print(f"      alt value: {c['value']}")
    print()
    if result["context"]:
        print(f"  Context (related mentions): {len(result['context'])}")
    print("=" * 60)


if __name__ == "__main__":
    _cli()
