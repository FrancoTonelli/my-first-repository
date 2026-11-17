#!/usr/bin/env python3
"""Convert album photos (JPEG or iPhone HEIC saved as .jpg) to upright JPGs for the edit.
usage: /opt/vlog-venv/bin/python -I photos.py WORKSPACE name1.jpg [name2.jpg ...]  -> WORKSPACE/ph/<name>.jpg"""
import sys, os, pillow_heif
from PIL import Image, ImageOps
pillow_heif.register_heif_opener()
W = sys.argv[1]; os.makedirs(W + '/ph', exist_ok=True)
for n in sys.argv[2:]:
    n = os.path.basename(n)
    im = ImageOps.exif_transpose(Image.open(f'{W}/media/{n}')).convert('RGB')
    im.thumbnail((2400, 3600), Image.LANCZOS)
    im.save(f'{W}/ph/{n}', quality=92); print(n, im.size)
