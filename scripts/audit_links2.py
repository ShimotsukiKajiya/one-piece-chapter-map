"""Audit dynamic link patterns and param routing in detail pages."""
import sys, re, glob, os
sys.stdout.reconfigure(encoding="utf-8")

DETAIL_PAGES = [
    "character.html", "crew.html", "location.html", "ship.html",
    "fruit.html", "voices.html", "theories.html",
    # weapons.html doubles as list + detail (no singular weapon.html exists)
    "weapons.html", "locations.html",
]

print("=== Detail page param handling ===")
for p in DETAIL_PAGES:
    if not os.path.exists(p):
        print(f"  {p}: FILE MISSING")
        continue
    with open(p, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    params = set(re.findall(r'params\.get\(["\'](\w+)["\']\)', src))
    print(f"  {p}: accepts ?{' ?'.join(sorted(params))}")

print()
print("=== Dynamic href patterns (template literals) ===")
for path in sorted(glob.glob("*.html")):
    with open(path, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    # Find backtick template strings containing href= with ${...}
    hits = re.findall(r'href=`([^`]{0,120})`', src)
    if hits:
        print(f"\n  {path}:")
        for h in hits[:12]:
            print(f"    {h}")

print()
print("=== ?name= links that might have parenthetical issue ===")
# Find all ?name= link constructions and see if the value might have parens
for path in sorted(glob.glob("*.html")):
    with open(path, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    # Static links with ?name= (non-template)
    static = re.findall(r'href="([^"]*\?name=[^"]+)"', src)
    for h in static:
        if "(" in h or "\xb7" in h or " · " in h:
            print(f"  {path}: {h[:100]}")
