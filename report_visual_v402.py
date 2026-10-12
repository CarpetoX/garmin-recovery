#!/usr/bin/env python3
"""V4.0.2 Visual Performance: offline, certified-snapshot-only visual panels.

Additive to V4.0.1: never edits GitHub, reports, certificates or user data.
The current V4.0.1 snapshot is validated first; 28d history is independently
SHA-validated and each day is selected once. No plotting of invented points.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from cycle_snapshot_report_v38 import build, SnapshotError
from garmin_report_v40 import SAFE_ID, latest_id, _immutable_write
from report_visual_v401 import render as render_v401, esc, amount
from report_visual_data_v402 import model, obj, num

CSS = r"""
/* V4.0.2 / additive, offline, mobile-friendly */
.visual-block{margin:16px 0}.visual-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.trendcard{border:1px solid var(--line);border-radius:15px;padding:13px;background:var(--bg);min-width:0}
.trendtop{display:flex;justify-content:space-between;gap:8px;align-items:center}.trendtitle{font-size:12px;font-weight:700}
.trendvalue{font-size:22px;font-weight:750;margin:4px 0}.spark{width:100%;height:49px;display:block}
.sparkline{fill:none;stroke:var(--accent);stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.sparkdot{fill:var(--accent)}.sparkgap{fill:var(--muted);opacity:.4}.rec-calendar{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;margin-top:14px}
.rec-day{min-height:51px;border-radius:9px;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px solid var(--line);font-size:11px;font-variant-numeric:tabular-nums;background:var(--bg)}
.rec-day .mark{height:4px;width:17px;border-radius:5px;margin-top:5px;background:transparent}
.rec-day[data-status='confirmed']{background:var(--soft);border-color:var(--accent)}
.rec-day[data-status='pending']{background:var(--amber-bg);border-color:var(--amber)}
.rec-day[data-status='missing']{background:var(--bg);border-style:dashed;color:var(--muted)}
.rec-day .mark[data-load='true']{background:var(--blue)}
.legend{display:flex;flex-wrap:wrap;gap:6px 12px;margin-top:10px;font-size:12px;color:var(--muted)}
.indicator{display:inline-flex;align-items:center;border-radius:50px;padding:3px 8px;font-size:11px;font-weight:750;border:1px solid var(--line);color:var(--muted)}
.indicator.ok{color:var(--accent);border-color:var(--accent)}.indicator.partial{color:var(--amber);border-color:var(--amber)}
.zonebar{height:22px;border-radius:11px;overflow:hidden;display:flex;max-width:100%;margin:14px 0 10px;background:var(--line)}
.zone{display:block;height:100%;min-width:0}.zone.z1{background:#7199c4}.zone.z2{background:#4aaea5}.zone.z3{background:#d7c253}.zone.z4{background:#ec9745}.zone.z5{background:#e36b69}
.strength-set{border-bottom:1px solid var(--line);padding:9px 0}.strength-set:last-child{border-bottom:0}
.strengthplot{width:100%;height:130px}.plotline{fill:none;stroke:var(--accent);stroke-width:3}.plotdot{fill:var(--blue)}
.timeline{height:24px;background:var(--line);border-radius:12px;overflow:hidden;display:flex;position:relative;margin:13px 0}
.timeline span{position:absolute;height:100%;top:0}.timeline .deep{background:var(--deep)}.timeline .light{background:var(--light)}.timeline .rem{background:var(--rem)}.timeline .awake{background:var(--amber)}
.evidence td{text-align:left;font-size:12px}.evidence td:nth-child(2){font-weight:700}.evidence td:nth-child(3){overflow-wrap:anywhere}
@media(max-width:680px){.visual-grid{grid-template-columns:1fr}.rec-day{min-height:43px}.rec-calendar{gap:4px}.visual-block{margin:12px 0}}
@media print{.rec-day,.zone,.timeline span{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
""".strip()


def status_badge(kind, caption):
    return '<span class="indicator ' + ('ok' if kind == 'confirmed' else 'partial' if kind == 'partial' else '') + '">' + esc(caption) + '</span>'


def spark(rows, name):
    """Plot dated finite values; keep missing days unconnected, never convert null to zero."""
    if not rows:
        return '<p class="empty">Tendencia no disponible en este corte.</p>'
    vals = [r.get('value') for r in rows]
    good = [v for v in vals if num(v) and v >= 0]
    if not good:
        return '<p class="empty">Sin mediciones certificadas para esta tendencia.</p>'
    lo, hi = min(good), max(good)
    rng = hi - lo or 1.0
    step = 292/max(1,len(rows)-1)
    points = []
    elements = ['<svg class="spark" viewBox="0 0 310 66" role="img" aria-label="' + esc(name + ': ' + ', '.join(r['date']+ ' ' + str(r['value']) if num(r.get('value')) else r['date']+ ' sin dato' for r in rows)) + '">']
    for i, v in enumerate(vals):
        if not num(v):
            if len(points) > 1:
                elements.append('<polyline class="sparkline" points="' + ' '.join(points) + '"/>')
            points = []
            continue
        x = 9 + i*step
        y = 54 - (v-lo)/rng*37
        points.append(f'{x:.2f},{y:.2f}')
        elements.append(f'<circle class="sparkdot" cx="{x:.2f}" cy="{y:.2f}" r="3.5"/>')
    if len(points) > 1:
        elements.append('<polyline class="sparkline" points="' + ' '.join(points) + '"/>')
    elements.append('</svg>')
    return ''.join(elements)


def trends_block(series):
    labels = [('hrv','HRV nocturna','ms'),('rhr','FC reposo','lpm'),('sleep','Sueño','h'),
              ('body_battery','Body Battery','/100'),('recovery','Recuperación','/100'),('srpe','Carga sRPE','UA')]
    cells = []
    for key,label,unit in labels:
        rows = series.get(key, [])
        values = [r['value'] for r in rows if num(r.get('value'))]
        last = rows[-1].get('value') if rows else None
        if key == 'srpe':
            last_label = amount(last,1,' '+unit) if num(last) else 'No disponible'
        else:
            last_label = amount(last,2 if key=='sleep' else 1,' '+unit) if num(last) else 'Pendiente'
        status = ('confirmed' if len(values) >= 5 else 'partial' if values else 'missing')
        cells.append('<article class="trendcard"><div class="trendtop"><span class="trendtitle">' + esc(label) + '</span>' +
                     status_badge(status, f'{len(values)}/{len(rows) or 7} días') + '</div><div class="trendvalue">' + esc(last_label) + '</div>' +
                     spark(rows,label) + '</article>')
    return '<section class="panel visual-block"><h2>09 · Mini tendencias · 7 días</h2><p class="note">Puntos certificados por día, sin interpolaciones ni valores de relleno.</p><div class="visual-grid">' + ''.join(cells) + '</div></section>'


def heatmap_block(rows, verified_count, quarantined):
    blocks=[]
    for r in rows:
        score = r['recovery_score']
        load = r.get('load')
        isload = num(load) and load > 0
        label = f"{r['date']} · recuperación: {amount(score) if num(score) else 'sin dato'} · carga sRPE: {amount(load,1) if num(load) else 'sin dato'}"
        blocks.append('<div class="rec-day" data-status="' + esc(r['state']) + '" title="' + esc(label) + '" aria-label="' + esc(label) + '"><span>' + esc(r['date'][8:10]) + '</span><b>' + (esc(amount(score)) if num(score) else '—') + '</b><span class="mark" data-load="' + str(isload).lower() + '"></span></div>')
    return ('<section class="panel visual-block"><h2>10 · Calendario · 28 días</h2><p class="note">' +
            esc(f'{verified_count}/28 días con snapshot certificado. Azul inferior: entrenamiento registrado con sRPE >0 dentro de la gráfica semanal válida.') +
            '</p><div class="rec-calendar" role="group" aria-label="Histórico diario 28 días">' + ''.join(blocks) + '</div>' +
            '<div class="legend"><span>Verde: evaluación confirmada</span><span>Ámbar: sueño pendiente</span><span>—: sin dato certificado</span><span>Marca azul: carga sRPE</span></div>' +
            ('<p class="note">' + esc(str(len(quarantined))) + ' ciclos históricos excluidos por no superar validación.</p>' if quarantined else '') + '</section>')


def strength_block(grouped, excluded):
    if not grouped:
        return ('<section class="panel visual-block"><h2>11 · Evolución de fuerza</h2>'
                '<p class="empty">El snapshot todavía no contiene series manuales por ejercicio con peso, equipo, repeticiones y confirmación individual. No se deduce el progreso desde el tonelaje agregado ni se estiman 1RM.</p>'
                '<p class="note">El panel se habilita automáticamente cuando los ciclos incluyan <code>manual_strength_sets</code> verificados y asociados a la actividad exacta.</p></section>')
    lines=[]
    for exercise, points in grouped.items():
        pts=points[-15:]
        lo=min(p['kg'] for p in pts)
        hi=max(p['kg'] for p in pts)
        span=(hi-lo) or 1
        pxy=[]
        for i,p in enumerate(pts):
            x=20+i*max(1,260/max(1,len(pts)-1))
            y=99-(p['kg']-lo)/span*74
            pxy.append((x,y))
        coords=' '.join(f'{x:.1f},{y:.1f}' for x,y in pxy)
        svg=('<svg class="strengthplot" viewBox="0 0 310 128" role="img" aria-label="' + esc(exercise + ': ' + ', '.join(f"{p['date']}: {p['kg']} kg x{p['reps']}" for p in pts)) + '">'
             + ('<polyline class="plotline" points="' + coords + '"/>' if len(pts)>1 else '')
             + ''.join(f'<circle class="plotdot" cx="{x:.1f}" cy="{y:.1f}" r="4"/>' for x,y in pxy) + '</svg>')
        last=pts[-1]
        lines.append('<div class="strength-set"><h3>'+esc(exercise)+'</h3><p class="note">Último registro: '+esc(f"{last['date']} · {last['kg']} kg × {last['reps']} reps")+'</p>'+svg+'</div>')
    return ('<section class="panel visual-block"><h2>11 · Evolución de fuerza · series manuales</h2><p class="note">Equipo separado (barra, mancuerna por mano o máquina identificada), registros confirmados; cada punto representa una serie, no un máximo estimado.</p>' + ''.join(lines) + ('<p class="note">Series omitidas por validación: '+str(excluded)+'.</p>' if excluded else '') + '</section>')


def timeline_block(timeline, sleep_confirmed):
    if not sleep_confirmed:
        subtitle='Sueño pendiente: no se dibujan fases ni se reciclan mediciones previas.'
        graphical='<p class="empty">Cronología no disponible: sueño sin confirmar.</p>'
    elif not timeline:
        subtitle='Distribución por duración disponible arriba; cronología minuto a minuto no certificada.'
        graphical='<p class="empty">No hay tramos horarios de cada fase en el snapshot. No se inventa su orden.</p>'
    else:
        subtitle='Orden y horario de las fases respaldados por intervalos certificados.'
        parts=[]
        for r in timeline:
            cls=r['stage']
            parts.append('<span class="'+cls+'" style="left:'+f"{r['start_fraction']*100:.3f}"+'%;width:'+f"{r['width_fraction']*100:.3f}"+'%" title="'+esc(cls+' · '+r['start']+' → '+r['end'])+'"></span>')
        graphical='<div class="timeline" role="img" aria-label="Secuencia temporal de fases de sueño">'+''.join(parts)+'</div><p class="note">Fases Garmin: profundo, ligero, REM y vigilia.</p>'
    return '<section class="panel visual-block"><h2>12 · Cronología de sueño</h2><p class="note">'+esc(subtitle)+'</p>'+graphical+'</section>'


def intensity_block(totals, current):
    zones=totals['zone_minutes']
    n=totals['zone_days']
    legend=''
    if n and sum(zones)>0:
        whole=sum(zones)
        colored=''.join('<span class="zone z'+str(i+1)+'" title="Zona '+str(i+1)+' · '+esc(amount(v,1))+' min" style="width:'+f'{v/whole*100:.3f}'+'%"></span>' for i,v in enumerate(zones))
        graph='<div class="zonebar" role="img" aria-label="Minutos en las cinco zonas Garmin">'+colored+'</div>'
        legend='<div class="legend">'+''.join('<span>Z'+str(i+1)+': '+esc(amount(v,1))+' min</span>' for i,v in enumerate(zones))+'</div>'
        description=f'Zonas cardíacas: {n}/7 días con medición completa de zonas; no representan necesariamente todas las sesiones de la semana.'
    else:
        graph='<p class="empty">Zonas cardíacas agregadas no disponibles en los snapshots diarios certificados. No se estima la intensidad desde el RPE.</p>'
        description='Sin cobertura suficiente para representar porcentajes de tiempo por zona.'
    types = totals['type_counts']
    if types:
        parts='<p class="note">Sesiones por tipo en '+str(totals['type_days'])+'/7 días con clasificación: '+esc(', '.join(f'{k}: {int(v) if float(v).is_integer() else v}' for k,v in types.items()))+'.</p>'
    else:
        parts='<p class="note">No hay clasificación diaria verificable de sesiones en la ventana.</p>'
    # Distinct 4-week Garmin training LOAD balance, never passed off as heart-rate zones.
    balance=obj(obj(obj(current.get('garmin')).get('extended_today')).get('four_week_load_balance'))
    values=[]
    labels=[('Aeróbica baja','monthlyLoadAerobicLow'),('Aeróbica alta','monthlyLoadAerobicHigh'),('Anaeróbica','monthlyLoadAnaerobic')]
    for label,suffix in labels:
        hits=[v for k,v in balance.items() if k.endswith('.'+suffix)]
        if len(hits)==1 and num(hits[0]) and hits[0]>=0:
            values.append((label,hits[0]))
    balance_html='<div class="statpair" style="margin-top:12px">'+''.join('<div><strong>'+esc(amount(v))+'</strong><span>'+esc(label)+'</span></div>' for label,v in values)+'</div>' if len(values)==3 else '<p class="note">Balance de carga Garmin de cuatro semanas no disponible.</p>'
    return ('<section class="panel visual-block"><h2>13 · Intensidad y tipos de sesión</h2><p class="note">'+esc(description)+'</p>'+graph+legend+parts+'<h3>Balance de carga Garmin · 4 semanas</h3>'+balance_html+
            '<p class="note">Este balance usa unidades de carga Garmin y NO es tiempo en zonas; nunca se suma a TRIMP o sRPE.</p></section>')


def evidence_block(meta, model_data):
    series= model_data['series']
    checks=[
        ('Sueño', 'Confirmado' if meta['sleep_confirmed'] else 'Pendiente', 'Control de sueño del informe certificado'),
        ('HRV últimos 7 días', str(sum(num(p['value']) for p in series['hrv']))+'/7 días', 'Solo sueño confirmado'),
        ('FC reposo', str(sum(num(p['value']) for p in series['rhr']))+'/7 días', 'Sin fechas obsoletas'),
        ('Body Battery', str(sum(num(p['value']) for p in series['body_battery']))+'/7 días', 'Fecha real de última lectura'),
        ('Histórico 28 días', str(model_data['historical_days'])+'/28 días', 'Ciclos SHA-256 verificados y deduplicados por fecha'),
        ('Fuerza', 'Disponible' if model_data['strength'] else 'Pendiente', 'Series manuales explícitas y confirmadas'),
        ('Cronología fases sueño', 'Disponible' if model_data['sleep_timeline'] else 'Pendiente', 'No confundir duraciones con secuencia temporal'),
        ('Zonas FC', str(model_data['intensity']['zone_days'])+'/7 días', 'Minutos por zona en los días medidos'),
        ('Entrega ChatGPT', 'No verificada', 'El artefacto de GitHub no constituye un acuse de entrega'),
    ]
    htmlrows=''.join('<tr><th scope="row">'+esc(label)+'</th><td>'+esc(value)+'</td><td>'+esc(note)+'</td></tr>' for label,value,note in checks)
    return '<section class="panel visual-block"><h2>14 · Fiabilidad de las visualizaciones</h2><div class="tablewrap"><table class="evidence"><thead><tr><th>Área</th><th>Cobertura</th><th>Criterio</th></tr></thead><tbody>'+htmlrows+'</tbody></table></div></section>'


def render(ledger, cycle_id):
    if not isinstance(cycle_id, str) or not SAFE_ID.fullmatch(cycle_id):
        raise SnapshotError('Unsafe cycle id')
    certified=build(ledger,cycle_id)
    parent_html, parent_meta=render_v401(ledger,cycle_id)
    evidence=model(ledger,cycle_id,certified,parent_meta)
    blocks=(trends_block(evidence['series']) + heatmap_block(evidence['heatmap'],evidence['historical_days'],evidence['quarantined_cycle_ids']) +
            strength_block(evidence['strength'],evidence['strength_excluded_sets']) + timeline_block(evidence['sleep_timeline'],evidence['sleep_confirmed']) +
            intensity_block(evidence['intensity'],certified['data']) + evidence_block(parent_meta,evidence))
    if '<footer class="foot">' not in parent_html or '</style>' not in parent_html:
        raise SnapshotError('V4.0.1 insertion anchors missing')
    document=(parent_html.replace('</style>',CSS+'</style>',1)
             .replace('/ V4.0.1','/ V4.0.2',1)
             .replace('<footer class="foot">', blocks+'<footer class="foot">',1))
    stat={
        'version':'4.0.2-visual-preview','source':'verified_cycle_snapshots_only',
        'mode':'artifact_only_parallel_to_v39_v401','format':'offline_responsive_html',
        'cycle_id':cycle_id,'snapshot_sha256':certified['snapshot_sha256'], 'slot_at': certified['slot_at'],
        'chatgpt_delivery':'unverified_no_receipt',
        'visual_panels':{'mini_trends':'partial_or_complete','calendar_28d':'partial_or_complete',
                         'strength':'rendered' if evidence['strength'] else 'insufficient_structured_manual_sets',
                         'sleep_timeline':'rendered' if evidence['sleep_timeline'] else 'stages_aggregated_only_or_pending',
                         'intensity_zones':'rendered' if evidence['intensity']['zone_days'] else 'insufficient_verified_zone_series',
                         'reliability':'rendered'},
        'coverage':{
            'historical_days_28d':evidence['historical_days'],
            'hrv_7d':sum(num(p['value']) for p in evidence['series']['hrv']),
            'rhr_7d':sum(num(p['value']) for p in evidence['series']['rhr']),
            'sleep_7d':sum(num(p['value']) for p in evidence['series']['sleep']),
            'body_battery_7d':sum(num(p['value']) for p in evidence['series']['body_battery']),
            'zone_days_7d':evidence['intensity']['zone_days'],
            'type_days_7d':evidence['intensity']['type_days'],
            'quarantined_invalid_historical_cycles':len(evidence['quarantined_cycle_ids']),
        },
        'validation_warnings': list(parent_meta['warnings']) + (['historical_quarantine'] if evidence['quarantined_cycle_ids'] else []),
        'parent_visual_version':'4.0.1-visual-preview',
    }
    return document, stat


def publish(ledger, cycle_id, outdir, write=False):
    document, stat=render(ledger,cycle_id)
    html_bytes=(document.rstrip()+'\n').encode('utf-8')
    stat['html_sha256']=hashlib.sha256(html_bytes).hexdigest()
    root=Path(outdir)
    stem=f'{cycle_id}-{stat["snapshot_sha256"][:16]}-v402-visual'
    htmlpath=root/(stem+'.html')
    manifest=root/(stem+'.manifest.json')
    stat['html_file']=htmlpath.name
    stat['manifest_file']=manifest.name
    man_bytes=(json.dumps(stat,sort_keys=True,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
    if not write:
        return {**stat,'state':'dry_run','html':document}
    # Validate all potential destinations prior to writing either artifact.
    for path,body in ((htmlpath,html_bytes),(manifest,man_bytes)):
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and (not path.is_file() or path.read_bytes()!=body)):
            raise SnapshotError('V4.0.2 existing artifact differs; refusing overwrite')
    a=_immutable_write(htmlpath,html_bytes)
    b=_immutable_write(manifest,man_bytes)
    return {**stat,'state':'already_present' if a==b=='already_present' else 'published_local'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='V4.0.2 offline visual dashboard; only certified snapshots')
    parser.add_argument('--ledger',type=Path,default=Path('report_cycles.json'))
    parser.add_argument('--cycle-id')
    parser.add_argument('--outdir',type=Path,default=Path('v40_preview_reports'))
    parser.add_argument('--write',action='store_true')
    a=parser.parse_args(argv)
    try:
        ledger=json.loads(a.ledger.read_text(encoding='utf-8'))
        result=publish(ledger,a.cycle_id or latest_id(ledger),a.outdir,a.write)
    except (OSError,ValueError,TypeError) as exc:
        parser.exit(2,'V4.0.2 preview not reportable: '+str(exc)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='html'},sort_keys=True,ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
