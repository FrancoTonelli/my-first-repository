"""Usa una canción que pasa el usuario como música del video, alineada al beat del motor.
uso: /opt/vlog-venv/bin/python -I music_from_track.py CANCION.mp3 SALIDA.wav SEGUNDOS [BPM_MOTOR]
- Mide el tempo y la fase de los beats (librosa), la estira apenas (atempo) al BPM del motor (por defecto el entero
  más cercano) y la recorta para que el primer beat caiga en t=0: así los cortes del video (múltiplos del pulso)
  caen en el beat de la canción.
- Si el video es más largo, la repite empalmando en un múltiplo de 16 pulsos (4 compases) antes del final,
  con un fundido corto. Después: loudnorm y renderizar con VLOG_BPM=<BPM_MOTOR>.
Imprime el BPM original y el usado. La canción es del usuario: el video es privado; si lo publican, ojo derechos."""
import sys, subprocess, numpy as np, wave, librosa

src, out, secs = sys.argv[1], sys.argv[2], float(sys.argv[3])
SR = 48000
def load(path, extra=''):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '2', '-ar', str(SR)] +
                         (['-af', extra] if extra else []) + ['-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2)

y = load(src).mean(1)
tempo, beats = librosa.beat.beat_track(y=librosa.resample(y, orig_sr=SR, target_sr=22050), sr=22050, units='time')
period = float(np.median(np.diff(beats))); bpm0 = 60 / period
bpm = float(sys.argv[4]) if len(sys.argv) > 4 else round(bpm0)
ratio = bpm / bpm0
x = load(src, f'atempo={ratio:.6f}')
P = 60 / bpm
bt = np.array(beats) / ratio
phase = float(np.median(bt % P))                       # dónde cae el pulso dentro de cada período
start = phase if phase < P else 0.0
mono = np.abs(x).mean(1)
env = np.convolve(mono, np.ones(SR // 2) / (SR // 2), mode='same')
loud = np.where(env > env.max() * 0.05)[0]
end_t = loud[-1] / SR - 2.0                            # antes del fundido final de la canción
nbeats = int((end_t - start) / P) // 16 * 16
seg = x[int(start * SR):int((start + nbeats * P) * SR)]
fx = int(0.25 * SR)
reps = int(np.ceil(secs / (nbeats * P))) + 1
parts = [seg]
for _ in range(reps - 1):
    nxt = seg.copy()
    fade = np.linspace(0, 1, fx)[:, None]
    parts[-1] = parts[-1].copy(); parts[-1][-fx:] *= (1 - fade)
    nxt[:fx] *= fade
    parts.append(nxt)
mix = np.concatenate(parts)[:int(secs * SR)]
mix = mix / max(1e-9, np.abs(mix).max()) * 0.9
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype(np.int16).tobytes()); w.close()
print(f'BPM original {bpm0:.2f} -> {bpm} (x{ratio:.4f}); primer beat {start:.3f}s; vuelta de {nbeats} pulsos '
      f'({nbeats * P:.1f}s), {reps} vueltas')
