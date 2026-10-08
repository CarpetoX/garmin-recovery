#!/usr/bin/env python3
"""Read-only GitHub Actions monitor and conservative monthly summary."""
import json, os, urllib.request, urllib.error
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Europe/Madrid')
WORKFLOWS=['sync.yml','crossfit-insights.yml']
# GitHub Actions REST API returns actual runs, not inferred file timestamps.
def fetch_runs(repo, token, workflow):
    url=f'https://api.github.com/repos/{repo}/actions/workflows/{workflow}/runs?per_page=40'
    req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','Authorization':f'Bearer {token}','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Garmin-Workflow-Monitor'})
    with urllib.request.urlopen(req,timeout=25) as res:
        return json.load(res)['workflow_runs']

def monitor(now,repo,token,fetcher=fetch_runs):
    result={'checked_at':now.isoformat(),'repository':repo,'status':'unknown','workflows':{},'alerts':[],
            'note':'Checks actual GitHub Actions runs; scheduled run may be delayed by GitHub.'}
    if not token or not repo:
        result['alerts'].append({'severity':'error','code':'missing_github_credentials'});return result
    for wf in WORKFLOWS:
        try:
            runs=fetcher(repo,token,wf)
            completed=[r for r in runs if r.get('status')=='completed']
            latest=completed[0] if completed else None
            successes=[r for r in completed if r.get('conclusion')=='success']
            latest_ok=successes[0] if successes else None
            last_ok_time=datetime.fromisoformat(latest_ok['updated_at'].replace('Z','+00:00')).astimezone(TZ) if latest_ok else None
            age=round((now-last_ok_time).total_seconds()/3600,2) if last_ok_time else None
            result['workflows'][wf]={'last_completed_conclusion':latest.get('conclusion') if latest else None,
                'last_completed_at':latest.get('updated_at') if latest else None,
                'last_success_at':last_ok_time.isoformat() if last_ok_time else None,
                'last_success_age_hours':age,'latest_run_url':latest.get('html_url') if latest else None,
                'latest_run_event':latest.get('event') if latest else None}
            if latest and latest.get('conclusion') not in ('success','skipped'):
                result['alerts'].append({'severity':'warning','code':'latest_run_failed','workflow':wf,'conclusion':latest.get('conclusion')})
            if age is None or age>30:
                result['alerts'].append({'severity':'warning','code':'no_recent_success','workflow':wf,'age_hours':age})
            if wf=='sync.yml' and not any(r.get('event')=='schedule' and r.get('conclusion')=='success' and
                (now-datetime.fromisoformat(r['updated_at'].replace('Z','+00:00')).astimezone(TZ)).total_seconds()<72*3600 for r in completed):
                result['alerts'].append({'severity':'info','code':'no_recent_successful_scheduled_run','workflow':wf,'window_hours':72})
        except (urllib.error.URLError,ValueError,KeyError,TypeError) as exc:
            result['workflows'][wf]={'error':str(exc)[:200]}
            result['alerts'].append({'severity':'error','code':'workflow_check_failed','workflow':wf})
    result['status']='error' if any(a['severity']=='error' for a in result['alerts']) else ('attention' if any(a['severity']=='warning' for a in result['alerts']) else 'ok')
    return result

def monthly(now, history_path='report_history.json'):
    try: history=json.loads(Path(history_path).read_text(encoding='utf-8'))
    except (OSError,ValueError): history={}
    snapshots=history.get('snapshots',[]) if isinstance(history,dict) else []
    first=now.date().replace(day=1)
    # Last completed calendar month (not current partial month).
    end=first-timedelta(days=1)
    start=end.replace(day=1)
    items=[s for s in snapshots if isinstance(s,dict) and start.isoformat()<=str(s.get('date',''))<=end.isoformat()]
    readiness=[s['readiness_score'] for s in items if isinstance(s.get('readiness_score'),(int,float))]
    status=Counter(s.get('quality_status','unknown') for s in items)
    return {'generated_at':now.isoformat(),'period_start':start.isoformat(),'period_end':end.isoformat(),
        'days_with_snapshots':len(items),'coverage_pct':round(100*len(items)/end.day,1),
        'mean_readiness_score':round(sum(readiness)/len(readiness),1) if readiness else None,
        'quality_status_counts':dict(status),
        'latest_weekly_activities':items[-1].get('weekly_activities') if items else None,
        'latest_weekly_minimum_verified_strength_volume_kg':items[-1].get('minimum_verified_strength_volume_kg') if items else None,
        'confidence':'insufficient_history' if len(items)<14 else 'descriptive_only',
        'limitations':['Historical snapshots are daily summaries, not full exercise logs',
          'Weekly metrics in daily snapshots overlap and must not be summed',
          'Missing days are not zero-readiness days',
          'WOD performance trends require comparable sessions and explicit results',
          'Not a medical diagnosis']}

def main():
    now=datetime.now(TZ)
    repo=os.environ.get('GITHUB_REPOSITORY','')
    token=os.environ.get('GH_TOKEN','')
    result=monitor(now,repo,token)
    Path('workflow_health.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report=monthly(now)
    Path('monthly_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'monitor_status':result['status'],'alerts':result['alerts'],'monthly_coverage':report['coverage_pct']},ensure_ascii=False))
    # Make real monitor errors visible in Actions; report artifacts are still written.
    if result['status']=='error': raise SystemExit(1)

if __name__=='__main__':main()
