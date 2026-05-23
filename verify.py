"""
Verify v3 — Phase C of the Canon Engine. Free path (no AI).

For each wiki-derived claim in punk_records.json, scan sbs_archive.json
for confirmation. Recognises FOUR canon cases (per docs/canon-policy.md
"How Oda's style is interpreted"):

  1. SERIOUS direct statement     — Oda plainly states the value
  2. CONFIRMATION                 — Reader proposed value in Q,
                                    Oda agreed in A ("Yes!", "Correct!")
  3. JOCULAR                      — Oda's joke that's still on record
  4. (sarcasm) AMBIGUOUS          — needs human review (curate.html)

  Plus a critical 5th case:
  5. DODGED                       — Oda explicitly refused to confirm
                                    ("secret for now", "you'll see")
                                    -> NEVER auto-promoted

Each promoted fact carries TWO axes:
  tier   — how trustworthy (canon / likely / speculation / etc)
  intent — how to read it  (serious / confirmation / jocular / ambiguous)

Tier promotion rules:
  CANON  =  serious + verbatim + sentence-proximity + no negation
         OR confirmation pattern (Q proposes, A confirms)
         OR jocular + verbatim + proximity
  LIKELY =  serious + verbatim + paragraph-proximity (150 chars)
         OR normalised (digit groups / parenthetical-stripped) + proximity
         OR ambiguous (matches but cause unclear) — surfaces for curate.html
  REJECT =  dodged intent OR no proximity match at all

Run:
  py verify.py             # write canon_facts.json + report (free)
  py verify.py --dry-run   # report only
  py verify.py --strict    # only CANON promotions, no LIKELY
  py verify.py --top 50    # only top-N most-appearing characters
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
QUEUE_PATH = os.path.join(DIR, "docs", "promotions_pending.md")
QUEUE_JSON = os.path.join(DIR, "docs", "promotions_pending.json")
REPORT_PATH= os.path.join(DIR, "docs", "verification_report.md")
AMBIG_JSON = os.path.join(DIR, "docs", "curate_queue.json")  # for curate.html
DECISIONS_JSON = os.path.join(DIR, "docs", "curate_decisions.json")  # ledger of past decisions

VERIFIER          = "verify.py v3 (intent-aware)"
TODAY             = date.today().isoformat()
SENTENCE_PROXIMITY = 80    # chars — "same sentence" approximation
PARAGRAPH_PROXIMITY = 150  # chars — "same paragraph" approximation

sys.path.insert(0, DIR)
try:
    from bake import NAME_ALIASES   # type: ignore
except Exception:
    NAME_ALIASES = {}

# Fields we attempt to verify
VERIFIABLE_FIELDS = [
    "age", "birthday", "height", "weight", "blood_type",
    "bounty", "bounty_value", "devil_fruit_name",
    "epithet", "occupation", "origin",
]

# ── INTENT DETECTORS ─────────────────────────────────────────────
# Each returns True if the pattern is present in the text snippet.

# Words that, near the START of the answer, signal Oda agreeing with
# what the reader just proposed in the question.
CONFIRM_OPENERS = re.compile(
    r"^\s*(?:"
    r"yes(?:!|\.)?|yeah|yep|yup|"
    r"correct(?:!|\.)?|exactly(?:!|\.)?|"
    r"that['']s\s+right|right(?:!|\.)?|"
    r"indeed|precisely|"
    r"good\s+(?:guess|catch|eye)|nice\s+catch|"
    r"you\s+got\s+it|"
    r"はい|そう(?:です)?|正解|当たり"      # Japanese: yes/correct/right/bingo
    r")\b",
    re.IGNORECASE,
)

# Markers that indicate Oda is joking. Some are textual, some are emoji.
# When present, the surrounding fact is still recorded but tagged as
# jocular so readers know how to interpret it.
JOKE_MARKERS = re.compile(
    r"\(joke\)|\(笑\)|笑(?:い)?|haha+|hehe+|lol(?:l+)?|kidding|"
    r"just\s+kidding|on\s+a\s+serious\s+note|"
    r"😂|😆|😅|🤣|😄|😜|👅",
    re.IGNORECASE,
)

# Phrases where Oda explicitly refuses to confirm. If these appear
# within ~80 chars of the value-match, the fact is treated as DODGED
# and never promoted (regardless of any other match in the same text).
DODGE_PHRASES = re.compile(
    r"can['']?t\s+(?:say|tell|reveal)|"
    r"won['']?t\s+(?:say|tell|reveal)|"
    r"not\s+telling|"
    r"secret\s+for\s+now|that['']s\s+a\s+secret|that['']s\s+secret|"
    r"you['']?ll\s+see|wait\s+and\s+see|"
    r"is\s+a\s+secret|"
    r"hmm[…\.]+|hmmm[…\.]+|"
    r"please\s+wait|stay\s+tuned",
    re.IGNORECASE,
)

# Negation patterns near a value (e.g. "not 21") that flip the
# interpretation. Used during proximity check.
NEGATION_NEAR = re.compile(
    r"\b(?:not|isn['']?t|aren['']?t|wasn['']?t|weren['']?t|"
    r"doesn['']?t|don['']?t|never|no(?:t)?)\b",
    re.IGNORECASE,
)


def name_pattern(name, aliases=()):
    parts = [name] + list(aliases)
    parts.sort(key=len, reverse=True)
    alts = "|".join(re.escape(p) for p in parts if len(p) >= 3)
    if not alts: return None
    return re.compile(rf"\b(?:{alts})\b", re.IGNORECASE)


def normalised_candidates(value):
    """Variants to try, decreasing strictness."""
    out = [str(value).strip()]
    no_paren = re.sub(r"\s*\([^)]*\)", "", str(value)).strip()
    if no_paren and no_paren not in out: out.append(no_paren)
    for sep in [" · ", "; ", " , "]:
        if sep in str(value):
            for part in str(value).split(sep):
                p = part.strip()
                if p and p not in out: out.append(p)
                p2 = re.sub(r"\s*\([^)]*\)", "", p).strip()
                if p2 and p2 not in out: out.append(p2)
    digits_only = re.sub(r"[^\d]", "", str(value))
    if digits_only and len(digits_only) >= 3 and digits_only not in out:
        out.append(digits_only)
    no_commas = str(value).replace(",", "")
    if no_commas and no_commas not in out: out.append(no_commas)
    return out


def proximity_match(text, value, name_pat, window):
    """Find a value-mention within `window` chars of a name-mention.
    Returns the match dict (with snippet) or None."""
    if not value: return None
    val_pat = re.compile(rf"\b{re.escape(value)}\b", re.IGNORECASE)
    for m in val_pat.finditer(text):
        lo = max(0, m.start() - window)
        hi = min(len(text), m.end() + window)
        window_text = text[lo:hi]
        nm = name_pat.search(window_text)
        if nm:
            return {
                "value_match": m.group(0),
                "name_match":  nm.group(0),
                "value_pos":   m.start(),
                "value_end":   m.end(),
                "snippet":     text[max(0, m.start()-80):min(len(text), m.end()+80)].strip(),
            }
    return None


def digit_proximity_match(text, value, name_pat, window):
    digit_groups = sorted(set(re.findall(r"\d+", str(value))), key=len, reverse=True)
    for d in digit_groups:
        if len(d) < 2: continue
        d_pat = re.compile(rf"\b{re.escape(d)}\b")
        for m in d_pat.finditer(text):
            lo = max(0, m.start() - window)
            hi = min(len(text), m.end() + window)
            nm = name_pat.search(text[lo:hi])
            if nm:
                return {
                    "value_match": m.group(0),
                    "name_match":  nm.group(0),
                    "value_pos":   m.start(),
                    "value_end":   m.end(),
                    "snippet":     text[max(0, m.start()-80):min(len(text), m.end()+80)].strip(),
                }
    return None


def detect_dodge_near(text, pos, end, window=80):
    """True if a dodge phrase appears within `window` chars of [pos, end]."""
    lo = max(0, pos - window)
    hi = min(len(text), end + window)
    return bool(DODGE_PHRASES.search(text[lo:hi]))


def detect_negation_near(text, pos, end, window=30):
    """True if a negation appears within `window` chars BEFORE the value."""
    lo = max(0, pos - window)
    return bool(NEGATION_NEAR.search(text[lo:pos]))


def detect_confirmation(question, answer, value, name_pat):
    """True if the reader proposed `value` in the question AND the answer
    opens with a confirmation word. This is the 'reader-proposed,
    Oda-agreed' canon case (e.g. Yamato's birthday)."""
    if not question or not answer: return False
    # Value must appear in the question
    val_pat = re.compile(rf"\b{re.escape(str(value))}\b", re.IGNORECASE)
    if not val_pat.search(question):
        # Try normalised variants in question
        for v in normalised_candidates(value)[1:3]:  # try 2 looser variants
            if re.search(rf"\b{re.escape(v)}\b", question, re.IGNORECASE):
                break
        else:
            return False
    # Answer must open with a confirmation word
    return bool(CONFIRM_OPENERS.match(answer.strip()))


def detect_jocular(answer):
    return bool(JOKE_MARKERS.search(answer or ""))


def evaluate_match(question, answer, value, name_pat):
    """Master decision function.
    Returns dict { tier, intent, match_info, matched_form } or None.

    Order of checks:
      1. Verbatim + sentence-proximity (in either Q or A) + no dodge nearby
         → CANON
      2. Confirmation pattern (Q has value, A confirms) + no dodge
         → CANON, intent=confirmation
      3. Verbatim + paragraph-proximity (in answer) + no dodge
         → LIKELY
      4. Normalised + proximity + no dodge
         → LIKELY
      5. Otherwise → None
    Jocular intent overlays on top of any tier.
    """
    text = (question or "") + " ║ " + (answer or "")  # separator marks Q|A boundary
    jocular = detect_jocular(answer)

    # Pass 1: verbatim + sentence proximity → CANON candidate
    m = proximity_match(text, value, name_pat, SENTENCE_PROXIMITY)
    if m:
        if detect_dodge_near(text, m["value_pos"], m["value_end"]):
            return None
        if detect_negation_near(text, m["value_pos"], m["value_end"]):
            return None
        intent = "jocular" if jocular else "serious"
        return {"tier": "canon", "intent": intent,
                "match_info": m, "matched_form": value, "rule": "verbatim+sentence"}

    # Pass 2: confirmation pattern → CANON candidate
    if detect_confirmation(question, answer, value, name_pat):
        if not DODGE_PHRASES.search(answer or ""):
            intent = "jocular" if jocular else "confirmation"
            # Source position = start of answer for snippet
            return {"tier": "canon", "intent": intent,
                    "match_info": {"snippet": (answer or "")[:200].strip(),
                                   "value_match": str(value),
                                   "name_match": name_pat.search(question or "").group(0) if name_pat.search(question or "") else "",
                                   "value_pos": 0, "value_end": 0},
                    "matched_form": value, "rule": "confirmation"}

    # Pass 3: verbatim + paragraph proximity → LIKELY
    m = proximity_match(text, value, name_pat, PARAGRAPH_PROXIMITY)
    if m:
        if detect_dodge_near(text, m["value_pos"], m["value_end"]):
            return None
        if detect_negation_near(text, m["value_pos"], m["value_end"]):
            return None
        intent = "jocular" if jocular else "serious"
        return {"tier": "likely", "intent": intent,
                "match_info": m, "matched_form": value, "rule": "verbatim+paragraph"}

    # Pass 4: normalised + paragraph proximity → LIKELY
    for variant in normalised_candidates(value)[1:]:  # skip original (already tried)
        m = proximity_match(text, variant, name_pat, PARAGRAPH_PROXIMITY)
        if m and not detect_dodge_near(text, m["value_pos"], m["value_end"]):
            intent = "jocular" if jocular else "serious"
            return {"tier": "likely", "intent": intent,
                    "match_info": m, "matched_form": variant, "rule": "normalised"}

    # Pass 5: digit-group proximity → LIKELY (loosest, only if no other hit)
    m = digit_proximity_match(text, value, name_pat, PARAGRAPH_PROXIMITY)
    if m and not detect_dodge_near(text, m["value_pos"], m["value_end"]):
        intent = "jocular" if jocular else "ambiguous"
        return {"tier": "likely", "intent": intent,
                "match_info": m, "matched_form": "digit-group",
                "rule": "digit-proximity"}

    return None


def main():
    dry    = "--dry-run" in sys.argv
    strict = "--strict" in sys.argv
    top    = None
    if "--top" in sys.argv:
        i = sys.argv.index("--top")
        try: top = int(sys.argv[i + 1])
        except: pass

    if not os.path.exists(PUNK_PATH):
        print("  ✗ punk_records.json missing"); sys.exit(1)
    if not os.path.exists(SBS_PATH):
        print("  ✗ sbs_archive.json missing"); sys.exit(1)

    pr  = json.load(open(PUNK_PATH, encoding="utf-8"))
    sbs = json.load(open(SBS_PATH,  encoding="utf-8"))
    facts = json.load(open(FACTS_PATH, encoding="utf-8")) if os.path.exists(FACTS_PATH) else []

    # Load curate decisions ledger so we don't re-surface items the
    # maintainer has already triaged. Most-recent row per (claim_id,
    # evidence_id) wins; "approve" / "reject" / "defer" all suppress
    # re-queueing.
    decided = {}  # (claim_id, evidence_id) -> latest decision row
    if os.path.exists(DECISIONS_JSON):
        try:
            ledger = json.load(open(DECISIONS_JSON, encoding="utf-8"))
            for row in ledger.get("decisions", []):
                key = (row.get("claim_id"), row.get("evidence_id"))
                if key[0] and key[1]:
                    decided[key] = row  # later rows overwrite earlier
        except Exception as e:
            print(f"  ⚠ curate_decisions.json unreadable ({e}) — proceeding without ledger")

    # Drop prior verify outputs; re-derive everything
    facts_kept = [f for f in facts if not f.get("id", "").startswith("verified:")]
    facts_by_id = {f["id"]: f for f in facts_kept}

    candidates = [(n, r) for n, r in pr.items() if r.get("found")]
    candidates.sort(key=lambda x: -(x[1].get("appearances", 0) or 0))
    if top: candidates = candidates[:top]

    print("=" * 60)
    print(f"  Verify v3 — intent-aware free-path verification")
    print(f"  Mode      : {'STRICT (canon only)' if strict else 'NORMAL'}")
    print(f"  Characters: {len(candidates):,}")
    print(f"  SBS Q&As  : {len(sbs):,}")
    print("=" * 60); print()

    promoted_canon  = 0
    promoted_likely = 0
    rejected_dodge  = 0
    rejected_negate = 0
    skipped_no_sbs  = 0
    skipped_decided = 0  # ambiguous items the maintainer already triaged
    by_intent = defaultdict(int)
    ambig_queue = []  # for curate.html

    for name, rec in candidates:
        pat = name_pattern(name, NAME_ALIASES.get(name, ()))
        if pat is None: continue

        # Filter to SBS Q&As that mention this character
        char_qas = []
        for entry in sbs:
            text = ((entry.get("question") or "") + " "
                  + (entry.get("answer")   or ""))
            if pat.search(text):
                char_qas.append(entry)
        if not char_qas:
            skipped_no_sbs += 1
            continue

        for field in VERIFIABLE_FIELDS:
            value = rec.get(field)
            if not value: continue
            value = str(value).strip()
            if not value: continue

            slug = name.replace(" ", "_").replace(".", "")
            claim_id = f"verified:{slug}:{field}"

            best = None  # (entry, evaluation)
            for entry in char_qas:
                ev = evaluate_match(entry.get("question", ""),
                                    entry.get("answer", ""),
                                    value, pat)
                if not ev: continue
                # Prefer canon over likely; among same tier, prefer earlier-found
                if not best:
                    best = (entry, ev)
                elif ev["tier"] == "canon" and best[1]["tier"] == "likely":
                    best = (entry, ev)
                if best[1]["tier"] == "canon": break  # canon wins, stop

            if not best: continue
            entry, ev = best
            if strict and ev["tier"] != "canon": continue

            qa_id = entry.get("id_num")
            vol   = entry.get("volume")
            evidence_id = (
                f"sbs:vol{str(vol).zfill(3)}-q{str(qa_id).zfill(4)}"
                if (vol is not None and qa_id is not None) else None
            )
            sources = [
                {"type": "sbs", "volume": vol,
                 "qa_id": str(qa_id).zfill(4) if qa_id else None,
                 "match_type": ev["rule"],
                 "matched_form": str(ev["matched_form"])},
                # Wiki source carries a value-at-verify snapshot so a
                # future run can detect when the wiki has been edited
                # since this promotion. If wiki[field] later differs
                # from value_at_verify, this fact is stale and needs
                # re-verification.
                {"type": "wiki", "page": name.replace(" ", "_"),
                 "field": field,
                 "value_at_verify": value}
            ]
            fact = {
                "id":        claim_id,
                "subject":   name,
                "predicate": field,
                "value":     value,
                "tier":      ev["tier"],
                "intent":    ev["intent"],
                "sources":   sources,
                "evidence_notes": (
                    f"{ev['tier'].upper()} ({ev['intent']}) — "
                    f"matched via '{ev['rule']}' in SBS Vol {vol} #{qa_id}. "
                    f"Snippet: \"{ev['match_info'].get('snippet', '')[:160]}…\""
                ),
                "verified_on": TODAY,
                "verified_by": VERIFIER,
            }
            facts_by_id[claim_id] = fact
            by_intent[ev["intent"]] += 1
            if ev["tier"] == "canon": promoted_canon += 1
            else:                     promoted_likely += 1

            # Anything tagged ambiguous goes to the curate queue too,
            # so a maintainer can upgrade it to canon or kick it down.
            # Skip items already decided in curate_decisions.json — the
            # maintainer has triaged them; don't re-surface.
            if ev["intent"] == "ambiguous":
                if evidence_id and (claim_id, evidence_id) in decided:
                    skipped_decided += 1
                    continue
                ambig_queue.append({
                    "claim_id":     claim_id,
                    "evidence_id":  evidence_id,
                    "subject":      name,
                    "field":        field,
                    "value":        value,
                    "vol":          vol,
                    "qa_id":        qa_id,
                    "snippet":      ev["match_info"].get("snippet", ""),
                    "rule":         ev["rule"],
                })

    # ── REPORT ────────────────────────────────────────────────
    print(f"  🟢 CANON  promotions  : {promoted_canon:,}")
    print(f"  🔵 LIKELY promotions  : {promoted_likely:,}")
    print(f"  · Skipped (no SBS)    : {skipped_no_sbs:,}")
    print(f"  · Ambiguous → curate  : {len(ambig_queue):,}")
    if decided:
        print(f"  · Suppressed by ledger: {skipped_decided:,}  ({len(decided)} prior decisions)")
    print()
    print(f"  By intent:")
    for k in ("serious", "confirmation", "jocular", "ambiguous"):
        if by_intent[k]: print(f"    {k:14s} {by_intent[k]:>5,}")
    print()

    # Apply curate-ledger approve decisions: upgrade matching likely→canon facts.
    # Only fires when curate_decisions.json has decide="approve" rows — currently
    # none exist, but the loop is ready when the maintainer starts approving.
    upgraded_by_curate = 0
    for (cid, eid), row in decided.items():
        if row.get("decision") != "approve":
            continue
        fact = facts_by_id.get(cid)
        if fact and fact.get("tier") == "likely":
            fact["tier"] = "canon"
            fact.setdefault("curate_approved_by", []).append({
                "evidence_id": eid,
                "decided_by":  row.get("decided_by", ""),
                "decided_on":  row.get("decided_on", ""),
                "note":        row.get("note", ""),
            })
            upgraded_by_curate += 1
    if upgraded_by_curate:
        print(f"  ✅ Curate-approved upgrades: {upgraded_by_curate}  (likely→canon)")

    if dry:
        print("  (dry run — nothing written)")
        return

    merged = list(facts_by_id.values())
    with open(FACTS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Wrote canon_facts.json  ({len(merged):,} total)")

    # Curate queue (ambiguous facts that could be upgraded by a human)
    os.makedirs(os.path.dirname(AMBIG_JSON), exist_ok=True)
    with open(AMBIG_JSON, "w", encoding="utf-8") as f:
        json.dump(ambig_queue, f, ensure_ascii=False, indent=2)
    print(f"  ✓ Wrote {AMBIG_JSON}  ({len(ambig_queue):,} ambiguous)")

    # Empty out the legacy queue files (no longer the source of truth)
    with open(QUEUE_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Promotions Pending — {TODAY}\n\n"
                f"_Verify v3 emits ambiguous matches to docs/curate_queue.json,_\n"
                f"_reviewable in `curate.html`. This file is kept empty for_\n"
                f"_backwards compatibility._\n")
    with open(QUEUE_JSON, "w", encoding="utf-8") as f:
        json.dump([], f)

    # Verification report
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Verification Report — {TODAY}\n\n")
        f.write(f"Run by: `{VERIFIER}`\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- 🟢 **Canon promotions:** {promoted_canon:,}\n")
        f.write(f"- 🔵 **Likely promotions:** {promoted_likely:,}\n")
        if upgraded_by_curate:
            f.write(f"- ✅ **Curate-approved upgrades (likely→canon):** {upgraded_by_curate:,}\n")
        f.write(f"- · **Skipped (no SBS hits):** {skipped_no_sbs:,}\n")
        f.write(f"- · **Ambiguous → curate.html:** {len(ambig_queue):,}\n")
        f.write(f"- **Total auto-promoted:** {promoted_canon + promoted_likely:,}\n\n")
        f.write(f"## By intent\n\n")
        f.write("| Intent | Count | Meaning |\n|---|---:|---|\n")
        meanings = {
            "serious":      "Oda's plain statement",
            "confirmation": "Reader proposed value, Oda agreed (e.g. Yamato's birthday)",
            "jocular":      "Oda's joke — still on record but tagged",
            "ambiguous":    "Match plausible but unclear; appears in curate.html",
        }
        for k in ("serious", "confirmation", "jocular", "ambiguous"):
            if by_intent[k]:
                f.write(f"| {k} | {by_intent[k]:,} | {meanings[k]} |\n")
        f.write(f"\n## How a fact qualifies\n\n")
        f.write("See [canon-policy.md](canon-policy.md) §How Oda's style is interpreted.\n")
    print(f"  ✓ Wrote {REPORT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
