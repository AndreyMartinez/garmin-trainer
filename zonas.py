# -*- coding: utf-8 -*-
"""
Zonas de entrenamiento ancladas a umbrales medidos en campo, expresadas en frecuencia cardiaca.

Todo el sistema cuelga de tres anclas: LT1, LT2 y FCmax. Se cambian SOLO con un test.
Sin lactometro: LT2 sale de la contrarreloj de 30 min (Test A) y LT1 de la deriva aerobica
(Test B). Los ritmos no son un ancla: se derivan de la regresion FC-ritmo ajustada con
los datos reales.

    python3 zonas.py                       # tabla de zonas vigente
    python3 zonas.py --garmin              # que teclear en Garmin Connect
    python3 zonas.py --protocolo A         # protocolo completo de un test
    python3 zonas.py --refit               # re-ajusta la regresion FC<->ritmo con lo ejecutado
    python3 zonas.py --lt2 173 --ritmo-lt2 3:47 --fecha 2026-10-01 --metodo "CR 30 min"
    python3 zonas.py --deriva 4:38 149 4:47 150     # Test B: calcula la deriva aerobica
"""
import json, csv, os, argparse, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, 'zonas.json')
CSV_ENTRENOS = os.path.join(BASE, 'entrenamientos_performance.csv')

# Tope de desnivel para un punto de la regresion FC<->ritmo, en metros por km.
# Por encima, la cuesta infla la FC para el ritmo y el punto deja de describir
# terreno llano.
MAX_DESNIVEL_M_KM = 15.0

# Sesiones cuya FC no sirve para la regresion. El sensor optico de la muneca se
# descuelga en esfuerzo duro y devuelve una FC baja y plana: el punto entra como
# "mucho ritmo con poca FC", le tumba la pendiente a la recta y toda la tabla de
# ritmos sale demasiado rapida. Es exactamente el error que rompio el bloque anterior,
# asi que estos puntos se descartan a mano. Clave: fecha (YYYY-MM-DD).
FC_DESCARTADA = {
    '2026-09-20': 'Carrera 5K con FC de muneca: la FC CAE de 186 a 168 mientras el ritmo '
                  'SUBE en los ultimos 8 min. Fisiologicamente imposible. El Test A del '
                  '1-oct con banda de pecho da 183 lpm a 3:47/km; este punto decia 174 lpm '
                  'a 3:33/km. Con el dentro, la regresion erraba -12 lpm en umbral.',
}


def cargar():
    return json.load(open(CFG, encoding='utf-8'))


def guardar(cfg):
    json.dump(cfg, open(CFG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)


def mmss(seg):
    if seg is None or seg <= 0 or seg > 3600:
        return '—'
    return f'{int(seg // 60)}:{seg % 60:04.1f}'


def ritmo_de_fc(fc, reg):
    """FC -> segundos por km, invirtiendo FC = a*v + b."""
    v = (fc - reg['b']) / reg['a']
    return 1000.0 / v if v > 0 else None


def limites(cfg):
    """Resuelve los offsets de cada zona contra las anclas -> rangos absolutos en lpm."""
    a = cfg['anclas']
    reg = cfg['regresion_fc_ritmo']
    out = []
    for z in cfg['zonas']:
        if z['lo_off'] is None:
            out.append({**z, 'lo': None, 'hi': None, 'ritmo_lo': None, 'ritmo_hi': None})
            continue
        lo = 0 if z['lo_off'][1] == -999 else a[z['lo_off'][0]] + z['lo_off'][1]
        hi = a[z['hi_off'][0]] + z['hi_off'][1]
        out.append({**z, 'lo': lo, 'hi': hi,
                    'ritmo_lo': ritmo_de_fc(max(lo, 120), reg),
                    'ritmo_hi': ritmo_de_fc(hi, reg)})
    return out


def puntos_continuos(dias=None):
    """Esfuerzos continuos (1 rep, >=15 min) que sirven para ajustar FC<->ritmo."""
    if not os.path.exists(CSV_ENTRENOS):
        return []
    corte = None
    if dias:
        corte = datetime.date.today() - datetime.timedelta(days=dias)
    pts = []
    for r in csv.DictReader(open(CSV_ENTRENOS, encoding='utf-8')):
        if r['Tipo'] != 'running' or not r['splitSummaryData']:
            continue
        f = datetime.datetime.strptime(r['Fecha'], '%Y-%m-%d %H:%M:%S')
        if corte and f.date() < corte:
            continue
        if r['Fecha'][:10] in FC_DESCARTADA:
            continue
        try:
            fases = json.loads(r['splitSummaryData'])
        except json.JSONDecodeError:
            continue
        for s in fases:
            if s.get('Tipo_Fase') != 'INTERVAL_ACTIVE' or (s.get('Numero_Reps') or 1) != 1:
                continue
            if (s.get('Duracion_s') or 0) < 900:
                continue
            v, fc = s.get('Ritmo_Medio_ms'), s.get('FC_Media')
            if not v or not fc:
                continue
            # Una cuesta sube la FC para un ritmo dado. Y un punto inclinado y lento
            # queda lejos del resto en el eje de velocidad, asi que arrastra la recta
            # hacia si: el descarte por 2 desviaciones no lo ve porque su propio
            # residuo se queda chico. Mejor no dejarlo entrar.
            dpos = float(s.get('Desnivel_Positivo') or 0)
            dist = float(s.get('Distancia_m') or 0)
            if dist and dpos / (dist / 1000.0) > MAX_DESNIVEL_M_KM:
                continue
            pts.append((float(v), float(fc), r['Fecha'][:10], dpos))
    return pts


def ajustar(pts, vueltas=2, ancla=None):
    """Minimos cuadrados FC = a*v + b, descartando atipicos a 2 desviaciones.

    Con `ancla` = (velocidad, FC) del Test A, la recta pasa OBLIGADA por ese punto y
    solo se ajusta la pendiente. Sin ancla la nube de rodajes faciles manda: hay
    diecinueve puntos en torno a 5:20/km y uno solo en umbral, asi que la recta libre
    se acuesta sobre los faciles y queda -4 lpm baja justo donde se prescriben las
    series. Traducido a ritmo: 6 s/km de mas en cada rep de umbral. La version anclada
    clava el unico punto que se midio a proposito y deja el error en los faciles,
    donde la regla es "si dudas, mas suave" y por tanto no hace dano.
    """
    datos = [(v, fc) for v, fc, _, _ in pts]
    a = b = None
    for _ in range(vueltas):
        n = len(datos)
        if n < 4:
            return None
        if ancla:
            va, fa = ancla
            den = sum((v - va) ** 2 for v, _ in datos)
            if den == 0:
                return None
            a = sum((v - va) * (f - fa) for v, f in datos) / den
            b = fa - a * va
        else:
            sv = sum(v for v, _ in datos); sf = sum(f for _, f in datos)
            svv = sum(v * v for v, _ in datos); svf = sum(v * f for v, f in datos)
            den = n * svv - sv * sv
            if den == 0:
                return None
            a = (n * svf - sv * sf) / den
            b = (sf - a * sv) / n
        res = [abs(f - (a * v + b)) for v, f in datos]
        sd = (sum(r * r for r in res) / n) ** 0.5
        datos = [(v, f) for (v, f), r in zip(datos, res) if r <= 2.0 * sd] or datos
    return a, b, len(datos)


def imprimir(cfg):
    a, reg = cfg['anclas'], cfg['regresion_fc_ritmo']
    prov = '  ⚠ PROVISIONALES — sin test de campo' if a.get('provisional') else ''
    print(f"\nANCLAS  ({a['fecha']} · {a['metodo']}){prov}")
    print(f"  LT1 {a['lt1']} lpm   LT2 {a['lt2']} lpm   FCmax {a['fcmax']} lpm"
          f"   |  LT1={a['lt1']/a['fcmax']*100:.1f}% FCmax · LT2={a['lt2']/a['fcmax']*100:.1f}% FCmax")
    print(f"  regresion: FC = {reg['a']:.2f}·v + {reg['b']:.1f}  (n={reg['n']}, {reg['ajustada']})")
    print(f"\n{'':4}{'zona':24}{'lpm':>11}{'ritmo/km':>19}{'RPE':>6}  como se oye")
    print('  ' + '─' * 96)
    for z in limites(cfg):
        if z['lo'] is None:
            rng, rit = 'no aplica', 'por ritmo'
        else:
            rng = f"{z['lo']}–{z['hi']}" if z['lo'] else f"≤{z['hi']}"
            rit = f"{mmss(z['ritmo_hi'])}–{mmss(z['ritmo_lo'])}" if z['lo'] else f"≥{mmss(z['ritmo_hi'])}"
        print(f"  {z['z']:<4}{z['nombre']:24}{rng:>11}{rit:>19}{z.get('rpe',''):>6}  "
              f"{z.get('habla','')}")
    print('  ' + '─' * 96)
    print(f"  ⚑ {reg['limite']}")
    if cfg['historial_tests']:
        print('\nHISTORIAL DE TESTS')
        for t in cfg['historial_tests'][-6:]:
            anc = f"LT1 {t['lt1']} / LT2 {t['lt2']}" if t.get('lt2') else 'sin anclas'
            print(f"  {t['fecha']}  {t['tipo']:<22} {anc:<20} {t.get('nota','')[:60]}")
    print()


def seg(txt):
    """'4:38' -> 278.0 segundos. Acepta tambien segundos sueltos."""
    if ':' in str(txt):
        m, sg = str(txt).split(':')
        return int(m) * 60 + float(sg)
    return float(txt)


def deriva(r1, f1, r2, f2):
    """Test B. razon = velocidad/FC en cada mitad; deriva = cuanto cae la segunda."""
    v1, v2 = 1000.0 / seg(r1), 1000.0 / seg(r2)
    q1, q2 = v1 / float(f1), v2 / float(f2)
    d = (q1 - q2) / q1 * 100
    print(f"\nTEST B — DERIVA AEROBICA")
    print(f"  1ª mitad: {r1}/km a {f1} lpm   razon {q1:.5f}")
    print(f"  2ª mitad: {r2}/km a {f2} lpm   razon {q2:.5f}")
    print(f"  deriva = {d:+.2f} %")
    if d < 5:
        print(f"  → POR DEBAJO de LT1. Sube 3 lpm (prueba {int(f1) + 3}) y repite en 2 semanas.")
    else:
        print(f"  → POR ENCIMA de LT1. Baja 3-4 lpm (prueba {int(f1) - 4}) y repite en 2 semanas.")
    print("  LT1 = la FC mas alta que todavia deja la deriva por debajo del 5 %.\n")


def garmin(cfg):
    a, g = cfg['anclas'], cfg['garmin']
    zs = [z for z in limites(cfg) if z['lo'] is not None]
    # Garmin solo admite 5 zonas: Z5 y Z6 se fusionan en la 5, que es donde se corre por ritmo.
    g5 = [(z['lo'], z['hi']) for z in zs[:4]] + [(zs[4]['lo'], a['fcmax'])]
    print(f"\nGARMIN CONNECT — {g['donde']}")
    print(f"\n  Metodo de zonas:  {g['metodo_zonas']}")
    print(f"  FC maxima:        {a['fcmax']} ppm" + ("  (provisional — pendiente Test C)" if a.get('provisional') else ""))
    print(f"  Umbral de lactato:{a['lt2']:>4} ppm  ← el campo que estaba en 186")
    print("\n  Zonas personalizadas (perfil de Carrera):")
    for i, (lo, hi) in enumerate(g5, 1):
        z = zs[i - 1]
        nom = z['nombre'] if i < 5 else f"{zs[4]['nombre']} + {zs[5]['nombre']}"
        print(f"    Zona {i}:  {max(lo, 100):>3}–{hi:<3} ppm   {nom}")
    print(f"\n  {g['nota_5_zonas']}")
    print(f"\n  IMPORTANTE: {g['desactivar']}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--lt1', type=int); p.add_argument('--lt2', type=int)
    p.add_argument('--fcmax', type=int); p.add_argument('--fcreposo', type=int)
    p.add_argument('--ritmo-lt2', dest='ritmo_lt2',
                   help='ritmo medio de los ultimos 20 min del Test A, m:ss por km. '
                        'Ancla la regresion FC<->ritmo en el punto medido.')
    p.add_argument('--fecha'); p.add_argument('--metodo', default='CR 30 min')
    p.add_argument('--garmin', action='store_true', help='que teclear en Garmin Connect')
    p.add_argument('--deriva', nargs=4, metavar=('RITMO1', 'FC1', 'RITMO2', 'FC2'),
                   help='Test B: dos mitades de 30 min (ritmo m:ss por km y FC media de cada una)')
    p.add_argument('--nota', default='')
    p.add_argument('--refit', action='store_true', help='re-ajusta la regresion FC<->ritmo')
    p.add_argument('--dias', type=int, help='con --refit: ventana de datos a usar')
    p.add_argument('--protocolo', help='A, B, C, D, E o F')
    args = p.parse_args()
    cfg = cargar()

    if args.deriva:
        deriva(*args.deriva)
        return
    if args.garmin:
        garmin(cfg)
        return

    if args.protocolo:
        clave = next((k for k in cfg['protocolos'] if k.upper().startswith(args.protocolo.upper())), None)
        if not clave:
            print('No existe ese protocolo. Hay:', ', '.join(cfg['protocolos']))
            return
        pr = cfg['protocolos'][clave]
        print(f"\n{pr['titulo']}\n  Frecuencia: {pr['cada']}")
        for seccion in ('donde', 'previo', 'pasos', 'lectura'):
            if seccion not in pr:
                continue
            val = pr[seccion]
            print(f"\n  {seccion.upper()}")
            for linea in ([val] if isinstance(val, str) else val):
                print(f"    · {linea}")
        print()
        return

    cambios = []
    if args.ritmo_lt2:
        cfg['anclas']['ritmo_lt2_s'] = round(seg(args.ritmo_lt2), 1)
        cambios.append(f"ritmo de umbral medido -> {args.ritmo_lt2}/km (ancla de la regresion)")
    if args.refit:
        pts = puntos_continuos(args.dias)
        rl = cfg['anclas'].get('ritmo_lt2_s')
        ancla = (1000.0 / rl, float(cfg['anclas']['lt2'])) if rl else None
        r = ajustar(pts, ancla=ancla)
        if not r:
            print('Datos insuficientes para ajustar (hacen falta 4+ esfuerzos continuos de 15 min).')
        else:
            a, b, n = r
            cfg['regresion_fc_ritmo'].update({'a': round(a, 2), 'b': round(b, 1), 'n': n,
                                              'ajustada': datetime.date.today().isoformat()})
            como = f"anclada en {mmss(rl)}/km @ {cfg['anclas']['lt2']} lpm" if ancla else 'libre (sin ancla de test)'
            cambios.append(f'regresion -> FC = {a:.2f}·v + {b:.1f} (n={n} de {len(pts)} puntos, {como})')
            for fecha, motivo in FC_DESCARTADA.items():
                cambios.append(f'descartado {fecha} por FC inservible: {motivo[:70]}...')

    if args.lt1 or args.lt2 or args.fcmax or args.fcreposo:
        if not args.fecha:
            print('Falta --fecha del test.')
            return
        anc = cfg['anclas']
        prev = dict(anc)
        for k, v in (('lt1', args.lt1), ('lt2', args.lt2), ('fcmax', args.fcmax), ('fcreposo', args.fcreposo)):
            if v:
                anc[k] = v
                cambios.append(f'{k}: {prev.get(k)} -> {v} lpm')
        anc['fecha'] = args.fecha
        anc['metodo'] = args.metodo
        # Cualquier test de campo real confirma las anclas; solo una estimacion las deja provisionales.
        anc['provisional'] = 'estim' in args.metodo.lower()
        cfg['historial_tests'].append({
            'fecha': args.fecha, 'tipo': args.metodo,
            'lt1': anc['lt1'], 'lt2': anc['lt2'], 'fcmax': anc['fcmax'],
            'nota': args.nota or 'Anclas actualizadas por test.'})

    if cambios:
        guardar(cfg)
        print('\nACTUALIZADO zonas.json')
        for c in cambios:
            print('  ·', c)
        print('  → ahora corre:  python3 gen_plan_v4.py   (regenera el plan con las zonas nuevas)')
    imprimir(cfg)


if __name__ == '__main__':
    main()
