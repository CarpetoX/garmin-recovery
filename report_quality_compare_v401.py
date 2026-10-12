#!/usr/bin/env python3
"""V4.0.1: deterministic, read-only semantic comparison of V3.9 and V4 reports.

Compares only metrics demonstrably present in V3.9 and current-day in the
certified snapshot. Does not assume string identity or medical equivalence.
Never alters production files, historical snapshots or delivery status.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from cycle_snapshot_report_v38 import build, SnapshotError
from cycle_report_enriched_v391 import render as render_v39
from garmin_report_v40 import render as render_v40, latest_id

NUMBER = r'([-+]?\d+(?:\.\d+)?)'

# Anchored selectors avoid a metric found elsewhere accidentally passing.
FIELDS = {
    'hrv_ms': (rf'(?m)^\| HRV nocturna \| {NUMBER} ms \|', rf'(?m)^\| HRV nocturna \| {NUMBER} ms \|', 0.051),
    'sleep_hours': (rf'(?m)^\| Sueño \| {NUMBER} h \|', rf'(?m)^\| Sueño \| {NUMBER} h \|', 0.051),
    'sleep_score': (rf'(?m)^\| Puntuación sueño \| {NUMBER}(?:/100)? \|', rf'(?m)^\| Puntuación sueño \| {NUMBER} \|', 0.051),
    'resting_hr': (rf'(?m)^\| FC reposo \| {NUMBER} lpm \|', rf'(?m)^\| FC en reposo \| {NUMBER} lpm \|', 0.051),
    'night_hr': (rf'(?m)^\| FC nocturna \| {NUMBER} lpm \|', rf'(?m)^\| FC media nocturna \| {NUMBER} lpm \|', 0.051),
    'sessions': (rf'(?m)^- Sesiones: {NUMBER};', rf'(?m)^\| Sesiones registradas \| {NUMBER} \|', 0),
    'mean_rpe': (rf'(?m)^- RPE medio(?: registrado)?: {NUMBER};', rf'(?m)^\| RPE medio \| {NUMBER} \|', 0.051),
    'srpe': (rf'(?m)^- sRPE(?: calculado con duración grabada)?: {NUMBER};', rf'(?m)^\| sRPE \(duración registrada × RPE\) \| {NUMBER} UA \|', 0.051),
    'volume_kg': (rf'(?m)^- Volumen externo mínimo(?: cuantificado)?: {NUMBER} kg;', rf'(?m)^\| Volumen externo mínimo conocido \| {NUMBER} kg \|', 0.051),
}


def _obj(value):
    return value if isinstance(value, dict) else {}


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _extract(text: str, pattern: str):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def compare_texts(ledger, cycle_id, markdown_v39, markdown_v40, meta_v40, state_v39):
    """Return deterministic QA findings, never a delivery receipt.

    Both Markdown strings are assumed to have been produced from the same
    snapshot; callers must verify SHA before comparing. The snapshot is
    re-checked here so standalone callers cannot bypass that rule.
    """
    cert = build(ledger, cycle_id)
    snap = cert['data']
    rec = _obj(snap.get('recovery_assessment'))
    current = _obj(rec.get('current'))
    perf = _obj(_obj(snap.get('crossfit')).get('performance_report'))
    week = _obj(_obj(perf.get('window_summaries')).get('recent_7d'))
    sleep_gate = _obj(snap.get('morning_sleep'))
    confirmed = (sleep_gate.get('state') == 'confirmed_ready'
                 and sleep_gate.get('evidence_valid') is True
                 and current.get('date') == cycle_id[:10])
    rows = []
    errors = []
    notices = []
    mapping = {
        'hrv_ms': current.get('hrv_ms'),
        'sleep_hours': current.get('sleep_hours'),
        'sleep_score': current.get('sleep_score'),
        'resting_hr': current.get('resting_hr'),
        'night_hr': current.get('night_hr'),
        'sessions': week.get('sessions'),
        'mean_rpe': week.get('mean_recorded_rpe'),
        'srpe': week.get('srpe_from_recorded_duration'),
        'volume_kg': week.get('minimum_recorded_external_volume_kg'),
    }
    for key, (v39pattern, v40pattern, tolerance) in FIELDS.items():
        source = mapping[key]
        if key in {'hrv_ms', 'sleep_hours', 'sleep_score', 'night_hr'} and not confirmed:
            rows.append({'metric': key, 'status': 'not_comparable_sleep_pending'})
            continue
        if key == 'resting_hr' and current.get('date') != cycle_id[:10]:
            rows.append({'metric': key, 'status': 'not_comparable_stale_recovery'})
            continue
        if not _number(source):
            rows.append({'metric': key, 'status': 'not_available_in_snapshot'})
            continue
        a = _extract(markdown_v39, v39pattern)
        b = _extract(markdown_v40, v40pattern)
        if a is None:
            rows.append({'metric': key, 'status': 'v39_not_comparable', 'source_value': source})
            notices.append('v39_not_comparable_' + key)
        elif b is None:
            rows.append({'metric': key, 'status': 'regression_v40_missing', 'v39_value': a})
            errors.append('v40_missing_' + key)
        elif abs(a - b) > tolerance or abs(b - source) > tolerance:
            rows.append({'metric': key, 'status': 'regression_value', 'v39_value': a,
                         'v40_value': b, 'source_value': source})
            errors.append('v40_value_mismatch_' + key)
        else:
            rounded = abs(a - b) > 0.000001
            rows.append({'metric': key, 'status': 'compatible_rounded' if rounded else 'compatible_exact',
                         'v39_value': a, 'v40_value': b, 'source_value': source})
            if rounded:
                notices.append('rounding_' + key)

    if not confirmed:
        for key in ('hrv_ms', 'sleep_hours', 'sleep_score', 'night_hr'):
            marker = {'hrv_ms': 'HRV nocturna', 'sleep_hours': 'Sueño',
                      'sleep_score': 'Puntuación sueño', 'night_hr': 'FC media nocturna'}[key]
            if not re.search(rf'(?m)^\| {re.escape(marker)} \| Pendiente \|', markdown_v40):
                errors.append('pending_sleep_exposed_' + key)
    chart = perf.get('daily_chart_7d')
    chart_eligible = isinstance(chart, list) and len(chart) == 7 and all(
        isinstance(p, dict) and isinstance(p.get('date'), str)
        and re.fullmatch(r'\d{4}-\d{2}-\d{2}', p['date']) for p in chart)
    if chart_eligible and state_v39 == 'complete':
        missing_dates = [p['date'] for p in chart if not re.search(
            rf'(?m)^\| {re.escape(p["date"])} \|', markdown_v40)]
        if missing_dates:
            errors.append('v40_chart_dates_missing')
    elif not chart_eligible and 'No se reconstruye' not in markdown_v40:
        errors.append('missing_chart_not_disclosed')

    if meta_v40.get('snapshot_sha256') != cert['snapshot_sha256']:
        errors.append('v40_snapshot_hash_mismatch')
    if meta_v40.get('cycle_id') != cycle_id:
        errors.append('v40_cycle_mismatch')
    if meta_v40.get('sleep_confirmed') is not confirmed:
        errors.append('v40_sleep_gate_mismatch')
    if meta_v40.get('delivery') != 'unverified_no_chatgpt_receipt':
        errors.append('v40_delivery_claim_invalid')
    if 'Entrega en ChatGPT: no verificada' not in markdown_v40:
        errors.append('v40_delivery_disclaimer_missing')
    if 'SHA-256 del snapshot:' not in markdown_v40:
        errors.append('v40_provenance_missing')

    return {
        'version': '4.0.1', 'cycle_id': cycle_id,
        'snapshot_sha256': cert['snapshot_sha256'],
        'v39_completeness': state_v39,
        'v40_sleep_confirmed': confirmed,
        'status': 'pass' if not errors else 'regression_detected',
        'compared_metrics': sum(r['status'].startswith('compatible_') for r in rows),
        'metric_checks': rows, 'errors': errors, 'notices': notices,
        'delivery': 'unverified_no_chatgpt_receipt',
        'method': 'anchored_semantic_values_from_same_verified_snapshot; no_artifact_delivery_claim',
    }


def evaluate(ledger, cycle_id):
    # Both renderers revalidate snapshot integrity independently.
    v39, completeness = render_v39(ledger, cycle_id)
    v40, meta = render_v40(ledger, cycle_id)
    return compare_texts(ledger, cycle_id, v39, v40, meta, completeness)


def main(argv=None):
    p = argparse.ArgumentParser(description='V4.0.1 comparison against V3.9.2.2')
    p.add_argument('--ledger', type=Path, default=Path('report_cycles.json'))
    p.add_argument('--cycle-id')
    p.add_argument('--outdir', type=Path, default=Path('v40_preview_reports'))
    args = p.parse_args(argv)
    try:
        ledger = json.loads(args.ledger.read_text(encoding='utf-8'))
        cid = args.cycle_id or latest_id(ledger)
        result = evaluate(ledger, cid)
        args.outdir.mkdir(parents=True, exist_ok=True)
        # Same immutable behavior as V4: do not overwrite a different QA result.
        from garmin_report_v40 import _immutable_write
        name = f'{cid}-{result["snapshot_sha256"][:16]}-v401-quality.json'
        payload = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        _immutable_write(args.outdir / name, payload)
    except (OSError, ValueError, TypeError) as exc:
        p.exit(2, f'V4 quality not evaluable: {exc}\n')
    print(json.dumps({'cycle_id': cid, 'status': result['status'], 'compared_metrics': result['compared_metrics'],
                      'errors': result['errors'], 'notices': result['notices']}, ensure_ascii=False))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
