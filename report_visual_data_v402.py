#!/usr/bin/env python3
"""V4.0.2: only certified daily data for visual trends, strength and intensity.

No network, no ingestion of unverified live files. Values missing from snapshots
remain missing. The historical ledger may contain multiple cycles per day:
choose the latest VERIFIED snapshot of each calendar day. Never sum overlapping
seven-day windows across cycles.
"""
from __future__ import annotations

from datetime import date, timedelta
import math
import re

from cycle_snapshot_report_v38 import build, SnapshotError


def obj(v):
    return v if isinstance(v, dict) else {}


def num(v):
    return type(v) in (float, int) and math.isfinite(v)


def valid_day(s):
    if not isinstance(s, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        return None
    try:
        d = date.fromisoformat(s)
    except ValueError:
        return None
    return d if d.isoformat() == s else None


def verified_days(ledger, cycle_id, window=28):
    """Verified latest snapshot per day for last 28 days, inclusive.

    A damaged older row is quarantined from trends (with count) but never read.
    The chosen cycle is validated by the caller and cannot be bypassed.
    """
    anchor = valid_day(cycle_id[:10])
    if anchor is None or window != 28:
        raise SnapshotError('Invalid visual historical window')
    first = anchor - timedelta(days=window - 1)
    selected, quarantined = {}, []
    for row in ledger.get('cycles', []) if isinstance(ledger, dict) else []:
        if not isinstance(row, dict):
            continue
        cid = row.get('cycle_id')
        d = valid_day(cid[:10]) if isinstance(cid, str) else None
        if d is None or not first <= d <= anchor:
            continue
        if not isinstance(row.get('snapshot'), dict):
            # Historical legacy records carry no verifiable data.
            continue
        try:
            record = build(ledger, cid)  # SHA, source provenance, state, date.
        except (SnapshotError, ValueError, KeyError, TypeError):
            quarantined.append(cid)
            continue
        if not isinstance(row.get('ready_at'), str):
            quarantined.append(cid)
            continue
        # Compare ISO instants only for same date and same timezone-format; stable
        # cycle-id tie break keeps determinism on a duplicated publication time.
        sort_key = (row['ready_at'], cid)
        if d not in selected or sort_key > selected[d][0]:
            selected[d] = (sort_key, record)
    return {d: item[1]['data'] for d, item in selected.items()}, sorted(set(quarantined))


def _confirmed(snapshot, d):
    rec = obj(snapshot.get('recovery_assessment'))
    curr = obj(rec.get('current'))
    sleep = obj(snapshot.get('morning_sleep'))
    return (curr.get('date') == d.isoformat() and rec.get('state') == 'assessed'
            and sleep.get('state') == 'confirmed_ready' and sleep.get('evidence_valid') is True)


def series(days, anchor, metric):
    """Seven days of distinct-date measurements, None for unavailable days."""
    getter = {
        'hrv': lambda s: obj(obj(s.get('recovery_assessment')).get('current')).get('hrv_ms'),
        'sleep': lambda s: obj(obj(s.get('recovery_assessment')).get('current')).get('sleep_hours'),
        'rhr': lambda s: obj(obj(s.get('garmin')).get('heart_rate_today')).get('resting_hr'),
        'body_battery': lambda s: obj(obj(s.get('garmin')).get('body_battery_today')).get('latest'),
        'recovery': lambda s: obj(s.get('recovery_assessment')).get('score'),
    }[metric]
    results = []
    for offset in range(6, -1, -1):
        d = anchor - timedelta(days=offset)
        snap = days.get(d, {})
        v = getter(snap)
        if metric in ('hrv', 'sleep', 'recovery') and not _confirmed(snap, d):
            v = None
        elif metric == 'rhr':
            hr = obj(obj(snap.get('garmin')).get('heart_rate_today'))
            if hr.get('date') != d.isoformat():
                v = None
        elif metric == 'body_battery':
            raw = obj(obj(snap.get('garmin')).get('body_battery_today'))
            ts = raw.get('endTimestampLocal')
            if not isinstance(ts, str) or not ts.startswith(d.isoformat()):
                v = None  # Date of last measure not certified.
        if not num(v) or v < 0:
            v = None
        results.append({'date': d.isoformat(), 'value': v})
    return results


def week_load(snapshot, anchor):
    perf = obj(obj(snapshot.get('crossfit')).get('performance_report'))
    chart = perf.get('daily_chart_7d')
    if not isinstance(chart, list) or len(chart) != 7:
        return []
    dates = [(anchor - timedelta(days=n)).isoformat() for n in range(6, -1, -1)]
    if any(not isinstance(v, dict) or v.get('date') != expected
           or not num(v.get('srpe_from_recorded_duration')) or v['srpe_from_recorded_duration'] < 0
           for v, expected in zip(chart, dates)):
        return []
    return [{'date': v['date'], 'value': v['srpe_from_recorded_duration']} for v in chart]


def heatmap(days, anchor, weekly_load):
    """Calendar statuses. Recent training load comes only from current 7d chart."""
    loads = {r['date']: r['value'] for r in weekly_load}
    output = []
    for offset in range(27, -1, -1):
        d = anchor - timedelta(days=offset)
        snap = days.get(d)
        rec = obj(snap.get('recovery_assessment')) if snap else {}
        measured = _confirmed(snap, d) if snap else False
        score = rec.get('score') if measured else None
        if not num(score) or not 0 <= score <= 100:
            score = None
        status = 'confirmed' if score is not None else 'pending' if snap else 'missing'
        load = loads.get(d.isoformat())
        output.append({'date': d.isoformat(), 'recovery_score': score,
                       'state': status, 'load': load})
    return output


def exercise_group(name):
    if not isinstance(name, str):
        return None
    clean = name.strip().lower()
    aliases = {
        'back squat': 'Sentadilla trasera', 'sentadilla trasera': 'Sentadilla trasera',
        'front squat': 'Sentadilla frontal', 'sentadilla frontal': 'Sentadilla frontal',
        'deadlift': 'Peso muerto', 'peso muerto': 'Peso muerto',
        'bench press': 'Press banca', 'press banca': 'Press banca',
        'clean': 'Clean', 'squat clean': 'Clean', 'clean squat': 'Clean',
        'snatch': 'Snatch', 'strict press': 'Press estricto',
    }
    return aliases.get(clean)


def verified_strength(days, anchor):
    """Only EXPLICITLY confirmed manual barbell sets within certified snapshots.

    Expected future snapshot schema: crossfit.activities_today[].manual_strength_sets
    each {exercise, equipment: barbell/dumbbell/machine, weight_kg, reps,
    verified: true}. Dumbbells require weight_basis='per_hand'; machines require
    a stable machine_id. Equipment is never combined across series.
    No inference from Garmin classifications, summary tonnage, or equipment conversions.
    """
    points = {}
    skipped = 0
    for d, snap in days.items():
        activities = obj(snap.get('crossfit')).get('activities_today')
        if not isinstance(activities, list):
            continue
        for act in activities:
            if not isinstance(act, dict) or str(act.get('date') or act.get('start_date_local') or '')[:10] != d.isoformat():
                continue
            identity = act.get('activity_id')
            if not isinstance(identity, (str, int)) or not str(identity).strip():
                continue
            sets = act.get('manual_strength_sets')
            if not isinstance(sets, list):
                continue
            for set_no, item in enumerate(sets):
                s = obj(item)
                name = exercise_group(s.get('exercise'))
                weight = s.get('weight_kg')
                reps = s.get('reps')
                equipment = s.get('equipment')
                if (name is None or s.get('verified') is not True or equipment not in ('barbell','dumbbell','machine')
                    or not num(weight) or weight <= 0 or weight > 500
                    or type(reps) is not int or not 1 <= reps <= 200):
                    skipped += 1
                    continue
                if equipment == 'dumbbell':
                    if s.get('weight_basis') != 'per_hand':
                        skipped += 1
                        continue
                    name += ' · mancuerna (por mano)'
                elif equipment == 'machine':
                    machine_id = s.get('machine_id')
                    if not isinstance(machine_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,24}', machine_id):
                        skipped += 1
                        continue
                    name += ' · máquina ' + machine_id
                key = (d.isoformat(), str(identity), set_no, name)
                points[key] = {'date': d.isoformat(), 'exercise': name, 'kg': weight, 'reps': reps}
    grouped = {}
    for point in points.values():
        grouped.setdefault(point['exercise'], []).append(point)
    return {k: sorted(v, key=lambda x: (x['date'], x['kg'])) for k, v in sorted(grouped.items())}, skipped


def intensity(days, anchor):
    """Day-by-day Garmin zone totals and type distribution, with explicit coverage."""
    sums, types = [0.0] * 5, {}
    zone_days, type_days = 0, 0
    for offset in range(6, -1, -1):
        d = anchor - timedelta(days=offset)
        snap = days.get(d)
        if not snap:
            continue
        training = obj(obj(snap.get('daily')).get('training_today'))
        zones = training.get('hr_zone_times_secs')
        if (isinstance(zones, list) and len(zones) == 5
            and all(num(v) and v >= 0 for v in zones)
            and sum(zones) > 0):
            sums = [a+b for a,b in zip(sums, zones)]
            zone_days += 1
        counts = training.get('session_type_distribution')
        if isinstance(counts, dict) and all(isinstance(k, str) and num(v) and v >= 0 for k,v in counts.items()):
            types = {k: types.get(k, 0) + v for k, v in counts.items()}
            type_days += 1
    return {'zone_minutes': [round(x/60, 1) for x in sums],
            'zone_days': zone_days, 'type_counts': dict(sorted(types.items())),
            'type_days': type_days}


def stage_segments(snapshot, current, confirmed):
    """Only render actual ordered stage events with explicit ISO timestamps.

    No reconstruction of order from aggregated phase durations.
    """
    if not confirmed:
        return []
    stages = obj(obj(snapshot.get('garmin')).get('extended_today')).get('sleep_detail')
    source = obj(stages).get('stage_segments')
    if not isinstance(source, list) or not source or len(source) > 300:
        return []
    from datetime import datetime
    try:
        begin = datetime.fromisoformat(current['sleep_start_local'])
        end = datetime.fromisoformat(current['sleep_end_local'])
        if begin.tzinfo is None or end.tzinfo is None or begin >= end:
            return []
        normalized = []
        prev_end = begin
        for v in source:
            if not isinstance(v, dict) or v.get('stage') not in ('deep', 'light', 'rem', 'awake'):
                return []
            a, b = datetime.fromisoformat(v['start']), datetime.fromisoformat(v['end'])
            if a.tzinfo is None or b.tzinfo is None or a < begin or a < prev_end or b > end or b <= a:
                return []
            normalized.append({'stage':v['stage'],'start':v['start'],'end':v['end'],
                               'start_fraction':(a-begin).total_seconds()/(end-begin).total_seconds(),
                               'width_fraction':(b-a).total_seconds()/(end-begin).total_seconds()})
            prev_end = b
        return normalized
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return []


def model(ledger, cycle_id, cert, v401_metadata):
    anchor = valid_day(cycle_id[:10])
    if anchor is None:
        raise SnapshotError('Invalid visual model date')
    days, quarantined = verified_days(ledger, cycle_id)
    current = cert['data']
    load = week_load(current, anchor)
    rec = obj(current.get('recovery_assessment'))
    strength, rejected_sets = verified_strength(days, anchor)
    trend = {metric: series(days, anchor, metric) for metric in ('hrv','sleep','rhr','body_battery','recovery')}
    trend['srpe'] = load
    return {
        'date': anchor.isoformat(), 'historical_days': len(days),
        'quarantined_cycle_ids': quarantined,
        'series': trend, 'heatmap': heatmap(days, anchor, load),
        'strength': strength, 'strength_excluded_sets': rejected_sets,
        'intensity': intensity(days, anchor),
        'sleep_timeline': stage_segments(current, obj(rec.get('current')), v401_metadata['sleep_confirmed']),
        'sleep_confirmed': v401_metadata['sleep_confirmed'],
        'comparison_status': 'not_recomputed_v401_comparator_preserved',
    }
