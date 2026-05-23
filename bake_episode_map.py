"""
Bake the episode <-> chapter map for The Shimotsuki Codex.

Sources:
  - listfist.com  (per-episode title + chapter list)
  - modernLifeRocko/fillers (canon/filler/mixed classification, MIT licensed)

Output: episode_map.json — { generated_on, episodes: [...], chapter_to_episodes: {...} }
where each episode entry is:
    { ep, title, chapters: [int,...], tag: "manga"|"anime"|"filler"|"mixed" }

Run periodically to refresh as new episodes air.
"""
import urllib.request, json, re, sys, os
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')

LISTFIST_URL = 'https://listfist.com/list-of-one-piece-episode-to-chapter-conversion'
FILLERS_URL  = 'https://raw.githubusercontent.com/modernLifeRocko/fillers/main/data/animefillerlist.json'

def http_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 ShimotsukiCodex/1.0'})
    return urllib.request.urlopen(req, timeout=30).read()

def strip_html(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    repl = {
        '&amp;': '&', '&quot;': '"', '&apos;': "'", '&#039;': "'",
        '&#8217;': '’', '&#8216;': '‘',
        '&#8220;': '"', '&#8221;': '"', '&#8211;': '–', '&#8212;': '—',
    }
    for k, v in repl.items():
        s = s.replace(k, v)
    return s.strip()

def main():
    print('[1/3] Fetching listfist episode->chapter table...')
    html = http_get(LISTFIST_URL).decode('utf-8', errors='replace')
    m = re.search(r'<table[^>]*>(.*?)</table>', html, re.S)
    if not m:
        raise SystemExit('Could not find table on listfist page')
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(1), re.S)
    episodes = []
    for r in rows:
        cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)
        if len(cells) < 3:
            continue
        ep_str = strip_html(cells[0])
        if not ep_str.isdigit():
            continue
        ep = int(ep_str)
        title = strip_html(cells[1])
        ch_text = strip_html(cells[2])
        ch_nums = []
        if ch_text and ch_text.lower() not in ('n/a', '-', ''):
            for p in re.split(r'[|,/]', ch_text):
                n = re.match(r'(\d+)', p.strip())
                if n:
                    ch_nums.append(int(n.group(1)))
        episodes.append({'ep': ep, 'title': title, 'chapters': ch_nums})
    episodes.sort(key=lambda x: x['ep'])
    print(f'  -> {len(episodes)} episodes parsed (max ep = {episodes[-1]["ep"]})')

    print('[2/3] Fetching filler classification...')
    fillers = json.loads(http_get(FILLERS_URL).decode('utf-8'))
    op = fillers['one piece']
    sets = {
        'manga': set(op['Manga Canon']),
        'anime': set(op['Anime Canon']),
        'filler': set(op['Filler']),
        'mixed': set(op['Mixed Canon/Filler']),
    }
    def classify(ep):
        for tag, s in sets.items():
            if ep in s:
                return tag
        return None
    for e in episodes:
        e['tag'] = classify(e['ep']) or ('manga' if e['chapters'] else 'filler')

    print('[3/3] Writing episode_map.json...')
    ch_to_eps = {}
    for e in episodes:
        for ch in e['chapters']:
            ch_to_eps.setdefault(ch, []).append(e['ep'])
    out = {
        'generated_on': str(date.today()),
        'sources': {
            'episode_chapter': LISTFIST_URL,
            'filler_classification': 'https://github.com/modernLifeRocko/fillers',
        },
        'episode_count': len(episodes),
        'max_episode': episodes[-1]['ep'],
        'max_chapter': max(ch_to_eps) if ch_to_eps else 0,
        'episodes': episodes,
        'chapter_to_episodes': {str(k): sorted(v) for k, v in sorted(ch_to_eps.items())},
    }
    with open('episode_map.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    print(f'  -> episode_map.json ({os.path.getsize("episode_map.json")/1024:.1f} KB)  '
          f'episodes: {len(episodes)}  chapters: {len(ch_to_eps)}')

if __name__ == '__main__':
    main()
