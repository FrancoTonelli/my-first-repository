"""Mide, en el video final, el desfase voz/imagen de cada charla (contra el archivo original).
uso: VLOG_BPM=<bpm> VLOG_WS=$VLOG_WS VLOG_SKILL=$K /opt/vlog-venv/bin/python -I sync_check.py plan_diaN.py FINAL.mp4
La columna "voz" es la confiable (tiene que dar ~0,00). La de "imagen" falla en clips verticales enteros (fondo
desenfocado) o girados: ahí ignorarla. Correlaciones r < 0.3 son ruido (música alta, poca voz)."""
import sys, os, runpy, subprocess, numpy as np
sys.path.insert(0, os.environ['VLOG_SKILL']); import casey
plan_file, final = sys.argv[1], sys.argv[2]
g = runpy.run_path(plan_file); plan = casey.flat(g['PLAN'])
plan = [casey.snap_to_beat(s, plan[n+1] if n+1 < len(plan) else None) for n, s in enumerate(plan)]
def pcm(p, ss, t):
    return np.frombuffer(subprocess.run(['ffmpeg','-v','error','-ss',f'{max(0,ss):.3f}','-i',p,'-t',f'{t:.3f}','-vn','-ac','1','-ar','4000','-f','f32le','-'],capture_output=True).stdout, np.float32)
def fr(p, ss, t, rot=''):
    a = np.frombuffer(subprocess.run(['ffmpeg','-v','error','-ss',f'{max(0,ss):.3f}','-i',p,'-t',f'{t:.3f}','-vf','fps=30,scale=32:18,format=gray','-f','rawvideo','-'],capture_output=True).stdout, np.uint8)
    return a.reshape(-1, 576).astype(np.float32)
M = 0.8; T = 3.0; t = 0.0; worst = 0
for s in plan:
    d = casey.seg_len(s)
    if s['kind'] == 'talk' and not s.get('overlays') and d >= 4 and s['i'] >= M:
        fa = pcm(final, t + 0.5, T); sa = pcm(s['src'], s['i'] + 0.5 - M, T + 2*M)
        cs = [(np.corrcoef(fa, sa[k:k+len(fa)])[0,1], k/4000 - M) for k in range(0, len(sa)-len(fa), 8)]
        ra, oa = max(cs)
        fv = fr(final, t + 0.5, T); sv = fr(s['src'], s['i'] + 0.5 - M, T + 2*M)
        fv -= fv.mean(1, keepdims=True); sv -= sv.mean(1, keepdims=True); n = len(fv)
        ev = [(np.mean(np.abs(fv - sv[k:k+n])), k/30 - M) for k in range(0, len(sv)-n)]
        _, ov = min(ev)
        ds = oa - ov; worst = max(worst, abs(ds)) if ra > 0.5 else worst
        print(f't={t:7.1f} {os.path.basename(s["src"])[5:16]}  voz {oa:+.2f}s (r={ra:.2f})  imagen {ov:+.2f}s  desfase {ds:+.3f}s', flush=True)
    t += d
print('peor desfase (r>0.5):', round(worst, 3))
