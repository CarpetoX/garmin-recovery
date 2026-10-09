#!/usr/bin/env python3
"""Garmin V2.3.2 monitor: separate cron failures, recovered syncs and real gaps.

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


def due_slots(now, lookback_hours=28, grace_minutes=120):
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


def audit_slots(now, runs, lookback_hours=28, grace_minutes=120):
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    if not isinstance(runs, list):
        return {'state': 'unverified', 'reason': 'no_workflow_run_data',
                'due': 0, 'matched': 0, 'recovered_count': 0,
                'missed': [], 'uncovered': [], 'recovered': []}
    slots = due_slots(now, lookback_hours, grace_minutes)
    scheduled = []
    dispatched = []
    for run in runs:
        if run.get('status') != 'completed' or run.get('conclusion') != 'success':
            continue
        started = _utc_local(run.get('created_at'))
        if not started:
            continue
        if run.get('event') == 'schedule':
            scheduled.append(started)
        elif run.get('event') == 'workflow_dispatch':
            dispatched.append(started)
    matched, recovered, uncovered = [], [], []
    for slot in slots:
        lower = slot - timedelta(minutes=5)
        upper = slot + timedelta(minutes=grace_minutes)
        if any(lower <= t <= upper for t in scheduled):
            matched.append(slot.isoformat())
        elif any(lower <= t <= upper for t in dispatched):
            recovered.append(slot.isoformat())
        else:
            uncovered.append(slot.isoformat())
    state = ('attention' if uncovered else 'recovered' if recovered else
             'ok' if slots else 'awaiting_next_due_slot')
    return {
        'state': state, 'due': len(slots), 'matched': len(matched),
        'recovered_count': len(recovered), 'recovered': recovered,
        'cron_missed': recovered + uncovered, 'uncovered': uncovered,
        'missed': uncovered,  # compatibility with V2.3.1 consumers
        'manual_runs_counted_as_schedule': False,
        'dispatch_origin_verified': False,
        'grace_minutes': grace_minutes, 'timezone': 'Europe/Madrid',
        'schedule_version': 'three_syncs_v2',
        'sync_slots': ['08:30', '16:45', '22:45'],
        'report_targets': ['08:45', '17:00', '23:00'],
        'effective_date': SCHEDULE_START,
        'note': ('Recovered means a successful dispatch was found, but it is not '
                 'provably an Apps Script dispatch rather than a human dispatch.'),
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


def enhance_monitor(base, now, repo, token, fetcher):
    if not isinstance(base, dict):
        return base
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    try:
        slots = audit_slots(now, fetcher(repo, token, 'sync.yml')) if repo and token else {
            'state': 'unverified', 'reason': 'missing_credentials'}
    except Exception as exc:
        slots = {'state': 'unverified', 'reason': type(exc).__name__}
    base['schedule_v231'] = slots
    base['delivery_gate'] = gate_status(now)
    alerts = base.setdefault('alerts', [])
    # Original monitor reports missing scheduled cron success over last 72h.
    # If a dispatch recovered ALL due slots, it is cron reliability degradation
    # rather than failed collection or report-data loss.
    if slots.get('state') == 'recovered':
        for alert in alerts:
            if alert.get('code') == 'no_recent_successful_scheduled_run':
                alert['severity'] = 'info'
                alert['clarification'] = 'data_recovered_by_dispatch; cron_still_unreliable'
        alerts.append({'severity': 'info', 'code': 'cron_missed_dispatch_recovered',
                       'slots': slots.get('recovered'),
                       'dispatch_origin': 'unverified'})
    elif slots.get('state') == 'attention':
        alerts.append({'severity': 'warning', 'code': 'sync_slot_not_recovered',
                       'slots': slots.get('uncovered'),
                       'cron_missed': slots.get('cron_missed')})
    elif slots.get('state') == 'unverified':
        alerts.append({'severity': 'warning', 'code': 'schedule_audit_unverified'})
    # A gate certificate is allowed to lag the most recent Sync while stages run.
    # Warn only after the oldest plausible gate-grace interval has passed.
    if now.date().isoformat() >= SCHEDULE_START:
        recent = []
        for off in (0, 1):
            d = now.date() - timedelta(days=off)
            if d.isoformat() < SCHEDULE_START:
                continue
            for h, m in SLOTS:
                point = datetime(d.year, d.month, d.day, h, m, tzinfo=TZ)
                if point + timedelta(minutes=130) < now and now - point < timedelta(hours=8):
                    recent.append(point)
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
    base['note'] = ('Cron health and dispatch recovery are audited separately. '
                    'report_ready.json certifies publication readiness, not actual ChatGPT delivery.')
    return base


def self_test():
    from datetime import timezone
    now = datetime(2026, 10, 11, 13, 19, tzinfo=TZ)
    morning = datetime(2026, 10, 11, 8, 35, tzinfo=TZ).astimezone(timezone.utc).isoformat()
    manual = {'event': 'workflow_dispatch', 'status': 'completed',
              'conclusion': 'success', 'created_at': morning}
    scheduled = dict(manual, event='schedule')
    assert audit_slots(datetime(2026, 10, 9, 23, 59, tzinfo=TZ), [])['due'] == 0
    a = audit_slots(now, [manual], lookback_hours=12)
    assert a['due'] == 1 and a['matched'] == 0 and a['recovered_count'] == 1 and a['state'] == 'recovered', a
    b = audit_slots(now, [scheduled], lookback_hours=12)
    assert b['due'] == 1 and b['matched'] == 1 and b['state'] == 'ok', b
    c = audit_slots(datetime(2026, 10, 11, 10, tzinfo=TZ), [], lookback_hours=28)
    assert c['due'] == 3 and c['uncovered'], c
    d = audit_slots(now, [dict(manual, conclusion='failure')], lookback_hours=12)
    assert d['state'] == 'attention' and len(d['uncovered']) == 1, d
    assert SLOTS == ((8, 30), (16, 45), (22, 45))
    print('OK: 6 tests of V2.3.2 schedule distinction')


if __name__ == '__main__':
    self_test()
