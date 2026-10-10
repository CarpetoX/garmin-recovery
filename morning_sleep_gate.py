#!/usr/bin/env python3
"""Non-destructive, conservative morning sleep state classifier (Europe/Madrid)."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')

def load(name):
    try:
        obj=json.loads(Path(name).read_text(encoding='utf-8'))
        return obj if isinstance(obj,dict) else {}
    except (OSError,ValueError):
        return {}

def dt(value):
    if not isinstance(value,str) or not value: return None
    try:
        x=datetime.fromisoformat(value.replace('Z','+00:00'))
        return x.replace(tzinfo=TZ) if x.tzinfo is None else x.astimezone(TZ)
    except ValueError: return None

def classify(now=None, sleep=None, recovery=None, shifts=None):
    now=now or datetime.now(TZ)
    sleep=sleep if sleep is not None else load('garmin_sleep_history.json')
    recovery=recovery if recovery is not None else load('recovery_assessment.json')
    shifts=shifts if shifts is not None else load('shift_calendar.json')
    today=now.date().isoformat()
    yesterday=(now.date()-timedelta(days=1)).isoformat()
    shift_days=shifts.get('days',{}) if isinstance(shifts.get('days'),dict) else {}
    post_night_shift=shift_days.get(yesterday)=='TN'
    row=(sleep.get('days') or {}).get(today,{})
    if not isinstance(row,dict): row={}
    end=dt(row.get('sleep_end_local'))
    start=dt(row.get('sleep_start_local'))
    confirmed=row.get('window_confirmed') is True and end is not None and start is not None and end>start and end.date()==now.date() and end<=now+timedelta(minutes=2)
    rec_current=recovery.get('current') or {}
    rec_end=dt(rec_current.get('sleep_end_local'))
    rec_matches=rec_end is not None and end is not None and abs((rec_end-end).total_seconds())<=300
    age_minutes=round((now-end).total_seconds()/60,1) if confirmed else None
    # After a night shift, a 03:00-05:00 episode can precede the main sleep.
    # Do not declare a definitive morning report from an episode ending before 07:00.
    early_post_shift_episode=bool(post_night_shift and confirmed and end.hour<7)
    fresh_sleep=(recovery.get('input_freshness') or {}).get('sleep') is True
    if confirmed:
        if early_post_shift_episode:
            state='post_night_shift_early_sleep_pending'
        elif age_minutes<30:
            state='confirmed_wait_30m'
        elif not rec_matches or not fresh_sleep:
            state='confirmed_recovery_sync_pending'
        else:
            state='confirmed_ready'
    else:
        state='post_night_shift_sleep_pending' if post_night_shift else 'sleep_or_sync_pending'
    return {
        'schema_version':1,'generated_at':now.isoformat(),'date':today,
        'state':state,'is_definitive':state=='confirmed_ready',
        'possible_sleep_in_progress':not confirmed or early_post_shift_episode,
        'wake_confirmed':confirmed and not early_post_shift_episode,
        'episode_end_confirmed':confirmed,
        'post_night_shift':post_night_shift,
        'early_post_shift_episode':early_post_shift_episode,
        'sleep_end_local':end.isoformat() if confirmed else None,
        'minutes_since_sleep_end':age_minutes,
        'recovery_matches_sleep_episode':rec_matches if confirmed else None,
        'recovery_sleep_fresh':fresh_sleep,
        'earliest_definitive_at':(end+timedelta(minutes=30)).isoformat() if confirmed else None,
        'message':{
          'confirmed_ready':'Sueño confirmado, margen de 30 minutos cumplido y recuperación sincronizada.',
          'confirmed_wait_30m':'Despertar confirmado; pendiente margen de 30 minutos.',
          'confirmed_recovery_sync_pending':'Sueño confirmado; falta sincronizar el análisis de recuperación del mismo episodio.',
          'post_night_shift_sleep_pending':'Posible sueño diurno o fragmentado tras turno de noche; no asumir despertar.',
          'post_night_shift_early_sleep_pending':'Episodio temprano tras TN confirmado; puede faltar el descanso principal.',
          'sleep_or_sync_pending':'Sueño posiblemente en curso o despertar pendiente de sincronizar; no se puede distinguir con certeza.'
        }[state],
        'policy':'No usar sueño anterior como actual ni inferir vigilia sin episodio confirmado.',
    }

def main():
    result=classify()
    Path('morning_sleep_status.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'state':result['state'],'is_definitive':result['is_definitive']},ensure_ascii=False))

if __name__=='__main__': main()
