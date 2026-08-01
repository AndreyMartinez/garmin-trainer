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

const DAYS_BACK = parseInt(process.env.DAYS_BACK || '9', 10);
const OUT = path.join(__dirname, 'entrenamientos_performance.csv');

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

                detailedData.push({
                    splitSummaryData,
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
                    Tiempo_Recuperacion_Horas: activity.recoveryTime,
                    Varianza_FC: activity.hrvStatus,
                });
            } catch (error) {
                console.error(`Error procesando la actividad ${activity.activityId}:`, error.message);
            }
        }

        if (detailedData.length === 0) {
            console.log('No se encontraron actividades en el rango indicado.');
            return;
        }

        fs.writeFileSync(OUT, new Parser().parse(detailedData));
        console.log(`CSV generado con éxito (${detailedData.length} actividades) -> ${OUT}`);
    } catch (error) {
        console.error('Error en la extracción:', error.message);
    }
}

main();
