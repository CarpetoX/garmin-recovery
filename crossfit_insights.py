#!/usr/bin/env python3
"""CrossFit supplement: manual Sheet A:H + Garmin/Intervals, no invented data."""
import csv, io, json, os, math, statistics, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from muscle_load import analyze as analyze_muscle_load
from data_quality import analyze as analyze_data_quality
from training_extensions import analyze as analyze_training_extensions

TZ = ZoneInfo('Europe/Madrid')
SHEET_ID = '1vbxls-yyBOs8_gAmp9ld2WI_Ss9jvXNMFbxV5TKWX_k'
HEADERS = ['Fecha','ID actividad','Actividad','RPE','Sensaciones','Notas','Registrado','Detalle JSON']

def load(name, fallback):
    try: return json.loads(Path(name).read_text(encoding='utf-8'))
    except (OSError, ValueError): return fallback

def number(v):
    try:
        if v is None or isinstance(v, bool) or str(v).strip()=='': return None
        n=float(str(v).replace(',','.'))
        return n if math.isfinite(n) else None
    except (TypeError, ValueError): return None

def detail(value):
    if isinstance(value, dict): return value
    if isinstance(value, str):
        try:
            obj=json.loads(value)
            return obj if isinstance(obj, dict) else {}
        except ValueError: return {}
    return {}

def sheet_rows():
    # Secret can be a published CSV URL, or an Apps Script endpoint exporting A:H.
    # A private Google Sheet cannot be fetched using only its spreadsheet ID.
    url=os.environ.get('RPE_CSV_URL','').strip()
    if not url: return [], 'not_configured', 'RPE_CSV_URL no configurada; no hay lectura en vivo'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Garmin-CrossFit-Insights/1.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            raw=response.read(3_000_000).decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(raw)))
        if not rows: raise ValueError('CSV vacío')
        # Accept header row or A:H ordered columns, never silently accept HTML.
        if '<html' in raw[:500].lower(): raise ValueError('URL devolvió HTML, no CSV')
        first=[x.strip() for x in rows[0][:8]]
        has_header=(first[:4]==HEADERS[:4])
        if not has_header and first[0].lower() in ('fecha','date'):
            raise ValueError('Cabeceras inesperadas: se necesitan A:H con Detalle JSON')
        data=rows[1:] if has_header else rows
        output=[]
        for cells in data:
            if len(cells)<2 or not cells[0].strip(): continue
            padded=(cells+['']*8)[:8]
            output.append(dict(zip(HEADERS,padded)))
        return output,'live_csv',None
    except Exception as exc:
        return [],'unavailable',str(exc)[:250]

def normalize_id(x): return str(x or '').strip().lower()

def local_date(a):
    for key in ('start_date_local','start_date','date'):
        s=str(a.get(key) or '')
        if len(s)>=10: return s[:10]
    return None

def match_feedback(activity,rows,feedback):
    aid=normalize_id(activity.get('id'))
    date=local_date(activity)
    exact=[r for r in rows if normalize_id(r['ID actividad'])==aid and aid]
    if exact: return exact,'sheet_id'
    # Date-only matching is ambiguous with multiple sessions; don't attribute one row to another.
    legacy=(feedback.get('activities') or {}).get(str(activity.get('id')), {})
    if isinstance(legacy,dict) and legacy: return [legacy],'github_feedback'
    return [],'unmatched'

def extract(row):
    if 'ID actividad' in row:
        return {'date':row['Fecha'],'activity':row['Actividad'],'rpe':number(row['RPE']),
                'notes':row['Notas'],'feel':row['Sensaciones'],'detail':detail(row['Detalle JSON'])}
    return {'date':row.get('date'),'activity':row.get('activity'),'rpe':number(row.get('rpe')),
            'notes':row.get('notes'),'feel':row.get('sensations'),
            'detail':detail(row.get('detail_json') or row.get('detail'))}

def sets_volume(obj):
    """Calculate only verifiable strength tonnage, including nested exercises."""
    if not isinstance(obj, dict):
        return None, False, 0, 0

    exercises = obj.get('exercises')
    groups = exercises if isinstance(exercises, list) else [obj]
    total_volume = 0.0
    known_sets = 0
    total_sets = 0

    for exercise in groups:
        if not isinstance(exercise, dict):
            continue
        sets = exercise.get('sets', [])
        if not isinstance(sets, list):
            continue
        for item in sets:
            if not isinstance(item, dict):
                continue
            count = number(item.get('count'))
            count = int(count) if count is not None and count >= 1 and count.is_integer() else 1
            total_sets += count
            reps = number(item.get('reps'))
            kg = number(item.get('load_kg'))
            if kg is None:
                kg = number(item.get('weight_kg'))
            if reps is not None and reps > 0 and kg is not None and kg > 0:
                total_volume += reps * kg * count
                known_sets += count

    complete = total_sets > 0 and known_sets == total_sets
    volume = round(total_volume, 1) if known_sets else None
    return volume, complete, known_sets, total_sets

def shift(day):
    try: d=datetime.fromisoformat(day).date()
    except (TypeError,ValueError): return 'unknown'
    mt={10:{2,7,12,17,22},11:{1,6,11,16,21,26}}
    tn={10:{3,8,13,18,23,30},11:{2,7,12,17,22,27}}
    if d.year!=2026 or d.month not in mt: return 'unknown'
    if d.day in tn[d.month]: return 'TN'
    if d.day in mt[d.month]: return 'MT'
    from datetime import timedelta
    prev=d-timedelta(days=1)
    if prev.month in tn and prev.day in tn[prev.month]: return 'post-TN'
    return 'free'

def main():
    now=datetime.now(TZ)
    activities=load('activities.json',[])
    advanced=load('advanced_analytics.json',{})
    feedback=load('training_feedback.json',{})
    rows,source,error=sheet_rows()
    if not isinstance(activities,list): activities=[]
    if not isinstance(advanced,dict): advanced={}
    if not isinstance(feedback,dict): feedback={}
    results=[]
    for a in activities:
        if not isinstance(a,dict): continue
        matches,match=match_feedback(a,rows,feedback)
        manual=[extract(r) for r in matches]
        seconds=number(a.get('moving_time'))
        if seconds is None: seconds=number(a.get('elapsed_time'))
        minutes=round(seconds/60,2) if seconds is not None else None
        rpes=[x['rpe'] for x in manual if x['rpe'] is not None]
        rpe=(rpes[0] if len(set(rpes))==1 else None) if rpes else (number(a.get('icu_rpe')) or number(a.get('session_rpe')))
        blocks=[]
        for x in manual:
            vol,complete,known,total=sets_volume(x['detail'])
            blocks.append({'activity':x['activity'],'rpe':x['rpe'],'notes':x['notes'],
                           'sensations':x['feel'],'detail_json':x['detail'],
                           'minimum_verified_volume_kg':vol,'volume_complete':complete,
                           'structured_sets_known':known,'structured_sets_total':total})
        results.append({'activity_id':a.get('id'),'date':local_date(a),'context':shift(local_date(a)),
            'name':a.get('name'),'manual_match':match,'manual_blocks':blocks,
            'manual_rpe_conflict':len(set(rpes))>1,'rpe_used':rpe,
            'rpe_interval':number(a.get('icu_rpe')) or number(a.get('session_rpe')),
            'rpe_disagreement':bool(rpes and (number(a.get('icu_rpe')) or number(a.get('session_rpe'))) is not None and any(abs(x-(number(a.get('icu_rpe')) or number(a.get('session_rpe'))))>0.01 for x in rpes)),
            'recorded_minutes':minutes,
            'srpe_using_recorded_minutes':round(rpe*minutes,1) if rpe is not None and minutes is not None and not (len(set(rpes))>1) else None,
            'srpe_caveat':'Duración grabada; no equivale necesariamente al tiempo efectivo del WOD.',
            'external_work':{'distance_m':number(a.get('distance')),'reps':None,'strength_volume_kg':None},
            'internal_load_not_additive':{'trimp':number(a.get('trimp')),
                 'intervals_load':number(a.get('icu_training_load')),'hr_load':number(a.get('hr_load'))},
            'heart_rate':{'average':number(a.get('average_heartrate')),'max':number(a.get('max_heartrate'))},
            'efficiency':'insufficient_matched_repeated_workouts',
            'neuromuscular_fatigue':'not_directly_measured'})
    ctx=advanced.get('baselines_by_context',{})
    counts={k:v.get('days') for k,v in ctx.items() if isinstance(v,dict)} if isinstance(ctx,dict) else {}
    out={'generated_at':now.isoformat(),'source_measurement_note':'La generación del JSON no es hora de medición',
         'sheet_source':source,'sheet_error':error,'sheet_rows_loaded':len(rows),
         'sheet_has_detail_json':bool(rows and any(r.get('Detalle JSON','').strip() for r in rows)),
         'manual_source_rule':'Sheet A:H en vivo es prioritario; GitHub training_feedback es respaldo.',
         'quality':{'interpretation':'provisional','limitations':['Pocos WOD equivalentes para eficiencia','Fatiga neuromuscular no medida directamente','La respuesta 24-48 h no demuestra causalidad']},
         'context_today':shift(now.date().isoformat()),'context_baseline_days':counts,
         'response_24_48h':advanced.get('training_response_24_48h'),
         'readiness_hybrid':advanced.get('readiness_hybrid'),
         'activities':results[-90:],
         'muscle_load':analyze_muscle_load(results, now.date().isoformat()),
         'training_extensions':analyze_training_extensions(results, advanced, now.date().isoformat())}
    out.update(analyze_data_quality(rows, results, advanced, now, source, error))
    # Preserve the last complete report when the live CSV cannot be read.
    if source != 'live_csv':
        raise RuntimeError('RPE CSV unavailable: refusing to overwrite last good report: ' + str(error))
    Path('crossfit_insights.json').write_text(json.dumps(out,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'generated_at':out['generated_at'],'sheet_source':source,'sheet_rows':len(rows),'activities':len(results),'warning':error},ensure_ascii=False))

if __name__=='__main__': main()
