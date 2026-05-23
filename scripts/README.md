# Codex control shortcuts

Double-click any `.bat` file to run it. The window stays open so you can read
the output; press any key when done.

| File | What it does | Network? | Pushes to live site? |
|---|---|---|---|
| `audit.bat` | Sanity-check all data files. Read-only. | No | No |
| `refresh-quick.bat` | Pull new chapters / SBS / theories / covers. Skips long scrapes. | Yes | No |
| `refresh.bat` | Full refresh including Punk Records + SBS images. ~30 min cold. | Yes | No |
| `freshen.bat` | Mark stale wiki pages for re-fetch on next refresh. | Yes (light) | No |
| `publish.bat` | Full refresh **and** commits + pushes to GitHub. | Yes | **YES** |

## Pinning to the taskbar

Right-click `refresh-quick.bat` → "Pin to Start" (or drag to your desktop).
Now it's one click from anywhere.

## Safety

These run **only on your PC** when **you** double-click. Visitors to the
live site cannot trigger them — there is no path from the public site to
this folder.
