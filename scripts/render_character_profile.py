"""Render a character profile HTML page from the relationship shards.

Pure server-side render via scripts/lib/query.py — no source-file lookups
beyond what query.py exposes. The point: produce a tangible, openable
artifact that proves the shards compose into a real view.

Output: ./out/character-profiles/<slug>.html  (override with CODEX_RENDER_OUT env var)

Usage:
    python scripts/render_character_profile.py             # default 6 chars
    python scripts/render_character_profile.py "Luffy"     # single character by name
    python scripts/render_character_profile.py --all       # every chr: ID we have appearance data for
"""
import argparse
import html
import json
import os
import sys
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Make scripts/lib importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import query  # type: ignore

OUT_DIR = Path(os.environ.get("CODEX_RENDER_OUT", "out/character-profiles"))

# Default character set — diverse data shapes
DEFAULT_NAMES = [
    "Monkey D. Luffy",         # rich shard data, captain
    "Roronoa Zoro",            # owns multiple weapons, transfer chain
    "Nico Robin",              # multi-crew history with "temporary" role
    "Portgas D. Ace",          # deceased, debut in flashback
    "Edward Newgate",          # Yonko, Rocks past
    "Trafalgar Law",           # Donquixote → Heart Pirates arc
]


def esc(s) -> str:
    return html.escape(str(s)) if s is not None else ""


# Edge convention: `from` HAS this relation = `to` (e.g. {Luffy, Dragon, father}
# reads "Luffy's father is Dragon"). When the subject is `from`, render the
# relation directly. When the subject is `to`, render the *inverse* — what is
# the subject TO the from-side? Gender-uncertain on the inverse for many cases.
_INVERSE_RELATION = {
    "father":            "child",        # subject's child is the from-side
    "mother":            "child",
    "parent":            "child",
    "child":             "parent",
    "son":               "parent",
    "daughter":          "parent",
    "grandfather":       "grandchild",
    "grandmother":       "grandchild",
    "grandparent":       "grandchild",
    "grandchild":        "grandparent",
    "grandson":          "grandparent",
    "granddaughter":     "grandparent",
    "brother":           "sibling",
    "sister":            "sibling",
    "sibling":           "sibling",
    "half-sibling":      "half-sibling",
    "foster-sibling":    "foster-sibling",
    "husband":           "spouse",
    "wife":              "spouse",
    "spouse":            "spouse",
    "partner":           "partner",
    "uncle":             "niece-nephew",
    "aunt":              "niece-nephew",
    "uncle-aunt":        "niece-nephew",
    "nephew":            "uncle-aunt",
    "niece":             "uncle-aunt",
    "niece-nephew":      "uncle-aunt",
    "cousin":            "cousin",
    "in-law":            "in-law",
    "ancestor":          "descendant",
    "descendant":        "ancestor",
    "adopted-by":        "adopted-child",
    "adoptive-father":   "adoptive-child",
    "adoptive-mother":   "adoptive-child",
    "adopted-child":     "adopted-by",
    "adoptive-son":      "adoptive-parent",
    "adoptive-daughter": "adoptive-parent",
    "adoptive-brother":  "adoptive-sibling",
    "adoptive-sister":   "adoptive-sibling",
    "sworn-sibling":     "sworn-sibling",
    "sworn-brother":     "sworn-sibling",
    "sworn-sister":      "sworn-sibling",
    "guardian":          "ward",          # not in the schema; rendering only
}


def _label(relation: str) -> str:
    """Title-case a relation slug for display: 'sworn-brother' -> 'Sworn brother'."""
    return relation.replace("-", " ").capitalize()


_TIER_GLYPH = {
    "canon":       "🟢",
    "likely":      "🔵",
    "speculation": "🟣",
    "rumour":      "🟠",
    "disproven":   "🔴",
}


def _tier_badge(tier: str | None) -> str:
    """Return a small inline tier-badge HTML span, or empty string if no tier."""
    if not tier:
        return ""
    glyph = _TIER_GLYPH.get(tier, "·")
    return f"<span class='badge tier-{esc(tier)}'>{glyph} {esc(tier)}</span>"


def _evidence_html(evidence: list | None) -> str:
    """Render evidence pointers as small monospace text after a fact."""
    if not evidence:
        return ""
    refs = []
    for e in evidence:
        if isinstance(e, dict) and e.get("canon_fact_id"):
            refs.append(esc(e["canon_fact_id"]))
    if not refs:
        return ""
    return f"<span class='ev'>← {' · '.join(refs)}</span>"


def render_profile(chr_id: str) -> tuple[str, str]:
    """Return (slug, html_text) for the character. Slug used as filename."""
    name = query.display_name(chr_id) or chr_id
    d = query.character_dossier(chr_id)

    # Derive a filename slug from the name
    slug = name.lower().replace(" ", "-").replace(".", "").replace(",", "")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append("<html lang='en'><head>")
    parts.append(f"<meta charset='utf-8'><title>{esc(name)} — shard view</title>")
    parts.append("<style>")
    parts.append("""
      body { font: 16px/1.5 system-ui, sans-serif; max-width: 760px;
             margin: 2em auto; padding: 0 1em; color: #222; }
      header { border-bottom: 2px solid #d4a44a; padding-bottom: 1em;
               margin-bottom: 1em; }
      h1 { margin: 0 0 .2em 0; }
      .id { color: #888; font-family: monospace; font-size: .9em; }
      .meta { color: #555; }
      h2 { color: #6a9ec8; border-bottom: 1px solid #ddd;
           padding-bottom: .2em; margin-top: 1.5em; }
      table { border-collapse: collapse; width: 100%; margin: .5em 0; }
      td, th { text-align: left; padding: .3em .6em; border-bottom: 1px solid #eee; }
      th { color: #666; font-weight: 600; font-size: .85em;
           text-transform: uppercase; letter-spacing: .03em; }
      .empty { color: #999; font-style: italic; }
      .badge { display: inline-block; padding: 1px 8px; border-radius: 10px;
               font-size: .78em; margin-left: .4em; }
      .current  { background: #d4f5d4; color: #2a662a; }
      .former   { background: #f0e0e0; color: #863030; }
      .role     { background: #f0e8d4; color: #6a4a10; }
      .tier-canon       { background: #d4a44a; color: #3a2a05; font-weight: 600; }
      .tier-likely      { background: #cfe1f0; color: #1d3e57; }
      .tier-speculation { background: #ece4f5; color: #4a2c6e; font-style: italic; }
      .tier-rumour      { background: #ffe4ca; color: #774311; font-style: italic; }
      .tier-disproven   { background: #f5d0d0; color: #883333; text-decoration: line-through; }
      .ev   { color: #888; font-size: .8em; margin-left: .3em; font-family: monospace; }
      .ev a { color: #6a9ec8; text-decoration: none; }
      footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid #ddd;
               color: #888; font-size: .85em; }
      code { background: #f4f4f4; padding: 1px 5px; border-radius: 3px;
             font-size: .9em; }
    """)
    parts.append("</style></head><body>")

    # Header
    parts.append("<header>")
    parts.append(f"<h1>{esc(name)}</h1>")
    parts.append(f"<div class='id'>{esc(chr_id)}</div>")
    debut = d.get("debut")
    if debut:
        # Find the debut row in the shard so we can grab its tier + evidence
        debut_rows = query.by_from("debuts-in").get(chr_id, [])
        debut_row = debut_rows[0] if debut_rows else {}
        debut_tier = _tier_badge(debut_row.get("tier"))
        debut_ev   = _evidence_html(debut_row.get("evidence"))
        debut_str = (f"debut <code>{esc(debut['chapter'])}</code> "
                     f"({esc(debut['appearance_type'])}){debut_tier}{debut_ev}")
    else:
        debut_str = "no debut row"
    parts.append(f"<div class='meta'>{d['appearance_count']:,} appearances · {debut_str}</div>")
    parts.append("</header>")

    # Crews
    parts.append("<h2>Crews</h2>")
    if d["crews"]:
        parts.append("<table>")
        parts.append("<tr><th>Crew</th><th>Status</th><th>Role</th></tr>")
        for c in d["crews"]:
            crew_name = query.display_name(c["to"]) or c["to"]
            badge = "<span class='badge current'>current</span>" if c.get("current") else "<span class='badge former'>former</span>"
            role = f"<span class='badge role'>{esc(c['role'])}</span>" if c.get("role") else ""
            parts.append(f"<tr><td>{esc(crew_name)}</td><td>{badge}</td><td>{role}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<div class='empty'>No crew membership recorded in shards.</div>")

    # Devil Fruit
    parts.append("<h2>Devil Fruit</h2>")
    if d["fruits"]:
        parts.append("<table>")
        parts.append("<tr><th>Fruit</th><th>First chapter</th><th>Status</th><th>Tier</th></tr>")
        for f in d["fruits"]:
            fruit_name = query.display_name(f["to"]) or f["to"]
            chap = esc(f.get("chapter", "—"))
            badge = "<span class='badge current'>current</span>" if f.get("current") else "<span class='badge former'>former</span>"
            tier_html = _tier_badge(f.get("tier")) + _evidence_html(f.get("evidence"))
            parts.append(f"<tr><td>{esc(fruit_name)}</td><td><code>{chap}</code></td><td>{badge}</td><td>{tier_html}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<div class='empty'>No devil fruit recorded.</div>")

    # Owns (weapons / items)
    parts.append("<h2>Owned weapons / items</h2>")
    if d["owns"]:
        parts.append("<table>")
        parts.append("<tr><th>Item</th><th>Status</th><th>From</th></tr>")
        for o in d["owns"]:
            item_name = query.display_name(o["to"]) or o["to"]
            badge = "<span class='badge current'>current</span>" if o.get("current") else "<span class='badge former'>former</span>"
            from_owner = ""
            if o.get("from_owner"):
                from_name = query.display_name(o["from_owner"]) or o["from_owner"]
                from_owner = f"from {esc(from_name)}"
            parts.append(f"<tr><td>{esc(item_name)}</td><td>{badge}</td><td>{from_owner}</td></tr>")
        parts.append("</table>")
    else:
        parts.append("<div class='empty'>No owned items recorded.</div>")

    # Family — natural-language directional list
    # Convention: edge {from, to, relation} reads "from's RELATION is to".
    # If subject is `from`: render relation as-is ("Father: Dragon").
    # If subject is `to`: render the inverse relation ("Child: Luffy" on Dragon's profile).
    parts.append("<h2>Family</h2>")
    if d["family"]:
        parts.append("<ul style='list-style:none;padding:0;'>")
        for fam in d["family"]:
            relation = fam["relation"]
            if fam["from"] == chr_id:
                other_id   = fam["to"]
                label      = _label(relation)
            else:
                other_id   = fam["from"]
                label      = _label(_INVERSE_RELATION.get(relation, relation))
            other_name = query.display_name(other_id) or other_id
            src = f" <code>ch:{fam['chapter']}</code>" if fam.get("chapter") else ""
            note = f" — <em>{esc(fam['note'])}</em>" if fam.get("note") else ""
            tier_html = _tier_badge(fam.get("tier")) + _evidence_html(fam.get("evidence"))
            parts.append(f"<li><strong>{esc(label)}:</strong> {esc(other_name)}{src}{note}{tier_html}</li>")
        parts.append("</ul>")
    else:
        parts.append("<div class='empty'>No family edges recorded.</div>")

    # Footer
    parts.append("<footer>")
    parts.append("Generated from the relationship shards via <code>scripts/lib/query.py</code>. ")
    parts.append("Sources: <code>relationships/{family,member-of,ate-fruit,owns,debuts-in,appears-in}.json</code>. ")
    parts.append("This is a demo render — no live styling, no JS, no source-file fallbacks.")
    parts.append("</footer>")
    parts.append("</body></html>")

    return slug, "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="Render a single character by name")
    parser.add_argument("--all", action="store_true",
                        help="Render every character that has at least one shard row")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        # Collect every chr: ID that appears as `from` in any major shard
        targets: set[str] = set()
        for shard in ("appears-in", "debuts-in", "member-of", "ate-fruit", "owns"):
            for row in query.load_shard(shard):
                fr = row.get("from")
                if fr and fr.startswith("chr:"):
                    targets.add(fr)
        target_ids = sorted(targets)
        print(f"Rendering {len(target_ids)} character profiles…")
    elif args.name:
        cid = query.resolve_character(args.name)
        if not cid:
            print(f"Could not resolve character: {args.name!r}")
            sys.exit(1)
        target_ids = [cid]
    else:
        target_ids = []
        for n in DEFAULT_NAMES:
            cid = query.resolve_character(n)
            if cid:
                target_ids.append(cid)
            else:
                print(f"  ⚠  could not resolve {n!r}, skipping")

    written = 0
    used_slugs: dict[str, str] = {}  # slug -> chr_id (for collision detection)
    rendered: list[tuple[str, str, int]] = []  # (chr_id, slug, appearance_count)

    for cid in target_ids:
        slug, body = render_profile(cid)
        # Slug collision: append numeric suffix until unique
        if slug in used_slugs and used_slugs[slug] != cid:
            n = 2
            while f"{slug}-{n}" in used_slugs:
                n += 1
            slug = f"{slug}-{n}"
        used_slugs[slug] = cid

        out_path = OUT_DIR / f"{slug}.html"
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        rendered.append((cid, slug, query.character_dossier(cid)["appearance_count"]))
        written += 1

    print(f"Wrote {written} profiles → {OUT_DIR}")

    # Always rebuild the index — alphabetical, with appearance count for scale
    if written:
        idx_path = OUT_DIR / "index.html"
        # Sort alphabetically by display name (case-insensitive)
        rendered_sorted = sorted(
            rendered,
            key=lambda r: (query.display_name(r[0]) or r[0]).lower(),
        )
        with open(idx_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("<!DOCTYPE html><html><head><meta charset='utf-8'>")
            f.write(f"<title>Character profile demos ({written:,})</title>")
            f.write("<style>")
            f.write("body{font:15px/1.5 system-ui;max-width:760px;margin:1.5em auto;padding:0 1em}")
            f.write("h1{color:#d4a44a;border-bottom:2px solid #d4a44a;padding-bottom:.3em}")
            f.write(".meta{color:#666;margin-bottom:1em}")
            f.write("a{color:#6a9ec8;text-decoration:none}a:hover{text-decoration:underline}")
            f.write("ul{columns:2;column-gap:2em;list-style:none;padding:0}")
            f.write("li{break-inside:avoid;padding:.15em 0;border-bottom:1px solid #eee}")
            f.write(".cnt{color:#888;font-size:.8em;float:right}")
            f.write("input{width:100%;padding:.5em;margin-bottom:1em;font-size:1em;")
            f.write("       border:1px solid #ccc;border-radius:4px}")
            f.write("</style></head><body>")
            f.write(f"<h1>Character profile demos</h1>")
            f.write(f"<div class='meta'>{written:,} profiles, rendered from relationship shards. ")
            f.write("Press Ctrl+F to search.</div>")
            f.write("<input type='text' placeholder='Filter by name…' oninput=\"")
            f.write("var q=this.value.toLowerCase();")
            f.write("document.querySelectorAll('li').forEach(li=>{")
            f.write("li.style.display=li.textContent.toLowerCase().includes(q)?'':'none'})\">")
            f.write("<ul>")
            for cid, slug, app_count in rendered_sorted:
                name = query.display_name(cid) or cid
                f.write(f"<li><a href='{slug}.html'>{html.escape(name)}</a>")
                f.write(f"<span class='cnt'>{app_count:,}</span></li>")
            f.write("</ul></body></html>")
        print(f"Wrote index → {idx_path}")


if __name__ == "__main__":
    main()
