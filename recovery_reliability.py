#!/usr/bin/env python3
"""Capa conservadora de fiabilidad de recuperación para Garmin Recovery.

Se ejecuta DESPUÉS de rpe_enrichment.py. Conserva métricas originales
como auditoría, fusiona por fecha (sin sumar fuentes duplicadas) y evita
recomendaciones verdes con sueño/VFC incompletos o baselines inmaduras.
Las puntuaciones son heurísticas para entrenamiento, nunca diagnósticos.
"""
import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')


def read(name, default):
    try:
        item = json.loads(Path(name).read_text(encoding='utf-8'))
        return item if isinstance(item, type(default)) else default
    except (OSError, ValueError):
        return default


def write(name, obj):
    Path(name).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')


def n(v, lo=None, hi=None):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    v = float(v)
    return v if (lo is None or v >= lo) and (hi is None or v <= hi) else None


def dt(value):
    if isinstance(value, (int, float)) and 1e12 <= value < 1e13:
        try:
            return datetime.fromtimestamp(value / 1000, TZ)
        except (OverflowError, ValueError, OSError):
            return None
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=TZ) if parsed.tzinfo is None else parsed.astimezone(TZ)
    except (ValueError, TypeError):
        return None


def source_is_fresh(source, now, max_age_hours=16):
    moment = dt(source.get('generated_at')) if isinstance(source, dict) else None
    return moment is not None and -0.25 <= (now - moment).total_seconds() / 3600 <= max_age_hours


def select(primary, backup, key, lo, hi, p_name, b_name):
    a = n((primary or {}).get(key), lo, hi)
    if a is not None:
        return a, p_name
    b = n((backup or {}).get(key), lo, hi)
    return b, b_name if b is not None else None


def nightly_rows(wellness, hrv_timeline, sleep_store, extended, heart, now):
    well = {x.get('id'): x for x in wellness if isinstance(x, dict) and isinstance(x.get('id'), str)}
    hrv_days = hrv_timeline.get('days', {})
    sleep_days = sleep_store.get('days', {})
    ext_days = extended.get('days', {})
    hr_days = heart.get('days', {})
    start = now.date() - timedelta(days=59)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(60)]
    records = {}
    for day in dates:
        w = well.get(day) or {}
        h = hrv_days.get(day) or {}
        sl = sleep_days.get(day) or {}
        ex = ext_days.get(day) or {}
        ext_sleep = ex.get('sleep_detail') or {}
        ext_hrv = ex.get('hrv_status') or {}
        hr = hr_days.get(day) or {}
        # Prefer the official Garmin nightly summary, then Intervals.icu.
        garmin_hrv = n(h.get('night_avg_ms'), 1, 500)
        if garmin_hrv is None:
            garmin_hrv = n(sl.get('hrv_ms'), 1, 500)
        if garmin_hrv is None:
            garmin_hrv = n(ext_hrv.get('last_night_avg'), 1, 500)
        hrv = garmin_hrv if garmin_hrv is not None else n(w.get('hrv'), 1, 500)
        hrv_source = ('garmin_hrv_timeline' if n(h.get('night_avg_ms'), 1, 500) is not None else
                      'garmin_sleep_history' if n(sl.get('hrv_ms'), 1, 500) is not None else
                      'garmin_extended' if n(ext_hrv.get('last_night_avg'), 1, 500) is not None else
                      'intervals_icu' if hrv is not None else None)

        sleep_hours = n(sl.get('sleep_hours'), 0.15, 20)
        sleep_source = 'garmin_sleep_history' if sleep_hours is not None else None
        start_local, end_local = sl.get('sleep_start_local'), sl.get('sleep_end_local')
        if sleep_hours is None and ext_sleep.get('sleep_window_confirmed') is not False:
            sleep_hours = n(ext_sleep.get('sleep_hours'), 0.15, 20)
            if sleep_hours is not None:
                sleep_source = 'garmin_extended'
                start_local, end_local = ext_sleep.get('sleep_start_local'), ext_sleep.get('sleep_end_local')
        if sleep_hours is None:
            secs = n(w.get('sleepSecs'), 600, 72000)
            if secs is not None:
                sleep_hours, sleep_source = round(secs / 3600, 2), 'intervals_icu'
        sleep_score = n(sl.get('sleep_score'), 0, 100)
        score_source = 'garmin_sleep_history' if sleep_score is not None else None
        if sleep_score is None:
            scores = ext_sleep.get('score_components') or {}
            overall = scores.get('overall') if isinstance(scores, dict) else None
            score = n(overall.get('value'), 0, 100) if isinstance(overall, dict) else None
            if score is not None:
                sleep_score, score_source = score, 'garmin_extended'
            else:
                sleep_score = n(w.get('sleepScore'), 0, 100)
                score_source = 'intervals_icu' if sleep_score is not None else None
        rest = n(hr.get('resting_hr'), 20, 150)
        rest_source = 'garmin_heart_rate' if rest is not None else None
        if rest is None:
            rest = n(w.get('restingHR'), 20, 150)
            rest_source = 'intervals_icu' if rest is not None else None
        night_hr = n(hr.get('nighttime_avg_hr'), 20, 180)
        begin, finish = dt(start_local), dt(end_local)
        sleep_context = sl.get('sleep_context') if sleep_source == 'garmin_sleep_history' else None
        if sleep_context not in ('day_sleep', 'night_sleep') and begin and finish and finish > begin:
            mid = begin + (finish - begin) / 2
            sleep_context = 'day_sleep' if 8 <= mid.hour < 18 or 6 <= begin.hour < 18 else 'night_sleep'
        records[day] = {
            'date': day, 'hrv_ms': hrv, 'sleep_hours': sleep_hours,
            'sleep_score': sleep_score, 'resting_hr': rest, 'night_hr': night_hr,
            'sleep_context': sleep_context,
            'sleep_start_local': begin.isoformat() if begin else None,
            'sleep_end_local': finish.isoformat() if finish else None,
            'sources': {'hrv_ms': hrv_source, 'sleep_hours': sleep_source,
                        'sleep_score': score_source, 'resting_hr': rest_source,
                        'night_hr': 'garmin_heart_rate' if night_hr is not None else None},
        }
    return records


def observations(records, now, key, context=None):
    selected = []
    for day in sorted(records):
        diff = (now.date() - datetime.strptime(day, '%Y-%m-%d').date()).days
        if not 1 <= diff <= 28:
            continue
        row = records[day]
        if context and row.get('sleep_context') != context:
            continue
        value = n(row.get(key))
        if value is not None:
            selected.append(value)
    return selected


def baselines(records, now, day_context):
    recent_day_sleep = observations(records, now, 'hrv_ms', 'day_sleep')
    # Only use subgroup when at least 7 matched prior nights; otherwise pooled reference.
    selected_context = 'day_sleep' if day_context == 'day_sleep' and len(recent_day_sleep) >= 7 else None
    result = {}
    for metric in ('hrv_ms', 'sleep_hours', 'sleep_score', 'resting_hr', 'night_hr'):
        values = observations(records, now, metric, selected_context)
        result[metric] = {'n': len(values), 'median': round(statistics.median(values), 2) if values else None,
                          'last7_mean': round(statistics.fmean(values[-7:]), 2) if values else None,
                          'scope': selected_context or 'overall'}
    return result


def recovery_assessment(records, now, advanced, inputs_fresh=True):
    current = records[now.date().isoformat()]
    shift = str((advanced.get('day_context') or {}).get('today') or 'unknown')
    context = current.get('sleep_context') or shift
    baseline = baselines(records, now, current.get('sleep_context'))
    essential = ('hrv_ms', 'sleep_hours', 'resting_hr')
    missing = [k for k in essential if current.get(k) is None]
    minimum = min(baseline[k]['n'] for k in essential)
    sample_quality = 'high' if minimum >= 21 and not missing and inputs_fresh else 'medium' if minimum >= 7 and not missing and inputs_fresh else 'low'
    if not inputs_fresh:
        reason = 'fuentes_desactualizadas'
    elif missing:
        reason = 'faltan_sueno_vfc_o_fc_reposo'
    elif minimum < 7:
        reason = 'referencia_personal_insuficiente'
    else:
        reason = None
    status = 'pending' if missing or not inputs_fresh else 'provisional' if minimum < 14 else 'assessed'
    if minimum < 7 and status == 'provisional':
        status = 'provisional'
    score, metrics_used, flags = None, [], []
    if not missing and inputs_fresh and minimum >= 7:
        score = 85.0  # Heurística conservadora; se calibrará posteriormente.
        hrv, hr_med = current['hrv_ms'], baseline['hrv_ms']['median']
        if hr_med and hr_med > 0:
            hrv_change = (hrv / hr_med - 1) * 100
            metrics_used.append({'metric': 'hrv_ms', 'value': hrv, 'reference': hr_med, 'change_pct': round(hrv_change, 1)})
            if hrv_change <= -20: score -= 22; flags.append('hrv_baja_20pct')
            elif hrv_change <= -10: score -= 12; flags.append('hrv_baja_10pct')
            elif hrv_change >= 10: score += 3
        rh_delta = current['resting_hr'] - baseline['resting_hr']['median']
        metrics_used.append({'metric': 'resting_hr', 'value': current['resting_hr'], 'reference': baseline['resting_hr']['median'], 'delta_bpm': round(rh_delta, 1)})
        if rh_delta >= 8: score -= 15; flags.append('fc_reposo_muy_alta')
        elif rh_delta >= 5: score -= 10; flags.append('fc_reposo_alta')
        elif rh_delta >= 3: score -= 5
        if current['sleep_hours'] < 5: score -= 25; flags.append('sueno_menor_5h')
        elif current['sleep_hours'] < 6: score -= 15; flags.append('sueno_menor_6h')
        elif current['sleep_hours'] < 7: score -= 7
        metrics_used.append({'metric': 'sleep_hours', 'value': current['sleep_hours'], 'reference': baseline['sleep_hours']['median']})
        sc = current.get('sleep_score')
        if sc is not None:
            if sc < 60: score -= 12; flags.append('sueno_baja_calidad')
            elif sc < 75: score -= 6
        nh = current.get('night_hr')
        if nh is not None and baseline['night_hr']['n'] >= 7:
            if nh - baseline['night_hr']['median'] >= 6: score -= 7; flags.append('fc_nocturna_alta')
        score = max(0, min(100, round(score)))
    # A provisional heuristic never authorizes a high-intensity session.
    color = ('unavailable' if status == 'pending' else
             'red' if score is not None and score < 50 else
             'yellow' if sample_quality != 'high' or score is None or score < 75 else
             'green')
    if status == 'provisional' and score is not None and score < 50:
        color = 'red'
    return {
        'generated_at': now.isoformat(), 'methodology_version': 'recovery-reliability-v1',
        'state': status, 'status': color, 'score': score,
        'confidence': sample_quality, 'reason': reason,
        'missing_essential': missing, 'fresh_sources': inputs_fresh,
        'context': context, 'work_shift_context': shift,
        'sleep_context': current.get('sleep_context'),
        'current': current, 'baseline_28d': baseline,
        'metrics_used': metrics_used, 'warnings': flags,
        'recommendation': ('Reevaluar tras el siguiente sueño confirmado; no autorizar intensidad máxima con información incompleta.'
                           if status == 'pending' else
                           'Interpretación provisional: confirmar sensaciones y calentamiento; no inferir aptitud máxima.'
                           if status == 'provisional' else
                           'Interpretar junto con dolor, sensaciones, RPE y rendimiento; no es un diagnóstico.'),
        'limitations': ['No mide fatiga neuromuscular directamente.',
                        'Puntuación heurística no validada clínicamente.',
                        'No suma valores Garmin + Intervals del mismo día.'],
    }


def patch_hybrid(hybrid, assessment):
    if not isinstance(hybrid, dict):
        return hybrid
    hybrid = dict(hybrid)
    raw = n(hybrid.get('score'), 0, 100)
    if raw is None:
        return hybrid
    hybrid['score_before_recovery_guardrail'] = int(raw)
    # State pending/provisional is not physiologic "yellow". We use a yellow
    # compatibility envelope because the existing validator expects 0..100 +
    # green/yellow/red; the authoritative result is recovery_assessment_v2.
    if assessment['score'] is not None and assessment['score'] < 50:
        limit = 49
    elif assessment['state'] in ('pending', 'provisional') or assessment['confidence'] != 'high':
        limit = 74
    elif assessment['score'] is not None and assessment['score'] < 75:
        limit = 74
    else:
        limit = 100
    capped = min(int(raw), limit)
    hybrid['score'] = capped
    hybrid['status'] = 'red' if capped < 50 else 'yellow' if capped < 75 else 'green'
    hybrid['recommended_volume'] = 'sin recomendación hasta completar datos' if assessment['state'] == 'pending' else 'individualizar; evitar sesión máxima sin confirmar' if assessment['state'] == 'provisional' else hybrid.get('recommended_volume')
    hybrid['recommendation'] = 'pending' if assessment['state'] == 'pending' else 'moderate' if assessment['state'] == 'provisional' else hybrid.get('recommendation')
    hybrid['confidence'] = assessment['confidence']
    hybrid['recovery_assessment_state'] = assessment['state']
    hybrid['guardrails_applied'] = list(hybrid.get('guardrails_applied') or [])
    if limit < 100 and 'recovery_reliability_gate' not in hybrid['guardrails_applied']:
        hybrid['guardrails_applied'].append('recovery_reliability_gate')
    hybrid['note'] = 'Compatibilidad; para decisiones usar recovery_assessment_v2.state y confidence, NO solo score.'
    return hybrid


def produce(now=None, files=None):
    now = now or datetime.now(TZ)
    now = now.replace(tzinfo=TZ) if now.tzinfo is None else now.astimezone(TZ)
    files = files or {}
    def get(k, default):
        return files[k] if k in files else read(k, default)
    well = get('wellness.json', [])
    hrv = get('garmin_hrv_timeline.json', {})
    sleep = get('garmin_sleep_history.json', {})
    extended = get('garmin_extended.json', {})
    heart = get('garmin_heart_rate.json', {})
    adv = get('advanced_analytics.json', {})
    daily = get('daily_summary.json', {})
    weekly = get('weekly_summary.json', {})
    quality = get('data_quality.json', {})
    records = nightly_rows(well, hrv, sleep, extended, heart, now)
    # When a source has generated_at but is stale, lower confidence; no live claims.
    hrv_fresh = source_is_fresh(hrv, now) or source_is_fresh(sleep, now)
    sleep_fresh = source_is_fresh(sleep, now) or source_is_fresh(extended, now)
    hr_fresh = source_is_fresh(heart, now)
    assessment = recovery_assessment(records, now, adv, hrv_fresh and sleep_fresh and hr_fresh)
    assessment['input_freshness'] = {'hrv': hrv_fresh, 'sleep': sleep_fresh, 'heart_rate': hr_fresh}
    # Update the canonical analysis and the two report files; retain originals.
    adv['recovery_assessment_v2'] = assessment
    adv['readiness_hybrid'] = patch_hybrid(adv.get('readiness_hybrid'), assessment)
    for report in (daily, weekly):
        report['recovery_assessment_v2'] = assessment
        report['readiness_hybrid'] = adv['readiness_hybrid']
        sub = report.get('advanced_analytics')
        if isinstance(sub, dict):
            sub['recovery_assessment_v2'] = assessment
            sub['readiness_hybrid'] = adv['readiness_hybrid']
    if isinstance(daily.get('readiness_model'), dict):
        daily['readiness_model'] = patch_hybrid(daily['readiness_model'], assessment)
    current = assessment['current']
    if isinstance(daily.get('recovery_today'), dict):
        mapping = {'hrv': 'hrv_ms', 'sleep_hours': 'sleep_hours', 'sleep_score': 'sleep_score', 'resting_hr': 'resting_hr'}
        for dest, src in mapping.items():
            if current[src] is not None:
                daily['recovery_today'][dest] = current[src]
        if current['sleep_hours'] is not None:
            daily['recovery_today']['sleep_secs'] = round(current['sleep_hours'] * 3600)
        daily['recovery_today']['fusion_sources'] = current['sources']
    coverage = {}
    for name in ('hrv_ms', 'sleep_hours', 'sleep_score', 'resting_hr'):
        samples = observations(records, now, name)
        coverage[name] = {'days_present': len(samples), 'days_expected': 28, 'pct': round(len(samples) / 28 * 100, 1)}
    quality['recovery_fused_coverage_28d'] = coverage
    quality['recovery_v2_status'] = assessment['state']
    quality['recovery_v2_confidence'] = assessment['confidence']
    adv['recovery_data_coverage'] = coverage
    daily['recovery_data_coverage'] = coverage
    weekly['recovery_data_coverage'] = coverage
    return {'advanced_analytics.json': adv, 'daily_summary.json': daily,
            'weekly_summary.json': weekly, 'data_quality.json': quality,
            'recovery_assessment.json': assessment}


def main():
    outputs = produce()
    for name, obj in outputs.items():
        write(name, obj)
    result = outputs['recovery_assessment.json']
    print(json.dumps({'state': result['state'], 'status': result['status'],
                      'confidence': result['confidence'], 'score': result['score'],
                      'missing': result['missing_essential'],
                      'history_days': {k: v['n'] for k, v in result['baseline_28d'].items()},
                      'freshness': result['input_freshness']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
