#!/usr/bin/env python3
"""Garmin V2.4.4 monitor: distinguish cron, Apps Script backup and manual syncs.

Retains V2.3.1 API: audit_slots and enhance_monitor, imported by monitor_monthly.py.
A manual workflow_dispatch may have been issued by Apps Script OR by a person;
no run metadata available here proves the dispatch origin.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
SLOTS = ((8, 30), (16, 45), (22, 45))
SCHEDULE_START = '2026-10-10'


def _utc_local(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ)
    except (ValueError, TypeError, AttributeError):
        return None


def due_slots(now, lookback_hours=28, grace_minutes=150):
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    slots = []
    for offset in range(3):
        date = now.date() - timedelta(days=offset)
        if date.isoformat() < SCHEDULE_START:
            continue
        for hh, mm in SLOTS:
            slot = datetime(date.year, date.month, date.day, hh, mm, tzinfo=TZ)
            if now - timedelta(hours=lookback_hours) <= slot and slot + timedelta(minutes=grace_minutes) <= now:
                slots.append(slot)
    return sorted(slots)


def audit_slots(now, runs, lookback_hours=28, grace_minutes=150):
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    if not isinstance(runs, list):
        return {'state': 'unverified', 'reason': 'no_workflow_run_data',
                'due': 0, 'matched': 0, 'recovered_count': 0,
                'missed': [], 'uncovered': [], 'recovered': []}
    slots = due_slots(now, lookback_hours, grace_minutes)
    scheduled = []
    apps_dispatched = []
    manual_dispatched = []
    for run in runs:
        if run.get('status') != 'completed' or run.get('conclusion') != 'success':
            continue
        started = _utc_local(run.get('created_at'))
        if not started:
            continue
        if run.get('event') == 'schedule':
            scheduled.append(started)
        elif run.get('event') == 'repository_dispatch':
            apps_dispatched.append(started)
        elif run.get('event') == 'workflow_dispatch':
            manual_dispatched.append(started)
    matched, recovered, uncovered = [], [], []
    recovered_apps, recovered_manual = [], []
    for slot in slots:
        lower = slot - timedelta(minutes=5)
        upper = slot + timedelta(minutes=grace_minutes)
        if any(lower <= t <= upper for t in scheduled):
            matched.append(slot.isoformat())
        elif any(lower <= t <= upper for t in apps_dispatched):
            recovered.append(slot.isoformat())
            recovered_apps.append(slot.isoformat())
        elif any(lower <= t <= upper for t in manual_dispatched):
            recovered.append(slot.isoformat())
            recovered_manual.append(slot.isoformat())
        else:
            uncovered.append(slot.isoformat())
    state = ('attention' if uncovered else 'recovered' if recovered else
             'ok' if slots else 'awaiting_next_due_slot')
    return {
        'state': state, 'due': len(slots), 'matched': len(matched),
        'recovered_count': len(recovered), 'recovered': recovered,
        'recovered_by_apps_script': recovered_apps,
        'recovered_by_manual': recovered_manual,
        'cron_missed': recovered + uncovered, 'uncovered': uncovered,
        'missed': uncovered,  # compatibility with V2.3.1 consumers
        'manual_runs_counted_as_schedule': False,
        'dispatch_origin_verified': True if recovered else None,
        'grace_minutes': grace_minutes, 'timezone': 'Europe/Madrid',
        'schedule_version': 'three_syncs_v244',
        'sync_slots': ['08:30', '16:45', '22:45'],
        'report_targets': ['08:45', '17:00', '23:00'],
        'effective_date': SCHEDULE_START,
        'note': ('repository_dispatch=Apps Script backup; '
                 'workflow_dispatch=manual; schedule=GitHub cron.'),
    }


def gate_status(now, path='report_ready.json'):
    try:
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'state': 'not_yet_published'}
    if not isinstance(obj, dict) or obj.get('status') != 'ready':
        return {'state': 'invalid'}
    ts = _utc_local(obj.get('verified_at'))
    return {'state': 'ready', 'cycle_id': obj.get('cycle_id'),
            'last_verified_at': obj.get('verified_at'),
            'age_hours': round((now - ts).total_seconds() / 3600, 2) if ts else None,
            'last_sync_run_id': obj.get('chain', {}).get('sync', {}).get('id'),
            'report_delivered': 'not_verified'}



PIPELINE_STAGES = (
    ('sync', 'sync.yml'),
    ('heart', 'garmin-heart-rate.yml'),
    ('advanced', 'advanced-analytics-rpe.yml'),
    ('crossfit', 'crossfit-insights.yml'),
)


def run_progress(now, runs_by_stage, certificate=None, stage_timeout_minutes=35):
    """Report the CURRENT pipeline instead of presenting previous success as current.

    A monitor triggered by Sync may run before Heart Rate is even queued.
    That is 'in_progress', not failure and not 'ready'.
    """
    roots = sorted(runs_by_stage.get('sync', []), key=lambda r: r.get('created_at',''), reverse=True)
    if not roots:
        return {'state': 'unverified', 'reason': 'no_sync_runs'}
    root = roots[0]
    root_at = _utc_local(root.get('created_at'))
    if not root_at:
        return {'state': 'unverified', 'reason': 'invalid_sync_timestamp'}
    age_min = round((now - root_at).total_seconds() / 60, 1)
    pieces = {'sync': {'run_id': root.get('id'), 'status': root.get('status'),
                       'conclusion': root.get('conclusion'), 'created_at': root.get('created_at'),
                       'updated_at': root.get('updated_at')}}
    if root.get('status') != 'completed':
        return {'state': 'in_progress', 'current_stage': 'sync',
                'sync_run_id': root.get('id'), 'age_minutes': age_min, 'stages': pieces}
    if root.get('conclusion') != 'success':
        return {'state': 'failed', 'current_stage': 'sync',
                'sync_run_id': root.get('id'), 'age_minutes': age_min, 'stages': pieces}
    parent = root
    for stage, _ in PIPELINE_STAGES[1:]:
        parent_end = _utc_local(parent.get('updated_at'))
        options = []
        for candidate in runs_by_stage.get(stage, []):
            if candidate.get('event') != 'workflow_run':
                continue
            started = _utc_local(candidate.get('created_at'))
            if started and parent_end and -2 <= (started - parent_end).total_seconds()/60 <= 25:
                options.append(candidate)
        if not options:
            waited = round((now - parent_end).total_seconds()/60, 1) if parent_end else None
            status = 'waiting' if waited is None or waited < stage_timeout_minutes else 'missing'
            return {'state': 'in_progress' if status == 'waiting' else 'attention',
                    'current_stage': stage, 'step': status, 'age_minutes': age_min,
                    'waiting_minutes': waited, 'sync_run_id': root.get('id'), 'stages': pieces}
        current = max(options, key=lambda x: x.get('created_at', ''))
        pieces[stage] = {'run_id': current.get('id'), 'status': current.get('status'),
                         'conclusion': current.get('conclusion'), 'created_at': current.get('created_at'),
                         'updated_at': current.get('updated_at')}
        if current.get('status') != 'completed':
            elapsed = (now - _utc_local(current.get('created_at'))).total_seconds()/60
            return {'state': 'in_progress' if elapsed < 65 else 'attention',
                    'current_stage': stage, 'step': 'running', 'age_minutes': age_min,
                    'sync_run_id': root.get('id'), 'stages': pieces}
        if current.get('conclusion') != 'success':
            return {'state': 'failed', 'current_stage': stage,
                    'sync_run_id': root.get('id'), 'age_minutes': age_min, 'stages': pieces}
        parent = current
    # The full four-workflow chain completed. Only a slot run needs a ready certificate.
    is_slot = any(-2 <= (root_at - datetime(root_at.year, root_at.month, root_at.day, h, m, tzinfo=TZ)).total_seconds()/60 <= 150
                  for h, m in SLOTS)
    if not is_slot:
        return {'state': 'completed_outside_report_slots',
                'age_minutes': age_min, 'sync_run_id': root.get('id'), 'stages': pieces}
    cert_run = (certificate or {}).get('chain', {}).get('sync', {}).get('id')
    if (certificate or {}).get('status') == 'ready' and str(cert_run) == str(root.get('id')):
        state = 'ready'
    else:
        last = _utc_local(parent.get('updated_at'))
        seconds = (now - last).total_seconds() if last else 0
        state = 'awaiting_certificate' if seconds < 15*60 else 'attention'
    return {'state': state, 'age_minutes': age_min, 'sync_run_id': root.get('id'),
            'current_stage': 'ready_certificate' if state != 'ready' else None,
            'stages': pieces}


def load_ready_certificate(path='report_ready.json'):
    try:
        obj = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def enhance_monitor(base, now, repo, token, fetcher):
    if not isinstance(base, dict):
        return base
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    runs = {}
    try:
        if not (repo and token):
            raise ValueError('missing_credentials')
        for stage, workflow in PIPELINE_STAGES:
            runs[stage] = fetcher(repo, token, workflow)
        slots = audit_slots(now, runs['sync'])
    except Exception as exc:
        slots = {'state': 'unverified', 'reason': type(exc).__name__}
    base['schedule_v231'] = slots
    base['delivery_gate'] = gate_status(now)
    if runs:
        progress = run_progress(now, runs, load_ready_certificate())
    else:
        progress = {'state': 'unverified', 'reason': 'run_history_unavailable'}
    base['pipeline_progress'] = progress
    alerts = base.setdefault('alerts', [])
    if slots.get('state') == 'recovered':
        for alert in alerts:
            if alert.get('code') == 'no_recent_successful_scheduled_run':
                alert['severity'] = 'info'
                alert['clarification'] = 'data_recovered_by_dispatch; cron_still_unreliable'
        dispatch_origin = ('apps_script_backup' if slots.get('recovered_by_apps_script')
                           else 'manual' if slots.get('recovered_by_manual')
                           else 'unknown')
        alerts.append({'severity': 'info', 'code': 'cron_missed_dispatch_recovered',
                       'slots': slots.get('recovered'),
                       'dispatch_origin': dispatch_origin,
                       'dispatch_origin_verified': slots.get('dispatch_origin_verified')})
    elif slots.get('state') == 'attention':
        alerts.append({'severity': 'warning', 'code': 'sync_slot_not_recovered',
                       'slots': slots.get('uncovered'), 'cron_missed': slots.get('cron_missed')})
    elif slots.get('state') == 'unverified':
        alerts.append({'severity': 'warning', 'code': 'schedule_audit_unverified'})
    # Flag actual failures only after pipeline-specific grace time, never during normal chaining.
    if progress.get('state') in ('failed', 'attention'):
        alerts.append({'severity': 'warning', 'code': 'latest_pipeline_not_complete',
                       'stage': progress.get('current_stage'),
                       'state': progress.get('state'),
                       'sync_run_id': progress.get('sync_run_id')})
    elif progress.get('state') in ('in_progress', 'awaiting_certificate'):
        # Previous completed failure is not the status of a newer running cycle.
        for alert in alerts:
            if alert.get('code') == 'latest_run_failed':
                alert['severity'] = 'info'
                alert['clarification'] = 'latest_sync_chain_in_progress'
    # Preserve the daily certification audit without treating today's running chain as failure.
    if now.date().isoformat() >= SCHEDULE_START:
        recent = []
        for off in (0, 1):
            day = now.date() - timedelta(days=off)
            if day.isoformat() < SCHEDULE_START:
                continue
            for h, m in SLOTS:
                when = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
                if when + timedelta(minutes=150) < now and now - when < timedelta(hours=8):
                    recent.append(when)
        latest_due = max(recent) if recent else None
        gate = base['delivery_gate']
        verified = _utc_local(gate.get('last_verified_at'))
        if latest_due and (verified is None or verified < latest_due):
            alerts.append({'severity': 'warning', 'code': 'report_gate_not_current',
                           'last_due_slot': latest_due.isoformat(),
                           'last_ready_cycle': gate.get('cycle_id')})
    base['status'] = ('error' if any(a.get('severity') == 'error' for a in alerts)
                      else 'attention' if any(a.get('severity') == 'warning' for a in alerts)
                      else 'ok')
    base['note'] = ('pipeline_progress tracks the current Sync→Heart→Advanced→CrossFit chain; '
                    'a previous successful stage is not presented as completion of a running cycle. '
                    'report_cycles.json records readiness, NOT delivery receipts.')
    return base


def self_test():
    from datetime import timezone
    now = datetime(2026, 10, 11, 13, 19, tzinfo=TZ)
    morning = datetime(2026, 10, 11, 8, 35, tzinfo=TZ).astimezone(timezone.utc).isoformat()
    manual = {'event': 'workflow_dispatch', 'status': 'completed',
              'conclusion': 'success', 'created_at': morning}
    apps = dict(manual, event='repository_dispatch')
    scheduled = dict(manual, event='schedule')
    assert audit_slots(datetime(2026, 10, 9, 23, 59, tzinfo=TZ), [])['due'] == 0
    a = audit_slots(now, [manual], lookback_hours=12)
    assert a['due'] == 1 and a['matched'] == 0 and a['recovered_count'] == 1 and a['state'] == 'recovered', a
    assert a['recovered_by_manual'] and not a['recovered_by_apps_script'], a
    app = audit_slots(now, [apps], lookback_hours=12)
    assert app['state'] == 'recovered' and app['recovered_by_apps_script'], app
    assert app['dispatch_origin_verified'] is True, app
    b = audit_slots(now, [scheduled], lookback_hours=12)
    assert b['due'] == 1 and b['matched'] == 1 and b['state'] == 'ok', b
    c = audit_slots(datetime(2026, 10, 11, 10, tzinfo=TZ), [], lookback_hours=28)
    assert c['due'] == 3 and c['uncovered'], c
    d = audit_slots(now, [dict(manual, conclusion='failure')], lookback_hours=12)
    assert d['state'] == 'attention' and len(d['uncovered']) == 1, d
    assert SLOTS == ((8, 30), (16, 45), (22, 45))
    print('OK: V2.4.4 schedule/manual/Apps Script distinction')


if __name__ == '__main__':
    self_test()
