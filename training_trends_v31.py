#!/usr/bin/env python3
"""V3.1: conservative CrossFit trends (3/7/28d) from recorded evidence.

Compare exactly matching exercise, equipment and load unit. Exercise peaks are
observed declared loads, NOT estimated 1RM. The Garmin recorded duration is
not the effective WOD time. Missing/unmatched entries remain missing.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from performance_report_v32 import build_report
from performance_enhancements_v35 import build as build_v35

TZ = ZoneInfo('Europe/Madrid')
WINDOWS = (3, 7, 28)


def num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def date_of(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def trend(report, today):
    if not isinstance(report, dict) or not isinstance(report.get('activities'), list):
        raise ValueError('CrossFit JSON without activities array')
    if isinstance(today, str):
        today = date.fromisoformat(today)
    if not isinstance(today, date):
        raise ValueError('today must be a date')
    acts = [a for a in report['activities'] if isinstance(a, dict) and date_of(a.get('date'))]
    # JSON source is a last-90 activity view; 28d window can thus be incomplete.
    windows = {}
    for days in WINDOWS:
        start = today - timedelta(days=days - 1)
        rows = [a for a in acts if start <= date_of(a['date']) <= today]
        rpe = [num(a.get('rpe_used')) for a in rows]
        rpe = [x for x in rpe if x is not None]
        s_rpe = [num(a.get('srpe_using_recorded_minutes')) for a in rows]
        s_rpe = [x for x in s_rpe if x is not None]
        minutes = [num(a.get('recorded_minutes')) for a in rows]
        minutes = [x for x in minutes if x is not None]
        windows[f'{days}d'] = {
            'start_date': start.isoformat(), 'end_date': today.isoformat(),
            'recorded_sessions': len(rows), 'recorded_sessions_with_rpe': len(rpe),
            'mean_session_rpe': round(sum(rpe)/len(rpe), 2) if rpe else None,
            'recorded_duration_minutes': round(sum(minutes), 1) if minutes else None,
            'srpe_recorded_duration_sum': round(sum(s_rpe), 1) if s_rpe else None,
            'srpe_samples': len(s_rpe),
        }
    daily=[]
    for lag in range(27,-1,-1):
        d=today-timedelta(days=lag)
        observed=[a for a in acts if date_of(a.get('date'))==d]
        rpe=[num(a.get('rpe_used')) for a in observed]
        rpe=[x for x in rpe if x is not None]
        daily.append({'date':d.isoformat(), 'recorded_sessions':len(observed),
                      'mean_session_rpe':round(sum(rpe)/len(rpe),2) if rpe else None,
                      'no_recorded_sessions_not_proof_of_rest':not bool(observed)})
    exercises=(report.get('muscle_load') or {}).get('strength_exercises') or []
    if not isinstance(exercises,list):
        exercises=[]
    groups=defaultdict(list)
    for x in exercises:
        if not isinstance(x,dict):
            continue
        when=date_of(x.get('date'))
        load=num(x.get('peak_declared_load_kg'))
        # Only actual declaration, not an estimate. Never compare equipment across types.
        if (when is None or when>today or when<today-timedelta(days=27) or load is None
                or load<0 or not isinstance(x.get('exercise'),str)
                or not isinstance(x.get('equipment'),str)
                or not isinstance(x.get('load_unit'),str)):
            continue
        key=(x['exercise'].strip().casefold(),x['equipment'],x['load_unit'])
        groups[key].append({'date':when.isoformat(), 'observed_peak_kg':load,
                            'recorded_activity_id':x.get('activity_id'),
                            'verified_volume_kg':num(x.get('verified_volume_kg')),
                            'known_sets':x.get('known_sets'),
                            'volume_complete':x.get('volume_complete') is True})
    by_exercise=[]
    for (name,equipment,unit),history in sorted(groups.items()):
        history.sort(key=lambda x:(x['date'],str(x['recorded_activity_id'])))
        by_exercise.append({'exercise':name,'equipment':equipment,'load_unit':unit,
                            'sessions':len(history),'points':history,
                            'progression_status':'descriptive_only' if len(history)>=2 else 'insufficient_repeats',
                            'estimated_1rm_inferred':False})
    reasons=[]
    if windows['28d']['recorded_sessions'] < 10:
        reasons.append('Not enough recorded sessions for a reliable 28-day trend')
    if report.get('sheet_source') not in ('cycle_snapshot','live_csv'):
        reasons.append('RPE source not verified')
    recent=windows['7d']
    if recent['recorded_sessions'] and not recent['recorded_sessions_with_rpe']:
        reasons.append('Missing session RPE; do not infer it from activity type')
    return {'schema_version':1,'version':'3.1','as_of_date':today.isoformat(),
            'source':'crossfit_insights.json', 'source_generated_at':report.get('generated_at'),
            'sheet_source':report.get('sheet_source'), 'windows':windows,
            'daily_chart_28d':daily,'strength_by_exact_equipment':by_exercise,
            'confidence':'provisional' if reasons else 'descriptive', 'limitations':reasons,
            'recommendations':[{'type':'data_quality','text':'Track consistent activity IDs, set loads, units and session RPE.'},
                               {'type':'interpretation','text':'Compare only repeated identical benchmark variants and the same equipment.'}],
            'interpretation':('Observed peak loads are not 1RM estimates. Session-RPE × Garmin recorded '
                              'minutes is not effective WOD duration. No-day entry is not proof of rest. '
                              'No medical conclusions or causal effect of night shifts.')}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,default=Path('crossfit_insights.json'))
    parser.add_argument('--out',type=Path,default=Path('training_trends_v31.json'))
    parser.add_argument('--today',default=None)
    a=parser.parse_args(argv)
    raw=json.loads(a.input.read_text(encoding='utf-8'))
    day=date.fromisoformat(a.today) if a.today else datetime.now(TZ).date()
    result=trend(raw,day)
    # V3.2: anadir un informe compatible al JSON existente; no crear otro workflow.
    # Las fuentes siguen separadas, sin inferir datos ausentes.
    wellness_path=Path('wellness.json')
    daily_path=Path('daily_summary.json')
    wellness=json.loads(wellness_path.read_text(encoding='utf-8')) if wellness_path.exists() else []
    daily=json.loads(daily_path.read_text(encoding='utf-8')) if daily_path.exists() else {}
    result['performance_report_v32']=build_report(raw,wellness,daily,day)
    # V3.5: seccion estrictamente aditiva, mantiene intacto el contrato V3.2.
    result['performance_report_v32']['performance_enhancements_v35'] = build_v35(
        raw, result['performance_report_v32'], day)
    result['generated_at']=datetime.now(timezone.utc).isoformat()
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':'ok','sessions_28d':result['windows']['28d']['recorded_sessions'],
                      'exercise_groups':len(result['strength_by_exact_equipment'])}))


if __name__=='__main__':
    main()
