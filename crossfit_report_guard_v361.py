#!/usr/bin/env python3
"""CrossFit V3.6.1: validated optional publication and truthful state marker.

Runs after V3.3 and the unchanged readiness certificate. Never edits upstream
CrossFit, recovery, training history, the certificate, or shadow branch.
A validation failure leaves committed V3.6 reports untouched and writes a
failure marker; the workflow may still publish the independently valid cycle.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import argparse
import json
import os
from pathlib import Path

from crossfit_report_v36 import (
    ReportError, TZ, VERSION as REPORT_VERSION, atomic_write,
    make_report, validate, markdown, svg_chart, read_object, timestamp,
)

VERSION = '3.6.1'
MAX_SOURCE_AGE = timedelta(minutes=20)
REPORT_NAMES = ('crossfit_report_v36.json', 'crossfit_report_v36.md', 'crossfit_chart_v36.svg')
STATE_NAME = 'crossfit_report_status_v361.json'


def positive_id(value):
    if isinstance(value, bool):
        return None
    try:
        n = int(value)
        return n if n > 0 and str(value) == str(n) else None
    except (ValueError, TypeError):
        return None


def obj(value):
    return value if isinstance(value, dict) else {}


def previous_report(root: Path):
    """Old data is retained, never silently presented as newly certified."""
    p = root / REPORT_NAMES[0]
    try:
        old = json.loads(p.read_text(encoding='utf-8'))
        validate(old)
        return {'state': 'present_not_current', 'as_of_date': old.get('as_of_date'),
                'generated_at': old.get('generated_at')}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return {'state': 'absent_or_invalid', 'as_of_date': None, 'generated_at': None}


def cycle_status(root: Path, run_id: int | None, crossfit_generated_at: str):
    """A manual run can produce a valid report but not a new slot certificate."""
    if run_id is None:
        return 'not_verified_missing_run_id'
    cert = read_object(root / 'report_ready.json')
    lineage = read_object(root / 'pipeline_lineage_v29.json')
    chain = obj(cert.get('chain'))
    matches = (
        cert.get('status') == 'ready'
        and positive_id(obj(chain.get('crossfit')).get('id')) == run_id
        and obj(cert.get('source_generated_at')).get('crossfit_insights.json') == crossfit_generated_at
        and lineage.get('complete_chain_verified') is True
        and positive_id(lineage.get('run_id')) == run_id
        and positive_id(obj(lineage.get('root')).get('run_id')) == positive_id(obj(chain.get('sync')).get('id'))
    )
    return 'same_certified_cycle' if matches else 'not_linked_to_a_current_certificate'


def check_fresh_sources(crossfit, trends, now):
    source_at = timestamp(crossfit.get('generated_at'))
    trends_at = timestamp(trends.get('generated_at'))
    if not source_at or not trends_at:
        raise ReportError('No hay marcas de tiempo verificables de CrossFit y tendencias')
    for name, instant in (('CrossFit', source_at), ('tendencias', trends_at)):
        age = now - instant.astimezone(timezone.utc)
        if age < timedelta(minutes=-2) or age > MAX_SOURCE_AGE:
            raise ReportError(f'Fuente {name} fuera de la ventana de frescura de 20 minutos')
    return source_at, trends_at


def emit_status(root, payload):
    atomic_write(root / STATE_NAME,
                 json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')


def run_once(root=Path('.'), *, now=None, run_id=None, event_name=None):
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Se requiere una hora con zona horaria')
    now = now.astimezone(timezone.utc)
    run_id = positive_id(run_id)
    event_name = event_name if event_name in ('workflow_run', 'workflow_dispatch') else 'unknown'
    prior = previous_report(root)
    status = {
        'schema_version': 1, 'version': VERSION,
        'checked_at': now.astimezone(TZ).isoformat(),
        'state': 'generation_failed_previous_retained',
        'report_current': False,
        'report_version': REPORT_VERSION,
        'github_run_id': run_id,
        'github_event': event_name,
        'cycle_certificate': 'not_checked',
        'previous_report': prior,
        'failure_kind': None,
        'diagnostic': None,
        'chatgpt_delivery': 'unverified_no_receipt',
        'note': 'Un informe generado no acredita su entrega en ChatGPT.',
    }
    stage = root / '.diagnostics_current'
    stage.mkdir(parents=True, exist_ok=True)
    # Read-only input objects; old reports are never used as the source for a new one.
    try:
        crossfit = read_object(root / 'crossfit_insights.json', required=True)
        trends = read_object(root / 'training_trends_v31.json', required=True)
        source_at, trends_at = check_fresh_sources(crossfit, trends, now)
        report = make_report(crossfit, trends,
                             read_object(root / 'recovery_assessment.json'),
                             read_object(root / 'data_quality.json'),
                             read_object(root / 'report_ready.json'), now=now)
        validate(report)
        raw = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        md = markdown(report) + '\n\n![Gráficas de HRV y RPE](crossfit_chart_v36.svg)\n'
        svg = svg_chart(report)
        if not md.strip() or '<svg ' not in svg or '</svg>' not in svg:
            raise ReportError('El informe o la gráfica carecen de contenido válido')
        candidates = (raw, md, svg)
        # Prepare every candidate before touching the last published report.
        for name, content in zip(REPORT_NAMES, candidates):
            atomic_write(stage / name, content)
        validate(json.loads((stage / REPORT_NAMES[0]).read_text(encoding='utf-8')))
        for name in REPORT_NAMES[1:]:
            if not (stage / name).read_text(encoding='utf-8').strip():
                raise ReportError('Salida candidata incompleta')
        status.update(
            state='current_validated', report_current=True,
            report_generated_at=report['generated_at'],
            as_of_date=report['as_of_date'],
            source_generated_at=crossfit['generated_at'],
            trends_generated_at=trends['generated_at'],
            cycle_certificate=cycle_status(root, run_id, crossfit['generated_at']),
            previous_report=prior,
            outputs=list(REPORT_NAMES),
        )
        # No partial publication if calculations or validation failed. A rare
        # filesystem error during replacement is restored from local backups.
        original = {}
        replaced = []
        try:
            for name in REPORT_NAMES:
                path = root / name
                original[name] = path.read_bytes() if path.exists() else None
            for name in REPORT_NAMES:
                os.replace(stage / name, root / name)
                replaced.append(name)
            emit_status(root, status)
        except Exception:
            for name in reversed(replaced):
                old = original[name]
                if old is None:
                    (root / name).unlink(missing_ok=True)
                else:
                    atomic_write(root / name, old.decode('utf-8'))
            raise
        return status
    except Exception as error:
        # Errors are observable independently of the overall workflow success.
        # Do not include credentials or unbounded external exception messages.
        status['failure_kind'] = type(error).__name__
        status['diagnostic'] = (str(error)[:180] if isinstance(error, ReportError)
                                else 'Fallo de generación o publicación; revisar paso V3.6.1')
        emit_status(root, status)
        return status


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    a = p.parse_args(argv)
    state = run_once(a.root, run_id=os.getenv('GITHUB_RUN_ID'),
                     event_name=os.getenv('GITHUB_EVENT_NAME'))
    print(json.dumps({'version': VERSION, 'state': state['state'],
                      'cycle_certificate': state['cycle_certificate'],
                      'failure_kind': state['failure_kind']}, ensure_ascii=False))
    return 0 if state['report_current'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
