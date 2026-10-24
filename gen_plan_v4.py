# -*- coding: utf-8 -*-
"""
Generador del PROYECTO SUB-16 — bloque de 18 semanas (21 sep 2026 -> 24 ene 2027).

Anclado a zonas.json: si un test cambia LT1/LT2/FCmax, se vuelve a correr esto y
todas las FC y ritmos del plan se recalculan solos.

    python3 zonas.py --lt2 173 --fecha 2026-10-01 --metodo "CR 30 min"
    python3 gen_plan_v4.py

Salidas: plan_maestro.json · PLAN_MAESTRO.csv · sesiones.html (datos embebidos)
"""
import csv, json, os, re, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
CFG = json.load(open(os.path.join(BASE, 'zonas.json'), encoding='utf-8'))
A, REG = CFG['anclas'], CFG['regresion_fc_ritmo']
ZDEF = {z['z']: z for z in CFG['zonas']}

RITMO_OBJ = 203       # s/km del objetivo de carrera en CDMX (3:23) = sub-16 a nivel del mar
META = "bajar de 17:00 en Reforma (CDMX, 2,240 m) · el sub-16 en CDMX es el proyecto largo"


# ---------------------------------------------------------------- zonas -> texto
def lim(zc):
    z = ZDEF[zc]
    if z['lo_off'] is None:
        return None, None
    lo = 0 if z['lo_off'][1] == -999 else A[z['lo_off'][0]] + z['lo_off'][1]
    return lo, A[z['hi_off'][0]] + z['hi_off'][1]


def mmss(seg):
    # Redondear seg % 60 por separado da '3:60'. Se redondea el total y luego se parte.
    s = round(seg)
    return f'{s // 60}:{s % 60:02d}'


def ritmo_fc(fc):
    return 1000.0 / ((fc - REG['b']) / REG['a'])


def Z(zc, etiqueta=True):
    """'Z4 sub-umbral (162-169)'"""
    lo, hi = lim(zc)
    if lo is None:
        return 'N neuromuscular (FC no aplica)'
    rango = f'≤{hi}' if not lo else f'{lo}-{hi}'
    return f"{zc} {ZDEF[zc]['nombre'].lower()} ({rango})" if etiqueta else f'{zc} ({rango})'


def RZ(zc):
    """'3:43-3:58' — ritmo esperado de la zona."""
    lo, hi = lim(zc)
    if lo is None:
        return '—'
    if not lo:
        return f'≥{mmss(ritmo_fc(hi))}'
    return f'{mmss(ritmo_fc(hi))}-{mmss(ritmo_fc(max(lo, 120)))}'


def techo(zc):
    return lim(zc)[1]


def ro(delta=0):
    return mmss(RITMO_OBJ + delta)


# ---------------------------------------------------------------- bloques fijos
RUTINA = ('Rutina diaria (8 min): movilidad de tobillo 2\' · 90/90 de cadera 2\' · '
          'puente de glúteo x15 · plancha 45" · respiración diafragmática 2\'')

CAL = {
 'C1': ["Movilidad dinámica 5 min: círculos de cadera · balanceo frontal 10/lado · balanceo lateral 10/lado · círculos de tobillo · rotación de tronco",
        "Caminar rápido 3 min",
        f"Arrancar 40 s/km más lento que el objetivo y subir progresivo. FC del primer km SIEMPRE ≤{techo('Z1')}",
        "⚑ En día fácil no hacen falta drills ni rectas. El trote es el calentamiento."],
 'C2': ["Movilidad dinámica 5 min",
        f"Trote progresivo 15-18 min terminando en {RZ('Z2')}. FC no debe pasar {techo('Z2')}",
        "Drills 5 min: skipping A 2x20 m · skipping B 2x20 m · talón-glúteo 2x20 m · carioca 2x20 m · taloneo rápido 2x20 m",
        "4 rectas progresivas de 80 m — la última al 95% del ritmo de la sesión. Vuelta caminando",
        "Pausa 2-3 min: hidratar y respirar",
        "⚑ Si la primera repetición es la más rápida del día, calentaste mal o salió demasiado fuerte."],
 'C3': ["Movilidad dinámica 5 min con énfasis en cadera y tobillo",
        f"Los primeros 3 km del fondo en {RZ('Z1')} — FC ≤{techo('Z1')}",
        "⚑ Esos 3 km CUENTAN dentro del volumen. Nunca salgas a ritmo de fondo desde el km 1."],
 'C4': ["Movilidad dinámica 5 min",
        f"Trote 15 min en {Z('Z1', False)} — llega a la cuesta caliente de verdad",
        "Drills 4 min + 3 rectas progresivas en llano",
        "2 subidas de aproximación: una al 70% y otra al 85%",
        "⚑ CRÍTICO: nunca arranques a máximo en frío. El riesgo de isquios es real."],
 'C5': ["Movilidad dinámica 6 min",
        "Trote 18 min: 12 min Z1 + 6 min subiendo a Z2",
        "Drills 5 min + 5 rectas de 80 m, la última a ritmo objetivo",
        "Sentarse 3 min. Banda de pecho colocada y señal comprobada ANTES de arrancar",
        "⚑ Protocolo idéntico cada vez que repitas el test: misma pista, misma hora, mismo desayuno."],
 'C6': ["T-45 min · Movilidad dinámica 6 min",
        "T-38 min · Trote progresivo 15 min",
        "T-22 min · Drills técnicos 4 min",
        f"T-16 min · 4 rectas de 80 m — la última EXACTAMENTE a {ro()}/km",
        "T-9 min · Caminar, respirar, últimos sorbos de agua, quitar ropa extra",
        "T-3 min · A la línea + 2 aceleraciones cortas",
        "⚑ Nada nuevo el día de la carrera. Todo esto se ensaya el martes y el jueves previos."],
}
VC = {
 'VC1': ["Bajar el ritmo naturalmente los últimos 5 min",
         "Caminar 3 min",
         "Estiramiento suave 30 s c/u: isquios · cuádriceps · gemelo · sóleo · flexor de cadera · glúteo"],
 'VC2': [f"Trote MUY suave 10-12 min — FC por debajo de {techo('Z1')}",
         "Caminar 3 min",
         "Estiramiento estático 6 min (30-45 s por músculo)",
         "Foam roller 5 min: cuádriceps · banda iliotibial · gemelos · glúteos",
         "Proteína + carbohidrato dentro de los 45 min",
         "⚑ Saltártela es la razón #1 de que un martes duro arruine el miércoles."],
 'VC3': ["Último km trotando suave después del tramo progresivo",
         "Caminar 5 min + hidratar con electrolitos",
         "Estiramiento 6 min · piernas en alto contra la pared 5 min",
         "Comida completa dentro de los 30-45 min. En fondos de 22+ km, 60-80 g de carbohidrato DURANTE."],
 'VC4': ["Trote suave 8-10 min",
         "Estiramiento con énfasis en isquios y gemelos",
         "⚑ Los esfuerzos máximos cargan el tendón. No te lo saltes."],
 'VC6': ["Caminar 5 min INMEDIATAMENTE al cruzar la meta — no te sientes",
         "Trote muy suave 10 min",
         "Estiramiento + hidratación con electrolitos",
         "Anotar en el mismo día: parciales, FC media/máxima, sensación por km. Se olvida en 48 h."],
}
# La fuerza es guiada en Comando Fuerza desde el 1-oct-2026. El plan sigue diciendo QUÉ
# necesita el bloque ese día: sirve para pedírselo al entrenador y como plan B los días
# que no se pueda ir. Lo que no cambia es CUÁNDO: eso lo manda la regla de la fuerza
# (correr primero, 4-6 h de separación, nunca lunes/miércoles/viernes).
GYM = 'Comando Fuerza'

PM = {
 'FA': (f"FUERZA A — Máxima (45 min) · {GYM}",
        [f"Sesión guiada en {GYM}. Lo que hoy necesita el bloque es FUERZA MÁXIMA: "
         "carga alta, pocas repeticiones, descanso largo. Nada de circuitos con poco peso y muchas reps.",
         "Sentadilla trasera 4 x 5 @ 80-85% 1RM",
         "Peso muerto rumano 3 x 6 @ 75-80%",
         "Zancada con mancuernas 3 x 8 por pierna",
         "Elevación de gemelo a 1 pierna 3 x 12",
         "Plancha frontal 3 x 45 s · Dead bug 3 x 10 por lado",
         "→ PLAN B sin gimnasio: la misma lista con mancuernas o peso corporal lastrado.",
         "→ bici o caminar 5 min + estiramiento 5 min + proteína en 30 min"]),
 'FB': (f"FUERZA B — Pliometría + Core (35 min) · {GYM}",
        [f"Sesión guiada en {GYM}. Hoy toca PLIOMETRÍA: salto y rebote, calidad de gesto. "
         "Si se degrada la técnica se corta la serie — no se completa por completarla.",
         "Salto al cajón 4 x 5 (40-50 cm)",
         "Salto con contramovimiento 3 x 6",
         "Bounding / multisaltos 4 x 20 m",
         "Peso muerto a 1 pierna 3 x 8 por pierna",
         "Puente de glúteo a 1 pierna 3 x 12 · Pallof press 3 x 10 por lado",
         "Plancha lateral 3 x 30 s por lado",
         "→ PLAN B sin gimnasio: todo esto sale en un parque, sin material.",
         "→ bici o caminar 5 min + estiramiento 5 min + proteína en 30 min"]),
 'MOV': (f"Movilidad 15 min · opcional en {GYM}",
         ["Solo movilidad y estiramiento. Cero carga.",
          f"Es el tercer día de {GYM} si lo quieres usar, pero sin tocar peso: "
          "el viernes existe para que el sábado haya fondo."]),
}


def doble(km, nota=''):
    return (f"DOBLE — Trote regenerativo {km} km",
            [f"Ritmo {RZ('Z1')}, FC por debajo de {techo('Z1')}",
             "Es volumen aeróbico barato: su único trabajo es sumar km sin fatiga.",
             nota or "Si te cuesta arrancar, camina 5 min primero. Si sigue costando, sáltalo sin culpa."])


def doble_umbral_pm(detalle, senal, km):
    return (f"2ª SESIÓN DE UMBRAL — {detalle}",
            [f"Volumen total {km} km con calentamiento y vuelta a la calma incluidos",
             f"FC techo {techo('Z5')}. Si la pasas, acortas la rep — no la aguantes.",
             f"Control sin lactómetro: {senal}",
             "⚑ Esta sesión existe porque el estímulo de umbral se acumula mejor partido en dos que junto en una."])


# ---------------------------------------------------------------- tipos de día
TIPO = {
 'rec':   ('C1', 'VC1'), 'base':  ('C1', 'VC1'), 'fondo': ('C3', 'VC3'),
 'cal':   ('C2', 'VC2'), 'cuesta': ('C4', 'VC4'), 'test':  ('C5', 'VC2'),
 'tt':    ('C2', 'VC2'), 'maxi':  ('C4', 'VC4'), 'carrera': ('C6', 'VC6'),
 'off':   (None, None), 'reentrada': ('C1', 'VC1'),
}

F = {
 0: "Fase 0: Reset",
 1: "Fase 1: Recalibración y base",
 2: "Fase 2: Re-entrada y reconstrucción",
 3: "Fase 3: Umbral — el motor",
 4: "Fase 4: Umbral + VO2 · pico de volumen",
 5: "Fase 5: Específico 5K",
 6: "Fase 6: Taper y carrera",
}

# ---------------------------------------------------------------- protocolos largos
P_TESTA = [
    "30 minutos al máximo esfuerzo SOSTENIBLE. No es un 10K ni un 5K: es lo máximo que aguantas 30 min exactos.",
    "Auto-lap cada 5 min, para poder aislar después los últimos 20.",
    "Los primeros 10 min NO pueden ser los más rápidos. Sal a un ritmo que creas sostenible; aprieta solo en los últimos 5.",
    "Banda de pecho, no muñeca: en 30 min a tope el sensor óptico se descuelga.",
    "LT2 (= LTHR) = FC MEDIA DE LOS ÚLTIMOS 20 MINUTOS. No la de los 30: los primeros 10 la ensucian mientras la FC sube.",
    "Ritmo de umbral = el ritmo medio de esos mismos 20 min. Debe coincidir con lo que la regresión predice para esa FC.",
    "Un 10K de competencia sirve igual: su FC media es LTHR ±2 lpm. Si corres uno, úsalo y ahórrate el test.",
    "Cargar: python3 zonas.py --lt2 <FC> --fecha <hoy> --metodo 'CR 30 min'   y luego gen_plan_v4.py",
]
P_TESTB = [
    f"10 min progresivos hasta la FC objetivo. Esos 10 min NO cuentan para el cálculo.",
    f"60 min continuos CLAVADO a una FC fija. Primer intento: {A['lt2'] - 18} lpm (LT2 − 18).",
    "Auto-lap cada 15 min. Se corre por FC, no por ritmo: que el ritmo baje solo es exactamente lo que se mide.",
    "Partir los 60 min en dos mitades de 30 y calcular: razón = velocidad media / FC media de cada mitad.",
    "Deriva % = (razón_1 − razón_2) / razón_1 × 100.",
    "Menos del 5 % → estás en o por debajo de LT1: sube 3 lpm y repite. Más del 5 % → estás por encima: baja 3-4 lpm.",
    "LT1 = la FC más alta que todavía deja la deriva por debajo del 5 %.",
    "Cálculo automático: python3 zonas.py --deriva <ritmo1> <fc1> <ritmo2> <fc2>",
    "Prueba del habla en la misma sesión: LT1 es lo más rápido donde aún dices una frase entera cómoda.",
]
P_TESTC = [
    "Cuesta de 3-5% de pendiente. 3 x 2 min: la 1ª al 80%, la 2ª al 90%, la 3ª a todo.",
    "2 min de bajada trotando entre repeticiones.",
    "Los últimos 30 s de la tercera: máximo absoluto, sin reservar nada.",
    "Tomar el valor más alto de los 5 s finales, NO el promedio de la repetición.",
    "Cargar: python3 zonas.py --fcmax <FC> --fecha <hoy> --metodo 'test C cuestas'",
]
P_TESTD = [
    "3000 m a tope en pista. Parciales cada 400 m.",
    "Salir al ritmo que creas sostenible, no al que quieras: los primeros 400 m deciden el test.",
    "Anotar tiempo total, parciales, FC media, FC máxima y cadencia.",
    "Predicción de 5K a la misma altitud: T5K ≈ T3000 × 1.75.",
    "Es el marcador honesto del bloque: un test a tope no se puede sobre-ejecutar.",
]
P_TESTE = [
    "Par de contrarrelojes con 48 h de separación: hoy 1200 m a tope, el sábado 3600 m a tope.",
    "CS = (3600 - 1200) / (t3600 - t1200)  en m/s.     D' = 1200 - CS × t1200  en metros.",
    "5K predicho = (5000 - D') / CS.",
    "Sin lactómetro, CS es el segundo pilar: debe coincidir con el ritmo de umbral del Test A dentro de 2-3 s/km.",
    "Comprobación extra: dos días después, 20 min clavado al ritmo de CS. La FC en la que te estabilices ES tu LT2.",
]
P_TESTF = [
    "3 x 30 m volantes con 20 m de aceleración previa. 3 min COMPLETOS entre intentos.",
    "Cronometrar solo los 30 m centrales. Anotar el mejor.",
    "Velocidad máxima = 30 / mejor tiempo (m/s).  Reserva anaeróbica = Vmax - velocidad a VO2max.",
    "Se mide una vez por bloque para confirmar lo que ya sabemos: la velocidad sobra. No para entrenarla más.",
]
PROTO = {'A': P_TESTA, 'B': P_TESTB, 'C': P_TESTC, 'D': P_TESTD, 'E': P_TESTE, 'F': P_TESTF}




# ---------------------------------------------------------------- colocacion de la fuerza
# Los dias duros se hacen duros y los faciles se dejan en paz. La fuerza maxima pide 48 h
# antes de una sesion de calidad (Ronnestad): ponerla el miercoles dejaba 20 h hasta el
# jueves. Va DESPUES de la calidad del jueves, con el viernes regenerativo absorbiendola.
# La pliometria se junta con las cuestas del domingo, que ya es el dia neuromuscular.
REPLAN = '2026-10-26'   # lunes en que arranca el bloque replanificado el 24-oct-2026


def colocar_fuerza_b1(spec):
    """Regla del bloque 1, CONGELADA.

    Las semanas ya corridas no se reescriben: analiza.py cruza plan contra ejecutado por
    fecha, y mover la pesa de un jueves de octubre convertiria el informe en una version
    retocada de lo que de verdad paso. Esta funcion existe solo para eso.
    """
    for d in spec:
        if d['pm'] in ('FA', 'FB'):
            d['pm'] = None
    jue, dom, mar = spec[3], spec[6], spec[1]
    if jue['t'] == 'cal':                       # calidad, no test a tope
        jue['pm'] = 'FA'
    elif mar['t'] == 'cal' and not (mar['pm'] or '').startswith('DU'):
        mar['pm'] = 'FA'                        # respaldo si el jueves es test
    if dom['t'] == 'cuesta':
        dom['pm'] = 'FB'
    elif mar['t'] == 'cal' and not (mar['pm'] or '').startswith('DU') and mar['pm'] != 'FA':
        mar['pm'] = 'FB'
    return spec


def colocar_fuerza(spec):
    """El gimnasio esta reservado JUEVES y DOMINGO: la fuerza vive ahi, no donde cuadre.

    La maxima pide 48 h antes de calidad (Ronnestad). El jueves por la tarde deja el
    viernes regenerativo absorbiendola y el fondo del sabado a 48 h, y da igual que el
    jueves sea calidad o rodaje facil: lo que importa es que no sea un test a tope,
    porque detras de un maximo no va nada. La pliometria se junta con las cuestas del
    domingo, que ya es el dia neuromuscular.

    Si la semana no admite las dos, se queda con una. Son 2 de los 20 dias del mes: el
    margen existe para recolocar, no para meter una tercera.
    """
    for d in spec:
        if d['pm'] in ('FA', 'FB'):
            d['pm'] = None
    jue, dom = spec[3], spec[6]
    if not jue['pm'] and jue['t'] not in ('tt', 'test', 'maxi', 'off', 'carrera'):
        jue['pm'] = 'FA'
    if not dom['pm'] and dom['t'] in ('cuesta', 'rec', 'base'):
        dom['pm'] = 'FB'
    return spec


# ---------------------------------------------------------------- semana de 7 dias
# El atleta entrena 7 dias cuando la semana le sale completa (W34, W36 y W38 de agosto-
# septiembre: 7/7). Imponer un descanso no salia de sus datos. El descanso pasa a ser
# regenerativo, y el volumen NO sube: se reparte, que es lo que baja la carga por sesion.
NOTA_VIE = ("DÍA AJUSTABLE. Regenerativo de verdad: FC por debajo de {techo}, y si dudas si vas "
            "demasiado suave, vas bien. Se puede cambiar por 40 min de bici o elíptica sin impacto. "
            "Y es el único día del plan que se puede convertir en descanso total sin recuperarlo: "
            "si el jueves salió mal, si dormiste mal o si algo molesta, hoy no corres y no pasa nada.")


def km_txt(v):
    m = re.search(r'([\d.]+)\s*km', v or '')
    return float(m.group(1)) if m else 0.0


def set_km(v, nuevo):
    return re.sub(r'[\d.]+(\s*km)', lambda m: f'{nuevo:g}{m.group(1)}', v, count=1)


def a_siete_dias(spec, compensar=True):
    """Convierte los descansos en regenerativos y devuelve el volumen a los dias faciles."""
    objetivo = sum(km_txt(d['v']) for d in spec)
    for d in spec:
        if d['t'] != 'off' or 'DESCANSO' not in d['s']:
            continue
        km = min(8, max(4, round(objetivo * 0.09)))
        d.update(t='rec', s='Regenerativo — día ajustable', v=f'{km} km',
                 r=RZ('Z1'), z=Z('Z1'), pm='MOV',
                 n=NOTA_VIE.format(techo=techo('Z1')))
    if not compensar:
        return spec
    # Devolver parte de los km anadidos, y solo desde los regenerativos: el rodaje base
    # lleva rectas y el fondo es estimulo, recortarlos deforma la semana. Con suelo de 5 km,
    # asi que si no alcanza, la semana sube un poco — que es lo correcto al anadir un dia.
    exceso = sum(km_txt(d['v']) for d in spec) - objetivo
    donantes = sorted((d for d in spec if d['t'] == 'rec' and 'ajustable' not in d['s']),
                      key=lambda d: -km_txt(d['v']))
    i = 0
    while exceso > 0 and donantes and any(km_txt(d['v']) > 5 for d in donantes):
        d = donantes[i % len(donantes)]
        if km_txt(d['v']) > 5:
            d['v'] = set_km(d['v'], km_txt(d['v']) - 1)
            exceso -= 1
        i += 1
    return spec


# ---------------------------------------------------------------- dia
def D(t, s, v, r, z, pm=None, n='', desc='', proto=None, princ=None):
    return dict(t=t, s=s, v=v, r=r, z=z, pm=pm, n=n, desc=desc, proto=proto, princ=princ or [])


OFF = D('off', 'DESCANSO TOTAL', '0 km', '—', '—', 'MOV',
        'Descanso real. El bloque anterior se rompió por semanas perdidas, no por sesiones blandas.')


def rec(km, n=''):
    return D('rec', 'Recuperación', f'{km} km', RZ('Z1'), Z('Z1'), None,
             n or f"Regenerativo estricto. FC techo {techo('Z1')}: si la pasas, caminas. Nada de 'me sentí bien'.")


def base(km, rectas=0, pm=None, n=''):
    s = 'Rodaje base' + (f' + {rectas} rectas' if rectas else '')
    extra = f" Terminar con {rectas} rectas de 100 m en progresión, vuelta caminando." if rectas else ''
    return D('base', s, f'{km} km', RZ('Z2'), Z('Z2'), pm,
             n or f"El grueso del volumen vive aquí. FC techo {techo('Z2')}.{extra}")


def fondo(km, z3=0, n=''):
    r = f"{RZ('Z2')}" + (f" + últimos {z3} km en {RZ('Z3')}" if z3 else '')
    z = Z('Z2') + (f" → {Z('Z3', False)}" if z3 else '')
    return D('fondo', 'FONDO' + (' + final progresivo' if z3 else ''), f'{km} km', r, z, None,
             n or (f"Los últimos {z3} km entran en Z3 por FC, no por ritmo: el ritmo es la consecuencia."
                   if z3 else "Fondo plano, sin final rápido. Su trabajo es el tiempo en pie, no la intensidad."))


def continuo(minutos, km_aprox, s='RE-ENTRADA — rodaje por tiempo', zc='Z1', n=''):
    """Rodaje prescrito por TIEMPO, no por distancia.

    Al volver de un paron la FC va 3-6 lpm alta para el mismo ritmo: el volumen
    plasmatico cae ~5% en una semana sin correr y tarda otra en volver. Un objetivo
    en kilometros empuja a forzar el ritmo para cerrarlo; con los minutos contando y
    la FC como techo, el kilometraje es la consecuencia — que es la regla del bloque.
    El km aproximado se conserva en el volumen para que analiza.py siga sumando."""
    return D('reentrada', s, f'{km_aprox} km aprox ({minutos} min)',
             f"{minutos} min continuos a {RZ(zc)}", Z(zc), None, n)


# ---------------------------------------------------------------- semanas
S = []
def W(lunes, etiqueta, fase, dias):
    S.append((lunes, etiqueta, fase, dias))

# ---- S0 · reset -------------------------------------------------------------
W('2026-09-21', 'Semana 0 · RESET post-carrera', F[0], [
  rec(7, "Ya corrido: 6.6 km a 5:19 con FC 137. Exactamente lo que tocaba."),
  base(8, 0, 'MOV', "Suave. Después de un 5K a tope la reparación muscular tarda 7-10 días, no 3."),
  OFF,
  base(7, 4, None, "4 rectas solo para despertar el gesto. Nada de intensidad todavía."),
  OFF,
  fondo(12, 0, "Fondo corto y plano. Esta semana no existe la palabra 'ritmo'."),
  D('off', 'DESCANSO o caminata', '0 km', '—', '—', 'MOV',
    "Último día antes de empezar el proyecto. Comprueba la banda de pecho (cargada y emparejada) y deja la pista apalabrada para el jueves 1: el Test A define las zonas de los próximos cuatro meses.")])

# ---- Fase 1 · recalibración -------------------------------------------------
W('2026-09-28', 'Semana 1 · LOS TESTS', F[1], [
  rec(6),
  base(8, 6, 'FA', "Vuelve la fuerza. Pesado: 4x5 al 80-85%. La fuerza máxima no te hace lento, te hace económico."),
  rec(6, "Muy suave: el jueves es el test que define las zonas de los próximos 4 meses."),
  D('test', 'TEST A — Contrarreloj de 30 min', '13 km total', 'Máximo esfuerzo sostenible 30 min',
    'define LT2 = FC media de los últimos 20 min', None,
    "EL DÍA MÁS IMPORTANTE DEL BLOQUE. Sin este número, todo lo demás es adivinar. "
    "El LTHR=186 del bloque pasado equivalía a ritmo de 3K: por eso ninguna sesión de umbral fue de umbral. "
    "Auto-lap cada 5 min y banda de pecho, obligatorio.",
    None, 'A'),
  OFF,
  fondo(13, 0, "Por FC, no por ritmo. Hoy todavía con las zonas viejas: techo 150 y punto."),
  D('maxi', 'TEST C — FCmax real', '7 km total', '3 x 2 min en cuesta: 80% · 90% · todo',
    'FCmax (hoy solo hay 194 observada)', None,
    "Hoy 194 es la máxima VISTA, no la máxima real. Define el techo de Z6.", '2 min bajando trotando.', 'C')])

W('2026-10-05', 'Semana 2 · Primer sub-umbral real', F[1], [
  rec(6),
  D('cal', 'SUB-UMBRAL — introducción', '11 km total', f"5 x 5 min a {RZ('Z4')}", Z('Z4'), 'FA',
    "La primera sesión de umbral de verdad de tu historia registrada. Se corre por FC, con techo "
    f"{techo('Z4')}. Si el ritmo sale más rápido, MEJOR — pero la FC no se negocia.",
    '1 min de trote entre repeticiones.'),
  base(9, 6),
  D('cal', 'TEMPO CONTINUO', '11 km total', f"20 min continuos a {RZ('Z3')}", Z('Z3'), 'FB',
    "Continuo, sin cortes. Aquí es donde el bloque pasado tenía un agujero: en 6 semanas no hubo "
    "ni un solo esfuerzo continuo entre 4:34 y 3:33 por km."),
  OFF,
  fondo(15, 3),
  D('maxi', 'TEST F — Velocidad máxima + cuestas cortas', '6 km total', '3 x 30 m volantes + 6 x 12 s cuesta',
    Z('N'), None, "Se mide una vez y no se vuelve a tocar: confirma que la velocidad te sobra.",
    'Recuperación COMPLETA: 3 min entre volantes, caminar la bajada.', 'F')])

W('2026-10-12', 'Semana 3 · Validación del umbral', F[1], [
  rec(7),
  D('cal', 'SUB-UMBRAL', '12 km total', f"6 x 6 min a {RZ('Z4')}", Z('Z4'), 'FA',
    f"36 min acumulados en Z4. El control es la FC: debe estabilizarse dentro de la zona en los "
    f"primeros 90 s de cada rep. Si entre la rep 2 y la 6 sube más de 3 lpm al mismo ritmo, "
    f"la sesión salió demasiado fuerte y la siguiente se recorta.", '1 min de trote.'),
  base(10, 6),
  D('cal', 'UMBRAL CONTINUO', '13 km total', f"2 x 12 min a {RZ('Z4')}", Z('Z4'), 'FB',
    "Bloques largos y continuos. El sábado es test, así que hoy se termina con margen.",
    '3 min de trote.'),
  OFF,
  D('test', 'TEST B — Deriva aeróbica', '17 km total',
    f"10 min progresivos + 60 min clavado a {A['lt2'] - 18} lpm", f"FC fija {A['lt2'] - 18}", None,
    "Este test ES el fondo de la semana: 60 min a FC constante. Lo que se mide no es el ritmo sino "
    "cuánto se cae solo al pasar los minutos. Auto-lap cada 15 min o no hay cómo calcularlo.", None, 'B'),
  rec(5, "Corto y suave. Mañana empieza la descarga.")])

W('2026-10-19', 'Semana 4 · DESCARGA + primer marcador', F[1], [
  rec(6, "Semana de descarga: volumen -16%. Aquí es donde se absorbe todo lo anterior."),
  D('cal', 'SUB-UMBRAL corto', '10 km total', f"4 x 6 min a {RZ('Z4')}", Z('Z4'), 'FB',
    "Solo 4 reps. Mantener el estímulo, no acumular fatiga: el jueves hay test.", '1 min de trote.'),
  base(8, 4),
  D('tt', 'TEST D — 3000 m contrarreloj', '10 km total', 'A tope, parciales cada 400 m',
    'máxima', None,
    "Primer marcador objetivo del bloque. Multiplica por 1.75 para tu 5K equivalente en CDMX. "
    "El 20 de septiembre corriste 17:47: eso son 10:10 en 3000 m. Cualquier cosa por debajo ya es progreso.",
    None, 'D'),
  OFF,
  continuo(45, 9,
    n="RE-ENTRADA. Ocho días sin correr: el último fue el viernes 16. Esto NO es el fondo "
      "de 14 km que decía aquí, porque ese fondo daba por hecha una semana de descarga que "
      "no se ejecutó. La sesión de hoy tiene un solo trabajo: volver a arrancar sin cobrar "
      f"nada. Techo {techo('Z1')} y el ritmo libre — va a salir 15-25 s/km más lento de lo "
      "normal y eso es plasma sanguíneo, no forma perdida. Si a los 20 min el cuerpo dice "
      "que no, se corta en 30 y sigue contando como sesión hecha."),
  continuo(35, 7, 'RE-ENTRADA — día 2',
    n="Misma regla: el reloj cuenta minutos y la FC pone el techo, el ritmo es lo que salga. "
      "Tres días fáciles seguidos antes de volver a tocar calidad el martes.")])

# ---- Fase 2 · re-entrada ----------------------------------------------------
# BLOQUE REPLANIFICADO EL 24-OCT-2026, desde cero, con el parón ya dentro del dato.
#
# Lo que se cambió y por qué, para que no haya que reconstruirlo de memoria:
#
# 1) FUERA EL DOBLE UMBRAL. Era el motor del plan anterior y pedía 8-9 sesiones por
#    semana. El histórico dice 5-6: 6 · 6 · 6 · 5 sesiones en las últimas cuatro semanas
#    con dato. Un plan con dobles se ejecuta como un plan sin dobles, y entonces la semana
#    no es ni una cosa ni la otra. El estímulo de umbral se acumula ALARGANDO la sesión
#    única: 24 min en Z4 en octubre, 45 min en diciembre, reps de 6 → 10 → 12 → 15 → 20 min.
#    Los códigos 'DU:' y 'DOB:' siguen vivos en resolver_pm por si el doble vuelve en el
#    bloque siguiente, pero ninguna semana de aquí los usa.
#
# 2) SE SUBE EL PISO, NO EL TECHO. El histórico es claro: las dos únicas semanas por
#    encima de 55 km (56.7 y 66.1) fueron seguidas de un desplome (-35% y -78%), y el único
#    par de semanas sostenidas de todo el registro es 49.4 → 51.0. Media 43.5 km, coeficiente
#    de variación del 30%. El problema no es que el pico sea bajo: es que la media se hunde
#    con cada desplome. Así que las descargas bajan INTENSIDAD, no volumen, y se quedan en
#    ~61-64 nominales (~50 reales, tu mejor semana sostenida); los lunes y miércoles fáciles
#    suben, y el fondo llega a 22 km. Pico nominal 78 (~62 reales), por debajo de tu máximo
#    de 66. La costumbre de volumen se construye con semanas parecidas entre sí, no con una
#    semana enorme. El volumen alto de verdad (80-100 km, base de maratón) va en el bloque
#    de febrero-mayo, sin una carrera tirando de él.
#
# 3) SEIS DÍAS, con el viernes de verdad ajustable. Es lo que se ejecuta.
#
# 4) LOS TESTS, en el orden en que sirven para algo:
#    B  07-nov  LT1 por deriva — el ancla más débil (hoy estimada; deja Z3 de 22 lpm)
#    C  15-nov  FCmax real — LT2/FCmax = 94.3% es imposible, y sin FCmax Z6 sale degenerada
#    A  19-nov  retest de 30 min → reubica LT2 y regenera el plan a 9 semanas de la carrera
#    D  10-dic  3000 m, marcador de mitad de bloque
#    A  31-dic  retest final → las zonas que gobiernan las tres semanas que deciden
#    D  14-ene  3000 m final → de aquí salen las bandas del 24-ene, no de una tabla
#    Test E (velocidad crítica) y Test F (velocidad máxima) salen del bloque: el propio
#    histórico dice que la velocidad no es el limitante y CS ya predijo 18:02 contra 17:47.
W('2026-10-26', 'Semana 5 · RE-ENTRADA', F[2], [
  rec(6, "Tercer día fácil seguido y es deliberado: hoy todavía no vuelve la calidad."),
  D('cal', 'SUB-UMBRAL corto — vuelve la calidad', '9 km total', f"4 x 6 min a {RZ('Z4')}",
    Z('Z4'), None,
    f"24 min en Z4: la sesión del 20-oct que no se corrió. Techo {techo('Z4')}, y si el ritmo no "
    "llega sin pasarlo, se cede el ritmo. Tras un parón la FC va 3-6 lpm alta para el mismo ritmo "
    "durante 3-5 sesiones — el techo manda y el ritmo vuelve solo.", '1 min de trote.'),
  base(8, 6),
  rec(6, "Jueves fácil A PROPÓSITO: en la primera semana de vuelta hay UNA sesión de calidad, "
         "no dos. La pesa sí vuelve hoy, que para eso el jueves está reservado."),
  OFF,
  fondo(12, 0, "Primer fondo tras el parón: plano y sin final progresivo. El final progresivo "
               "vuelve cuando estos 12 km salgan cómodos."),
  D('cuesta', 'CUESTAS cortas — neuromuscular', '5 km total', '6 x 20 s cuesta fuerte', Z('N'), None,
    "Seis, no diez. Es el estímulo que las piernas echan de menos después de una semana parada "
    "y es barato: 20 s no acumulan fatiga.", 'Bajar CAMINANDO. Recuperación completa.')])

W('2026-11-02', 'Semana 6 · Reconstrucción + LT1', F[2], [
  rec(6, "Semanas 6 y 7 casi iguales a propósito: el parón dejó tu carga de las últimas 4 semanas en ~37 km, y subir aquí sería un salto de 1.45 sobre ella. Primero dos semanas parecidas; la subida empieza el 23-nov."),
  D('cal', 'SUB-UMBRAL', '10 km total', f"5 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "30 min en Z4. Una repetición más que la semana pasada: eso es toda la progresión que toca.",
    '1 min de trote.'),
  base(9, 6),
  base(9, 4, None, "Jueves fácil otra vez: el sábado hay test y un test de 70 min no se corre "
                   "sobre un jueves duro. FC techo 152 y rectas al final para no apagarse."),
  OFF,
  D('test', 'TEST B — Deriva aeróbica (el del 17-oct)', '15 km total',
    f"10 min progresivos + 60 min clavado a {A['lt2'] - 18} lpm", f"FC fija {A['lt2'] - 18}", None,
    "El test perdido el 17-oct, y se corre HOY y no en la re-entrada a propósito: la deriva mide "
    "cuánto cae el ritmo a FC fija, y eso depende del volumen plasmático — justo lo que vacía un "
    "parón de ocho días. Corrido la semana pasada habría dado deriva inflada y un LT1 falsamente "
    "bajo: el mismo tipo de error que costó el bloque anterior. Con dos semanas de vuelta ya mide "
    "lo que dice medir, y hace falta, porque LT1 sigue siendo estimación y deja Z3 de 22 lpm de "
    "ancho. Este test ES el fondo de la semana. Auto-lap cada 15 min o no hay cálculo.",
    None, 'B'),
  D('cuesta', 'CUESTAS cortas', '5 km total', '8 x 20 s cuesta fuerte', Z('N'), None,
    "Suaves: ayer fueron 70 min clavados a una FC. Si las piernas pesan, 5 km Z1 y ya.",
    'Bajar CAMINANDO. Recuperación completa.')])

# ---- Fase 3 · umbral -------------------------------------------------------
W('2026-11-09', 'Semana 7 · Primera carga real + FCmax', F[3], [
  rec(6),
  D('cal', 'SUB-UMBRAL', '11 km total', f"6 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "36 min en Z4, y ya es la sesión de umbral más grande que has hecho en este bloque. El control "
    "es la deriva: si entre la rep 2 y la 6 la FC sube más de 3 lpm al mismo ritmo, salió fuerte y "
    "el jueves se recorta.", '1 min de trote.'),
  base(8, 6),
  D('cal', 'UMBRAL CONTINUO', '11 km total', f"2 x 15 min a {RZ('Z4')}", Z('Z4'), None,
    "Primera vez en bloques de 15. El objetivo es tiempo bajo tensión aeróbica, no velocidad: "
    "si el ritmo cae 3 s/km dentro del bloque pero la FC se queda en zona, el bloque es bueno.",
    '3 min de trote.'),
  OFF,
  fondo(13, 0),
  D('maxi', 'TEST C — FCmax real', '6 km total', '3 x 2 min en cuesta: 80% · 90% · todo',
    'FCmax (hoy solo hay 194 observada)', None,
    "194 es la máxima VISTA el 1-oct en los últimos 30 s de un esfuerzo de 30 min, que no es un "
    "protocolo de FCmax. Y chirría: LT2/FCmax = 94.3% cuando el rango normal es 85-90%. Si la "
    "FCmax real está 10-15 lpm más arriba, Z6 deja de salir degenerada (190-190) y el VO2 de "
    "diciembre se puede prescribir. Hoy se mide antes de que haga falta, no después. "
    "Valor = el más alto de los 5 s finales de la tercera, no el promedio.",
    '2 min bajando trotando.', 'C')])

W('2026-11-16', 'Semana 8 · DESCARGA + reubicar LT2', F[3], [
  rec(6, "Descarga de INTENSIDAD, no de volumen: los km se quedan cerca de tu mejor semana sostenida (49-51) y lo que baja es el umbral. Así la costumbre de volumen no se interrumpe cada tres semanas."),
  D('cal', 'SUB-UMBRAL de mantenimiento', '9 km total', f"4 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "Descarga: se mantiene el estímulo y se recorta el volumen. El jueves hay test a tope.",
    '1 min de trote.'),
  base(9, 4),
  D('test', 'TEST A — Retest de 30 min (7 semanas)', '11 km total',
    'Máximo esfuerzo sostenible 30 min', 'reubica LT2', None,
    "Mismo circuito y misma hora que el 1 de octubre, o el dato no es comparable. Lo que debe "
    "haber cambiado NO es la FC: es el RITMO a esa misma FC. El 1-oct fueron 3:47/km a 183 lpm. "
    "Cargar el resultado con zonas.py y regenerar: las 9 semanas que quedan se recalculan solas, "
    "y lo hacen con LT1 y FCmax ya medidos, que es la primera vez en todo el proyecto.",
    None, 'A'),
  OFF,
  fondo(13, 0, "Plano. El jueves fue a tope y la semana que viene empieza la carga de verdad."),
  D('cuesta', 'CUESTAS cortas', '5 km total', '6 x 20 s cuesta fuerte', Z('N'), None,
    "Cortas y suaves.", 'Bajar CAMINANDO. Recuperación completa.')])

W('2026-11-23', 'Semana 9 · Carga · reps largas', F[3], [
  rec(7),
  D('cal', 'UMBRAL — reps largas', '11 km total', f"4 x 10 min a {RZ('Z4')}", Z('Z4'), None,
    "40 min en Z4 en bloques de 10. Aquí empieza la parte del bloque que de verdad mueve el 5K: "
    "a partir de hoy el umbral crece alargando la repetición, no añadiendo repeticiones.",
    '2 min de trote.'),
  base(11, 6),
  D('cal', 'UMBRAL CONTINUO', '11 km total', f"3 x 12 min a {RZ('Z4')}", Z('Z4'), None,
    "36 min en tres bloques. Segunda sesión de umbral de la semana: si la del martes salió por "
    "encima del techo, esta se convierte en 2 x 12 y no pasa nada.", '2:30 de trote.'),
  OFF,
  fondo(18, 3),
  D('cuesta', 'CUESTAS largas', '6 km total', '6 x 60 s cuesta a esfuerzo de 5K', Z('N'), None,
    "Cuesta larga = fuerza específica sin impacto excéntrico. Bajar trotando suave.",
    'Bajar trotando 2-3 min.')])

W('2026-11-30', 'Semana 10 · Carga alta', F[3], [
  rec(8),
  D('cal', 'UMBRAL — bloques de 15', '12 km total', f"3 x 15 min a {RZ('Z4')}", Z('Z4'), None,
    "45 min en Z4: el máximo de umbral de todo el bloque. No hay que superarlo, hay que repetirlo "
    "limpio.", '3 min de trote.'),
  base(12, 6),
  D('cal', 'UMBRAL — reps a Z5', '11 km total', f"4 x 2000 m a {RZ('Z5')}", Z('Z5'), None,
    f"Ritmo de 10K, FC techo {techo('Z5')}. Máximo 30 min acumulados en Z5 por sesión: por encima "
    "de eso ya no es umbral, es carrera.", '2 min de trote.'),
  OFF,
  fondo(19, 4),
  D('cuesta', 'CUESTAS cortas', '6 km total', '10 x 20 s cuesta fuerte', Z('N'), None,
    "Mantenimiento neuromuscular. Mañana empieza descarga.", 'Bajar CAMINANDO.')])

W('2026-12-07', 'Semana 11 · DESCARGA + marcador', F[3], [
  rec(7, "Descarga de INTENSIDAD, no de volumen: los km se quedan cerca de tu mejor semana sostenida (49-51) y lo que baja es el umbral. Así la costumbre de volumen no se interrumpe cada tres semanas."),
  D('cal', 'SUB-UMBRAL de mantenimiento', '10 km total', f"5 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "Mantener, no cargar. El jueves hay test.", '1 min de trote.'),
  base(10, 4),
  D('tt', 'TEST D — 3000 m contrarreloj', '11 km total', 'A tope, parciales cada 400 m',
    'máxima', None,
    "Marcador de mitad de bloque, el primero de verdad del proyecto. Referencias: 10:10 = 17:47 "
    "de 5K (tu marca del 20-sep) · 9:50 = 17:12 · 9:39 = 16:53 · 9:08 = 16:00 en CDMX. "
    "Un test a tope no se puede sobre-ejecutar: sal al ritmo que creas sostenible, no al que "
    "quieras. Los primeros 400 m deciden el test.", None, 'D'),
  OFF,
  fondo(15, 0),
  D('cuesta', 'CUESTAS cortas', '5 km total', '6 x 20 s cuesta fuerte', Z('N'), None,
    "Suaves.", 'Bajar CAMINANDO.')])

# ---- Fase 4 · umbral + VO2 -------------------------------------------------
W('2026-12-14', 'Semana 12 · Entra el VO2', F[4], [
  rec(8, "El VO2 entra esta semana y el pico de volumen es la que viene: dos estímulos nuevos "
         "no se meten en la misma semana."),
  D('cal', 'UMBRAL — bloques de 20', '13 km total', f"2 x 20 min a {RZ('Z4')}", Z('Z4'), None,
    "40 min en dos bloques de 20: el formato más parecido a lo que exige un 5K rápido. Si el "
    "segundo bloque no se puede sostener en zona, se corta en 15 y se anota.", '4 min de trote.'),
  base(12, 6),
  D('cal', 'VO2max', '12 km total', f"5 x 1000 m a {ro(-8)}-{ro(-3)}", Z('Z6'), None,
    f"Por RITMO, no por FC: a tres minutos por repetición la FC llega tarde. Objetivo "
    f"{ro(-8)}-{ro(-3)}/km. UNA sola sesión de VO2 cada 7-10 días: tu reserva de velocidad ya "
    "está desarrollada, lo que falta está debajo.", '2:30 de trote — recuperación amplia de verdad.'),
  OFF,
  fondo(18, 4),
  D('cuesta', 'CUESTAS cortas', '6 km total', '8 x 20 s cuesta fuerte', Z('N'), None,
    "Muy suave: esta semana el jueves fue nuevo.", 'Bajar CAMINANDO.')])

W('2026-12-21', 'Semana 13 · PICO DE VOLUMEN', F[4], [
  rec(8, "Semana más grande del bloque. Si algo molesta hoy, se recorta HOY, no el jueves."),
  D('cal', 'UMBRAL — reps largas', '12 km total', f"4 x 10 min a {RZ('Z4')}", Z('Z4'), None,
    "40 min en Z4. Mismo trabajo que la semana 9, pero ahora con VO2 el jueves: la semana pesa "
    "más aunque la sesión sea igual.", '2 min de trote.'),
  base(12, 6),
  D('cal', 'VO2max', '12 km total', f"6 x 1000 m a {ro(-8)}-{ro(-3)}", Z('Z6'), None,
    "Seis reps. Si la última no puede ser la más rápida, se corta en cinco y no pasa nada — "
    "esa es la regla, no una concesión.", '2:30 de trote.'),
  OFF,
  fondo(22, 5, "Fondo más largo del bloque, y el primer ladrillo de la maratón: 22 km con final progresivo. 60-80 g de carbohidrato DURANTE."),
  D('cuesta', 'CUESTAS cortas', '6 km total', '8 x 20 s cuesta fuerte', Z('N'), None,
    "Mantenimiento.", 'Bajar CAMINANDO.')])

W('2026-12-28', 'Semana 14 · DESCARGA + zonas finales', F[4], [
  rec(7, "Descarga de INTENSIDAD, no de volumen: los km se quedan cerca de tu mejor semana sostenida (49-51) y lo que baja es el umbral. Así la costumbre de volumen no se interrumpe cada tres semanas."),
  D('cal', 'SUB-UMBRAL de mantenimiento', '9 km total', f"5 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "Descarga profunda: después de dos semanas de carga es aquí donde aparece la forma.",
    '1 min de trote.'),
  base(10, 4),
  D('test', 'TEST A — Retest de 30 min (zonas finales)', '11 km total',
    'Máximo esfuerzo sostenible 30 min', 'zonas de la fase específica', None,
    "Último retest del proyecto. Estas zonas gobiernan las tres semanas que deciden la carrera, "
    "así que se carga y se regenera el plan el mismo día. Mismo circuito, misma hora.",
    None, 'A'),
  OFF,
  fondo(16, 0),
  D('cuesta', 'CUESTAS cortas', '5 km total', '6 x 20 s cuesta fuerte', Z('N'), None,
    "Cortas.", 'Bajar CAMINANDO.')])

# ---- Fase 5 · específico ---------------------------------------------------
W('2027-01-04', 'Semana 15 · Específico 5K', F[5], [
  rec(7),
  D('cal', 'UMBRAL CONTINUO', '11 km total', f"3 x 12 min a {RZ('Z4')}", Z('Z4'), None,
    "El motor se mantiene mientras lo específico sube. A partir de aquí el umbral no crece más.",
    '2:30 de trote.'),
  base(10, 6),
  D('cal', 'SIMULACIÓN 5K PARTIDO', '13 km total',
    f"2000 + 1600 + 1000 + 400 a {ro()} · último a {ro(-8)}",
    Z('Z6'), None,
    f"La sesión más específica del bloque: 5000 m a ritmo objetivo ({ro()}/km) partidos en cuatro, "
    f"con recuperación decreciente. El 400 final a {ro(-8)}: así se cierra una carrera. Ese ritmo "
    "en CDMX equivale a 3:12/km a nivel del mar.", "3 min · 2:30 · 2 min de trote."),
  OFF,
  fondo(16, 4, "La fase específica no es una fase de volumen: el fondo baja de 22 a 16 para que la "
               "simulación del jueves se corra entera."),
  D('cuesta', 'CUESTAS cortas', '5 km total', '6 x 20 s cuesta fuerte', Z('N'), None,
    "Mantenimiento.", 'Bajar CAMINANDO.')])

W('2027-01-11', 'Semana 16 · Afinado + marcador final', F[5], [
  rec(6),
  D('cal', 'SUB-UMBRAL corto', '9 km total', f"4 x 6 min a {RZ('Z4')}", Z('Z4'), None,
    "Corta a propósito: el jueves es el test que fija las bandas del 24-ene.", '1 min de trote.'),
  base(9, 4),
  D('tt', 'TEST D — 3000 m contrarreloj FINAL', '11 km total', 'A tope, parciales cada 400 m',
    'máxima', None,
    "De aquí salen las bandas de la carrera, no de una tabla. x1.75 = tu 5K en CDMX; -5.3% si "
    "fuera a nivel del mar. En septiembre la carrera no se perdió por falta de fitness: el modelo "
    "predecía 18:02 y corriste 17:47. Se perdió por una banda que los datos no sostenían.",
    None, 'D'),
  OFF,
  fondo(12, 0, "Último fondo. Plano y alegre."),
  D('rec', 'Regenerativo + movilidad', '5 km', RZ('Z1'), Z('Z1'), 'MOV',
    "Última sesión de fuerza del bloque fue el domingo pasado. A partir de hoy solo movilidad: "
    "nada que deje las piernas pesadas a siete días de la carrera.")])

# ---- Fase 6 · taper --------------------------------------------------------
W('2027-01-18', 'Semana 17 · TAPER y CARRERA', F[6], [
  rec(6, "Empieza el taper: volumen -35%, intensidad se mantiene. No inventes nada esta semana."),
  D('cal', 'AFILADO', '8 km total', f"5 x 400 m a {ro(-4)}", Z('Z6'), None,
    "Recordar el ritmo, NO fatigar. Debe sentirse fácil — y si se siente fácil, NO añadas "
    "repeticiones. Ese fue exactamente el error de septiembre.", '2 min completos de trote.'),
  base(6, 4, None, "Suave con 4 rectas. FC techo Z1."),
  D('cal', 'ACTIVACIÓN', '6 km total', f"3 x 300 m a {ro(-4)}", Z('Z6'), None,
    "Última sesión con ritmo. Ensaya AQUÍ el calentamiento completo de carrera, cronómetro en mano.",
    '2 min de trote.'),
  OFF,
  D('base', 'Trote pre-carrera + rectas', '4 km + 4 x 80 m', 'Muy suave', Z('Z1'), None,
    "Soltar nervios. Ropa, dorsal, alfileres, desayuno y gel listos HOY, no mañana."),
  D('carrera', '🏁 CARRERA 5K — Reforma', '5 km', f"{ro()}/km de media · NO en parciales iguales",
    'máxima', None,
    "Mismo circuito del 20 de septiembre: ida en subida (~25 m hasta el retorno del km 2.5) y "
    "vuelta en bajada. Los parciales NO deben ser iguales. Sal 4-6 s/km MÁS LENTO que el objetivo "
    f"en los primeros 2.5 km y recupéralos en la bajada. El primer km nunca más rápido que {ro(6)}. "
    "La banda sale del 3000 m del 14 de enero, no de una tabla.",
    None, None)])

# ---------------------------------------------------------------- PM: dobles y umbral 2
SENAL5 = (f"FC {lim('Z5')[0]}-{lim('Z5')[1]}, 2-3 palabras seguidas como máximo. La FC debe estabilizarse "
          "en los primeros 90 s de cada rep y no subir más de 3 lpm entre la rep 2 y la última.")
DU = {
 '8x3':  (f"8 x 3 min a {RZ('Z5')}",  SENAL5, 9),
 '5x5':  (f"5 x 5 min a {RZ('Z5')}",  SENAL5, 9),
 '10x3': (f"10 x 3 min a {RZ('Z5')}", SENAL5, 10),
 '4x6':  (f"4 x 6 min a {RZ('Z5')}",  SENAL5, 9),
 '6x4':  (f"6 x 4 min a {RZ('Z5')}",  SENAL5, 9),
 '4x5':  (f"4 x 5 min a {RZ('Z5')}",  SENAL5, 8),
}


def resolver_pm(cod):
    """Devuelve (titulo, lineas, km_extra)."""
    if not cod:
        return '', [], 0
    if cod in PM:
        return PM[cod][0], PM[cod][1], 0
    if cod.startswith('DOB:'):
        km = int(cod.split(':')[1])
        t, l = doble(km)
        return t, l, km
    if cod.startswith('DU:'):
        det, senal, km = DU[cod.split(':')[1]]
        t, l = doble_umbral_pm(det, senal, km)
        return t, l, km
    raise KeyError(cod)


REGLAS = [
 "REGLA DEL TECHO — cada sesión tiene un techo de FC. Pasarlo más de 3 lpm durante más de 1 minuto "
 "INVALIDA la sesión, aunque el ritmo sea bueno. El bloque pasado se perdió por esto: 6x400 a 72.5 s "
 "cuando pedía 80-81, y 2x800 a 2:26.6 cuando pedía 2:39-2:42. Ir más rápido de lo prescrito no es disciplina: es cambiar de sesión.",
 "El ritmo es la CONSECUENCIA, no el objetivo. En Z1-Z5 se corre por FC. Solo Z6 y N se corren por ritmo, "
 "porque a esas duraciones la FC llega tarde.",
 "Si la última repetición no puede ser la más rápida de la serie, la sesión estuvo mal dosificada. Se corta y se anota.",
 "60-70% de los kilómetros de cada semana van en Z1-Z2. Si esa proporción baja, el volumen no está construyendo nada.",
 "Correr SIEMPRE antes de la pesa, con 4-6 h de separación. La fuerza MÁXIMA va el jueves, después de la calidad, para que el viernes regenerativo la absorba; la PLIOMETRÍA va el domingo con las cuestas, que ya es el día neuromuscular. Nunca en lunes, miércoles ni viernes: esos días existen para estar fáciles.",
 "FUERZA GUIADA EN COMANDO FUERZA — 2 sesiones por semana con carga, más el viernes de movilidad sin peso: 3 de los 20 días del mes, unos 13. Los 7 que sobran NO son días perdidos, son el margen para recolocar una sesión cuando la semana se mueve. Una cuarta sesión con carga tendría que caer en lunes, miércoles o viernes, y esos días son los que absorben el umbral: ahí la fuerza resta, no suma.",
 "Se entrena los 7 días, pero el VIERNES es el día ajustable: es el único que se puede convertir en descanso total sin recuperarlo, y el primero que se recorta cuando algo va mal. Los otros seis no se negocian.",
 "La semana perdida cuesta más que la sesión perdida. Piso mínimo: 5 sesiones y 60% del volumen semanal, aunque todo salga mal.",
 "VOLVER DE UN PARÓN SE HACE POR TIEMPO, NO POR KILÓMETROS. El volumen plasmático cae ~5% en una semana "
 "sin correr y tarda otra en volver, así que la FC va 3-6 lpm alta para el mismo ritmo durante 3-5 sesiones. "
 "Un objetivo en km empuja a forzar el ritmo para cerrarlo; con los minutos contando y la FC de techo, el "
 "kilometraje es la consecuencia. Y los tests de deriva (B) y de FCmax (C) NO se corren en una re-entrada: "
 "miden justo lo que el parón acaba de mover y devuelven un ancla falsa.",
 "Sin lactómetro, el control de la sesión de umbral es la DERIVA DE FC: la frecuencia debe estabilizarse dentro de la zona en los primeros 90 s de cada repetición, y entre la rep 2 y la última no debe subir más de 3 lpm al mismo ritmo. Si sube más, ibas por encima de LT2 aunque la media pareciera correcta.",
 "Si aparece molestia: se recorta el fondo antes que la calidad. Dos días de molestia seguidos = parar y revisar.",
 "EL UMBRAL VA EN UNA SOLA SESIÓN. El doble umbral acumula más estímulo por día, pero tu histórico "
 "dice 5-6 sesiones por semana (6 · 6 · 6 · 5 en las últimas cuatro con dato), no 8: un plan con dobles "
 "se ejecuta como un plan sin dobles y la semana queda deformada. El volumen de umbral crece ALARGANDO "
 "la repetición — 6 → 10 → 12 → 15 → 20 min — no añadiendo una segunda sesión.",
 "Todo umbral se mide a 2,240 m. A nivel del mar la misma FC da un ritmo 5-6% más rápido: se trasladan las FC, no los ritmos.",
]


def construir():
    dias, resumen = [], []
    for n_sem, (lunes, etiqueta, fase, spec) in enumerate(S):
        # La semana 0 es reset post-carrera: ahi los descansos se convierten pero NO se
        # compensa, porque 34 km sigue estando muy por debajo de su media de 47.7.
        spec = a_siete_dias([dict(x) for x in spec], compensar=(n_sem > 0 and lunes < REPLAN))
        if n_sem < 17:                  # en la semana de carrera no hay pesa
            spec = (colocar_fuerza if lunes >= REPLAN else colocar_fuerza_b1)(spec)
        d0 = datetime.date.fromisoformat(lunes)
        km_sem = 0.0
        for i, s in enumerate(spec):
            f = d0 + datetime.timedelta(days=i)
            cal_cod, vc_cod = TIPO[s['t']]
            pm_t, pm_l, pm_km = resolver_pm(s['pm'])
            principal = list(s['princ'])
            if s['proto']:
                principal += PROTO[s['proto']]
            m = re.search(r'([\d.]+)\s*km', s['v'])
            km_sem += (float(m.group(1)) if m else 0.0) + pm_km
            dias.append({
                'fecha': f.isoformat(), 'dia': DIAS[f.weekday()], 'semana': etiqueta, 'fase': fase,
                'sesion': s['s'], 'volumen': s['v'], 'ritmo': s['r'], 'zona': s['z'],
                'cal_cod': cal_cod or '—', 'cal': CAL.get(cal_cod, []) if cal_cod else [],
                'vc_cod': vc_cod or '—', 'vc': VC.get(vc_cod, []) if vc_cod else [],
                'pm_titulo': pm_t, 'pm': pm_l, 'pm_km': pm_km, 'nota': s['n'], 'rutina': RUTINA,
                'descanso': s['desc'], 'principal': principal,
            })
        resumen.append((etiqueta, lunes, km_sem))
    return dias, resumen


def escribir(dias):
    plan = {'meta': {'proyecto': 'SUB-16 en 5K', 'meta': META,
                     'carrera_objetivo': '2027-01-24',
                     'generado': datetime.datetime.now().isoformat(timespec='seconds'),
                     'anclas': {k: A[k] for k in ('lt1', 'lt2', 'fcmax', 'fecha', 'metodo', 'provisional')},
                     'ritmo_objetivo_cdmx': f'{ro()}/km'},
            'dias': dias, 'reglas': REGLAS}
    json.dump(plan, open(os.path.join(BASE, 'plan_maestro.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    hdr = ['Fecha', 'Día', 'Semana', 'Fase', 'SESIÓN', 'Volumen', 'Ritmo objetivo', 'Zona FC',
           '1. CALENTAMIENTO (completo)', '2. SESIÓN PRINCIPAL', '3. VUELTA A LA CALMA (completo)',
           '4. PM — Fuerza o doble', 'Rutina diaria (8 min)', 'Nota del coach']
    def blq(cod, lineas):
        if not lineas:
            return ''
        return f'[{cod}]\n' + '\n'.join(f'{i}. {l}' for i, l in enumerate(lineas, 1))
    # Las fechas anteriores al bloque nuevo se conservan desde PLAN_HISTORICO.csv:
    # analiza.py cruza plan vs ejecutado por fecha, y borrarlas convertiría el historial
    # del bloque 1 en "días sin plan".
    historico = []
    hist_path = os.path.join(BASE, 'PLAN_HISTORICO.csv')
    inicio = dias[0]['fecha']
    if os.path.exists(hist_path):
        for r in csv.DictReader(open(hist_path, encoding='utf-8')):
            f = (r.get('Fecha') or '').strip()
            if f and f < inicio and r.get('SESIÓN'):
                historico.append([r.get(c, '') for c in hdr])

    with open(os.path.join(BASE, 'PLAN_MAESTRO.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        w.writerows(historico)
        for d in dias:
            principal = (f"{d['sesion']}\nVolumen: {d['volumen']}\nRitmo: {d['ritmo']}\nZona: {d['zona']}"
                         + (f"\nDescanso: {d['descanso']}" if d['descanso'] else '')
                         + ('\n' + '\n'.join(f'· {l}' for l in d['principal']) if d['principal'] else ''))
            pm = (d['pm_titulo'] + '\n' + '\n'.join(f'• {l}' for l in d['pm'])) if d['pm_titulo'] else ''
            w.writerow([d['fecha'], d['dia'], d['semana'], d['fase'], d['sesion'], d['volumen'],
                        d['ritmo'], d['zona'], blq(d['cal_cod'], d['cal']), principal,
                        blq(d['vc_cod'], d['vc']), pm, d['rutina'], d['nota']])
        w.writerow([])
        w.writerow(['REGLAS DE ORO DEL BLOQUE'])
        for r in REGLAS:
            w.writerow(['', r])

    # datos embebidos del visor
    ruta = os.path.join(BASE, 'sesiones.html')
    if os.path.exists(ruta):
        html = open(ruta, encoding='utf-8').read()
        nuevo = 'const D=' + json.dumps({'dias': dias, 'reglas': REGLAS}, ensure_ascii=False) + ';'
        html2 = re.sub(r'const D=\{.*?\};', lambda _: nuevo, html, count=1, flags=re.S)
        # el visor debe mostrar los pasos del protocolo cuando existan
        if 'x.principal' not in html2:
            html2 = html2.replace(
                "${x.descanso?`<div class=\"row\"><span>Descanso entre reps</span><span>${x.descanso}</span></div>`:''}</div></div>",
                "${x.descanso?`<div class=\"row\"><span>Descanso entre reps</span><span>${x.descanso}</span></div>`:''}"
                "${x.principal&&x.principal.length?`<ul style=\"margin-top:10px\">${li(x.principal)}</ul>`:''}</div></div>")
        open(ruta, 'w', encoding='utf-8').write(html2)


if __name__ == '__main__':
    dias, resumen = construir()
    escribir(dias)
    print(f"\nPROYECTO SUB-16 · {META}")
    print(f"anclas: LT1 {A['lt1']} · LT2 {A['lt2']} · FCmax {A['fcmax']}"
          f"{'  ⚠ PROVISIONALES' if A.get('provisional') else ''}")
    print(f"ritmo objetivo de carrera en CDMX: {ro()}/km\n")
    print(f"{'semana':46}{'lunes':12}{'km':>7}")
    print('─' * 66)
    tot = 0
    for et, lun, km in resumen:
        tot += km
        print(f"{et:46}{lun:12}{km:7.0f}")
    print('─' * 66)
    print(f"{'TOTAL 18 semanas':46}{'':12}{tot:7.0f} km   (media {tot/18:.0f} km/sem)")
    # Calendario de la fuerza guiada: que dias reservar en el gimnasio, semana a semana.
    # El plan ya los coloca segun la regla (jueves la maxima, domingo la pliometria, y
    # martes cuando el martes PM no lo ocupa la 2a sesion de umbral), pero verlos juntos
    # es lo unico que sirve para apartar las clases.
    print(f"\nDÍAS DE {GYM} — qué reservar (2 con carga + viernes de movilidad):")
    print(f"{'semana':46}{'con carga':26}{'movilidad':10}")
    print('─' * 84)
    tot_carga = 0
    for et, lun, _km in resumen:
        dd = [d for d in dias if d['semana'] == et]
        carga = [f"{d['dia'][:3]} {d['fecha'][5:]}" for d in dd if d['pm_titulo'].startswith('FUERZA')]
        mov = [d['dia'][:3] for d in dd if d['pm_titulo'].startswith('Movilidad')]
        tot_carga += len(carga)
        if carga or mov:
            print(f"{et[:44]:46}{' · '.join(carga) or '—':26}{' · '.join(mov) or '—':10}")
    print('─' * 84)
    print(f"{'TOTAL sesiones con carga en 18 semanas':46}{tot_carga:>4}   "
          f"(~{tot_carga / 18 * 4.3:.0f} al mes de los 20 disponibles)")

    print(f"\nhistórico del bloque 1 conservado en PLAN_MAESTRO.csv (desde PLAN_HISTORICO.csv)")
    print(f"días generados: {len(dias)}  ·  {dias[0]['fecha']} → {dias[-1]['fecha']}")
    print("salidas: plan_maestro.json · PLAN_MAESTRO.csv · sesiones.html")
