"""Conservative CrossFit extensions: metcon work, comparable benchmarks and recovery context."""
from collections import defaultdict
from datetime import date, timedelta
import math
import re


def n(value):
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == '': return None
        v = float(str(value).replace(',', '.'))
        return v if math.isfinite(v) else None
    except (ValueError, TypeError): return None


def d(value):
    try: return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError): return None


def metcon(activities, today):
    """Only count explicit structured completed movements, never infer rounds from prose."""
    entries=[]
    for a in activities:
        for block in a.get('manual_blocks', []):
            obj=block.get('detail_json') or {}
            if not isinstance(obj, dict): continue
            # Accepted explicit schema: completed_movements: [{name,reps,load_kg?,distance_m?}]
            moves=obj.get('completed_movements')
            if not isinstance(moves, list): continue
            for move in moves:
                if not isinstance(move, dict): continue
                reps=n(move.get('reps'))
                distance=n(move.get('distance_m'))
                load=n(move.get('load_kg'))
                if reps is None and distance is None: continue
                entries.append({'date':a.get('date'),'activity_id':a.get('activity_id'),
                    'movement':str(move.get('name') or 'sin nombre'),
                    'verified_reps':int(reps) if reps is not None and reps >= 0 and reps.is_integer() else None,
                    'verified_distance_m':round(distance,1) if distance is not None and distance>=0 else None,
                    'declared_load_kg':load if load is not None and load>=0 else None})
    windows={}
    for days in (7,28):
        start=today-timedelta(days=days-1)
        relevant=[e for e in entries if d(e['date']) and start<=d(e['date'])<=today]
        groups=defaultdict(lambda:{'reps':0,'distance_m':0,'entries':0})
        for e in relevant:
            g=groups[e['movement'].casefold()]
            g['entries']+=1
            g['reps']+=e['verified_reps'] or 0
            g['distance_m']+=e['verified_distance_m'] or 0
        windows[str(days)+'d']={k:{**v,'distance_m':round(v['distance_m'],1)} for k,v in groups.items()}
    return {'entries':entries,'movement_work':windows,'coverage':'Only completed_movements explicitly provided in structured JSON; older narrative WODs not counted',
            'note':'Repetitions are movement exposure, not an estimate of muscular force or tonnage.'}


def performance(activities):
    """Benchmark comparisons require explicit benchmark_id and equivalent prescribed workout."""
    groups=defaultdict(list)
    for a in activities:
        for block in a.get('manual_blocks',[]):
            obj=block.get('detail_json') or {}
            if not isinstance(obj,dict): continue
            benchmark=str(obj.get('benchmark_id') or '').strip()
            variant=str(obj.get('benchmark_variant') or '').strip()
            if not benchmark or not variant: continue
            result=obj.get('benchmark_result') or {}
            if not isinstance(result,dict): continue
            metric=str(result.get('metric') or '')
            value=n(result.get('value'))
            if metric not in ('time_seconds','reps','load_kg','distance_m') or value is None or value<0: continue
            groups[(benchmark.casefold(),variant.casefold(),metric)].append({'date':a.get('date'),'activity_id':a.get('activity_id'), 'value':value,'rpe':block.get('rpe')})
    comparisons=[]
    for (benchmark,variant,metric),samples in groups.items():
        samples.sort(key=lambda x:(str(x['date']),str(x['activity_id'])))
        if len(samples)<2: continue
        first,last=samples[0],samples[-1]
        delta=round(last['value']-first['value'],2)
        improvement= -delta if metric=='time_seconds' else delta
        comparisons.append({'benchmark_id':benchmark,'variant':variant,'metric':metric,'samples':len(samples),
            'first':first,'latest':last,'absolute_change':delta,'direction':'improved' if improvement>0 else ('worse' if improvement<0 else 'unchanged'),
            'rpe_comparison':'descriptive_only; effort and conditions may differ'})
    return {'comparisons':comparisons,'eligible_benchmarks':len(groups),
            'note':'Only explicitly matching benchmark_id, benchmark_variant and metric are compared; no equivalence inferred from names.'}


def recovery(activities,advanced):
    response=advanced.get('training_response_24_48h')
    baseline=advanced.get('baselines_by_context') or {}
    contexts={}
    for a in activities:
        key=a.get('context') or 'unknown'
        contexts[key]=contexts.get(key,0)+1
    return {'existing_24_48h':response if isinstance(response,(dict,list)) else None,
        'available_context_baseline_days':{k:v.get('days') for k,v in baseline.items() if isinstance(v,dict)} if isinstance(baseline,dict) else {},
        'recorded_activities_by_shift_context':contexts,
        'confidence':'descriptive_only',
        'limitations':['Do not attribute HRV or sleep changes causally to a specific workout or shift',
            'Use actual measurement dates and sleep windows from upstream analytics',
            'Small and uneven context groups cannot establish a personal baseline']}


def analyze(activities,advanced,as_of):
    today=d(as_of)
    return {'metcon_exposure':metcon(activities,today),
            'performance_trends':performance(activities),
            'recovery_context':recovery(activities,advanced),
            'version':'1.0; conservative structured data only'}
