"""Pista original de hip-hop instrumental (boom bap) a 90 BPM para el estilo Casey.
uso: /opt/vlog-venv/bin/python -I music_hiphop.py SALIDA.wav SEGUNDOS [VARIANTE]
VARIANTE (entero, por defecto 0 = la pista original): cambia progresión, tonalidad, instrumento, ritmo y melodía,
siempre a 90 BPM (los cortes del motor siguen cayendo en el beat). Usar el número del día para que cada video suene distinto.
Después: ffmpeg -i SALIDA.wav -af "loudnorm=I=-16:TP=-1.5" -ar 48000 music_hiphop.wav
Batería desde el primer compás (los montajes empiezan en cualquier compás), acordes de piano eléctrico,
bajo, hi-hats con swing y una variación cada 8 compases."""
import numpy as np, wave, sys

SR = 48000; BPM = 90; beat = 60 / BPM; bar = 4 * beat
dur = float(sys.argv[2]); n = int(SR * dur)
VAR = int(sys.argv[3]) if len(sys.argv) > 3 else 0
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(11 + VAR * 101)

def midi(m): return 440 * 2 ** ((m - 69) / 12)

def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i >= n or j <= i: return
    s = sig[:j - i] * gain
    L[i:j] += s * (1 - pan); R[i:j] += s * (1 + pan)

def keys(m, length, vel):
    t = np.arange(int(SR * length)) / SR; fr = midi(m)
    env = np.exp(-t * 1.8) * (1 - np.exp(-t * 300))
    s = np.sin(2*np.pi*fr*t) + 0.3*np.sin(2*np.pi*2*fr*t)*np.exp(-t*5) + 0.15*np.sin(2*np.pi*3*fr*t)*np.exp(-t*9)
    return s * env * (1 + 0.1 * np.sin(2 * np.pi * 5 * t)) * vel

_PL = {}
def pluck(m, length, vel):
    """Cuerda punteada (Karplus-Strong), tipo guitarra limpia. Cacheada por nota."""
    key = (m, round(length, 3))
    if key not in _PL:
        fr = midi(m); N = max(2, int(SR / fr)); total = int(SR * min(length, 1.6))
        x = np.zeros(total); x[:N] = rng.uniform(-1, 1, N)
        y = np.zeros(total)
        for i0 in range(0, total, N):             # y[n] = x[n] + 0.497 (y[n-N] + y[n-N-1]), por bloques de N
            i1 = min(total, i0 + N)
            prev = y[i0 - N:i1 - N] if i0 >= N else np.zeros(i1 - i0)
            prev1 = y[i0 - N - 1:i1 - N - 1] if i0 >= N + 1 else np.concatenate([np.zeros(1), prev[:-1]])
            y[i0:i1] = x[i0:i1] + 0.497 * (prev + prev1)
        _PL[key] = y * 1.4
    return _PL[key] * vel

def bell(m, length, vel):
    """Vibráfono suave."""
    t = np.arange(int(SR * length)) / SR; fr = midi(m)
    s = np.sin(2*np.pi*fr*t) + 0.25*np.sin(2*np.pi*4*fr*t)*np.exp(-t*6)
    return s * np.exp(-t * 2.5) * (1 - np.exp(-t * 500)) * (1 + 0.25*np.sin(2*np.pi*6*t)) * vel

def pad(m, length, vel):
    """Colchón cálido (dos osciladores desafinados, ataque lento)."""
    t = np.arange(int(SR * length)) / SR; fr = midi(m)
    s = np.sin(2*np.pi*fr*t) + np.sin(2*np.pi*fr*1.004*t) + 0.3*np.sin(2*np.pi*2*fr*t)
    env = np.minimum(1, t / 0.35) * np.clip((length - t) / 0.3, 0, 1)
    return s * env * vel * 0.55

def bass(m, length):
    t = np.arange(int(SR * length)) / SR; fr = midi(m)
    env = np.minimum(1, t * 120) * np.exp(-t * 1.2) * np.clip((length - t) * 25, 0, 1)
    return (np.sin(2*np.pi*fr*t) + 0.25*np.sin(2*np.pi*2*fr*t)) * env * 0.75

def kick():
    t = np.arange(int(SR * 0.45)) / SR
    fr = 45 + 95 * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 7)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.25
    return np.tanh((body + click) * 1.6) * 0.95

def snare():
    t = np.arange(int(SR * 0.35)) / SR
    noise = rng.standard_normal(len(t)); noise = np.diff(noise, prepend=0) * 0.6 + noise * 0.4
    tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.5
    clap = sum(rng.standard_normal(len(t)) * np.exp(-np.maximum(0, t - k * 0.011) * 60) * (t >= k * 0.011)
               for k in range(3)) * 0.15
    return np.tanh((noise * np.exp(-t * 16) * 0.55 + tone + clap) * 1.4) * 0.8

def hat(open_=False):
    t = np.arange(int(SR * (0.22 if open_ else 0.05))) / SR
    s = np.diff(rng.standard_normal(len(t)), prepend=0)
    return s * np.exp(-t * (14 if open_ else 80)) * 0.11

# Progresiones (A y B) por variante. 0 = la original: Dm9 - G13 - Cmaj9 - Am7(11)
PROGS = [
    ([[50, 57, 60, 64, 65], [43, 53, 59, 64, 65], [48, 55, 59, 62, 64], [45, 52, 55, 60, 62]], [38, 31, 36, 33]),
    ([[45, 52, 55, 59, 60], [41, 48, 52, 55, 57], [43, 50, 53, 57, 59], [40, 47, 50, 55, 56]], [33, 29, 31, 28]),  # Am9 Fmaj9 G6 E7
    ([[48, 55, 59, 62, 64], [45, 52, 55, 59, 60], [41, 48, 52, 55, 57], [43, 50, 53, 57, 62]], [36, 33, 29, 31]),  # Cmaj9 Am9 Fmaj9 G9
    ([[47, 54, 57, 61, 62], [43, 50, 54, 57, 59], [45, 52, 55, 59, 62], [42, 49, 52, 57, 59]], [35, 31, 33, 30]),  # Bm9 Gmaj7 A6 F#m7
    ([[52, 59, 62, 66, 67], [48, 55, 59, 62, 64], [50, 57, 60, 64, 66], [47, 54, 57, 62, 64]], [40, 36, 38, 35]),  # Em9 Cmaj9 D6 Bm7
]
v = VAR % len(PROGS)
progA, rootsA = PROGS[v]
progB, rootsB = PROGS[(v + 2) % len(PROGS)] if VAR else PROGS[v]
shift = 0 if VAR == 0 else [0, -2, 1, -1, 2][VAR % 5]
INSTR = [keys, pluck, bell, pad, keys][VAR % 5] if VAR else keys
KICKS = [(0, 1.75, 2.5), (0, 0.75, 2.5), (0, 2.25, 2.75), (0, 1.5, 2.5), (0, 0.5, 2.25)][VAR % 5] if VAR else (0, 1.75, 2.5)
SCALE = [0, 3, 5, 7, 10, 12, 15]                  # pentatónica menor
mel_rng = np.random.default_rng(500 + VAR)
MOTIF = [(float(b), int(mel_rng.integers(0, len(SCALE))), float(l)) for b, l in
         [(0, 0.75), (0.75, 0.5), (1.5, 1.0), (2.5, 0.5), (3.0, 1.0)][:int(mel_rng.integers(3, 6))]]
K, S_ = kick(), snare()
t = 0.0; k = 0
while t < dur:
    sec_b = VAR and (k // 8) % 2 == 1            # cada 8 compases cambia de sección
    prog, roots = (progB, rootsB) if sec_b else (progA, rootsA)
    c = [m + shift for m in prog[k % 4]]; r = roots[k % 4] + shift
    vel = 0.13 if INSTR is keys else (0.07 if INSTR is pluck else 0.10)
    for idx, m in enumerate(c[1:]):
        add(INSTR(m + 12, bar * 1.05, vel), t + idx * (0.008 if INSTR is not pluck else 0.045), pan=(idx - 1.5) * 0.15)
    add(INSTR(c[2] + 12, beat, vel * 0.55), t + 2.5 * beat, pan=0.3)
    # melodía corta en la sección B (solo variantes nuevas)
    if sec_b and k % 2 == 0:
        for b0, deg, ln in MOTIF:
            add(bell(r + 36 + SCALE[deg], beat * ln * 1.3, 0.05), t + b0 * beat, pan=-0.25)
    # bajo
    add(bass(r, beat * 1.4), t); add(bass(r, beat * 0.5), t + 1.75 * beat)
    add(bass(r + 7 if k % 2 else r + 12, beat * 0.9), t + 2.5 * beat)
    # batería boom bap: caja 2 y 4; el bombo cambia por variante
    for j, kb in enumerate(KICKS):
        add(K, t + kb * beat, gain=[1.0, 0.7, 0.9][j])
    if k % 8 == 7: add(K, t + 3.5 * beat, gain=0.8)
    add(S_, t + beat); add(S_, t + 3 * beat)
    for h in range(8):
        sw = 0.055 * beat if h % 2 else 0
        add(hat(h == 7 and k % 2 == 1), t + h * beat / 2 + sw, pan=0.3, gain=1.0 if h % 2 == 0 else 0.55)
    t += bar; k += 1
noise = rng.standard_normal(n) * 0.003 + (rng.random(n) > 0.99975) * rng.standard_normal(n) * 0.12
L += noise; R += noise
st = np.stack([L, R], 1)
st[:int(SR * 0.02)] *= np.linspace(0, 1, int(SR * 0.02))[:, None]
st = st / np.max(np.abs(st)) * 0.85
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
