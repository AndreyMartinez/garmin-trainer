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
| `zonas.json` | **Fuente de verdad del sistema**: las anclas LT1/LT2/FCmax, los seis protocolos de test y el histórico de lo medido. |
| `zonas.py` | Tabla de zonas, `--refit` de la regresión FC↔ritmo, `--garmin`, `--deriva` (Test B), `--protocolo`. |
| `gen_plan_v4.py` | Genera el plan de 18 semanas desde las anclas (`plan_maestro.json` / `PLAN_MAESTRO.csv` / datos de `sesiones.html`). Sustituye a `gen_plan.py`. |
| `sube_garmin.js` | Compila cada día del plan a un entrenamiento estructurado de Garmin y lo agenda. Ensayo por defecto. |
| `config_garmin.js` | Lee y escribe el umbral de lactato y las zonas de FC en la cuenta de Garmin. |
| `gen_web_plan.py` + `plan_web_plantilla.html` | Las 126 sesiones como página publicable (`plan_web.html`, derivado). |
| `proyecto_sub16.html` | La página de estrategia del bloque. |
| `PLAN_HISTORICO.csv` | El plan del bloque 1, que se antepone al generado para que `analiza.py` no pierda el historial. |
| `gen_plan.py` | Generador del bloque 1. **Obsoleto**, se conserva como referencia. |
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

### 2. Anclar las zonas a un test

Todo cuelga de tres anclas medidas en campo. Sin lactómetro, LT2 sale de la contrarreloj
de 30 min (Test A) y LT1 de la deriva aeróbica (Test B):

    python3 zonas.py                                   # tabla de zonas vigente
    python3 zonas.py --protocolo A                     # el protocolo completo
    python3 zonas.py --lt2 183 --ritmo-lt2 3:47 --fecha 2026-10-01 --metodo "CR 30 min" --refit

**Los ritmos no son un ancla**: se derivan de la regresión `FC = a·v + b` ajustada con los
esfuerzos continuos reales. Con `--ritmo-lt2` la recta pasa obligada por el punto del test y
solo se ajusta la pendiente; sin anclar, la nube de rodajes fáciles la acuesta y deja el
umbral varios lpm bajo, que es justo donde se prescriben las series.

Dos filtros protegen esa regresión, y los dos existen por un error real que ya ocurrió:

- `MAX_DESNIVEL_M_KM` — una cuesta infla la FC para el ritmo, y un punto lento e inclinado
  arrastra la recta por apalancamiento sin que el descarte por desviaciones lo vea.
- `FC_DESCARTADA` — la FC óptica de muñeca se descuelga en esfuerzo duro y devuelve ritmo
  alto con FC baja. Un solo punto así tumbó la pendiente 12 lpm en umbral.

### 3. Generar el plan

    python3 gen_plan_v4.py

### 4. Ver las sesiones

Abre `sesiones.html` en el navegador, o genera la página publicable con `python3 gen_web_plan.py`.

### 5. Llevarlo al reloj

    node sube_garmin.js                 # ENSAYO: imprime lo que subiría
    node sube_garmin.js --diff          # entra a Garmin solo a LEER y dice qué crearía o reemplazaría
    node sube_garmin.js --semana --subir

Cada entrenamiento lleva una huella `[plan:<sha1>]` en su descripción. Si un test mueve las
zonas y el plan se regenera, el que ya está en el reloj conserva los objetivos viejos: la
huella detecta ese caso y lo reemplaza en vez de saltárselo por nombre.

El calentamiento y la vuelta a la calma bajan **como pasos**, no como una frase en la
descripción: los códigos `C1..C6` y `VC1..VC6` del plan se traducen a tramos con su duración
y su objetivo de FC, y los bloques sin ritmo medible (movilidad, drills, estiramiento) van a
golpe de botón de vuelta, como lista de control. Lo que no es un paso no se ejecuta.

### 6. Zonas en la cuenta de Garmin

    node config_garmin.js               # LEER: compara lo que Garmin tiene contra zonas.json
    node config_garmin.js --aplicar     # ESCRIBIR umbral, techo y los cinco pisos

La API no acepta zonas en lpm absolutos: rechaza `trainingMethod: 'BPM'` y convierte
`'CUSTOM'` en `'HR_MAX'`. Los cinco pisos **sí** se escriben en lpm si van en el mismo PUT que
la FCmax, pero a partir de ahí Garmin los lee como porcentajes de ella, así que **cualquier
cambio de FCmax los desplaza solos**. De ahí tres reglas: la FCmax se cambia siempre con este
script, la detección automática de FCmax y de umbral se queda apagada en el reloj, y el modo
lectura avisa si los pisos se han movido.

### 7. Informe semanal

    npm start                      # extrae y fusiona en el histórico
    python3 analiza.py --dias 14   # -> analisis.json
    python3 zonas.py --refit       # re-ajusta la regresión con lo ejecutado
    # (reescribir narrativa.json con la lectura de la semana)
    python3 informe.py             # -> informe_5k.html

Corre solo los **domingos a las 20:00** mediante la tarea programada
`Cierre de semana · bloque 5K`, que encadena los pasos, republica la página y deja la
semana siguiente lista en el reloj:
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

- **Las credenciales nunca se suben.** El patrón es `.env*` con `!.env.example`, no `.env` exacto:
  el Desktop está sincronizado con iCloud y los conflictos dejan copias `nombre 2.ext`. Ya apareció
  un `.env 2` con las credenciales dentro, que la regla exacta no tapaba y un `git add -A` se habría
  llevado. Por lo mismo se ignora el patrón `* [0-9].*`.
- `node_modules/` tampoco se versiona; se reinstala con `npm install`.
- **Este repo es público y los datos de entrenamiento van dentro a propósito** (decisión tomada):
  los CSV y `historial_entrenamientos.json` contienen frecuencias cardiacas, ritmos y los nombres
  de las alcaldías donde se corrió. No hay coordenadas. Quien clone el repo ve todo eso.
- Las salidas derivadas no se versionan y se regeneran: `analisis.json`, `informe_5k.html`,
  `plan_web.html`.
- El informe publicado es un artifact **privado**; solo se comparte si tú lo compartes desde el menú de la página.

## Contexto del atleta

Objetivo de enero: **bajar de 17:00 en Reforma** (CDMX, 2,240 m), el mismo circuito donde
corrió 17:47 el 20-sep-2026. El sub-16 es el proyecto largo.

Anclas vigentes, medidas el 1-oct-2026 con banda de pecho (Test A, contrarreloj de 30 min):

| | |
|---|---|
| LT2 | **183 lpm a 3:47/km** — media de los últimos 20 min, que es la definición del protocolo |
| LT1 | 153 lpm — **estimado**, pendiente del Test B |
| FCmax | 194 — **observada**, no medida; pendiente del Test C |

Se entrena **7 días**, con el viernes como día ajustable: el único convertible en descanso
total sin recuperarlo. La fuerza es guiada y va siempre **después** de correr, con 4-6 h de
separación: la máxima el jueves tras la calidad, la pliometría el domingo con las cuestas.
Nunca lunes, miércoles ni viernes — esos días existen para absorber el umbral.
