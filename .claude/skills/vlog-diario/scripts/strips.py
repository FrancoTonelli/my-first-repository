#!/usr/bin/env python3
"""Contact sheets to review footage: one row of 8 frames per video, photos as a grid.
usage: python3 strips.py WORKSPACE OUT_PREFIX name1 [name2 ...]  -> OUT_PREFIX_1.png, _2.png ... (max 11 rows each)
Read the PNGs with the Read tool. Frames are auto-rotated like the edit will be (HDR looks flat; that's fine)."""
import sys, os, subprocess, tempfile
W, pre = sys.argv[1], sys.argv[2]; names = [os.path.basename(n) for n in sys.argv[3:]]
tmp = tempfile.mkdtemp(); rows = []
def run(c): subprocess.run(c, check=True)
for n in names:
    p = f'{W}/media/{n}'; label = n.rsplit('.', 1)[0]; r = f'{tmp}/{label}.png'
    if n.endswith('.mp4'):
        d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                 capture_output=True, text=True).stdout)
        run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-vf', f"fps={8/d},scale=150:150:force_original_aspect_ratio=decrease,"
             "pad=150:150:(ow-iw)/2:(oh-ih)/2,drawtext=text='%{pts\\:hms}':x=2:y=138:fontsize=10:fontcolor=yellow:box=1:boxcolor=black,"
             "tile=8x1", '-frames:v', '1', '-update', '1', f'{tmp}/t.png'])
    else:
        src = f'{W}/ph/{n}' if os.path.exists(f'{W}/ph/{n}') else p
        run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', 'scale=150:150:force_original_aspect_ratio=decrease,'
             'pad=1200:150:(150-iw)/2:(150-ih)/2', '-frames:v', '1', f'{tmp}/t.png'])
    run(['ffmpeg', '-v', 'error', '-y', '-i', f'{tmp}/t.png', '-vf',
         f"pad=iw+150:ih:150:0,drawtext=text='{label}':x=2:y=65:fontsize=11:fontcolor=white", r])
    rows.append(r)
for k in range(0, len(rows), 11):
    chunk = rows[k:k + 11]; out = f'{pre}_{k // 11 + 1}.png'
    ins = sum([['-i', r] for r in chunk], [])
    run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', f'vstack=inputs={len(chunk)}' if len(chunk) > 1 else 'null', out])
    print(out)
