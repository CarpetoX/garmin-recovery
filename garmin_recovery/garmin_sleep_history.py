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

from . import sleep_stages as _stages

TZ = ZoneInfo('Europe/Madrid')
STORE = Path('garmin_sleep_history.json')
OVERRIDES = Path('manual_sleep_overrides.json')
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
    # Si Garmin informa de tiempo despierto, el sueño efectivo no puede ocupar toda la ventana.
    awake_secs = n(dto.get('awakeSleepSeconds'), 0, 72000)
    if awake_secs and asleep_secs > elapsed - awake_secs + 600:
        asleep_secs = max(600, elapsed - awake_secs)
    scores = dto.get('sleepScores') or {}
    overall = (scores.get('overall') or {}) if isinstance(scores, dict) else {}
    score = n(overall.get('value'), 0, 100) if isinstance(overall, dict) else None
    midpoint = begin + (finish - begin) / 2
    # Classification is context, never a claim that a shift actually occurred.
    daytime = 8 <= midpoint.hour < 18 or 6 <= begin.hour < 18
    out = {
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
    flag = _stages.check(out['sleep_hours'], out['deep_minutes'], out['rem_minutes'])  # V9.7
    if flag:
        out['stages_suspect'] = flag
    return out


def _nap_time(v, local=False):
    """Marca de tiempo de Garmin (ms epoch o ISO; sin zona = GMT, o Madrid si la clave es «local») → datetime en Madrid."""
    if isinstance(v, (int, float)) and v > 10**11:
        return datetime.fromtimestamp(v / 1000, tz=timezone.utc).astimezone(TZ)
    if isinstance(v, str) and len(v) >= 16:
        try:
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            return None
        return (dt if dt.tzinfo else dt.replace(tzinfo=TZ if local else timezone.utc)).astimezone(TZ)
    return None


def extract_naps(raw):
    """V9.6: siestas de /sleep-service/sleep/naps. Solo describe; no entra en la recuperación.

    Busca en cada elemento una clave de inicio y otra de fin (preferencia GMT) y descarta lo incoherente
    (fin antes del inicio o más de 4 h)."""
    items = raw if isinstance(raw, list) else (raw.get('naps') or raw.get('dailyNapDTOS') or []) if isinstance(raw, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        keys = sorted(it, key=lambda k: ('gmt' not in k.lower(), k))
        start = next((_nap_time(it[k], 'local' in k.lower()) for k in keys if 'start' in k.lower() and _nap_time(it[k])), None)
        end = next((_nap_time(it[k], 'local' in k.lower()) for k in keys if 'end' in k.lower() and _nap_time(it[k])), None)
        if not start or not end:
            continue
        minutes = round((end - start).total_seconds() / 60)
        if not 5 <= minutes <= 240:
            continue
        out.append({'start_local': start.isoformat(timespec='minutes'), 'end_local': end.isoformat(timespec='minutes'),
                    'minutes': minutes, 'source': 'Garmin Connect siestas'})
    return sorted(out, key=lambda x: x['start_local'])


def choose_dates(today, rows, cursor):
    all_days = [today - timedelta(days=i) for i in range(RETENTION_DAYS)]
    missing = [d for d in all_days[2:] if not isinstance(rows.get(d.isoformat()), dict) or rows[d.isoformat()].get('sleep_hours') is None or rows[d.isoformat()].get('hrv_ms') is None]
    # Rota los huecos no disponibles para que los días recientes no bloqueen el backfill.
    offset = int(cursor or 0) % max(1, len(missing))
    rotated = missing[offset:] + missing[:offset]
    selected = all_days[:2] + rotated[:BACKFILL_PER_RUN]
    return selected, (offset + BACKFILL_PER_RUN) % max(1, len(missing))


def collect(api, now=None, existing=None, overrides=None):
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
        fetch_naps = getattr(api, 'get_naps', None)
        if fetch_naps is None and hasattr(api, 'connectapi'):
            def fetch_naps(k):
                return api.connectapi(f'/sleep-service/sleep/naps/{k}', params={'includeOverlaps': 'true'})
        if fetch_naps is not None and d in days[:2]:  # V9.6: siestas solo de hoy y ayer (2 llamadas por ciclo)
            try:
                naps = extract_naps(fetch_naps(key))
                if naps:  # sin siestas no se crea ni se borra nada
                    old['naps'] = naps
                    old['nap_minutes'] = sum(x['minutes'] for x in naps)
            except Exception as exc:
                errors[f'naps:{key}'] = f'{type(exc).__name__}: {str(exc)[:160]}'
        fix = (overrides or {}).get(key)
        if isinstance(fix, dict) and fix:
            old.update({k: v for k, v in fix.items() if k != 'reason'})
            old['source'] = 'Garmin Connect + corrección manual desde el reloj'
            if fix.get('reason'):
                old['note'] = str(fix['reason'])
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
    try:
        overrides = json.loads(OVERRIDES.read_text(encoding='utf-8')).get('days') or {}
    except (OSError, ValueError, AttributeError):
        overrides = {}
    result = collect(api, existing=existing, overrides=overrides)
    STORE.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'saved_to': str(STORE), 'nights': len(result['days']),
                      'unavailable': result['unavailable_dates'],
                      'errors': result['fetch_errors']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
