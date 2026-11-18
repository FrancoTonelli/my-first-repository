# Estilo 2 · "Casey" (inspirado en los vlogs diarios de Casey Neistat)

Se usa cuando el usuario pide "estilo Casey", "estilo 2" o "como Casey Neistat". Motor: `scripts/casey.py`
(importa `vlog.py`, así que valen las mismas claves de archivo, transcripciones y bip). Acordado con el usuario:

- **Horizontal 1920x1080** (YouTube). Todo llena la pantalla: los clips verticales se recortan a una franja
  horizontal (`band`; en clips hablados la franja va arriba, `band_y=0.32`, para no cortar caras; ajustable por
  segmento con `band_y=`). `mode='pillar'` (vertical chiquito sobre fondo desenfocado) solo si el usuario lo pide.
- **Variante vertical** (el usuario la pidió para el Día 1, que tiene mucho material vertical): mismo estilo en
  1080x1920 con `VLOG_CANVAS=vertical` antes de importar `casey`. Los verticales llenan la pantalla, los horizontales
  hablados van enteros a lo ancho sobre su fondo desenfocado (`fitw`) y las tomas horizontales se recortan al centro.
  Usar otro nombre de build (la caché depende del lienzo). Ejemplo: un `run_*.py` que hace
  `os.environ['VLOG_CANVAS']='vertical'`, carga el plan con `runpy.run_path` y llama `casey.build(PLAN, 'diaN_vertical', ...)`.
- **Sin subtítulos**, salvo cuando una frase no se entiende bien (ruido, viento, gente hablando encima).
- **Puede quedar largo.** Aprovechar la mayoría de las tomas generales y de detalle de cada lugar.

## Reglas de edición

**Pedidos explícitos del usuario (no negociables):**
- **Las charlas van completas**: en los clips donde hablan, usar todo lo que dicen (desde la primera hasta la última
  frase del clip), no elegir pedacitos. `jump()` solo corta silencios de más de 1 s (`gap=1.0`, margen `pad=0.25`).
  Si hay un tramo feo (cámara al piso), taparlo con un overlay, nunca cortar la voz.
- **Nada de tomas parecidas repetidas**: si los dos celulares filmaron lo mismo (mismo mostrador, misma calle), usar una
  sola de las dos (la otra, como mucho, para tapar un tramo feo).
- **Tomas cinematográficas cortas**: no poner las tomas enteras; `broll()` usa por defecto el mejor tramo limpio de hasta
  6 pulsos (4 s). Solo `max_beats=None` (o más pulsos) en tomas que de verdad lo merecen.
- **De lo general al detalle**: en cada lugar, primero la toma general (fachada, panorámica, establecimiento) y después
  los detalles (texturas, comida, carteles, manos). Ordenar el plan así dentro de cada sección.
- **Sin sonido donde no se habla**: las tomas sin voz van solo con música (`amb=0` por defecto).
- **Cambios de escena en el beat**: todo segmento dura un múltiplo exacto del pulso (90 BPM = 0,667 s), también los
  clips hablados (`build()` los ajusta), la música corre continua y el concat usa duraciones exactas: cada corte cae en
  un beat.

0. **Videos antes que fotos** (pedido del usuario): las fotos solo cuando no hay video de ese momento o lugar.

1. **El día es una historia**: plan o problema al principio → camino → resolución → cierre. Lo que no suma a
   esa historia se va; lo que suma, se queda aunque sea largo.
2. **Gancho primero**: abrir con el momento más llamativo del día (2-6 s), después el título grande
   (`title=(t, dur, 'BANGKOK', 'Día 2')`) sobre una toma general con música arriba.
3. **Hablando a cámara con cortes secos**: usar `jump(...)`, que recorta los silencios. Detecta la voz con dos
   fuentes juntas: las palabras de la transcripción y la energía en la banda de voz comparada con el piso de
   ruido del clip (así no corta a nadie aunque la transcripción se haya comido una frase, y funciona en lugares
   ruidosos). `gap` = silencio máximo que se deja (0.45 s). Si la frase se adivina, cortar antes de que termine
   (el "corte Casey") acortando el `o` a mano.
   En `jump`, los tiempos de `labels`, `overlays` y `caps` van en segundos del archivo; en `talk`/`broll`/`photo`
   los `labels` van en segundos desde el inicio del segmento.
4. **Las tomas cuentan la historia**: por cada lugar, toma general → detalles (comida, carteles, precios,
   manos, texturas) → gente. Los traslados se resumen con **hyperlapse** (`broll(..., speed=4..8)`) de
   caminatas, tuk tuk, tren, auto. Timelapses cortos (menos de 5 s).
5. **Barridos** (`whip_out=True` en una toma y `whip_in=True` en la siguiente) solo en los 4-6 cambios grandes de
   lugar del día. El "whoosh" suena únicamente cuando los dos lados lo marcan, y bajito. **El usuario pidió no
   abusar del whoosh.**
5b. **Cortes limpios**: antes de escribir el plan, mirar cada clip a 1 cuadro por segundo y elegir entradas y
   salidas a mano (sin cámara al piso, contra la luz, de costado ni borrosa). `broll()` además recorta solo a su
   tramo limpio más largo (`clean=True`, usa `bad_spans()`); en clips hablados, tapar los tramos feos con
   `overlays` de otras tomas en vez de cortar la voz.
5c. **No repetir material**: cada pedazo de video se usa una sola vez (el gancho tampoco se repite después: se
   saca de la historia). `build()` avisa si hay repeticiones. Tampoco repetir la misma frase desde dos clips ni
   la misma escena en video y en foto.
6. **La música manda** en los montajes: hip-hop instrumental (`music_hiphop.py`, 90 BPM). Los bloques de tomas
   arrancan en compás y sus duraciones se redondean al pulso (cortes en el beat). Bajo la voz queda muy baja.
   Para remarcar un remate: `music='off'` en ese segmento (silencio de golpe).
7. **Texto mínimo**: `labels=[(t, dur, 'LUGAR', 'hora o dato')]` abajo a la izquierda en mayúsculas: lugar,
   hora ("4:12 PM", sale del nombre del archivo), precio ("120 ฿"), temperatura. Nada de tarjetas ni etiquetas
   de colores (eso es del estilo 1).
8. **Imagen cruda con contraste**: el motor aplica más contraste y nitidez; no agregar filtros llamativos.
9. **Mostrar lo que nombran**: `overlays=[('full', t0, t1, media(...))]` mientras sigue la voz (como en el estilo 1);
   PiP solo si hace falta ver la reacción.
10. **Bip** igual que en el estilo 1 (automático).
11. **Cierre fijo**: toma general del último lugar con música arriba + `title=(..., 'MAÑANA', 'lo que sigue')` o la
    frase de despedida que elija el usuario. Sin bloopers en blanco y negro (si hay un momento gracioso, va
    dentro de la historia, con corte seco).

## Ejemplo mínimo

```python
import os, sys; sys.path.insert(0, os.environ['VLOG_SKILL'])
import casey
from casey import jump, talk, broll, photo, media
PLAN = [
    jump('2055_abc123', 0.5, 6.0),                                   # gancho
    broll('2056_def456', 0.0, 6.0, title=(0.3, 3.0, 'Bangkok', 'Día 2'), music='up', whip_out=True),
    jump('0905_ghi789', 0.0, 40.0, whip_in=True, labels=[(0.5, 3.0, 'Hotel', '9:05 AM')],
         overlays=[('full', 12.0, 16.0, media('0910_jkl012'))]),
    broll('0930_mno345', 0.0, 30.0, speed=6),                        # hyperlapse del traslado
    broll('0945_pqr678', 2.0, 6.0), broll('0946_stu901', 0.0, 3.0), photo('0947_vwx234'),
    ...
]
casey.build(PLAN, 'dia2_casey', os.environ['VLOG_WS'] + '/Dia2_casey.mp4')
```

Música (una vez por sesión):
```bash
/opt/vlog-venv/bin/python -I $K/music_hiphop.py $VLOG_WS/hh_raw.wav 1200 && \
ffmpeg -v error -y -i $VLOG_WS/hh_raw.wav -af "loudnorm=I=-16:TP=-1.5" -ar 48000 $VLOG_WS/music_hiphop.wav
```
La página del celular se arma igual (`publish_prep.py` detecta que es horizontal).
