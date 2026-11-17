#!/usr/bin/env python3
"""Transcribe clips (Spanish) with word timestamps.
usage: /opt/vlog-venv/bin/python -I transcribe.py WORKSPACE file1.mp4 [file2.mp4 ...]   (names inside WORKSPACE/media)
Writes WORKSPACE/transcripts/<name>.json and prints the text with times. Skips clips already done.
Model: large-v3-turbo (needs huggingface.co hosts; if a xethub host is refused, add it to the environment)."""
import sys, os, json, subprocess, numpy as np
W = sys.argv[1]; names = sys.argv[2:]
os.makedirs(W + '/transcripts', exist_ok=True); os.makedirs(W + '/models', exist_ok=True)
from faster_whisper import WhisperModel
m = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8', download_root=W + '/models')
for n in names:
    base = os.path.basename(n).rsplit('.', 1)[0]; out = f'{W}/transcripts/{base}.json'
    if not os.path.exists(out):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f'{W}/media/{os.path.basename(n)}', '-vn', '-ac', '1', '-ar', '16000',
                              '-f', 's16le', '-'], capture_output=True).stdout
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        segs, _ = m.transcribe(a, language='es', vad_filter=True, word_timestamps=True) if len(a) else ([], None)
        data = [dict(start=round(s.start, 2), end=round(s.end, 2), text=s.text.strip(),
                     words=[(round(w.start, 2), round(w.end, 2), w.word) for w in s.words]) for s in segs]
        json.dump(data, open(out, 'w'), ensure_ascii=False, indent=1)
    data = json.load(open(out))
    print(f'== {base}')
    for s in data:
        print(f"  [{s['start']:6.2f}-{s['end']:6.2f}] {s['text']}")
