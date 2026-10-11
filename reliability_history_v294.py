#!/usr/bin/env python3
"""Garmin Recovery V2.9.4: bounded, evidence-based 7/28-day cycle reliability.

Read-only calculation. A readiness ledger records only successful publications; it
is NOT a GitHub cron audit or evidence of ChatGPT message delivery. Missing due
slots are labelled *not certified in the ledger*, not necessarily Sync failures.
Post-sleep ad-hoc cycles are excluded from nominal scheduled-slot denominators.
"""
import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Europe/Madrid')
# Source: active Garmin workflow schedules and report targets, verified Oct 11.
SLOTS = ((8, 30, 9, 5), (16, 45, 17, 10), (22, 45, 23, 10))
EFFECTIVE_FROM = date(2026, 10, 10)
GRACE_MINUTES = 150


def _dt(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def _slot(day, h, m):
    return datetime.combine(day, time(h, m), tzinfo=ZONE)


def _round_ratio(n, d):
    return round(100 * n / d, 1) if d else None


def _cycle_kind(entry):
    cid = entry.get('cycle_id')
    if not isinstance(cid, str):
        return 'invalid'
    if cid.endswith('-post-sleep'):
        return 'post_sleep'
    return 'official' if len(cid) == 15 and cid[4] == '-' and cid[7] == '-' and cid[10] == '-' and cid[11:].isdigit() else 'other'


def _valid_ready(entry, cid, due, now):
    if not isinstance(entry, dict) or entry.get('cycle_id') != cid or entry.get('state') != 'data_ready':
        return None
    ready = _dt(entry.get('ready_at'))
    if not ready or not (due <= ready <= now):
        return None
    if type(entry.get('sync_run_id')) is not int or entry['sync_run_id'] <= 0:
        return None
    if type(entry.get('crossfit_run_id')) is not int or entry['crossfit_run_id'] <= 0:
        return None
    return ready


def analyze(ledger, now=None, effective_from=EFFECTIVE_FROM, grace_minutes=GRACE_MINUTES):
    """Build a deterministic report; never mutate ledger or extrapolate missing history."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must include timezone')
    if not isinstance(effective_from, date) or isinstance(effective_from, datetime):
        raise ValueError('effective_from must be a date')
    if type(grace_minutes) is not int or not 0 <= grace_minutes <= 1440:
        raise ValueError('invalid grace')
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise ValueError('report_cycles.json must contain cycles list')
    local = now.astimezone(ZONE)
    official = {}
    post_sleep = []
    invalid = 0
    for entry in ledger['cycles']:
        if not isinstance(entry, dict):
            invalid += 1
            continue
        kind = _cycle_kind(entry)
        if kind == 'official':
            official.setdefault(entry['cycle_id'], []).append(entry)
        elif kind == 'post_sleep':
            post_sleep.append(entry)
        else:
            invalid += 1
    # Completed calendar days are required for honest 7/28-day period KPIs.
    # The last 22:45 slot matures at 01:15 on the *next* calendar day.
    yesterday = local.date() - timedelta(days=1)
    mature_at = _slot(yesterday, SLOTS[-1][0], SLOTS[-1][1]) + timedelta(minutes=grace_minutes)
    last_complete_day = yesterday if now >= mature_at else yesterday - timedelta(days=1)
    windows = {}
    for days in (7, 28):
        window_start = last_complete_day - timedelta(days=days - 1)
        observed_start = max(window_start, effective_from)
        expected = []
        ready_count = on_time = 0
        latencies = []
        not_certified = []
        duplicates = []
        for ix in range(days):
            day = window_start + timedelta(days=ix)
            if day < effective_from or day > last_complete_day:
                continue
            for h, m, target_h, target_m in SLOTS:
                due = _slot(day, h, m)
                # Grace is deliberately measured from the due slot, not latest Sync run.
                if now < due + timedelta(minutes=grace_minutes):
                    continue
                cid = f'{day.isoformat()}-{h:02d}{m:02d}'
                target = _slot(day, target_h, target_m)
                matches = official.get(cid, [])
                if len(matches) > 1:
                    duplicates.append(cid)
                valid = [t for t in (_valid_ready(e, cid, due, now) for e in matches) if t]
                certified_at = min(valid) if valid else None
                expected.append(cid)
                if certified_at:
                    ready_count += 1
                    on_time += certified_at <= target
                    latencies.append(round((certified_at - due).total_seconds() / 60, 2))
                else:
                    not_certified.append(cid)
        # All dates in this window are mature; history must reach the first day.
        full = observed_start == window_start
        n = len(expected)
        windows[f'{days}d'] = {
            'status': 'complete_calendar_window_evidence_only' if full else 'provisional_incomplete_window',
            'calendar_window_start': window_start.isoformat(),
            'calendar_window_end': last_complete_day.isoformat(),
            'effective_observation_start': observed_start.isoformat(),
            'as_of': local.isoformat(),
            'matured_scheduled_slots': n,
            'certified_ready': ready_count,
            'not_certified_in_ledger': len(not_certified),
            'certified_ready_coverage_pct': _round_ratio(ready_count, n),
            'ready_by_report_target': on_time,
            'ready_by_target_pct_of_due': _round_ratio(on_time, n),
            'ready_by_target_pct_of_ready': _round_ratio(on_time, ready_count),
            'avg_ready_delay_minutes': round(sum(latencies) / len(latencies), 2) if latencies else None,
            'max_ready_delay_minutes': max(latencies) if latencies else None,
            'missing_cycle_ids': not_certified,
            'duplicate_cycle_ids': duplicates,
            'cron_started_pct': None,
            'cron_started_reason': 'requires_complete_timestamped_GitHub_run_history',
            'chatgpt_delivery_pct': None,
            'chatgpt_delivery_reason': 'requires_delivery_receipts',
            'calendar_window_complete': bool(full and n == days * 3),
            'slo_certified': False,
            'slo_limitation': 'positive_only_ledger; no_complete_negative_run_history',
        }
    # Today's slots remain a separate *partial day* observation.
    today_matured, today_ready, today_on_time = [], 0, 0
    today_unverified = []
    for h, m, target_h, target_m in SLOTS:
        due = _slot(local.date(), h, m)
        if now < due + timedelta(minutes=grace_minutes) or due.date() < effective_from:
            continue
        cid = f'{local.date().isoformat()}-{h:02d}{m:02d}'
        target = _slot(local.date(), target_h, target_m)
        today_matured.append(cid)
        matches = [_valid_ready(e, cid, due, now) for e in official.get(cid, [])]
        valid = [x for x in matches if x is not None]
        if valid:
            today_ready += 1
            if min(valid) <= target:
                today_on_time += 1
        else:
            today_unverified.append(cid)
    today_progress = {
        'status': 'partial_day', 'date': local.date().isoformat(),
        'matured_scheduled_slots': len(today_matured),
        'certified_ready': today_ready, 'ready_by_report_target': today_on_time,
        'certified_ready_coverage_pct': _round_ratio(today_ready, len(today_matured)),
        'not_certified_cycle_ids': today_unverified,
        'not_a_full_day_or_slo': True,
    }
    return {
        'version': '2.9.4',
        'checked_at': now.isoformat(),
        'source': 'report_cycles.json',
        'source_scope': 'successful_certificates_ledger_with_nominal_schedule_reconstruction',
        'schedule_timezone': 'Europe/Madrid',
        'schedule_effective_from': effective_from.isoformat(),
        'post_sleep_entries_excluded_from_denominators': len(post_sleep),
        'invalid_or_unknown_entries_excluded': invalid,
        'warnings': [
            'Without a complete GitHub Actions runs history, cron success is not measurable.',
            'A missing ledger certificate does not by itself prove failed Sync.',
            'A 7/28-day SLO must not be claimed until a complete observed window exists.',
            'No proof of ChatGPT notification delivery is available.',
        ],
        'last_matured_calendar_day': last_complete_day.isoformat(),
        'most_recent_local_date': local.date().isoformat(),
        'windows': windows,
        'today_progress': today_progress,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ledger', default='report_cycles.json')
    ap.add_argument('--out', default='reliability_history_v294.json')
    ap.add_argument('--now', default=None, help='optional timezone-aware ISO instant for deterministic tests')
    args = ap.parse_args(argv)
    ledger = json.loads(Path(args.ledger).read_text(encoding='utf-8'))
    now = _dt(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        raise SystemExit('Invalid --now; an explicit timezone offset is required')
    output = analyze(ledger, now=now)
    Path(args.out).write_text(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status_7d': output['windows']['7d']['status'],
                      'status_28d': output['windows']['28d']['status'],
                      'post_sleep_excluded': output['post_sleep_entries_excluded_from_denominators']}))


if __name__ == '__main__':
    main()
