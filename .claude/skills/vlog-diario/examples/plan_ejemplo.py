"""Plan de ejemplo. Copiar a $VLOG_WS/plan_diaN.py, reemplazar las claves por fragmentos de nombres reales
(album.py list) y correr:  VLOG_WS=$VLOG_WS VLOG_SKILL=<skill>/scripts /opt/vlog-venv/bin/python -I plan_diaN.py"""
import os, sys
sys.path.insert(0, os.environ['VLOG_SKILL'])
import vlog
from vlog import talk, broll, photo, blooper, media

LB = 'letterbox'
PLAN = [
    # apertura: hablan a cámara, título del día
    talk('0905_abc123', 0.4, 9.8, caps=[(0.5, 3.0, 'Buen día, arrancamos el día 2'), (3.2, 9.6, 'Hoy vamos al Gran Palacio')],
         title=(0.2, 3.6, 'DÍA 2', 'Templos de Bangkok')),
    # tomas artísticas del lugar, música arriba
    broll('0931_def456', 1.0, 4.5, title=(0.2, 3.0, 'BANGKOK', 'Gran Palacio')),
    broll('0933_ghi789', 0.0, 3.0, mode='portrait'),
    photo('0935_jkl012', 1.8),
    # mencionan algo -> se ve mientras siguen hablando; PiP / chroma
    talk('0940_mno345', 0.3, 14.0, mode=LB,
         caps=[(0.4, 4.0, 'Miren el buda de oro'), (4.2, 13.8, 'Dicen que pesa cinco toneladas')],
         overlays=[('full', 4.0, 8.0, media('0938_pqr678')),                 # foto o video del buda
                   ('pip', 8.0, 13.9, media('0939_stu901', 2.0, mode='portrait'))],
         cards=[(5.0, 5.0, 'DATO CURIOSO', 'Texto verificable\\Nen dos líneas')]),
    # toma con la voz de ellos de fondo
    broll('0950_vwx234', 0.0, 6.0, vo=('0940_mno345', 20.0), caps=[(20.1, 25.5, 'Lo que dicen de fondo')]),
    # algo curioso que se ve en cámara
    talk('1010_yza567', 1.0, 6.0, mode=LB, caps=[(1.1, 5.8, '¿Qué es esto?')],
         tags=[(0.3, 'CURIOSIDAD · lo que se ve', 5.0)]),
    # chroma: ellos recortados sobre una toma
    talk('1100_bcd890', 0.5, 9.0, mode=LB, caps=[(0.6, 8.8, 'Estamos en el río')],
         overlays=[('chroma', 3.0, 9.0, media('1102_efg123', 1.0))]),
    # bloopers al final
    blooper('1200_hij456', 2.0, 5.5, caps=[(2.1, 5.4, 'Se me cayó el celular')]),
    blooper('1300_klm789', 0.0, 3.0, mode=LB),
    broll('2100_nop012', 2.0, 8.5, title=(0.3, 6.0, 'FIN DEL DÍA 2', 'Continuará…')),
]
PLAN[[i for i, s in enumerate(PLAN) if s['kind'] == 'blooper'][0]]['title'] = (0.0, 2.5, 'LOS', 'Bloopers')

if __name__ == '__main__':
    vlog.build(PLAN, 'dia2', os.environ['VLOG_WS'] + '/Dia2.mp4')
