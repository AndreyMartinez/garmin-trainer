# Bloque 5K · Garmin

Herramientas personales para entrenar hacia un **5K sub-16** desde CDMX (2,240 m): extracción de datos de Garmin Connect, generación del plan de entrenamiento y un visor web de sesiones.

## Contenido

| Archivo | Qué hace |
|---|---|
| `garmin.js` | Extrae las actividades de Garmin Connect, las fusiona en `historial_entrenamientos.json` y reconstruye `entrenamientos_performance.csv`. |
| `analiza.py` | Cruza lo ejecutado contra el plan y escribe `analisis.json` con todos los números calculados. |
| `narrativa.json` | La lectura de la semana. Lo único escrito a mano. |
| `informe.py` | Combina plantilla + `analisis.json` + `narrativa.json` → `informe_5k.html`. |
| `informe_plantilla.html` | Estructura y estilos del informe (con marcadores `__DATOS__` / `__NARRATIVA__`). |
| `gen_plan.py` | Genera el plan maestro (`plan_maestro.json` / `PLAN_MAESTRO.csv`) y sus variantes. |
| `sesiones.html` | Visor del plan por día/semana (abrir en el navegador). |
| `run_garmin.sh` | Lanza la extracción de Garmin. |
| `com.raphael.garmin.plist` | Agente launchd (macOS), **no instalado**: su ruta apunta a `Desktop/código` (con acento) y la carpeta real es `Desktop/codigo`. La automatización actual no lo usa. |
| `*.csv`, `plan_maestro.json` | Datos del plan y de entrenamientos. |

`entrenamientos_performance.csv` se **reconstruye completo desde `historial_entrenamientos.json`** en cada corrida. Garmin solo devuelve los últimos `DAYS_BACK` días, así que el histórico es lo que impide perder las semanas anteriores; la deduplicación va por `Activity_ID` (o por fecha-hora en los registros anteriores a ese campo).

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

### 4. Informe semanal

    npm start                      # extrae y fusiona en el histórico
    python3 analiza.py --dias 14   # -> analisis.json
    # (reescribir narrativa.json con la lectura de la semana)
    python3 informe.py             # -> informe_5k.html

Corre solo cada **lunes a las 07:00** mediante la tarea programada `informe-5k-semanal`,
que ejecuta los cuatro pasos y republica la página:
<https://claude.ai/code/artifact/80f3285e-9613-4b80-b19a-87eb2f04cafd>

Las tareas programadas corren mientras la app de Claude esté abierta; si estaba cerrada
al vencer el disparo, corre al siguiente arranque. Por eso `DAYS_BACK` es **30** y no 9:
aunque pasen dos o tres semanas sin abrirla, la extracción siguiente recupera todo.

#### Distinción que el informe no debe romper

`analiza.py` separa dos cosas que parecen iguales y no lo son:

- **`omitidos`** — días del plan dentro de la cobertura del histórico, sin ninguna actividad.
- **`sin_datos`** — días anteriores a `cobertura_desde`, nunca extraídos. No permiten concluir nada.

Mezclarlas convierte un hueco de extracción en un entrenamiento perdido que quizá sí ocurrió.

## Seguridad

- **`.env` nunca se sube** (contiene tus credenciales de Garmin) — está en `.gitignore`.
- `node_modules/` tampoco se versiona; se reinstala con `npm install`.
- Los datos de entrenamiento sí se incluyen en este repo por ser de uso personal: los CSV, `historial_entrenamientos.json`, `analisis.json` y el `informe_5k.html` generado. Si lo haces **público**, quítalos todos (contienen datos de salud: FC, ritmos, ubicaciones de las sesiones).
- El informe publicado es un artifact **privado**; solo se comparte si tú lo compartes desde el menú de la página.

## Contexto del atleta

Meta 5K sub-16 (largo plazo). Zonas Friel con LTHR ~186 lpm. Estructura semanal: Lun recuperación · Mar VO2 + fuerza · Mié rodaje + strides · Jue umbral · Vie descanso · Sáb fondo largo · Dom cuestas.
