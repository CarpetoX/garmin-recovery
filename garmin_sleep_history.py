#!/usr/bin/env python3
"""Histórico compacto de sueño y promedio nocturno de VFC Garmin (hasta 60 días).

Se ejecuta en Garmin Heart Rate Enrichment con GARMIN_TOKENS_B64.
Guarda los datos asociados al día de despertar, también tras turnos nocturnos.
"""
import base64
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
STORE = Path('garmin_sleep_history.json')
RETENTION_DAYS = 60
BACKFILL_PER_RUN = 4


def n(value, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    value = float(value)
    if (low is not None and value < low) or (high is not None and value > high):
        return None
    return value


def epoch_ms(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (float, int)):
        if 1e12 <= value < 1e13:
            return int(value)
        if 1e9 <= value < 1e10:
            return int(value * 1000)
        return None
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except (ValueError, OverflowError):
            return None
    return None


def local_time(value):
    ms = epoch_ms(value)
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, TZ).isoformat(timespec='seconds')
    except (ValueError, OverflowError, OSError):
        return None


def extract_sleep(raw, day, generated_at):
    if not isinstance(raw, dict):
        return None
    dto = raw.get('dailySleepDTO') or {}
    if not isinstance(dto, dict):
        return None
    start = local_time(dto.get('sleepStartTimestampGMT'))
    end = local_time(dto.get('sleepEndTimestampGMT'))
    asleep_secs = n(dto.get('sleepTimeSeconds'), 600, 72000)
    if not start or not end or asleep_secs is None:
        return None
    begin, finish = datetime.fromisoformat(start), datetime.fromisoformat(end)
    elapsed = (finish - begin).total_seconds()
    if not 600 <= elapsed <= 30 * 3600 or asleep_secs > elapsed + 900:
        return None
    # Do not treat an ongoing sleep as a completed recovery night.
    checked_at = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
    checked_at = checked_at.replace(tzinfo=TZ) if checked_at.tzinfo is None else checked_at.astimezone(TZ)
    if finish > checked_at - timedelta(minutes=5):
        return None
    # Explicit false means Garmin has not confirmed the sleep window yet.
    confirmed = dto.get('sleepWindowConfirmed')
    if confirmed is False:
        return None
    scores = dto.get('sleepScores') or {}
    overall = (scores.get('overall') or {}) if isinstance(scores, dict) else {}
    score = n(overall.get('value'), 0, 100) if isinstance(overall, dict) else None
    midpoint = begin + (finish - begin) / 2
    # Classification is context, never a claim that a shift actually occurred.
    daytime = 8 <= midpoint.hour < 18 or 6 <= begin.hour < 18
    return {
        'date': day.isoformat() if isinstance(day, date) else str(day),
        'generated_at': generated_at,
        'source': 'Garmin Connect get_sleep_data',
        'sleep_hours': round(asleep_secs / 3600, 2),
        'sleep_score': int(score) if score is not None else None,
        'sleep_start_local': start,
        'sleep_end_local': end,
        'sleep_context': 'day_sleep' if daytime else 'night_sleep',
        'window_confirmed': True,
        'deep_minutes': round(n(dto.get('deepSleepSeconds'), 0, 72000) / 60, 1) if n(dto.get('deepSleepSeconds'), 0, 72000) is not None else None,
        'rem_minutes': round(n(dto.get('remSleepSeconds'), 0, 72000) / 60, 1) if n(dto.get('remSleepSeconds'), 0, 72000) is not None else None,
        'note': 'Duración efectiva del sueño Garmin; NO tiempo transcurrido entre acostarse y despertarse.',
    }


def choose_dates(today, rows, cursor):
    all_days = [today - timedelta(days=i) for i in range(RETENTION_DAYS)]
    missing = [d for d in all_days[2:] if not isinstance(rows.get(d.isoformat()), dict) or rows[d.isoformat()].get('sleep_hours') is None or rows[d.isoformat()].get('hrv_ms') is None]
    # Rota los huecos no disponibles para que los días recientes no bloqueen el backfill.
    offset = int(cursor or 0) % max(1, len(missing))
    rotated = missing[offset:] + missing[:offset]
    selected = all_days[:2] + rotated[:BACKFILL_PER_RUN]
    return selected, (offset + BACKFILL_PER_RUN) % max(1, len(missing))


def collect(api, now=None, existing=None):
    now = now or datetime.now(TZ)
    now = now.replace(tzinfo=TZ) if now.tzinfo is None else now.astimezone(TZ)
    old = existing if isinstance(existing, dict) else {}
    rows = dict(old.get('days') or {})
    errors, unavailable = {}, []
    days, cursor = choose_dates(now.date(), rows, old.get('backfill_cursor', 0))
    for d in days:
        key = d.isoformat()
        old = dict(rows.get(key) or {})
        try:
            record = extract_sleep(api.get_sleep_data(key), d, now.isoformat())
            if record:
                old.update(record)
            elif 'sleep_hours' not in old:
                unavailable.append(f'sleep:{key}')
        except Exception as exc:
            errors[f'sleep:{key}'] = f'{type(exc).__name__}: {exc}'
        try:
            raw_hrv = api.get_hrv_data(key)
            summary = raw_hrv.get('hrvSummary') if isinstance(raw_hrv, dict) else None
            hrv = n(summary.get('lastNightAvg'), 1, 500) if isinstance(summary, dict) else None
            if hrv is not None:
                old['hrv_ms'] = hrv
                old['hrv_source'] = 'Garmin Connect get_hrv_data'
            elif old.get('hrv_ms') is None:
                unavailable.append(f'hrv:{key}')
        except Exception as exc:
            errors[f'hrv:{key}'] = f'{type(exc).__name__}: {exc}'
        if old:
            old.setdefault('date', key)
            old['generated_at'] = now.isoformat()
            rows[key] = old
    cutoff = (now.date() - timedelta(days=RETENTION_DAYS - 1)).isoformat()
    rows = {k: v for k, v in sorted(rows.items()) if cutoff <= k <= now.date().isoformat()}
    return {'timezone': 'Europe/Madrid', 'generated_at': now.isoformat(),
            'retention_days': RETENTION_DAYS, 'backfill_cursor': cursor,
            'days': rows, 'unavailable_dates': unavailable, 'fetch_errors': errors}


def main():
    token = os.environ.get('GARMIN_TOKENS_B64', '').strip()
    if not token:
        raise RuntimeError('Falta GARMIN_TOKENS_B64')
    from garminconnect import Garmin
    directory = Path.home() / '.garminconnect'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    tokenfile = directory / 'garmin_tokens.json'
    tokenfile.write_bytes(base64.b64decode(token))
    tokenfile.chmod(0o600)
    api = Garmin()
    api.login(str(directory))
    try:
        existing = json.loads(STORE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        existing = {}
    result = collect(api, existing=existing)
    STORE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'saved_to': str(STORE), 'nights': len(result['days']),
                      'unavailable': result['unavailable_dates'],
                      'errors': result['fetch_errors']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
