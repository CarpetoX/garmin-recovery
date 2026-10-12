#!/usr/bin/env python3
"""V3.8.1: reproducible historical CrossFit Markdown report from certified snapshot only.

Read-only: no Garmin calls, no live JSON sources, no delivery assertions.
"""
import argparse
import json
from pathlib import Path
from cycle_snapshot_report_v38 import build, SnapshotError


def obj(value):
    return value if isinstance(value, dict) else {}


def number(value, suffix=''):
    return f'{value:g}{suffix}' if type(value) in (int, float) else 'No disponible'


def make(ledger, cycle_id):
    certified = build(ledger, cycle_id)
    data = certified['data']
    recovery = obj(data.get('recovery_assessment'))
    current = obj(recovery.get('current'))
    daily = obj(data.get('daily'))
    crossfit = obj(data.get('crossfit'))
    performance = obj(crossfit.get('performance_report'))
    windows = obj(performance.get('window_summaries'))
    week = obj(windows.get('recent_7d'))
    chart = performance.get('daily_chart_7d')
    if not isinstance(chart, list) or len(chart) != 7:
        raise SnapshotError('Historical 7-day CrossFit chart unavailable')
    for point in chart:
        if not isinstance(point, dict) or not isinstance(point.get('date'), str):
            raise SnapshotError('Malformed historical chart')
    heart = obj(obj(data.get('garmin')).get('heart_rate_rolling'))
    lines = [
        '# Garmin Recovery — Informe histórico CrossFit V3.8.1', '',
        f"**Ciclo:** `{cycle_id}` · **Hora:** {certified['slot_at']}",
        f"**SHA-256:** `{certified['snapshot_sha256']}`",
        '**Fuente:** snapshot histórico certificado, sin datos posteriores.', '',
        '## Recuperación y sueño', '',
        f"- Estado: {recovery.get('status', 'No disponible')} (confianza: {recovery.get('confidence', 'No disponible')}).",
        f"- Sueño: {number(current.get('sleep_hours'), ' h')} · Puntuación: {number(current.get('sleep_score'), '/100')}.",
        f"- HRV: {number(current.get('hrv_ms'), ' ms')} · FC reposo: {number(current.get('resting_hr'), ' lpm')} · FC nocturna: {number(current.get('night_hr'), ' lpm')}.",
        f"- Readiness híbrida: {number(obj(daily.get('readiness_hybrid')).get('score'), '/100')} (heurística; no diagnóstico).", '',
        '## Entrenamiento registrado', '',
        f"- Sesiones 7 días: {number(week.get('sessions'))} · Con RPE: {number(week.get('sessions_with_rpe'))}.",
        f"- RPE medio: {number(week.get('mean_recorded_rpe'))} · sRPE registrado: {number(week.get('srpe_from_recorded_duration'))}.",
        f"- Minutos registrados: {number(week.get('recorded_duration_minutes'))}. No equivalen a minutos efectivos de WOD.", '',
        '### Serie histórica de 7 días', '',
        '| Fecha | Sesiones | RPE medio | sRPE registrado |',
        '|---|---:|---:|---:|',
    ]
    for p in chart:
        lines.append(f"| {p['date']} | {number(p.get('sessions'))} | {number(p.get('mean_recorded_rpe'))} | {number(p.get('srpe_from_recorded_duration'))} |")
    lines += ['', '## Frecuencia cardíaca: medias registradas', '',
              '| Ventana | Diurna (lpm) | Nocturna (lpm) |', '|---|---:|---:|']
    for label, key in [('3 días', '3d'), ('7 días', '7d'), ('28 días', '28d')]:
        row = obj(heart.get(key))
        lines.append(f"| {label} | {number(row.get('daytime_avg_hr'))} | {number(row.get('nighttime_avg_hr'))} |")
    lines += ['', '## Recomendaciones registradas en el ciclo', '']
    recommendations = performance.get('recommendations')
    if isinstance(recommendations, list):
        for rec in recommendations:
            msg = obj(rec).get('text')
            if isinstance(msg, str) and msg.strip():
                lines.append('- ' + msg.strip().replace('\n', ' '))
    lines += ['', '## Límites de interpretación', '',
              '- Un día sin sesiones registradas no demuestra descanso.',
              '- No se infieren 1RM, RIR, cargas o RPE ausentes.',
              '- Las medias diurnas del día del ciclo pueden ser parciales.',
              '- No se mezclan archivos actuales ni informes V3.6 independientes.',
              '- El certificado no acredita entrega en ChatGPT.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--cycle-id', required=True)
    parser.add_argument('--out', help='Optional Markdown output')
    args = parser.parse_args()
    try:
        content = make(json.loads(Path(args.ledger).read_text(encoding='utf-8')), args.cycle_id)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f'Not reportable: {exc}\n')
    if args.out:
        Path(args.out).write_text(content, encoding='utf-8')
    else:
        print(content)


if __name__ == '__main__':
    main()
