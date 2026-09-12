# -*- coding: utf-8 -*-
"""
Arma el informe publicable a partir de la plantilla, los números y la narrativa.

    informe_plantilla.html  (estructura y estilos, con marcadores)
  + analisis.json           (lo que calculó analiza.py)
  + narrativa.json          (lo único escrito a mano cada semana)
  -> informe_5k.html        (lo que se publica)

Uso:  python3 informe.py
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(BASE, 'informe_plantilla.html')
ANALISIS = os.path.join(BASE, 'analisis.json')
NARRATIVA = os.path.join(BASE, 'narrativa.json')
SALIDA = os.path.join(BASE, 'informe_5k.html')


def main():
    faltan = [p for p in (PLANTILLA, ANALISIS, NARRATIVA) if not os.path.exists(p)]
    if faltan:
        print('Faltan archivos:', ', '.join(os.path.basename(f) for f in faltan), file=sys.stderr)
        if ANALISIS in faltan:
            print('Corre primero:  python3 analiza.py', file=sys.stderr)
        return 1

    html = open(PLANTILLA, encoding='utf-8').read()
    datos = json.load(open(ANALISIS, encoding='utf-8'))
    narrativa = json.load(open(NARRATIVA, encoding='utf-8'))

    for marcador in ('__DATOS__', '__NARRATIVA__'):
        if marcador not in html:
            print(f'La plantilla no contiene {marcador}.', file=sys.stderr)
            return 1

    # </script> dentro de un literal JSON cerraría la etiqueta del documento.
    def incrustar(obj):
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

    html = html.replace('__DATOS__', incrustar(datos), 1)
    html = html.replace('__NARRATIVA__', incrustar(narrativa), 1)

    open(SALIDA, 'w', encoding='utf-8').write(html)

    aviso = ''
    if datos.get('generado', '')[:10] != datos.get('hasta'):
        aviso = '  (ojo: analisis.json no es de hoy, corre analiza.py)'
    print(f"informe_5k.html generado · {datos['total_sesiones']} sesiones · "
          f"{datos['km_totales']} km · ventana {datos['desde']} → {datos['hasta']}{aviso}")
    print(f'  {len(html):,} bytes -> {SALIDA}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
