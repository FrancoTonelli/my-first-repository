#!/usr/bin/env python3
"""Sync a shared Google Photos album into a local workspace.

usage:
  album.py WORKSPACE list   [--from 'YYYY-MM-DD HH:MM'] [--to ...]   # list items (no download)
  album.py WORKSPACE pull   [--from ...] [--to ...]                  # download new items in range
  album.py WORKSPACE retry  [--rounds 20] [--wait 120]               # re-download low-res videos until HD

Items are keyed by their Google Photos id (stable even when the album gets reordered) and saved as
  WORKSPACE/media/<MMDD_HHMM>_<id6>.<mp4|jpg>   (local time, see --tz; photos may be HEIC inside .jpg)
State lives in WORKSPACE/manifest.json.
"""
import argparse, json, os, re, subprocess, sys, time, datetime as dt

ALBUM_URL = os.environ.get('VLOG_ALBUM') or sys.exit('Falta VLOG_ALBUM: el enlace compartido del álbum (variable del entorno)')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36'

def fetch_items(url):
    html = subprocess.run(['curl', '-sSL', '-A', UA, url], capture_output=True, text=True, check=True).stdout
    title = None; items = []
    for b in re.findall(r"AF_initDataCallback\((\{key: 'ds:\d+'.*?)\);</script>", html, re.S):
        m = re.search(r"key: '(ds:\d+)'.*?data:(.*), sideChannel", b, re.S)
        if not m or m.group(1) != 'ds:1':
            continue
        d = json.loads(m.group(2))
        try: title = d[3][1]
        except Exception: pass
        for it in d[1]:
            items.append(dict(id=it[0], url=it[1][0], w=it[1][1], h=it[1][2], ts=it[2],
                              video='76647426' in json.dumps(it)))
    if not items:
        sys.exit('No pude leer el álbum (¿el enlace sigue compartido? ¿el host está permitido en el entorno?)')
    return title, items

def local(ts, tz):
    return dt.datetime.fromtimestamp(ts / 1000, dt.timezone(dt.timedelta(hours=tz)))

def vsize(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                          '-of', 'csv=p=0', path], capture_output=True, text=True).stdout.strip()
    try: return max(int(x) for x in out.split(',') if x)
    except ValueError: return 0

def download(url, path):
    tmp = path + '.part'
    r = subprocess.run(['curl', '-sSL', '--retry', '3', '-o', tmp, url])
    if r.returncode == 0 and os.path.getsize(tmp) > 0:
        os.replace(tmp, path); return True
    if os.path.exists(tmp): os.remove(tmp)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('workspace'); ap.add_argument('cmd', choices=['list', 'pull', 'retry'])
    ap.add_argument('--from', dest='frm'); ap.add_argument('--to')
    ap.add_argument('--tz', type=float, default=7.0, help='horas respecto de UTC para nombrar (Tailandia = 7)')
    ap.add_argument('--rounds', type=int, default=20); ap.add_argument('--wait', type=int, default=120)
    a = ap.parse_args()
    W = a.workspace; os.makedirs(W + '/media', exist_ok=True)
    mpath = W + '/manifest.json'
    man = json.load(open(mpath)) if os.path.exists(mpath) else {}
    parse = lambda s: dt.datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone(dt.timedelta(hours=a.tz)))
    lo = parse(a.frm) if a.frm else None; hi = parse(a.to) if a.to else None

    def in_range(it):
        t = local(it['ts'], a.tz)
        return (lo is None or t >= lo) and (hi is None or t <= hi)

    if a.cmd in ('list', 'pull'):
        title, items = fetch_items(ALBUM_URL)
        sel = sorted([it for it in items if in_range(it)], key=lambda x: x['ts'])
        print(f'Álbum "{title}": {len(items)} elementos; {len(sel)} en el rango')
        for it in sel:
            t = local(it['ts'], a.tz)
            name = f"{t:%m%d_%H%M}_{it['id'][-6:]}." + ('mp4' if it['video'] else 'jpg')
            have = it['id'] in man
            if a.cmd == 'pull' and not have:
                ok = download(it['url'] + ('=dv' if it['video'] else '=d'), f'{W}/media/{name}')
                if not ok:
                    print('  FALLÓ', name); continue
                hd = (vsize(f'{W}/media/{name}') >= 1000) if it['video'] else True
                man[it['id']] = dict(file=name, video=it['video'], ts=it['ts'], hd=hd, url=it['url'])
                json.dump(man, open(mpath, 'w'), indent=1)
            e = man.get(it['id'])
            flag = '' if not e else ('' if e['hd'] else '  (BAJA RESOLUCIÓN: correr retry)')
            print(f"  {t:%d/%m %H:%M}  {'VID' if it['video'] else 'IMG'}  {name}{'' if e or a.cmd == 'list' else ''}{flag}")
    else:
        for rnd in range(1, a.rounds + 1):
            pend = [k for k, e in man.items() if e['video'] and not e['hd']]
            if not pend:
                print('Todo en HD'); return
            _, items = fetch_items(ALBUM_URL)           # urls change once Google finishes processing
            urls = {it['id']: it['url'] for it in items}
            for k in pend:
                e = man[k]; p = f"{W}/media/{e['file']}"; tmp = p + '.new'
                if download(urls.get(k, e['url']) + '=dv', tmp) and vsize(tmp) >= 1000:
                    os.replace(tmp, p); e['hd'] = True; print('HD', e['file'], flush=True)
                elif os.path.exists(tmp):
                    os.remove(tmp)
            json.dump(man, open(mpath, 'w'), indent=1)
            left = sum(1 for e in man.values() if e['video'] and not e['hd'])
            print(f'ronda {rnd}: faltan {left}', flush=True)
            if left == 0: return
            time.sleep(a.wait)

if __name__ == '__main__':
    main()
