"""Estilo 2 — "Casey": vlog horizontal 1920x1080, inspirado en el ritmo de Casey Neistat.

Reutiliza de vlog.py: búsqueda de archivos, transcripciones, bip, tonemap HDR, recorte rembg.
Lo propio de este estilo:
  jump(...)    clip hablado recortado solo en sus silencios -> cortes secos (jump cuts)
  talk(...)    clip hablado entero (con overlays 'full'/'pip' mientras sigue la voz)
  broll(...)   toma de lugar: color con contraste, zoom lento; speed>1 = hyperlapse estabilizado
  photo(...)   foto con zoom lento
  En cualquiera: labels=[(t, dur, 'TEXTO', 'subtexto')] (abajo a la izquierda: hora, lugar, precio),
                 title=(t, dur, 'GRANDE', 'chico') (centrado), whip_in/whip_out (barrido + whoosh),
                 music='off'|'low'|'up' (forzar nivel), caps solo si no se entiende lo que dicen.
  Música: hip-hop instrumental (music_hiphop.py). Los bloques de tomas arrancan en el compás y sus
  duraciones se redondean al pulso, así los cortes caen en el beat.
"""
import os, sys, json, hashlib, math, wave, subprocess
import numpy as np
import vlog
from vlog import f, ph, run, dur, is_hdr, TONEMAP, achain, bleeps_for, mask_caption, ts, WORDS

W = vlog.W
CW, CH = 1920, 1080
BPM = 90
BEAT = 60 / BPM
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30',
       '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
ROT = {'180': 'hflip,vflip,', 'ccw': 'transpose=2,', 'cw': 'transpose=1,', None: ''}

# ---------------------------------------------------------------- helpers para los planes
def _base(kind, p, **kw):
    s = dict(kind=kind, caps=[], labels=[], title=None, whip_in=False, whip_out=False, music=None, rot=None, mode='auto')
    s.update(kw)
    if p is not None and 'src' not in s:
        s['src'] = f(p)
    for k in ('caps', 'labels'):
        s[k] = list(s[k])
    return s

def talk(p, i, o, **kw):
    kw.setdefault('overlays', [])
    kw['overlays'] = list(kw['overlays'])
    return _base('talk', p, i=i, o=o, **kw)

def _voiced(src, i, o, gap, margin_db=7.0):
    """Tramos con voz entre i y o (segundos del archivo). Mide la energía en la banda de la voz cada 50 ms y la
    compara con el piso de ruido del propio clip (percentil 15): sirve también en lugares ruidosos."""
    d = o - i
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{i:.3f}', '-t', f'{d:.3f}', '-i', src, '-vn', '-ac', '1',
                          '-ar', '16000', '-af', 'highpass=f=250,lowpass=f=3500', '-f', 's16le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 800
    if len(x) < hop * 4:
        return [[i, o]]
    fr = x[:len(x) // hop * hop].reshape(-1, hop)
    db = 10 * np.log10((fr ** 2).mean(1) + 1e-10)
    thr = np.percentile(db, 15) + margin_db
    on = db > thr
    out = []; start = None
    for k, v in enumerate(on):
        t = k * hop / 16000
        if v and start is None: start = t
        if not v and start is not None:
            out.append([i + start, i + t]); start = None
    if start is not None: out.append([i + start, o])
    merged = []
    for a2, b2 in out:
        if merged and a2 - merged[-1][1] < gap: merged[-1][1] = b2
        else: merged.append([a2, b2])
    return [r for r in merged if r[1] - r[0] > 0.15]

def jump(p, i, o, gap=0.45, pad=0.14, min_len=0.5, **kw):
    """Clip hablado recortado en sus silencios (según la transcripción). Devuelve una lista de segmentos.
    Los overlays/labels/caps se reparten en los pedazos según sus tiempos (en segundos del archivo)."""
    src = f(p); key = os.path.basename(src)[:-4]
    ws = [w for w in WORDS.get(key, []) if w[1] > i and w[0] < o]
    speech = [[a, b] for a, b, _ in ws] + _voiced(src, i, o, gap)
    speech.sort()
    runs = []
    for a, b in speech:
        if runs and a - runs[-1][1] < gap: runs[-1][1] = max(runs[-1][1], b)
        else: runs.append([a, b])
    rng = [(max(i, a - pad), min(o, b + pad)) for a, b in runs] or [(i, o)]
    merged = []
    for a, b in rng:
        if merged and a - merged[-1][1] < 0.25: merged[-1] = (merged[-1][0], b)
        else: merged.append((a, b))
    first = True; segs = []
    for a, b in merged:
        if b - a < min_len: continue
        s = talk(p, a, b, **{k: v for k, v in kw.items() if k not in ('title', 'labels', 'caps', 'overlays')})
        s['caps'] = [c for c in kw.get('caps', []) if c[1] > a and c[0] < b]
        s['overlays'] = [ov for ov in kw.get('overlays', []) if ov[1] < b and ov[2] > a]
        s['overlays'] = [(k, max(a, t0), min(b, t1),
                          dict(md, i=md['i'] + max(0.0, a - t0)) if md['kind'] == 'clip' else md)
                         for k, t0, t1, md in s['overlays']]   # si la superposición sigue en el pedazo siguiente, la toma continúa
        s['labels'] = []
        segs.append(s)  # labels se asignan abajo
        s['title'] = kw.get('title') if first else None
        s['whip_in'] = kw.get('whip_in', False) if first else False
        s['whip_out'] = False
        first = False
    for l in kw.get('labels', []):   # cada etiqueta va al primer pedazo que termina después de su tiempo (fuente)
        tgt = next((x for x in segs if x['o'] > l[0]), segs[-1] if segs else None)
        if tgt: tgt['labels'].append((max(0.0, l[0] - tgt['i']),) + tuple(l[1:]))
    if segs: segs[-1]['whip_out'] = kw.get('whip_out', False)
    return segs

# ---------------------------------------------------------------- calidad de imagen (para cortar bien las tomas)
def quality(src):
    """Por cada 1/6 s: nitidez (varianza del laplaciano), movimiento (diferencia entre cuadros) y brillo.
    Se cachea en VLOG_WS/quality/<clip>.json."""
    qd = W + '/quality'; os.makedirs(qd, exist_ok=True)
    out = f'{qd}/{os.path.basename(src)[:-4]}.json'
    if os.path.exists(out):
        return json.load(open(out))
    w, h = 160, 90
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', src, '-vf', f'fps=6,scale={w}:{h}:force_original_aspect_ratio=decrease,'
                          f'pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    lap = (-4 * fr[:, 1:-1, 1:-1] + fr[:, :-2, 1:-1] + fr[:, 2:, 1:-1] + fr[:, 1:-1, :-2] + fr[:, 1:-1, 2:])
    sharp = lap.reshape(len(fr), -1).var(1)
    mot = np.concatenate([[0], np.abs(np.diff(fr, axis=0)).reshape(len(fr) - 1, -1).mean(1)]) if len(fr) > 1 else np.zeros(1)
    bright = fr.reshape(len(fr), -1).mean(1)
    data = dict(fps=6, sharp=sharp.round(2).tolist(), motion=mot.round(2).tolist(), bright=bright.round(1).tolist())
    json.dump(data, open(out, 'w'))
    return data

def bad_spans(src, i=0.0, o=None):
    """Tramos feos (movidos, borrosos, muy oscuros o apuntando a cualquier lado) entre i y o."""
    q = quality(src); fps = q['fps']
    sh = np.array(q['sharp']); mo = np.array(q['motion']); br = np.array(q['bright'])
    if len(sh) < 3: return []
    bad = (sh < 0.35 * np.median(sh)) | (mo > max(3 * np.median(mo), 12)) | (br < 18)
    bad = np.convolve(bad.astype(float), np.ones(3) / 3, mode='same') > 0.5   # suaviza
    spans = []; start = None
    for k, b in enumerate(bad):
        t = k / fps
        if b and start is None: start = t
        if not b and start is not None: spans.append((start, t)); start = None
    if start is not None: spans.append((start, len(bad) / fps))
    o = o if o is not None else len(bad) / fps
    return [(max(a, i), min(b, o)) for a, b in spans if b > i and a < o and b - a >= 0.3]

def good_window(src, i, o, need=None):
    """Tramo limpio más largo dentro de [i, o] (o el primero que alcance para `need` segundos)."""
    t = i; best = (i, i)
    for a, b in bad_spans(src, i, o) + [(o, o)]:
        if a - t > best[1] - best[0]: best = (t, a)
        if need and a - t >= need: return (t, a)
        t = max(t, b)
    return best if best[1] - best[0] >= 0.6 else (i, o)

def broll(p, i, o=None, speed=1.0, vo=None, push=0.04, amb=0.2, quantize=True, clean=True, **kw):
    """Toma de lugar. o=None -> usa hasta el final útil. speed>1 = hyperlapse (dura (o-i)/speed).
    vo=(clave, t) pone la voz de ese clip de fondo. quantize redondea la duración al pulso de la música.
    clean=True recorta la toma a su tramo limpio más largo (sin sacudones, borrones ni cámara al piso);
    en hyperlapses no se recorta (el movimiento es la idea)."""
    src = f(p)
    if o is None: o = dur(src) - 0.05
    if clean and speed == 1 and not vo:
        i, o = good_window(src, i, o)
    d = (o - i) / speed
    if quantize and not vo:
        d = max(BEAT, round(d / BEAT) * BEAT)
    return _base('broll', p, i=i, d=round(d, 4), speed=speed, vo=vo, push=push, amb=amb, **kw)

def photo(p, d=None, vo=None, **kw):
    d = d or 2 * BEAT
    return _base('photo', None, src=ph(p), d=d, vo=vo, **kw)

def media(p, i=0.0, mode='auto', rot=None):
    if not f(p).endswith('.mp4'):
        return dict(kind='photo', src=ph(p))
    return dict(kind='clip', src=f(p), i=i, mode=mode, rot=rot)

def flat(plan):
    out = []
    for x in plan:
        out += x if isinstance(x, list) else [x]
    return out

# ---------------------------------------------------------------- video
_dims = {}
def display_is_portrait(src, rot):
    if src not in _dims:
        o = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                            'stream=width,height:stream_side_data=rotation', '-of', 'json', src], capture_output=True, text=True).stdout
        st = json.loads(o)['streams'][0]; w, h = st['width'], st['height']
        r = 0
        for sd in st.get('side_data_list', []):
            if 'rotation' in sd: r = abs(int(sd['rotation']))
        if r in (90, 270): w, h = h, w
        _dims[src] = (w, h)
    w, h = _dims[src]
    if rot in ('ccw', 'cw'): w, h = h, w
    return h > w

def vchain(idx, m, d, out='v', grade=False, push=0.0, speed=1.0, whip_in=False, whip_out=False, kind='talk'):
    src = m['src']; rot = ROT[m.get('rot')]
    tm = (',' + TONEMAP) if is_hdr(src) else ',format=yuv420p'
    sp = f'setpts=PTS/{speed},' if speed != 1 else ''
    mode = m.get('mode', 'auto')
    portrait = display_is_portrait(src, m.get('rot'))
    if mode == 'auto':   # vertical -> franja horizontal que llena la pantalla (nunca chiquito en el medio)
        mode = 'band' if portrait else 'fill'
    by = m.get('band_y', 0.5 if kind == 'broll' else 0.32)   # en clips hablados la cara suele estar arriba
    post = []
    if speed > 1.5:
        post.append('deshake=rx=48:ry=48:edge=mirror')
    if push:
        post.append(f"scale=w='trunc({CW}*(1+{push}*t/{d})/2)*2':h=-2:eval=frame,crop={CW}:{CH}")
    if grade:
        post.append('eq=contrast=1.12:saturation=1.07:gamma=0.97,unsharp=5:5:0.35')
    if whip_in or whip_out:
        T = 0.2; S = 230
        xs = (f"(iw-ow)/2+{S}*(-{int(whip_in)}*max(0,({T}-t)/{T})+{int(whip_out)}*max(0,(t-{d - T:.3f})/{T}))")
        en = '+'.join(x for x in ([f'lt(t,{T})'] if whip_in else []) + ([f'gt(t,{d - T:.3f})'] if whip_out else []))
        post.append(f"scale=2400:-2,crop={CW}:{CH}:x='{xs}':y=(ih-oh)/2,avgblur=sizeX=56:sizeY=1:enable='{en}'")
    post = (',' + ','.join(post)) if post else ''
    if mode == 'fill':
        return f"[{idx}:v]{sp}{rot}scale={CW}:{CH}:force_original_aspect_ratio=increase,crop={CW}:{CH}{tm}{post},setsar=1,fps=30[{out}]"
    if mode == 'band':  # franja horizontal del medio de una toma vertical
        return f"[{idx}:v]{sp}{rot}crop=iw:iw*9/16:0:(ih-iw*9/16)*{by},scale={CW}:{CH}{tm}{post},setsar=1,fps=30[{out}]"
    # pillar: vertical entero sobre su propio fondo desenfocado
    return (f"[{idx}:v]{sp}{rot}scale=-2:{CH}{tm},split[a{out}][b{out}];"
            f"[a{out}]scale={CW}:{CH}:force_original_aspect_ratio=increase,crop={CW}:{CH},gblur=sigma=45,eq=brightness=-0.1[bg{out}];"
            f"[bg{out}][b{out}]overlay=(W-w)/2:0{post},setsar=1,fps=30[{out}]")

def photo_chain(idx, d, out='v', whip_in=False, whip_out=False):
    c = (f"[{idx}:v]scale={CW}:{CH}:force_original_aspect_ratio=increase,crop={CW}:{CH},"
         f"scale=w='trunc({CW}*(1+0.06*t/{d})/2)*2':h=-2:eval=frame,crop={CW}:{CH},setsar=1,fps=30,format=yuv420p")
    if whip_in or whip_out:
        T = 0.2; S = 230
        xs = (f"(iw-ow)/2+{S}*(-{int(whip_in)}*max(0,({T}-t)/{T})+{int(whip_out)}*max(0,(t-{d - T:.3f})/{T}))")
        en = '+'.join(x for x in ([f'lt(t,{T})'] if whip_in else []) + ([f'gt(t,{d - T:.3f})'] if whip_out else []))
        c += f",scale=2400:-2,crop={CW}:{CH}:x='{xs}':y=(ih-oh)/2,avgblur=sizeX=56:sizeY=1:enable='{en}'"
    return c + f"[{out}]"

def seg_bleeps(src, i, o, a, b):
    d = b - a; res = []
    for x, y in bleeps_for(src, i, o):
        x0 = x + i - a; y0 = y + i - a
        if y0 > 0 and x0 < d: res.append((max(0, x0), min(d, y0)))
    return res

def render_talk(out, s, tmpdir):
    pieces = []; t = s['i']
    for kind, t0, t1, md in sorted(s['overlays'], key=lambda x: x[1]):
        if t0 > t: pieces.append(('plain', t, t0, None))
        pieces.append((kind, t0, t1, md)); t = t1
    if t < s['o']: pieces.append(('plain', t, s['o'], None))
    files = []
    for n, (kind, a, b, md) in enumerate(pieces):
        d = b - a; pf = f'{tmpdir}/{os.path.basename(out)[:-4]}_p{n}.mp4'
        wi = s['whip_in'] and n == 0; wo = s['whip_out'] and n == len(pieces) - 1
        af = achain(0, d, 1.0, seg_bleeps(s['src'], s['i'], s['o'], a, b))
        ins = ['-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', s['src']]
        if kind == 'plain':
            vf = vchain(0, s, d, whip_in=wi, whip_out=wo, kind='talk')
        else:
            if md['kind'] == 'photo':
                ins += ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', md['src']]
                bg = photo_chain(1, d, 'bg', wi, wo)
            else:
                ins += ['-ss', f"{md['i']:.3f}", '-t', f'{d:.3f}', '-i', md['src']]
                bg = vchain(1, md, d, 'bg', grade=True, push=0.04, whip_in=wi, whip_out=wo, kind='broll')
            if kind == 'full':
                vf = bg.replace('[bg]', '[v]')
            else:  # pip: ellos en un recuadro arriba a la derecha
                tm = (',' + TONEMAP) if is_hdr(s['src']) else ',format=yuv420p'
                vf = (bg + f";[0:v]{ROT[s.get('rot')]}scale='if(gt(iw,ih),560,300)':-2{tm},pad=iw+10:ih+10:5:5:white[fg];"
                      f"[bg][fg]overlay=W-w-50:50,setsar=1[v]")
        run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', vf + ';' + af, '-map', '[v]', '-map', '[a]',
             *ENC, '-t', f'{d:.3f}', pf])
        files.append(pf)
    if len(files) == 1:
        os.replace(files[0], out); return
    lst = out + '.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for p in files))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', out])

def render_broll(out, s):
    d = s['d']; srcdur = d * s['speed']
    vf = vchain(0, s, d, grade=True, push=s['push'] if s['speed'] == 1 else 0, speed=s['speed'],
                whip_in=s['whip_in'], whip_out=s['whip_out'], kind='broll')
    ins = ['-ss', f"{s['i']:.3f}", '-t', f'{srcdur:.3f}', '-i', s['src']]
    if s['vo']:
        vsrc = f(s['vo'][0]); st = s['vo'][1]
        ins += ['-ss', f'{st:.3f}', '-t', f'{d:.3f}', '-i', vsrc]
        af = achain(1, d, 1.0, seg_bleeps(vsrc, st, st + d, st, st + d), (), 'a')
    elif s['speed'] == 1:
        af = achain(0, d, s['amb'])
    else:
        ins += ['-f', 'lavfi', '-t', f'{d:.3f}', '-i', 'anullsrc=r=48000:cl=stereo']; af = '[1:a]anull[a]'
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', vf + ';' + af, '-map', '[v]', '-map', '[a]',
         *ENC, '-t', f'{d:.3f}', out])

def render_photo(out, s):
    d = s['d']
    ins = ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', s['src']]
    if s['vo']:
        vsrc = f(s['vo'][0]); st = s['vo'][1]
        ins += ['-ss', f'{st:.3f}', '-t', f'{d:.3f}', '-i', vsrc]
        af = achain(1, d, 1.0, seg_bleeps(vsrc, st, st + d, st, st + d))
    else:
        ins += ['-f', 'lavfi', '-t', f'{d:.3f}', '-i', 'anullsrc=r=48000:cl=stereo']; af = '[1:a]anull[a]'
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', photo_chain(0, d, 'v', s['whip_in'], s['whip_out']) + ';' + af,
         '-map', '[v]', '-map', '[a]', *ENC, '-t', f'{d:.3f}', out])

def render(s, outdir):
    key = hashlib.md5(json.dumps(s, sort_keys=True, default=str).encode()).hexdigest()[:12]
    out = f'{outdir}/{s["kind"]}_{key}.mp4'
    if not os.path.exists(out):
        {'talk': lambda: render_talk(out, s, outdir), 'broll': lambda: render_broll(out, s),
         'photo': lambda: render_photo(out, s)}[s['kind']]()
    return out

# ---------------------------------------------------------------- texto en pantalla
ASS_HEAD = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CW}
PlayResY: {CH}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,160,160,70,1
Style: Label,Inter Display Black,66,&H00FFFFFF,&H00FFFFFF,&H90000000,&H70000000,-1,0,0,0,100,100,2,0,1,2,3,1,90,90,80,1
Style: Title,Inter Display Black,170,&H00FFFFFF,&H00FFFFFF,&H90000000,&H70000000,-1,0,0,0,100,100,6,0,1,3,5,5,80,80,0,1
"""

def events_for(start, d, s):
    ev = []
    base = s.get('vo')[1] if s.get('vo') else s.get('i', 0)
    for a, b, text in s['caps']:
        a0 = max(start, start + a - base); b0 = min(start + d, start + b - base + 0.12)
        if b0 - a0 < 0.2: continue
        parts = text.split('|'); tot = sum(len(p) for p in parts); cur = a0
        for p in parts:
            e = cur + (b0 - a0) * len(p) / tot
            ev.append(f"Dialogue: 0,{ts(cur)},{ts(e)},Cap,,0,0,0,,{mask_caption(p.strip())}"); cur = e
    for l in s['labels']:
        o, ld, big = l[0], l[1], l[2]; small = l[3] if len(l) > 3 else ''
        txt = big.upper() + (f"\\N{{\\fs40\\fnInter}}{small}" if small else '')
        ev.append(f"Dialogue: 2,{ts(start + o)},{ts(min(start + d, start + o + ld))},Label,,0,0,0,,{{\\fad(150,200)}}{txt}")
    if s.get('title'):
        o, td, big = s['title'][:3]; small = s['title'][3] if len(s['title']) > 3 else ''
        txt = big.upper() + (f"\\N{{\\fs56\\fnInter\\b1}}{small}" if small else '')
        ev.append(f"Dialogue: 3,{ts(start + o)},{ts(start + o + td)},Title,,0,0,0,,{{\\fad(120,300)}}{txt}")
    return ev

# ---------------------------------------------------------------- música, whoosh, mezcla
LEVEL = dict(talk=0.11, broll=0.95, broll_vo=0.28, photo=0.95, photo_vo=0.28)
FORCED = dict(off=0.0, low=0.11, up=0.95)

def whoosh(sr=48000):
    n = int(0.42 * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(3); x = rng.standard_normal(n)
    out = np.zeros(n); y = 0.0
    for k in range(n):  # filtro pasa-bajos que se abre y se cierra
        fc = 300 + 5200 * math.sin(math.pi * t[k] / t[-1]) ** 2
        a = math.exp(-2 * math.pi * fc / sr); y = (1 - a) * x[k] + a * y; out[k] = y
    env = np.sin(np.pi * t / t[-1]) ** 1.5
    out = out * env; out /= np.max(np.abs(out)) + 1e-9
    pan = np.linspace(-0.7, 0.7, n)
    return np.stack([out * (1 - pan) * 0.5, out * (1 + pan) * 0.5], 1).astype(np.float32)

def used_ranges(s):
    """(archivo, desde, hasta) de todo el material que muestra un segmento."""
    r = []
    if s['kind'] == 'talk':
        r.append((s['src'], s['i'], s['o']))
        for k, t0, t1, md in s.get('overlays', []):
            if md['kind'] == 'clip': r.append((md['src'], md['i'], md['i'] + (t1 - t0)))
            else: r.append((md['src'], 0, 0))
    elif s['kind'] == 'broll':
        r.append((s['src'], s['i'], s['i'] + s['d'] * s['speed']))
    else:
        r.append((s['src'], 0, 0))
    return r

def check_repeats(plan):
    seen = []; warn = []
    for n, s in enumerate(plan):
        for src, a, b in used_ranges(s):
            for m, (src2, a2, b2) in seen:
                same_photo = a == b == 0 and a2 == b2 == 0 and src == src2
                if src == src2 and (same_photo or min(b, b2) - max(a, a2) > 0.3):
                    warn.append(f'  seg {m} y seg {n} repiten {os.path.basename(src)} [{max(a, a2):.1f}-{min(b, b2):.1f}]')
        seen += [(n, r) for r in used_ranges(s)]
    if warn:
        print('MATERIAL REPETIDO (evitarlo salvo que sea a propósito):'); print('\n'.join(warn))
    return warn

def build(plan, name, final, music=None):
    plan = flat(plan)
    check_repeats(plan)
    music = music or W + '/music_hiphop.wav'
    outdir = f'{W}/build_{name}'; os.makedirs(outdir, exist_ok=True)
    files = []
    for n, s in enumerate(plan):
        files.append(render(s, outdir)); print('seg', n, s['kind'], flush=True)
    t = 0.0; tl = []
    for s, p in zip(plan, files):
        d = dur(p); tl.append((t, d, s)); t += d
    total = t
    ev = []
    for start, d, s in tl: ev += events_for(start, d, s)
    open(f'{outdir}/subs.ass', 'w').write(ASS_HEAD + '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n' + '\n'.join(ev) + '\n')
    # música: se arma por tramos; cada bloque de tomas arranca en un compás nuevo de la pista
    w = wave.open(music); sr = w.getframerate()
    src = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    nT = int(total * sr) + sr
    mus = np.zeros((nT, 2), np.float32); env = np.zeros(nT, np.float32)
    clock = 0.0; bar = 4 * BEAT; prev = None; xf = int(0.03 * sr)
    for start, d, s in tl:
        k = s['kind'] + ('_vo' if s.get('vo') else '')
        lvl = FORCED.get(s.get('music'), LEVEL.get(k, 0.11))
        is_montage = s['kind'] in ('broll', 'photo') and not s.get('vo')
        if is_montage and prev != 'montage':
            clock = math.ceil(clock / bar) * bar
        a = int(start * sr); n = int(d * sr) + 1
        c0 = int(clock * sr) % (len(src) - n - 1)
        chunk = src[c0:c0 + n].copy()
        chunk[:xf] *= np.linspace(0, 1, xf)[:, None]
        mus[a:a + n] += chunk[:len(mus) - a]
        env[a:a + n] = lvl
        clock += d; prev = 'montage' if is_montage else 'other'
    k = int(0.25 * sr); env = np.convolve(env, np.ones(k) / k, mode='same')
    fo = int(3 * sr); end = int(total * sr); env[end - fo:end] *= np.linspace(1, 0, fo); env[end:] = 0
    mus = mus * env[:, None]
    wh = whoosh(sr)
    for (s0, d0, a), (s1, d1, b) in zip(tl, tl[1:]):
        if a.get('whip_out') and b.get('whip_in'):   # solo en cambios de lugar marcados de los dos lados
            p = int((s1 - 0.21) * sr); mus[p:p + len(wh)] += wh[:len(mus) - p] * 0.3
    mus = np.clip(mus, -1, 1)
    wo = wave.open(f'{outdir}/music_env.wav', 'wb'); wo.setnchannels(2); wo.setsampwidth(2); wo.setframerate(sr)
    wo.writeframes((mus * 32767).astype(np.int16).tobytes()); wo.close()
    open(f'{outdir}/list.txt', 'w').write(''.join(f"file '{p}'\n" for p in files))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{outdir}/list.txt', '-c', 'copy', f'{outdir}/concat.mp4'])
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{outdir}/concat.mp4', '-i', f'{outdir}/music_env.wav', '-filter_complex',
         f"[0:v]ass={outdir}/subs.ass[v];[0:a]loudnorm=I=-16:TP=-2:LRA=9[d];[d][1:a]amix=inputs=2:normalize=0:duration=first,"
         f"alimiter=limit=0.89[a]", '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
         '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', final])
    print('done', final, round(dur(final), 2))
    return tl
