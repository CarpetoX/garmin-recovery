#!/usr/bin/env python3
"""Garmin Recovery V2.3.3: certificate for a completed cross-workflow report cycle.

Designed to run DURING the final CrossFit Insights workflow before its commit.
Only publishes report_ready.json if the three upstream runs succeeded,
the fourth (current CrossFit run) reached this successful processing step,
are time-correlated in the correct order, and essential JSON files were renewed.
The certificate is NOT evidence that a ChatGPT notification was delivered.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
SLOTS = ((8, 30, '0830', '08:45'), (16, 45, '1645', '17:00'), (22, 45, '2245', '23:00'))
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
    sync = parent_before(sync_runs, heart, {'schedule', 'workflow_dispatch'})
    if not sync:
        return None, ['sync_missing_or_not_correlated']
    slot = slot_for_run(stamp(sync['created_at']))
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
        'User-Agent': 'Garmin-Report-Delivery-Gate/2.3.2',
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
        'schema_version': 1, 'gate_version': '2.3.3', 'status': 'ready',
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



def append_ready_cycle(cert, path=Path('report_cycles.json'), max_entries=120):
    """Persist completed-data cycles. A readiness ledger is NOT a delivery receipt."""
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        items = data.get('cycles', []) if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
    except (OSError, ValueError):
        items = []
    cycle_id = cert['cycle_id']
    if any(isinstance(x, dict) and x.get('cycle_id') == cycle_id for x in items):
        return False
    items.append({
        'cycle_id': cycle_id, 'ready_at': cert['verified_at'],
        'slot_at': cert['slot_at'], 'target_report_at': cert['target_report_at'],
        'sync_run_id': cert['chain']['sync']['id'],
        'crossfit_run_id': cert['chain']['crossfit']['id'],
        'state': 'data_ready',
        'notification_delivery': 'unverified',
        'notice': 'No ChatGPT delivery acknowledgment is available to GitHub Actions.'
    })
    items = sorted(items, key=lambda x: x.get('slot_at', ''))[-max_entries:]
    path.write_text(json.dumps({
        'schema_version': 1,
        'purpose': 'Historical data-readiness ledger (not an outgoing notification receipt)',
        'cycles': items, 'count': len(items)
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
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
