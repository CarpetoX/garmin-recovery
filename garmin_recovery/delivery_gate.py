#!/usr/bin/env python3
"""Garmin Recovery V2.3.4: certificate for a completed cross-workflow report cycle.

Designed to run DURING the final CrossFit Insights workflow before its commit.
Only publishes report_ready.json if the three upstream runs succeeded,
the fourth (current CrossFit run) reached this successful processing step,
are time-correlated in the correct order, and essential JSON files were renewed.
The certificate is NOT evidence that a ChatGPT notification was delivered.
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
SLOTS = ((8, 30, '0830', '09:05'), (16, 45, '1645', '17:10'), (22, 45, '2245', '23:10'))
WORKFLOW = {
    'sync': 'sync.yml',
    'heart': 'garmin-heart-rate.yml',
    'advanced': 'advanced-analytics-rpe.yml',
    'crossfit': 'crossfit-insights.yml',
}
REQUIRED = {
    'daily_summary.json': 'sync',
    'weekly_summary.json': 'sync',
    'garmin_status.json': 'heart',
    'garmin_heart_rate.json': 'heart',
    'recovery_assessment.json': 'advanced',
    'advanced_analytics.json': 'advanced',
    'data_quality.json': 'advanced',
    'crossfit_insights.json': 'crossfit',
}


def stamp(s):
    if not isinstance(s, str) or not s:
        return None
    try:
        x = datetime.fromisoformat(s.replace('Z', '+00:00'))
        return x.replace(tzinfo=TZ) if x.tzinfo is None else x.astimezone(TZ)
    except ValueError:
        return None


def slot_for_run(sync_started):
    if sync_started is None:
        return None
    local = sync_started.astimezone(TZ)
    for day in (local.date(), (local - timedelta(days=1)).date()):
        for hh, mm, code, target in SLOTS:
            scheduled = datetime(day.year, day.month, day.day, hh, mm, tzinfo=TZ)
            delta = (local - scheduled).total_seconds() / 60
            if -2 <= delta <= 150:
                return dict(cycle_id=f'{day.isoformat()}-{code}', slot_at=scheduled,
                            report_target=target, slot=code)
    return None


def late_post_sleep_slot(sync_started):
    """Map a late verified post-sleep sync to the prior pending morning cycle.

    This is only candidate routing; _publish_post_sleep checks all evidence.
    """
    if sync_started is None:
        return None
    local = sync_started.astimezone(TZ)
    day = local.date().isoformat()
    if not (datetime(local.year, local.month, local.day, 8, 30, tzinfo=TZ)
            <= local < datetime(local.year, local.month, local.day, 22, 45, tzinfo=TZ)):
        return None
    ledger = _read_json('report_cycles.json', {})
    cycles = ledger.get('cycles', []) if isinstance(ledger, dict) else []
    base = next((row for row in cycles if isinstance(row, dict)
                 and row.get('cycle_id') == day + '-0830'), None)
    if not base or (base.get('snapshot') or {}).get('morning_sleep', {}).get('evidence_valid') is not False:
        return None
    sleep = _read_json('morning_sleep_status.json', {})
    if sleep.get('date') != day or sleep.get('state') != 'confirmed_ready':
        return None
    end = stamp(sleep.get('sleep_end_local'))
    margin = stamp(sleep.get('earliest_definitive_at'))
    generated = stamp(sleep.get('generated_at'))
    if (not end or not margin or not generated or
            margin > local or generated < local - timedelta(minutes=5)):
        return None
    slot_time = stamp(base.get('slot_at'))
    if slot_time is None:
        return None
    return {'cycle_id': day + '-0830', 'slot_at': slot_time,
            'report_target': '09:05', 'slot': '0830'}


def successful(run, allowed_events):
    return (isinstance(run, dict) and run.get('status') == 'completed'
            and run.get('conclusion') == 'success' and run.get('event') in allowed_events
            and stamp(run.get('created_at')) and stamp(run.get('updated_at')))


def parent_before(runs, child, allowed_events, max_gap_minutes=25):
    child_start = stamp(child.get('created_at'))
    if child_start is None:
        return None
    eligible = []
    for r in runs:
        if not successful(r, allowed_events):
            continue
        end = stamp(r.get('updated_at'))
        delay = (child_start - end).total_seconds() / 60
        if -2 <= delay <= max_gap_minutes:
            eligible.append(r)
    return max(eligible, key=lambda x: stamp(x['updated_at'])) if eligible else None


def validate_chain(crossfit, advanced_runs, heart_runs, sync_runs):
    if not isinstance(crossfit, dict) or crossfit.get('event') != 'workflow_run':
        return None, ['crossfit_not_workflow_run']
    if crossfit.get('status') != 'in_progress' and not successful(crossfit, {'workflow_run'}):
        return None, ['crossfit_not_active_or_successful']
    advanced = parent_before(advanced_runs, crossfit, {'workflow_run'})
    if not advanced:
        return None, ['advanced_missing_or_not_correlated']
    heart = parent_before(heart_runs, advanced, {'workflow_run'})
    if not heart:
        return None, ['heart_missing_or_not_correlated']
    sync = parent_before(sync_runs, heart, {'schedule', 'workflow_dispatch', 'repository_dispatch'})
    if not sync:
        return None, ['sync_missing_or_not_correlated']
    slot = slot_for_run(stamp(sync['created_at']))
    if not slot:
        slot = late_post_sleep_slot(stamp(sync['created_at']))
    if not slot:
        return None, ['sync_outside_report_slot']
    return dict(slot=slot, runs={'sync': sync, 'heart': heart,
                                 'advanced': advanced, 'crossfit': crossfit}), []


def validate_files(chain, directory=Path('.')):
    generated = {}
    problems = []
    for name, stage in REQUIRED.items():
        path = directory / name
        try:
            j = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            problems.append('missing_or_invalid:' + name)
            continue
        created = stamp(j.get('generated_at')) if isinstance(j, dict) else None
        lower = stamp(chain['runs'][stage]['created_at'])
        if created is None or lower is None or created < lower - timedelta(minutes=2):
            problems.append('not_generated_in_cycle:' + name)
        else:
            generated[name] = created.isoformat()
        if name == 'garmin_status.json' and j.get('status') != 'success':
            problems.append('garmin_status_not_success')
        if name == 'recovery_assessment.json':
            if j.get('v23', {}).get('version') != '2.3.1':
                problems.append('wrong_recovery_version')
            if j.get('state') not in ('assessed', 'provisional', 'pending'):
                problems.append('invalid_recovery_state')
    return generated, problems


def github_json(url, token):
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Garmin-Report-Delivery-Gate/2.4.4',
    })
    with urllib.request.urlopen(req, timeout=25) as f:
        return json.load(f)


def get_runs(repo, token, workflow):
    url = f'https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=80'
    return github_json(url, token).get('workflow_runs', [])


def build_certificate(chain, file_times, now):
    ids = {stage: {'id': r['id'], 'event': r['event'],
                   'started_at': stamp(r['created_at']).isoformat(),
                   'finished_at': stamp(r['updated_at']).isoformat(),
                   'conclusion': r.get('conclusion') or 'publishing_in_same_job'} for stage, r in chain['runs'].items()}
    rec = json.loads(Path('recovery_assessment.json').read_text(encoding='utf-8'))
    sources = (rec.get('v23', {}).get('measurement_provenance', {}).get('sources', {}))
    measurements = {k: {'state': v.get('state'), 'measured_at': v.get('measured_at')}
                    for k, v in sources.items() if isinstance(v, dict)}
    return {
        'schema_version': 1, 'gate_version': '2.3.4', 'status': 'ready',
        'cycle_id': chain['slot']['cycle_id'],
        'slot_at': chain['slot']['slot_at'].isoformat(),
        'target_report_at': chain['slot']['report_target'],
        'timezone': 'Europe/Madrid', 'verified_at': now.isoformat(),
        'chain': ids, 'source_generated_at': file_times,
        'measurement_provenance': measurements,
        'recovery_state': rec.get('state'), 'recovery_confidence': rec.get('confidence'),
        'delivery_status': 'unconfirmed_no_chatgpt_receipt',
        'evidence': ('Three successful upstream GitHub Actions runs, current CrossFit step successful; '
                     'all key generated_at renewed; certificate committed atomically with CrossFit output'),
        'limitations': [
            'CrossFit→Advanced parent is verified with the GitHub event run ID; earlier ancestors are time-correlated',
            'CrossFit job is still running when marker is produced; its successful commit publishes both marker and output',
            'This marker certifies data readiness, not ChatGPT message delivery',
            'Only a ChatGPT delivery callback/receipt could confirm an actual notification',
            'New file generation does not imply new physiological sensor samples',
        ],
    }


def _read_json(name, default):
    try:
        return json.loads(Path(name).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return default


def _today_row(obj, day):
    if not isinstance(obj, dict):
        return {}
    days = obj.get('days')
    if isinstance(days, dict) and isinstance(days.get(day), dict):
        return days[day]
    return {}


def _last_body_battery(row):
    values = row.get('bodyBatteryValuesArray') if isinstance(row, dict) else None
    if not isinstance(values, list):
        return None
    valid = [
        x for x in values
        if isinstance(x, list)
        and len(x) >= 2
        and isinstance(x[1], (int, float))
    ]
    return valid[-1][1] if valid else None


def compact_cycle_snapshot(cert):
    """Freeze the report inputs used by this cycle."""
    day = str(cert.get('cycle_id') or '')[:10]
    daily = _read_json('daily_summary.json', {})
    recovery = _read_json('recovery_assessment.json', {})
    advanced = _read_json('advanced_analytics.json', {})
    quality = _read_json('data_quality.json', {})
    crossfit = _read_json('crossfit_insights.json', {})
    status = _read_json('garmin_status.json', {})
    heart = _read_json('garmin_heart_rate.json', {})
    stress = _today_row(_read_json('garmin_stress.json', {}), day)
    battery = _today_row(_read_json('garmin_body_battery.json', {}), day)
    extended = _today_row(_read_json('garmin_extended.json', {}), day)
    hr_day = _today_row(heart, day)

    crossfit_day = []
    for row in crossfit.get('activities', []) if isinstance(crossfit, dict) else []:
        if isinstance(row, dict) and str(row.get('date') or '') == day:
            crossfit_day.append(row)

    rec_v23 = recovery.get('v23') if isinstance(recovery.get('v23'), dict) else {}
    snapshot = {
        'snapshot_version': '2.3.4',
        'date': day,
        'source_generated_at': cert.get('source_generated_at'),
        'measurement_provenance': cert.get('measurement_provenance'),
        'recovery_assessment': {
            'generated_at': recovery.get('generated_at'),
            'state': recovery.get('state'),
            'status': recovery.get('status'),
            'score': recovery.get('score'),
            'confidence': recovery.get('confidence'),
            'reason': recovery.get('reason'),
            'current': recovery.get('current'),
            'baseline_28d': recovery.get('baseline_28d'),
            'metrics_used': recovery.get('metrics_used'),
            'warnings': recovery.get('warnings'),
            'recommendation': recovery.get('recommendation'),
            'work_shift_context': recovery.get('work_shift_context'),
            'sleep_integrity': rec_v23.get('sleep_integrity'),
            'reason_codes': rec_v23.get('reason_codes'),
            'training_guidance': rec_v23.get('training_guidance'),
        },
        'daily': {
            'generated_at': daily.get('generated_at'),
            'recovery_today': daily.get('recovery_today'),
            'training_today': daily.get('training_today'),
            'readiness_model': daily.get('readiness_model'),
            'readiness_hybrid': daily.get('readiness_hybrid'),
        },
        'advanced': {
            'generated_at': advanced.get('generated_at'),
            'readiness_hybrid': advanced.get('readiness_hybrid'),
            'personal_recovery_index': advanced.get('personal_recovery_index'),
            'convergence_alert': advanced.get('convergence_alert'),
            'weekly_load': advanced.get('weekly_load'),
            'heart_rate_recovery': advanced.get('heart_rate_recovery'),
            'recovery_data_coverage': advanced.get('recovery_data_coverage'),
            'recovery_fused_baseline_28d': advanced.get('recovery_fused_baseline_28d'),
            'rpe_feedback': advanced.get('rpe_feedback'),
        },
        'data_quality': quality,
        'crossfit': {
            'generated_at': crossfit.get('generated_at'),
            'sheet_source': crossfit.get('sheet_source'),
            'sheet_error': crossfit.get('sheet_error'),
            'sheet_rows_loaded': crossfit.get('sheet_rows_loaded'),
            'sheet_latest_date': crossfit.get('sheet_latest_date'),
            'data_quality': crossfit.get('data_quality'),
            'weekly_report': crossfit.get('weekly_report'),
            'performance_report': (crossfit.get('training_extensions') or {}).get('performance_report'),
            'activities_today': crossfit_day,
        },
        'garmin': {
            'status': {
                'generated_at': status.get('generated_at'),
                'status': status.get('status'),
                'error': status.get('error'),
                'activity_metrics_available': status.get('activity_metrics_available'),
                'activity_metrics_error': status.get('activity_metrics_error'),
            },
            'heart_rate_today': hr_day,
            'heart_rate_rolling': heart.get('rolling') if isinstance(heart, dict) else None,
            'stress_today': {
                'avgStressLevel': stress.get('avgStressLevel'),
                'maxStressLevel': stress.get('maxStressLevel'),
                'endTimestampLocal': stress.get('endTimestampLocal'),
            },
            'body_battery_today': {
                'charged': battery.get('charged'),
                'drained': battery.get('drained'),
                'latest': _last_body_battery(battery),
                'endTimestampLocal': battery.get('endTimestampLocal'),
            },
            'extended_today': {
                'training_readiness': extended.get('training_readiness'),
                'recovery_time': extended.get('recovery_time'),
                'hrv_status': extended.get('hrv_status'),
                'sleep_detail': extended.get('sleep_detail'),
                'four_week_load_balance': extended.get('four_week_load_balance'),
                'activity_metrics': extended.get('activity_metrics'),
            },
        },
    }
    encoded = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    return snapshot, hashlib.sha256(encoded).hexdigest()



def _mark_legacy_cycles(items):
    """Mark pre-schema-2 rows without inventing unavailable historical snapshots."""
    out = []
    for raw in items:
        if not isinstance(raw, dict):
            out.append(raw)
            continue
        row = dict(raw)
        if 'entry_schema_version' not in row:
            if isinstance(row.get('snapshot'), dict) and isinstance(row.get('snapshot_sha256'), str):
                row['entry_schema_version'] = 2
            else:
                row['entry_schema_version'] = 1
                row['legacy_without_snapshot'] = True
                row['snapshot_status'] = 'legacy_unavailable'
                row['legacy_note'] = (
                    'Created before report_cycles schema 2; no retrospective '
                    'snapshot was fabricated.'
                )
        out.append(row)
    return out


def _write_ledger(path, items):
    # V2.8: fail closed on corruption, retain every old cycle and write atomically.
    from .ledger_safety import atomic_write_ledger
    return atomic_write_ledger(path, items)

def append_ready_cycle(cert, path=Path('report_cycles.json'), max_entries=120):
    """Persist completed-data cycles. A readiness ledger is NOT a delivery receipt."""
    from .ledger_safety import read_ledger
    data, source_schema_version = read_ledger(path)
    items = data.get('cycles', []) if data else []

    if source_schema_version < 2:
        items = _mark_legacy_cycles(items)

    cycle_id = cert['cycle_id']
    if any(isinstance(x, dict) and x.get('cycle_id') == cycle_id for x in items):
        if source_schema_version < 2:
            _write_ledger(path, items)
        return False

    snapshot, snapshot_sha256 = compact_cycle_snapshot(cert)
    items.append({
        'entry_schema_version': 2,
        'certificate_kind': cert.get('certificate_kind', 'scheduled_cycle'),
        'parent_cycle_id': cert.get('parent_cycle_id'),
        'cycle_id': cycle_id, 'ready_at': cert['verified_at'],
        'slot_at': cert['slot_at'], 'target_report_at': cert['target_report_at'],
        'sync_run_id': cert['chain']['sync']['id'],
        'crossfit_run_id': cert['chain']['crossfit']['id'],
        'chain': cert.get('chain'),
        'source_generated_at': cert.get('source_generated_at'),
        'measurement_provenance': cert.get('measurement_provenance'),
        'recovery_state': cert.get('recovery_state'),
        'recovery_confidence': cert.get('recovery_confidence'),
        'snapshot': snapshot,
        'snapshot_sha256': snapshot_sha256,
        'state': 'data_ready',
        'notification_delivery': 'unverified',
        'notice': 'No ChatGPT delivery acknowledgment is available to GitHub Actions.'
    })
    # V2.8: max_entries kept only for API compatibility. Never drop old cycles.
    items = sorted(items, key=lambda x: x.get('slot_at', ''))
    _write_ledger(path, items)
    return True

def _publish_post_sleep(chain, generated, now, output):
    """Append one supplemental certificate; keep original 08:30 immutable.

    A data-ready certificate is not proof of a ChatGPT delivery.
    """
    sync_start = stamp(chain['runs']['sync']['created_at'])
    if sync_start is None:
        return False
    local = sync_start.astimezone(TZ)
    day = local.date().isoformat()
    original_id, supplement_id = day + '-0830', day + '-0830-post-sleep'
    ledger = _read_json('report_cycles.json', {})
    cycles = ledger.get('cycles', []) if isinstance(ledger, dict) else []
    if not isinstance(cycles, list):
        return False
    original = next((row for row in cycles if isinstance(row, dict)
                     and row.get('cycle_id') == original_id), None)
    if not original or any(isinstance(row, dict) and row.get('cycle_id') == supplement_id for row in cycles):
        return False
    initial_sleep = (original.get('snapshot') or {}).get('morning_sleep') or {}
    if initial_sleep.get('evidence_valid') is not False:
        return False
    original_sync = stamp((original.get('chain') or {}).get('sync', {}).get('started_at'))
    if not original_sync or sync_start <= original_sync:
        return False

    sleep = _read_json('morning_sleep_status.json', {})
    if (sleep.get('date') != day or sleep.get('state') != 'confirmed_ready'
            or sleep.get('is_definitive') is not True
            or sleep.get('wake_confirmed') is not True
            or sleep.get('episode_end_confirmed') is not True
            or sleep.get('recovery_matches_sleep_episode') is not True
            or sleep.get('recovery_sleep_fresh') is not True):
        return False
    end = stamp(sleep.get('sleep_end_local'))
    margin = stamp(sleep.get('earliest_definitive_at'))
    checked = stamp(sleep.get('generated_at'))
    if (not end or not margin or not checked or end.date().isoformat() != day
            or abs((margin - end).total_seconds() - 1800) > 120
            or sync_start < margin or margin > now
            or checked < sync_start - timedelta(minutes=5)
            or checked > now + timedelta(minutes=2)):
        return False

    rec = _read_json('recovery_assessment.json', {})
    recent = rec.get('current') or {}
    freshness = rec.get('input_freshness') or {}
    measured_end = stamp(recent.get('sleep_end_local'))
    if (rec.get('state') != 'assessed'
            or recent.get('date') != day or not measured_end
            or abs((measured_end - end).total_seconds()) > 300
            or not all(freshness.get(k) is True for k in ('hrv', 'sleep', 'heart_rate'))
            or not isinstance(recent.get('hrv_ms'), (int, float))
            or recent['hrv_ms'] <= 0):
        return False

    confirmed = (_read_json('garmin_sleep_history.json', {}).get('days') or {}).get(day) or {}
    confirmed_end = stamp(confirmed.get('sleep_end_local'))
    hrv = (_read_json('garmin_hrv_timeline.json', {}).get('days') or {}).get(day) or {}
    hrv_end = stamp(hrv.get('sleep_end_local'))
    if (confirmed.get('window_confirmed') is not True
            or not confirmed_end or abs((confirmed_end - end).total_seconds()) > 300
            or not hrv_end or abs((hrv_end - end).total_seconds()) > 300
            or not isinstance(hrv.get('night_avg_ms'), (int, float))
            or hrv['night_avg_ms'] <= 0):
        return False

    certificate = build_certificate(chain, generated, now)
    certified_sleep = certificate.get('morning_sleep') or {}
    if certified_sleep.get('evidence_valid') is not True:
        return False
    certificate.update(
        cycle_id=supplement_id,
        parent_cycle_id=original_id,
        certificate_kind='post_sleep_supplement',
        physiological_report_status='definitive',
        target_report_at='after_confirmed_sleep',
    )
    if not append_ready_cycle(certificate):
        return False
    # The new certificate may be the latest pointer only when no different
    # afternoon/evening certificate would be overwritten.
    prior = _read_json('report_ready.json', {})
    if prior.get('cycle_id') in (original_id, supplement_id):
        output.write_text(json.dumps(certificate, ensure_ascii=False, indent=2)
                          + '\n', encoding='utf-8')
    print('Post-sleep certificate READY:', supplement_id,
          'sync_run', chain['runs']['sync']['id'],
          'delivery remains UNVERIFIED')
    return True


def main():
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    token = os.environ.get('GH_TOKEN', '')
    crossfit_id = os.environ.get('CROSSFIT_RUN_ID', '')
    advanced_id = os.environ.get('ADVANCED_RUN_ID', '')
    if not repo or not token or not crossfit_id.isdigit() or not advanced_id.isdigit():
        raise SystemExit('Missing GH_TOKEN/repository or CrossFit/Advanced run IDs')
    base = f'https://api.github.com/repos/{repo}'
    crossfit = github_json(base + f'/actions/runs/{crossfit_id}', token)
    # GitHub supplies the EXACT triggering Advanced Analytics run id.
    advanced = github_json(base + f'/actions/runs/{advanced_id}', token)
    chain, problems = validate_chain(
        crossfit, [advanced], get_runs(repo, token, WORKFLOW['heart']),
        get_runs(repo, token, WORKFLOW['sync']))
    if problems:
        print('Report gate: NOT READY: ' + ', '.join(problems))
        return 0 if problems == ['sync_outside_report_slot'] else 1
    generated, problems = validate_files(chain)
    if problems:
        print('Report gate: NOT READY: ' + ', '.join(problems))
        return 1
    output = Path('report_ready.json')
    _publish_post_sleep(chain, generated, datetime.now(TZ), output)
    stored_cycles = _read_json('report_cycles.json', {}).get('cycles', [])
    if any(isinstance(row, dict) and row.get('cycle_id') == chain['slot']['cycle_id']
           for row in stored_cycles):
        print('Report gate: original cycle is immutable in ledger; leave current pointer unchanged.')
        return 0
    if output.is_file():
        try:
            prior = json.loads(output.read_text(encoding='utf-8'))
            if prior.get('status') == 'ready' and prior.get('cycle_id') == chain['slot']['cycle_id']:
                append_ready_cycle(prior)
                print('Report gate: certificate already published for this cycle; keep cycle_id immutable.')
                return 0
            prior_sync = stamp(prior.get('chain', {}).get('sync', {}).get('started_at'))
            this_sync = stamp(chain['runs']['sync']['created_at'])
            if prior_sync and this_sync and prior_sync >= this_sync:
                print('Report gate: already has equally new/newer verified cycle.')
                return 0
        except (ValueError, TypeError, KeyError):
            pass
    data = build_certificate(chain, generated, datetime.now(TZ))
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    append_ready_cycle(data)
    print('Report gate READY:', data['cycle_id'], 'sync_run', data['chain']['sync']['id'],
          'crossfit_run', data['chain']['crossfit']['id'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
