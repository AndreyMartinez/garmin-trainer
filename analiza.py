# -*- coding: utf-8 -*-
"""
Motor de análisis del bloque 5K.

Lee el histórico de entrenamientos y el plan maestro, cruza lo ejecutado contra
lo prescrito y escribe `analisis.json` con todos los números ya calculados.
El informe narrativo se construye encima de este JSON, no re-derivando a mano.

Uso:  python3 analiza.py [--dias 14]
"""
import csv, json, sys, datetime, argparse, os

BASE = os.path.dirname(os.path.abspath(__file__))
HIST = os.path.join(BASE, 'historial_entrenamientos.json')
CSV_ENTRENOS = os.path.join(BASE, 'entrenamientos_performance.csv')
PLAN = os.path.join(BASE, 'PLAN_MAESTRO.csv')
OUT = os.path.join(BASE, 'analisis.json')

# --- Contexto del atleta (README): LTHR ~186, zonas Friel, 5K en CDMX a 2,240 m ---
LTHR = 186
ZONAS = [('Z1', 0, 157), ('Z2', 158, 165), ('Z3', 166, 175), ('Z4', 176, 185), ('Z5', 186, 999)]
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']


def zona(fc):
    if not fc:
        return None
    fc = float(fc)
    for nombre, lo, hi in ZONAS:
        if lo <= fc <= hi:
            return nombre
    return None


def ritmo(ms):
    """m/s -> 'm:ss' por km. None si no aplica."""
    try:
        ms = float(ms)
    except (TypeError, ValueError):
        return None
    if ms <= 0:
        return None
    secs = 1000.0 / ms
    m = int(secs // 60)
    s = round(secs - m * 60)
    if s == 60:
        m, s = m + 1, 0
    return f'{m}:{s:02d}'


def mmss(segundos):
    if segundos is None:
        return None
    s = round(float(segundos))
    return f'{s // 60}:{s % 60:02d}'


def num(v):
    try:
        f = float(v)
        return round(f, 2)
    except (TypeError, ValueError):
        return None


def cargar_actividades():
    """Prefiere el histórico JSON; cae al CSV si aún no existe."""
    if os.path.exists(HIST):
        return list(json.load(open(HIST, encoding='utf-8')).values())
    filas = list(csv.DictReader(open(CSV_ENTRENOS, encoding='utf-8')))
    for f in filas:
        try:
            f['splitSummaryData'] = json.loads(f['splitSummaryData'] or '[]')
        except json.JSONDecodeError:
            f['splitSummaryData'] = []
    return filas


def cargar_plan():
    """Indexa el plan por fecha. El CSV trae al final filas de apéndice
    ('REGLAS DE ORO DEL BLOQUE', etc.) sin fecha: se descartan."""
    plan = {}
    if not os.path.exists(PLAN):
        return plan
    for r in csv.DictReader(open(PLAN, encoding='utf-8')):
        try:
            datetime.date.fromisoformat((r.get('Fecha') or '').strip())
        except ValueError:
            continue
        if not r.get('SESIÓN'):
            continue
        plan[r['Fecha'].strip()] = r
    return plan


def analiza_sesion(act):
    fases = act.get('splitSummaryData') or []
    km = num(act.get('Distancia_Km')) or 0
    minutos = num(act.get('Duracion_Min')) or 0
    ritmo_global = ritmo(km * 1000 / (minutos * 60)) if km and minutos else None

    detalle = {'activas': [], 'recuperacion': None, 'calentamiento': None}
    for f in fases:
        tipo = f.get('Tipo_Fase', '')
        reps = f.get('Numero_Reps') or 1
        dist = f.get('Distancia_m') or 0
        dur = f.get('Duracion_s') or 0
        bloque = {
            'tipo': tipo,
            'reps': reps,
            'metros_total': round(dist),
            'metros_por_rep': round(dist / reps) if reps else None,
            'seg_por_rep': round(dur / reps, 1) if reps else None,
            'ritmo_real': ritmo(f.get('Ritmo_Medio_ms')),
            'ritmo_ajustado_grado': ritmo(f.get('Ritmo_Ajustado_Grado')),
            'fc_media': f.get('FC_Media'),
            'fc_maxima': f.get('FC_Maxima'),
            'zona_fc': zona(f.get('FC_Media')),
            'potencia_w': f.get('Potencia_Media_W'),
            'cadencia': round(f['Cadencia_Media']) if f.get('Cadencia_Media') else None,
            'zancada_cm': num(f.get('Longitud_Zancada_cm')),
            'contacto_suelo_ms': num(f.get('Tiempo_Contacto_Suelo_ms')),
            'desnivel_pos_m': f.get('Desnivel_Positivo'),
        }
        if tipo == 'INTERVAL_ACTIVE':
            detalle['activas'].append(bloque)
        elif tipo == 'INTERVAL_RECOVERY':
            detalle['recuperacion'] = bloque
        elif tipo == 'INTERVAL_WARMUP':
            detalle['calentamiento'] = bloque

    return {
        'fecha': act['Fecha'][:10],
        'hora': act['Fecha'][11:16],
        'dia': DIAS[datetime.date.fromisoformat(act['Fecha'][:10]).weekday()],
        'nombre': act.get('Nombre'),
        'tipo': act.get('Tipo'),
        'km': km,
        'minutos': minutos,
        'ritmo_global': ritmo_global,
        'fc_media': num(act.get('FC_Media')),
        'fc_maxima': num(act.get('FC_Maxima')),
        'zona_fc_global': zona(act.get('FC_Media')),
        'cadencia': round(float(act['Cadencia_Media'])) if act.get('Cadencia_Media') else None,
        'te_aerobico': num(act.get('Training_Effect_Aerobico')),
        'te_anaerobico': num(act.get('Training_Effect_Anaerobico')),
        'descanso_entre_reps': act.get('Descanso_Entre_Reps') or None,
        'fases': detalle,
        'es_fragmento': bool(km and km < 1.0),  # arranques falsos que ensucian promedios
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias', type=int, default=14,
                    help='ventana del detalle: tira de adherencia, tabla y zonas')
    ap.add_argument('--historial', type=int, default=56,
                    help='horizonte largo para volumen semanal y conteo de omitidos')
    args = ap.parse_args()

    hoy = datetime.date.today()
    desde = hoy - datetime.timedelta(days=args.dias)
    # El detalle quiere ventana corta (se lee cada semana); la tendencia de volumen
    # y el conteo de omitidos quieren horizonte largo. No es la misma ventana.
    desde_hist = hoy - datetime.timedelta(days=args.historial)

    actividades = cargar_actividades()
    sesiones_todas = [analiza_sesion(a) for a in actividades]

    # Hasta dónde llega realmente el histórico. Antes de esta fecha, "sin actividad"
    # significa "nunca se extrajo", no "no entrenó": son cosas distintas y no deben mezclarse.
    cobertura_desde = min((s['fecha'] for s in sesiones_todas), default=hoy.isoformat())

    en_ventana = [s for s in sesiones_todas if datetime.date.fromisoformat(s['fecha']) >= desde]

    # El plan es de carrera y las métricas (cadencia, zancada, contacto de suelo) son
    # de carrera: el ciclismo se reporta aparte como carga cruzada, no se promedia aquí.
    sesiones = [s for s in en_ventana if s['tipo'] == 'running']
    hist_running = [s for s in sesiones_todas
                    if s['tipo'] == 'running' and not s['es_fragmento']
                    and datetime.date.fromisoformat(s['fecha']) >= desde_hist]
    cruzado = [{'fecha': s['fecha'], 'tipo': s['tipo'], 'km': s['km'], 'minutos': s['minutos'],
                'fc_media': s['fc_media'], 'nombre': s['nombre']}
               for s in en_ventana if s['tipo'] != 'running']
    sesiones.sort(key=lambda s: (s['fecha'], s['hora']), reverse=True)

    plan = cargar_plan()

    # Cruce plan vs ejecutado, día por día, incluyendo los días sin registro.
    hechos = {}
    for s in sesiones:
        hechos.setdefault(s['fecha'], []).append(s)

    calendario = []
    d = desde
    while d <= hoy:
        f = d.isoformat()
        p = plan.get(f)
        reales = [s for s in hechos.get(f, []) if not s['es_fragmento']]
        calendario.append({
            'fecha': f,
            'dia': DIAS[d.weekday()],
            'planeado': {
                'sesion': p['SESIÓN'], 'volumen': p['Volumen'],
                'ritmo_objetivo': p['Ritmo objetivo'], 'zona': p['Zona FC'],
                'nota_coach': (p.get('Nota del coach') or '').strip(),
            } if p else None,
            'ejecutado': reales,
            'cumplido': bool(reales),
            'km_dia': round(sum(s['km'] for s in reales), 2),
        })
        d += datetime.timedelta(days=1)

    # Volumen por semana ISO, sobre el horizonte largo
    semanas = {}
    for s in hist_running:
        iso = datetime.date.fromisoformat(s['fecha']).isocalendar()
        k = f'{iso[0]}-W{iso[1]:02d}'
        w = semanas.setdefault(k, {'km': 0.0, 'minutos': 0.0, 'sesiones': 0, 'dias': set()})
        w['km'] += s['km']
        w['minutos'] += s['minutos']
        w['sesiones'] += 1
        w['dias'].add(s['fecha'])
    for k, w in semanas.items():
        w['km'] = round(w['km'], 2)
        w['minutos'] = round(w['minutos'], 1)
        w['dias_entrenados'] = len(w.pop('dias'))

    # Días del plan sin actividad. Solo cuentan como omitidos dentro de la cobertura
    # del histórico; los anteriores se reportan aparte como zona sin datos.
    dias_con_carrera = {s['fecha'] for s in hist_running}
    omitidos, sin_datos = [], []
    d = desde_hist
    while d < hoy:
        f = d.isoformat()
        p = plan.get(f)
        if p and f not in dias_con_carrera:
            fila = {'fecha': f, 'dia': DIAS[d.weekday()], 'sesion': p['SESIÓN'],
                    'volumen': p['Volumen'], 'nota_coach': (p.get('Nota del coach') or '').strip()}
            (omitidos if f >= cobertura_desde else sin_datos).append(fila)
        d += datetime.timedelta(days=1)

    # Fragmentos (arranques falsos)
    fragmentos = [{'fecha': s['fecha'], 'hora': s['hora'], 'km': s['km']}
                  for s in sesiones if s['es_fragmento']]

    # Huecos de datos en el pipeline
    faltantes = {}
    for campo in ('Tiempo_Recuperacion_Horas', 'Varianza_FC'):
        vacios = sum(1 for a in actividades if not str(a.get(campo) or '').strip())
        faltantes[campo] = {'vacios': vacios, 'total': len(actividades)}

    # Carrera objetivo: la fila marcada con 🏁. Ojo: buscar solo "carrera" también
    # engancha "Pista / Ritmo carrera" y "Trote pre-carrera", que no son la carrera.
    carrera = None
    for f, p in sorted(plan.items()):
        if '🏁' in p['SESIÓN'] and f >= hoy.isoformat():
            carrera = {'fecha': f, 'sesion': p['SESIÓN'],
                       'objetivo': p['Ritmo objetivo'],
                       'dias_restantes': (datetime.date.fromisoformat(f) - hoy).days}
            break

    salida = {
        'generado': datetime.datetime.now().isoformat(timespec='seconds'),
        'ventana_dias': args.dias, 'historial_dias': args.historial,
        'desde': desde.isoformat(), 'hasta': hoy.isoformat(),
        'desde_historial': desde_hist.isoformat(),
 'cobertura_desde': cobertura_desde,
        'lthr': LTHR,
        'carrera': carrera,
        'total_sesiones': len([s for s in sesiones if not s['es_fragmento']]),
        'km_totales': round(sum(s['km'] for s in sesiones if not s['es_fragmento']), 2),
        'semanas': semanas,
        'calendario': calendario,
        'sesiones': sesiones,
        'omitidos': omitidos,
        'sin_datos': sin_datos,
        'fragmentos': fragmentos,
        'cross_training': cruzado,
        'calidad_datos': faltantes,
    }

    json.dump(salida, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    # Resumen legible en consola
    print(f"Análisis {salida['desde']} -> {salida['hasta']}  ({salida['total_sesiones']} sesiones de carrera, {salida['km_totales']} km)")
    if cruzado:
        print(f"  Carga cruzada: {len(cruzado)} actividades no-carrera "
              f"({', '.join(sorted({c['tipo'] for c in cruzado}))}), "
              f"{round(sum(c['km'] for c in cruzado),2)} km — fuera de los promedios de carrera")
    if carrera:
        print(f"Carrera: {carrera['fecha']} ({carrera['dias_restantes']} días) · objetivo {carrera['objetivo']}")
    for k in sorted(semanas):
        w = semanas[k]
        print(f"  {k}: {w['km']} km · {w['sesiones']} sesiones · {w['dias_entrenados']} días")
    if omitidos:
        print(f"  OMITIDOS ({len(omitidos)}) - planeados, con datos, sin actividad:")
        for o in omitidos:
            print(f"    {o['fecha']} {o['dia']}: {o['sesion']} ({o['volumen']})")
    if sin_datos:
        print(f"  Sin datos ({len(sin_datos)}) - anteriores a la cobertura ({cobertura_desde}), no concluyente:")
        for o in sin_datos:
            print(f"    {o['fecha']} {o['dia']}: {o['sesion']}")
    print(f"-> {OUT}")


if __name__ == '__main__':
    main()
