# -*- coding: utf-8 -*-
"""
Construye plan_web.html: el plan dia por dia como pagina publicable.

Lee plan_maestro.json y zonas.json. Los bloques de calentamiento y vuelta a la calma
no se repiten 126 veces: se listan una vez al final y cada dia los referencia por codigo,
que es justo para lo que existen los codigos.

    python3 gen_web_plan.py
"""
import json, os, datetime, html as H

BASE = os.path.dirname(os.path.abspath(__file__))
PLAN = json.load(open(os.path.join(BASE, 'plan_maestro.json'), encoding='utf-8'))
ZC = json.load(open(os.path.join(BASE, 'zonas.json'), encoding='utf-8'))
A = ZC['anclas']
DIAS, REGLAS, META = PLAN['dias'], PLAN['reglas'], PLAN['meta']

e = lambda s: H.escape(str(s or ''))


def lim(zc):
    z = next(x for x in ZC['zonas'] if x['z'] == zc)
    if z['lo_off'] is None:
        return None, None
    lo = 0 if z['lo_off'][1] == -999 else A[z['lo_off'][0]] + z['lo_off'][1]
    return lo, A[z['hi_off'][0]] + z['hi_off'][1]


def mmss(s):
    # Mismo cuidado que en gen_plan_v4: redondear el total, no los segundos sueltos.
    t = round(s)
    return f'{t // 60}:{t % 60:02d}'


def ritmo_fc(fc):
    r = ZC['regresion_fc_ritmo']
    return 1000.0 / ((fc - r['b']) / r['a'])


# ---- catalogo de bloques, recogido del plan -------------------------------
bloques, fuerzas = {}, {}
for d in DIAS:
    if d['cal'] and d['cal_cod'] not in bloques:
        bloques[d['cal_cod']] = d['cal']
    if d['vc'] and d['vc_cod'] not in bloques:
        bloques[d['vc_cod']] = d['vc']
    t = d['pm_titulo']
    if t and t.startswith('FUERZA') and t not in fuerzas:
        fuerzas[t] = d['pm']

# ---- agrupar por semana ---------------------------------------------------
semanas, orden = {}, []
for d in DIAS:
    k = d['semana']
    if k not in semanas:
        semanas[k] = []
        orden.append(k)
    semanas[k].append(d)

def km_de(v):
    import re
    m = re.search(r'([\d.]+)\s*km', v or '')
    return float(m.group(1)) if m else 0.0

# Los km de la sesion de tarde vienen calculados desde gen_plan_v4 (campo pm_km):
# deducirlos otra vez del texto es como se perdian los dobles regenerativos.
km_sem = {k: sum(km_de(d['volumen']) + (d.get('pm_km') or 0) for d in semanas[k]) for k in orden}
KMAX = max(km_sem.values())

TIPO_CLASE = lambda s: ('test' if 'TEST' in s else 'carrera' if 'CARRERA' in s else
                        'off' if 'DESCANSO' in s else
                        'duro' if any(x in s for x in ('UMBRAL', 'VO2', 'ESPECÍFICO', 'SIMULACIÓN', 'AFILADO', 'CUESTAS')) else
                        'fondo' if 'FONDO' in s else 'suave')

def dia_html(d, i):
    cl = TIPO_CLASE(d['sesion'])
    f = datetime.date.fromisoformat(d['fecha'])
    fecha_corta = f'{f.day} {["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"][f.month-1]}'
    chips = ''.join(
        f'<span class="mini"><b>{e(lab)}</b>{e(val)}</span>'
        for lab, val in (('Vol', d['volumen']), ('Ritmo', d['ritmo']), ('FC', d['zona']))
        if val and val != '—')
    if d['descanso']:
        chips += f'<span class="mini"><b>Rec</b>{e(d["descanso"])}</span>'
    cuerpo = []
    if d['principal']:
        cuerpo.append('<div class="proto"><h4>Protocolo</h4><ol>' +
                      ''.join(f'<li>{e(l)}</li>' for l in d['principal']) + '</ol></div>')
    if d['cal']:
        cuerpo.append(f'<p class="ref">Calentamiento <a href="#b-{d["cal_cod"]}">{d["cal_cod"]}</a>'
                      f' &nbsp;·&nbsp; Vuelta a la calma <a href="#b-{d["vc_cod"]}">{d["vc_cod"]}</a></p>')
    if d['pm_titulo']:
        anc = f' <a href="#b-{d["pm_titulo"][:8].strip()}">ver</a>' if d['pm_titulo'].startswith('FUERZA') else ''
        pm = '' if d['pm_titulo'].startswith('FUERZA') else \
             '<ul>' + ''.join(f'<li>{e(l)}</li>' for l in d['pm']) + '</ul>'
        cuerpo.append(f'<div class="pm"><h4>Por la tarde</h4><p class="pmt">{e(d["pm_titulo"])}{anc}</p>{pm}</div>')
    if d['nota']:
        cuerpo.append(f'<p class="coach"><b>Coach:</b> {e(d["nota"])}</p>')
    return f'''<details class="dia {cl}" id="d-{d['fecha']}">
<summary><span class="dd"><i>{e(d['dia'][:3])}</i>{fecha_corta}</span>
<span class="ds">{e(d['sesion'])}</span><span class="chips">{chips}</span></summary>
<div class="det">{''.join(cuerpo)}</div></details>'''


bloques_html = ''.join(
    f'<div class="blq" id="b-{k}"><h4>{k}</h4><ol>' +
    ''.join(f'<li>{e(l)}</li>' for l in v) + '</ol></div>'
    for k, v in sorted(bloques.items()))
fuerza_html = ''.join(
    f'<div class="blq" id="b-{k[:8].strip()}"><h4>{e(k)}</h4><ul>' +
    ''.join(f'<li>{e(l)}</li>' for l in v) + '</ul></div>'
    for k, v in fuerzas.items())

rail = ''.join(
    f'<a class="wk{" dl" if "DESCARGA" in k or "RESET" in k else ""}" href="#s{i}" '
    f'title="Semana {i} · {km_sem[k]:.0f} km" aria-label="Semana {i}, {km_sem[k]:.0f} kilómetros">'
    f'<span class="bar" style="height:{max(km_sem[k] / KMAX * 100, 5):.0f}%"></span>'
    f'<span class="lab"><b>S{i}</b><i>{km_sem[k]:.0f}</i></span></a>'
    for i, k in enumerate(orden))

cuerpo = ''
for i, k in enumerate(orden):
    ds = semanas[k]
    fase = ds[0]['fase']
    ini = datetime.date.fromisoformat(ds[0]['fecha'])
    fin = datetime.date.fromisoformat(ds[-1]['fecha'])
    M = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
    rango = f'{ini.day} {M[ini.month-1]} – {fin.day} {M[fin.month-1]}'
    cuerpo += (f'<section class="sem" id="s{i}"><div class="semcab">'
               f'<p class="semfase">{e(fase)}</p><h3>{e(k)}</h3>'
               f'<p class="semmeta">{rango} &nbsp;·&nbsp; <b>{km_sem[k]:.0f} km</b></p></div>'
               + ''.join(dia_html(d, i) for d in ds) + '</section>')

zonas_filas = ''
for z in ZC['zonas']:
    lo, hi = lim(z['z'])
    if lo is None:
        rng, rit = 'no aplica', 'por ritmo'
    else:
        rng = f'≤{hi}' if not lo else f'{lo}–{hi}'
        rit = f'≥{mmss(ritmo_fc(hi))}' if not lo else f'{mmss(ritmo_fc(hi))}–{mmss(ritmo_fc(lo))}'
    zonas_filas += (f'<tr><td><b>{z["z"]}</b> {e(z["nombre"])}</td><td class="n">{rng}</td>'
                    f'<td class="n">{rit}</td><td>{e(z["habla"])}</td></tr>')

PLANTILLA = open(os.path.join(BASE, 'plan_web_plantilla.html'), encoding='utf-8').read()
out = (PLANTILLA
       .replace('__RAIL__', rail)
       .replace('__CUERPO__', cuerpo)
       .replace('__ZONAS__', zonas_filas)
       .replace('__BLOQUES__', bloques_html + fuerza_html)
       .replace('__REGLAS__', ''.join(f'<li>{e(r)}</li>' for r in REGLAS))
       .replace('__META__', f"{e(META['meta'])}")
       .replace('__ANCLAS__', f"LT1 {A['lt1']} · LT2 {A['lt2']} · FCmax {A['fcmax']}"
                              + (" · provisionales" if A.get('provisional') else ""))
       .replace('__RITMO__', e(META['ritmo_objetivo_cdmx']))
       .replace('__CARRERA__', META['carrera_objetivo'])
       .replace('__NDIAS__', str(len(DIAS))))
open(os.path.join(BASE, 'plan_web.html'), 'w', encoding='utf-8').write(out)
print(f'plan_web.html · {len(out):,} bytes · {len(DIAS)} días · {len(orden)} semanas · '
      f'{len(bloques)} bloques + {len(fuerzas)} rutinas de fuerza')
