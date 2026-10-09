#!/usr/bin/env python3
"""V2.3.1 schedule verification: a manual success cannot mask a missed cron slot."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ=ZoneInfo('Europe/Madrid')
SLOTS=((8,30),(14,30),(18,30),(23,0))

def _utc_local(t):
    try:
        return datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(TZ)
    except (ValueError,TypeError,AttributeError):
        return None

def audit_slots(now,runs, lookback_hours=28, grace_minutes=120):
    if now.tzinfo is None: now=now.replace(tzinfo=TZ)
    now=now.astimezone(TZ)
    if not isinstance(runs,list):
        return {'state':'unverified','reason':'no_workflow_run_data','due':0,'matched':0,'missed':[]}
    eligible=[]
    for offset in range(3):
        d=now.date()-timedelta(days=offset)
        for hr,mn in SLOTS:
            slot=datetime(d.year,d.month,d.day,hr,mn,tzinfo=TZ)
            if now-timedelta(hours=lookback_hours)<=slot and slot+timedelta(minutes=grace_minutes)<=now:
                eligible.append(slot)
    matches=[]; missed=[]
    scheduled=[]
    for r in runs:
        if r.get('event')!='schedule' or r.get('status')!='completed' or r.get('conclusion')!='success':
            continue
        created=_utc_local(r.get('created_at'))
        if created: scheduled.append(created)
    for slot in sorted(eligible):
        ok=any(slot-timedelta(minutes=5)<=run<=slot+timedelta(minutes=grace_minutes) for run in scheduled)
        (matches if ok else missed).append(slot.isoformat())
    return {'state':'attention' if missed else 'ok' if eligible else 'awaiting_next_due_slot',
            'due':len(eligible),'matched':len(matches),'missed':missed,
            'manual_runs_counted_as_schedule':False,
            'grace_minutes':grace_minutes,'timezone':'Europe/Madrid'}

def enhance_monitor(base, now, repo, token, fetcher):
    if not isinstance(base,dict): return base
    try:
        result=audit_slots(now,fetcher(repo,token,'sync.yml')) if repo and token else {'state':'unverified','reason':'missing_credentials'}
    except Exception as e:
        result={'state':'unverified','reason':type(e).__name__}
    base['schedule_v231']=result
    if result.get('state')=='attention':
        base.setdefault('alerts',[]).append({'severity':'warning','code':'scheduled_sync_slots_missed',
             'missed_count':len(result['missed']), 'window_hours':28})
        if base.get('status')!='error': base['status']='attention'
    elif result.get('state')=='unverified':
        base.setdefault('alerts',[]).append({'severity':'warning','code':'schedule_audit_unverified'})
        if base.get('status')!='error': base['status']='attention'
    base['note']='Actual run outcomes and per-slot schedule audit; manual runs never satisfy scheduled slots.'
    return base


def self_test():
    from datetime import timezone
    now=datetime(2026,10,9,13,19,tzinfo=TZ)
    yesterday=datetime(2026,10,8,8,30,tzinfo=TZ)
    runs=[{'event':'workflow_dispatch','status':'completed','conclusion':'success','created_at':'2026-10-09T10:00:00Z'},
          {'event':'schedule','status':'completed','conclusion':'success','created_at':yesterday.astimezone(timezone.utc).isoformat()}]
    a=audit_slots(now,runs)
    assert a['due'] >= 1 and a['state']=='attention' and a['manual_runs_counted_as_schedule'] is False, a
    scheduled=datetime(2026,10,9,8,38,tzinfo=TZ).astimezone(timezone.utc).isoformat()
    b=audit_slots(now,[{'event':'schedule','status':'completed','conclusion':'success','created_at':scheduled}],lookback_hours=12)
    assert b['due']==1 and b['matched']==1 and b['state']=='ok', b
    c=audit_slots(datetime(2026,10,9,7,tzinfo=TZ),[],lookback_hours=4)
    assert c['state']=='awaiting_next_due_slot',c
    print('3 schedule-monitor tests passed')

if __name__=='__main__': self_test()
