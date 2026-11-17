#!/bin/bash
# Instala lo que necesita la skill (idempotente). Uso: bash setup.sh
set -e
command -v ffmpeg >/dev/null || { apt-get update -qq && apt-get install -y -qq ffmpeg; }
if [ ! -x /opt/vlog-venv/bin/python ]; then python3 -m venv /opt/vlog-venv; fi
/opt/vlog-venv/bin/python -c "import faster_whisper, pillow_heif, rembg, numpy" 2>/dev/null || \
  /opt/vlog-venv/bin/pip install -q faster-whisper pillow-heif "rembg[cpu]" numpy pillow
fc-list | grep -qi "Inter" || echo "AVISO: falta la fuente Inter (subtítulos usarán otra)"
echo "listo: /opt/vlog-venv"
