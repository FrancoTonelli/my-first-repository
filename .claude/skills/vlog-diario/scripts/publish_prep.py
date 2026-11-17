#!/usr/bin/env python3
"""Make the phone version of a built day and a ready-to-publish page folder.
usage: python3 publish_prep.py WORKSPACE BUILD_NAME OUT_DIR --title 'Rumbo a Tailandia' --day 2
         [--route 'Bangkok|Templo|Khao San'] [--target-mb 180]
Result: OUT_DIR/index.html + OUT_DIR/poster.jpg + OUT_DIR/partNN.mp4 (14 MiB each).
Publish with the Artifact tool, root=OUT_DIR, capabilities {"downloads": true} on the first publish,
at most 4 parts per publish (64 MB limit). Under ~190 MB because the Claude Android app caps saves at 200 MiB."""
import argparse, os, subprocess, glob
ap = argparse.ArgumentParser()
ap.add_argument('ws'); ap.add_argument('build'); ap.add_argument('out')
ap.add_argument('--title', required=True); ap.add_argument('--day', required=True)
ap.add_argument('--route', default=''); ap.add_argument('--target-mb', type=float, default=180)
a = ap.parse_args()
B = f'{a.ws}/build_{a.build}'; os.makedirs(a.out, exist_ok=True)
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f'{B}/concat.mp4'],
                           capture_output=True, text=True).stdout)
vbr = min(6000, int((a.target_mb * 8e6 / dur - 170e3) / 1000))   # kbps, tope 6 Mbps
mob = f'{B}/movil.mp4'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{B}/concat.mp4', '-i', f'{B}/music_env.wav', '-filter_complex',
                f"[0:v]ass={B}/subs.ass[v];[0:a]loudnorm=I=-16:TP=-2:LRA=9[d];[d][1:a]amix=inputs=2:normalize=0:duration=first,"
                "alimiter=limit=0.89[a]", '-map', '[v]', '-map', '[a]', '-c:v', 'libx264', '-preset', 'medium',
                '-b:v', f'{vbr}k', '-maxrate', f'{int(vbr*1.8)}k', '-bufsize', f'{int(vbr*2.8)}k', '-profile:v', 'high',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-c:a', 'aac', '-b:a', '160k', mob], check=True)
for old in glob.glob(f'{a.out}/part*.mp4'): os.remove(old)
subprocess.run(['split', '-b', '14m', '-d', '-a', '2', '--numeric-suffixes=1', '--additional-suffix=.mp4', mob, f'{a.out}/part'], check=True)
parts = len(glob.glob(f'{a.out}/part*.mp4')); size = os.path.getsize(mob)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '1.6', '-i', mob, '-frames:v', '1', '-vf', 'scale=540:960', '-q:v', '4',
                f'{a.out}/poster.jpg'], check=True)
tpl = open(os.path.join(os.path.dirname(__file__), '..', 'assets', 'page_template.html')).read()
route = ' <span aria-hidden="true">→</span> '.join(x.strip() for x in a.route.split('|') if x.strip())
m, s = divmod(int(round(dur)), 60)
page = (tpl.replace('__PAGE_TITLE__', f'Día {a.day} · {a.title}').replace('__EYEBROW__', f'Vlog de viaje · Día {a.day}')
        .replace('__HEADLINE__', a.title).replace('__ROUTE__', route).replace('__DURATION__', f'{m}:{s:02d}')
        .replace('__PARTS__', str(parts)).replace('__BYTES__', str(size))
        .replace('__FILENAME__', f'Dia{a.day}_' + ''.join(c if c.isalnum() else '_' for c in a.title) + '.mp4'))
open(f'{a.out}/index.html', 'w').write(page)
print(f'{parts} partes, {size/1e6:.0f} MB, {m}:{s:02d} -> {a.out}')
