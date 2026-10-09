#!/usr/bin/env python3
"""V2.3.1: audita tres franjas de GitHub Sync; los disparos manuales no las sustituyen.

Cambio de 4 a 3 franjas, efectivo a partir del 10-10-2026.
La transición evita falsas alertas históricas del horario anterior.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
SLOTS = ((8, 30), (16, 45), (22, 45))
SCHEDULE_START = '2026-10-10'  # Día a partir del que se evalúa la nueva configuración.


def _utc_local(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ)
    except (ValueError, TypeError, AttributeError):
        return None


def audit_slots(now, runs, lookback_hours=28, grace_minutes=120):
    """Comprueba cada franja vencida; NO considera un workflow_dispatch como schedule."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    if not isinstance(runs, list):
        return {'state': 'unverified', 'reason': 'no_workflow_run_data', 'due': 0,
                'matched': 0, 'missed': []}
    eligible = []
    for offset in range(3):
        day = now.date() - timedelta(days=offset)
        if day.isoformat() < SCHEDULE_START:
            continue
        for hour, minute in SLOTS:
            slot = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)
            if now - timedelta(hours=lookback_hours) <= slot and slot + timedelta(minutes=grace_minutes) <= now:
                eligible.append(slot)
    scheduled = []
    for run in runs:
        if run.get('event') != 'schedule' or run.get('status') != 'completed' or run.get('conclusion') != 'success':
            continue
        created = _utc_local(run.get('created_at'))
        if created:
            scheduled.append(created)
    matched, missed = [], []
    for slot in sorted(eligible):
        successful = any(slot - timedelta(minutes=5) <= run <= slot + timedelta(minutes=grace_minutes)
                         for run in scheduled)
        (matched if successful else missed).append(slot.isoformat())
    return {'state': 'attention' if missed else 'ok' if eligible else 'awaiting_next_due_slot',
            'due': len(eligible), 'matched': len(matched), 'missed': missed,
            'manual_runs_counted_as_schedule': False,
            'grace_minutes': grace_minutes, 'timezone': 'Europe/Madrid',
            'schedule_version': 'three_syncs_v1', 'sync_slots': ['08:30', '16:45', '22:45'],
            'report_targets': ['08:45', '17:00', '23:00'], 'effective_date': SCHEDULE_START}


def enhance_monitor(base, now, repo, token, fetcher):
    if not isinstance(base, dict):
        return base
    try:
        result = audit_slots(now, fetcher(repo, token, 'sync.yml')) if repo and token else {
            'state': 'unverified', 'reason': 'missing_credentials'}
    except Exception as exc:
        result = {'state': 'unverified', 'reason': type(exc).__name__}
    base['schedule_v231'] = result
    if result.get('state') == 'attention':
        base.setdefault('alerts', []).append({'severity': 'warning',
            'code': 'scheduled_sync_slots_missed', 'missed_count': len(result['missed']),
            'window_hours': 28})
        if base.get('status') != 'error':
            base['status'] = 'attention'
    elif result.get('state') == 'unverified':
        base.setdefault('alerts', []).append({'severity': 'warning', 'code': 'schedule_audit_unverified'})
        if base.get('status') != 'error':
            base['status'] = 'attention'
    base['note'] = ('Actual run outcomes and per-slot schedule audit; '
                    'manual runs never satisfy scheduled slots. Apps Script backup is independent.')
    return base


def self_test():
    from datetime import timezone
    now = datetime(2026, 10, 11, 13, 19, tzinfo=TZ)
    morning = datetime(2026, 10, 11, 8, 35, tzinfo=TZ).astimezone(timezone.utc).isoformat()
    manual = {'event': 'workflow_dispatch', 'status': 'completed',
              'conclusion': 'success', 'created_at': morning}
    scheduled = dict(manual, event='schedule')
    empty = audit_slots(datetime(2026, 10, 9, 23, 59, tzinfo=TZ), [])
    assert empty['state'] == 'awaiting_next_due_slot', empty
    a = audit_slots(now, [manual], lookback_hours=12)
    assert a['due'] == 1 and a['matched'] == 0 and a['state'] == 'attention', a
    b = audit_slots(now, [scheduled], lookback_hours=12)
    assert b['due'] == 1 and b['matched'] == 1 and b['state'] == 'ok', b
    c = audit_slots(datetime(2026, 10, 11, 10, tzinfo=TZ), [], lookback_hours=28)
    assert c['due'] == 3 and c['matched'] == 0, c
    assert SLOTS == ((8, 30), (16, 45), (22, 45))
    print('OK: cinco pruebas de horarios/monitor V2.3.1')


if __name__ == '__main__':
    self_test()
