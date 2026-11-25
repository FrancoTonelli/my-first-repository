"""Pista original cálida y melódica (deep / afro house tranquilo) para el estilo Casey. Sintetizada acá: sin derechos.
Hecha a partir de la referencia que mandó el usuario (tema de ~112 BPM en sol# menor, mucho grave y sub-bajo, poca
percusión, líneas melódicas sostenidas en los medios, agudos suaves).
uso: /opt/vlog-venv/bin/python -I music_chill.py SALIDA.wav SEGUNDOS [VARIANTE] [BPM]
Después: ffmpeg -i SALIDA.wav -af "loudnorm=I=-15:TP=-1.5" -ar 48000 music_hiphop.wav  y renderizar con VLOG_BPM=<BPM>."""
import numpy as np, wave, sys

SR = 48000
dur = float(sys.argv[2]); VAR = int(sys.argv[3]) if len(sys.argv) > 3 else 0
BPM = float(sys.argv[4]) if len(sys.argv) > 4 else 112.0
beat = 60 / BPM; bar = 4 * beat; s16 = beat / 4
n = int(SR * dur) + int(SR * bar * 2)
L = np.zeros(n); R = np.zeros(n); SC = np.ones(n)
rng = np.random.default_rng(500 + VAR)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def T(sec): return np.arange(int(SR * sec)) / SR
def add(sig, t0, pan=0.0, gain=1.0, duck=True):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i >= n or j <= i: return
    s = sig[:j - i] * gain * (SC[i:j] if duck else 1)
    L[i:j] += s * (1 - pan); R[i:j] += s * (1 + pan)

def kick():
    t = T(0.45); f = 42 + 70 * np.exp(-t * 25)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5.5) * 0.5
def rim():
    t = T(0.08); return (np.sin(2 * np.pi * 1700 * t) * 0.5 + rng.standard_normal(len(t)) * 0.3) * np.exp(-t * 70) * 0.26
def hat():
    t = T(0.06); return np.diff(rng.standard_normal(len(t)), prepend=0) * np.exp(-t * 70) * 0.16
def shaker():
    t = T(0.12); return rng.standard_normal(len(t)) * np.sin(np.pi * t / 0.12) ** 2 * 0.09
def tom(m):
    t = T(0.4); f = midi(m) * (1 + 0.25 * np.exp(-t * 18))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 0.22
_c = {}
def sub(m, length):   # sub-bajo redondo con un poco de saturación
    k = ('s', m, round(length, 3))
    if k not in _c:
        t = T(length); fr = midi(m)
        env = np.minimum(1, t * 80) * np.clip((length - t) * 20, 0, 1) * (0.75 + 0.25 * np.exp(-t * 3))
        _c[k] = np.tanh((np.sin(2 * np.pi * fr * t) + 0.25 * np.sin(4 * np.pi * fr * t)) * env * 1.6) * 0.17
    return _c[k]
def keys(m, length, vel):   # piano eléctrico cálido (tipo Rhodes)
    k = ('k', m, round(length, 3), vel)
    if k not in _c:
        t = T(length); fr = midi(m)
        s = np.sin(2 * np.pi * fr * t + 0.8 * np.sin(2 * np.pi * fr * t) * np.exp(-t * 3))
        s += 0.2 * np.sin(2 * np.pi * 2 * fr * t) * np.exp(-t * 2)
        env = (1 - np.exp(-t * 200)) * np.exp(-t * 1.1) * np.clip((length - t) * 8, 0, 1)
        _c[k] = s * env * (1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)) * vel
    return _c[k]
def pad(notes, length):   # colchón suave, ataque lento
    t = T(length); s = np.zeros(len(t))
    for m in notes:
        fr = midi(m); s += np.sin(2 * np.pi * fr * t) + np.sin(2 * np.pi * fr * 1.003 * t) + 0.3 * np.sin(2 * np.pi * 2 * fr * t)
    env = np.minimum(1, t / 0.8) * np.clip((length - t) / 0.6, 0, 1)
    return s * env / len(notes) * 0.22
def pluck(m, length):   # punteo corto y brillante (tipo marimba/kalimba)
    k = ('p', m, round(length, 3))
    if k not in _c:
        t = T(length); fr = midi(m)
        s = np.sin(2 * np.pi * fr * t) + 0.5 * np.sin(2 * np.pi * 3 * fr * t) * np.exp(-t * 25) + 0.25 * np.sin(2 * np.pi * 5.4 * fr * t) * np.exp(-t * 40)
        _c[k] = s * (1 - np.exp(-t * 900)) * np.exp(-t * 9) * 0.13
    return _c[k]
def lead(m, length):   # línea melódica sostenida, tipo flauta/sintetizador suave, con vibrato
    t = T(length); fr = midi(m) * (1 + 0.007 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t * 2))
    ph = np.cumsum(fr) / SR
    s = np.sin(2 * np.pi * ph) + 0.3 * np.sin(4 * np.pi * ph) + 0.12 * np.sin(6 * np.pi * ph)
    env = np.minimum(1, t * 12) * np.clip((length - t) * 6, 0, 1)
    return s * env * 0.30

KEY = 44 + ([0, -2, 3, -4, 5, 2][VAR % 6] if VAR else 0)          # sol#2 por defecto (como la referencia)
NAT = [0, 2, 3, 5, 7, 8, 10]                     # menor natural: acordes diatónicos (sin notas fuera de la tonalidad)
def chord_of(d):   # grado (0-6) -> notas del acorde por terceras dentro de la escala, relativas a la tónica
    return [NAT[(d + 2 * j) % 7] + 12 * ((d + 2 * j) // 7) for j in range(4)]
PROGS = [[0, 5, 2, 6], [0, 3, 5, 4], [0, 6, 5, 2], [0, 2, 6, 5], [0, 5, 6, 3], [0, 4, 5, 6]]
progA = PROGS[VAR % 6]; progB = PROGS[(VAR + 2) % 6]
MIN = [0, 3, 7, 10, 14]
SCALE = [0, 2, 3, 5, 7, 8, 10, 12, 14, 15]
rr = np.random.default_rng(900 + VAR)
def phrase():   # frase de 2 compases: notas largas, pocas, que respiran
    out = []; pos = 0
    while pos < 32:
        ln = int(rr.choice([4, 6, 8, 12])); deg = int(rr.integers(2, 9))
        if rr.random() < 0.8: out.append((pos, SCALE[deg], ln))
        pos += ln
    return out
MEL = [phrase(), phrase()]
BASS = [(0, 0, 6), (6, 0, 2), (10, 7, 2), (12, 12, 2), (14, 10, 2)] if VAR % 2 == 0 else \
       [(0, 0, 4), (6, 0, 2), (8, 7, 4), (14, 5, 2)]
PERC = [3, 6, 11, 14] if VAR % 3 == 0 else ([3, 7, 10, 14] if VAR % 3 == 1 else [2, 6, 11, 13])
K_ = kick(); t = 0.0; k = 0
while t < dur + bar:
    sec = (k // 8) % 4                    # 0: entra suave, 1: + melodía, 2: B, 3: B + melodía y percusión
    prog = progA if sec < 2 else progB
    dg = prog[(k % 8) // 2]; root = KEY + NAT[dg]; CH = chord_of(dg)
    soft = (k < 2) or (k % 16 == 15)      # respiro: sin bombo
    if not soft:
        for q in range(4):
            i = int((t + q * beat) * SR); j = min(n, i + int(beat * SR))
            if i < n: SC[i:j] = np.minimum(SC[i:j], 0.55 + 0.45 * np.minimum(1, np.arange(j - i) / (SR * beat * 0.6)))
        for q in range(4): add(K_, t + q * beat, duck=False)
    for h in range(16):
        sw = 0.06 * s16 if h % 2 else 0
        if h % 2 == 1: add(hat(), t + h * s16 + sw, pan=0.3, gain=1.0 if h % 4 == 2 else 0.6)
        if sec >= 1 and h % 2 == 0: add(shaker(), t + h * s16, pan=-0.3)
    for h in PERC: add(rim(), t + h * s16, pan=0.2)
    if sec == 3:
        for h, m in [(6, 52), (10, 49), (15, 47)]: add(tom(m), t + h * s16, pan=-0.4)
    BMAP = {0: 0, 5: CH[1] - CH[0], 7: CH[2] - CH[0], 10: CH[3] - CH[0], 12: 12}   # grados del bajo dentro del acorde
    for h, deg, ln in BASS: add(sub(root - 12 + BMAP[deg], ln * s16 * 0.95), t + h * s16)
    if k % 2 == 0:
        ch = [KEY + 12 + x for x in CH] + [KEY + 24 + CH[0]]
        add(pad(ch, bar * 2), t, pan=0.0)
        for idx, m in enumerate(ch[:3]): add(keys(m + 12, beat * 1.5, 0.30), t + 2 * s16 + idx * 0.012, pan=-0.2)
        for idx, m in enumerate(ch[:3]): add(keys(m + 12, beat * 1.2, 0.24), t + bar + 10 * s16 + idx * 0.012, pan=-0.2)
        if sec in (1, 3):
            for p, deg, ln in MEL[(k // 2) % 2]:
                add(lead(KEY + 24 + deg, ln * s16 * 0.97), t + p * s16, pan=0.15)
    if k >= 2:
        c0 = [x - CH[0] for x in CH]; arp = [root + 24 + x for x in (0, c0[2], 12, 12 + c0[1], c0[3], c0[2], c0[1], c0[2])]
        for h in range(8):
            add(pluck(arp[h], s16 * 1.8), t + h * 2 * s16 + (0.05 * s16 if h % 2 else 0), pan=0.35 * (1 if h % 2 else -1), gain=0.9 if h % 2 == 0 else 0.6)
    t += bar; k += 1
# eco suave (corchea con puntillo) para que suene más amplio
d = int(SR * beat * 0.75)
for C, g in ((L, 0.22), (R, 0.26)):
    e = np.zeros_like(C); e[d:] = C[:-d] * g; e[2 * d:] += C[:-2 * d] * g * 0.5; C += e
st = np.stack([L, R], 1)[:int(SR * dur)]
st[:int(SR * 0.02)] *= np.linspace(0, 1, int(SR * 0.02))[:, None]
st = np.tanh(st / np.max(np.abs(st)) * 1.3) / np.tanh(1.3) * 0.9
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
