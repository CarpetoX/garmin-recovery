#!/usr/bin/env python3
"""V3.5: complemento descriptivo y verificable al informe V3.2.

No inventa equivalencias entre cargas ni WOD; no estima 1RM, sueño ni RPE.
Una ausencia de registro NO significa descanso. Sin escritura de fuentes.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, timedelta
import json
import math
from pathlib import Path

VERSION = '3.5'


def number(x):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    try:
        n = float(x)
    except (ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def positive(x):
    n = number(x)
    return n if n is not None and n > 0 else None


def day_of(x):
    if not isinstance(x, str):
        return None
    try:
        return date.fromisoformat(x[:10])
    except ValueError:
        return None


def _name(x):
    return x.strip().casefold() if isinstance(x, str) else ''


def activities(raw, today):
    if not isinstance(raw, list):
        raise ValueError('activities_missing')
    seen, result, duplicates = set(), [], 0
    for a in raw:
        if not isinstance(a, dict):
            continue
        day = day_of(a.get('date'))
        aid = str(a.get('activity_id') or '').strip()
        if not day or day > today or day < today-timedelta(days=27) or not aid:
            continue
        if aid in seen:
            duplicates += 1
            continue
        seen.add(aid)
        result.append({**a, '_day': day})
    return result, duplicates


def _rpe(value):
    x = number(value)
    return x if x is not None and 0 <= x <= 10 else None


def session_window(rows, start, end):
    period = [a for a in rows if start <= a['_day'] <= end]
    types = defaultdict(list)
    for a in period:
        raw_name = a.get('name')
        category = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else 'Sin categoría'
        types[category].append(a)
    def rpe_summary(group):
        vals = [_rpe(a.get('rpe_used')) for a in group]
        vals = [x for x in vals if x is not None]
        return {
            'sessions': len(group), 'rpe_samples': len(vals),
            'mean_rpe': round(sum(vals)/len(vals), 2) if vals else None,
            'sessions_rpe_8_plus': sum(x >= 8 for x in vals),
            'rpe_distribution': {
                '0_to_3': sum(0 <= x < 4 for x in vals),
                '4_to_6': sum(4 <= x < 7 for x in vals),
                '7_to_8_9': sum(7 <= x < 9 for x in vals),
                '9_to_10': sum(9 <= x <= 10 for x in vals),
            },
        }
    summary = rpe_summary(period)
    summary['start_date'] = start.isoformat()
    summary['end_date'] = end.isoformat()
    summary['rpe_missing'] = summary['sessions'] - summary['rpe_samples']
    summary['rpe_coverage_pct'] = (round(100*summary['rpe_samples']/summary['sessions'], 1)
                                    if summary['sessions'] else None)
    summary['categories'] = [
        {'category': name, **rpe_summary(group),
         'garmin_minutes_sum': round(sum(positive(x.get('recorded_minutes')) or 0 for x in group), 1),
         'minutes_samples': sum(positive(x.get('recorded_minutes')) is not None for x in group),
         'mean_of_session_average_hr_bpm_unweighted': round(sum(v)/len(v), 1) if (v := [h for x in group
             if (h := positive((x.get('heart_rate') or {}).get('average'))) is not None]) else None,
         'hr_samples': sum(positive((x.get('heart_rate') or {}).get('average')) is not None for x in group),
         'category_origin': 'garmin_activity_name_not_a_verified_wod_variant',
         'session_hr_average_is_unweighted': True}
        for name, group in sorted(types.items())]
    summary['recorded_sessions_not_verified_complete_calendar'] = True
    return summary


def _daily_14(rows, today):
    chart = []
    for delay in range(13, -1, -1):
        d = today-timedelta(days=delay)
        items = [a for a in rows if a['_day'] == d]
        rp = [_rpe(a.get('rpe_used')) for a in items]
        rp = [x for x in rp if x is not None]
        chart.append({
            'date': d.isoformat(), 'recorded_sessions': len(items),
            'missing_record_is_not_rest': not bool(items),
            'mean_session_rpe': round(sum(rp)/len(rp), 2) if rp else None,
            'rpe_samples': len(rp),
            'high_rpe_8_plus': sum(x >= 8 for x in rp),
        })
    return chart


def _strength_patterns(raw, activity_dates, today):
    """Contar solo series declaradas, sin sumar kg entre equipos o lados."""
    seen = set()
    duplicates = 0
    accepted = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        d = day_of(item.get('date'))
        aid = str(item.get('activity_id') or '').strip()
        exercise = _name(item.get('exercise'))
        equipment = _name(item.get('equipment'))
        unit = _name(item.get('load_unit'))
        if not d or d > today or d < today-timedelta(days=27) or not aid or activity_dates.get(aid) != d or not exercise or not equipment or not unit:
            continue
        # El origen ya agrupa cada ejercicio por actividad; una segunda copia idéntica es duplicada.
        k = (aid, d, exercise, equipment, unit)
        if k in seen:
            duplicates += 1
            continue
        seen.add(k)
        sets = item.get('known_sets')
        if not (type(sets) is int and sets >= 0):
            sets = None
        pattern = _name(item.get('movement_pattern')) or 'sin_clasificar'
        accepted.append((d, pattern, sets, item.get('volume_complete') is True,
                         item.get('laterality_unconfirmed') is True))
    def per_period(start):
        patterns = defaultdict(list)
        for d, pattern, sets, complete, lateral in accepted:
            if d >= start:
                patterns[pattern].append((sets, complete, lateral))
        return [
            {'movement_pattern': key, 'registered_exercise_blocks': len(points),
             'known_sets_recorded': sum(n or 0 for n, _, _ in points),
             'blocks_with_known_sets': sum(n is not None for n, _, _ in points),
             'volume_complete_blocks': sum(complete and not lateral for _, complete, lateral in points),
             'laterality_unconfirmed_blocks': sum(lateral for _, _, lateral in points)}
            for key, points in sorted(patterns.items())]
    return {'7d': per_period(today-timedelta(days=6)),
            '28d': per_period(today-timedelta(days=27)),
            'duplicate_exercise_rows_skipped': duplicates,
            'known_sets_are_not_equivalent_to_volume_or_strength_gain': True,
            'kg_from_different_equipment_or_units_never_added': True}


def _metcon_exposure(ext, activity_dates, today):
    ext = ext if isinstance(ext, dict) else {}
    entries = ext.get('entries')
    seen, accepted, duplicates = set(), [], 0
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict):
            continue
        d = day_of(e.get('date'))
        aid = str(e.get('activity_id') or '').strip()
        movement = _name(e.get('movement'))
        evidence = e.get('evidence')
        if not d or d > today or d < today-timedelta(days=27) or activity_dates.get(aid) != d or not movement or not isinstance(evidence, str) or not evidence.startswith('performed.'):
            continue
        # Entrada repetida del mismo movimiento/actividad: no sumarla de nuevo.
        key = (aid, movement)
        r, meters = positive(e.get('verified_reps')), positive(e.get('verified_distance_m'))
        if r is None and meters is None:
            continue
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        accepted.append((d, movement, r, meters))
    def expose(start, end):
        by = defaultdict(list)
        for d, movement, r, meters in accepted:
            if start <= d <= end:
                by[movement].append((r, meters))
        return [
            {'movement': movement, 'recorded_entries': len(vals),
             'verified_reps_total': round(sum(x or 0 for x, _ in vals), 1) if any(x is not None for x, _ in vals) else None,
             'verified_distance_m_total': round(sum(y or 0 for _, y in vals), 1) if any(y is not None for _, y in vals) else None,
             'reps_entries': sum(x is not None for x, _ in vals),
             'distance_entries': sum(y is not None for _, y in vals)}
            for movement, vals in sorted(by.items())]
    return {'7d': expose(today-timedelta(days=6), today),
            'previous_7d': expose(today-timedelta(days=13), today-timedelta(days=7)),
            '28d': expose(today-timedelta(days=27), today),
            'duplicate_activity_movement_rows_skipped': duplicates,
            'only_performed_totals_counted': True,
            'prescribed_work_never_inferred': True,
            'not_comparable_benchmark_performance': True}


def build(crossfit, base, today):
    if not isinstance(crossfit, dict) or not isinstance(crossfit.get('activities'), list):
        raise ValueError('CrossFit activities required')
    if not isinstance(base, dict) or base.get('version') != '3.2' or not isinstance(base.get('window_comparison'), dict):
        raise ValueError('V3.2 report required')
    if isinstance(today, str):
        today = date.fromisoformat(today)
    if not isinstance(today, date) or base.get('as_of_date') != today.isoformat():
        raise ValueError('mismatched report local date')
    if (base.get('provenance') or {}).get('crossfit_generated_at') != crossfit.get('generated_at'):
        raise ValueError('crossfit source does not match V3.2')
    rows, dup = activities(crossfit['activities'], today)
    activity_dates = {str(a['activity_id']): a['_day'] for a in rows}
    start7, start14, start28 = (today-timedelta(days=n) for n in (6, 13, 27))
    periods = {'7d': session_window(rows, start7, today),
               'previous_7d': session_window(rows, start14, start7-timedelta(days=1)),
               '28d': session_window(rows, start28, today)}
    extensions = crossfit.get('training_extensions') or {}
    if not isinstance(extensions, dict):
        extensions = {}
    patterns = _strength_patterns((crossfit.get('muscle_load') or {}).get('strength_exercises'), activity_dates, today)
    exposure = _metcon_exposure(extensions.get('metcon_exposure'), activity_dates, today)
    benchmarks = extensions.get('performance_trends') or {}
    if not isinstance(benchmarks, dict):
        benchmarks = {}
    comparisons = benchmarks.get('comparisons')
    comparisons = comparisons if isinstance(comparisons, list) else []
    benchmark_count = benchmarks.get('eligible_benchmarks')
    benchmark_count = benchmark_count if type(benchmark_count) is int and benchmark_count >= 0 else None
    conflicts = sum(a.get('manual_rpe_conflict') is True for a in rows)
    recommendations = []
    if periods['7d']['rpe_missing']:
        recommendations.append({'priority':1,'category':'data_quality','message':
            'Añadir RPE a las actividades sin RPE de los últimos 7 días usando su ID de Garmin.'})
    if conflicts:
        recommendations.append({'priority':1,'category':'rpe_conflicts','message':
            'Revisar discrepancias explícitas de RPE antes de interpretar carga percibida.'})
    if periods['previous_7d']['sessions'] < 3:
        recommendations.append({'priority':1,'category':'insufficient_history','message':
            'Registrar otra semana de sesiones comparables antes de valorar una tendencia semanal.'})
    if benchmark_count == 0 or not comparisons:
        recommendations.append({'priority':2,'category':'wod_comparability','message':
            'Para comparar WOD, registrar benchmark_id, variante, estándares, tiempo o repeticiones efectivas y RPE.'})
    if not any(p['registered_exercise_blocks']>=2 for p in patterns['28d']):
        recommendations.append({'priority':2,'category':'strength_evidence','message':
            'Repetir ejercicios con mismo equipo, unidad, repeticiones y esfuerzo de serie para poder comparar.'})
    return {
        'schema_version':1,'version':VERSION,'as_of_date':today.isoformat(),
        'provenance':{'crossfit_generated_at':crossfit.get('generated_at'),
                      'rpe_sheet_source':crossfit.get('sheet_source'),
                      'unique_activity_ids_28d':len(rows),
                      'duplicate_activity_ids_ignored':dup,
                      'no_calendar_completeness_assumed':True},
        'session_breakdown':periods,
        'charts':{'daily_14d':_daily_14(rows,today),
                  'modality_rpe_7d':periods['7d']['categories'],
                  'modality_rpe_previous_7d':periods['previous_7d']['categories']},
        'strength_patterns':patterns,
        'metcon_exposure':exposure,
        'benchmarks':{'verified_matching_benchmarks':benchmark_count,
                      'reported_comparison_count':len(comparisons),
                      'status':'verified_comparisons_exist' if comparisons else 'no_verified_repeated_benchmarks',
                      'workout_names_are_not_benchmark_ids':True},
        'rpe_conflicts_recorded':conflicts,
        'recommendations':recommendations,
        'interpretation_quality':{
            'level':'provisional' if periods['28d']['sessions'] < 10 or periods['previous_7d']['sessions'] < 3 else 'descriptive_only',
            'no_absent_training_day_called_rest':True,
            'garmin_recorded_minutes_not_wod_time':True,
            'different_equipment_tonnage_not_comparable':True,
            'known_unilateral_sets_not_doubled':True,
            'no_1rm_from_session_rpe':True,
            'no_causal_recovery_or_medical_claims':True,
            'rpe_distribution_not_diagnostic':True,
        },
    }


def validate(candidate, crossfit):
    """Validar salida enriquecida antes de publicarla; no toca los JSON."""
    errors = []
    if not isinstance(candidate, dict) or not isinstance(crossfit, dict):
        return ['missing_candidate_or_source']
    v32 = candidate.get('performance_report_v32')
    if not isinstance(v32, dict):
        return ['v32_missing']
    addon = v32.get('performance_enhancements_v35')
    if not isinstance(addon, dict):
        return ['v35_missing']
    if addon.get('version') != VERSION or addon.get('schema_version') != 1:
        errors.append('v35_contract_invalid')
    day = day_of(candidate.get('as_of_date'))
    if day is None or addon.get('as_of_date') != candidate.get('as_of_date') or v32.get('as_of_date') != addon.get('as_of_date'):
        errors.append('v35_local_day_invalid')
    p = addon.get('provenance')
    if not isinstance(p, dict) or p.get('crossfit_generated_at') != crossfit.get('generated_at'):
        errors.append('v35_source_mismatch')
    if not isinstance(p, dict) or p.get('rpe_sheet_source') != crossfit.get('sheet_source'):
        errors.append('v35_rpe_source_mismatch')
    if not isinstance(p, dict) or p.get('no_calendar_completeness_assumed') is not True:
        errors.append('v35_calendar_guard_missing')
    windows = addon.get('session_breakdown')
    base_windows = (v32.get('window_comparison') or {}).get('windows') or {}
    if not isinstance(windows, dict):
        errors.append('v35_windows_missing')
    else:
        for key in ('7d','previous_7d','28d'):
            row = windows.get(key)
            old = base_windows.get(key)
            if not isinstance(row, dict) or not isinstance(old, dict) or row.get('sessions') != old.get('sessions'):
                errors.append('v35_window_mismatch:'+key)
                continue
            rpe_n = row.get('rpe_samples')
            sessions = row.get('sessions')
            dist = row.get('rpe_distribution')
            if not (type(sessions) is int and sessions >= 0 and type(rpe_n) is int and 0 <= rpe_n <= sessions
                    and isinstance(dist, dict) and all(type(v) is int and v >= 0 for v in dist.values())
                    and sum(dist.values()) == rpe_n):
                errors.append('v35_rpe_count_invalid:'+key)
    chart = (addon.get('charts') or {}).get('daily_14d') if isinstance(addon.get('charts'), dict) else None
    if not isinstance(chart, list) or len(chart) != 14 or day is None:
        errors.append('v35_chart_missing')
    elif [x.get('date') if isinstance(x, dict) else None for x in chart] != [
            (day-timedelta(days=d)).isoformat() for d in range(13,-1,-1)]:
        errors.append('v35_chart_dates_invalid')
    patterns = addon.get('strength_patterns')
    if not isinstance(patterns, dict) or patterns.get('kg_from_different_equipment_or_units_never_added') is not True:
        errors.append('v35_strength_guard_invalid')
    metcon = addon.get('metcon_exposure')
    if not isinstance(metcon, dict) or metcon.get('prescribed_work_never_inferred') is not True or metcon.get('not_comparable_benchmark_performance') is not True:
        errors.append('v35_metcon_guard_invalid')
    bench = addon.get('benchmarks')
    if not isinstance(bench, dict) or bench.get('workout_names_are_not_benchmark_ids') is not True:
        errors.append('v35_benchmark_guard_invalid')
    quality = addon.get('interpretation_quality')
    required = ('no_absent_training_day_called_rest','garmin_recorded_minutes_not_wod_time',
                'different_equipment_tonnage_not_comparable','known_unilateral_sets_not_doubled',
                'no_1rm_from_session_rpe','no_causal_recovery_or_medical_claims')
    if not isinstance(quality, dict) or any(quality.get(k) is not True for k in required):
        errors.append('v35_interpretation_guard_invalid')
    if not isinstance(addon.get('recommendations'), list):
        errors.append('v35_recommendations_missing')
    # Recalcular los agregados usando LA MISMA fotografía del CrossFit del ciclo.
    # Además del esquema, impide publicar valores manipulados o de otro archivo.
    if day is not None:
        try:
            expected = build(crossfit, v32, day)
        except (ValueError, TypeError, AttributeError):
            errors.append('v35_cannot_rebuild_from_source')
        else:
            if addon != expected:
                errors.append('v35_source_derived_values_mismatch')
    return errors


def _strict_float(s):
    x = float(s)
    if not math.isfinite(x):
        raise ValueError('non_finite_number')
    return x


def main(argv=None):
    ap=argparse.ArgumentParser(description='Fail-closed V3.5 candidate validation')
    ap.add_argument('--candidate',type=Path,required=True)
    ap.add_argument('--crossfit',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        candidate=json.loads(args.candidate.read_text(encoding='utf-8'),parse_float=_strict_float,
                             parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        source=json.loads(args.crossfit.read_text(encoding='utf-8'),parse_float=_strict_float,
                          parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        errors=validate(candidate,source)
    except (OSError, ValueError, TypeError) as exc:
        errors=['invalid_json_or_source:'+type(exc).__name__]
    print(json.dumps({'validator':'V3.5','status':'ok' if not errors else 'failed',
                      'errors':errors},ensure_ascii=False))
    return 1 if errors else 0

if __name__=='__main__':
    raise SystemExit(main())
