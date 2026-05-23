"""Audit all internal href patterns across HTML files."""
import sys, re, os, glob
sys.stdout.reconfigure(encoding="utf-8")

patterns = {}
for path in sorted(glob.glob("*.html")):
    with open(path, encoding="utf-8", errors="ignore") as f:
        src = f.read()
    for h in re.findall(r'href="([^"]+)"', src) + re.findall(r"href='([^']+)'", src):
        h = h.strip()
        if h.startswith(("http", "javascript", "#", "mailto")): continue
        if "${" in h or "`" in h: continue
        base = h.split("?")[0]
        qs   = h[len(base):]
        param_pattern = re.sub(r"=[^&]+", "=*", qs)
        key  = (base, param_pattern)
        patterns.setdefault(key, set()).add(path)

print(f"Unique link patterns found: {len(patterns)}\n")
missing = []
for (base, qs), sources in sorted(patterns.items()):
    exists = os.path.exists(base)
    flag = "  *** MISSING TARGET ***" if not exists else ""
    src_list = ", ".join(sorted(sources)[:4])
    print(f"  {base}{qs}  [{src_list}]{flag}")
    if not exists:
        missing.append((base, qs, sorted(sources)))

print(f"\n--- MISSING TARGETS ({len(missing)}) ---")
for base, qs, sources in missing:
    print(f"  {base}{qs}  used in: {', '.join(sources[:5])}")
