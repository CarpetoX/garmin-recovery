"""Conservative strength and muscular-load insights from explicit manual sets.

No inferred sets, no invented pain scores, no diagnosis, and no mixing
cardiovascular TRIMP with external muscular volume.
"""
from collections import defaultdict
from datetime import date, timedelta
import math

PATTERNS = {
    'hinge': ('peso muerto', 'deadlift', 'rdl', 'romanian deadlift', 'good morning', 'kettlebell swing'),
    'squat': ('sentadilla', 'squat', 'thruster', 'wall ball', 'goblet squat'),
    'horizontal_push': ('bench press', 'press banca', 'push-up', 'flexion', 'floor press'),
    'vertical_push': ('shoulder press', 'strict press', 'push press', 'press militar', 'jerk'),
    'vertical_pull': ('pull-up', 'dominada', 'chest-to-bar', 'toes-to-bar'),
    'horizontal_pull': ('remo', 'bent-over row', 'barbell row', 'dumbbell row'),
    'olympic_lift': ('clean', 'snatch', 'arrancada', 'cargada'),
    'single_leg': ('lunge', 'zancada', 'split squat', 'step-up'),
}

def num(v):
    try:
        if v is None or isinstance(v, bool) or str(v).strip() == '': return None
        n = float(str(v).replace(',', '.'))
        return n if math.isfinite(n) else None
    except (ValueError, TypeError): return None

def classify(name):
    n = str(name or '').casefold()
    return next((p for p, words in PATTERNS.items() if any(w in n for w in words)), 'other')

def pain(obj):
    """Only accept explicit numeric 0-10 pain entries; no inference from notes."""
    if not isinstance(obj, dict): return None
    result = {}
    for key in ('pain_during_0_10', 'pain_after_0_10', 'pain_next_day_0_10'):
        v = num(obj.get(key))
        if v is not None and 0 <= v <= 10: result[key] = v
    return result or None

def analyze(activities, as_of):
    today = date.fromisoformat(as_of)
    sessions = []
    for a in activities:
        try: day = date.fromisoformat(str(a.get('date'))[:10])
        except (TypeError, ValueError): continue
        if day > today: continue
        for block in a.get('manual_blocks', []):
            obj = block.get('detail_json') or {}
            if not isinstance(obj, dict): continue
            exercises = obj.get('exercises')
            groups = exercises if isinstance(exercises, list) else ([obj] if isinstance(obj.get('sets'), list) else [])
            for exercise in groups:
                if not isinstance(exercise, dict): continue
                name = str(exercise.get('name') or block.get('activity') or 'Sin nombre')
                pattern = classify(name)
                known_volume = 0.0
                known_sets = total_sets = 0
                best_e1rm = None
                for item in exercise.get('sets', []):
                    if not isinstance(item, dict): continue
                    count = num(item.get('count'))
                    count = int(count) if count is not None and count >= 1 and count.is_integer() else 1
                    total_sets += count
                    reps = num(item.get('reps'))
                    kg = num(item.get('load_kg'))
                    if kg is None: kg = num(item.get('weight_kg'))
                    if reps is None or reps <= 0 or kg is None or kg <= 0: continue
                    known_sets += count
                    known_volume += reps * kg * count
                    if reps <= 10:
                        estimate = kg * (1 + reps / 30)
                        best_e1rm = max(best_e1rm or 0, estimate)
                if total_sets:
                    sessions.append({'date':day.isoformat(), 'activity_id':a.get('activity_id'),
                        'exercise':name, 'movement_pattern':pattern,
                        'verified_volume_kg':round(known_volume, 1) if known_sets else None,
                        'known_sets':known_sets, 'total_sets':total_sets,
                        'volume_complete':known_sets == total_sets,
                        'estimated_1rm_kg':round(best_e1rm, 1) if best_e1rm else None,
                        'estimated_1rm_method':'Epley, reps <= 10; approximate, not tested 1RM' if best_e1rm else None,
                        'rpe':block.get('rpe'), 'pain':pain(obj)})
    windows = {}
    for days in (7, 28):
        cutoff = today - timedelta(days=days-1)
        relevant = [s for s in sessions if date.fromisoformat(s['date']) >= cutoff]
        groups = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,'total_sets':0,'sessions':0})
        for s in relevant:
            g = groups[s['movement_pattern']]
            g['sessions'] += 1
            g['known_sets'] += s['known_sets']
            g['total_sets'] += s['total_sets']
            g['verified_volume_kg'] += s['verified_volume_kg'] or 0
        windows[str(days)+'d'] = {
            k: {**v,'verified_volume_kg':round(v['verified_volume_kg'],1),
                'volume_complete':v['known_sets']==v['total_sets']} for k,v in groups.items()}
    best = {}
    for s in sessions:
        if s['estimated_1rm_kg'] is not None:
            key = s['exercise'].casefold()
            if key not in best or s['estimated_1rm_kg'] > best[key]['estimated_1rm_kg']:
                best[key] = {'exercise':s['exercise'],'date':s['date'],
                    'estimated_1rm_kg':s['estimated_1rm_kg']}
    return {'as_of_date':today.isoformat(), 'source':'explicit manual strength sets only',
        'strength_exercises':sessions, 'movement_pattern_load':windows,
        'best_estimated_1rm_by_exercise':list(best.values()),
        'limitations':['Unknown loads excluded from verified volume',
          'Patterns are exercise categories, not isolated muscle-group loads',
          'Metcon repetitions and loads are not counted as strength sets',
          '7/28-day comparisons need adequate recorded history',
          'Pain is only included when explicitly reported as structured 0-10 values',
          'Epley estimates are approximate and not directly measured strength']}
