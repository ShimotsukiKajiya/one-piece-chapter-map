"""
audit_awakenings.py — Tighten awakening status flags to match the page's
own rule: "confirmed = Oda explicit". Updates awakenings.json AND the
embedded JSON in awakenings.html in lockstep.

Downgrades to implied (with revised notes):
  - Pica (Ishi Ishi)         — environmental conversion fits, but never named
  - Perospero (Pero Pero)    — same: WCI candy conversion not named as awakening
  - Katakuri (Mochi Mochi)   — Luffy fight feats consistent but not named

Kept as confirmed (Oda explicit):
  - Doflamingo (Ito Ito), Luffy (Nika), Kid (Jiki Jiki), Law (Ope Ope)
"""
import json
import re
import sys

if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass

DOWNGRADES = {
    ("Pica", "Ishi Ishi no Mi"): {
        "status": "implied",
        "notes": "Pica's stone manipulation across the entire mountain of Dressrosa fits the textbook description of awakening (environmental conversion as Doflamingo described it), but the manga never explicitly names it as such. Strong implication, not stated canon.",
    },
    ("Charlotte Perospero", "Pero Pero no Mi"): {
        "status": "implied",
        "notes": "Perospero's island-scale candy conversion during Whole Cake matches the awakening pattern, but Oda doesn't name it as awakening on-page. Implied, not stated.",
    },
    ("Charlotte Katakuri", "Mochi Mochi no Mi"): {
        "status": "implied",
        "notes": "Katakuri's mochi feats during the Luffy mirror-world fight are widely read as awakening, and his Special Paramecia status invites the comparison, but the manga never uses the word 'awakening' for him.",
    },
}


def update_awakening(entry: dict) -> bool:
    key = (entry.get("user"), entry.get("fruit"))
    if key in DOWNGRADES:
        change = DOWNGRADES[key]
        entry["status"] = change["status"]
        entry["notes"] = change["notes"]
        return True
    return False


def update_json_file(path: str) -> int:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    count = sum(update_awakening(a) for a in data["awakenings"])
    data["generated_on"] = "2026-04-28"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return count


def update_embedded_json(html_path: str, marker_id: str) -> int:
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    pattern = re.compile(
        r'(<script id="' + re.escape(marker_id) + r'"[^>]*>)(.*?)(</script>)',
        re.DOTALL
    )
    m = pattern.search(html)
    if not m:
        print(f"  ! {marker_id} not found in {html_path}")
        return 0
    data = json.loads(m.group(2))
    count = sum(update_awakening(a) for a in data["awakenings"])
    data["generated_on"] = "2026-04-28"
    new_payload = json.dumps(data, indent=2, ensure_ascii=False)
    new_html = html[:m.start(2)] + "\n" + new_payload + "\n" + html[m.end(2):]
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(new_html)
    return count


def main():
    json_count = update_json_file("D:/One Piece/awakenings.json")
    html_count = update_embedded_json("D:/One Piece/awakenings.html", "awakenings-data")
    print(f"  JSON: updated {json_count} entries")
    print(f"  HTML: updated {html_count} entries")


if __name__ == "__main__":
    main()
