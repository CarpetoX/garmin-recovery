#!/usr/bin/env python3
"""CrossFit V3.6: read-only, additive report over already validated V3.2/V3.5.

No Garmin calls, no rewriting sources, no derived one-rep max, no delivery claims.
Produces independent JSON + Markdown for optional publication by CrossFit workflow.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
VERSION = '3.6'


class ReportError(ValueError):
    pass


def obj(value):
    return value if isinstance(value, dict) else {}


def date_from(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return value.astimezone(TZ) if value.tzinfo is not None else None
    except ValueError:
        return None


def safe_number(value, lo=None, hi=None):
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        return None
    return round(value, 2)


def finite_count(value):
    return value if type(value) is int and value >= 0 else None


def read_object(path, *, required=False):
    try:
        payload = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError, ValueError) as error:
        if required:
            raise ReportError(f'Fuente obligatoria no disponible: {Path(path).name}') from error
        return {}
    if not isinstance(payload, dict):
        if required:
            raise ReportError(f'Fuente obligatoria con tipo incorrecto: {Path(path).name}')
        return {}
    return payload


def make_report(crossfit, trends, recovery=None, quality=None, ready=None, now=None):
    """Build a report without mutating input structures or recomputing load."""
    crossfit, trends = obj(crossfit), obj(trends)
    recovery, quality, ready = obj(recovery), obj(quality), obj(ready)
    base = obj(trends.get('performance_report_v32'))
    addon = obj(base.get('performance_enhancements_v35'))
    day = date_from(trends.get('as_of_date'))
    if not day or trends.get('schema_version') != 1 or trends.get('version') != '3.1':
        raise ReportError('V3.6 requiere training_trends_v31 válido y fechado')
    if (base.get('version') != '3.2' or addon.get('version') != '3.5'
            or base.get('as_of_date') != day.isoformat()
            or addon.get('as_of_date') != day.isoformat()):
        raise ReportError('Se requiere informe validado V3.2 + complemento V3.5')
    if not isinstance(crossfit.get('activities'), list):
        raise ReportError('Falta la lista de actividades CrossFit')
    source_time = timestamp(crossfit.get('generated_at'))
    trend_time = timestamp(trends.get('generated_at'))
    if (not source_time or not trend_time
            or trends.get('source_generated_at') != crossfit.get('generated_at')
            or obj(base.get('provenance')).get('crossfit_generated_at') != crossfit.get('generated_at')
            or trend_time < source_time - timedelta(minutes=2)):
        raise ReportError('Desfase o discrepancia entre CrossFit y tendencias; NO publicar')
    if trend_time.astimezone(TZ).date() != day:
        raise ReportError('Las tendencias no corresponden a la fecha local declarada')

    chart = obj(base.get('charts')).get('daily_28d')
    if not isinstance(chart, list) or len(chart) != 28:
        raise ReportError('Gráfica de 28 días de V3.2 ausente/incompleta')
    expected = [str(day - timedelta(days=k)) for k in range(27, -1, -1)]
    if [obj(v).get('date') for v in chart] != expected:
        raise ReportError('Fechas de gráfica no consecutivas o inconsistentes')

    points = []
    for item in chart:
        row = obj(item)
        sessions = finite_count(row.get('recorded_sessions'))
        if sessions is None:
            raise ReportError('Número de sesiones no válido en la gráfica')
        points.append({
            'date': row['date'], 'recorded_sessions': sessions,
            'mean_rpe': safe_number(row.get('mean_rpe'), 0, 10),
            'srpe_proxy': safe_number(row.get('srpe_proxy'), 0),
            'trimp': safe_number(row.get('trimp'), 0),
            'sleep_hours': safe_number(row.get('sleep_hours'), 0, 24),
            'hrv_ms': safe_number(row.get('hrv'), 0),
            'resting_hr_bpm': safe_number(row.get('resting_hr'), 0),
            'sleep_score': safe_number(row.get('sleep_score'), 0, 100),
            'no_record_does_not_prove_rest': sessions == 0,
        })

    windows = obj(trends.get('windows'))
    seven = obj(windows.get('7d'))
    twenty_eight = obj(windows.get('28d'))
    if any(finite_count(x.get('recorded_sessions')) is None for x in (seven, twenty_eight)):
        raise ReportError('Ventanas de sesiones ilegibles')
    if seven['recorded_sessions'] > twenty_eight['recorded_sessions']:
        raise ReportError('Más sesiones en 7 días que en 28 días')
    rpt = obj(base.get('window_comparison'))
    comparison = obj(rpt.get('current_vs_previous_7d'))
    interpretation = obj(base.get('interpretation_quality'))
    comparison_eligible = comparison.get('comparison_status') == 'descriptive_only'
    strength_data = obj(base.get('strength')).get('exact_exercise_groups')
    if not isinstance(strength_data, list):
        strength_data = []
    strength = []
    for item in strength_data:
        x = obj(item)
        if not all(isinstance(x.get(key), str) and x[key].strip()
                   for key in ('exercise', 'equipment', 'load_unit')):
            continue
        days = finite_count(x.get('distinct_training_days'))
        strength.append({
            'exercise': x['exercise'], 'equipment': x['equipment'],
            'load_unit': x['load_unit'], 'distinct_days': days,
            'last_day': x.get('last_day'),
            'observed_peak_change_kg': safe_number(x.get('observed_peak_change_kg')),
            'progression_state': 'descriptive_only_not_rep_rpe_matched' if days and days >= 2
                                  else 'insufficient_repeated_days',
            'verified_1rm': False,
        })
    strength.sort(key=lambda x: (x['exercise'].casefold(), x['equipment'], x['load_unit']))

    rec_current = obj(recovery.get('current')) if recovery.get('state') == 'assessed' and obj(recovery.get('current')).get('date') == str(day) else {}
    rec_valid = bool(rec_current)
    recovery_view = {
        'state': 'same_day_assessed' if rec_valid else 'not_current_or_unavailable',
        'score_heuristic': safe_number(recovery.get('score'), 0, 100) if rec_valid else None,
        'status_original': recovery.get('status') if rec_valid else None,
        'confidence_original': recovery.get('confidence') if rec_valid else None,
        'hrv_ms': safe_number(rec_current.get('hrv_ms'), 0),
        'sleep_hours': safe_number(rec_current.get('sleep_hours'), 0, 24),
        'resting_hr_bpm': safe_number(rec_current.get('resting_hr'), 0),
        'sleep_score': safe_number(rec_current.get('sleep_score'), 0, 100),
        'not_a_medical_diagnosis': True,
    }
    q_time = timestamp(quality.get('generated_at'))
    quality_view = {'state': 'same_local_day' if q_time and q_time.date() == day else 'stale_or_unavailable',
                    'data_score_not_software_quality': safe_number(quality.get('score'), 0, 100)
                    if q_time and q_time.date() == day else None,
                    'issues': [str(s) for s in quality.get('issues', []) if isinstance(s, str)][:12]
                    if q_time and q_time.date() == day and isinstance(quality.get('issues'), list) else []}

    ready_sources = obj(ready.get('source_generated_at'))
    cert_matches = (ready.get('status') == 'ready'
                    and ready_sources.get('crossfit_insights.json') == crossfit.get('generated_at')
                    and timestamp(ready.get('verified_at')) is not None
                    and timestamp(ready['verified_at']).date() == day)
    provenance = obj(ready.get('measurement_provenance')) if cert_matches else {}
    live = {}
    for key in ('heart_rate_live', 'body_battery_live'):
        record = obj(provenance.get(key))
        measured = timestamp(record.get('measured_at'))
        live[key] = {'state': record.get('state') if isinstance(record.get('state'), str) else 'unverified',
                     'measured_at': measured.isoformat() if measured else None}

    suggestions = []
    seen = set()
    for entry in [*base.get('recommendations', []), *addon.get('recommendations', [])]:
        if not isinstance(entry, dict):
            continue
        msg = entry.get('text') or entry.get('message')
        kind = entry.get('kind') or entry.get('category')
        if not isinstance(msg, str) or not msg.strip() or not isinstance(kind, str) or kind in seen:
            continue
        seen.add(kind)
        suggestions.append({'source': 'existing_v32_v35_rule', 'kind': kind,
                            'priority': entry.get('priority') if type(entry.get('priority')) is int else 2,
                            'text': msg.strip()})
    suggestions.sort(key=lambda x: x['priority'])

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ReportError('Hora de generación sin zona horaria')
    data = {
        'schema_version': 1, 'version': VERSION,
        'generated_at': current.astimezone(TZ).isoformat(), 'as_of_date': str(day),
        'timezone': 'Europe/Madrid',
        'status': 'descriptive_limited' if interpretation.get('level') == 'provisional' else 'descriptive',
        'source_provenance': {'crossfit_generated_at': crossfit['generated_at'],
                              'trends_generated_at': trends['generated_at'],
                              'same_source_verified': True,
                              'certificate_state': 'matched_data_ready_source' if cert_matches else 'not_linked_to_current_certificate',
                              'chatgpt_delivery': 'unverified_no_receipt'},
        'training': {'last_7d': {'registered_sessions': seven['recorded_sessions'],
                                'rpe_coverage': {'with_rpe': finite_count(seven.get('recorded_sessions_with_rpe')),
                                                 'sessions': seven['recorded_sessions']},
                                'mean_session_rpe': safe_number(seven.get('mean_session_rpe'), 0, 10),
                                'recorded_minutes': safe_number(seven.get('recorded_duration_minutes'), 0),
                                'srpe_recorded_minutes_proxy': safe_number(seven.get('srpe_recorded_duration_sum'), 0)},
                     'last_28d': {'registered_sessions': twenty_eight['recorded_sessions'],
                                  'trend_confidence': trends.get('confidence')},
                     'week_comparison': {'eligible': comparison_eligible,
                                         'srpe_delta_pct': safe_number(comparison.get('srpe_proxy_delta_pct')) if comparison_eligible else None,
                                         'trimp_delta_pct': safe_number(comparison.get('trimp_delta_pct')) if comparison_eligible else None,
                                         'status': comparison.get('comparison_status')},
                     'strength_exact_equipment': strength,
                     'benchmark': obj(addon.get('benchmarks')),
                     'missing_day_is_not_proof_of_rest': True,
                     'session_rpe_is_not_set_rir': True},
        'recovery': recovery_view, 'data_quality': quality_view,
        'live_measures': live,
        'charts': {'daily_28d': points, 'last_7d': points[-7:],
                   'modality_rpe_7d': obj(addon.get('charts')).get('modality_rpe_7d', []),
                   'no_causal_inference': True},
        'recommendations': suggestions[:3],
        'limitations': ['No equiparar minutos Garmin y tiempo efectivo del WOD.',
                        'No sumar kg de barras, máquinas y cargas por pierna.',
                        'Un día sin actividad registrada no demuestra descanso.',
                        'No inferir 1RM ni RIR a partir del RPE de sesión.',
                        'La publicación del archivo no acredita entrega en ChatGPT.'],
    }
    validate(data)
    return data


def validate(report):
    r = obj(report)
    if r.get('version') != VERSION or r.get('schema_version') != 1 or not date_from(r.get('as_of_date')):
        raise ReportError('Contrato V3.6 inválido')
    if obj(r.get('source_provenance')).get('same_source_verified') is not True:
        raise ReportError('No hay correspondencia de fuentes')
    d = obj(r.get('charts')).get('daily_28d')
    if not isinstance(d, list) or len(d) != 28:
        raise ReportError('La serie diaria no tiene 28 puntos')
    day = date_from(r['as_of_date'])
    if [obj(x).get('date') for x in d] != [str(day - timedelta(days=k)) for k in range(27, -1, -1)]:
        raise ReportError('Serie de fechas inválida')
    training = obj(r.get('training'))
    if not isinstance(training.get('missing_day_is_not_proof_of_rest'), bool) or not training['missing_day_is_not_proof_of_rest']:
        raise ReportError('Falta advertencia de días sin entrenamiento')
    if obj(r.get('source_provenance')).get('chatgpt_delivery') != 'unverified_no_receipt':
        raise ReportError('Prohibido atribuir entrega de mensaje')
    if any(row.get('verified_1rm') is not False for row in training.get('strength_exact_equipment', [])):
        raise ReportError('No estimar máximos verificados sin prueba')
    json.dumps(report, allow_nan=False)
    return True


def fmt(value, suffix=''):
    return '—' if value is None else f'{value:g}{suffix}' if isinstance(value, (float, int)) else str(value)


def markdown(report):
    t = report['training']
    r = report['recovery']
    s = t['last_7d']
    q = report['data_quality']
    cov = s['rpe_coverage']
    lines = [f'# Garmin Recovery · Informe CrossFit V3.6 · {report["as_of_date"]}', '',
             f'**Estado:** {report["status"]} · **Origen:** CrossFit y tendencias V3.2/V3.5 verificados.',
             '', '## Entrenamiento (últimos 7 días)', '',
             f'- Sesiones registradas: **{s["registered_sessions"]}**; RPE disponible: **{fmt(cov["with_rpe"])} de {cov["sessions"]}**.',
             f'- RPE medio por sesión: **{fmt(s["mean_session_rpe"])}**.',
             f'- Duración registrada Garmin: **{fmt(s["recorded_minutes"], " min")}**.',
             f'- Proxy sRPE × minutos Garmin: **{fmt(s["srpe_recorded_minutes_proxy"])}** (no equivale al tiempo efectivo del WOD).',
             f'- Comparación semanal: **{"descriptiva disponible" if t["week_comparison"]["eligible"] else "insuficiente historial comparable"}**.',
             '', '## Recuperación y calidad', '',
             f'- Recuperación: **{r["state"]}**; puntuación heurística **{fmt(r["score_heuristic"])}**, estado original **{fmt(r["status_original"])}**, confianza **{fmt(r["confidence_original"])}**.',
             f'- HRV: **{fmt(r["hrv_ms"], " ms")}**; sueño: **{fmt(r["sleep_hours"], " h")}**; FC reposo: **{fmt(r["resting_hr_bpm"], " lpm")}**.',
             f'- Calidad de datos Garmin: **{fmt(q["data_score_not_software_quality"], "/100")}** ({q["state"]}; no es la nota del software).',
             '', '## Evolución reciente', '',
             '| Fecha | Sesiones | RPE medio | Proxy sRPE | HRV ms | Sueño h | FC reposo |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for row in report['charts']['last_7d']:
        lines.append('| ' + ' | '.join([row['date'], str(row['recorded_sessions']), fmt(row['mean_rpe']),
                                       fmt(row['srpe_proxy']), fmt(row['hrv_ms']),
                                       fmt(row['sleep_hours']), fmt(row['resting_hr_bpm'])]) + ' |')
    lines.extend(['', '*Una fecha con cero sesiones registradas no demuestra que fuera un día de descanso.*',
                  '', '## Fuerza: observaciones por equipo', ''])
    strength = t['strength_exact_equipment']
    if not strength:
        lines.append('Aún no hay bloques de fuerza comparables.')
    else:
        lines.extend(['| Ejercicio | Equipo | Unidad | Días distintos | Interpretación |',
                      '|---|---|---|---:|---|'])
        for row in strength[:15]:
            lines.append(f'| {row["exercise"]} | {row["equipment"]} | {row["load_unit"]} | {fmt(row["distinct_days"])} | {row["progression_state"]} |')
    lines.extend(['', '## Recomendaciones con evidencia', ''])
    if report['recommendations']:
        for idx, x in enumerate(report['recommendations'], 1):
            lines.append(f'{idx}. {x["text"]}')
    else:
        lines.append('No hay nuevas recomendaciones con evidencia suficiente.')
    lines.extend(['', '## Estado y limitaciones', '',
                  f'- Certificado: **{report["source_provenance"]["certificate_state"]}**.',
                  '- Entrega en ChatGPT: **no verificada**.',
                  '- Frecuencia cardíaca y Body Battery: usar siempre la hora real de la muestra, no la hora de generación del JSON.',
                  '- El informe es descriptivo, no diagnóstico, y no demuestra causalidad.', ''])
    return '\n'.join(lines)



def svg_chart(report):
    """Stand-alone SVG with separate scales; gaps remain gaps, never zeroes."""
    from xml.sax.saxutils import escape
    points = report['charts']['daily_28d']
    palette = [('hrv_ms', 'HRV durante el sueño (ms)', '#2969a7'),
               ('srpe_proxy', 'RPE de sesión × minutos Garmin (proxy)', '#b36e22')]
    width, height = 880, 485
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
           'role="img" aria-label="Evolución de HRV y carga percibida de 28 días; los valores ausentes no se representan">',
           '<rect width="880" height="485" fill="#ffffff"/>',
           '<text x="38" y="32" fill="#202d3d" font-size="18" font-family="sans-serif" font-weight="bold">CrossFit V3.6 · 28 días</text>',
           '<text x="38" y="52" fill="#546477" font-size="11" font-family="sans-serif">Dos escalas independientes · Sin interpolar días sin datos</text>']
    left, right = 64, 840
    for j, (field, label, color) in enumerate(palette):
        top, bottom = (83, 231) if j == 0 else (278, 426)
        observed = [row[field] for row in points if row[field] is not None]
        out.append(f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" rx="6" fill="#f6f8fa"/>')
        out.append(f'<text x="{left}" y="{top-10}" fill="{color}" font-size="13" font-family="sans-serif">{escape(label)}</text>')
        if not observed:
            out.append(f'<text x="{(left+right)//2}" y="{(top+bottom)//2}" text-anchor="middle" fill="#6c7682" font-size="12" font-family="sans-serif">Sin muestras suficientes</text>')
            continue
        lo, hi = min(observed), max(observed)
        margin = max((hi-lo)*0.12, 1.0)
        lo, hi = max(0, lo - margin), hi + margin
        for frac in (0, 0.5, 1):
            y = bottom - frac*(bottom-top)
            value = lo + frac*(hi-lo)
            out.append(f'<path d="M{left} {y:.1f} H{right}" stroke="#d8dfe7" stroke-width="1"/>')
            out.append(f'<text x="{left-9}" y="{y+3:.1f}" fill="#596470" text-anchor="end" font-size="10" font-family="sans-serif">{value:.0f}</text>')
        coordinates = []
        for index, item in enumerate(points):
            value = item[field]
            if value is None:
                coordinates.append(None)
                continue
            x = left + index*(right-left)/27
            y = bottom - (value-lo)/(hi-lo)*(bottom-top)
            coordinates.append((x, y))
        for i in range(len(coordinates)-1):
            if coordinates[i] and coordinates[i+1]:
                x1,y1 = coordinates[i]; x2,y2 = coordinates[i+1]
                out.append(f'<path d="M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}" stroke="{color}" stroke-width="2.5" fill="none"/>')
        for p in coordinates:
            if p:
                out.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="3" fill="{color}"/>')
        out.append(f'<text x="{right}" y="{top-10}" text-anchor="end" fill="#65717e" font-size="10" font-family="sans-serif">{len(observed)} muestras observadas</text>')
        for idx in (0, 7, 14, 21, 27):
            x = left + idx*(right-left)/27
            label_date = points[idx]['date'][5:]
            out.append(f'<text x="{x:.1f}" y="{bottom+14}" text-anchor="middle" fill="#65717e" font-size="10" font-family="sans-serif">{label_date}</text>')
    out.extend(['<text x="38" y="466" fill="#65717e" font-size="11" font-family="sans-serif">La ausencia de RPE o actividad registrada no significa carga cero ni día de descanso.</text>', '</svg>'])
    return '\n'.join(out) + '\n'

def atomic_write(path, content):
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=dest.parent, prefix='.'+dest.name+'.',
                                         suffix='.tmp', encoding='utf-8', delete=False) as f:
            name = f.name
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, dest)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--crossfit', default='crossfit_insights.json')
    p.add_argument('--trends', default='training_trends_v31.json')
    p.add_argument('--recovery', default='recovery_assessment.json')
    p.add_argument('--quality', default='data_quality.json')
    p.add_argument('--ready', default='report_ready.json')
    p.add_argument('--out', default='crossfit_report_v36.json')
    p.add_argument('--markdown', default='crossfit_report_v36.md')
    p.add_argument('--chart', default='crossfit_chart_v36.svg')
    p.add_argument('--validate', default=None, help='Validate a previously written V3.6 JSON, no files changed')
    a = p.parse_args(argv)
    if a.validate:
        validate(read_object(a.validate, required=True))
        print('V3.6 validación OK')
        return 0
    report = make_report(read_object(a.crossfit, required=True),
                         read_object(a.trends, required=True),
                         read_object(a.recovery), read_object(a.quality), read_object(a.ready))
    # Build both in memory before touching any output file.
    raw = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n'
    md = markdown(report) + '\n\n![Gráficas de HRV y RPE](crossfit_chart_v36.svg)\n'
    chart = svg_chart(report)
    atomic_write(a.out, raw)
    atomic_write(a.markdown, md)
    atomic_write(a.chart, chart)
    print(json.dumps({'version': VERSION, 'status': 'ok', 'as_of': report['as_of_date'],
                      'sessions_7d': report['training']['last_7d']['registered_sessions'],
                      'report_certificate': report['source_provenance']['certificate_state']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
