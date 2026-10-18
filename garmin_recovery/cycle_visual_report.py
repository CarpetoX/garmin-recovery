#!/usr/bin/env python3
"""V3.8.2: immutable-snapshot-only historical Markdown report with text charts.

No network, Garmin live files, commits, or delivery assertions. Rejects altered snapshots.
"""
import argparse
import json
from pathlib import Path
from .cycle_snapshot_report import build, SnapshotError


def mapping(v):
    return v if isinstance(v, dict) else {}


def fmt(v, unit=''):
    return f'{v:g}{unit}' if type(v) in (int, float) else 'No disponible'


def bars(points, key, width=22):
    vals = [p.get(key) if type(p.get(key)) in (int, float) and p[key] >= 0 else None for p in points]
    ceiling = max((v for v in vals if v is not None), default=0)
    output = []
    for p, v in zip(points, vals, strict=False):
        n = round(width * v / ceiling) if ceiling and v is not None else 0
        output.append(f"{p['date']} | {'█' * n}{'░' * (width-n)} | {fmt(v)}")
    return output


def make(ledger, cycle_id):
    cert = build(ledger, cycle_id)
    data = cert['data']
    recovery = mapping(data.get('recovery_assessment'))
    current = mapping(recovery.get('current'))
    base = mapping(recovery.get('baseline_28d'))
    daily = mapping(data.get('daily'))
    crossfit = mapping(data.get('crossfit'))
    performance = mapping(crossfit.get('performance_report'))
    week = mapping(mapping(performance.get('window_summaries')).get('recent_7d'))
    chart = performance.get('daily_chart_7d')
    if not isinstance(chart, list) or len(chart) != 7 or any(not isinstance(p, dict) or not isinstance(p.get('date'), str) or '\n' in p['date'] for p in chart):
        raise SnapshotError('Seven-day CrossFit chart unavailable or malformed')
    heart = mapping(mapping(data.get('garmin')).get('heart_rate_rolling'))
    lines = [
        '# Garmin Recovery — Informe histórico V3.8.2', '',
        f"**Ciclo:** `{cycle_id}` · **Corte:** `{cert['slot_at']}`",
        f"**SHA-256 verificado:** `{cert['snapshot_sha256']}`",
        '**Fuente:** exclusivamente snapshot certificado del libro histórico.', '',
        '## Recuperación', '',
        f"- Estado: **{recovery.get('status', 'No disponible')}** · Confianza: {recovery.get('confidence', 'No disponible')}.",
        f"- Puntuación de recuperación (modelo local): {fmt(recovery.get('score'), '/100')}.",
        f"- Readiness híbrida: {fmt(mapping(daily.get('readiness_hybrid')).get('score'), '/100')} (modelo orientativo).", '',
        '| Métrica | Ciclo | Mediana 28 días | Observaciones |', '|---|---:|---:|---|',
    ]
    for label, key, unit in [('HRV nocturna','hrv_ms',' ms'), ('Sueño','sleep_hours',' h'), ('Puntuación sueño','sleep_score','/100'), ('FC reposo','resting_hr',' lpm'), ('FC nocturna','night_hr',' lpm')]:
        ref = mapping(base.get(key))
        lines.append(f"| {label} | {fmt(current.get(key), unit)} | {fmt(ref.get('median'), unit)} | n={fmt(ref.get('n'))} |")
    lines += ['', '## CrossFit — últimos 7 días', '',
              f"- Sesiones: {fmt(week.get('sessions'))}; con RPE: {fmt(week.get('sessions_with_rpe'))}.",
              f"- RPE medio registrado: {fmt(week.get('mean_recorded_rpe'))}; sesiones de RPE alto: {fmt(week.get('high_rpe_sessions'))}.",
              f"- sRPE calculado con duración grabada: {fmt(week.get('srpe_from_recorded_duration'))}; minutos grabados: {fmt(week.get('recorded_duration_minutes'))}.",
              f"- Volumen externo mínimo cuantificado: {fmt(week.get('minimum_recorded_external_volume_kg'), ' kg')}; bloques de fuerza sin peso cuantificado: {fmt(week.get('strength_blocks_missing_quantified_weight'))}.", '',
              '### Gráfica textual — carga sRPE diaria', '', '```text', *bars(chart, 'srpe_from_recorded_duration'), '```', '',
              '### Evolución diaria', '', '| Fecha | Sesiones | RPE medio | sRPE |', '|---|---:|---:|---:|']
    for p in chart:
        lines.append(f"| {p['date']} | {fmt(p.get('sessions'))} | {fmt(p.get('mean_recorded_rpe'))} | {fmt(p.get('srpe_from_recorded_duration'))} |")
    lines += ['', '## Frecuencia cardíaca — medias por ventana', '',
              '| Ventana | Diurna | Nocturna | Días diurnos válidos | Días nocturnos válidos |', '|---|---:|---:|---:|---:|']
    for label, key in [('3 días','3d'),('7 días','7d'),('28 días','28d')]:
        row = mapping(heart.get(key))
        lines.append(f"| {label} | {fmt(row.get('daytime_avg_hr'),' lpm')} | {fmt(row.get('nighttime_avg_hr'),' lpm')} | {fmt(row.get('daytime_days_present'))} | {fmt(row.get('nighttime_days_present'))} |")
    lines += ['', '## Recomendaciones presentes en el snapshot', '']
    for rec in performance.get('recommendations', []) if isinstance(performance.get('recommendations'), list) else []:
        message = mapping(rec).get('text')
        if isinstance(message, str) and message.strip():
            lines.append('- ' + message.replace('\n',' ').replace('\r',' ').strip())
    lines += ['', '## Limitaciones y trazabilidad', '',
              '- No hay serie diaria completa de HRV ni sueño dentro de este snapshot: no se representan curvas inventadas.',
              '- Las medias de 28 días tienen cobertura variable y referencias provisionales.',
              '- La duración registrada no es la duración efectiva del WOD; sRPE y TRIMP no se suman.',
              '- Un día sin actividades registradas no demuestra descanso.',
              '- El volumen de fuerza es un mínimo y no se deducen pesos, 1RM ni RPE ausentes.',
              '- El informe no prueba entrega a ChatGPT ni equivalencia con un informe V3.6 independiente.', '']
    return '\n'.join(lines)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--ledger',type=Path,default=Path('report_cycles.json'))
    p.add_argument('--cycle-id',required=True)
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    try:
        result=make(json.loads(args.ledger.read_text(encoding='utf-8')),args.cycle_id)
    except (OSError,ValueError,TypeError) as exc:
        p.exit(2,f'Not reportable: {exc}\n')
    if args.out:
        args.out.write_text(result,encoding='utf-8')
    else:
        print(result)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
