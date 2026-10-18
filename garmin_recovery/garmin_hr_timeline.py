#!/usr/bin/env python3
"""Persist timestamped Garmin heart-rate samples for real intraday charts.

Run after garmin_metrics.py in the existing GitHub Actions workflow.
Secrets: GARMIN_TOKENS_B64 (the same token used by garmin_metrics.py).

Only actual Garmin samples are written; missing intervals are never inferred.
Timestamps are Unix milliseconds, rendered with timezone Europe/Madrid.
"""

import base64
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
FILE = Path("garmin_hr_timeline.json")
RETENTION_DAYS = 14
BACKFILL_PER_RUN = 4


def to_milliseconds(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if 1_000_000_000_000 <= value <= 10_000_000_000_000:
            return int(value)
        if 1_000_000_000 <= value <= 10_000_000_000:
            return int(value * 1000)
        return None
    if isinstance(value, str):
        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000)
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def local_iso(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000, TZ).isoformat(timespec="seconds")


def extract_hr_samples(raw, day):
    """Returns the actual Garmin points belonging to the Madrid local day.

    Both minute-level and irregularly spaced samples are retained. A repeated
    timestamp is deduplicated; samples are sorted chronologically.
    """
    if not isinstance(raw, dict):
        return []
    day_str = day.isoformat() if isinstance(day, date) else str(day)
    unique = {}
    for point in raw.get("heartRateValues") or []:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        ts = to_milliseconds(point[0])
        bpm = point[1]
        if ts is None or isinstance(bpm, bool) or not isinstance(bpm, (int, float)) or not 20 <= bpm <= 250:
            continue
        try:
            if datetime.fromtimestamp(ts / 1000, TZ).date().isoformat() != day_str:
                continue
        except (OSError, OverflowError, ValueError):
            continue
        unique[ts] = int(bpm) if float(bpm).is_integer() else round(float(bpm), 1)
    return [[ts, unique[ts]] for ts in sorted(unique)]


def extract_sleep_window(raw):
    if not isinstance(raw, dict):
        return None
    dto = raw.get("dailySleepDTO") or {}
    start = to_milliseconds(dto.get("sleepStartTimestampGMT"))
    end = to_milliseconds(dto.get("sleepEndTimestampGMT"))
    if start is None or end is None or end <= start:
        return None
    return {"start_local": local_iso(start), "end_local": local_iso(end)}


def make_day_record(raw, day, generated_at, sleep_windows=None, partial_day=False):
    day_str = day.isoformat() if isinstance(day, date) else str(day)
    samples = extract_hr_samples(raw, day)
    unique_windows = []
    for window in sleep_windows or []:
        if isinstance(window, dict) and window not in unique_windows:
            unique_windows.append(window)
    return {
        "date": day_str,
        "generated_at": generated_at,
        "partial_day": bool(partial_day),
        "sample_count": len(samples),
        "first_sample_local": local_iso(samples[0][0]) if samples else None,
        "last_sample_local": local_iso(samples[-1][0]) if samples else None,
        "sleep_windows_local": unique_windows,
        "samples": samples,
        "note": "FC de Garmin con tiempo real de cada muestra; los huecos no se interpolan.",
    }


def dates_to_fetch(today, days, retention=RETENTION_DAYS, backfill=BACKFILL_PER_RUN):
    """Refresh current and previous day and gradually backfill 14 days."""
    recent = [today - timedelta(days=i) for i in range(retention)]
    refresh = recent[:2]
    missing = [day for day in recent[2:] if day.isoformat() not in days]
    return refresh + missing[:backfill]


def load_store():
    try:
        stored = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(stored, dict) and isinstance(stored.get("days"), dict):
            return stored
    except (OSError, ValueError):
        pass
    return {"timezone": "Europe/Madrid", "days": {}}


def collect(api, now=None, store=None):
    now = now or datetime.now(TZ)
    today = now.date()
    existing = store if isinstance(store, dict) else load_store()
    days = existing.get("days", {})
    if not isinstance(days, dict):
        days = {}
    days = dict(days)
    errors = {}
    sleep_cache = {}

    def sleep_for(day):
        key = day.isoformat()
        if key not in sleep_cache:
            try:
                sleep_cache[key] = api.get_sleep_data(key)
            except Exception as exc:
                sleep_cache[key] = None
                errors[f"sleep:{key}"] = f"{type(exc).__name__}: {exc}"
        return extract_sleep_window(sleep_cache[key])

    for day in dates_to_fetch(today, days):
        key = day.isoformat()
        try:
            raw = api.get_heart_rates(key)
            sleep_windows = [sleep_for(day)]
            if day < today:
                sleep_windows.append(sleep_for(day + timedelta(days=1)))
            record = make_day_record(
                raw, day, now.isoformat(), [x for x in sleep_windows if x], day == today
            )
            if record["sample_count"]:
                days[key] = record
            else:
                errors[key] = "Garmin no devolvio muestras validas; datos previos conservados"
        except Exception as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"

    cutoff = (today - timedelta(days=RETENTION_DAYS - 1)).isoformat()
    days = {k: v for k, v in sorted(days.items()) if cutoff <= k <= today.isoformat()}
    result = {
        "timezone": "Europe/Madrid",
        "generated_at": now.isoformat(),
        "retention_days": RETENTION_DAYS,
        "format": "samples: [unix_epoch_milliseconds, bpm]",
        "days": days,
        "fetch_errors": errors,
    }
    return result


def main():
    token_b64 = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if not token_b64:
        raise RuntimeError("Falta GARMIN_TOKENS_B64")

    token_dir = Path.home() / ".garminconnect"
    token_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_file = token_dir / "garmin_tokens.json"
    token_file.write_bytes(base64.b64decode(token_b64))
    token_file.chmod(0o600)

    from garminconnect import Garmin

    api = Garmin()
    api.login(str(token_dir))
    result = collect(api)
    FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    today_key = datetime.now(TZ).date().isoformat()
    today = result["days"].get(today_key, {})
    print(json.dumps({
        "saved_to": str(FILE),
        "generated_at": result["generated_at"],
        "days_stored": len(result["days"]),
        "today_samples": today.get("sample_count", 0),
        "latest_sample_local": today.get("last_sample_local"),
        "errors": result["fetch_errors"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
