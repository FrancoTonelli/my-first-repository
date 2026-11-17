"""Vertical travel-vlog engine (1080x1920) built on ffmpeg.

A plan is a list of segments built with the helpers below; `build(plan, ...)` renders,
captions, mixes music and exports. Features:
  talk(...)     clip with voices: auto-bleep of swear words, captions, overlays, curiosity cards
                overlays: ('full'|'pip'|'chroma', t0, t1, media) shown while the voice keeps going
  broll(...)    'artistic' shot: cinematic grade + slow push-in; music up; optional voice-over
  photo(...)    still with Ken Burns; optional voice-over
  blooper(...)  black & white + grain + radio voice + BLOOPER tag
"""
import subprocess, json, os, sys, re, glob, hashlib, wave
import numpy as np

W = os.environ.get('VLOG_WS') or sys.exit('Definí VLOG_WS (carpeta de trabajo del día)')
M = W + '/media/'
PY = '/opt/vlog-venv/bin/python'

# ---------------------------------------------------------------- helpers to write plans
def f(key):
    """Media file by unique name fragment (e.g. '1116_2055_a1b2c3', '2055_a1b2', or the id tail)."""
    hits = [M + x for x in sorted(os.listdir(M)) if key in x and not x.endswith('.part')]
    if len(hits) != 1:
        raise SystemExit(f'"{key}" coincide con {len(hits)} archivos: {[os.path.basename(h) for h in hits][:5]}')
    return hits[0]

def ph(key):
    """Upright JPG of a photo (run photos.py first)."""
    return W + '/ph/' + os.path.basename(f(key))

def media(p, i=0.0, mode='crop', rot=None, kb=True):
    """Something to show on screen: a clip (from second i) or a photo (ph/<p>.jpg)."""
    if not f(p).endswith('.mp4'):
        return dict(kind='photo', src=ph(p))
    return dict(kind='clip', src=f(p), i=i, mode=mode, rot=rot)

def talk(p, i, o, mode='portrait', rot=None, caps=(), title=None, overlays=(), cards=(), tags=(), vol=1.0):
    return dict(kind='talk', src=f(p), i=i, o=o, mode=mode, rot=rot, caps=list(caps), title=title,
                overlays=list(overlays), cards=list(cards), tags=list(tags), vol=vol, fx=[])

def blooper(p, i, o, mode='portrait', rot=None, caps=()):
    s = talk(p, i, o, mode, rot, caps, tags=[(None, 'BLOOPER')])
    s['fx'] = ['bw', 'radio']; s['kind'] = 'blooper'
    return s

def broll(p, i, o, mode='crop', rot=None, vo=None, caps=(), title=None, cards=(), tags=(), push=0.06, amb=0.25):
    """Artistic shot. vo=(clip_prefix, start) puts a voice under it for the shot's length."""
    return dict(kind='broll', src=f(p), i=i, o=o, mode=mode, rot=rot, vo=vo, caps=list(caps), title=title,
                cards=list(cards), tags=list(tags), push=push, amb=amb, fx=[])

def photo(p, d, vo=None, caps=(), title=None, cards=(), tags=()):
    return dict(kind='photo', src=ph(p), d=d, vo=vo, caps=list(caps), title=title,
                cards=list(cards), tags=list(tags), fx=[])

# ---------------------------------------------------------------- swear words / bleeps
SWEAR = re.compile(r'\b(put[ao]s?|mierda|pelotud[oa]s?|conchud[oa]s?|concha|carajo|forr[oa]s?|cagad[oa]|'
                   r'verga|pija|hdp|orto|cul(o|iado))\b', re.I)

def load_words():
    words = {}
    for fn in glob.glob(W + '/transcripts/*.json'):
        words[os.path.basename(fn)[:-5]] = [w for seg in json.load(open(fn)) for w in seg['words']]
    return words
WORDS = load_words()

def bleeps_for(src, i, o):
    key = os.path.basename(src)[:-4]
    out = []; ws = WORDS.get(key, [])
    for n, (a, b, w) in enumerate(ws):
        clean = w.strip().strip('¿?¡!.,…').lower()
        if SWEAR.fullmatch(clean) or (clean == 'madre' and n and ws[n-1][2].strip().lower().startswith('puta')):
            if b > i and a < o:
                out.append((max(0, a - i - 0.05), min(o - i, b - i + 0.08)))
    return out

def mask_caption(t):
    return SWEAR.sub(lambda m: m.group(0)[0] + '#@!', t)

# ---------------------------------------------------------------- ffmpeg building blocks
TONEMAP = ("zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,"
           "zscale=p=bt709,tonemap=mobius:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
ENC = ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', '30',
       '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-ac', '2']
_hdr = {}

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(' '.join(cmd)[:3000]); print(r.stderr[-3000:]); sys.exit(1)

def is_hdr(src):
    if src not in _hdr:
        out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                              'stream=color_transfer', '-of', 'csv=p=0', src], capture_output=True, text=True).stdout
        _hdr[src] = 'arib-std-b67' in out or 'smpte2084' in out
    return _hdr[src]

def dur(p):
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                capture_output=True, text=True).stdout)

def vchain(idx, m, d, fx=(), grade=False, push=0.0, out='v'):
    """Video of input idx -> 1080x1920 [out]. m = dict(src, mode, rot)."""
    rot = {'180': 'hflip,vflip,', 'ccw': 'transpose=2,', 'cw': 'transpose=1,', None: ''}[m.get('rot')]
    tm = (',' + TONEMAP) if is_hdr(m['src']) else ',format=yuv420p'
    post = []
    if push:
        post.append(f"scale=w='trunc(1080*(1+{push}*t/{d})/2)*2':h=-2:eval=frame,crop=1080:1920")
    if grade:
        post.append('eq=contrast=1.06:saturation=1.14:gamma=0.98,vignette=angle=PI/5')
    if 'bw' in fx:
        post.append('hue=s=0,eq=contrast=1.18:brightness=0.02,noise=alls=14:allf=t,vignette=angle=PI/4')
    post = (',' + ','.join(post)) if post else ''
    mode = m.get('mode', 'portrait')
    if mode == 'portrait':
        return f"[{idx}:v]{rot}scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920{tm}{post},setsar=1,fps=30[{out}]"
    if mode == 'crop':
        return f"[{idx}:v]{rot}scale=-2:1920,crop=1080:1920{tm}{post},setsar=1,fps=30[{out}]"
    # letterbox over a blurred fill of itself
    return (f"[{idx}:v]{rot}scale=1242:-2{tm},split[a{out}][b{out}];"
            f"[a{out}]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=40,eq=brightness=-0.08[bg{out}];"
            f"[b{out}]crop=1080:ih[fg{out}];[bg{out}][fg{out}]overlay=(W-w)/2:(H-h)/2{post},setsar=1,fps=30[{out}]")

def photo_chain(idx, d, out='v'):
    return (f"[{idx}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
            f"scale=w='trunc(1080*(1+0.07*t/{d})/2)*2':h=-2:eval=frame,crop=1080:1920,setsar=1,fps=30,format=yuv420p[{out}]")

def media_inputs(md, d):
    if md['kind'] == 'photo':
        return ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', md['src']]
    return ['-ss', f"{md['i']:.3f}", '-t', f'{d:.3f}', '-i', md['src']]

def achain(idx, d, vol=1.0, bleeps=(), fx=(), out='a'):
    c = f"[{idx}:a]volume={vol}"
    if bleeps:
        cond = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in bleeps)
        c += f",volume=enable='{cond}':volume=0"
    if 'radio' in fx:
        c += ",highpass=f=380,lowpass=f=3200,acompressor=threshold=-24dB:ratio=6:attack=5:release=80,volume=1.8,acrusher=bits=10:mix=0.25"
    c += f",afade=t=in:d=0.04,afade=t=out:st={max(0, d-0.06):.3f}:d=0.06"
    if bleeps:
        cond = '+'.join(f'between(t,{a:.3f},{b:.3f})' for a, b in bleeps)
        c += (f"[pre{out}];aevalsrc='0.22*sin(2*PI*1000*t)*({cond})':s=48000:d={d:.3f},aformat=channel_layouts=stereo[bp{out}];"
              f"[pre{out}][bp{out}]amix=inputs=2:normalize=0:duration=first")
    return c + f"[{out}]"

# ---------------------------------------------------------------- person cut-out (chroma)
def person_matte(src_proc, out_mask):
    """Grayscale matte video for a pre-rendered clip, using rembg (u2net_human_seg)."""
    if os.path.exists(out_mask):
        return
    code = f"""
import subprocess, numpy as np, os
os.environ['U2NET_HOME'] = {W + '/models/u2net'!r}
from rembg import remove, new_session
from PIL import Image
s = new_session('u2net_human_seg')
W, H = 540, 960
src = {src_proc!r}
p = subprocess.Popen(['ffmpeg','-v','error','-i',src,'-vf',f'scale={{W}}:{{H}}','-f','rawvideo','-pix_fmt','rgb24','-'], stdout=subprocess.PIPE)
o = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','gray','-s',f'{{W}}x{{H}}','-r','30','-i','-',
                      '-vf','gblur=sigma=1.5','-c:v','libx264','-crf','12','-pix_fmt','yuv420p',{out_mask!r}], stdin=subprocess.PIPE)
n = W*H*3
while True:
    b = p.stdout.read(n)
    if len(b) < n: break
    im = Image.frombytes('RGB', (W, H), b)
    m = remove(im, session=s, only_mask=True)
    o.stdin.write(np.asarray(m.convert('L')).tobytes())
o.stdin.close(); o.wait()
"""
    r = subprocess.run([PY, '-I', '-c', code], capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[-2000:]); sys.exit(1)

# ---------------------------------------------------------------- rendering
def seg_bleeps(seg, a, b):
    d = b - a; res = []
    for x, y in bleeps_for(seg['src'], seg['i'], seg['o']):
        x0 = x + seg['i'] - a; y0 = y + seg['i'] - a
        if y0 > 0 and x0 < d:
            res.append((max(0, x0), min(d, y0)))
    return res

def piece_overlay(out, seg, a, b, kind, md, tmp):
    d = b - a; bl = seg_bleeps(seg, a, b)
    ins = ['-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', seg['src']] + media_inputs(md, d)
    bg = photo_chain(1, d, 'bg') if md['kind'] == 'photo' else vchain(1, md, d, grade=True, push=0.05, out='bg')
    af = achain(0, d, seg.get('vol', 1.0), bl, seg['fx'])
    if kind == 'full':
        vf = bg.replace('[bg]', '[v]')
    elif kind == 'pip':
        rot = {'180': 'hflip,vflip,', 'ccw': 'transpose=2,', 'cw': 'transpose=1,', None: ''}[seg.get('rot')]
        tm = (',' + TONEMAP) if is_hdr(seg['src']) else ',format=yuv420p'
        vf = (bg + f";[0:v]{rot}scale='if(gt(iw,ih),640,420)':-2{tm},pad=iw+12:ih+12:6:6:white[fg];"
              f"[bg][fg]overlay=W-w-48:170,setsar=1[v]")
    else:  # chroma: speaker cut out over the media
        proc = f'{tmp}_spk.mp4'; mask = f'{tmp}_mask.mp4'
        if not os.path.exists(proc):
            run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', seg['src'], '-filter_complex',
                 vchain(0, dict(seg, mode='portrait' if seg['mode'] == 'portrait' else 'fitw'), d).replace('[v]', '[v]')
                 if seg['mode'] == 'portrait' else
                 f"[0:v]{'' if not seg.get('rot') else {'180': 'hflip,vflip,', 'ccw': 'transpose=2,', 'cw': 'transpose=1,'}[seg['rot']]}"
                 f"scale=1080:-2{(',' + TONEMAP) if is_hdr(seg['src']) else ',format=yuv420p'},"
                 f"pad=1080:1920:0:1920-ih:black,setsar=1,fps=30[v]",
                 '-map', '[v]', '-an', '-c:v', 'libx264', '-crf', '14', '-pix_fmt', 'yuv420p', proc])
        person_matte(proc, mask)
        ins = ['-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', seg['src']] + media_inputs(md, d) + ['-i', proc, '-i', mask]
        vf = (bg + ";[3:v]scale=1080:1920,format=gray[m];[2:v][m]alphamerge[fg];"
              "[bg][fg]overlay=0:0:format=auto,format=yuv420p,setsar=1[v]")
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', vf + ';' + af, '-map', '[v]', '-map', '[a]',
         *ENC, '-t', f'{d:.3f}', out])

def render_talk(out, seg, tmpdir):
    cuts = sorted(seg['overlays'], key=lambda x: x[1])
    pieces = []; t = seg['i']
    for kind, t0, t1, md in cuts:
        if t0 > t: pieces.append(('plain', t, t0, None))
        pieces.append((kind, t0, t1, md)); t = t1
    if t < seg['o']: pieces.append(('plain', t, seg['o'], None))
    files = []
    for n, (kind, a, b, md) in enumerate(pieces):
        pf = f'{tmpdir}/{os.path.basename(out)[:-4]}_p{n}.mp4'
        if kind == 'plain':
            d = b - a; bl = seg_bleeps(seg, a, b)
            vf = vchain(0, seg, d, fx=seg['fx']); af = achain(0, d, seg.get('vol', 1.0), bl, seg['fx'])
            run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-t', f'{d:.3f}', '-i', seg['src'],
                 '-filter_complex', vf + ';' + af, '-map', '[v]', '-map', '[a]', *ENC, '-t', f'{d:.3f}', pf])
        else:
            piece_overlay(pf, seg, a, b, kind, md, pf[:-4])
        files.append(pf)
    lst = out + '.txt'; open(lst, 'w').write(''.join(f"file '{p}'\n" for p in files))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', out])

def render_broll(out, seg):
    d = seg['o'] - seg['i']
    vf = vchain(0, seg, d, grade=True, push=seg['push'])
    if seg['vo']:
        src = f(seg['vo'][0]); st = seg['vo'][1]
        vseg = dict(src=src, i=st, o=st + d)
        bl = [(max(0, x), min(d, y)) for x, y in bleeps_for(src, st, st + d)]
        ins = ['-ss', f"{seg['i']:.3f}", '-t', f'{d:.3f}', '-i', seg['src'], '-ss', f'{st:.3f}', '-t', f'{d:.3f}', '-i', src]
        af = (achain(1, d, 1.0, bl, (), 'vo') + ';' + f"[0:a]volume={seg['amb'] * 0.5}[amb];[vo][amb]amix=inputs=2:normalize=0:duration=first[a]")
    else:
        ins = ['-ss', f"{seg['i']:.3f}", '-t', f'{d:.3f}', '-i', seg['src']]
        af = achain(0, d, seg['amb'])
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', vf + ';' + af, '-map', '[v]', '-map', '[a]',
         *ENC, '-t', f'{d:.3f}', out])

def render_photo(out, seg):
    d = seg['d']
    if seg['vo']:
        src = f(seg['vo'][0]); st = seg['vo'][1]
        bl = [(max(0, x), min(d, y)) for x, y in bleeps_for(src, st, st + d)]
        ins = ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', seg['src'], '-ss', f'{st:.3f}', '-t', f'{d:.3f}', '-i', src]
        af = achain(1, d, 1.0, bl)
    else:
        ins = ['-loop', '1', '-framerate', '30', '-t', f'{d:.3f}', '-i', seg['src'], '-f', 'lavfi', '-t', f'{d:.3f}',
               '-i', 'anullsrc=r=48000:cl=stereo']
        af = '[1:a]anull[a]'
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', photo_chain(0, d) + ';' + af, '-map', '[v]', '-map', '[a]',
         *ENC, '-t', f'{d:.3f}', out])

def render(seg, outdir):
    key = hashlib.md5(json.dumps(seg, sort_keys=True, default=str).encode()).hexdigest()[:12]
    out = f'{outdir}/{seg["kind"]}_{key}.mp4'
    if not os.path.exists(out):
        if seg['kind'] in ('talk', 'blooper'): render_talk(out, seg, outdir)
        elif seg['kind'] == 'broll': render_broll(out, seg)
        else: render_photo(out, seg)
    return out

# ---------------------------------------------------------------- captions / titles / cards (ASS)
def ts(x):
    return f'{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}'

ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,90,90,430,1
Style: Title,Inter Display Black,110,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,1,0,1,6,3,8,60,60,250,1
Style: Card,Inter,52,&H00FFFFFF,&H00FFFFFF,&H001B61C8,&H001B61C8,-1,0,0,0,100,100,0,0,3,18,0,7,70,140,330,1
Style: Tag,Inter Display Black,46,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,-1,0,0,0,100,100,4,0,3,14,0,7,60,60,120,1
"""

def captions_for(start, d, seg):
    ev = []
    if seg['kind'] in ('talk', 'blooper'):
        base = seg['i']
    elif seg.get('vo'):
        base = seg['vo'][1]
    else:
        base = seg.get('i', 0)
    for a, b, text in seg['caps']:
        a0 = max(start, start + a - base); b0 = min(start + d, start + b - base + 0.15)
        parts = text.split('|'); tot = sum(len(p) for p in parts); cur = a0
        for p in parts:
            e = cur + (b0 - a0) * len(p) / tot
            ev.append(f"Dialogue: 0,{ts(cur)},{ts(e)},Cap,,0,0,0,,{mask_caption(p.strip())}"); cur = e
    if seg.get('title'):
        o, td, small, big = seg['title']
        ev.append(f"Dialogue: 1,{ts(start + o)},{ts(start + o + td)},Title,,0,0,0,,"
                  f"{{\\fad(250,350)\\fs54\\c&H3FD7FF&}}{small}\\N{{\\fs118\\c&HFFFFFF&}}{big}")
    for c in seg.get('cards', []):
        # (t from segment start, duration, header, text) -- slides in from the left
        o, cd, head, text = c
        ev.append(f"Dialogue: 2,{ts(start + o)},{ts(start + o + cd)},Card,,0,0,0,,"
                  f"{{\\fad(200,250)\\move(-400,330,70,330,0,260)}}{{\\fs38\\c&HD8F1FF&}}{head}\\N{{\\fs52\\c&HFFFFFF&}}{text}")
    for t in seg.get('tags', []):
        o, label = (0, t[1]) if t[0] is None else t[:2]
        td = d if t[0] is None else t[2]
        ev.append(f"Dialogue: 3,{ts(start + o)},{ts(start + o + td)},Tag,,0,0,0,,{{\\fad(120,120)}}{label}")
    return ev

# ---------------------------------------------------------------- music + mix + export
MUSIC_LEVEL = dict(talk=0.14, blooper=0.0, broll=0.9, broll_vo=0.32, photo=0.85, photo_vo=0.3)

def build(plan, name, final, music=None, bitrate=None):
    music = music or W + '/music.wav'
    outdir = f'{W}/build_{name}'; os.makedirs(outdir, exist_ok=True)
    files = []
    for n, seg in enumerate(plan):
        files.append(render(seg, outdir)); print('seg', n, seg['kind'], flush=True)
    t = 0.0; tl = []
    for seg, p in zip(plan, files):
        d = dur(p); tl.append((t, d, seg)); t += d
    total = t
    ev = []
    for start, d, seg in tl: ev += captions_for(start, d, seg)
    open(f'{outdir}/subs.ass', 'w').write(ASS_HEAD + '\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n' + '\n'.join(ev) + '\n')
    w = wave.open(music); sr = w.getframerate()
    mus = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2).astype(np.float32) / 32768
    nT = int(total * sr) + sr
    if len(mus) < nT: mus = np.concatenate([mus] * (nT // len(mus) + 1))
    mus = mus[:nT]; env = np.zeros(len(mus), np.float32)
    for start, d, seg in tl:
        k = seg['kind'] + ('_vo' if seg.get('vo') else '')
        env[int(start * sr):int((start + d) * sr)] = MUSIC_LEVEL.get(k, 0.14)
    k = int(0.35 * sr); env = np.convolve(env, np.ones(k) / k, mode='same')
    fo = int(2.5 * sr); end = int(total * sr); env[end - fo:end] *= np.linspace(1, 0, fo); env[end:] = 0
    mus = np.clip(mus * env[:, None], -1, 1)
    wo = wave.open(f'{outdir}/music_env.wav', 'wb'); wo.setnchannels(2); wo.setsampwidth(2); wo.setframerate(sr)
    wo.writeframes((mus * 32767).astype(np.int16).tobytes()); wo.close()
    open(f'{outdir}/list.txt', 'w').write(''.join(f"file '{p}'\n" for p in files))
    run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', f'{outdir}/list.txt', '-c', 'copy', f'{outdir}/concat.mp4'])
    venc = ['-b:v', bitrate, '-maxrate', '6M', '-bufsize', '9M'] if bitrate else ['-crf', '20']
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{outdir}/concat.mp4', '-i', f'{outdir}/music_env.wav', '-filter_complex',
         f"[0:v]ass={outdir}/subs.ass[v];[0:a]loudnorm=I=-16:TP=-2:LRA=9[d];[d][1:a]amix=inputs=2:normalize=0:duration=first,"
         f"alimiter=limit=0.89[a]", '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium', *venc,
         '-profile:v', 'high', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', final])
    print('done', final, round(dur(final), 2))
    return tl
