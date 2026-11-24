"""Pista original con más onda (funk / disco house) para el estilo Casey. Todo sintetizado acá: sin derechos.
uso: /opt/vlog-venv/bin/python -I music_funk.py SALIDA.wav SEGUNDOS [VARIANTE] [BPM]
Después: ffmpeg -i SALIDA.wav -af "loudnorm=I=-15:TP=-1.5" -ar 48000 music_hiphop.wav   (el motor busca ese nombre)
y renderizar con VLOG_BPM=<BPM> (por defecto 118) para que los cortes caigan en el beat.
Bombo en negras con "pumping", palmas en 2 y 4, hats en semicorcheas, bajo funky sincopado, acordes cortados (stabs),
vientos, un riff pegadizo y cortes/subidas cada 16 compases. VARIANTE cambia tonalidad, progresión, groove y riff."""
import numpy as np, wave, sys

SR = 48000
dur = float(sys.argv[2]); VAR = int(sys.argv[3]) if len(sys.argv) > 3 else 0
BPM = float(sys.argv[4]) if len(sys.argv) > 4 else 118.0
beat = 60 / BPM; bar = 4 * beat; s16 = beat / 4
n = int(SR * dur) + SR
L = np.zeros(n); R = np.zeros(n); SC = np.ones(n)      # SC: envolvente de sidechain (pumping)
rng = np.random.default_rng(1000 + VAR)

def midi(m): return 440 * 2 ** ((m - 69) / 12)
def T(sec): return np.arange(int(SR * sec)) / SR

def add(sig, t0, pan=0.0, gain=1.0, duck=True, buf=None):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i >= n or j <= i: return
    s = sig[:j - i] * gain
    if duck: s = s * SC[i:j]
    L[i:j] += s * (1 - pan); R[i:j] += s * (1 + pan)

# ---------- instrumentos
def kick():
    t = T(0.38); f = 48 + 110 * np.exp(-t * 32)
    b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    return np.tanh((b + rng.standard_normal(len(t)) * np.exp(-t * 500) * 0.3) * 2.0) * 0.9
def clap():
    t = T(0.3); nz = rng.standard_normal(len(t))
    env = sum((t >= k * 0.009) * np.exp(-np.maximum(0, t - k * 0.009) * (90 if k < 3 else 22)) for k in range(4))
    bp = np.diff(nz, prepend=0) - 0.6 * np.diff(np.diff(nz, prepend=0), prepend=0)
    return bp * env * 0.33
def hat(open_=False):
    t = T(0.28 if open_ else 0.045); s = np.diff(rng.standard_normal(len(t)), prepend=0)
    return s * np.exp(-t * (11 if open_ else 95)) * 0.13
def shaker():
    t = T(0.09); s = rng.standard_normal(len(t)); return s * np.sin(np.pi * t / 0.09) ** 2 * 0.05
def conga(m):
    t = T(0.25); f = midi(m) * (1 + 0.3 * np.exp(-t * 40))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14) * 0.35
_bass = {}
def bass(m, length):
    k = (m, round(length, 3))
    if k not in _bass:
        t = T(length); fr = midi(m)
        # slap: ataque con armónicos que se cierran rápido (filtro que baja) + cuerpo redondo
        harm = sum(np.sin(2 * np.pi * fr * h * t) / h * np.exp(-t * (6 + 9 * h)) for h in range(2, 9))
        body = np.sin(2 * np.pi * fr * t) + 0.35 * np.sin(2 * np.pi * 2 * fr * t) * np.exp(-t * 4)
        env = np.minimum(1, t * 400) * np.exp(-t * 2.2) * np.clip((length - t) * 60, 0, 1)
        _bass[k] = np.tanh((body + 1.4 * harm) * env * 1.3) * 0.62
    return _bass[k]
_stab = {}
def stab(notes, length, bright=1.0):
    k = (tuple(notes), round(length, 3), bright)
    if k not in _stab:
        t = T(length); s = np.zeros(len(t))
        for m in notes:
            fr = midi(m)
            for h in range(1, 7):   # serrucho filtrado: armónicos que decaen (más brillo = más armónicos)
                s += np.sin(2 * np.pi * fr * h * t * (1 + 0.0015 * (h % 2))) / h * np.exp(-t * (3 + 6 * h / bright))
        env = np.minimum(1, t * 600) * np.clip((length - t) * 50, 0, 1)
        _stab[k] = s * env / len(notes) * 0.42
    return _stab[k]
def brass(notes, length):
    t = T(length); s = np.zeros(len(t))
    for m in notes:
        fr = midi(m); vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t * 4)
        for h in range(1, 9):
            s += np.sin(2 * np.pi * fr * h * np.cumsum(vib) / SR) / h ** 1.15 * (1 - np.exp(-t * (30 / h)))
    env = np.minimum(1, t * 35) * np.clip((length - t) * 30, 0, 1) * (0.8 + 0.2 * np.exp(-t * 6))
    return np.tanh(s * env / len(notes) * 0.9) * 0.24
def lead(m, length):
    t = T(length); fr = midi(m) * (1 + 0.006 * np.sin(2 * np.pi * 6 * t) * np.minimum(1, t * 3))
    ph = np.cumsum(fr) / SR
    sq = np.sign(np.sin(2 * np.pi * ph)) * 0.5 + np.sin(2 * np.pi * ph) * 0.5
    env = np.minimum(1, t * 300) * np.exp(-t * 3) * np.clip((length - t) * 40, 0, 1)
    return sq * env * 0.12
def riser(length):
    t = T(length); nz = rng.standard_normal(len(t))
    sweep = np.sin(2 * np.pi * np.cumsum(300 + 4000 * (t / length) ** 2) / SR)
    return (nz * 0.5 * (t / length) ** 2 + sweep * 0.15 * (t / length)) * 0.35

# ---------- material por variante
KEY = 33 + [0, 5, 2, 7, 3, 10][VAR % 6]            # La1 + transpuesto
PROGS = [[0, 5, 3, 7], [0, 8, 3, 10], [0, 3, 5, 8], [0, 10, 8, 7], [0, 5, 10, 3], [0, 7, 8, 5]]
progA = PROGS[VAR % 6]; progB = PROGS[(VAR + 3) % 6]
MINOR7 = [0, 3, 7, 10, 14]
BASSPAT = [  # (semicorchea, grado relativo, largo en 16avos)
    [(0, 0, 2), (3, 12, 1), (4, 0, 1), (6, 7, 1), (8, 0, 2), (10, 10, 1), (11, 12, 1), (14, 7, 2)],
    [(0, 0, 3), (3, 0, 1), (6, 12, 1), (7, 10, 1), (8, 7, 2), (11, 0, 1), (12, 3, 2), (14, 5, 2)],
    [(0, 0, 1), (2, 12, 1), (3, 0, 1), (6, 0, 2), (8, 7, 1), (10, 10, 1), (12, 12, 1), (13, 10, 1), (14, 7, 2)],
][VAR % 3]
STABPAT = [[2, 6, 10, 14], [3, 6, 11, 14], [2, 7, 10, 13, 15]][(VAR // 3 + VAR) % 3]
rr = np.random.default_rng(77 + VAR)
PENT = [0, 3, 5, 7, 10, 12, 15]
RIFF = [(int(p), int(rr.integers(0, len(PENT))), l) for p, l in
        [(0, 2), (3, 1), (4, 2), (6, 2), (10, 1), (11, 2), (14, 2)][:int(rr.integers(5, 8))]]

K_, C_ = kick(), clap()
t = 0.0; k = 0
while t < dur + bar:
    sec = (k // 8) % 4                 # 0: groove, 1: + vientos y riff, 2: B (otra progresión), 3: B + todo
    prog = progA if sec in (0, 1) else progB
    root = KEY + prog[(k % 8) // 2]
    brk = (k % 16 == 15)               # compás de corte antes de cada vuelta (sin bombo, con subida)
    # sidechain: cada negra baja el resto y vuelve
    if not brk:
        for q in range(4):
            i = int((t + q * beat) * SR); j = min(n, i + int(beat * SR))
            if i < n: SC[i:j] = np.minimum(SC[i:j], 0.35 + 0.65 * np.minimum(1, np.arange(j - i) / (SR * beat * 0.55)))
    # batería
    for q in range(4):
        if not brk: add(K_, t + q * beat, gain=1.0, duck=False)
        if q % 2 == 1: add(C_, t + q * beat, gain=0.9 if not brk else 0.6, duck=False)
    for h in range(16):
        sw = 0.08 * s16 if h % 2 else 0
        if h % 4 == 2: add(hat(True), t + h * s16 + sw, pan=0.25, gain=0.9)
        else: add(hat(), t + h * s16 + sw, pan=0.3, gain=1.0 if h % 2 == 0 else 0.55)
        if sec >= 1 and h % 2 == 1: add(shaker(), t + h * s16 + sw, pan=-0.35)
    if sec in (1, 3):
        for h, m in [(3, 64), (6, 69), (11, 64), (14, 71)]: add(conga(m), t + h * s16, pan=-0.4, gain=0.8)
    # bajo
    if not brk:
        for h, deg, ln in BASSPAT:
            add(bass(root + deg, ln * s16 * 0.95), t + h * s16, pan=0.0, gain=1.0)
    else:
        add(bass(root, beat * 1.5), t)
    # acordes cortados
    chord = [root + 24 + x for x in MINOR7[1:4]] + [root + 12]
    for h in STABPAT:
        add(stab(chord, s16 * 1.6, 1.4 if sec >= 2 else 1.0), t + h * s16, pan=0.2, gain=1.0)
    # vientos: un golpe en el 1 y otro al final de cada 2 compases
    if sec in (1, 3) and k % 2 == 0:
        add(brass([root + 24, root + 31, root + 36], beat * 0.9), t, pan=-0.15)
        add(brass([root + 27, root + 34, root + 39], s16 * 1.5), t + bar - 2 * s16 + bar, pan=-0.15)
    # riff
    if sec in (1, 3) and k % 4 in (0, 2):
        for h, deg, ln in RIFF:
            add(lead(KEY + 36 + PENT[deg], ln * s16 * 1.1), t + h * s16, pan=0.3)
    if brk: add(riser(bar), t, duck=False, gain=0.9)
    t += bar; k += 1

st = np.stack([L, R], 1)[:int(SR * dur)]
st[:int(SR * 0.01)] *= np.linspace(0, 1, int(SR * 0.01))[:, None]
st = np.tanh(st / np.max(np.abs(st)) * 1.6) / np.tanh(1.6) * 0.9     # un poco de saturación: más "pegada"
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
