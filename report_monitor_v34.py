#!/usr/bin/env python3
"""V3.4 - Auditar la vida de un informe sin afirmar entrega en ChatGPT.

Complemento SOLO de lectura de los JSON de Garmin. Integra un apartado
report_status_v34 en workflow_health.json; nunca modifica certificados,
report_cycles.json ni reportes históricos. No envía notificaciones.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
STAGES = ('sync', 'heart', 'advanced', 'crossfit')
COMPLETED_STATES = ('ready', 'already_certified_cycle', 'completed_outside_report_slots')


def _datetime(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    return result if result.tzinfo is not None else None


def _id(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        result = int(value)
        return result if result > 0 else None
    return None


def _dict(value):
    return value if isinstance(value, dict) else {}


def _read(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _valid_time(value, now):
    dt = _datetime(value)
    return dt is not None and dt <= now + timedelta(minutes=2)


def _pipeline_evidence(health, lineage, now):
    progress = _dict(health.get('pipeline_progress'))
    stage_rows = _dict(progress.get('stages'))
    sync = _dict(stage_rows.get('sync'))
    root = _id(progress.get('sync_run_id'))
    sync_id = _id(sync.get('run_id'))
    started = bool(root and root == sync_id and _valid_time(sync.get('created_at'), now))
    all_success = started and progress.get('state') in COMPLETED_STATES
    ids = {}
    for stage in STAGES:
        item = _dict(stage_rows.get(stage))
        sid = _id(item.get('run_id'))
        ids[stage] = sid
        if not (sid and item.get('status') == 'completed'
                and item.get('conclusion') == 'success'
                and _valid_time(item.get('created_at'), now)
                and _valid_time(item.get('updated_at'), now)):
            all_success = False
    lineage = _dict(lineage)
    exact = bool(all_success and lineage.get('complete_chain_verified') is True
                 and _id(_dict(lineage.get('root')).get('run_id')) == root
                 and _id(lineage.get('run_id')) == ids.get('crossfit'))
    chain = _dict(lineage.get('stages'))
    if exact:
        exact = all(_id(_dict(chain.get(s)).get('run_id')) == ids[s] for s in STAGES)
    if not started:
        state = 'sync_not_observed'
    elif progress.get('state') == 'failed':
        state = 'failed'
    elif progress.get('state') in ('in_progress', 'awaiting_certificate'):
        state = 'in_progress'
    elif all_success:
        state = 'completed_exact_chain' if exact else 'completed_lineage_unverified'
    else:
        state = 'unverified_or_incomplete'
    return {
        'state': state,
        'sync_run_id': root,
        'start_observed': started,
        'four_stages_completed': bool(all_success),
        'exact_lineage_verified': exact,
        'evidence': 'github_run_ids_and_verified_lineage' if exact else 'monitor_runs_only_or_unavailable',
        'run_ids': ids,
    }


def _origin(health, lineage, pipeline):
    progress = _dict(health.get('pipeline_progress'))
    stage = _dict(_dict(progress.get('stages')).get('sync'))
    event = stage.get('event')
    last_sync = _dict(_dict(health.get('workflows')).get('sync.yml'))
    last_url = last_sync.get('latest_run_url')
    if (not event and isinstance(last_url, str)
            and last_url.rstrip('/').split('/')[-1] == str(pipeline.get('sync_run_id'))):
        event = last_sync.get('latest_run_event')
    # El monitor principal no siempre conserva event en pipeline_progress;
    # root.event solo es fiable si corresponde al sync actual.
    root = _dict(_dict(lineage).get('root'))
    if _id(root.get('run_id')) == pipeline.get('sync_run_id'):
        event = event or root.get('event')
        proof = _dict(root.get('origin_v291'))
        if (pipeline.get('exact_lineage_verified') is True
                and proof.get('source_verified') is True
                and proof.get('origin_source') == 'apps_script_backup'
                and proof.get('auth_method') == 'hmac_sha256_shared_secret_v291'
                and proof.get('github_event') == event
                and event in ('repository_dispatch', 'workflow_dispatch')):
            return {'state': 'apps_script_signed_verified', 'github_event': event,
                    'verified_sender': True, 'proof_cycle_id': proof.get('cycle_id')}
    if event == 'schedule':
        return {'state': 'github_schedule_observed', 'github_event': event,
                'verified_sender': True}
    return {'state': 'caller_unverified' if event in ('workflow_dispatch', 'repository_dispatch')
            else 'origin_unknown', 'github_event': event, 'verified_sender': False}


def _ledger_evidence(ledger, cert, pipeline, now):
    entries = _dict(ledger).get('cycles')
    rows = [x for x in entries if isinstance(x, dict)] if isinstance(entries, list) else []
    cert = _dict(cert)
    cert_id = cert.get('cycle_id')
    ready_time = _datetime(cert.get('verified_at'))
    last_cert = {
        'cycle_id': cert_id if isinstance(cert_id, str) else None,
        'status': 'data_ready' if cert.get('status') == 'ready' and ready_time and ready_time <= now + timedelta(minutes=2)
        else 'not_verified',
        'last_ready_at': cert.get('verified_at') if ready_time else None,
        'notification_delivery': 'unverified_no_chatgpt_receipt',
    }
    cert_chain = _dict(cert.get('chain'))
    same_root = (_id(_dict(cert_chain.get('sync')).get('id')) == pipeline.get('sync_run_id')
                 and _id(_dict(cert_chain.get('crossfit')).get('id'))
                 == pipeline.get('run_ids', {}).get('crossfit'))
    ledger_match = any(x.get('cycle_id') == cert_id
                       and _id(x.get('sync_run_id')) == pipeline.get('sync_run_id')
                       and _id(x.get('crossfit_run_id')) == pipeline.get('run_ids', {}).get('crossfit')
                       and x.get('state') == 'data_ready' and _valid_time(x.get('ready_at'), now)
                       for x in rows)
    current = bool(pipeline.get('exact_lineage_verified')
                   and last_cert['status'] == 'data_ready' and same_root and ledger_match)
    last_cert['corresponds_to_observed_pipeline'] = current
    last_cert['relationship'] = 'same_verified_cycle' if current else (
        'previous_or_unmatched_certificate' if last_cert['status'] == 'data_ready'
        else 'no_verified_certificate')
    return last_cert, rows


def _performance_evidence(trends, crossfit, health, pipeline, now):
    trends, crossfit = _dict(trends), _dict(crossfit)
    report = _dict(trends.get('performance_report_v32'))
    meta = _dict(report.get('provenance'))
    trend_time = _datetime(trends.get('generated_at'))
    crossfit_time = _datetime(crossfit.get('generated_at'))
    p = _dict(health.get('pipeline_progress'))
    crossfit_run = _dict(_dict(p.get('stages')).get('crossfit'))
    start = _datetime(crossfit_run.get('created_at'))
    finish = _datetime(crossfit_run.get('updated_at'))
    chart = _dict(report.get('charts')).get('daily_28d')
    candidate_shape = (report.get('version') == '3.2' and report.get('schema_version') == 1
                       and isinstance(chart, list) and len(chart) == 28)
    matched_source = bool(candidate_shape and trends.get('source_generated_at')
                          == crossfit.get('generated_at')
                          and meta.get('crossfit_generated_at') == crossfit.get('generated_at'))
    matched_run = bool(matched_source and pipeline.get('exact_lineage_verified')
                       and trend_time and crossfit_time and start and finish
                       and start - timedelta(minutes=2) <= crossfit_time <= finish + timedelta(minutes=5)
                       and crossfit_time <= trend_time <= finish + timedelta(minutes=5)
                       and trend_time <= now + timedelta(minutes=2)
                       and report.get('as_of_date') == trends.get('as_of_date'))
    if matched_run:
        state = 'published_for_observed_pipeline'
    elif not report:
        state = 'not_published_or_legacy'
    else:
        state = 'present_but_not_attributable_to_observed_pipeline'
    return {
        'state': state,
        'verified_current_pipeline': matched_run,
        'report_version': report.get('version') if isinstance(report.get('version'), str) else None,
        'generated_at': trends.get('generated_at') if trend_time else None,
        'crossfit_source_match': matched_source,
        'note': 'GitHub JSON publication, not ChatGPT message delivery.',
    }


def _post_sleep(ledger, rows, now):
    if not isinstance(_dict(ledger).get('cycles'), list):
        return {'state': 'ledger_unavailable', 'supplement_ids': [],
                'duplicate_certificate_ids': [], 'orphan_certificate_ids': []}
    current = now.astimezone(TZ).date().isoformat()
    known = {r.get('cycle_id') for r in rows if isinstance(r.get('cycle_id'), str)}
    supplements = [r for r in rows if isinstance(r.get('cycle_id'), str)
                   and r['cycle_id'].startswith(current + '-')
                   and r['cycle_id'].endswith('-post-sleep')]
    counts = {}
    orphan = []
    malformed = []
    for item in supplements:
        cid = item['cycle_id']
        counts[cid] = counts.get(cid, 0) + 1
        parent = cid.removesuffix('-post-sleep')
        if item.get('parent_cycle_id') != parent or parent not in known:
            orphan.append(cid)
        if (item.get('state') != 'data_ready' or
                not _valid_time(item.get('ready_at'), now)):
            malformed.append(cid)
    duplicates = sorted(k for k, v in counts.items() if v > 1)
    state = ('invalid_certificate_relationship' if orphan or malformed else
             'duplicate_certificates_detected' if duplicates else
             'supplement_data_ready_once' if supplements else 'no_post_sleep_supplement')
    return {
        'state': state, 'supplement_ids': sorted(counts),
        'duplicate_certificate_ids': duplicates,
        'orphan_certificate_ids': sorted(set(orphan)),
        'invalid_certificate_ids': sorted(set(malformed)),
        'not_a_second_scheduled_report': True,
        'delivery_to_chatgpt_confirmed': False,
        'note': 'Ledger evita duplicar certificados; sin recibo de ChatGPT no demuestra ausencia de mensajes duplicados.',
    }


def analyze(health, ledger=None, certificate=None, lineage=None, trends=None, crossfit=None, now=None):
    """Retorna monitor ampliado sin mutar las fuentes ni certificar entregas."""
    if not isinstance(health, dict):
        raise ValueError('workflow_health.json must be an object')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Monitor timestamp requires timezone')
    result = copy.deepcopy(health)
    p = _pipeline_evidence(result, lineage, now)
    last, rows = _ledger_evidence(ledger, certificate, p, now)
    performance = _performance_evidence(trends, crossfit, result, p, now)
    supplements = _post_sleep(ledger, rows, now)
    slots = _dict(result.get('schedule_v231'))
    details = {
        'version': '3.4', 'checked_at': now.astimezone(TZ).isoformat(),
        'scheduled_slots': {'state': slots.get('state', 'unverified'),
                            'due_matured_count': slots.get('due'),
                            'github_cron_matched_count': slots.get('matched'),
                            'recovered_without_sender_proof': slots.get('recovered_by_unattributed', []),
                            'note': 'No inferir origen desde workflow_dispatch ni repository_dispatch.'},
        'observed_pipeline': p,
        'launch_origin': _origin(result, lineage, p),
        'last_readiness_certificate': last,
        'performance_report': performance,
        'post_sleep': supplements,
        'chatgpt_delivery': {'state': 'unverified_no_receipt',
                            'confirmed_message': False, 'confirmed_push': False,
                            'note': 'GitHub carece de callback/acuse de entrega de ChatGPT.'},
    }
    result['report_status_v34'] = details
    if supplements['state'] in ('duplicate_certificates_detected', 'invalid_certificate_relationship'):
        alerts = result.setdefault('alerts', [])
        if not isinstance(alerts, list):
            alerts = result['alerts'] = []
        if not any(isinstance(a, dict) and a.get('code') == 'post_sleep_certificate_integrity_v34'
                   for a in alerts):
            alerts.append({'severity': 'warning', 'code': 'post_sleep_certificate_integrity_v34',
                           'state': supplements['state']})
        if result.get('status') not in ('error',):
            result['status'] = 'attention'
    suffix = 'V3.4: data-ready, performance JSON and ChatGPT delivery are independent states.'
    if suffix not in str(result.get('note') or ''):
        result['note'] = (str(result.get('note') or '') + ' ' + suffix).strip()
    return result


def _atomic_write(path, data):
    dest = Path(path)
    content = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=dest.parent,
                                         prefix='.' + dest.name + '.', suffix='.tmp',
                                         delete=False) as f:
            temp_name = f.name
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_name, dest)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--health', default='workflow_health.json')
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--certificate', default='report_ready.json')
    parser.add_argument('--lineage', default='pipeline_lineage_v29.json')
    parser.add_argument('--trends', default='training_trends_v31.json')
    parser.add_argument('--crossfit', default='crossfit_insights.json')
    args = parser.parse_args(argv)
    health = _read(args.health)
    if health is None:
        raise SystemExit('workflow_health.json missing/invalid: refusing to overwrite it')
    output = analyze(health, ledger=_read(args.ledger), certificate=_read(args.certificate),
                     lineage=_read(args.lineage), trends=_read(args.trends),
                     crossfit=_read(args.crossfit))
    _atomic_write(args.health, output)
    s = output['report_status_v34']
    print(json.dumps({'monitor': 'V3.4', 'pipeline': s['observed_pipeline']['state'],
                      'performance': s['performance_report']['state'],
                      'certificate': s['last_readiness_certificate']['relationship'],
                      'post_sleep': s['post_sleep']['state'],
                      'chatgpt_delivery': s['chatgpt_delivery']['state']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
