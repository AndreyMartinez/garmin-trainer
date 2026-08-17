# Bloque 5K · Garmin

Herramientas personales para entrenar hacia un **5K sub-16** desde CDMX (2,240 m): extracción de datos de Garmin Connect, generación del plan de entrenamiento y un visor web de sesiones.

## Contenido

| Archivo | Qué hace |
|---|---|
| `garmin.js` | Extrae las actividades recientes de Garmin Connect y las vuelca a `entrenamientos_performance.csv`. |
| `gen_plan.py` | Genera el plan maestro (`plan_maestro.json` / `PLAN_MAESTRO.csv`) y sus variantes. |
| `sesiones.html` | Visor del plan por día/semana (abrir en el navegador). |
| `run_garmin.sh` | Lanza la extracción de Garmin. |
| `com.raphael.garmin.plist` | Agente launchd (macOS) para correr la extracción automáticamente. |
| `*.csv`, `plan_maestro.json` | Datos del plan y de entrenamientos. |

`entrenamientos_performance.csv` incluye `Descanso_Entre_Reps`: el descanso **promedio** entre repeticiones cuando la sesión tuvo series (Garmin agrupa las repeticiones por tipo y solo entrega el total + cuántas se sumaron, no cada una por separado, así que no hay descanso rep-por-rep exacto).

## Uso

### 1. Extraer datos de Garmin

    npm install
    cp .env.example .env   # y rellena tus credenciales
    npm start              # o: ./run_garmin.sh

Variables en `.env`:

- `GARMIN_USERNAME`, `GARMIN_PASSWORD` — credenciales de Garmin Connect.
- `DAYS_BACK` — días hacia atrás a extraer (por defecto 9).

### 2. Generar el plan

    python3 gen_plan.py

### 3. Ver las sesiones

Abre `sesiones.html` en el navegador.

## Seguridad

- **`.env` nunca se sube** (contiene tus credenciales de Garmin) — está en `.gitignore`.
- `node_modules/` tampoco se versiona; se reinstala con `npm install`.
- Los CSV de entrenamiento sí se incluyen en este repo por ser de uso personal. Si lo haces **público**, considera quitarlos (contienen datos de salud: FC, ritmos, etc.).

## Contexto del atleta

Meta 5K sub-16 (largo plazo). Zonas Friel con LTHR ~186 lpm. Estructura semanal: Lun recuperación · Mar VO2 + fuerza · Mié rodaje + strides · Jue umbral · Vie descanso · Sáb fondo largo · Dom cuestas.
