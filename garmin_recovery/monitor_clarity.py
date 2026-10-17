#!/usr/bin/env python3
"""Garmin V2.9.7: additive, read-only interpretation of the latest monitor cycle.

Does not alter Sync, Garmin outputs, RPE, recovery, report cycles or shadows.
Only adds ``monitor_v297`` to an existing workflow_health.json; no delivery
confirmation is ever inferred from a GitHub data-ready certificate.
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
VERSION = '2.9.7'
TARGET_BUFFER_WARNING_MINUTES = 5.0


def obj(x):
    return x if isinstance(x, dict) else {}


def parsed(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.astimezone(TZ) if dt.tzinfo is not None else None
    except ValueError:
        return None


def target_at(slot, raw):
    """Preserve the scheduled slot's LOCAL date (including across UTC midnight)."""
    if slot is None or not isinstance(raw, str):
        return None
    try:
        h, m = map(int, raw.split(':'))
        if not 0 <= h <= 23 or not 0 <= m <= 59 or len(raw.split(':')) != 2:
            return None
        target = slot.replace(hour=h, minute=m, second=0, microsecond=0)
        if target < slot:
            target += timedelta(days=1)
        return target
    except (ValueError, TypeError):
        return None


def positive_run_id(value):
    return type(value) is int and value > 0


def current_cycle_evidence(health, cert, origin, lineage):
    cert, origin, lineage = obj(cert), obj(origin), obj(lineage)
    details = obj(obj(health.get('report_status_v34')).get('observed_pipeline'))
    previous = obj(obj(health.get('report_status_v34')).get('last_readiness_certificate'))
    pipeline = obj(health.get('pipeline_progress'))
    chain = obj(cert.get('chain'))
    root = obj(lineage.get('root'))
    stages = obj(pipeline.get('stages'))
    ids = {stage: obj(chain.get(stage)).get('id') for stage in ('sync','heart','advanced','crossfit')}
    complete = bool(
        cert.get('status') == 'ready'
        and isinstance(cert.get('cycle_id'), str)
        and all(positive_run_id(x) for x in ids.values())
        and details.get('state') == 'completed_exact_chain'
        and details.get('exact_lineage_verified') is True
        and previous.get('relationship') == 'same_verified_cycle'
        and previous.get('cycle_id') == cert.get('cycle_id')
        and lineage.get('complete_chain_verified') is True
        and root.get('run_id') == ids['sync']
        and lineage.get('run_id') == ids['crossfit']
        and all(obj(stages.get(k)).get('run_id') == ids[k]
                and obj(stages.get(k)).get('status') == 'completed'
                and obj(stages.get(k)).get('conclusion') == 'success'
                for k in ids)
    )
    if not complete:
        return {'chain_verified': False, 'origin': 'unverified', 'sender_verified': False,
                'reason': 'certificate_or_exact_lineage_not_verified'}

    proof = obj(root.get('origin_v291'))
    origin_obj = obj(origin.get('origin'))
    verified_same_cycle = origin.get('cycle_id') == cert.get('cycle_id')
    if (verified_same_cycle and origin_obj.get('verified') is True
        and origin_obj.get('source') == 'apps_script_backup'
        and origin_obj.get('cycle_id') == cert.get('cycle_id')
        and origin_obj.get('evidence') == 'sync_hmac_validated_v291'
        and proof.get('cycle_id') == cert.get('cycle_id')
        and proof.get('source_verified') is True
        and proof.get('origin_source') == 'apps_script_backup'
        and proof.get('auth_method') == 'hmac_sha256_shared_secret_v291'
        and root.get('event') in ('workflow_dispatch', 'repository_dispatch')
        and proof.get('github_event') == root.get('event')):
        return {'chain_verified': True, 'origin': 'apps_script_signed_verified',
                'sender_verified': True, 'reason': 'matching_v291_hmac_evidence'}
    if (verified_same_cycle and root.get('event') == 'schedule'
            and origin_obj.get('source') == 'github_schedule'
            and origin_obj.get('verified') is True):
        return {'chain_verified': True, 'origin': 'github_schedule_verified',
                'sender_verified': True, 'reason': 'github_schedule_event_with_matching_lineage'}
    return {'chain_verified': True, 'origin': 'dispatch_caller_unverified',
            'sender_verified': False, 'reason': 'no_matching_origin_proof'}


def analyze(health, certificate, origin_report, lineage, now=None):
    """Produce a new view, never erasing older alert evidence or changing base status."""
    if not isinstance(health, dict):
        raise ValueError('workflow_health.json must be a JSON object')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must have timezone')
    cert = obj(certificate)
    view = current_cycle_evidence(health, cert, origin_report, lineage)
    slot = parsed(cert.get('slot_at'))
    ready = parsed(cert.get('verified_at'))
    target = target_at(slot, cert.get('target_report_at'))
    sync_start = parsed(obj(obj(cert.get('chain')).get('sync')).get('started_at'))
    available = bool(view['chain_verified'] and slot and ready and target
                     and ready >= slot and ready <= now.astimezone(TZ) + timedelta(minutes=2))
    margin = round((target-ready).total_seconds()/60, 2) if available else None
    lag = round((sync_start-slot).total_seconds()/60, 2) if available and sync_start else None
    punctuality = ('not_assessable' if margin is None else
                   'late' if margin < 0 else
                   'tight_margin' if margin < TARGET_BUFFER_WARNING_MINUTES else 'on_time')

    # Preserve original historical issues and distinguish them from evidence of THIS cycle.
    alerts = health.get('alerts')
    alerts = alerts if isinstance(alerts, list) else []
    old_issues, current_issues = [], []
    slot_text = cert.get('slot_at')
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        code = alert.get('code') if isinstance(alert.get('code'), str) else 'unspecified'
        slots = alert.get('slots')
        if isinstance(slots, list) and slot_text in slots:
            current_issues.append(code)
        else:
            old_issues.append(code)

    previous_status = health.get('status')
    if not available:
        status = 'cycle_unverified'
    elif current_issues or previous_status == 'error':
        status = 'needs_attention'
    elif punctuality == 'late':
        status = 'ready_late'
    elif not view['sender_verified']:
        status = 'ready_sender_unverified'
    else:
        status = 'verified_ready'

    # Do not invent a recovered-incident count or a verified success streak.
    details = {
        'version': VERSION,
        'checked_at': now.astimezone(TZ).isoformat(),
        'cycle_id': cert.get('cycle_id') if isinstance(cert.get('cycle_id'), str) else None,
        'current_cycle': {'state': status, 'data_ready_verified': available,
                          'exact_chain_verified': view['chain_verified'],
                          'origin': view['origin'], 'origin_verified': view['sender_verified'],
                          'origin_evidence': view['reason']},
        'punctuality': {'state': punctuality, 'slot_at': cert.get('slot_at'),
                        'data_ready_at': cert.get('verified_at'),
                        'target_report_at': target.isoformat() if target else None,
                        'ready_before_target_minutes': margin,
                        'sync_start_delay_from_slot_minutes': lag,
                        'minimum_buffer_warning_minutes': TARGET_BUFFER_WARNING_MINUTES,
                        'measures_data_readiness_not_chatgpt_delivery': True},
        'historical_alerts': {'base_monitor_status': previous_status,
                              'prior_or_unattributed_alert_codes': sorted(set(old_issues)),
                              'current_slot_alert_codes': sorted(set(current_issues)),
                              'prior_alerts_not_automatically_resolved': True,
                              'verified_recovered_incidents': None,
                              'consecutive_automatic_successes': None,
                              'note': 'A later green run does not prove a prior failure was fixed.'},
        'delivery': {'state': 'unverified_no_chatgpt_receipt',
                     'message_confirmed': False, 'push_confirmed': False},
    }
    result = copy.deepcopy(health)
    result['monitor_v297'] = details
    return result


def read_json(path, required=True):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(value, dict):
            return value
    except (OSError, ValueError):
        pass
    if required:
        raise ValueError(f'Missing or invalid JSON object: {path}')
    return {}


def atomic_json(path, value):
    dest = Path(path)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dest.parent,
                                         prefix='.' + dest.name + '.', suffix='.tmp', delete=False) as f:
            tmp = f.name
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dest)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--health', default='workflow_health.json')
    p.add_argument('--certificate', default='report_ready.json')
    p.add_argument('--origin', default='origin_monitor_v292.json')
    p.add_argument('--lineage', default='pipeline_lineage_v29.json')
    args = p.parse_args(argv)
    health = read_json(args.health)
    # This is optional telemetry: bad/missing supporting evidence must NEVER
    # prevent Sync, reporting or auto-mirror dispatch. Mark it unverified.
    cert = read_json(args.certificate, required=False)
    origin = read_json(args.origin, required=False)
    lineage = read_json(args.lineage, required=False)
    updated = analyze(health, cert, origin, lineage)
    atomic_json(args.health, updated)
    view = updated['monitor_v297']
    print(json.dumps({'version': VERSION, 'cycle_id': view['cycle_id'],
                      'state': view['current_cycle']['state'],
                      'punctuality': view['punctuality']['state'],
                      'original_monitor_status_preserved': True}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
