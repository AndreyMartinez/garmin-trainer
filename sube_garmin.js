// Sube los entrenamientos del plan a Garmin Connect y los agenda en el calendario,
// para que el reloj muestre la sesion del dia lista para ejecutar.
//
//   node sube_garmin.js                 # ENSAYO: imprime lo que subiria, no toca nada
//   node sube_garmin.js --dias 14       # ensayo de los proximos 14 dias
//   node sube_garmin.js --subir         # sube y agenda de verdad
//
// El ensayo es el modo por defecto a proposito: subir escribe en tu cuenta de Garmin.
//
// AVISO: usa los mismos endpoints no oficiales que la web de Garmin (workout-service).
// No hay API publica de entrenamientos para cuentas individuales. Si Garmin los cambia,
// esto deja de funcionar y hay que ajustarlo; la extraccion (garmin.js) seguiria igual.
const fs = require('fs');
const path = require('path');

(function loadEnv() {
    try {
        const p = path.join(__dirname, '.env');
        if (!fs.existsSync(p)) return;
        for (const line of fs.readFileSync(p, 'utf8').split('\n')) {
            const t = line.trim();
            if (!t || t.startsWith('#')) continue;
            const i = t.indexOf('=');
            if (i === -1) continue;
            const k = t.slice(0, i).trim();
            if (!(k in process.env)) process.env[k] = t.slice(i + 1).trim();
        }
    } catch (e) { /* noop */ }
})();

const args = process.argv.slice(2);
const SUBIR = args.includes('--subir');
// --diff: entra a Garmin, compara huella por huella y dice que haria, pero NO escribe.
// El ensayo normal no puede saberlo: la huella vieja vive en la descripcion del
// entrenamiento que ya esta en la cuenta, asi que hay que leerla de alli.
const DIFF = args.includes('--diff');
// --semana: la semana que viene, contada desde manana. Pensado para correr
// el domingo por la noche y dejar lista la semana que empieza el lunes.
const SEMANA = args.includes('--semana');
const DIAS = SEMANA ? 7 : parseInt((args[args.indexOf('--dias') + 1]) || '7', 10);
const DESDE = args.includes('--desde') ? args[args.indexOf('--desde') + 1]
    : SEMANA ? manana() : hoyLocal();

const PLAN = JSON.parse(fs.readFileSync(path.join(__dirname, 'plan_maestro.json'), 'utf8'));
const ZONAS = JSON.parse(fs.readFileSync(path.join(__dirname, 'zonas.json'), 'utf8'));

/** Dias que ya tienen actividad registrada: agendarles un entrenamiento no tiene sentido. */
const YA_ENTRENADOS = (() => {
    const hist = path.join(__dirname, 'historial_entrenamientos.json');
    if (!fs.existsSync(hist)) return new Set();
    return new Set(Object.values(JSON.parse(fs.readFileSync(hist, 'utf8')))
        .map((a) => (a.Fecha || '').slice(0, 10)).filter(Boolean));
})();

function hoyLocal(desplaza) {
    const d = new Date();
    if (desplaza) { d.setDate(d.getDate() + desplaza); }
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function manana() { return hoyLocal(1); }

// ---------------------------------------------------------------- utilidades
const seg = (t) => { const [m, s] = t.split(':'); return +m * 60 + parseFloat(s); };
const ms = (t) => 1000 / seg(t);                       // ritmo m:ss por km -> m/s
const km = (txt) => { const m = /([\d.]+)\s*km/.exec(txt || ''); return m ? parseFloat(m[1]) : 0; };
const ensancha = (t, d) => { const s = seg(t) + d; return `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`; };

/** Rango de pulsaciones escondido en la cadena de zona: "Z4 sub-umbral (162-169)". */
function fcDe(zona) {
    let m = /\((\d{2,3})\s*[-–]\s*(\d{2,3})\)/.exec(zona || '');
    if (m) return [+m[1], +m[2]];
    m = /≤\s*(\d{2,3})/.exec(zona || '');
    if (m) return [Math.max(90, +m[1] - 25), +m[1]];
    m = /(\d{2,3})\s*lpm/.exec(zona || '');
    if (m) return [+m[1] - 3, +m[1] + 3];
    return null;
}

function techoZona(z) {
    const zd = ZONAS.zonas.find((x) => x.z === z);
    const a = ZONAS.anclas;
    return a[zd.hi_off[0]] + zd.hi_off[1];
}

/** [piso, techo] de una zona en lpm, para un objetivo de FC de Garmin. */
function rangoZona(z) {
    const zd = ZONAS.zonas.find((x) => x.z === z);
    const a = ZONAS.anclas;
    const lo = zd.lo_off[1] === -999 ? 90 : a[zd.lo_off[0]] + zd.lo_off[1];
    return [lo, techoZona(z)];
}

/** Segundos de recuperacion a partir del campo "descanso" del plan. */
function recSeg(txt) {
    if (!txt) return null;
    let m = /(\d+):(\d\d)/.exec(txt);
    if (m) return +m[1] * 60 + +m[2];
    m = /(\d+)\s*min/.exec(txt);
    if (m) return +m[1] * 60;
    m = /(\d+)\s*s\b/.exec(txt);
    if (m) return +m[1];
    return null;
}

// ---------------------------------------------------------------- pasos Garmin
let orden = 1;
const TIPO = { warmup: 1, cooldown: 2, interval: 3, recovery: 4, rest: 5, repeat: 6 };

function paso(tipo, fin, valor, objetivo, nota, childId) {
    const p = {
        type: 'ExecutableStepDTO', stepId: null, stepOrder: orden++,
        childStepId: childId ?? null, description: nota || null,
        stepType: { stepTypeId: TIPO[tipo], stepTypeKey: tipo },
        endCondition: fin === 'time'
            ? { conditionTypeId: 2, conditionTypeKey: 'time' }
            : fin === 'distance'
                ? { conditionTypeId: 3, conditionTypeKey: 'distance' }
                : { conditionTypeId: 1, conditionTypeKey: 'lap.button' },
        endConditionValue: valor ?? null,
        preferredEndConditionUnit: fin === 'distance' ? { unitKey: 'kilometer' } : null,
        targetType: { workoutTargetTypeId: 1, workoutTargetTypeKey: 'no.target' },
        targetValueOne: null, targetValueTwo: null, zoneNumber: null
    };
    if (objetivo && objetivo.fc) {
        p.targetType = { workoutTargetTypeId: 4, workoutTargetTypeKey: 'heart.rate.zone' };
        [p.targetValueOne, p.targetValueTwo] = objetivo.fc;
    } else if (objetivo && objetivo.ritmo) {
        p.targetType = { workoutTargetTypeId: 6, workoutTargetTypeKey: 'pace.zone' };
        // Garmin espera m/s, y el valor menor primero.
        const [a, b] = objetivo.ritmo.map(ms).sort((x, y) => x - y);
        p.targetValueOne = +a.toFixed(4);
        p.targetValueTwo = +b.toFixed(4);
    }
    return p;
}

function repetir(n, hijos) {
    const grupo = {
        type: 'RepeatGroupDTO', stepId: null, stepOrder: orden++,
        stepType: { stepTypeId: TIPO.repeat, stepTypeKey: 'repeat' },
        childStepId: 1, numberOfIterations: n, smartRepeat: false,
        endCondition: { conditionTypeId: 7, conditionTypeKey: 'iterations' },
        endConditionValue: n, workoutSteps: hijos || []
    };
    if (hijos) conHijos(grupo, hijos);
    return grupo;
}

/** Cuelga los hijos de un grupo ya creado. Separado de repetir() para poder reservar
 *  el orden del grupo ANTES de construir los hijos: Garmin ejecuta por stepOrder, y
 *  si los hijos se crean primero se quedan con los numeros bajos y el calentamiento
 *  acaba numerado despues de las series. */
function conHijos(grupo, hijos) {
    grupo.workoutSteps = hijos;
    hijos.forEach((h) => { h.childStepId = 1; });
    return grupo;
}

// --------------------------------------------------- calentamiento y vuelta a la calma
// El plan ya trae el calentamiento desglosado (cal_cod C1..C6 y las lineas de texto en
// cal). Antes todo eso se aplastaba en UN paso de 18 min con el detalle metido en la
// descripcion, asi que en el reloj la diferencia entre "18 min de trote" y
// "12 min Z1 + 6 min a Z2 + drills + 5 rectas de 80 m" no existia: se corria lo primero.
// Aqui cada codigo se traduce a los pasos que el reloj sabe guiar.
//
// Los bloques sin ritmo medible (movilidad, drills, estiramiento) van a golpe de VUELTA:
// son una lista de control que hay que cerrar, no un cronometro.

const GATE = (txt) => paso('warmup', 'lap', null, null, txt);
const rectas = (n, dist, nota) => repetir(n, [
    paso('interval', 'distance', dist, null, nota),
    paso('recovery', 'lap', null, null, 'Vuelta caminando — recuperacion completa')
]);

const CAL = {
    // Dia facil: el trote ES el calentamiento. Solo se separa el primer km, que por
    // regla del plan va en Z1 aunque la sesion sea de Z2.
    C1: (d) => {
        const ps = [GATE('Movilidad dinamica 5 min (cadera · balanceos · tobillo · tronco) '
            + '+ caminar rapido 3 min. Pulsa VUELTA al empezar a trotar.')];
        if (!/^Z1/.test(d.zona || '')) {
            ps.push(paso('warmup', 'distance', 1000, { fc: [90, techoZona('Z1')] },
                `Primer km 40 s/km mas lento que el objetivo. FC <= ${techoZona('Z1')} SIEMPRE.`));
        }
        return ps;
    },
    // Dia de calidad: progresivo + drills + 4 rectas + pausa.
    C2: () => [
        GATE('Movilidad dinamica 5 min. Pulsa VUELTA al empezar a trotar.'),
        paso('warmup', 'time', 16 * 60, { fc: [100, techoZona('Z2')] },
            `Trote progresivo 16 min terminando en Z2. FC no debe pasar ${techoZona('Z2')}.`),
        GATE('Drills 5 min: skipping A 2x20 m · skipping B 2x20 m · talon-gluteo 2x20 m '
            + '· carioca 2x20 m · taloneo rapido 2x20 m'),
        rectas(4, 80, 'Recta progresiva de 80 m — la ULTIMA al 95% del ritmo de la sesion'),
        paso('rest', 'time', 150, null, 'Pausa 2-3 min: hidratar y respirar'),
    ],
    // Fondo: los primeros 3 km en Z1 y CUENTAN dentro del volumen del dia.
    C3: () => [
        GATE('Movilidad dinamica 5 min con enfasis en cadera y tobillo'),
        paso('warmup', 'distance', 3000, { fc: [90, techoZona('Z1')] },
            `Primeros 3 km del fondo en Z1 — FC <= ${techoZona('Z1')}. Cuentan en el total.`),
    ],
    // Cuestas y esfuerzos maximos: llegar caliente de verdad, con aproximaciones.
    C4: () => [
        GATE('Movilidad dinamica 5 min'),
        paso('warmup', 'time', 15 * 60, { fc: [90, techoZona('Z1')] },
            `Trote 15 min en Z1 (<= ${techoZona('Z1')}) — llega a la cuesta caliente`),
        GATE('Drills 4 min'),
        rectas(3, 80, 'Recta progresiva de 80 m en llano'),
        repetir(2, [
            paso('interval', 'lap', null, null,
                'Subida de aproximacion: la 1a al 70%, la 2a al 85%. Nunca a maximo en frio.'),
            paso('recovery', 'lap', null, null, 'Bajada trotando')
        ]),
    ],
    // Tests: el protocolo es el test. Doce minutos en Z1 y seis subiendo a Z2 NO son
    // dieciocho minutos de trote: de eso depende que la FC del test sea comparable.
    C5: () => [
        GATE('Movilidad dinamica 6 min'),
        paso('warmup', 'time', 12 * 60, { fc: [90, techoZona('Z1')] },
            `12 min en Z1 — FC por debajo de ${techoZona('Z1')}`),
        paso('warmup', 'time', 6 * 60, { fc: rangoZona('Z2') },
            `6 min subiendo a Z2 (${rangoZona('Z2').join('-')}) — terminar justo en el techo`),
        GATE('Drills 5 min'),
        rectas(5, 80, 'Recta de 80 m — la QUINTA a ritmo objetivo del test'),
        paso('rest', 'time', 180, null,
            'Sentarse 3 min. Banda de pecho colocada y senal COMPROBADA antes de arrancar.'),
    ],
    // Dia de carrera: la cuenta atras, con los tiempos del plan.
    C6: () => [
        GATE('T-45 · Movilidad dinamica 6 min'),
        paso('warmup', 'time', 15 * 60, { fc: [100, techoZona('Z2')] }, 'T-38 · Trote progresivo 15 min'),
        GATE('T-22 · Drills tecnicos 4 min'),
        rectas(4, 80, 'T-16 · Recta de 80 m — la ultima EXACTAMENTE a ritmo de carrera'),
        paso('rest', 'time', 7 * 60, null,
            'T-9 · Caminar, respirar, ultimos sorbos, quitar ropa extra. T-3 · a la linea + 2 aceleraciones.'),
    ],
};

const VC = {
    VC1: () => [
        paso('cooldown', 'time', 3 * 60, null, 'Caminar 3 min (el ritmo ya venia bajando los ultimos 5)'),
        paso('cooldown', 'lap', null, null,
            'Estiramiento suave 30 s c/u: isquios · cuadriceps · gemelo · soleo · flexor · gluteo'),
    ],
    VC2: () => [
        paso('cooldown', 'time', 11 * 60, { fc: [90, techoZona('Z1')] },
            `Trote MUY suave 11 min — FC por debajo de ${techoZona('Z1')}`),
        paso('cooldown', 'lap', null, null,
            'Caminar 3 min · estiramiento estatico 6 min · foam roller 5 min · proteina + carbo en 45 min'),
    ],
    VC3: () => [
        paso('cooldown', 'distance', 1000, { fc: [90, techoZona('Z1')] }, 'Ultimo km trotando suave'),
        paso('cooldown', 'lap', null, null,
            'Caminar 5 min + electrolitos · estiramiento 6 min · piernas en alto 5 min · comida en 30-45 min'),
    ],
    VC4: () => [
        paso('cooldown', 'time', 9 * 60, { fc: [90, techoZona('Z1')] }, 'Trote suave 9 min'),
        paso('cooldown', 'lap', null, null,
            'Estiramiento con enfasis en isquios y gemelos. Los maximos cargan el tendon: no te lo saltes.'),
    ],
    VC6: () => [
        paso('cooldown', 'time', 5 * 60, null, 'Caminar 5 min INMEDIATAMENTE al cruzar la meta — no te sientes'),
        paso('cooldown', 'time', 10 * 60, { fc: [90, techoZona('Z1')] }, 'Trote muy suave 10 min'),
        paso('cooldown', 'lap', null, null,
            'Estiramiento + electrolitos. Anotar HOY: parciales, FC media/maxima, sensacion por km.'),
    ],
};

/** Pasos de calentamiento del dia. Sin codigo reconocido, nada: mejor vacio que inventado. */
const calentar = (d) => (CAL[d.cal_cod] || (() => []))(d);
const enfriar = (d) => (VC[d.vc_cod] || (() => []))(d);

/** Km que el calentamiento ya se come del volumen del dia (C3 y el primer km de C1). */
function kmCalentamiento(d) {
    if (d.cal_cod === 'C3') return 3;
    if (d.cal_cod === 'C1' && !/^Z1/.test(d.zona || '')) return 1;
    return 0;
}

/** Km que la vuelta a la calma se come del volumen: VC3 remata el fondo con 1 km suave. */
const kmVuelta = (d) => (d.vc_cod === 'VC3' ? 1 : 0);

/** Lista de recuperaciones del campo descanso: "3 min · 2:30 · 2 min de trote" -> [180,150,120] */
function recLista(txt) {
    if (!txt) return [];
    return String(txt).split('·').map((t) => recSeg(t)).filter((v) => v);
}

// ---------------------------------------------------------------- traduccion del plan
function construirPasos(d) {
    orden = 1;
    const r = (d.ritmo || '').trim();
    const fc = fcDe(d.zona);
    const rec = recSeg(d.descanso);
    // El calentamiento se construye SIEMPRE primero: paso() lleva un contador de orden
    // y Garmin ejecuta por ese numero, no por la posicion en el array.
    const cal = calentar(d);
    const kmCal = kmCalentamiento(d);
    let m;

    // 1) Reps por TIEMPO:  "5 x 6 min a 3:43-3:58"
    if ((m = /^(\d+)\s*x\s*(\d+)\s*min\s*a\s*(\d+:\d\d)(?:\s*[-–]\s*(\d+:\d\d))?/.exec(r))) {
        const grupo = repetir(+m[1], null);
        const hijos = [paso('interval', 'time', +m[2] * 60, { fc }, `${m[2]} min · ${m[3]}${m[4] ? '-' + m[4] : ''}`)];
        if (rec) hijos.push(paso('recovery', 'time', rec, { fc: [90, techoZona('Z1')] }, d.descanso));
        return [...cal, conHijos(grupo, hijos), ...enfriar(d)];
    }
    // 2) Reps por DISTANCIA:  "4 x 2000 m a 3:30-3:41"  ·  "6 x 1000 m a 3:23"
    if ((m = /^(\d+)\s*x\s*(\d+)\s*m\s*a\s*(\d+:\d\d)(?:\s*[-–]\s*(\d+:\d\d))?/.exec(r))) {
        // Un ritmo unico no es rango: se abre +/-3 s/km para que Garmin lo acepte.
        const ritmo = m[4] ? [m[3], m[4]] : [ensancha(m[3], -3), ensancha(m[3], 3)];
        const porRitmo = /^(Z6|N)\b/.test(d.zona || '') || !fc;
        const obj = porRitmo ? { ritmo } : { fc };
        const grupo = repetir(+m[1], null);
        const hijos = [paso('interval', 'distance', +m[2], obj, `${m[2]} m · ${m[3]}${m[4] ? '-' + m[4] : ''}`)];
        if (rec) hijos.push(paso('recovery', 'time', rec, { fc: [90, techoZona('Z1')] }, d.descanso));
        return [...cal, conHijos(grupo, hijos), ...enfriar(d)];
    }
    // 3) Cuestas y rectas:  "10 x 20 s cuesta fuerte"  ·  "6 x 60 s cuesta"
    if ((m = /^(\d+)\s*x\s*(\d+)\s*s\b/.exec(r))) {
        const grupo = repetir(+m[1], null);
        const hijos = [paso('interval', 'time', +m[2], null, r),
                       paso('recovery', 'lap', null, null, d.descanso || 'Recuperacion completa')];
        return [...cal, conHijos(grupo, hijos), ...enfriar(d)];
    }
    // 3b) Reps por TIEMPO sin ritmo (cuestas y maximos): "3 x 2 min en cuesta: 80% · 90% · todo"
    if ((m = /^(\d+)\s*x\s*(\d+)\s*min\b/.exec(r)) && !/\d+:\d\d/.test(r)) {
        const grupo = repetir(+m[1], null);
        const hijos = [paso('interval', 'time', +m[2] * 60, null, r)];
        const rr = recSeg(d.descanso);
        hijos.push(rr ? paso('recovery', 'time', rr, null, d.descanso)
                      : paso('recovery', 'lap', null, null, d.descanso || 'Recuperacion completa'));
        return [...cal, conHijos(grupo, hijos), ...enfriar(d)];
    }
    // 3c) Tempo continuo cronometrado: "20 min continuos a 4:00-4:38"
    if ((m = /^(\d+)\s*min\s*continuos?\s*a\s*(\d+:\d\d)(?:\s*[-–]\s*(\d+:\d\d))?/.exec(r))) {
        return [...cal,
            paso('interval', 'time', +m[1] * 60, { fc },
                `${m[1]} min continuos · ${m[2]}${m[3] ? '-' + m[3] : ''}`),
            ...enfriar(d)];
    }
    // 3d) Escalera descendente: "2000 + 1600 + 1000 + 400 a 3:23", con una recuperacion
    //     distinta por hueco. La ultima rep no lleva recuperacion detras.
    if ((m = /^(\d{3,5}(?:\s*\+\s*\d{3,5})+)\s*a\s*(\d+:\d\d)(?:\s*[-–]\s*(\d+:\d\d))?/.exec(r))) {
        const tramos = m[1].split('+').map((t) => parseInt(t.trim(), 10));
        const ritmo = m[3] ? [m[2], m[3]] : [ensancha(m[2], -3), ensancha(m[2], 3)];
        const recs = recLista(d.descanso);
        const pasos = [...cal];
        tramos.forEach((dist, i) => {
            pasos.push(paso('interval', 'distance', dist, { ritmo }, `${dist} m · ${m[2]}`));
            if (i < tramos.length - 1) {
                const rr = recs[i] ?? recs[recs.length - 1];
                pasos.push(rr ? paso('recovery', 'time', rr, { fc: [90, techoZona('Z1')] },
                                     `Trote ${Math.round(rr / 60)}' entre tramos`)
                              : paso('recovery', 'lap', null, null, 'Trote de recuperacion'));
            }
        });
        return [...pasos, ...enfriar(d)];
    }
    // 3e) Dos bloques distintos en la misma sesion: "3 x 30 m volantes + 6 x 12 s cuesta"
    if ((m = /^(\d+)\s*x\s*(\d+)\s*m\s*(\w+)\s*\+\s*(\d+)\s*x\s*(\d+)\s*s\s*(.*)$/.exec(r))) {
        const g1 = repetir(+m[1], null);
        const h1 = [paso('interval', 'distance', +m[2], null, `${m[2]} m ${m[3]} (con 20 m de aceleracion previa)`),
                    paso('recovery', 'lap', null, null, 'Recuperacion COMPLETA: 3 min')];
        const g2 = repetir(+m[4], null);
        const h2 = [paso('interval', 'time', +m[5], null, `${m[5]} s ${m[6] || 'cuesta'}`),
                    paso('recovery', 'lap', null, null, 'Caminar la bajada')];
        return [...cal, conHijos(g1, h1), conHijos(g2, h2), ...enfriar(d)];
    }
    // 4) Rodaje con final progresivo:  "4:24-4:59 + últimos 5 km en 4:01-4:21"
    if ((m = /^(\d+:\d\d)\s*[-–]\s*(\d+:\d\d)\s*\+\s*últimos\s*(\d+)\s*km\s*en\s*(\d+:\d\d)\s*[-–]\s*(\d+:\d\d)/.exec(r))) {
        const total = km(d.volumen), fin = +m[3];
        // El calentamiento y el ultimo km suave ya van en pasos propios: restarlos,
        // o el fondo sale 4 km mas largo que lo que dice el plan.
        const base = total - fin - kmCal - kmVuelta(d);
        return [
            ...cal,
            paso('interval', 'distance', base * 1000, { fc }, `Base · ${m[1]}-${m[2]}`),
            paso('interval', 'distance', fin * 1000, { fc: [fcDe(d.zona.split('→')[1]) || fc][0] || fc },
                `Final progresivo · ${m[4]}-${m[5]}`),
            ...enfriar(d)
        ];
    }
    // 5) Rodaje continuo:  "≥5:02"  ·  "4:24-4:59"  ·  "Muy suave"
    if (/^(≥|\d+:\d\d\s*[-–])/.test(r) || /^Muy suave/i.test(r)) {
        const total = km(d.volumen);
        if (total) {
            const pasos = [...cal,
                paso('interval', 'distance', (total - kmCal - kmVuelta(d)) * 1000, { fc }, d.ritmo)];
            const n = /(\d+)\s*rectas/.exec(d.sesion);
            if (n) {
                const grupo = repetir(+n[1], null);
                pasos.push(conHijos(grupo, [
                    paso('interval', 'distance', 100, null, 'Recta de 100 m en progresion'),
                    paso('recovery', 'lap', null, null, 'Vuelta caminando')
                ]));
            }
            return [...pasos, ...enfriar(d)];
        }
    }
    // 6a) Test B: "10 min progresivos + 60 min clavado a 152 lpm". La duracion ES
    //     el protocolo, asi que va como pasos cronometrados, no a golpe de boton.
    if ((m = /^(\d+)\s*min\s*progresivos\s*\+\s*(\d+)\s*min\s*clavado\s*a\s*(?:la FC de \w+ \()?(\d+)/.exec(r))) {
        const objetivo = +m[3];
        return [
            paso('warmup', 'time', +m[1] * 60, { fc: [100, objetivo] },
                `Subir progresivo hasta ${objetivo} lpm. Estos ${m[1]} min NO cuentan.`),
            paso('interval', 'time', +m[2] * 60, { fc: [objetivo - 2, objetivo + 2] },
                `${m[2]} min clavado a ${objetivo} lpm. Auto-lap cada 15 min.`),
            ...enfriar(d)
        ];
    }
    // 6b) Contrarreloj con duracion fija: "Maximo esfuerzo sostenible 30 min".
    if ((m = /(\d+)\s*min/.exec(r)) && /m[áa]ximo|tope/i.test(r)) {
        return [...cal, paso('interval', 'time', +m[1] * 60, null, r), ...enfriar(d)];
    }
    // 6c) Contrarreloj por distancia: la distancia esta en el nombre del test
    //     ("TEST D — 3000 m contrarreloj"). Mejor un paso de distancia que un boton.
    if (/tope/i.test(r) && (m = /(\d{3,5})\s*m\b/.exec(d.sesion))) {
        return [...cal, paso('interval', 'distance', +m[1], null, r), ...enfriar(d)];
    }
    // 6d) Lo demas (simulaciones, carrera): estructura minima y el
    //     protocolo en la descripcion. Nunca inventar pasos para un test a tope.
    const pasos = [...cal, paso('interval', 'lap', null, fc ? { fc } : null, r || d.sesion)];
    if (!/CARRERA/.test(d.sesion)) pasos.push(...enfriar(d));
    return pasos;
}

/** Renumera stepOrder en profundidad. Garmin ejecuta por ese numero, y las ramas que
 *  construyen un calentamiento y luego no lo usan dejan huecos; mejor no depender
 *  de la suerte y numerar 1..n al final, grupo antes que sus hijos. */
function renumerar(pasos) {
    let i = 1;
    const anda = (lista) => lista.forEach((p) => {
        p.stepOrder = i++;
        if (p.type === 'RepeatGroupDTO') anda(p.workoutSteps);
    });
    anda(pasos);
    return pasos;
}

// Huella del contenido de la sesion. Si un test mueve las zonas y el plan se regenera,
// el entrenamiento ya subido conserva los objetivos VIEJOS y el control por nombre lo
// daria por bueno. La huella detecta ese caso y obliga a reemplazarlo.
function huella(pasos) {
    const crypto = require('crypto');
    // Solo lo que cambia la EJECUCION: tipo de paso, duracion y objetivo. Las descripciones
    // llevan el ritmo estimado, que se mueve en cada --refit sin que el objetivo cambie;
    // incluirlas provocaria reemplazar la semana entera por un texto distinto.
    const esencia = (p) => p.type === 'RepeatGroupDTO'
        ? ['rep', p.numberOfIterations, p.workoutSteps.map(esencia)]
        : [p.stepType.stepTypeKey, p.endCondition.conditionTypeKey, p.endConditionValue,
           p.targetType.workoutTargetTypeKey, p.targetValueOne, p.targetValueTwo];
    return crypto.createHash('sha1').update(JSON.stringify(pasos.map(esencia)))
        .digest('hex').slice(0, 10);
}

const MARCA = /\[plan:([0-9a-f]{10})\]/;

function nombre(d) {
    const sem = /Semana (\d+)/.exec(d.semana);
    const s = d.sesion.replace(/ — .*/, '').replace('🏁 ', '');
    return `S${sem ? sem[1].padStart(2, '0') : '??'} ${d.dia.slice(0, 3)} · ${s}`.slice(0, 80);
}

/** Un dia con bloque PM es doble jornada: dos sesiones, no una sesion con apendice.
 *  Va en la PRIMERA linea de la descripcion para que se vea en el reloj sin desplazar. */
const esDoble = (d) => !!(d.pm_titulo && d.pm_titulo.trim());

function descripcion(d) {
    const partes = [];
    if (esDoble(d)) partes.push(`== DOBLE JORNADA ==  AM: esta sesion  |  PM: ${d.pm_titulo}`);
    partes.push(`${d.volumen} · ${d.ritmo} · ${d.zona}`);
    if (d.descanso) partes.push(`Rec: ${d.descanso}`);
    if (d.principal && d.principal.length) partes.push(d.principal.join(' | '));
    if (d.nota) partes.push(`COACH: ${d.nota}`);
    if (esDoble(d) && d.pm && d.pm.length) partes.push(`PM · ${d.pm_titulo}: ${d.pm.join(' | ')}`);
    return partes.join('\n').slice(0, 960);
}

function workout(d) {
    const pasos = renumerar(construirPasos(d));
    const marca = huella(pasos);
    return {
        sportType: { sportTypeId: 1, sportTypeKey: 'running' },
        workoutName: nombre(d),
        description: descripcion(d) + `\n[plan:${marca}]`,
        _huella: marca,
        workoutSegments: [{
            segmentOrder: 1,
            sportType: { sportTypeId: 1, sportTypeKey: 'running' },
            workoutSteps: pasos
        }]
    };
}

// ---------------------------------------------------------------- resumen legible
function resumir(w, d) {
    const linea = (p, ind) => {
        if (p.type === 'RepeatGroupDTO') {
            return [`${ind}${p.numberOfIterations} x`].concat(
                p.workoutSteps.map((h) => linea(h, ind + '    '))).flat();
        }
        const fin = p.endCondition.conditionTypeKey === 'time'
            ? (p.endConditionValue < 60 ? `${p.endConditionValue} s` : `${+(p.endConditionValue / 60).toFixed(1)} min`)
            : p.endCondition.conditionTypeKey === 'distance' ? `${p.endConditionValue} m`
                : 'hasta pulsar vuelta';
        let obj = '';
        if (p.targetType.workoutTargetTypeKey === 'heart.rate.zone') obj = ` @ FC ${p.targetValueOne}-${p.targetValueTwo}`;
        if (p.targetType.workoutTargetTypeKey === 'pace.zone') {
            const r = (v) => { const t = Math.round(1000 / v); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`; };
            obj = ` @ ${r(p.targetValueTwo)}-${r(p.targetValueOne)}/km`;
        }
        return [`${ind}${p.stepType.stepTypeKey.padEnd(9)} ${fin}${obj}`];
    };
    console.log(`\n  ${d.fecha}  ${d.dia.slice(0, 3)}  ${w.workoutName}`);
    if (esDoble(d)) console.log(`      ** DOBLE JORNADA — PM: ${d.pm_titulo}`);
    w.workoutSegments[0].workoutSteps.forEach((p) => linea(p, '      ').forEach((l) => console.log(l)));
}

// ---------------------------------------------------------------- principal
(async function main() {
    const desde = DESDE;
    const hasta = new Date(new Date(desde + 'T12:00:00').getTime() + (DIAS - 1) * 86400000);
    const hastaStr = `${hasta.getFullYear()}-${String(hasta.getMonth() + 1).padStart(2, '0')}-${String(hasta.getDate()).padStart(2, '0')}`;
    const todos = PLAN.dias.filter((d) => d.fecha >= desde && d.fecha <= hastaStr);
    const dias = todos.filter((d) => !YA_ENTRENADOS.has(d.fecha));
    const hechos = todos.length - dias.length;

    console.log(`Plan: ${desde} -> ${hastaStr}  ·  ${dias.length} sesiones`
        + (hechos ? `  (${hechos} día(s) ya entrenados, se omiten)` : ''));
    console.log(`Zonas: LT1 ${ZONAS.anclas.lt1} · LT2 ${ZONAS.anclas.lt2} · FCmax ${ZONAS.anclas.fcmax}`
        + (ZONAS.anclas.provisional ? '  (provisionales)' : ''));
    console.log(SUBIR ? '\nMODO SUBIDA — se escribira en tu cuenta de Garmin.'
        : DIFF ? '\nCOMPARACION — entra a Garmin solo a LEER. No se escribe nada.'
        : '\nENSAYO — no se toca nada. Para subir de verdad: node sube_garmin.js --subir');

    const ws = dias.map((d) => ({ d, w: workout(d) }));
    ws.forEach(({ d, w }) => resumir(w, d));

    const dobles = todos.filter(esDoble);
    console.log('\n' + '-'.repeat(72));
    if (dobles.length) {
        console.log(`DOBLE JORNADA esta semana — ${dobles.length} dia(s). El reloj solo lleva la AM:`);
        for (const d of dobles) {
            console.log(`  ${d.fecha} ${d.dia.slice(0, 3)}  AM ${d.sesion.replace(/ — .*/, '')}`
                + `  +  PM ${d.pm_titulo}${d.pm_km ? ` (${d.pm_km} km)` : ''}`);
        }
    } else {
        console.log('Sin dobles jornadas en este rango: una sesion por dia.');
    }

    if (!SUBIR && !DIFF) {
        console.log(`\n${ws.length} entrenamientos listos. Revisa arriba y, si cuadra, corre con --subir.`);
        console.log('Para ver que pasaria con lo que YA esta en el reloj: node sube_garmin.js --diff');
        return;
    }

    const { GarminConnect } = require('garmin-connect');
    if (!process.env.GARMIN_USERNAME || !process.env.GARMIN_PASSWORD) {
        console.error('Faltan credenciales en .env'); process.exit(1);
    }
    const GC = new GarminConnect({
        username: process.env.GARMIN_USERNAME, password: process.env.GARMIN_PASSWORD
    });
    await GC.login();
    const base = GC.client.url.GC_API;

    const previos = new Map();
    for (const w of await GC.getWorkouts(0, 200)) { previos.set(w.workoutName, w); }

    /** Huella guardada en la descripcion del entrenamiento que ya esta en Garmin. */
    async function huellaPrevia(w) {
        var desc = w.description;
        if (desc == null) {
            try { desc = (await GC.getWorkoutDetail({ workoutId: w.workoutId })).description; }
            catch (e) { return null; }
        }
        const m = MARCA.exec(desc || '');
        return m ? m[1] : null;
    }

    let subidos = 0, saltados = 0, reemplazados = 0;
    console.log(DIFF ? '\nQUE HARIA, dia por dia:' : '');
    for (const { d, w } of ws) {
        const prev = previos.get(w.workoutName);
        if (prev) {
            const vieja = await huellaPrevia(prev);
            if (vieja === w._huella) {
                console.log(`  = sin cambios, se salta: ${w.workoutName}`);
                saltados++;
                continue;
            }
            if (DIFF) {
                console.log(`  ~ REEMPLAZAR  ${d.fecha}  ${w.workoutName}`);
                console.log(`      el del reloj lleva huella ${vieja || 'ninguna'}; el plan de ahora ${w._huella}`);
                console.log('      -> se borra el viejo y se crea de nuevo con los objetivos nuevos');
                reemplazados++;
                continue;
            }
            // El plan cambio (un test movio las zonas, o se ajusto la sesion):
            // el que esta en el reloj lleva objetivos viejos y hay que reemplazarlo.
            console.log(`  ~ cambio el plan (${vieja || 'sin huella'} -> ${w._huella}), se reemplaza`);
            try { await GC.deleteWorkout({ workoutId: prev.workoutId }); }
            catch (e) { console.log(`    no se pudo borrar el anterior: ${e.response?.status || e.message}`); }
            reemplazados++;
        }
        if (DIFF) {
            console.log(`  + CREAR       ${d.fecha}  ${w.workoutName}   (no existe en la cuenta)`);
            subidos++;
            continue;
        }
        const payload = Object.assign({}, w);
        delete payload._huella;
        const creado = await GC.client.post(`${base}/workout-service/workout`, payload);
        const id = creado.workoutId;
        await GC.client.post(`${base}/workout-service/schedule/${id}`, { date: d.fecha });
        console.log(`  ${prev ? '~' : '+'} ${d.fecha}  ${w.workoutName}  (id ${id})`);
        if (!prev) { subidos++; }
    }
    console.log(`\n${subidos} ${DIFF ? 'se crearian' : 'nuevos'}`
        + ` · ${reemplazados} ${DIFF ? 'se reemplazarian' : 'actualizados'} por cambio de plan`
        + ` · ${saltados} sin cambios.`);
    if (DIFF) console.log('\nNo se escribio nada. Para hacerlo de verdad: anade --subir en vez de --diff.');
})().catch((e) => {
    console.error('\nError:', e.response?.status || '', e.response?.data || e.message);
    console.error('Si es 400/404 en workout-service, Garmin cambio el endpoint: hay que ajustar el JSON.');
    process.exit(1);
});
