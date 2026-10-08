"""Data quality and seven-day summaries; never infer missing measurements."""
from collections import Counter
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')

def _date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None

def _age_hours(value, now):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return round((now - dt.astimezone(TZ)).total_seconds() / 3600, 1)
    except (ValueError, TypeError):
        return None

def analyze(rows, activities, advanced, now, sheet_source, sheet_error):
    """Return diagnostics and a descriptive weekly report, not medical advice."""
    today = now.date()
    start = today - timedelta(days=6)
    dates = [_date(a.get('date')) for a in activities]
    week = [a for a, d in zip(activities, dates) if d is not None and start <= d <= today]
    manual_week = [a for a in week if a.get('manual_match') == 'sheet_id']
    missing_manual = [str(a.get('activity_id')) for a in week if a.get('manual_match') == 'unmatched']
    sheet_ids = [str(r.get('ID actividad', '')).strip() for r in rows if r.get('ID actividad')]
    duplicates = sorted(k for k, v in Counter(sheet_ids).items() if v > 1)
    rpe_vals = [a.get('rpe_used') for a in week if isinstance(a.get('rpe_used'), (int, float))]
    strength = []
    for a in week:
        for block in a.get('manual_blocks', []):
            if block.get('structured_sets_total', 0):
                strength.append(block)
    known_volume = round(sum(b.get('minimum_verified_volume_kg') or 0 for b in strength), 1)
    incomplete_strength = sum(not b.get('volume_complete', False) for b in strength)
    advanced_age = _age_hours(advanced.get('generated_at'), now)
    latest_activity = max((d for d in dates if d and d <= today), default=None)
    activity_age_days = (today - latest_activity).days if latest_activity else None
    flags = []
    if sheet_source != 'live_csv':
        flags.append({'severity':'error','code':'sheet_unavailable','detail':sheet_error or 'CSV not loaded'})
    if sheet_source == 'live_csv' and not rows:
        flags.append({'severity':'warning','code':'sheet_empty','detail':'CSV loaded but contains no activity rows'})
    if duplicates:
        flags.append({'severity':'warning','code':'duplicate_sheet_ids','count':len(duplicates),'ids':duplicates[:20]})
    if advanced_age is None:
        flags.append({'severity':'warning','code':'advanced_timestamp_unknown'})
    elif advanced_age > 30:
        flags.append({'severity':'warning','code':'advanced_data_stale','age_hours':advanced_age})
    if activity_age_days is None:
        flags.append({'severity':'warning','code':'no_activities_available'})
    elif activity_age_days > 3:
        flags.append({'severity':'info','code':'no_recent_activities','days':activity_age_days,'note':'May simply be rest days; not proof of sync failure'})
    if missing_manual:
        flags.append({'severity':'info','code':'activities_without_manual_rpe','count':len(missing_manual),'ids':missing_manual[:20]})
    if incomplete_strength:
        flags.append({'severity':'info','code':'incomplete_strength_weights','count':incomplete_strength})
    if len(week) < 3:
        flags.append({'severity':'info','code':'limited_weekly_sample','activities':len(week)})
    quality = 'error' if any(f['severity']=='error' for f in flags) else ('attention' if any(f['severity']=='warning' for f in flags) else 'ok')
    # These percentages describe manual logging coverage, not physiological data quality.
    manual_coverage = round(100*len(manual_week)/len(week), 1) if week else None
    return {
        'data_quality': {
            'status':quality,'checked_at':now.isoformat(),'advanced_age_hours':advanced_age,
            'latest_activity_date':latest_activity.isoformat() if latest_activity else None,
            'latest_activity_age_days':activity_age_days,
            'sheet_rows':len(rows),'manual_coverage_7d_pct':manual_coverage,
            'flags':flags,
            'scope_note':'No activity for 3+ days may reflect rest; freshness of Garmin raw measurements is not verified from this summary alone.'
        },
        'weekly_report': {
            'window_start':start.isoformat(),'window_end':today.isoformat(),
            'activities':len(week),'activities_with_manual_sheet_match':len(manual_week),
            'activities_missing_manual_match':len(missing_manual),
            'mean_rpe':round(sum(rpe_vals)/len(rpe_vals),2) if rpe_vals else None,
            'recorded_srpe_sum':round(sum(a.get('srpe_using_recorded_minutes') or 0 for a in week),1) if week else None,
            'recorded_srpe_note':'Only recorded duration x RPE; not equivalent to effective WOD duration, and not comparable with TRIMP.',
            'minimum_verified_strength_volume_kg':known_volume if strength else None,
            'strength_blocks_with_missing_weights':incomplete_strength,
            'readiness_latest':advanced.get('readiness_hybrid'),
            'recommendation':'Interpret trends cautiously; compare only equivalent workouts and consider shift-work and subjective symptoms.',
            'confidence':'limited' if len(week)<5 or manual_coverage is None or manual_coverage<70 or incomplete_strength else 'moderate',
            'not_a_diagnosis':True
        }
    }
