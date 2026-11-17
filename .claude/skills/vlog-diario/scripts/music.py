# Original lo-fi style backing track: Rhodes-like chords, bass, soft drums.
import numpy as np, wave, sys
SR = 48000; BPM = 88; beat = 60 / BPM; bar = 4 * beat
dur = float(sys.argv[2]); n = int(SR * dur)
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(7)
def midi(m): return 440 * 2 ** ((m - 69) / 12)
def add(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR); j = min(n, i + len(sig))
    if i >= n: return
    s = sig[:j - i] * gain
    L[i:j] += s * (1 - pan) ; R[i:j] += s * (1 + pan)
def ep(m, length, vel=0.5):
    t = np.arange(int(SR * length)) / SR; f = midi(m)
    env = np.exp(-t * 2.2) * (1 - np.exp(-t * 200))
    trem = 1 + 0.15 * np.sin(2 * np.pi * 4.5 * t)
    s = (np.sin(2*np.pi*f*t) + 0.35*np.sin(2*np.pi*2*f*t)*np.exp(-t*4) + 0.12*np.sin(2*np.pi*3*f*t)*np.exp(-t*7))
    return s * env * trem * vel
def bass(m, length):
    t = np.arange(int(SR * length)) / SR; f = midi(m)
    env = np.minimum(1, t * 80) * np.exp(-t * 1.5) * np.minimum(1, (length - t) * 30).clip(0, 1)
    return (np.sin(2*np.pi*f*t) + 0.2*np.sin(2*np.pi*2*f*t)) * env * 0.55
def kick():
    t = np.arange(int(SR * 0.35)) / SR
    f = 50 + 70 * np.exp(-t * 30)
    return np.sin(2*np.pi*np.cumsum(f)/SR) * np.exp(-t * 9) * 0.9
def hat(open_=False):
    t = np.arange(int(SR * (0.18 if open_ else 0.06))) / SR
    s = rng.standard_normal(len(t)); s = np.diff(s, prepend=0)
    return s * np.exp(-t * (18 if open_ else 60)) * 0.08
def snare():
    t = np.arange(int(SR * 0.25)) / SR
    s = rng.standard_normal(len(t)) * np.exp(-t * 18) * 0.25 + np.sin(2*np.pi*190*t) * np.exp(-t*25) * 0.3
    return s
# Am9 - Fmaj7 - Cmaj7 - G6 (voicings)
chords = [[57, 60, 64, 67, 71], [53, 57, 60, 64, 67], [48, 55, 59, 64, 67], [55, 59, 62, 64, 69]]
roots = [45, 41, 48, 43]
melody = [[76, 74, 72, None], [72, None, 69, 67], [71, 72, None, 67], [69, None, 71, 74]]
t = 0.0; k = 0
while t < dur:
    c = chords[k % 4]
    for idx, m in enumerate(c):
        add(ep(m, bar * 1.1, 0.16), t + idx * 0.012, pan=(idx - 2) * 0.12)
    add(ep(c[1] + 12, beat * 1.5, 0.07), t + 2.5 * beat, pan=0.3)
    add(bass(roots[k % 4], beat * 1.8), t); add(bass(roots[k % 4], beat * 0.9), t + 2.5 * beat)
    add(bass(roots[k % 4] + 7, beat * 0.9), t + 3.5 * beat)
    if k >= 2:  # drums enter after intro
        add(kick(), t); add(kick(), t + 2.5 * beat, gain=0.8)
        add(snare(), t + beat); add(snare(), t + 3 * beat)
        for h in range(8):
            sw = 0.04 * beat if h % 2 else 0
            add(hat(h == 7), t + h * beat / 2 + sw, pan=0.25, gain=1.0 if h % 2 == 0 else 0.6)
    if k >= 4 and (k // 4) % 2 == 1:  # light melody every other phrase
        for q, m in enumerate(melody[k % 4]):
            if m: add(ep(m, beat * 1.2, 0.09), t + q * beat + 0.02, pan=-0.2)
    t += bar; k += 1
# vinyl noise + gentle low-pass
noise = rng.standard_normal(n) * 0.004
crackle = (rng.random(n) > 0.9997) * rng.standard_normal(n) * 0.15
L += noise + crackle; R += noise + crackle
st = np.stack([L, R], 1)
fade = int(SR * 2.5); st[:fade] *= np.linspace(0, 1, fade)[:, None]; st[-fade:] *= np.linspace(1, 0, fade)[:, None]
st = st / np.max(np.abs(st)) * 0.8
w = wave.open(sys.argv[1], 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close()
