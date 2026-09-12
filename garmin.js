// Lector simple de .env (sin dependencias externas)
const fs = require('fs');
const path = require('path');
(function loadEnv() {
    try {
        const envPath = path.join(__dirname, '.env');
        if (!fs.existsSync(envPath)) return;
        for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
            const t = line.trim();
            if (!t || t.startsWith('#')) continue;
            const i = t.indexOf('=');
            if (i === -1) continue;
            const k = t.slice(0, i).trim();
            const v = t.slice(i + 1).trim();
            if (!(k in process.env)) process.env[k] = v;
        }
    } catch (e) { /* noop */ }
})();

const { GarminConnect } = require('garmin-connect');
const { Parser } = require('json2csv');

const USERNAME = process.env.GARMIN_USERNAME;
const PASSWORD = process.env.GARMIN_PASSWORD;

if (!USERNAME || !PASSWORD || PASSWORD.includes('PEGA_AQUI')) {
    console.error('Faltan credenciales. Edita el archivo .env con GARMIN_USERNAME y GARMIN_PASSWORD.');
    process.exit(1);
}

const DAYS_BACK = parseInt(process.env.DAYS_BACK || '30', 10);
const OUT = path.join(__dirname, 'entrenamientos_performance.csv');
// Almacén histórico: Garmin solo entrega los últimos DAYS_BACK días, así que el CSV
// se reconstruye desde aquí para no perder las semanas anteriores en cada corrida.
const HIST = path.join(__dirname, 'historial_entrenamientos.json');

const CAMPOS = [
    'splitSummaryData', 'Descanso_Entre_Reps', 'Activity_ID', 'Fecha', 'Nombre', 'Tipo',
    'Distancia_Km', 'Duracion_Min', 'Calorias', 'FC_Media', 'FC_Maxima', 'Cadencia_Media',
    'Oscilacion_Vertical', 'Tiempo_Contacto_Suelo', 'Longitud_Zancada',
    'Training_Effect_Aerobico', 'Training_Effect_Anaerobico', 'Tiempo_Recuperacion_Horas',
    'Varianza_FC',
];

function cargarHistorial() {
    try {
        if (!fs.existsSync(HIST)) return {};
        return JSON.parse(fs.readFileSync(HIST, 'utf8'));
    } catch (e) {
        console.error('No se pudo leer el historial, se empieza vacío:', e.message);
        return {};
    }
}

// Clave de deduplicación: el id de Garmin si existe, si no la fecha-hora local (única por actividad).
function claveActividad(registro) {
    return String(registro.Activity_ID || registro.Fecha);
}

function formatMMSS(totalSeconds) {
    const s = Math.round(totalSeconds);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${String(r).padStart(2, '0')}`;
}

// Garmin agrupa las repeticiones por tipo (INTERVAL_ACTIVE, INTERVAL_RECOVERY, ...)
// y entrega el total + noOfSplits (cuántas repeticiones se sumaron), no cada una por separado.
// Con eso calculamos el descanso PROMEDIO entre repeticiones cuando hubo más de una.
function descansoEntreReps(splitSummaries) {
    if (!splitSummaries) return '';
    const recoveries = splitSummaries.filter(
        (s) => /RECOVERY/i.test(s.splitType) && s.noOfSplits > 1
    );
    if (recoveries.length === 0) return '';
    return recoveries
        .map((r) => `≈${formatMMSS(r.duration / r.noOfSplits)} x${r.noOfSplits} (${r.splitType})`)
        .join(' | ');
}

async function main() {
    try {
        const GCClient = new GarminConnect({ username: USERNAME, password: PASSWORD });
        await GCClient.login();
        console.log('Sesión iniciada correctamente.');

        const start = new Date();
        start.setDate(start.getDate() - DAYS_BACK);
        start.setHours(0, 0, 0, 0);

        const activities = await GCClient.getActivities(0, 500);
        const detailedData = [];

        for (const activity of activities) {
            try {
                const activityDate = new Date(activity.startTimeLocal);
                if (activityDate < start) continue;

                console.log(`Procesando: ${activity.activityName} - ${activity.startTimeLocal}`);
                const details = await GCClient.getActivity({ activityId: activity.activityId });

                const splitSummaryData = details.splitSummaries
                    ? details.splitSummaries.map((split) => ({
                          Tipo_Fase: split.splitType,
                          Numero_Reps: split.noOfSplits,
                          Distancia_m: split.distance,
                          Duracion_s: split.duration,
                          Ritmo_Medio_ms: split.averageSpeed,
                          Ritmo_Ajustado_Grado: split.avgGradeAdjustedSpeed,
                          Potencia_Media_W: split.averagePower,
                          Potencia_Normalizada_W: split.normalizedPower,
                          FC_Media: split.averageHR,
                          FC_Maxima: split.maxHR,
                          Calorias: split.calories,
                          Cadencia_Media: split.averageRunCadence,
                          Longitud_Zancada_cm: split.strideLength,
                          Tiempo_Contacto_Suelo_ms: split.groundContactTime,
                          Balance_Izquierdo: split.groundContactBalanceLeft,
                          Oscilacion_Vertical: split.verticalOscillation,
                          Ratio_Vertical: split.verticalRatio,
                          Desnivel_Positivo: split.elevationGain,
                          Desnivel_Negativo: split.elevationLoss,
                      }))
                    : [];

                // recoveryTime y hrvStatus no vienen en el listado de actividades;
                // hay que sacarlos del detalle (summaryDTO según versión de la API).
                const resumen = details.summaryDTO || {};

                detailedData.push({
                    splitSummaryData,
                    Descanso_Entre_Reps: descansoEntreReps(details.splitSummaries),
                    Activity_ID: activity.activityId,
                    Fecha: activity.startTimeLocal,
                    Nombre: activity.activityName,
                    Tipo: activity.activityType.typeKey,
                    Distancia_Km: (activity.distance / 1000).toFixed(2),
                    Duracion_Min: (activity.duration / 60).toFixed(2),
                    Calorias: activity.calories,
                    FC_Media: activity.averageHR,
                    FC_Maxima: activity.maxHR,
                    Cadencia_Media: activity.averageRunningCadenceInStepsPerMinute,
                    Oscilacion_Vertical: activity.avgVerticalOscillation,
                    Tiempo_Contacto_Suelo: activity.avgGroundContactTime,
                    Longitud_Zancada: activity.avgStrideLength,
                    Training_Effect_Aerobico: activity.aerobicTrainingEffect,
                    Training_Effect_Anaerobico: activity.anaerobicTrainingEffect,
                    Tiempo_Recuperacion_Horas:
                        activity.recoveryTime ?? resumen.recoveryTime ?? details.recoveryTime ?? '',
                    Varianza_FC:
                        activity.hrvStatus ?? resumen.hrvStatus ?? details.hrvStatus ?? '',
                });
            } catch (error) {
                console.error(`Error procesando la actividad ${activity.activityId}:`, error.message);
            }
        }

        if (detailedData.length === 0) {
            console.log('No se encontraron actividades en el rango indicado.');
            return;
        }

        // Fusionar con el histórico: lo recién extraído pisa a lo viejo (puede traer correcciones),
        // pero nada de lo anterior se borra aunque caiga fuera de la ventana de DAYS_BACK.
        const historial = cargarHistorial();
        const previas = Object.keys(historial).length;
        let nuevas = 0;
        for (const registro of detailedData) {
            const clave = claveActividad(registro);
            // Se considera nueva solo si no estaba ni por clave ni por fecha-hora.
            const yaEstaba =
                clave in historial ||
                Object.values(historial).some((v) => v.Fecha === registro.Fecha);
            if (!yaEstaba) nuevas++;
            // Migración: los registros anteriores a Activity_ID quedaron indexados por fecha.
            // Si esta actividad ya estaba guardada así, se retira para no duplicarla.
            for (const [k, v] of Object.entries(historial)) {
                if (k !== clave && v.Fecha === registro.Fecha) delete historial[k];
            }
            historial[clave] = registro;
        }

        // Más recientes primero, igual que antes.
        const todas = Object.values(historial).sort((a, b) => String(b.Fecha).localeCompare(String(a.Fecha)));

        fs.writeFileSync(HIST, JSON.stringify(historial, null, 1));
        fs.writeFileSync(OUT, new Parser({ fields: CAMPOS }).parse(todas));
        console.log(
            `Extraídas ${detailedData.length} actividades de los últimos ${DAYS_BACK} días ` +
            `(${nuevas} nuevas). Historial: ${previas} -> ${todas.length}. CSV -> ${OUT}`
        );
    } catch (error) {
        console.error('Error en la extracción:', error.message);
    }
}

main();
