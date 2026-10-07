// Lee (y opcionalmente ajusta) el umbral de lactato y las zonas de FC en Garmin Connect.
//
//   node config_garmin.js            # LEER: muestra lo que Garmin tiene hoy. No escribe nada.
//   node config_garmin.js --aplicar  # ESCRIBIR: pone LT2, FCmax y las 5 zonas de zonas.json
//
// Leer es el modo por defecto. El paso de escritura se construye sobre lo que devuelva
// la lectura: los nombres de campo de user-settings varian entre cuentas y versiones.
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

const APLICAR = process.argv.includes('--aplicar');
const ZONAS = JSON.parse(fs.readFileSync(path.join(__dirname, 'zonas.json'), 'utf8'));
const A = ZONAS.anclas;

/** Las 5 zonas de Garmin a partir de las 6 del sistema: Z5 y Z6 se fusionan arriba. */
function zonasGarmin() {
    const lim = (z) => {
        const d = ZONAS.zonas.find((x) => x.z === z);
        if (!d.lo_off) return null;
        return [d.lo_off[1] === -999 ? 0 : A[d.lo_off[0]] + d.lo_off[1], A[d.hi_off[0]] + d.hi_off[1]];
    };
    const z = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5'].map(lim);
    return [
        { zona: 1, lo: 100, hi: z[0][1] },
        { zona: 2, lo: z[1][0], hi: z[1][1] },
        { zona: 3, lo: z[2][0], hi: z[2][1] },
        { zona: 4, lo: z[3][0], hi: z[3][1] },
        { zona: 5, lo: z[4][0], hi: A.fcmax }
    ];
}

function interesantes(obj, prefijo = '') {
    const out = {};
    for (const [k, v] of Object.entries(obj || {})) {
        if (v && typeof v === 'object' && !Array.isArray(v)) {
            Object.assign(out, interesantes(v, prefijo + k + '.'));
        } else if (/lactate|heart|hr|zone|vo2|threshold|resting|max/i.test(k)) {
            out[prefijo + k] = v;
        }
    }
    return out;
}

(async function main() {
    const { GarminConnect } = require('garmin-connect');
    if (!process.env.GARMIN_USERNAME || !process.env.GARMIN_PASSWORD) {
        console.error('Faltan credenciales en .env'); process.exit(1);
    }
    const GC = new GarminConnect({
        username: process.env.GARMIN_USERNAME, password: process.env.GARMIN_PASSWORD
    });
    await GC.login();
    const base = GC.client.url.GC_API;

    console.log('\n================ LO QUE GARMIN TIENE HOY ================');
    const settings = await GC.getUserSettings();
    const campos = interesantes(settings);
    if (Object.keys(campos).length === 0) {
        console.log('  (user-settings no devolvio campos de FC — se imprime el objeto entero)');
        console.log(JSON.stringify(settings, null, 1).slice(0, 3000));
    } else {
        for (const [k, v] of Object.entries(campos)) console.log(`  ${k}: ${v}`);
    }

    console.log('\n---------------- zonas de FC (biometric-service) ----------------');
    let zonasGC = null;
    try {
        zonasGC = await GC.client.get(`${base}/biometric-service/heartRateZones`);
        console.log(JSON.stringify(zonasGC, null, 1));
    } catch (e) {
        console.log('  no accesible:', e.response?.status || e.message);
    }

    // Garmin no acepta un metodo por lpm absolutos: rechaza 'BPM' y convierte 'CUSTOM'
    // en 'HR_MAX'. Los pisos SI se guardan en lpm y quedan bien, pero a partir de ahi
    // Garmin los trata como porcentajes de la FCmax: el dia que la FCmax cambie —y el
    // Test C existe justo para eso— los recalcula y los cinco pisos se desplazan solos.
    // Los del plan no dependen de la FCmax: cuelgan de LT1 y LT2. Asi que cada lectura
    // comprueba si siguen donde deben.
    if (zonasGC && zonasGC.length) {
        const plan0 = zonasGarmin().map((z) => z.lo);
        const malas = zonasGC.filter((z) =>
            z.lactateThresholdHeartRateUsed !== A.lt2
            || [z.zone1Floor, z.zone2Floor, z.zone3Floor, z.zone4Floor, z.zone5Floor]
                .some((f, i) => f !== plan0[i]));
        if (malas.length) {
            console.log('\n  ⚠ LAS ZONAS NO CUADRAN CON EL PLAN:');
            for (const z of malas) {
                console.log(`      ${z.sport}: pisos `
                    + `${[z.zone1Floor, z.zone2Floor, z.zone3Floor, z.zone4Floor, z.zone5Floor].join(' · ')}`
                    + `  ·  el plan pide ${plan0.join(' · ')}`);
            }
            console.log('      Corrige con:  node config_garmin.js --aplicar');
        } else if (zonasGC.some((z) => /HR_MAX|PERCENT|RESERVE/i.test(z.trainingMethod || ''))) {
            console.log(`\n  (metodo ${zonasGC[0].trainingMethod}: los pisos estan bien HOY, pero Garmin los `
                + 'lee como % de la FCmax.');
            console.log('   Si la FCmax cambia, se desplazan solos. Tras el Test C: --aplicar otra vez.)');
        }
    }

    console.log('\n================ LO QUE DEBERIA QUEDAR ================');
    console.log(`  Umbral de lactato (LT2): ${A.lt2} ppm`
        + (A.provisional ? '   [provisional hasta el Test A]' : ''));
    console.log(`  FC maxima:               ${A.fcmax} ppm`);
    console.log('  Zonas personalizadas (ppm):');
    for (const z of zonasGarmin()) console.log(`    Zona ${z.zona}:  ${z.lo}-${z.hi}`);

    // Cuando LT1 y LT2 estaban a 17 lpm, las bandas %LTHR de Garmin reproducian el plan
    // casi exacto y bastaba corregir el ancla. Con LT2 medido en 183 y LT1 todavia en 153
    // la distancia es de 30 lpm y ningun juego de porcentajes fijos puede dar las dos
    // fronteras a la vez: hay que escribir los pisos en lpm. Esta comparacion lo demuestra
    // sola en cada corrida, en vez de confiar en una nota que envejece.
    const plan = zonasGarmin().map((z) => z.lo);
    const pct = zonasGC && zonasGC.find((z) => z.sport === 'RUNNING');
    if (pct) {
        const ratios = [pct.zone1Floor, pct.zone2Floor, pct.zone3Floor, pct.zone4Floor, pct.zone5Floor]
            .map((f) => f / pct.lactateThresholdHeartRateUsed);
        const escalados = ratios.map((r) => Math.round(r * A.lt2));
        console.log('\n  Si SOLO cambiamos el ancla a ' + A.lt2 + ', Garmin recalcula los pisos a:');
        console.log('    ' + escalados.join(' · '));
        console.log('    el plan necesita:  ' + plan.join(' · '));
        const dif = escalados.map((v, i) => v - plan[i]);
        console.log('    diferencia:        ' + dif.map((v) => (v > 0 ? '+' : '') + v).join(' · ')
            + (dif.some((v) => Math.abs(v) > 2)
                ? '   <-- por eso se escriben los pisos en lpm, no el porcentaje'
                : '   (dentro de 2 lpm: el porcentaje bastaria)'));
    }

    if (!APLICAR) {
        console.log('\nSOLO LECTURA. No se escribio nada.');
        console.log('Para aplicar:  node config_garmin.js --aplicar\n');
        return;
    }

    console.log('\n================ APLICANDO ================');
    // Payload minimo: solo los dos campos que importan, para no reescribir el perfil entero.
    const cambio = { userData: { lactateThresholdHeartRate: A.lt2, thresholdHeartRateAutoDetected: false } };
    console.log('  PUT user-settings ->', JSON.stringify(cambio.userData));
    await GC.client.put(`${base}/userprofile-service/userprofile/user-settings`, cambio);

    const despues = await GC.getUserSettings();
    const d = interesantes(despues);
    console.log(`  ahora: lactateThresholdHeartRate = ${d['userData.lactateThresholdHeartRate']}`
        + ` · autoDetected = ${d['userData.thresholdHeartRateAutoDetected']}`);
    if (d['userData.thresholdHeartRateAutoDetected'] !== false) {
        console.log('  ⚠ La deteccion automatica NO quedo apagada desde la API.');
        console.log('    Apagala en el reloj: Configuracion > Estadisticas fisiologicas >');
        console.log('    Deteccion automatica > Umbral de lactato. Si no, Garmin lo vuelve a subir.');
    }

    // biometric-service guarda SU PROPIA copia del umbral: no sigue a user-settings.
    // Hay que reescribir cada perfil de deporte con el ancla nueva y los pisos recalculados.
    console.log('\n  Las zonas no heredan el ancla: se reescriben una por una.');
    const pisos = (z) => [z.zone1Floor, z.zone2Floor, z.zone3Floor, z.zone4Floor, z.zone5Floor];
    // Los pisos salen del PLAN en lpm, no de escalar los porcentajes viejos. Con LT1 153 y
    // LT2 183 las bandas %LTHR dejarian el piso de Z3 en 163 cuando LT1 esta en 153: diez
    // lpm de margen para correr los dias faciles por encima de LT1, que es exactamente el
    // error que se arrastro todo el bloque 1.
    const planPisos = zonasGarmin().map((z) => z.lo);
    // Si el metodo se queda en %umbral, Garmin puede volver a derivar los pisos del
    // porcentaje y pisar lo que acabamos de escribir. Se prueban los metodos absolutos
    // primero y se comprueba releyendo; ninguno se da por bueno sin verificar.
    const METODOS = ['BPM', 'CUSTOM', null];   // null = dejar el que ya tiene

    const construir = (metodo) => zonasGC.map((z) => {
        const [f1, f2, f3, f4, f5] = planPisos;
        return {
            ...z,
            trainingMethod: metodo || z.trainingMethod,
            lactateThresholdHeartRateUsed: A.lt2,
            maxHeartRateUsed: Math.max(z.maxHeartRateUsed, A.fcmax),
            zone1Floor: f1, zone2Floor: f2, zone3Floor: f3, zone4Floor: f4, zone5Floor: f5,
            changeState: 'CHANGED'
        };
    });
    console.log(`    pisos a escribir (de zonas.json): ${planPisos.join(' · ')}`
        + `  ·  techo ${A.fcmax}  ·  LTHR ${A.lt2}`);

    const correcto = (z) => z.lactateThresholdHeartRateUsed === A.lt2
        && pisos(z).every((f, i) => f === planPisos[i]);

    let zdesp = zonasGC;
    for (const metodo of METODOS) {
        const cuerpo = construir(metodo);
        const etiqueta = metodo ? `metodo ${metodo}` : 'metodo actual';
        const intentos = [
            ['PUT array', () => GC.client.put(`${base}/biometric-service/heartRateZones`, cuerpo)],
            ['PUT uno a uno', async () => {
                for (const z of cuerpo) await GC.client.put(`${base}/biometric-service/heartRateZones`, z);
            }],
            ['POST array', () => GC.client.post(`${base}/biometric-service/heartRateZones`, cuerpo)]
        ];
        for (const [verbo, fn] of intentos) {
            try {
                await fn();
            } catch (e) {
                console.log(`  ${etiqueta} · ${verbo}: ${e.response?.status || e.message}`);
                continue;
            }
            // La unica prueba que vale es volver a leer: un POST que devuelve 200 no
            // garantiza que Garmin no haya recalculado los pisos desde el porcentaje.
            zdesp = await GC.client.get(`${base}/biometric-service/heartRateZones`);
            if (zdesp.every(correcto)) {
                console.log(`  ${etiqueta} · ${verbo}: aceptado y verificado`);
                break;
            }
            console.log(`  ${etiqueta} · ${verbo}: escribio, pero Garmin dejo `
                + `${pisos(zdesp.find((z) => z.sport === 'RUNNING') || zdesp[0]).join(' · ')}`);
        }
        if (zdesp.every(correcto)) break;
    }

    console.log('\n  VERIFICACION (releido de Garmin):');
    for (const z of zdesp) {
        console.log(`    ${z.sport.padEnd(8)} ${String(z.trainingMethod).padEnd(18)}`
            + ` LTHR ${z.lactateThresholdHeartRateUsed} · pisos ${pisos(z).join(' · ')}`
            + `  ${correcto(z) ? 'OK' : '<-- NO CUADRA CON EL PLAN'}`);
    }
    if (!zdesp.every(correcto)) {
        console.log('\n  La API no dejo las zonas como las pide el plan.');
        console.log('  A mano: Garmin Connect > Perfil de usuario > Frecuencia cardiaca > Zonas de FC >');
        console.log('  Carrera, metodo "Personalizado (ppm)" y estos limites:');
        for (const z of zonasGarmin()) console.log(`    Zona ${z.zona}:  ${z.lo}-${z.hi}`);
    } else {
        console.log('\nListo. Sincroniza el reloj para que baje el cambio.');
    }
    console.log();
})().catch((e) => {
    console.error('\nError:', e.response?.status || '', e.response?.data || e.message);
    process.exit(1);
});
