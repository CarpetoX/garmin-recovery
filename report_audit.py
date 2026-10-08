"""Conservative provenance, freshness and bounded history for Garmin/CrossFit.
A file's generated_at is NOT its physiological measurement timestamp.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Europe/Madrid')
SOURCES=('daily_summary.json','garmin_status.json','data_quality.json','advanced_analytics.json','weekly_summary.json','garmin_heart_rate.json','wellness.json','activities.json')

def parse_time(value):
    if not isinstance(value,str) or not value.strip(): return None
    try:
        d=datetime.fromisoformat(value.replace('Z','+00:00'))
        return (d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ))
    except ValueError: return None

def provenance(now):
    sources={}; flags=[]
    for name in SOURCES:
        path=Path(name)
        if not path.exists():
            sources[name]={'state':'missing','generated_at':None,'age_hours':None,'measurement_at':None}
            if name in SOURCES[:4]: flags.append({'severity':'warning','code':'missing_required_source','file':name})
            continue
        try: data=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):
            sources[name]={'state':'invalid_json','generated_at':None,'age_hours':None,'measurement_at':None}
            flags.append({'severity':'warning','code':'invalid_source','file':name});continue
        generated=parse_time(data.get('generated_at')) if isinstance(data,dict) else None
        age=round((now-generated).total_seconds()/3600,2) if generated else None
        state='ok' if age is not None and -0.25 <= age <= 8 else 'unknown_time' if age is None else 'stale' if age>8 else 'future_timestamp'
        sources[name]={'state':state,'generated_at':generated.isoformat() if generated else None,'age_hours':age,'measurement_at':None,'measurement_note':'No verified per-sample timestamp in this audit'}
        if name in SOURCES[:4] and state!='ok': flags.append({'severity':'warning','code':'source_not_fresh','file':name,'state':state})
        if name=='garmin_status.json' and isinstance(data,dict):
            sources[name]['garmin_status']=data.get('status')
            sources[name]['latest_date_markers']={k:data.get(k) for k in ('latest_stress_date','latest_body_battery_date','latest_extended_date','latest_heart_rate_date')}
            if data.get('status')!='success': flags.append({'severity':'warning','code':'garmin_status_not_success'})
    # Timestamp coherence is a heuristic, not proof of GitHub Actions completion.
    required=[sources[n] for n in SOURCES[:4]]
    times=[parse_time(s['generated_at']) for s in required if s['generated_at']]
    skew=round((max(times)-min(times)).total_seconds()/60,1) if len(times)==4 else None
    if skew is not None and skew>120: flags.append({'severity':'warning','code':'source_generation_skew','minutes':skew})
    return {'checked_at':now.isoformat(),'status':'attention' if flags else 'ok','sources':sources,'generation_skew_minutes':skew,'flags':flags,'chain_verification':'timestamps_only; GitHub Actions run conclusions not checked','measurement_timestamp_verified':False}

def update_history(out, now, path='report_history.json'):
    p=Path(path)
    try: previous=json.loads(p.read_text(encoding='utf-8'))
    except (OSError,ValueError): previous={}
    old=previous.get('snapshots',[]) if isinstance(previous,dict) else []
    if not isinstance(old,list): old=[]
    quality=out.get('data_quality') or {}
    weekly=out.get('weekly_report') or {}
    readiness=out.get('readiness_hybrid') or {}
    audit=out.get('report_audit') or {}
    # Store only aggregate metrics; no raw sheet notes, shifts or individual activity records.
    snap={'generated_at':now.isoformat(),'date':now.date().isoformat(),
          'sheet_rows_loaded':out.get('sheet_rows_loaded'),'quality_status':quality.get('status'),
          'audit_status':audit.get('status'),'readiness_score':readiness.get('score'),
          'readiness_confidence':readiness.get('local_confidence'),
          'weekly_activities':weekly.get('activities'),
          'minimum_verified_strength_volume_kg':weekly.get('minimum_verified_strength_volume_kg')}
    # Keep at most one snapshot per local day; latest successful report wins.
    old=[x for x in old if isinstance(x,dict) and x.get('date')!=snap['date']]
    old.append(snap)
    cutoff=(now.date()-timedelta(days=89)).isoformat()
    old=sorted((x for x in old if str(x.get('date',''))>=cutoff),key=lambda x:x.get('date',''))[-90:]
    p.write_text(json.dumps({'version':1,'timezone':'Europe/Madrid','retention_days':90,'snapshots':old},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return len(old)
