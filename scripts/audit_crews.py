"""Check crew.html for crew keys with parentheticals that will fail ?name= lookup."""
import sys, json, re
sys.stdout.reconfigure(encoding="utf-8")

with open("crew.html", encoding="utf-8", errors="ignore") as f:
    src = f.read()

# Find the baked crews data block
blocks = re.findall(r'<script[^>]*>(.*?)</script>', src, re.DOTALL)
crews = {}
for b in blocks:
    b = b.strip()
    if b.startswith("{") and '"crews"' in b[:80]:
        try:
            data = json.loads(b)
            crews = data.get("crews", {})
            break
        except Exception:
            pass

print(f"Total crew keys: {len(crews)}")
parens = [k for k in crews if "(" in k]
print(f"Crew keys with parentheticals: {len(parens)}")
for k in sorted(parens):
    bare = k.split("(")[0].strip()
    bare_exists = bare in crews
    print(f"  {repr(k)}")
    print(f"    bare={repr(bare)}  bare_in_crews={bare_exists}")
