#!/usr/bin/env python3
"""V3.9.1: deterministic, descriptive interpretation of certified snapshot metrics.

No medical diagnosis, thresholds for training clearance, or inferred measurements.
"""
import math

METRICS = (
    ('HRV nocturna', 'hrv_ms', 'ms'),
    ('Sueño', 'sleep_hours', 'h'),
    ('Puntuación de sueño', 'sleep_score', 'puntos'),
    ('FC en reposo', 'resting_hr', 'lpm'),
    ('FC nocturna', 'night_hr', 'lpm'),
)


def obj(value):
    return value if isinstance(value, dict) else {}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def safe(value):
    return str(value).replace('|', '/').replace('\r', ' ').replace('\n', ' ')[:80]


def section(data):
    recovery = obj(data.get('recovery_assessment'))
    current = obj(recovery.get('current'))
    baseline = obj(recovery.get('baseline_28d'))
    lines = ['## Interpretación técnica — referencia personal', '',
             'Comparaciones descriptivas respecto a la mediana registrada de 28 días; no son diagnósticos ni umbrales de autorización para entrenar.', '',
             '| Indicador | Actual | Mediana 28 d | Diferencia | Cobertura | Lectura |',
             '|---|---:|---:|---:|---:|---|']
    sufficient = 0
    for label, key, unit in METRICS:
        ref = obj(baseline.get(key))
        value, median, n = current.get(key), ref.get('median'), ref.get('n')
        covered = type(n) is int and n >= 7
        if number(value) and number(median) and covered:
            delta = value - median
            interpretation = 'Por encima de la mediana' if delta > 0 else 'Por debajo de la mediana' if delta < 0 else 'Igual a la mediana'
            lines.append(f'| {label} | {value:g} {unit} | {median:g} {unit} | {delta:+.1f} {unit} | {n} días | {interpretation} |')
            sufficient += 1
        else:
            reason = 'Cobertura insuficiente (<7 días)' if type(n) is int and n < 7 else 'Datos insuficientes'
            lines.append(f'| {label} | {f"{value:g} {unit}" if number(value) else "No disponible"} | {f"{median:g} {unit}" if number(median) else "No disponible"} | No calculable | {n if type(n) is int and n >= 0 else "No disponible"} | {reason} |')
    lines += ['', f'**Comparaciones evaluables:** {sufficient}/{len(METRICS)}.', '']
    quality = obj(data.get('data_quality'))
    if quality:
        lines += ['**Calidad del registro:** existe información de calidad en el snapshot; revisar sus incidencias originales antes de interpretar variaciones.', '']
    lines += ['**Interpretación:** una desviación aislada no permite atribuir fatiga, enfermedad ni capacidad de entrenamiento. El sueño posterior a un turno nocturno puede estar pendiente o fragmentado.',
              '**Procedencia:** solo datos incluidos en el snapshot certificado; no se consultan mediciones en directo.', '']
    return '\n'.join(lines)


def enrich(report, data):
    """Append only: preserve all historical report content and classification."""
    return report.rstrip() + '\n\n' + section(data) + '\n'
