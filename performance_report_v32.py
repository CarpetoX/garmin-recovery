#!/usr/bin/env python3
"""V3.2: informe de rendimiento trazable, sin datos fisiológicos inventados.

Fuentes: crossfit_insights.json (actividades/ejercicios vinculados por ID),
wellness.json (recuperación diaria), daily_summary.json (contexto actual).
No modifica otras fuentes ni realiza peticiones externas.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
import math
from statistics import fmean
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')


def numeric(v):
    """Acepta números JSON finitos; nunca convierte nulos/cadenas a ceros."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def positive(v):
    x = numeric(v)
    return x if x is not None and x > 0 else None


def when(v):
    if not isinstance(v, str):
        return None
    try:
        return date.fromisoformat(v[:10])
    except ValueError:
        return None


def mean(values, decimals=2):
    xs = [numeric(x) for x in values]
    xs = [x for x in xs if x is not None]
    return round(fmean(xs), decimals) if xs else None


def total(values, decimals=1):
    xs = [numeric(x) for x in values]
    xs = [x for x in xs if x is not None]
    return round(sum(xs), decimals) if xs else None


def delta_pct(current, previous):
    a, b = numeric(current), numeric(previous)
    if a is None or b is None or b <= 0:
        return None
    return round(100 * (a - b) / b, 1)


def _activity_rows(items, today):
    """No contar dos veces un mismo ID; si discrepan las copias, avisar."""
    rows = []
    seen = set()
    duplicates = 0
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        d = when(item.get('date'))
        if d is None or d > today or d < today - timedelta(days=27):
            continue
        aid = str(item.get('activity_id') or '').strip()
        # Los IDs ausentes NO autorizan un emparejamiento por fecha.
        if not aid:
            continue
        if aid in seen:
            duplicates += 1
            continue
        seen.add(aid)
        rows.append({**item, '_day': d})
    return rows, duplicates


def _wellness_rows(items, today):
    """Interpretar las fechas como días locales de Intervals/Connect."""
    result = {}
    dup = 0
    for raw in items if isinstance(items, list) else []:
        if not isinstance(raw, dict):
            continue
        d = when(raw.get('id'))
        if d is None or d > today or d < today - timedelta(days=27):
            continue
        if d in result:
            dup += 1
            # Conserva el registro con más señales válidas, no suma mediciones.
            fields = ('hrv', 'restingHR', 'sleepSecs', 'sleepScore', 'avgSleepingHR')
            def score(x, fields=fields):
                return sum(positive(x.get(f)) is not None for f in fields)
            if score(raw) <= score(result[d]):
                continue
        result[d] = raw
    return result, dup


def _window(activities, start, finish):
    rows = [a for a in activities if start <= a['_day'] <= finish]
    rpe = [numeric(a.get('rpe_used')) for a in rows]
    rpe = [x for x in rpe if x is not None and 0 <= x <= 10]
    minutes = [positive(a.get('recorded_minutes')) for a in rows]
    minutes = [x for x in minutes if x is not None]
    # RPE x duración GRABADA, no duración efectiva de WOD.
    srpe = [numeric(a.get('srpe_using_recorded_minutes')) for a in rows]
    srpe = [x for x in srpe if x is not None and x >= 0]
    trimp = []
    for a in rows:
        src = a.get('internal_load_not_additive') or {}
        if isinstance(src, dict):
            x = numeric(src.get('trimp'))
            if x is not None and x >= 0:
                trimp.append(x)
    return {
        'start': start.isoformat(), 'end': finish.isoformat(),
        'sessions': len(rows),
        'sessions_with_rpe': len(rpe),
        'rpe_coverage_pct': round(100 * len(rpe) / len(rows), 1) if rows else None,
        'mean_session_rpe': mean(rpe),
        'recorded_minutes': round(sum(minutes), 1) if minutes else None,
        'recorded_duration_count': len(minutes),
        'srpe_recorded_minutes_proxy': round(sum(srpe), 1) if srpe else None,
        'srpe_count': len(srpe),
        'trimp_total': round(sum(trimp), 1) if trimp else None,
        'trimp_count': len(trimp),
        'shift_context_counts': dict(sorted(Counter(str(a.get('context') or 'unknown') for a in rows).items())),
        'complete_calendar_coverage_verified': False,
    }


def _recovery(wellness, start, finish):
    subset = [x for d, x in wellness.items() if start <= d <= finish]
    def samples(field, divisor=1):
        vals = [positive(x.get(field)) for x in subset]
        vals = [x/divisor for x in vals if x is not None]
        return {'mean': mean(vals), 'days': len(vals)}
    return {
        'start': start.isoformat(), 'end': finish.isoformat(),
        'days_with_any_wellness_row': len(subset),
        'sleep_hours': samples('sleepSecs', 3600),
        'sleep_score': samples('sleepScore'),
        'hrv': samples('hrv'),
        'resting_hr': samples('restingHR'),
        'avg_sleeping_hr': samples('avgSleepingHR'),
    }


def _recovery_delta(now, earlier):
    changes = {}
    for key in ('sleep_hours','sleep_score','hrv','resting_hr','avg_sleeping_hr'):
        a, b = now[key], earlier[key]
        # No hacer tendencias con muestras de 1–3 días por semana.
        adequate = a['days'] >= 4 and b['days'] >= 4
        changes[key] = {
            'delta_mean': round(a['mean'] - b['mean'], 2) if adequate and a['mean'] is not None and b['mean'] is not None else None,
            'comparison_supported': adequate,
            'reason': None if adequate else 'at_least_4_days_needed_in_each_week',
        }
    return changes


def _strength(exercises, today):
    groups = defaultdict(list)
    for row in exercises if isinstance(exercises, list) else []:
        if not isinstance(row, dict):
            continue
        d = when(row.get('date'))
        if d is None or d > today or d < today - timedelta(days=27):
            continue
        name = str(row.get('exercise') or '').strip()
        equipment = str(row.get('equipment') or '').strip()
        unit = str(row.get('load_unit') or '').strip()
        if not name or not equipment or not unit:
            continue
        aid = str(row.get('activity_id') or '').strip()
        # En la identidad se incluyen equipo y unidad: máquina ≠ barra;
        # carga por pierna ≠ carga total; carga por mancuerna ≠ par.
        key = (name.casefold(), equipment, unit)
        peak = positive(row.get('peak_declared_load_kg'))
        volume = positive(row.get('verified_volume_kg'))
        complete = row.get('volume_complete') is True
        if row.get('laterality_unconfirmed') is True:
            complete = False
        if peak is None and volume is None:
            continue
        groups[key].append({
            'date': d.isoformat(), 'activity_id': aid or None,
            'observed_peak_kg': round(peak, 2) if peak is not None else None,
            'verified_volume_kg': round(volume, 1) if complete and volume is not None else None,
            'partial_volume_lower_bound_kg': round(volume, 1) if not complete and volume is not None else None,
            'known_sets': row.get('known_sets'),
            'volume_complete': complete,
            'laterality_unconfirmed': row.get('laterality_unconfirmed') is True,
        })
    result = []
    for (name, equipment, unit), obs in sorted(groups.items()):
        obs.sort(key=lambda x: (x['date'], x['activity_id'] or ''))
        # Comparar dos fechas distintas; repeticiones e intensidad pueden variar.
        distinct = sorted({o['date'] for o in obs})
        latest = [o for o in obs if o['date'] == distinct[-1]]
        earlier = [o for o in obs if len(distinct)>1 and o['date'] == distinct[-2]]
        current_peak = max((o['observed_peak_kg'] for o in latest if o['observed_peak_kg'] is not None),default=None)
        previous_peak = max((o['observed_peak_kg'] for o in earlier if o['observed_peak_kg'] is not None),default=None)
        delta = (round(current_peak - previous_peak, 2) if current_peak is not None and previous_peak is not None else None)

        def volume_period(begin, end, obs=obs):
            points = [o for o in obs if begin <= date.fromisoformat(o['date']) <= end]
            complete = bool(points) and all(o['volume_complete'] and o['verified_volume_kg'] is not None for o in points)
            return {'observations': len(points), 'complete': complete,
                    'verified_volume_kg': round(sum(o['verified_volume_kg'] for o in points), 1) if complete else None}

        v7 = volume_period(today-timedelta(days=6), today)
        prev7 = volume_period(today-timedelta(days=13), today-timedelta(days=7))
        v28 = volume_period(today-timedelta(days=27), today)
        comparison = (delta_pct(v7['verified_volume_kg'], prev7['verified_volume_kg'])
                      if v7['observations'] >= 2 and prev7['observations'] >= 2 else None)
        result.append({
            'exercise': name, 'equipment': equipment, 'load_unit': unit,
            'recorded_observations': len(obs), 'distinct_training_days': len(distinct),
            'last_day': distinct[-1], 'observed_peak_change_kg': delta,
            'volume_windows': {'7d':v7, 'previous_7d':prev7, '28d':v28},
            'volume_change_7d_vs_previous_pct': comparison,
            'volume_change_interpretation': 'external_work_not_strength_gain',
            'peak_change_interpretation': 'descriptive_only_not_strength_gain_or_1rm',
            'progression_confidence': 'insufficient_repeats' if len(distinct) < 2 else 'not_equated_for_reps_and_effort',
            'points': obs,
        })
    return result


def build_report(crossfit, wellness, daily, today):
    """Generar una sección V3.2; sin afectar al flujo Sync ni a certificados."""
    if not isinstance(crossfit, dict) or not isinstance(crossfit.get('activities'), list):
        raise ValueError('CrossFit report requires an activities array')
    if isinstance(today, str):
        today = date.fromisoformat(today)
    if not isinstance(today, date):
        raise ValueError('today must be a local date')
    daily = daily if isinstance(daily, dict) else {}
    rows, duplicate_activities = _activity_rows(crossfit['activities'], today)
    well, duplicate_wellness = _wellness_rows(wellness, today)
    start7 = today - timedelta(days=6)
    prev7_start = today - timedelta(days=13)
    prev7_end = start7 - timedelta(days=1)
    start28 = today - timedelta(days=27)

    windows = {'7d': _window(rows, start7, today),
               'previous_7d': _window(rows, prev7_start, prev7_end),
               '28d': _window(rows, start28, today)}
    recovery = {'7d': _recovery(well, start7, today),
                'previous_7d': _recovery(well, prev7_start, prev7_end),
                '28d': _recovery(well, start28, today)}
    current, previous = windows['7d'], windows['previous_7d']
    # Comparación de carga entre semanas, sin equivaler tipos de ejercicio.
    enough = current['sessions'] >= 3 and previous['sessions'] >= 3
    comparisons = {
        'weekly_sessions_delta': current['sessions'] - previous['sessions'] if enough else None,
        'srpe_proxy_delta_pct': delta_pct(current['srpe_recorded_minutes_proxy'], previous['srpe_recorded_minutes_proxy'])
            if enough and current['srpe_count'] == current['sessions'] and previous['srpe_count'] == previous['sessions'] else None,
        'trimp_delta_pct': delta_pct(current['trimp_total'], previous['trimp_total'])
            if enough and current['trimp_count'] == current['sessions'] and previous['trimp_count'] == previous['sessions'] else None,
        'comparison_status': 'descriptive_only' if enough else 'insufficient_sessions_in_either_week',
        'load_metrics_are_not_additive': True,
    }
    recovery['7d_vs_previous_7d'] = _recovery_delta(recovery['7d'], recovery['previous_7d'])

    chart = []
    for lag in range(27, -1, -1):
        d = today - timedelta(days=lag)
        acts = [a for a in rows if a['_day'] == d]
        sample = well.get(d)
        rpe = [numeric(a.get('rpe_used')) for a in acts]
        rpe = [x for x in rpe if x is not None and 0 <= x <= 10]
        values = []
        for a in acts:
            x = numeric(a.get('srpe_using_recorded_minutes'))
            if x is not None and x >= 0:
                values.append(x)
        trimp = [numeric((a.get('internal_load_not_additive') or {}).get('trimp')) for a in acts]
        trimp = [x for x in trimp if x is not None and x >= 0]
        def from_well(field, sample=sample):
            return positive(sample.get(field)) if isinstance(sample, dict) else None
        sec = from_well('sleepSecs')
        chart.append({
            'date': d.isoformat(), 'recorded_sessions': len(acts),
            'missing_training_entry_is_not_rest': not bool(acts),
            'mean_rpe': mean(rpe),
            'srpe_proxy': round(sum(values), 1) if values else None,
            'trimp': round(sum(trimp), 1) if trimp else None,
            'sleep_hours': round(sec/3600, 2) if sec is not None else None,
            'hrv': from_well('hrv'), 'resting_hr': from_well('restingHR'),
            'sleep_score': from_well('sleepScore'),
        })

    scatter = []
    for a in rows:
        rpe = numeric(a.get('rpe_used'))
        hr = positive((a.get('heart_rate') or {}).get('average'))
        if rpe is not None and 0 <= rpe <= 10 and hr is not None:
            scatter.append({'date':a['_day'].isoformat(),'activity_id':a.get('activity_id'),
                            'name':a.get('name'), 'session_rpe':rpe, 'garmin_avg_hr':round(hr,1),
                            'recorded_minutes':positive(a.get('recorded_minutes'))})
    scatter.sort(key=lambda x: (x['date'], str(x['activity_id'])))

    strength_rows = (crossfit.get('muscle_load') or {}).get('strength_exercises') or []
    strength = _strength(strength_rows, today)
    problems = []
    if crossfit.get('sheet_source') not in ('cycle_snapshot', 'live_csv'):
        problems.append('RPE source not verified')
    if duplicate_activities:
        problems.append(f'{duplicate_activities} duplicate activity IDs ignored')
    if duplicate_wellness:
        problems.append(f'{duplicate_wellness} duplicate wellness dates resolved by coverage')
    if windows['28d']['sessions'] < 10:
        problems.append('Fewer than 10 training sessions registered in the 28d window')
    if not enough:
        problems.append('No reliable 7d versus previous 7d training-load comparison')
    if recovery['7d']['days_with_any_wellness_row'] < 4:
        problems.append('Fewer than 4 wellness days in current week')

    recommendations = []
    missing_rpe = windows['7d']['sessions'] - windows['7d']['sessions_with_rpe']
    if missing_rpe:
        recommendations.append({'priority':1,'kind':'data_quality',
            'text':f'Registrar RPE y actividad Garmin por ID en {missing_rpe} sesiones de los ultimos 7 dias.'})
    if not enough:
        recommendations.append({'priority':1,'kind':'trend_confidence',
            'text':'Registrar una segunda semana completa antes de interpretar cambios de carga 7d frente a 7d.'})
    if not strength or all(x['distinct_training_days'] < 2 for x in strength):
        recommendations.append({'priority':2,'kind':'strength_tracking',
            'text':'Repetir algun ejercicio con el mismo equipo y anotar series, repeticiones, carga y esfuerzo de cada serie para comparar rendimiento.'})
    else:
        recommendations.append({'priority':2,'kind':'strength_tracking',
            'text':'Comparar las series de cada ejercicio solo con la misma variante, equipamiento, repeticiones y esfuerzo; el peso pico aislado es descriptivo.'})
    if recovery['7d']['days_with_any_wellness_row'] < 4:
        recommendations.append({'priority':2,'kind':'recovery_coverage',
            'text':'Esperar al registro de sueno/HRV de mas dias antes de usar tendencias de recuperacion para ajustar la carga.'})
    # Recomendacion integrada SOLO si hay dos semanas comparables y al menos
    # dos señales de recuperación observadas. Una coincidencia no es causalidad.
    hrv_signal = recovery['7d_vs_previous_7d']['hrv']
    sleep_signal = recovery['7d_vs_previous_7d']['sleep_hours']
    hrv_drop = (hrv_signal['comparison_supported'] and
        delta_pct(recovery['7d']['hrv']['mean'], recovery['previous_7d']['hrv']['mean']) is not None and
        delta_pct(recovery['7d']['hrv']['mean'], recovery['previous_7d']['hrv']['mean']) <= -10)
    sleep_drop = (sleep_signal['comparison_supported'] and
                  sleep_signal['delta_mean'] is not None and sleep_signal['delta_mean'] <= -0.5)
    load_increase = comparisons['srpe_proxy_delta_pct'] is not None and comparisons['srpe_proxy_delta_pct'] >= 25
    if load_increase and hrv_drop and sleep_drop:
        recommendations.insert(0, {'priority':1,'kind':'load_recovery_coincidence',
            'text':'Se observa mas carga percibida junto a menor duracion de sueno y HRV semanal; revisar sensaciones y considerar moderar el volumen antes de incrementar de nuevo. Coincidencia, no causalidad.'})
    if not recommendations:
        recommendations.append({'priority':2,'kind':'interpretation',
            'text':'Revisar juntas las series de carga, RPE y recuperacion; ninguna correlacion aislada prueba causalidad.'})

    date_matches = when(daily.get('date')) == today
    readiness = daily.get('readiness_model') if isinstance(daily.get('readiness_model'), dict) else {}
    return {
        'schema_version':1, 'version':'3.2', 'as_of_date':today.isoformat(),
        'timezone':'Europe/Madrid',
        'provenance':{
            'crossfit_generated_at':crossfit.get('generated_at'),
            'sheet_source':crossfit.get('sheet_source'),
            'last_recorded_activity_date':max((a['_day'] for a in rows), default=None).isoformat() if rows else None,
            'last_wellness_date':max(well).isoformat() if well else None,
            'daily_summary_date':daily.get('date'),
            'daily_summary_is_today':date_matches,
            'deduplicated_activity_ids':duplicate_activities,
            'deduplicated_wellness_dates':duplicate_wellness,
            'registered_days_are_not_guaranteed_complete':True,
        },
        'window_comparison':{'windows':windows,'current_vs_previous_7d':comparisons},
        'recovery':recovery,
        'readiness_today':{'score':numeric(readiness.get('score')) if date_matches else None,
                           'status':readiness.get('status') if date_matches else 'unavailable',
                           'source':'daily_summary.readiness_model',
                           'not_medical_diagnosis':True},
        'strength':{'exact_exercise_groups':strength,
                    'est_1rm_from_session_rpe':False,
                    'mixed_equipment_tonnage_comparable':False},
        'charts':{'daily_28d':chart,
                  'rpe_vs_garmin_hr':scatter,
                  'rpe_hr_scatter_interpretation':'descriptive_pairs_only_not_correlation_or_causality'},
        'interpretation_quality':{'level':'provisional' if problems else 'descriptive',
                                   'limitations':problems,
                                   'no_training_day_is_not_proof_of_rest':True,
                                   'no_set_rir_inferred_from_session_rpe':True,
                                   'srpe_uses_garmin_recorded_minutes':True,
                                   'no_diagnosis_or_shift_causality':True},
        'recommendations':recommendations,
    }
