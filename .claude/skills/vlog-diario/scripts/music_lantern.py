"""Pista original emotiva y luminosa para noches especiales (Yi Peng, faroles, momentos románticos). Sin derechos.
uso: /opt/vlog-venv/bin/python -I music_lantern.py SALIDA.wav SEGUNDOS [VARIANTE] [BPM]
Después: ffmpeg -i SALIDA.wav -af "loudnorm=I=-16:TP=-1.5" -ar 48000 music_hiphop.wav  y renderizar con VLOG_BPM=<BPM>.
Tonalidad mayor, progresión I–V–vi–IV y variantes, colchón de cuerdas, piano con arpegios, una melodía de marimba
(tipo ranat tailandés) con la escala pentatónica, campanitas, y una batería suave que entra de a poco y crece.
CONSONANTE por construcción: cada voz toca solo notas de la tríada que suena (sin séptimas, sin parciales
inarmónicos), la mezcla no se satura y el eco es corto."""
import numpy as np, wave, sys

SR = 48000
dur = float(sys.argv[2]); VAR = int(sys.argv[3]) if len(sys.argv) > 3 else 0
BPM = float(sys.argv[4]) if len(sys.argv) > 4 else 84.0
beat = 60 / BPM; bar = 4 * beat; s16 = beat / 4
n = int(SR * dur) + int(SR * bar * 2)
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(700 + VAR)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def T(sec): return np.arange(int(SR * sec)) / SR
def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i >= n or j <= i: return
    s = sig[:j - i] * gain
    L[i:j] += s * (1 - pan); R[i:j] += s * (1 + pan)

_c = {}
def strings(notes, length):     # colchón de cuerdas: tres osciladores apenas desafinados, ataque y salida lentos
    t = T(length); s = np.zeros(len(t))
    for m in notes:
        fr = midi(m)
        for det in (0.997, 1.0, 1.003):
            ph = 2 * np.pi * fr * det * t
            s += np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
    env = np.minimum(1, t / 1.2) * np.clip((length - t) / 1.0, 0, 1)
    return s * env * (1 + 0.04 * np.sin(2 * np.pi * 0.25 * t)) / (3 * len(notes)) * 0.20
def piano(m, length, vel):
    k = ('p', m, round(length, 3), vel)
    if k not in _c:
        t = T(length); fr = midi(m)
        s = np.sin(2 * np.pi * fr * t) + 0.45 * np.sin(4 * np.pi * fr * t) * np.exp(-t * 2) + \
            0.2 * np.sin(6 * np.pi * fr * t) * np.exp(-t * 4) + 0.08 * np.sin(8 * np.pi * fr * t) * np.exp(-t * 6)
        env = (1 - np.exp(-t * 400)) * np.exp(-t * 1.3) * np.clip((length - t) * 10, 0, 1)
        _c[k] = s * env * vel
    return _c[k]
def mallet(m, length):           # marimba / ranat: madera, armónico 4x (consonante: dos octavas)
    k = ('m', m, round(length, 3))
    if k not in _c:
        t = T(length); fr = midi(m)
        s = np.sin(2 * np.pi * fr * t) + 0.35 * np.sin(2 * np.pi * 4 * fr * t) * np.exp(-t * 30)
        _c[k] = s * (1 - np.exp(-t * 900)) * np.exp(-t * 5) * 0.20
    return _c[k]
def bell(m, length):             # campanita suave (armónicos 2x y 3x: octava y quinta)
    t = T(length); fr = midi(m)
    s = np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(4 * np.pi * fr * t) * np.exp(-t * 3) + 0.15 * np.sin(6 * np.pi * fr * t) * np.exp(-t * 5)
    return s * (1 - np.exp(-t * 600)) * np.exp(-t * 2.2) * 0.07
def bass(m, length):
    k = ('b', m, round(length, 3))
    if k not in _c:
        t = T(length); fr = midi(m)
        env = np.minimum(1, t * 60) * np.clip((length - t) * 12, 0, 1) * (0.7 + 0.3 * np.exp(-t * 2))
        _c[k] = (np.sin(2 * np.pi * fr * t) + 0.2 * np.sin(4 * np.pi * fr * t)) * env * 0.30
    return _c[k]
def kick():
    t = T(0.5); f = 45 + 55 * np.exp(-t * 20)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 5) * 0.55
def brush():
    t = T(0.18); s = rng.standard_normal(len(t)); s = np.convolve(s, np.ones(6) / 6, mode='same')
    return s * np.sin(np.pi * np.minimum(1, t / 0.18)) * np.exp(-t * 8) * 0.06
def snap():
    t = T(0.12); s = np.diff(rng.standard_normal(len(t)), prepend=0)
    return s * np.exp(-t * 45) * 0.10
def swell(length):               # subida de ruido filtrado antes de cada sección (sin tono: no choca)
    t = T(length); s = np.convolve(rng.standard_normal(len(t)), np.ones(30) / 30, mode='same')
    return s * (t / length) ** 2.5 * 0.10

KEY = 50 + ([0, 2, -2, 3, -3, 5][VAR % 6] if VAR else 0)    # re mayor por defecto
MAJ = [0, 2, 4, 5, 7, 9, 11]
def triad(d):
    return [MAJ[(d + 2 * j) % 7] + 12 * ((d + 2 * j) // 7) for j in range(3)]
PROGS = [[0, 4, 5, 3], [0, 5, 3, 4], [3, 4, 0, 5], [0, 3, 5, 4], [5, 3, 0, 4], [0, 4, 3, 4]]   # sin el disminuido
progA = PROGS[VAR % 6]; progB = PROGS[(VAR + 2) % 6]
rr = np.random.default_rng(1300 + VAR)
def phrase():                    # 2 compases; índices dentro de la tríada (0-5: raíz, 3a, 5a y su octava)
    out = []; pos = 0
    while pos < 32:
        ln = int(rr.choice([2, 2, 4, 4, 6, 8])); idx = int(rr.integers(0, 6))
        if rr.random() < 0.85: out.append((pos, idx, ln))
        pos += ln
    return out
MEL = [phrase(), phrase(), phrase()]
K_ = kick(); t = 0.0; k = 0
while t < dur + bar:
    sec = (k // 8) % 4           # 0: piano y cuerdas, 1: + marimba, 2: + batería suave, 3: todo + campanitas
    if k >= 32: sec = max(sec, 1)
    prog = progA if (k // 8) % 2 == 0 else progB
    dg = prog[(k % 8) // 2]; root = KEY + MAJ[dg]; CH = triad(dg)
    tones = [CH[0], CH[1], CH[2], CH[0] + 12, CH[1] + 12, CH[2] + 12]
    if k % 2 == 0:
        add(strings([KEY + 12 + x for x in CH] + [KEY + 24 + CH[0]], bar * 2 + 0.3), t)
        add(bass(root - 12, bar * 2 * 0.98), t)
        arp = [KEY + 24 + tones[i] for i in (0, 1, 2, 3, 2, 1, 4, 2)]
        for h in range(16 if sec >= 1 else 8):
            step = 2 if sec >= 1 else 4
            add(piano(arp[h % 8], beat * 1.4, 0.10 if h % 4 else 0.13), t + h * step * s16, pan=-0.15 + 0.3 * (h % 2))
        if sec >= 1:
            for p, idx, ln in MEL[(k // 2) % 3]:
                add(mallet(KEY + 36 + tones[idx], min(ln, 32 - p) * s16 * 0.95), t + p * s16, pan=0.25)
        if sec == 3:
            for p in (0, 12, 20):
                add(bell(KEY + 48 + tones[[0, 2, 1][p % 3]], beat * 2), t + p * s16, pan=-0.3)
    if sec >= 2 and k % 16 != 15:
        add(K_, t); add(K_, t + 2.5 * beat, gain=0.6)
        add(snap(), t + beat, pan=0.1); add(snap(), t + 3 * beat, pan=0.1)
        for h in range(8): add(brush(), t + h * beat / 2, pan=0.3, gain=1.0 if h % 2 == 0 else 0.6)
    if k % 8 == 7: add(swell(bar), t)
    t += bar; k += 1
d = int(SR * beat * 0.5)
for C, g in ((L, 0.08), (R, 0.10)):
    e = np.zeros_like(C); e[d:] = C[:-d] * g; C += e
st = np.stack([L, R], 1)[:int(SR * dur)]
fi = int(SR * 0.05); st[:fi] *= np.linspace(0, 1, fi)[:, None]
st = st / np.max(np.abs(st)) * 0.89
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
