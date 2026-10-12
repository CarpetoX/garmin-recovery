#!/usr/bin/env python3
"""Garmin Recovery V4.0.1 — fully offline, certified-snapshot HTML dashboard.

- No network, scripts, external fonts or dynamic data fetching.
- Uses the same SHA-verified snapshot and sleep/HR gates as Garmin V4.0.
- Writes immutable HTML + visual manifest in a shadow artifact folder only.
- This is a descriptive presentation, not an athlete clearance or a delivery receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import re
from pathlib import Path

from cycle_snapshot_report_v38 import build, SnapshotError
from garmin_report_v40 import SAFE_ID, _immutable_write, latest_id, render as render_v40


def mapping(v):
    return v if isinstance(v, dict) else {}


def numeric(v):
    return type(v) in (float, int) and math.isfinite(v)


def esc(v):
    return html.escape(str(v), quote=True)


def amount(v, digits=0, suffix=''):
    if not numeric(v):
        return 'No disponible'
    return f'{v:.{digits}f}{suffix}' if digits else f'{v:,.0f}{suffix}'.replace(',', ' ')


def cell_value(label, value, sub='', state='neutral'):
    return ('<article class="metric"><p class="metric-label">' + esc(label) + '</p>'
            '<div class="metric-number ' + esc(state) + '">' + esc(value) + '</div>'
            '<p class="metric-sub">' + esc(sub) + '</p></article>')


def stage_bar(sleep):
    stages = [('Profundo', sleep.get('deep_minutes'), 'deep'),
              ('Ligero', sleep.get('light_minutes'), 'light'),
              ('REM', sleep.get('rem_minutes'), 'rem')]
    valid = [(label, v, typ) for label, v, typ in stages if numeric(v) and v >= 0]
    # Never invent a stage duration, including unknown awake time.
    if len(valid) != 3 or sum(v for _, v, _ in valid) <= 0:
        return '<p class="empty">Fases del sueño no disponibles o incompletas: no se reconstruyen.</p>'
    total = sum(v for _, v, _ in valid)
    bars = ''.join('<span class="stage ' + typ + '" style="width:' + f'{v / total * 100:.3f}' + '%" '
                   'title="' + esc(f'{label}: {amount(v)} min') + '"></span>' for label, v, typ in valid)
    legends = ''.join('<li><span class="dot ' + typ + '"></span><b>' + esc(amount(v) + ' min') +
                      '</b> ' + esc(label) + '</li>' for label, v, typ in valid)
    return ('<div class="stagebar" role="img" aria-label="' + esc('; '.join(f'{l}: {amount(v)} min' for l, v, _ in valid)) +
            '">' + bars + '</div><ul class="stage-legend">' + legends + '</ul>' +
            '<p class="muted small">Fases estimadas por Garmin; la vigilia no se suma a las fases.</p>')


def srpe_svg(chart):
    valid = (isinstance(chart, list) and len(chart) == 7 and
             all(isinstance(row, dict) and isinstance(row.get('date'), str)
                 and re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date'])
                 for row in chart) and len({r['date'] for r in chart}) == 7)
    if not valid:
        return ('<p class="empty">Gráfica de carga semanal no disponible en el snapshot. '
                'No se reconstruyen ni interpolan valores.</p>')
    vals = [r.get('srpe_from_recorded_duration') for r in chart]
    if any(not numeric(v) or v < 0 for v in vals):
        return ('<p class="empty">Gráfica de carga incompleta: existen valores sRPE sin confirmar. '
                'No se representan como cero.</p>')
    top = max(max(vals), 1)
    base, graph_h, graph_top = 196, 132, 54
    elements = [
        '<svg class="chart-svg" viewBox="0 0 740 248" role="img" aria-labelledby="srpe-title srpe-desc">',
        '<title id="srpe-title">Carga de entrenamiento sRPE de siete días</title>',
        '<desc id="srpe-desc">' + esc(', '.join(f'{r["date"]}: {amount(v, 1)} unidades' for r, v in zip(chart, vals))) + '</desc>',
    ]
    for pct in (0, .5, 1):
        yy = base - pct * graph_h
        elements.append(f'<line x1="36" y1="{yy:.1f}" x2="722" y2="{yy:.1f}" class="gridline"/>')
        elements.append('<text x="31" y="' + f'{yy+4:.1f}' + '" text-anchor="end" class="axis">' +
                        esc(amount(top * pct)) + '</text>')
    for i, (row, value) in enumerate(zip(chart, vals)):
        x = 60 + i * 96
        height = max(0., value / top * graph_h)
        y = base - height
        elements.append(f'<rect x="{x}" y="{y:.2f}" width="46" height="{height:.2f}" rx="7" class="bar"/>')
        elements.append('<text x="' + str(x + 23) + '" y="' + f'{max(45, y - 9):.1f}' +
                        '" text-anchor="middle" class="barlabel">' + esc(amount(value)) + '</text>')
        elements.append('<text x="' + str(x + 23) + '" y="216" text-anchor="middle" class="axis">' +
                        esc(row['date'][8:10] + ' oct') + '</text>')
    elements.append('</svg>')
    return ''.join(elements) + ('<p class="muted small">sRPE = duración grabada × RPE. No equivale a TRIMP '
                                'ni necesariamente a la duración efectiva del WOD.</p>')


def rolling_table(rolling):
    rows = []
    for name, key in [('3 días', '3d'), ('7 días', '7d'), ('28 días', '28d')]:
        d = mapping(rolling.get(key))
        rows.append('<tr><th scope="row">' + esc(name) + '</th>'
                    '<td>' + esc(amount(d.get('daytime_avg_hr'), 1, ' lpm')) + '</td>'
                    '<td>' + esc(amount(d.get('nighttime_avg_hr'), 1, ' lpm')) + '</td>'
                    '<td>' + esc(amount(d.get('daytime_days_present'))) + ' / ' +
                    esc(amount(d.get('nighttime_days_present'))) + '</td></tr>')
    return '<div class="tablewrap"><table><thead><tr><th>Ventana</th><th>Diurna</th><th>Nocturna</th><th>Días válidos D/N</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


CSS = r"""
:root{color-scheme:light dark;--bg:#f3f6fa;--paper:#fff;--ink:#132238;--muted:#64748b;--line:#e2e8f0;--accent:#0b827a;--soft:#e0f5f0;--amber:#a46a00;--amber-bg:#fff5df;--blue:#276bb4;--deep:#315cc5;--light:#8bb9ea;--rem:#9369c8;--shadow:0 12px 32px rgba(25,42,70,.05)}
*{box-sizing:border-box}body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:15px;line-height:1.5} .page{max-width:1020px;margin:0 auto;padding:26px 19px 55px}
header{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:18px} .logo{font-size:14px;font-weight:800;letter-spacing:.10em;text-transform:uppercase;color:var(--accent)} .tiny{font-size:12px;color:var(--muted)} .pill{border:1px solid var(--line);border-radius:99px;padding:6px 11px;font-size:12px;font-weight:700}
h1{font-size:clamp(27px,4vw,41px);letter-spacing:-.045em;line-height:1.11;margin:0 0 9px}h2{font-size:19px;letter-spacing:-.025em;margin:0 0 16px}h3{font-size:15px;margin:0 0 7px}.lead{color:var(--muted);margin:0}.hero{background:linear-gradient(130deg,#112c39 0%,#154c54 70%,#0b7d74 100%);color:#fff;padding:27px;border-radius:24px;margin-bottom:15px;display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap}.hero .tiny,.hero .lead{color:#d8f0ee}.hero strong{font-size:15px}.hero-state{padding:10px 15px;border:1px solid #ffffff60;border-radius:15px;font-weight:700}.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0}.metric,.panel{background:var(--paper);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}.metric{padding:17px 16px;min-height:127px}.metric-label{text-transform:uppercase;letter-spacing:.07em;font-size:11px;font-weight:750;color:var(--muted);margin:0 0 9px}.metric-number{font-size:clamp(22px,3vw,30px);font-weight:830;letter-spacing:-.035em;line-height:1.15}.metric-number.positive{color:var(--accent)}.metric-number.caution{color:var(--amber)}.metric-sub{font-size:12px;color:var(--muted);margin:9px 0 0}.layout{display:grid;grid-template-columns:1.14fr .86fr;gap:13px;margin:13px 0}.panel{padding:22px;min-width:0}.label{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:750;margin:0 0 9px}.section{margin-top:16px}.focal{font-size:30px;font-weight:800;line-height:1.2;letter-spacing:-.04em}.focal span{font-size:15px;color:var(--muted);font-weight:500}.muted{color:var(--muted)}.small{font-size:12px}.empty{padding:22px;border:1px dashed var(--line);border-radius:12px;color:var(--muted);font-size:13px}.stagebar{height:19px;border-radius:12px;overflow:hidden;display:flex;background:var(--line);margin:19px 0 10px}.stage{display:block;height:100%}.deep,.dot.deep{background:var(--deep)}.light,.dot.light{background:var(--light)}.rem,.dot.rem{background:var(--rem)}.stage-legend{display:flex;flex-wrap:wrap;gap:10px 16px;list-style:none;margin:0;padding:0;font-size:12px}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.stage-legend b{font-variant-numeric:tabular-nums} .chart-svg{width:100%;height:auto;display:block;overflow:visible}.gridline{stroke:var(--line);stroke-width:1.5}.axis{font-size:13px;fill:var(--muted)}.barlabel{font-size:13px;font-weight:700;fill:var(--ink)}.bar{fill:var(--accent)}.tablewrap{width:100%;overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}th,td{padding:10px 8px;border-bottom:1px solid var(--line)}thead th{font-weight:700;color:var(--muted);font-size:12px}td{text-align:right;font-variant-numeric:tabular-nums}tbody th{font-weight:600}.statpair{display:flex;gap:12px;flex-wrap:wrap}.statpair>div{flex:1;min-width:110px;background:var(--bg);border-radius:12px;padding:12px}.statpair strong{font-size:23px;display:block;line-height:1.3}.statpair span{font-size:12px;color:var(--muted)}.note{font-size:13px;color:var(--muted);margin:10px 0 0}.flags{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 0}.flag{border-radius:99px;background:var(--amber-bg);color:var(--amber);font-size:11px;font-weight:750;padding:5px 10px}.bullet{padding-left:18px;margin:0}.bullet li{margin:9px 0}.foot{font-size:12px;color:var(--muted);overflow-wrap:anywhere;padding-top:18px;border-top:1px solid var(--line);margin-top:16px}.hash{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px;overflow-wrap:anywhere}
@media(max-width:740px){.page{padding:16px 11px 28px}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}.metric{padding:14px 12px;min-height:115px}.layout{grid-template-columns:1fr}.panel{padding:16px}.hero{border-radius:18px;padding:20px}.hero-state{font-size:12px}.chart-svg .axis{font-size:16px}h2{font-size:18px}}@media(prefers-color-scheme:dark){:root{--bg:#0c1724;--paper:#132337;--ink:#e8f0f9;--muted:#a1afc2;--line:#2c4056;--accent:#5ed8bd;--soft:#173d3b;--amber:#ffd584;--amber-bg:#423320;--blue:#76b3ff;--light:#79a5d1;--deep:#5987e4;--rem:#b88aeb;--shadow:none}.hero{background:linear-gradient(130deg,#102b37,#14545a)}}
@media print{body{background:#fff}.page{max-width:100%;padding:0}.metric,.panel{box-shadow:none;break-inside:avoid}.hero{print-color-adjust:exact;-webkit-print-color-adjust:exact}.bar,.stage{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
""".strip()


def render(ledger, cycle_id):
    """Return deterministic HTML and metadata. No data outside certified snapshot."""
    if not isinstance(cycle_id, str) or not SAFE_ID.fullmatch(cycle_id):
        raise SnapshotError('Unsafe cycle id')
    cert = build(ledger, cycle_id)
    markdown, v4 = render_v40(ledger, cycle_id)  # Same sleep/recency gates, verified twice.
    data = cert['data']
    rec = mapping(data.get('recovery_assessment'))
    curr = mapping(rec.get('current'))
    baseline = mapping(rec.get('baseline_28d'))
    daily = mapping(data.get('daily'))
    quality = mapping(data.get('data_quality'))
    garmin = mapping(data.get('garmin'))
    heart = mapping(garmin.get('heart_rate_today'))
    extended = mapping(garmin.get('extended_today'))
    perf = mapping(mapping(data.get('crossfit')).get('performance_report'))
    week = mapping(mapping(perf.get('window_summaries')).get('recent_7d'))
    live = mapping(mapping(data.get('live_sensor_quality')).get('live_measurements'))
    battery = mapping(garmin.get('body_battery_today'))
    stress = mapping(garmin.get('stress_today'))

    sleep_ok = v4['sleep_confirmed']
    current_ok = curr.get('date') == cycle_id[:10]
    heart_ok = heart.get('date') == cycle_id[:10]
    assessed = rec.get('state') == 'assessed' and current_ok and sleep_ok
    show_hrv = sleep_ok and current_ok
    status = rec.get('status') if assessed else 'Pendiente'
    status_words = {'green': 'Estado favorable', 'yellow': 'Precaución / moderar', 'red': 'Precaución alta'}
    confidence_label = {'medium': 'media', 'high': 'alta', 'low': 'baja'}.get(rec.get('confidence'), 'no disponible')
    quality_confidence = {'medium': 'media', 'high': 'alta', 'low': 'baja'}.get(quality.get('confidence'), 'no disponible')
    quality_state = {'usable': 'utilizable', 'attention': 'revisar', 'good': 'buena'}.get(quality.get('status'), quality.get('status') or 'No disponible')
    status_label = status_words.get(status, 'Estado no evaluable')
    score = amount(rec.get('score'), 0, '/100') if assessed else 'Pendiente'
    hybrid = amount(mapping(daily.get('readiness_hybrid')).get('score'), 0, '/100') if assessed else 'Pendiente'
    hrv = amount(curr.get('hrv_ms'), 0, ' ms') if show_hrv else 'Pendiente'
    hr_rest = amount(heart.get('resting_hr'), 0, ' lpm') if heart_ok else 'No disponible'
    hr_sub = 'Dato del día confirmado por fecha' if heart_ok else 'La FC registrada no corresponde al día del ciclo'
    sleep_h = amount(curr.get('sleep_hours'), 2, ' h') if sleep_ok else 'Pendiente'
    sleep_score = amount(curr.get('sleep_score'), 0, '/100') if sleep_ok else 'Sin confirmar'
    hrv_ref = mapping(baseline.get('hrv_ms'))
    if show_hrv and numeric(hrv_ref.get('median')) and type(hrv_ref.get('n')) is int and hrv_ref['n'] >= 7:
        hrv_sub = f'Mediana 28d: {amount(hrv_ref["median"])} ms · {hrv_ref["n"]} noches'
    else:
        hrv_sub = 'Sin comparación histórica evaluable'

    # Current incomplete days are flagged, never shown as full-day totals.
    day_hr = amount(heart.get('daytime_avg_hr'), 1, ' lpm') if heart_ok else 'No disponible'
    day_suffix = ' · día parcial' if heart_ok and heart.get('partial_day') is True else ''
    night_hr = amount(heart.get('nighttime_avg_hr'), 1, ' lpm') if heart_ok and sleep_ok else 'Pendiente'

    sleep_panel = (
        '<p class="label">Sueño confirmado</p><div class="focal">' + esc(sleep_h) +
        ' <span>· puntuación ' + esc(sleep_score) + '</span></div>' +
        '<p class="note">' + esc((str(curr.get('sleep_start_local') or '') + ' → ' + str(curr.get('sleep_end_local') or '')) if sleep_ok else
                                 'Sueño pendiente. No se utilizan horas ni fases del día anterior.') + '</p>' +
        (stage_bar(mapping(extended.get('sleep_detail'))) if sleep_ok else
         '<p class="empty">No se muestra la distribución de fases hasta confirmar el sueño.</p>')
    )
    recovery_refs = [
        ('HRV nocturna', curr.get('hrv_ms') if sleep_ok and current_ok else None, hrv_ref, ' ms'),
        ('FC en reposo', curr.get('resting_hr') if current_ok else None, mapping(baseline.get('resting_hr')), ' lpm'),
        ('Sueño', curr.get('sleep_hours') if sleep_ok and current_ok else None, mapping(baseline.get('sleep_hours')), ' h'),
    ]
    ref_rows = []
    for label, now, reference, unit in recovery_refs:
        n, med = reference.get('n'), reference.get('median')
        delta = f'{now-med:+.{2 if label == "Sueño" else 1}f}{unit}' if numeric(now) and numeric(med) and type(n) is int and n >= 7 else 'No evaluable'
        ref_rows.append('<tr><th scope="row">' + esc(label) + '</th><td>' +
                        esc(amount(now, 2 if label == 'Sueño' else 1, unit)) + '</td><td>' +
                        esc(amount(med, 2 if label == 'Sueño' else 1, unit)) + '</td><td>' +
                        esc(delta) + '</td><td>' + esc(amount(n)) + '</td></tr>')

    warning_labels = {'baseline_provisional': 'Referencia provisional',
                      'daytime_hr_partial': 'FC diurna parcial',
                      'sleep_unconfirmed_or_pending': 'Sueño pendiente',
                      'recovery_current_date_unverified': 'Recuperación no actual',
                      'heart_rate_today_date_unverified': 'FC diaria no actual',
                      'crossfit_chart_unavailable': 'Gráfica no disponible',
                      'chatgpt_delivery_unverified': 'Entrega no verificada'}
    flags = ''.join('<span class="flag">' + esc(warning_labels.get(code, code)) + '</span>'
                    for code in v4['warning_codes'])
    recommendations = []
    for row in perf.get('recommendations', []) if isinstance(perf.get('recommendations'), list) else []:
        msg = mapping(row).get('text')
        if isinstance(msg, str) and msg.strip():
            recommendations.append('<li>' + esc(msg.strip()[:400]) + '</li>')
    if not recommendations:
        recommendations.append('<li>No hay recomendaciones deportivas específicas confirmadas en este ciclo.</li>')
    live_hr = mapping(live.get('heart_rate_live'))
    live_battery = mapping(live.get('body_battery_live'))
    live_status = '; '.join(
        f'{label}: {value["measured_at"]}' if value.get('state') == 'recent' and isinstance(value.get('measured_at'), str)
        else f'{label}: medición reciente no confirmada'
        for label, value in (('FC', live_hr), ('Body Battery', live_battery))
    )
    # chart data is bounded to 7 verified dates and finite non-negative numbers.
    chart = perf.get('daily_chart_7d')
    chart_svg = srpe_svg(chart)
    html_doc = f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark"><meta name="referrer" content="no-referrer">
<title>Garmin Recovery · Informe visual {esc(cycle_id)}</title>
<style>{CSS}</style></head><body><main class="page">
<header><div class="logo">Garmin Recovery <span class="tiny">/ V4.0.1</span></div><div class="pill">INFORME CERTIFICADO · OFFLINE</div></header>
<section class="hero"><div><p class="tiny">{esc(cert['slot_at'])} · {esc(cycle_id)}</p>
<h1>Tu informe deportivo,<br>de un vistazo.</h1><p class="lead">Recuperación · sueño · CrossFit · calidad de datos</p></div>
<div class="hero-state" aria-label="Estado de recuperación">{esc(status_label)}</div></section>
<section class="cards" aria-label="Indicadores destacados">
{cell_value('Recuperación fisiológica', score, 'Modelo local · confianza '+confidence_label, 'positive' if status=='green' else 'caution' if status=='yellow' else 'neutral')}
{cell_value('Readiness híbrida',hybrid,'Escala distinta del modelo local')}
{cell_value('HRV nocturna',hrv,hrv_sub, 'positive' if show_hrv else 'neutral')}
{cell_value('FC reposo',hr_rest,hr_sub)}</section>
<section class="layout">
<article class="panel" aria-labelledby="sleep-heading"><h2 id="sleep-heading">01 · Sueño</h2>{sleep_panel}</article>
<article class="panel" aria-labelledby="phys-heading"><h2 id="phys-heading">02 · Estado del día</h2>
<div class="statpair"><div><strong>{esc(day_hr)}</strong><span>FC diurna{esc(day_suffix)}</span></div>
<div><strong>{esc(night_hr)}</strong><span>FC nocturna</span></div></div>
<div class="statpair" style="margin-top:12px"><div><strong>{esc(amount(stress.get('avgStressLevel'),0,'/100'))}</strong><span>Estrés Garmin medio</span></div>
<div><strong>{esc(amount(battery.get('latest'),0,'/100'))}</strong><span>Última Body Battery</span></div></div>
<p class="note">{esc(live_status)}</p></article></section>
<section class="layout"><article class="panel" aria-labelledby="load-heading"><h2 id="load-heading">03 · Carga CrossFit · 7 días</h2>
{chart_svg}</article>
<article class="panel" aria-labelledby="train-heading"><h2 id="train-heading">04 · Entrenamiento resumido</h2>
<div class="statpair"><div><strong>{esc(amount(week.get('sessions')))}</strong><span>Sesiones</span></div>
<div><strong>{esc(amount(week.get('mean_recorded_rpe'),2))}</strong><span>RPE medio</span></div></div>
<div class="statpair" style="margin-top:12px"><div><strong>{esc(amount(week.get('srpe_from_recorded_duration'),1))}</strong><span>Carga sRPE · UA</span></div>
<div><strong>{esc(amount(week.get('minimum_recorded_external_volume_kg')))} kg</strong><span>Volumen externo mínimo registrado</span></div></div>
<p class="note">El registro de carga no convierte el tonelaje de máquinas, mancuernas y barra en una medida comparable. Las sesiones sin registro no prueban descanso.</p>
</article></section>
<section class="layout"><article class="panel"><h2>05 · Frente a tu referencia personal</h2>
<div class="tablewrap"><table><thead><tr><th>Indicador</th><th>Actual</th><th>Mediana</th><th>Diferencia</th><th>n</th></tr></thead><tbody>{''.join(ref_rows)}</tbody></table></div>
<p class="note">Referencias de hasta 28 días; requieren al menos 7 noches válidas por indicador para comparar.</p></article>
<article class="panel"><h2>06 · Frecuencia cardíaca</h2>{rolling_table(mapping(garmin.get('heart_rate_rolling')))}
<p class="note">Las medias diurnas excluyen días parciales según la cobertura publicada; no son curvas temporales diarias.</p></article></section>
<section class="layout"><article class="panel"><h2>07 · Recomendaciones del ciclo</h2><ul class="bullet">{''.join(recommendations)}</ul>
<p class="note">Orientaciones descriptivas; no determinan aptitud para levantar máximos ni constituyen diagnóstico médico.</p></article>
<article class="panel"><h2>08 · Calidad y advertencias</h2><p>Calidad del registro: <b>{esc(amount(quality.get('score'),0,'/100'))}</b> · {esc(quality_state)} · confianza {esc(quality_confidence)}.</p>
<div class="flags">{flags}</div><p class="note">Las marcas de tiempo de producción no prueban mediciones en vivo. La entrega de este informe en ChatGPT permanece sin verificar.</p></article></section>
<footer class="foot">Fuente única: snapshot certificado del ciclo <b>{esc(cycle_id)}</b> · corte {esc(cert['slot_at'])}.<br>
SHA-256 del snapshot: <span class="hash">{esc(cert['snapshot_sha256'])}</span>.<br>
Informe generado sin red, bibliotecas externas ni JavaScript. No modifica Garmin Recovery V3.8/V3.9 ni publica en ChatGPT.
</footer></main></body></html>'''
    return html_doc, {
        'version': '4.0.1-visual-preview', 'cycle_id': cycle_id,
        'slot_at': cert['slot_at'], 'snapshot_sha256': cert['snapshot_sha256'],
        'delivery': 'unverified_no_chatgpt_receipt',
        'source': 'verified_cycle_snapshot_only', 'mode': 'artifact_only_parallel_to_v39',
        'sleep_confirmed': sleep_ok, 'chart_complete': v4['chart_complete'],
        'warnings': v4['warning_codes'], 'format': 'offline_responsive_html',
    }


def publish(ledger, cycle_id, outdir, write=False):
    document, meta = render(ledger, cycle_id)
    meta = dict(meta)
    html_bytes = (document.rstrip() + '\n').encode('utf-8')
    meta['html_sha256'] = hashlib.sha256(html_bytes).hexdigest()
    outdir = Path(outdir)
    stem = f'{cycle_id}-{meta["snapshot_sha256"][:16]}-v401-visual'
    output = outdir / (stem + '.html')
    manifest = outdir / (stem + '.manifest.json')
    meta['html_file'] = output.name
    meta['manifest_file'] = manifest.name
    manifest_bytes = (json.dumps(meta, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if not write:
        return {**meta, 'state': 'dry_run', 'html': document}
    for path, contents in ((output, html_bytes), (manifest, manifest_bytes)):
        if path.is_symlink() or path.parent.is_symlink() or (path.exists() and (not path.is_file() or path.read_bytes() != contents)):
            raise SnapshotError('Visual artifact conflict; refusing overwrite')
    a = _immutable_write(output, html_bytes)
    b = _immutable_write(manifest, manifest_bytes)
    return {**meta, 'state': 'already_present' if a == b == 'already_present' else 'published_local'}


def main(argv=None):
    p = argparse.ArgumentParser(description='V4.0.1 offline visual preview from certified snapshots')
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--cycle-id')
    p.add_argument('--outdir', type=Path, default=Path('v40_preview_reports'))
    p.add_argument('--write', action='store_true')
    a = p.parse_args(argv)
    try:
        ledger = json.loads(a.ledger.read_text(encoding='utf-8'))
        cid = a.cycle_id or latest_id(ledger)
        r = publish(ledger, cid, a.outdir, a.write)
    except (OSError, ValueError, TypeError) as exc:
        p.exit(2, 'V4 visual not reportable: ' + str(exc) + '\n')
    print(json.dumps({k: v for k, v in r.items() if k != 'html'}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
