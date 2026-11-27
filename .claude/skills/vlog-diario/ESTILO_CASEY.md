# Estilo 2 · "Casey" (inspirado en los vlogs diarios de Casey Neistat)

Se usa cuando el usuario pide "estilo Casey", "estilo 2" o "como Casey Neistat". Motor: `scripts/casey.py`
(importa `vlog.py`, así que valen las mismas claves de archivo, transcripciones y bip). Acordado con el usuario:

- **Horizontal 1920x1080** (YouTube). Los clips y fotos VERTICALES van ENTEROS, centrados sobre su propio fondo
  desenfocado (`pillar`, automático): el usuario se quejó de que la franja recortada (`band`) dejaba afuera partes
  importantes del cuadro. `mode='band'` solo a mano, si una toma vertical no tiene nada arriba ni abajo.
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
- **Todas las charlas del día entran** (cada clip donde hablan a cámara es una "entrada" del blog): no dejar afuera
  ninguna, tampoco por chistes o comentarios jugados. Los videos son privados (para ellos), no se censura contenido; solo
  se bipean las malas palabras. Si dos clips dicen casi lo mismo, van los dos (uno atrás del otro).
- **Nada de tomas parecidas repetidas**: si los dos celulares filmaron lo mismo (mismo mostrador, misma calle), usar una
  sola de las dos (la otra, como mucho, para tapar un tramo feo).
- **Tomas a velocidad normal, elegidas a mano**: el usuario NO quiere escenas aceleradas. Cada toma dura como mucho
  ~5 s (`max_beats=8`); para las tomas largas, mirar la hoja de fotogramas y poner en el plan el tramo (i, o) donde está
  lo importante (la revelación, el elefante, la cara), para no cortar a la mitad de lo que se quiere mostrar. Si hay
  demasiadas tomas parecidas, SACAR las que sobran en vez de acelerar. Hyperlapse (`speed>1`) solo en un traslado
  puntual y si suma; nunca como forma de "hacer entrar" una toma.
- **No dejar afuera lo importante del lugar**: antes de renderizar, repasar la lista de clips sin usar y las fotos.
  Cada atracción principal (la estatua gigante, el templo) tiene que verse al menos una vez; las fotos de ellos dos en
  un lugar donde no hay video juntos van siempre (con `pan` si son verticales).
- **Charlas con ruido**: si la transcripción casi no tiene palabras de un clip donde se ve que hablan (música, mercado),
  `jump()` lo puede dejar en nada: usar `talk(clave, 0, fin)` entero. Después de armar el plan, comparar lo que queda de
  cada charla contra su largo y revisar las que perdieron más de un 15 %.
- **De lo general al detalle**: en cada lugar, primero la toma general (fachada, panorámica, establecimiento) y después
  los detalles (texturas, comida, carteles, manos). Ordenar el plan así dentro de cada sección.
- **Sin sonido donde no se habla**: las tomas sin voz van solo con música (`amb=0` por defecto).
- **Cada toma donde corresponde, no en el orden en que se grabó**: el usuario a veces filma antes o después algo que va
  en otro momento. Ubicar las tomas por lo que muestran y por lo que se dice: nada de mostrar un lugar antes de que lo
  nombren (p. ej. el Buda de lejos va cuando dicen "vamos a ver un Buda gigante", con `overlays` en esa frase), y las
  tomas de afuera de un edificio van en la llegada aunque se hayan filmado a la salida. Mirar las tomas del final del
  día con esa duda antes de usarlas como "vuelta al hotel".
- **Nada que no sume a la historia**: fotos sueltas sin relación (p. ej. la pileta del hotel un día sin pileta) se van.
- **Fotos verticales en el lienzo horizontal**: si hay gente y lugar (el Buda arriba, ellos abajo), usar
  `photo(..., d=3.4, pan=(0.0, 0.7))`, que baja de arriba hacia las caras; ajustar el final para que las caras queden
  enteras. Nunca dejar la foto recortada al medio si las caras quedan afuera.
- **Música: la canción que elige el usuario.** Ningún generador se acercó a lo que quería ("no está ni cerca"):
  si pasa un tema (para el Día 7 fue "Adventurous", de Mellowdy, ~112 BPM), usarlo con
  `music_from_track.py CANCION.mp3 SALIDA.wav SEGUNDOS 112`: lo estira apenas al BPM entero, lo pone en fase con el
  pulso y lo repite empalmando cada 4 compases; normalizar a `music_hiphop.wav` y renderizar con `VLOG_BPM=112`.
  Si el celular sube el archivo vacío (`.mp3.download`, 0 bytes), pedirle que espere a que termine de bajar.
  Sin canción del usuario, o si pide "la música hecha por vos": `music_chill.py SALIDA.wav SEGUNDOS <día> 112`.
  **Nada disonante** (pedido del usuario): todas las voces tocan solo notas de la tríada que suena (melodía, bajo,
  arpegio, acordes), sin séptimas, sin parciales inarmónicos, sin saturar la mezcla, y el eco es corto para no
  arrastrar el acorde anterior. Si se toca el generador, medir con un chroma por ventana de acorde que la energía
  fuera del acorde no suba (sin batería: ~25 %, el resto son armónicos naturales).
- **Nada de verticales con barras**: en el lienzo horizontal, TODOS los clips verticales se recortan a horizontal
  (`mode='band', band_y=<0..1>`), eligiendo la altura a mano: sacar 5 alturas (0.2-0.8) en 2 momentos de la toma y
  quedarse con la que muestra lo importante (caras, el animal, la comida). Si el sujeto se mueve mucho, partir el clip
  con distinta altura por pedazo. **Nunca paneo en videos** (pedido del usuario): altura fija por pedazo. El paneo
  (`band_y=(y0, y1)` en video está disponible pero NO usarlo; `photo(..., pan=(y0, y1))`) es solo para FOTOS
  verticales que no entran recortadas. Fotos verticales: recortar a horizontal (`pan=(y, y)`, altura fija) si no se
  pierde nada importante; si se pierde, paneo de arriba a abajo para que se vea toda. Además, priorizar tomas horizontales: si el mismo momento está en horizontal, sacar
  el vertical. (Las fotos verticales quedan enteras con fondo desenfocado o con `pan`.)
- **Fotos: solo las que el usuario dejó en el álbum** (borra las que no le gustan; volver a listar antes de rehacer) y
  nunca con alguien con los ojos cerrados: recortar las caras (OpenCV Haar, `opencv-python-headless<5` en el venv) y
  mirarlas antes de elegir.
- **Bip solo si la palabra es segura**: si al volver a transcribir el tramo no sale la misma mala palabra, no bipear
  (`bleep=False` en ese clip). El usuario marcó bips puestos sobre palabras normales.
- **Clips duplicados**: si dos clips seguidos dicen lo mismo (uno se cortó y lo volvieron a grabar), va solo el completo.
- **Charlas "basura"** (sin contenido, gente hablando de fondo, frases sueltas): si el usuario lo marca, sacarla y
  reemplazarla por una toma.
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
/opt/vlog-venv/bin/python -I $K/music_hiphop.py $VLOG_WS/hh_raw.wav 1200 <número del día> && \
ffmpeg -v error -y -i $VLOG_WS/hh_raw.wav -af "loudnorm=I=-16:TP=-1.5" -ar 48000 $VLOG_WS/music_hiphop.wav
```
La página del celular se arma igual (`publish_prep.py` detecta que es horizontal).
