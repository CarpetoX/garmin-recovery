"""Evidence-based, bounded-window reliability KPIs for Garmin Recovery.

No inferred Apps Script sender, no claims of notification delivery. Never mistake
manual recovery of a missed cron for a successful scheduled launch.
"""
from datetime import datetime

STAGES = ('sync', 'heart', 'advanced', 'crossfit')

def _parse(value):
    if not value or not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt if dt.tzinfo is not None else None
    except ValueError:
        return None

def report(now, slot_audit, pipeline, runs):
    """Describe only runs actually inspected; never extrapolate a monthly SLO."""
    slots = slot_audit if isinstance(slot_audit, dict) else {}
    pipeline = pipeline if isinstance(pipeline, dict) else {}
    runs = runs if isinstance(runs, dict) else {}
    due = slots.get('due')
    matched = slots.get('matched')
    recovered = slots.get('recovered_count')
    valid = all(type(x) is int and x >= 0 for x in (due, matched, recovered)) and matched + recovered <= due
    strict_pct = round(100 * matched / due, 1) if valid and due else None
    automated_pct = round(100 * (matched + recovered) / due, 1) if valid and due else None
    unverified_backup = len(slots.get('recovered_by_repository_dispatch_unverified') or [])
    unknown_dispatch = len(slots.get('recovered_by_unattributed') or [])
    if not valid:
        classification = 'unknown'
    elif not due:
        classification = 'awaiting_due_slots'
    elif matched == due:
        classification = 'cron_observed_all'
    elif matched + recovered == due:
        classification = 'recovered_without_automatic_cron_proof'
    else:
        classification = 'missed_uncovered'
    root = max((x for x in runs.get('sync', []) if isinstance(x, dict)),
               key=lambda x: x.get('created_at') or '', default={})
    event = root.get('event')
    origin = ('github_schedule' if event == 'schedule' else
              'repository_dispatch_sender_unverified' if event == 'repository_dispatch' else
              'workflow_dispatch_caller_unverified' if event == 'workflow_dispatch' else
              'unknown')
    steps = pipeline.get('stages') or {}
    duration = None
    if pipeline.get('state') in ('ready', 'completed_outside_report_slots', 'already_certified_cycle'):
        start = _parse((steps.get('sync') or {}).get('created_at'))
        end = _parse((steps.get('crossfit') or {}).get('updated_at'))
        if start and end and 0 <= (end-start).total_seconds() <= 86400:
            duration = round((end-start).total_seconds()/60, 2)
    blockers = []
    if classification == 'missed_uncovered':
        blockers.append('sync_slot_uncovered')
    if classification == 'recovered_without_automatic_cron_proof':
        blockers.append('github_schedule_not_verified')
    if unverified_backup or unknown_dispatch:
        blockers.append('backup_sender_not_verified')
    if pipeline.get('state') in ('attention', 'failed'):
        blockers.append('pipeline_incomplete_or_failed')
    return {
        'version': '2.8', 'checked_at': now.isoformat(),
        'observation_scope': 'monitor_bounded_lookback; not 7d_or_28d_slo',
        'schedule_state': classification,
        'due_observed': due if valid else None,
        'cron_confirmed': matched if valid else None,
        'recovered_unattributed': recovered if valid else None,
        'cron_confirmed_pct': strict_pct,
        'sync_started_or_recovered_pct': automated_pct,
        'backup_sender_verified': False if (unverified_backup or unknown_dispatch) else None,
        'last_sync_event': event, 'last_sync_origin': origin,
        'latest_chain_state': pipeline.get('state', 'unverified'),
        'latest_chain_duration_minutes': duration,
        'report_delivery_receipt': 'unavailable',
        'confidence': 'observed_window_only' if valid and due else 'insufficient_evidence',
        'blockers': sorted(set(blockers)),
    }
