# -*- coding: utf-8 -*-
import csv, datetime

R=[]
def add(f,fase,ses,vol,ritmo,zona,pm,nota):
    d=datetime.date.fromisoformat(f)
    dias=['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    R.append([f,dias[d.weekday()],fase,ses,vol,ritmo,zona,pm,nota])

F2="Fase 2: Base y Umbral"; F3="Fase 3: VO2 Específico"; F4="Fase 4: Pico de Forma"; F5="Fase 5: Taper y Carrera"
FA="FUERZA A — Máxima (45 min)"; FB="FUERZA B — Pliometría + Core (35 min)"

# --- Fin de semana de arranque ---
add("2026-07-25",F2,"FONDO + final progresivo","15 km","12 km @4:50-5:00 + 3 km bajando a 4:20","Z2 → Z3","-","Primer fondo del bloque. No lo negocies.")
add("2026-07-26",F2,"CUESTAS A — Neuromuscular","8 km total","10 x 12 s cuesta a MÁXIMO","Z1 + picos","-","Bajar CAMINANDO 2-3 min. Recuperación completa.")

def semana(lun, fase, mar_ses, mar_vol, mar_ritmo, mar_zona, jue_ses, jue_vol, jue_ritmo, jue_zona,
           sab_km, sab_det, dom_tipo, dom_det, dobles, notas=None, lun_km="8 km", mie_km="10 km"):
    d=datetime.date.fromisoformat(lun)
    n=notas or {}
    f=lambda i:(d+datetime.timedelta(days=i)).isoformat()
    add(f(0),fase,"Recuperación",lun_km,"5:20-5:30","Z1 (<158)",
        "Trote suave 5 km Z1" if "lun" in dobles else "-", n.get('lun',"Soltar piernas del fin de semana."))
    add(f(1),fase,mar_ses,mar_vol,mar_ritmo,mar_zona,FA,n.get('mar',"Fuerza DESPUÉS de correr, mínimo 4 h de separación."))
    add(f(2),fase,"Rodaje medio",mie_km,"5:00","Z2 (158-166)",
        "Trote suave 6 km Z1" if "mie" in dobles else "-", n.get('mie',"Frenar de verdad. FC techo 166."))
    add(f(3),fase,jue_ses,jue_vol,jue_ritmo,jue_zona,FB,n.get('jue',"Pliometría en piernas ya calientes."))
    add(f(4),fase,"Recuperación","6 km","5:30","Z1","-",n.get('vie',"Regenerativo estricto. Nada de fuerza hoy."))
    add(f(5),fase,"FONDO + final progresivo",sab_km,sab_det,"Z2 → Z3","-",n.get('sab',""))
    add(f(6),fase,dom_tipo,"8-10 km total",dom_det,"Z5 en la rep" if "B" in dom_tipo else "Z1 + picos","-",n.get('dom',""))

# S1
semana("2026-07-27",F2,"Intervalos de Umbral","4 x 2 km","3:40-3:45","Z4 (177-186)",
       "Tempo continuo","2 cal + 5 tempo + 2 enf","3:50-3:55","Z3-Z4",
       "16 km","13 km @4:50 + 3 km bajando a 4:15","CUESTAS B — Fuerza-Resistencia","8 x 45 s cuesta fuerte",[],
       {'jue':"Completar los 5 km enteros. Sal conservador.",'sab':"Semana 1 de 8. Construyendo.",
        'dom':"Bajada TROTANDO = recuperación. Cadencia >180."})
# S2
semana("2026-08-03",F2,"Intervalos de Umbral","5 x 2 km","3:38-3:42","Z4",
       "Tempo continuo","2 cal + 6 tempo + 2 enf","3:48-3:52","Z4",
       "17 km","14 km @4:45 + 3 km bajando a 4:10","CUESTAS A — Neuromuscular","12 x 12 s cuesta a MÁXIMO",["mie"],
       {'sab':"", 'dom':"Día ligero tras el fondo. No lo conviertas en aeróbico."})
# S3 pico volumen
semana("2026-08-10",F3,"Series específicas 5K","5 x 1000 m","3:10-3:12","Z5 (>186)",
       "Series cortas (velocidad)","10 x 400 m","1:15 vuelta (~3:07/km)","Z5 (>187)",
       "18 km","15 km @4:45 + 3 km bajando a 4:10","CUESTAS B — Fuerza-Resistencia","10 x 45 s cuesta fuerte",["mie"],
       {'mar':"LA sesión clave del bloque. Rec 2 min activos. + Fuerza A PM.",
        'jue':"Rec 60 s. Mecánica de 5K. + Fuerza B PM.",
        'sab':"PICO DE VOLUMEN — fondo más largo de todo el plan.",'dom':"Pico de carga en cuestas."})
# S4 descarga
semana("2026-08-17",F3,"Series específicas 5K","4 x 1000 m","3:10","Z5",
       "Rodaje con rectas","8 km + 6 x 100 m","Suave + explosivo","Z2",
       "13 km","11 km @4:45 + 2 km a 4:15","CUESTAS A — corto","8 x 10 s cuesta a MÁXIMO",["mie"],
       {'lun':"SEMANA DE DESCARGA. Volumen -25%. Aquí es donde absorbes todo.",
        'mar':"Solo 4 series. Calidad, no cantidad.",
        'jue':"Sin fuerza pesada esta semana — solo Fuerza B ligera.",
        'sab':"Fondo corto. Confía en la descarga.",'dom':"Cuestas breves. Recuperar es entrenar."},
       lun_km="6 km", mie_km="8 km")
# S5
semana("2026-08-24",F4,"Series específicas 5K","6 x 1000 m","3:08-3:10","Z5",
       "Pista / Ritmo carrera","3 x 1500 m","3:10-3:12","Z4-Z5",
       "16 km","13 km @4:40 + 3 km a 4:05","CUESTAS B — Fuerza-Resistencia","10 x 45 s cuesta fuerte",["mie"],
       {'lun':"Vuelve la carga. Debes sentirte fresco tras la descarga.",
        'mar':"Sesión más dura del bloque hasta ahora.",'jue':"Rec 3 min. Simulación parcial de carrera."})
# S6 pico intensidad + TEST
semana("2026-08-31",F4,"TEST DE LACTATO","2 x 2000 m","3:08-3:10","Z5",
       "Series cortas (velocidad)","10 x 400 m","1:14 vuelta","Z5",
       "15 km","12 km @4:40 + 3 km a 4:05","CUESTAS A — Afilado","10 x 10 s cuesta a MÁXIMO",["mie"],
       {'mar':"EL TEST. Rec 3 min. Aquí sabemos tu tiempo real de carrera.",
        'jue':"Última sesión de fuerza pesada del bloque.",
        'sab':"",'dom':"Explosividad pura. Cero fatiga residual."})
# S7 pre-taper
semana("2026-09-07",F4,"Pista / Ritmo carrera","4 x 1500 m","3:08-3:10","Z4-Z5",
       "Series cortas","8 x 400 m","1:14 vuelta","Z5",
       "12 km","10 km @4:40 + 2 km a 4:05","CUESTAS A — corto","6 x 10 s cuesta",["mie"],
       {'lun':"Última semana completa. Empieza a bajar volumen.",
        'mar':"Ritmo de carrera con recuperación amplia (3 min).",
        'jue':"Solo Fuerza B LIGERA — nada pesado ya.",
        'sab':"Último fondo. Corto y alegre.",'dom':"Mantener chispa, nada más."},
       lun_km="6 km", mie_km="8 km")

# S8 TAPER
add("2026-09-14",F5,"Recuperación","6 km","5:20","Z1","-","Empieza el taper. Volumen -50%, intensidad se mantiene.")
add("2026-09-15",F5,"Series de afilado","6 x 400 m","3:08","Z4-Z5","-","Recordar el ritmo, NO fatigar. Rec 2 min completos.")
add("2026-09-16",F5,"Rodaje suave","6 km","5:20","Z1-Z2","Movilidad 15 min","Nada de fuerza. Solo movilidad y estiramiento.")
add("2026-09-17",F5,"Activación 5K","6 km total","2 x 800 m a 3:10","Z2-Z5","-","Última sesión con ritmo. Debe sentirse fácil.")
add("2026-09-18",F5,"Trote muy suave","4 km","5:40","Z1","-","Piernas sueltas. Dormir 8 h y empezar a hidratar.")
add("2026-09-19",F5,"Trote pre-carrera + rectas","4 km + 4 x 80 m","Muy suave","Z1","-","Soltar nervios. Prepara ropa y dorsal hoy.")
add("2026-09-20",F5,"🏁 CARRERA 5K","5 km","OBJETIVO 3:19-3:23/km","Z5 (>188)","-","Salir en 3:22 los primeros 1000 m. Apretar del km 3.")

hdr=["Fecha","Día","Fase","Sesión AM","Volumen","Ritmo objetivo","Zona FC","Sesión PM (doble/fuerza)","Notas del coach"]
with open('plan_v3_completo.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.writer(fh); w.writerow(hdr); w.writerows(R)
print("filas:",len(R))
print("dobles:",sum(1 for r in R if 'Trote' in r[7]))
print("fuerza:",sum(1 for r in R if 'FUERZA' in r[7]))
