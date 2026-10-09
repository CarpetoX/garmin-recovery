#!/usr/bin/env python3
"""Monitor the actual GitHub Actions pipeline and summarize the previous month."""
import json
import os
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
WORKFLOWS = (
    'sync.yml',
    'garmin-heart-rate.yml',
    'advanced-analytics-rpe.yml',
    'crossfit-insights.yml',
)


def fetch_runs(repo, token, workflow):
    url = f'https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=50'
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Garmin-Workflow-Monitor',
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)['workflow_runs']


def parsed_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(TZ)


def monitor(now, repo, token, fetcher=fetch_runs):
    result = {
        'checked_at': now.isoformat(), 'repository': repo,
        'status': 'unknown', 'workflows': {}, 'alerts': [],
        'note': 'Actual GitHub Actions conclusions; schedule omissions are checked separately. '
                'Skipped runs are not successful runs.',
    }
    if not token or not repo:
        result['alerts'].append({'severity': 'error', 'code': 'missing_github_credentials'})
        result['status'] = 'error'
        return result

    for workflow in WORKFLOWS:
        try:
            runs = fetcher(repo, token, workflow)
            completed = sorted(
                (run for run in runs if run.get('status') == 'completed'),
                key=lambda run: run.get('created_at', ''), reverse=True,
            )
            latest = completed[0] if completed else None
            successes = [run for run in completed if run.get('conclusion') == 'success']
            latest_success = successes[0] if successes else None
            successful_at = parsed_time(latest_success.get('updated_at')) if latest_success else None
            age = round((now - successful_at).total_seconds() / 3600, 2) if successful_at else None
            result['workflows'][workflow] = {
                'last_completed_conclusion': latest.get('conclusion') if latest else None,
                'last_completed_at': latest.get('updated_at') if latest else None,
                'last_success_at': successful_at.isoformat() if successful_at else None,
                'last_success_age_hours': age,
                'latest_run_url': latest.get('html_url') if latest else None,
                'latest_run_event': latest.get('event') if latest else None,
            }
            if latest and latest.get('conclusion') in ('failure', 'timed_out', 'cancelled', 'action_required'):
                result['alerts'].append({
                    'severity': 'warning', 'code': 'latest_run_failed',
                    'workflow': workflow, 'conclusion': latest['conclusion'],
                    'url': latest.get('html_url'),
                })
            elif latest and latest.get('conclusion') == 'skipped':
                result['alerts'].append({
                    'severity': 'info', 'code': 'latest_run_skipped', 'workflow': workflow,
                    'url': latest.get('html_url'),
                })
            if age is None or age > 30:
                result['alerts'].append({
                    'severity': 'warning', 'code': 'no_recent_success',
                    'workflow': workflow, 'age_hours': age,
                })
            if workflow == 'sync.yml':
                scheduled_success = any(
                    run.get('event') == 'schedule' and run.get('conclusion') == 'success'
                    and parsed_time(run.get('updated_at')) is not None
                    and timedelta(0) <= now - parsed_time(run['updated_at']) < timedelta(hours=72)
                    for run in completed
                )
                if not scheduled_success:
                    result['alerts'].append({
                        'severity': 'warning', 'code': 'no_recent_successful_scheduled_run',
                        'workflow': workflow, 'window_hours': 72,
                    })
        except (urllib.error.URLError, ValueError, KeyError, TypeError) as exc:
            result['workflows'][workflow] = {'error': str(exc)[:200]}
            result['alerts'].append({
                'severity': 'error', 'code': 'workflow_check_failed', 'workflow': workflow,
            })

    result['status'] = ('error' if any(a['severity'] == 'error' for a in result['alerts'])
                        else 'attention' if any(a['severity'] == 'warning' for a in result['alerts'])
                        else 'ok')
    return result


def monthly(now, history_path='report_history.json'):
    try:
        history = json.loads(Path(history_path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        history = {}
    snapshots = history.get('snapshots', []) if isinstance(history, dict) else []
    if not isinstance(snapshots, list):
        snapshots = []
    end = now.date().replace(day=1) - timedelta(days=1)
    start = end.replace(day=1)
    items = sorted(
        (s for s in snapshots if isinstance(s, dict)
         and start.isoformat() <= str(s.get('date', '')) <= end.isoformat()),
        key=lambda s: s.get('date', ''),
    )
    readiness = [s['readiness_score'] for s in items
                 if s.get('readiness_state') == 'assessed'
                 and s.get('readiness_confidence') == 'high'
                 and isinstance(s.get('readiness_score'), (int, float))
                 and not isinstance(s['readiness_score'], bool)]
    counts = Counter(s.get('quality_status', 'unknown') for s in items)
    return {
        'generated_at': now.isoformat(), 'period_start': start.isoformat(),
        'period_end': end.isoformat(), 'days_with_snapshots': len(items),
        'coverage_pct': round(100 * len(items) / end.day, 1),
        'mean_readiness_score': round(sum(readiness) / len(readiness), 1) if readiness else None,
        'quality_status_counts': dict(counts),
        'latest_weekly_activities': items[-1].get('weekly_activities') if items else None,
        'latest_weekly_minimum_verified_strength_volume_kg':
            items[-1].get('minimum_verified_strength_volume_kg') if items else None,
        'confidence': 'insufficient_history' if len(items) < 14 else 'descriptive_only',
        'limitations': [
            'Historical snapshots are daily summaries, not full exercise logs',
            'Weekly metrics in daily snapshots overlap and must not be summed',
            'Missing days are not zero-readiness days',
            'WOD performance trends require comparable sessions and explicit results',
            'Not a medical diagnosis',
        ],
    }


def main():
    now = datetime.now(TZ)
    health = monitor(now, os.environ.get('GITHUB_REPOSITORY', ''), os.environ.get('GH_TOKEN', ''))
    Path('workflow_health.json').write_text(
        json.dumps(health, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report = monthly(now)
    Path('monthly_report.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'monitor_status': health['status'], 'alerts': health['alerts'],
                      'monthly_coverage': report['coverage_pct']}, ensure_ascii=False))
    if health['status'] == 'error':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
