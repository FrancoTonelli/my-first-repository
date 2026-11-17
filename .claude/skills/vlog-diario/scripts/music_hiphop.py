"""Pista original de hip-hop instrumental (boom bap) a 90 BPM para el estilo Casey.
uso: /opt/vlog-venv/bin/python -I music_hiphop.py SALIDA.wav SEGUNDOS
Después: ffmpeg -i SALIDA.wav -af "loudnorm=I=-16:TP=-1.5" -ar 48000 music_hiphop.wav
Batería desde el primer compás (los montajes empiezan en cualquier compás), acordes de piano eléctrico,
bajo, hi-hats con swing y una variación cada 8 compases."""
import numpy as np, wave, sys

SR = 48000; BPM = 90; beat = 60 / BPM; bar = 4 * beat
dur = float(sys.argv[2]); n = int(SR * dur)
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(11)

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

# Dm9 - G13 - Cmaj9 - Am7(11)
chords = [[50, 57, 60, 64, 65], [43, 53, 59, 64, 65], [48, 55, 59, 62, 64], [45, 52, 55, 60, 62]]
roots = [38, 31, 36, 33]
K, S_ = kick(), snare()
t = 0.0; k = 0
while t < dur:
    c = chords[k % 4]; r = roots[k % 4]
    for idx, m in enumerate(c[1:]):
        add(keys(m + 12, bar * 1.05, 0.13), t + idx * 0.008, pan=(idx - 1.5) * 0.15)
    add(keys(c[2] + 12, beat, 0.07), t + 2.5 * beat, pan=0.3)
    # bajo
    add(bass(r, beat * 1.4), t); add(bass(r, beat * 0.5), t + 1.75 * beat)
    add(bass(r + 7 if k % 2 else r + 12, beat * 0.9), t + 2.5 * beat)
    # batería boom bap: bombo 1, 1.75(&a), 3.5 ; caja 2 y 4
    add(K, t); add(K, t + 1.75 * beat, gain=0.7); add(K, t + 2.5 * beat, gain=0.9)
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
