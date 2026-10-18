#!/usr/bin/env python3
"""V3.3: fail-closed validation of the newly generated CrossFit performance report.

Read-only. Does not alter source JSON, prior good reports, or delivery certificates.
The CrossFit workflow calls this on the *candidate* JSON BEFORE any commit.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
FRESHNESS_MINUTES = 90


def _time(value):
    if not isinstance(value, str):
        return None
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return d if d.tzinfo is not None else None
    except ValueError:
        return None


def _day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('non_finite_number')
    return number


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'),
                          parse_float=_finite_float,
                          parse_constant=lambda s: (_ for _ in ()).throw(ValueError('non_finite_' + s)))
    except (OSError, ValueError, TypeError) as exc:
        raise ValueError(f'cannot_read_valid_json:{path.name}:{type(exc).__name__}') from exc


def audit(candidate, crossfit, now):
    """Return actionable error codes. Missing observations are allowed; missing structure is not."""
    errors = []
    if not isinstance(candidate, dict):
        return ['candidate_not_object']
    if not isinstance(crossfit, dict):
        return ['crossfit_not_object']
    if not isinstance(now, datetime) or now.tzinfo is None:
        return ['invalid_audit_clock']

    if candidate.get('version') != '3.1' or candidate.get('schema_version') != 1:
        errors.append('wrong_top_level_contract')
    if candidate.get('source') != 'crossfit_insights.json':
        errors.append('wrong_source_name')
    if not isinstance(crossfit.get('activities'), list):
        errors.append('crossfit_activities_not_list')

    created = _time(candidate.get('generated_at'))
    source_time = _time(crossfit.get('generated_at'))
    report_source_time = _time(candidate.get('source_generated_at'))
    if not created or not source_time or not report_source_time:
        errors.append('missing_or_invalid_timestamp')
    else:
        age = now - source_time
        if age < -timedelta(minutes=2) or age > timedelta(minutes=FRESHNESS_MINUTES):
            errors.append('crossfit_source_not_fresh')
        if created < source_time - timedelta(minutes=2) or created > now + timedelta(minutes=2):
            errors.append('report_generation_not_current')
        if candidate.get('source_generated_at') != crossfit.get('generated_at'):
            errors.append('source_timestamp_mismatch')

    today = _day(candidate.get('as_of_date'))
    if not today or not created or today != created.astimezone(TZ).date():
        errors.append('report_local_day_invalid')

    if candidate.get('sheet_source') != crossfit.get('sheet_source'):
        errors.append('rpe_source_mismatch')

    windows = candidate.get('windows')
    if not isinstance(windows, dict):
        errors.append('windows_missing')
    else:
        for key in ('3d', '7d', '28d'):
            window = windows.get(key)
            if not isinstance(window, dict) or not _count(window.get('recorded_sessions')):
                errors.append(f'window_invalid:{key}')

    chart = candidate.get('daily_chart_28d')
    if not isinstance(chart, list) or len(chart) != 28:
        errors.append('v31_chart_28d_missing')
    elif today:
        expect = [(today - timedelta(days=n)).isoformat() for n in range(27, -1, -1)]
        if [x.get('date') if isinstance(x, dict) else None for x in chart] != expect:
            errors.append('v31_chart_dates_inconsistent')

    report = candidate.get('performance_report_v32')
    if not isinstance(report, dict):
        return errors + ['performance_v32_missing']
    if report.get('version') != '3.2' or report.get('schema_version') != 1:
        errors.append('performance_v32_wrong_contract')
    if report.get('as_of_date') != candidate.get('as_of_date'):
        errors.append('performance_v32_day_mismatch')
    if report.get('timezone') != 'Europe/Madrid':
        errors.append('performance_v32_timezone_invalid')

    provenance = report.get('provenance')
    if not isinstance(provenance, dict) or provenance.get('crossfit_generated_at') != crossfit.get('generated_at'):
        errors.append('performance_v32_source_mismatch')
    if not isinstance(provenance, dict) or provenance.get('sheet_source') != crossfit.get('sheet_source'):
        errors.append('performance_v32_rpe_source_mismatch')

    comparisons = report.get('window_comparison')
    if not isinstance(comparisons, dict):
        errors.append('performance_v32_comparison_missing')
    else:
        groups = comparisons.get('windows')
        if not isinstance(groups, dict):
            errors.append('performance_v32_windows_missing')
        else:
            for key in ('7d', 'previous_7d', '28d'):
                if not isinstance(groups.get(key), dict) or not _count(groups[key].get('sessions')):
                    errors.append(f'performance_v32_window_invalid:{key}')
        week = comparisons.get('current_vs_previous_7d')
        if not isinstance(week, dict) or week.get('comparison_status') not in (
                'descriptive_only', 'insufficient_sessions_in_either_week'):
            errors.append('performance_v32_weekly_comparison_invalid')
        elif week.get('load_metrics_are_not_additive') is not True:
            errors.append('performance_v32_load_guardrail_missing')

    charts = report.get('charts')
    daily = charts.get('daily_28d') if isinstance(charts, dict) else None
    if not isinstance(daily, list) or len(daily) != 28:
        errors.append('performance_v32_chart_28d_missing')
    elif today:
        expect = [(today - timedelta(days=n)).isoformat() for n in range(27, -1, -1)]
        if [x.get('date') if isinstance(x, dict) else None for x in daily] != expect:
            errors.append('performance_v32_chart_dates_inconsistent')
    if not isinstance(charts, dict) or not isinstance(charts.get('rpe_vs_garmin_hr'), list):
        errors.append('performance_v32_rpe_hr_chart_invalid')

    strength = report.get('strength')
    if not isinstance(strength, dict) or not isinstance(strength.get('exact_exercise_groups'), list):
        errors.append('performance_v32_strength_invalid')
    elif strength.get('est_1rm_from_session_rpe') is not False or strength.get('mixed_equipment_tonnage_comparable') is not False:
        errors.append('performance_v32_strength_guardrails_missing')

    quality = report.get('interpretation_quality')
    if not isinstance(quality, dict) or quality.get('no_training_day_is_not_proof_of_rest') is not True:
        errors.append('performance_v32_interpretation_guardrails_missing')
    if not isinstance(report.get('recommendations'), list):
        errors.append('performance_v32_recommendations_missing')
    recovery = report.get('recovery')
    if not isinstance(recovery, dict) or any(not isinstance(recovery.get(key), dict)
                                              for key in ('7d', 'previous_7d', '28d', '7d_vs_previous_7d')):
        errors.append('performance_v32_recovery_missing')
    if not isinstance(report.get('readiness_today'), dict):
        errors.append('performance_v32_readiness_missing')
    if not isinstance(quality, dict) or quality.get('no_set_rir_inferred_from_session_rpe') is not True:
        errors.append('performance_v32_1rm_guardrail_missing')

    return errors


def main(argv=None):
    p = argparse.ArgumentParser(description='Fail-closed, read-only report validation V3.3')
    p.add_argument('--candidate', type=Path, default=Path('.diagnostics_current/training_trends_v31.json'))
    p.add_argument('--crossfit', type=Path, default=Path('crossfit_insights.json'))
    args = p.parse_args(argv)
    try:
        data = _read(args.candidate)
        crossfit = _read(args.crossfit)
        errors = audit(data, crossfit, datetime.now(timezone.utc))
    except (ValueError, OSError) as exc:
        errors = [str(exc)]
    print(json.dumps({'validator':'V3.3','status':'ok' if not errors else 'failed',
                      'candidate':str(args.candidate),'errors':errors}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
