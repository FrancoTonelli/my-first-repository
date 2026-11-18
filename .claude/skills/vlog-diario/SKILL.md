---
name: vlog-diario
description: Arma el video diario del vlog de viaje a Tailandia a partir del álbum compartido de Google Photos "Tailandia 2026" - baja los videos y fotos del día en HD, los transcribe, los edita en vertical 9:16 con el estilo acordado (subtítulos, bip, superposiciones, PiP/chroma, curiosidades, tomas artísticas, bloopers) y publica una página privada para verlo y guardarlo desde el celular. Usar cuando el usuario pida "armá el día N", "sumá lo nuevo del álbum", "editá el video de hoy" o cambios sobre un video del viaje.
---

# Vlog diario · Tailandia 2026

El usuario (habla en español rioplatense) viaja por Tailandia y sube cada día fotos y videos de su iPhone
a un álbum compartido de Google Photos. El enlace del álbum está en la variable de entorno
`VLOG_ALBUM` (configurada en el entorno privado "Tailandia video blog"; si falta, pedírselo al usuario). Quiere un video vertical por día. **Solo usa el celular**: el
resultado se entrega en una página privada (Artifact) con un botón para guardarlo en el teléfono.

## Dos estilos de edición (preguntar cuál si el usuario no lo dice)

| Estilo | Cuándo | Motor | Guía |
|---|---|---|---|
| **1 · Clásico** (vertical 9:16) | "estilo 1", "clásico", "como el día 1", Reels/TikTok | `scripts/vlog.py` | sección 3 de este archivo |
| **2 · Casey** (horizontal 16:9) | "estilo 2", "estilo Casey", "como Casey Neistat", YouTube | `scripts/casey.py` | `ESTILO_CASEY.md` |

Los pasos 0, 1, 2, 4, 5 y 6 son iguales para los dos. Se pueden hacer los dos estilos del mismo día
(el material, las transcripciones y la caché se comparten).

## 0. Preparar la sesión (1 minuto)

```bash
K=<carpeta de esta skill>/scripts
bash $K/setup.sh                      # instala ffmpeg + /opt/vlog-venv (whisper, heic, rembg) si falta
export VLOG_WS=$SCRATCHPAD/vlog_diaN   # carpeta de trabajo del día (usar el scratchpad, no /tmp)
```

- Red necesaria (entorno "Tailandia video blog" ya la tiene): photos.app.goo.gl, photos.google.com,
  lh3.googleusercontent.com, video-downloads.googleusercontent.com, huggingface.co + cdn-lfs*.hf.co,
  cas-bridge/cas-server/transfer.xethub.hf.co, us.aws.cdn.hf.co, github.com (+ objects/release-assets).
  Si el proxy rechaza un host, pedirlo con `update_environment` (no adivinar workarounds).
- Fuentes: Inter e Inter Display (vienen instaladas en el contenedor).

**Espacio en disco**: la sesión tiene un cupo fijo (un día de material 4K + caché ronda 6-10 GB). Usar una sola
carpeta de modelos (no copiarla a cada `VLOG_WS`), borrar `build_*` y videos finales viejos una vez publicados,
y si un `ffmpeg` falla con "No space left on device": liberar espacio, borrar el archivo final truncado y los
segmentos que no abran con `ffprobe`, y volver a correr el plan (los segmentos sanos se reutilizan).

## 1. Traer el material del día

**Límite de 300**: el enlace compartido de Google Photos muestra solo los primeros 300 elementos del álbum (el
resto lo carga por páginas con una API interna que esta skill NO usa). El álbum general "Tailandia 2026" ya
superó ese número, así que el usuario arma **un álbum por día** ("Tailandia · Día N") y pasa su enlace:
`album.py ... --album <enlace del día>`. Si `album.py` avisa que hay 300 o más, pedirle el álbum del día.

```bash
python3 $K/album.py $VLOG_WS list --from '2026-11-17 00:00' --to '2026-11-18 03:00'   # ver qué hay
python3 $K/album.py $VLOG_WS pull --from '2026-11-17 00:00' --to '2026-11-18 03:00'   # bajar
python3 $K/album.py $VLOG_WS retry        # en background (Monitor): reintenta los videos en baja calidad
```

- Horas en hora de Tailandia (UTC+7). El "día" del vlog puede pasar de medianoche: incluir la madrugada.
- Los archivos quedan como `media/MMDD_HHMM_<id6>.mp4|jpg`. En los planes se citan por un fragmento único
  del nombre (por ej. `'2055_a1b2c3'`); si es ambiguo, el motor avisa.
- **Videos en 568x320** = Google todavía no recibió/procesó el original (el celular sigue subiendo).
  `retry` los vuelve a bajar cada 2 min tomando las URLs nuevas del álbum. Si tarda, se puede armar una
  versión preliminar y reexportar después (el motor cachea por contenido: borrar `build_<nombre>/` si cambió el archivo).
- El usuario a veces agrega fotos de días anteriores: por eso todo se identifica por id, no por posición.

## 2. Mirar y escuchar todo antes de editar

```bash
/opt/vlog-venv/bin/python -I $K/photos.py $VLOG_WS <fotos .jpg>            # HEIC -> ph/<nombre>.jpg
/opt/vlog-venv/bin/python -I $K/transcribe.py $VLOG_WS <videos .mp4>       # transcripts/<nombre>.json
python3 $K/strips.py $VLOG_WS $VLOG_WS/sheet <videos y fotos>             # hojas de fotogramas -> Read
```

- Leer las hojas con Read para entender cada clip: orientación (si algo sale de costado o al revés,
  usar `rot='ccw'|'cw'|'180'`), qué se ve, cuándo hay caras, qué es "artístico".
- La transcripción no es determinística: si un clip importante sale con frases faltantes o raras, volver a
  correrlo (borrar su `transcripts/<nombre>.json`). El bip depende de que la mala palabra esté transcripta.
- La transcripción (large-v3-turbo) es buena pero se equivoca con nombres propios: corregir con contexto
  (p. ej. "Causton Road" = Khao San Road, "Finlandia" = Tailandia, "grado" = Grab). **Si una frase no se
  entiende, no subtitularla** (mejor sin subtítulo que inventado) y avisarle al usuario cuáles quedaron dudosas.

## 3. Escribir el plan del día

Un archivo `plan_diaN.py` en `$VLOG_WS` (ver `examples/plan_ejemplo.py` y, como referencia de tono y
subtítulos, el plan del Día 1 que está en el Drive del usuario: `skill_vlog_diario.tar.gz` → reference/plan_dia1.py). API del motor (`scripts/vlog.py`):

| Helper | Uso |
|---|---|
| `talk(key, i, o, mode, rot, caps, title, overlays, cards, tags)` | Clip con voz. Bip automático. |
| `broll(key, i, o, mode, vo=(key, t), caps, title, cards)` | Toma artística: color cine + zoom lento; música fuerte. Con `vo` lleva su voz de fondo. |
| `photo(key, d, vo, caps, title, cards)` | Foto con Ken Burns. |
| `blooper(key, i, o, mode, rot, caps)` | B/N + grano + voz de radio + etiqueta BLOOPER. |
| `media(key, i, mode)` | Lo que se superpone en `overlays`. |

- `mode`: `'portrait'` (vertical), `'crop'` (horizontal recortado a 9:16, para tomas), `'letterbox'`
  (horizontal entero sobre fondo desenfocado, para selfies horizontales de dos personas).
- `caps=[(t0, t1, 'texto'), ...]` en segundos **del archivo fuente** (para `broll` con `vo`, en tiempo del clip de la voz).
  `|` parte un subtítulo largo en dos. Las malas palabras se enmascaran solas (`p#@!`).
- `overlays=[('full'|'pip'|'chroma', t0, t1, media(...))]`: mientras siguen hablando se ve el material.
  `full` = pantalla completa; `pip` = ellos en un recuadro arriba a la derecha; `chroma` = ellos recortados
  (rembg) sobre la toma. Chroma cuesta ~0.4 s por cuadro: usarlo 1-3 veces por video.
- `cards=[(t_desde_inicio_del_segmento, duración, 'DATO CURIOSO'|'TIP', 'texto\\Nsegunda línea')]`.
- `tags=[(t, 'CURIOSIDAD · ...', duración)]` para marcar algo raro que se ve en cámara.
- `title=(t, dur, 'CHICO', 'Grande')` títulos de sección arriba.
- `PLAN[...]['title']` también vale para bloques (p. ej. "LOS Bloopers").

### Estilo acordado con el usuario (respetarlo siempre)

1. Vertical 1080x1920. Arranca con título `DÍA N` + frase del día; termina con `FIN DEL DÍA N · Continuará…`.
2. **Voces completas** en los clips hablados, con subtítulos grandes. Cortar silencios, "eeh" y partes sin interés.
3. **Mezclar** clips hablando con **tomas artísticas** de los lugares. En las tomas: música sola un poco más
   fuerte, o la voz de ellos de fondo (`vo`). Abrir cada lugar con un título de sección.
4. **Si mencionan algo y hay foto o video, mostrarlo superpuesto** mientras la voz sigue (full / PiP / chroma).
5. **Curiosidades**: todo lo curioso que se vea va marcado (`tags`) y se suman tarjetas `DATO CURIOSO` /
   `TIP`. Solo datos **verificables y conocidos** (si hay duda, no ponerlo o buscarlo antes).
6. **Bip** en malas palabras (lista `SWEAR` en vlog.py; "boludo" no se bipea).
7. **Bloopers al final** (antes del cierre): risas, errores, momentos absurdos, en B/N con voz de radio.
8. Música de fondo original (sin derechos): `music.py`, baja bajo la voz, sube en tomas.
9. Duración: lo que el día dé (el Día 1 quedó en 9 min). Si piden versión corta, 60-90 s para Reels.
10. Colores: los videos del iPhone son HDR HLG; el motor los pasa a SDR (tonemap mobius, npl 203). No cambiar.

Música (una vez por sesión):
```bash
/opt/vlog-venv/bin/python -I $K/music.py $VLOG_WS/music_raw.wav 900 && \
ffmpeg -v error -y -i $VLOG_WS/music_raw.wav -af "lowpass=f=6000,aecho=0.8:0.5:60:0.15,loudnorm=I=-18:TP=-2" -ar 48000 $VLOG_WS/music.wav
```

## 4. Renderizar y revisar

```bash
cd $VLOG_WS && VLOG_WS=$VLOG_WS VLOG_SKILL=$K /opt/vlog-venv/bin/python -I plan_diaN.py
```
- En background (tarda ~3-4 min por minuto de video; más con chroma). Avisar al usuario mientras tanto.
- Revisar: sacar ~40 fotogramas repartidos (ffmpeg `-ss`) en una grilla y mirarla con Read. Chequear
  orientación, que los subtítulos no tapen caras, títulos/tarjetas legibles. El audio no se puede escuchar:
  decírselo al usuario y pedirle que avise si algo suena raro.

## 5. Entregar en el celular

El chat no le deja descargar archivos y Drive solo acepta subidas de hasta 10 MB desde acá. Se usa una
página privada (Artifact) que une partes y ofrece **Guardar en el celular** (capacidad `downloads`; en iPhone
abre el menú de compartir → Guardar video / Google Photos).

```bash
python3 $K/publish_prep.py $VLOG_WS diaN $SCRATCHPAD/pagina_diaN --title 'Templos y mercados' --day N \
        --route 'Bangkok|Wat Pho|Chinatown'
```
- Publicar con el tool Artifact: primer publish con `file_path=.../index.html`, `root=` la carpeta,
  `capabilities={"downloads": true}`, `icon="video"`, `files` = poster.jpg + part01..04; después tandas de
  ≤4 partes (límite 64 MB por publish) con el mismo `file_path`. Al final, `list scope=files` para verificar.
- Una página nueva por día (cada versión de artifact admite ~256 MB). Para rehacer el mismo día, republicar
  en la misma URL (los `partNN` se pisan; si hay menos partes, borrar las sobrantes con `null`).
- Para encontrar páginas de días anteriores: Artifact `action: "list"`.
- Mantener la versión del celular en ~180 MB: la app de Android corta en 200 MiB.
- No mandar el MP4 por SendUserFile como forma de entrega principal (en el celular no se puede bajar).

## 6. Cerrar

Mensaje corto al usuario: link de la página, qué se agregó (por secciones), qué subtítulos quedaron
dudosos, y si quedó algo en baja calidad. Preguntar qué cambiar. Guardar el `plan_diaN.py` del día en el Drive
del usuario (Google Drive `create_file` con `textContent`, título `plan_diaN.py`): tiene frases privadas,
no va al repositorio (que es público).
