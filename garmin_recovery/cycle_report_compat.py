#!/usr/bin/env python3
"""V3.8.6: full available metrics on SHA-verified historical snapshots."""
import re
from .cycle_snapshot_report import build, SnapshotError
from .cycle_visual_report import make, mapping, fmt

SAFE_ID = re.compile(r'\A\d{4}-\d{2}-\d{2}-\d{4}(?:-post-sleep)?\Z', re.ASCII)

def render(ledger, cycle_id):
    if not isinstance(cycle_id, str) or not SAFE_ID.fullmatch(cycle_id):
        raise SnapshotError('Unsafe cycle id')
    cert = build(ledger, cycle_id)  # mandatory integrity and provenance validation
    data = cert['data']
    performance = mapping(mapping(data.get('crossfit')).get('performance_report'))
    chart = performance.get('daily_chart_7d')
    valid = (isinstance(chart, list) and len(chart) == 7 and all(
        isinstance(p, dict) and isinstance(p.get('date'), str) and
        '\n' not in p['date'] and '\r' not in p['date'] for p in chart))
    if valid:
        return make(ledger, cycle_id), 'complete'
    recovery = mapping(data.get('recovery_assessment'))
    current = mapping(recovery.get('current'))
    baseline = mapping(recovery.get('baseline_28d'))
    daily = mapping(data.get('daily'))
    week = mapping(mapping(performance.get('window_summaries')).get('recent_7d'))
    heart = mapping(mapping(data.get('garmin')).get('heart_rate_rolling'))
    lines = [
        '# Garmin Recovery — Informe histórico V3.8.6 (parcial)', '',
        f"**Ciclo:** `{cycle_id}` · **Corte:** `{cert['slot_at']}`",
        f"**SHA-256 verificado:** `{cert['snapshot_sha256']}`", '',
        '**Fuente:** únicamente snapshot histórico certificado.', '',
        '## Recuperación y sueño', '',
        f"- Estado: {recovery.get('status', 'No disponible')}; confianza: {recovery.get('confidence', 'No disponible')}.",
        f"- Recuperación: {fmt(recovery.get('score'), '/100')}.",
        f"- Readiness híbrida: {fmt(mapping(daily.get('readiness_hybrid')).get('score'), '/100')}.", '',
        '| Métrica | Ciclo | Mediana 28 días | Cobertura |', '|---|---:|---:|---|'
    ]
    for label, key, unit in [('HRV nocturna','hrv_ms',' ms'), ('Sueño','sleep_hours',' h'), ('Puntuación sueño','sleep_score','/100'), ('FC reposo','resting_hr',' lpm'), ('FC nocturna','night_hr',' lpm')]:
        ref = mapping(baseline.get(key))
        lines.append(f"| {label} | {fmt(current.get(key), unit)} | {fmt(ref.get('median'), unit)} | n={fmt(ref.get('n'))} |")
    lines += ['', '## CrossFit — últimos 7 días', '',
        f"- Sesiones: {fmt(week.get('sessions'))}; con RPE: {fmt(week.get('sessions_with_rpe'))}.",
        f"- RPE medio: {fmt(week.get('mean_recorded_rpe'))}; sesiones RPE alto: {fmt(week.get('high_rpe_sessions'))}.",
        f"- sRPE: {fmt(week.get('srpe_from_recorded_duration'))}; minutos grabados: {fmt(week.get('recorded_duration_minutes'))}.",
        f"- Volumen externo mínimo: {fmt(week.get('minimum_recorded_external_volume_kg'), ' kg')}; bloques sin peso: {fmt(week.get('strength_blocks_missing_quantified_weight'))}.", '',
        '**Gráfica diaria CrossFit: no disponible o formato incompatible. No reconstruida.**', '',
        '## Frecuencia cardíaca — medias por ventana', '',
        '| Ventana | Diurna | Nocturna | Días diurnos | Días nocturnos |', '|---|---:|---:|---:|---:|']
    for label, key in [('3 días','3d'),('7 días','7d'),('28 días','28d')]:
        row = mapping(heart.get(key))
        lines.append(f"| {label} | {fmt(row.get('daytime_avg_hr'), ' lpm')} | {fmt(row.get('nighttime_avg_hr'), ' lpm')} | {fmt(row.get('daytime_days_present'))} | {fmt(row.get('nighttime_days_present'))} |")
    lines += ['', '## Recomendaciones presentes en el snapshot', '']
    recs = performance.get('recommendations')
    for rec in recs if isinstance(recs, list) else []:
        message = mapping(rec).get('text')
        if isinstance(message, str) and message.strip():
            lines.append('- ' + message.replace('\n', ' ').replace('\r', ' ').strip())
    lines += ['', '## Limitaciones', '',
        '- Informe parcial: falta la gráfica diaria CrossFit de siete días.',
        '- No se inventan métricas ni se reconstruyen datos ausentes.',
        '- Un día sin actividad registrada no demuestra descanso.',
        '- No demuestra entrega en ChatGPT ni lectura en tiempo real.', '']
    return '\n'.join(lines), 'partial_missing_crossfit_chart'
