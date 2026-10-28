"""Conservative strength and muscular-load insights from explicit manual sets.

No inferred sets, no invented pain scores, no diagnosis, and no mixing
cardiovascular TRIMP with external muscular volume.
"""
from collections import defaultdict
from datetime import date, timedelta
import math

PATTERNS = {
    # V8.7: los olímpicos primero (un squat clean es halterofilia, no sentadilla) y los tirones con sus nombres habituales
    'olympic_lift': ('clean', 'snatch', 'jerk', 'arrancada', 'cargada', 'envion', 'envión'),
    'hinge': ('peso muerto', 'deadlift', 'rdl', 'romanian deadlift', 'good morning', 'kettlebell swing'),
    'squat': ('sentadilla', 'squat', 'thruster', 'wall ball', 'goblet squat',
              'prensa horizontal', 'prensa de piernas', 'prensa inclinada', 'leg press'),
    'knee_flexion': ('curl femoral', 'curl de isquios', 'leg curl', 'hamstring curl'),
    'chest_isolation': ('aperturas', 'chest fly', 'pec deck', 'crossover'),
    'biceps_isolation': ('curl de bíceps', 'curl bíceps', 'curl de biceps', 'curl biceps', 'bicep curl', 'biceps curl', 'curl martillo'),
    'triceps_isolation': ('tríceps', 'triceps', 'pressdown', 'extensión de codo'),
    'horizontal_push': ('bench press', 'press banca', 'press de pecho', 'press inclinado',
                        'press superinclinado', 'chest press', 'push-up', 'flexion',
                        'floor press', 'fondos de pecho', 'chest dips'),
    'vertical_push': ('shoulder press', 'strict press', 'push press', 'press militar'),
    'vertical_pull': ('pull-up', 'pull up', 'pullup', 'chin up', 'chin-up', 'dominada', 'chest-to-bar', 'jalón', 'lat pulldown'),
    'horizontal_pull': ('remo', 'ring row', 'bent-over row', 'barbell row', 'dumbbell row'),
    'single_leg': ('lunge', 'zancada', 'split squat', 'step-up'),
    'core': ('sit-up', 'situp', 'plank', 'plancha', 'abdominales', 'hollow'),
}

def equipment_for(exercise):
    """Separate free-weight, selectorized-machine, and bodyweight measures."""
    unit = str(exercise.get('load_unit') or '').casefold()
    if unit == 'kg_total_dos_mancuernas': return 'dumbbell_pair'
    if unit == 'kg_total_barra': return 'barbell'
    if unit == 'kg_total_dos_lados': return 'plate_loaded_machine'
    if unit == 'kg_indicado_maquina': return 'machine_stack'
    if unit == 'peso_corporal': return 'bodyweight'
    return 'unspecified'

def num(v):
    try:
        if v is None or isinstance(v, bool) or str(v).strip() == '': return None
        n = float(str(v).replace(',', '.'))
        return n if math.isfinite(n) else None
    except (ValueError, TypeError): return None

def classify(name):
    n = str(name or '').casefold()
    return next((p for p, words in PATTERNS.items() if any(w in n for w in words)), 'other')

def strength_estimate(sets, equipment):
    """Estimate free-weight strength only with explicit set-level RIR.

    Session RPE must never be used as a per-set RIR estimate. Machine-stack
    kilograms are not a mechanically comparable barbell 1RM.
    """
    if equipment not in ('barbell', 'dumbbell_pair'):
        return None, 'unsupported_equipment'
    best = None
    status = 'set_effort_not_reported'
    for item in sets:
        if not isinstance(item, dict):
            continue
        reps = num(item.get('reps'))
        kg = num(item.get('load_kg'))
        if kg is None:
            kg = num(item.get('weight_kg'))
        if reps is None or kg is None or reps <= 0 or kg <= 0 or reps > 10:
            continue
        rir = num(item.get('reps_in_reserve'))
        if rir is None:
            rir = num(item.get('rir'))
        if rir is None:
            set_rpe = num(item.get('set_rpe'))
            if set_rpe is not None and 0 <= set_rpe <= 10:
                rir = 10 - set_rpe
        if rir is None and item.get('confirmed_to_failure') is True:
            rir = 0
        if rir is None:
            continue
        if rir < 0 or rir > 2 or reps + rir > 10:
            status = 'set_not_near_failure'
            continue
        estimate = kg * (1 + (reps + rir) / 30)
        best = max(best or 0, estimate)
        status = 'eligible'
    return (round(best, 1) if best is not None else None), status


def epley_lower_bound(sets, equipment):
    """1RM MÍNIMO por Epley con la mejor serie (kg y repeticiones), sin RIR.

    Si la serie no llegó al fallo, el 1RM real es igual o mayor: por eso es un límite
    inferior y no sustituye a ``estimated_1rm_kg`` (que exige RIR explícito). Nunca usa
    el RPE de la sesión. Solo barra o par de mancuernas y series de 1–10 repeticiones.
    """
    if equipment not in ('barbell', 'dumbbell_pair'):
        return None, None, None
    best = None
    for item in sets or []:
        if not isinstance(item, dict):
            continue
        reps = num(item.get('reps'))
        kg = num(item.get('load_kg'))
        if kg is None:
            kg = num(item.get('weight_kg'))
        if reps is None or kg is None or reps < 1 or reps > 10 or kg <= 0:
            continue
        estimate = kg * (1 + reps / 30) if reps > 1 else kg
        if best is None or estimate > best[0]:
            best = (estimate, kg, int(reps) if float(reps).is_integer() else reps)
    if best is None:
        return None, None, None
    return round(best[0], 1), best[1], best[2]


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
                # V8.2: un registro de un solo ejercicio lo nombra en «exercise»; el título de la sesión es el último recurso
                name = str(exercise.get('name') or exercise.get('exercise') or block.get('activity') or 'Sin nombre')
                pattern = classify(name)
                equipment = equipment_for(exercise)
                external_expected = equipment != 'bodyweight'
                known_volume = 0.0
                known_sets = total_sets = 0
                best_e1rm, estimate_status = strength_estimate(exercise.get('sets', []), equipment)
                e1rm_min, top_kg, top_reps = epley_lower_bound(exercise.get('sets', []), equipment)
                peak_load = None
                for item in exercise.get('sets', []):
                    if not isinstance(item, dict) or item.get('bar_empty'): continue  # V8.7: barra vacía fuera, como en la app
                    count = num(item.get('count'))
                    count = int(count) if count is not None and count >= 1 and count.is_integer() else 1
                    total_sets += count
                    reps = num(item.get('reps'))
                    kg = num(item.get('load_kg'))
                    if kg is None: kg = num(item.get('weight_kg'))
                    if reps is None or reps <= 0 or kg is None or kg <= 0: continue
                    known_sets += count
                    known_volume += reps * kg * count
                    peak_load = max(peak_load or 0, kg)
                if total_sets:
                    sessions.append({'date':day.isoformat(), 'activity_id':a.get('activity_id'),
                        'exercise':name, 'movement_pattern':pattern,
                        'equipment':equipment, 'load_unit':exercise.get('load_unit'),
                        'external_load_applicable':external_expected,
                        'verified_volume_kg':round(known_volume, 1) if known_sets else None,
                        'known_sets':known_sets, 'total_sets':total_sets,
                        'volume_complete':(known_sets == total_sets) if external_expected else None,
                        'volume_status':('complete' if known_sets == total_sets else 'partial')
                                         if external_expected else 'bodyweight_no_external_load',
                        'peak_declared_load_kg':peak_load,
                        'laterality_unconfirmed':bool(exercise.get('reps_per_leg_unconfirmed')),
                        'estimated_1rm_kg':best_e1rm,
                        'estimated_1rm_status':estimate_status,
                        'estimated_1rm_method':('Epley using explicit set RIR (0-2); approximate' if best_e1rm is not None else None),
                        'top_set_kg':top_kg, 'top_set_reps':top_reps, 'e1rm_min_kg':e1rm_min,
                        'e1rm_min_method':('Epley sin RIR: limite inferior' if e1rm_min is not None else None),
                        'rpe':block.get('rpe'), 'pain':pain(obj)})
    windows = {}
    equipment_windows = {}
    for days in (7, 28):
        cutoff = today - timedelta(days=days-1)
        relevant = [s for s in sessions if date.fromisoformat(s['date']) >= cutoff]
        groups = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,'total_sets':0,'sessions':0})
        separate = defaultdict(lambda: {'verified_volume_kg':0.0,'known_sets':0,
                                        'external_sets_expected':0,'total_sets':0,'sessions':0})
        for s in relevant:
            g = groups[s['movement_pattern']]
            g['sessions'] += 1
            g['known_sets'] += s['known_sets']
            g['total_sets'] += s['total_sets']
            g['verified_volume_kg'] += s['verified_volume_kg'] or 0
            key = s['movement_pattern'] + ':' + s['equipment']
            x = separate[key]
            x['sessions'] += 1
            x['known_sets'] += s['known_sets']
            x['total_sets'] += s['total_sets']
            x['external_sets_expected'] += s['total_sets'] if s['external_load_applicable'] else 0
            x['verified_volume_kg'] += s['verified_volume_kg'] or 0
        windows[str(days)+'d'] = {
            k: {**v,'verified_volume_kg':round(v['verified_volume_kg'],1),
                'volume_complete':v['known_sets']==v['total_sets'],
                'mixed_equipment_caution':True} for k,v in groups.items()}
        equipment_windows[str(days)+'d'] = {
            k: {**v,'verified_volume_kg':round(v['verified_volume_kg'],1),
                'volume_complete':v['known_sets']==v['external_sets_expected']}
            for k,v in separate.items()}
    best = {}
    for s in sessions:
        if s['estimated_1rm_kg'] is not None:
            key = (s['exercise'].casefold(), s['equipment'])
            if key not in best or s['estimated_1rm_kg'] > best[key]['estimated_1rm_kg']:
                best[key] = {'exercise':s['exercise'],'equipment':s['equipment'],
                    'load_unit':s['load_unit'],'date':s['date'],
                    'estimated_1rm_kg':s['estimated_1rm_kg']}
    return {'as_of_date':today.isoformat(), 'source':'explicit manual strength sets only',
        'strength_exercises':sessions, 'movement_pattern_load':windows,
        'movement_pattern_load_by_equipment':equipment_windows,
        'best_estimated_1rm_by_exercise':list(best.values()),
        'limitations':['Unknown loads excluded from verified volume',
          'Patterns are exercise categories, not isolated muscle-group loads',
          'Mixed-equipment totals are not directly comparable; use load_by_equipment',
          'Bodyweight sets do not imply external weight-volume',
          'Machine-stack loads are not comparable to barbell loads',
          'Metcon repetitions and loads are not counted as strength sets',
          '7/28-day comparisons need adequate recorded history',
          'Pain is only included when explicitly reported as structured 0-10 values',
          'Estimated 1RM requires explicitly reported set-level RIR (0-2), not session RPE',
          'Machine loads are descriptive and are not used for free-weight 1RM',
          'Unilateral exercises with unknown side assignment are never doubled']}
