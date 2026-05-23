"""Quick inspection — dump the raw wikitext of one SBS volume to a file
so we can see what format the wiki actually uses."""
import requests, sys, os

VOL = int(sys.argv[1]) if len(sys.argv) > 1 else 10

resp = requests.get("https://onepiece.fandom.com/api.php", params={
    "action": "parse",
    "page":   f"SBS_Volume_{VOL}",
    "prop":   "wikitext",
    "format": "json",
}, headers={"User-Agent": "OPInspect/1.0"}, timeout=20)

text = resp.json().get("parse", {}).get("wikitext", {}).get("*", "")
out = os.path.join(os.path.dirname(__file__), f"sbs_raw_vol{VOL}.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Wrote {len(text)} chars to {out}")
print("First 800 chars:")
print("-" * 50)
print(text[:800])
