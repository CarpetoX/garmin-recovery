"""CrossFit extensions v2.4.11: only explicit completed work is quantified.

Never infer executed work from prescribed rounds, time caps or narrative notes.
Keep movement exposure separate from strength tonnage and physiological load.
"""
from collections import defaultdict
from datetime import date, timedelta
import math
import re


def n(value):
    try:
        if value is None or isinstance(value, bool) or str(value).strip() == '':
            return None
        result = float(str(value).replace(',', '.'))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def d(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _valid_reps(value):
    value = n(value)
    return int(value) if value is not None and value >= 0 and value.is_integer() else None


def _valid_distance(value):
    value = n(value)
    return round(value, 1) if value is not None and value >= 0 else None


def _declared_load(value):
    value = n(value)
    return value if value is not None and value >= 0 else None


# These mappings identify an explicitly recorded field, NOT a prescribed amount.
# All quantities still come exclusively from the performed.totals dictionary.
TOTAL_FIELD_NAMES = {
    'run_m': 'carrera',
    'running_m': 'carrera',
    'row_m': 'remo',
    'bike_m': 'bicicleta',
    'thruster_reps': 'thruster alterno con mancuerna',
    'toes_to_bar_reps': 'toes-to-bar',
    'devil_press_reps': 'devil press alterno con mancuerna',
    'hspu_reps': 'handstand push-up',
    'front_squat_reps': 'sentadilla frontal',
}


def _movement_from_total(field, prescribed):
    """Name a reported performed total; never derive its count from prescription."""
    if field in TOTAL_FIELD_NAMES:
        return TOTAL_FIELD_NAMES[field]
    token = re.sub(r'_(reps|m)$', '', field).replace('_', ' ').strip()
    if not token:
        return None
    # For a new key, require an explicit matching exercise in the prescription.
    for exercise in prescribed:
        if isinstance(exercise, dict):
            name = str(exercise.get('name') or '').strip()
            basic = re.sub(r'[^a-z0-9]+', ' ', name.casefold()).strip()
            candidate = re.sub(r'[^a-z0-9]+', ' ', token.casefold()).strip()
            if basic == candidate or basic.startswith(candidate + ' '):
                return name
    return None


def _iter_reported_movements(obj):
    """Yield (movement, repetitions, metres, load, evidence).

    Preference: explicit completed_movements > performed.totals > completed 21-15-9
    per-exercise count. Alternative schemas are never combined for one WOD.
    """
    direct = obj.get('completed_movements')
    performed = obj.get('performed') if isinstance(obj.get('performed'), dict) else {}
    if not isinstance(direct, list):
        direct = performed.get('completed_movements')
    if isinstance(direct, list):
        for move in direct:
            if not isinstance(move, dict):
                continue
            reps = _valid_reps(move.get('reps'))
            distance = _valid_distance(move.get('distance_m'))
            name = str(move.get('name') or '').strip()
            if name and (reps is not None or distance is not None):
                yield name, reps, distance, _declared_load(move.get('load_kg')), 'completed_movements'
        return

    totals = performed.get('totals')
    if isinstance(totals, dict):
        prescribed = obj.get('prescribed_round')
        prescribed = prescribed if isinstance(prescribed, list) else []
        for key, value in totals.items():
            if not isinstance(key, str):
                continue
            if key.endswith('_reps'):
                reps, distance = _valid_reps(value), None
            elif key.endswith('_m'):
                reps, distance = None, _valid_distance(value)
            else:
                continue
            name = _movement_from_total(key, prescribed)
            if name and (reps is not None or distance is not None):
                yield name, reps, distance, None, 'performed.totals'
        return

    # e.g. completed 21-15-9: 45 reps OF EACH explicitly listed exercise.
    # A time cap without completed=true cannot be used as proof of completion.
    if performed.get('completed') is True:
        count = _valid_reps(performed.get('total_reps_each_exercise'))
        exercises = obj.get('exercises')
        if count is not None and isinstance(exercises, list):
            for exercise in exercises:
                if not isinstance(exercise, dict):
                    continue
                name = str(exercise.get('name') or '').strip()
                if name:
                    yield name, count, None, _declared_load(exercise.get('load_kg')), 'performed.completed_exercises'


def metcon(activities, today):
    """Aggregate explicit performed work, never a prescription or assumed round."""
    entries = []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        for block in activity.get('manual_blocks', []):
            if not isinstance(block, dict):
                continue
            obj = block.get('detail_json') or {}
            if not isinstance(obj, dict):
                continue
            for name, reps, distance, load, evidence in _iter_reported_movements(obj):
                entries.append({
                    'date': activity.get('date'),
                    'activity_id': activity.get('activity_id'),
                    'movement': name,
                    'verified_reps': reps,
                    'verified_distance_m': distance,
                    'declared_load_kg': load,
                    'evidence': evidence,
                    'time_cap_minutes': n(obj.get('time_cap_minutes')),
                    'recorded_garmin_minutes': n(obj.get('recorded_garmin_minutes')),
                })
    windows = {}
    for days in (7, 28):
        start = today - timedelta(days=days-1) if today is not None else None
        relevant = [e for e in entries if start is not None and d(e['date']) and start <= d(e['date']) <= today]
        groups = defaultdict(lambda: {'reps': 0, 'distance_m': 0., 'entries': 0})
        for entry in relevant:
            group = groups[entry['movement'].casefold()]
            group['entries'] += 1
            group['reps'] += entry['verified_reps'] or 0
            group['distance_m'] += entry['verified_distance_m'] or 0
        windows[f'{days}d'] = {
            movement: {**stats, 'distance_m': round(stats['distance_m'], 1)}
            for movement, stats in groups.items()
        }
    return {
        'entries': entries,
        'movement_work': windows,
        'coverage': 'Explicit completed_movements, performed.totals or a confirmed completed per-exercise total; no prescribed-only extrapolation',
        'note': 'Repetitions and distance represent exposure, never estimated force, effective tonnage or medical fatigue.',
    }


def performance(activities):
    """Benchmark comparisons require explicit benchmark_id and equivalent variant."""
    groups = defaultdict(list)
    for a in activities:
        for block in a.get('manual_blocks', []):
            obj = block.get('detail_json') or {}
            if not isinstance(obj, dict):
                continue
            benchmark = str(obj.get('benchmark_id') or '').strip()
            variant = str(obj.get('benchmark_variant') or '').strip()
            if not benchmark or not variant:
                continue
            result = obj.get('benchmark_result') or {}
            if not isinstance(result, dict):
                continue
            metric = str(result.get('metric') or '')
            value = n(result.get('value'))
            if metric not in ('time_seconds', 'reps', 'load_kg', 'distance_m') or value is None or value < 0:
                continue
            groups[(benchmark.casefold(), variant.casefold(), metric)].append({
                'date': a.get('date'), 'activity_id': a.get('activity_id'),
                'value': value, 'rpe': block.get('rpe'),
            })
    comparisons = []
    for (benchmark, variant, metric), samples in groups.items():
        samples.sort(key=lambda x: (str(x['date']), str(x['activity_id'])))
        if len(samples) < 2:
            continue
        first, last = samples[0], samples[-1]
        delta = round(last['value']-first['value'], 2)
        improvement = -delta if metric == 'time_seconds' else delta
        comparisons.append({
            'benchmark_id': benchmark, 'variant': variant, 'metric': metric,
            'samples': len(samples), 'first': first, 'latest': last,
            'absolute_change': delta,
            'direction': 'improved' if improvement > 0 else ('worse' if improvement < 0 else 'unchanged'),
            'rpe_comparison': 'descriptive_only; effort and conditions may differ',
        })
    return {
        'comparisons': comparisons, 'eligible_benchmarks': len(groups),
        'note': 'Only explicitly matching benchmark_id, benchmark_variant and metric are compared; no equivalence inferred from names.',
    }


def recovery(activities, advanced):
    response = advanced.get('training_response_24_48h')
    baseline = advanced.get('baselines_by_context') or {}
    contexts = {}
    for a in activities:
        key = a.get('context') or 'unknown'
        contexts[key] = contexts.get(key, 0)+1
    return {
        'existing_24_48h': response if isinstance(response, (dict, list)) else None,
        'available_context_baseline_days': {k: v.get('days') for k, v in baseline.items() if isinstance(v, dict)} if isinstance(baseline, dict) else {},
        'recorded_activities_by_shift_context': contexts,
        'confidence': 'descriptive_only',
        'limitations': [
            'Do not attribute HRV or sleep changes causally to a specific workout or shift',
            'Use actual measurement dates and sleep windows from upstream analytics',
            'Small and uneven context groups cannot establish a personal baseline',
        ],
    }



def performance_report(activities, advanced, today, benchmarks):
    """Evidence-based coaching summary; no invented benchmark equivalence.

    Garmin/Intervals/TRIMP and duration*RPE are separate load units. Recorded
    machine/dumbbell/barbell kilograms are exposure descriptors, not a common
    physiological workload or directly comparable mechanical tonnage.
    """
    groups = {}
    if today is None:
        return {'status': 'date_unavailable', 'interpretation': 'insufficient_data'}
    for key in ('recent_7d', 'previous_7d', 'recent_28d'):
        groups[key] = {
            'sessions': 0, 'sessions_with_rpe': 0, 'rpe_total': 0.0,
            'high_rpe_sessions': 0, 'recorded_duration_minutes': 0.0,
            'sessions_with_duration': 0,
            'srpe_from_recorded_duration': 0.0, 'srpe_sessions': 0,
            'minimum_recorded_external_volume_kg': 0.0,
            'strength_blocks_with_quantified_weight': 0,
            'strength_blocks_missing_quantified_weight': 0,
            'garmin_intervals_load_separate': 0.0,
            'intervals_load_sessions': 0,
            'trimp_separate': 0.0, 'trimp_sessions': 0,
        }
    daily = {}
    latest = None
    eligible = []
    for a in activities:
        if not isinstance(a, dict):
            continue
        on = d(a.get('date'))
        if on is None:
            continue
        age = (today - on).days
        if age < 0 or age >= 28:
            continue
        eligible.append(a)
        bucket_names = ['recent_28d']
        if age <= 6:
            bucket_names.append('recent_7d')
        elif age <= 13:
            bucket_names.append('previous_7d')
        rpe = n(a.get('rpe_used'))
        if rpe is not None and not 0 <= rpe <= 10:
            rpe = None
        minutes = n(a.get('recorded_minutes'))
        if minutes is not None and minutes < 0:
            minutes = None
        srpe = n(a.get('srpe_using_recorded_minutes'))
        if srpe is not None and srpe < 0:
            srpe = None
        loads = a.get('internal_load_not_additive') or {}
        intervals_load = n(loads.get('intervals_load'))
        trimp = n(loads.get('trimp'))
        blocks = a.get('manual_blocks') or []
        quantified = [n(b.get('minimum_verified_volume_kg')) for b in blocks if isinstance(b, dict)]
        vol = sum(value for value in quantified if value is not None and value >= 0)
        known = sum(1 for v in quantified if v is not None and v >= 0)
        unknown = sum(1 for v in quantified if v is None)
        for name in bucket_names:
            group = groups[name]
            group['sessions'] += 1
            if rpe is not None:
                group['sessions_with_rpe'] += 1
                group['rpe_total'] += rpe
                group['high_rpe_sessions'] += int(rpe >= 8)
            if minutes is not None:
                group['recorded_duration_minutes'] += minutes
                group['sessions_with_duration'] += 1
            if srpe is not None:
                group['srpe_from_recorded_duration'] += srpe
                group['srpe_sessions'] += 1
            group['minimum_recorded_external_volume_kg'] += vol
            group['strength_blocks_with_quantified_weight'] += known
            group['strength_blocks_missing_quantified_weight'] += unknown
            if intervals_load is not None:
                group['garmin_intervals_load_separate'] += intervals_load
                group['intervals_load_sessions'] += 1
            if trimp is not None:
                group['trimp_separate'] += trimp
                group['trimp_sessions'] += 1
        if age <= 6:
            item = daily.setdefault(on.isoformat(), {'sessions': 0, 'rpe_sum': 0.0,
                            'rpe_count': 0, 'recorded_minutes': 0.0,
                            'srpe_from_recorded_duration': 0.0})
            item['sessions'] += 1
            if rpe is not None:
                item['rpe_count'] += 1
                item['rpe_sum'] += rpe
            if minutes is not None:
                item['recorded_minutes'] += minutes
            if srpe is not None:
                item['srpe_from_recorded_duration'] += srpe
    for name, group in groups.items():
        group['mean_recorded_rpe'] = (
            round(group['rpe_total'] / group['sessions_with_rpe'], 2)
            if group['sessions_with_rpe'] else None)
        del group['rpe_total']
        for fld in ('recorded_duration_minutes', 'srpe_from_recorded_duration',
                    'minimum_recorded_external_volume_kg',
                    'garmin_intervals_load_separate', 'trimp_separate'):
            group[fld] = round(group[fld], 1)
    from datetime import timedelta
    chronological = []
    for age in range(6, -1, -1):
        key = (today - timedelta(days=age)).isoformat()
        record = daily.get(key, {'sessions': 0, 'rpe_count': 0, 'rpe_sum': 0,
                                 'recorded_minutes': 0, 'srpe_from_recorded_duration': 0})
        chronological.append({'date': key, 'sessions': record['sessions'],
                              'mean_recorded_rpe': round(record['rpe_sum']/record['rpe_count'], 2)
                              if record['rpe_count'] else None,
                              'recorded_minutes': round(record['recorded_minutes'], 1),
                              'srpe_from_recorded_duration': round(record['srpe_from_recorded_duration'], 1)})
    if eligible:
        latest = max(eligible, key=lambda x: (str(x.get('date')), str(x.get('activity_id'))))
    last = None
    if latest is not None:
        last = {'date': latest.get('date'), 'activity_id': latest.get('activity_id'),
                'name': latest.get('name'), 'rpe': n(latest.get('rpe_used')),
                'recorded_minutes': n(latest.get('recorded_minutes')),
                'heart_rate': latest.get('heart_rate'),
                'manual_blocks_recorded': len(latest.get('manual_blocks') or [])}
    recovery = advanced.get('recovery_assessment_v2') or {}
    rec_state = recovery.get('state')
    rec_status = recovery.get('status')
    recommendations = []
    if rec_state != 'assessed':
        recommendations.append({'code': 'recovery_unconfirmed',
            'text': 'Esperar al sueño y HRV confirmados antes de fijar intensidad; decidir con sensaciones y calentamiento.'})
    elif rec_status == 'red':
        recommendations.append({'code': 'recovery_red',
            'text': 'Valorar descarga, técnica o actividad suave; evitar máximos según síntomas y calentamiento.'})
    elif rec_status == 'yellow':
        recommendations.append({'code': 'recovery_yellow',
            'text': 'Individualizar intensidad y revisar calentamiento, fatiga y RPE antes de subir cargas.'})
    else:
        recommendations.append({'code': 'recovery_context',
            'text': 'Usar recuperación junto con objetivos de entrenamiento, síntomas y rendimiento, no como permiso automático para hacer máximos.'})
    if groups['recent_7d']['high_rpe_sessions'] >= 3:
        recommendations.append({'code': 'frequent_high_rpe',
            'text': 'Registrar recuperación 24-48 h y ajustar volumen si coinciden fatiga o bajada del rendimiento; no asumir sobreentrenamiento.'})
    if not benchmarks['comparisons']:
        recommendations.append({'code': 'benchmark_history_incomplete',
            'text': 'Repetir algún WOD con misma variante, cargas y estándares para comparar tiempos o repeticiones objetivamente.'})
    recent, previous = groups['recent_7d'], groups['previous_7d']
    comparable = recent['sessions'] >= 2 and previous['sessions'] >= 2
    return {
        'status': 'descriptive_ready' if eligible else 'insufficient_data',
        'as_of_date': today.isoformat(),
        'window_summaries': groups,
        'daily_chart_7d': chronological,
        'latest_session': last,
        'previous_week_context': {
            'sufficient_for_descriptive_comparison': comparable,
            'session_count_change': recent['sessions'] - previous['sessions'] if comparable else None,
            'mean_rpe_change': round(recent['mean_recorded_rpe']-previous['mean_recorded_rpe'], 2)
                if comparable and recent['mean_recorded_rpe'] is not None
                and previous['mean_recorded_rpe'] is not None else None,
            'note': 'El cambio de número de sesiones o RPE no demuestra mejora física ni equivalencia de entrenamiento.'},
        'benchmark_comparisons': benchmarks['comparisons'],
        'recovery_context': {'state': rec_state or 'unavailable',
                             'status': rec_status or 'unavailable',
                             'confidence': recovery.get('confidence')},
        'recommendations': recommendations,
        'data_confidence': 'limited' if not comparable else 'descriptive',
        'limitations': [
            'Los pesos de barra, máquina y mancuerna no son comparables como fuerza externa equivalente.',
            'Volumen cuantificado es un mínimo declarado: no incluye ejercicios sin peso conocido.',
            'No se suman TRIMP, carga Intervals, carga Garmin ni sRPE entre unidades distintas.',
            'Duración Garmin grabada no es duración efectiva del WOD.',
            'No usar planificados como realizados ni asumir rondas no confirmadas.',
            'Las correlaciones de 24-48h no prueban causalidad y las referencias iniciales son provisionales.'
        ]
    }


def analyze(activities, advanced, as_of):
    today = d(as_of)
    benchmark_results = performance(activities)
    return {
        'metcon_exposure': metcon(activities, today),
        'performance_trends': benchmark_results,
        'recovery_context': recovery(activities, advanced),
        'performance_report': performance_report(activities, advanced, today, benchmark_results),
        'version': '2.5; coaching insights with verified comparisons',
    }
