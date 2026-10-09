#!/usr/bin/env python3
"""Histórico nocturno de VFC Garmin, con muestras reales y hora Madrid.

Recupera Garmin Connect get_hrv_data(fecha), preservando la fecha de la
noche que Garmin asigna al registro aunque empiece el día anterior.
Reutiliza GARMIN_TOKENS_B64, igual que garmin_metrics.py.
"""

import base64
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
FILE = Path("garmin_hrv_timeline.json")
RETENTION_DAYS = 14
BACKFILL_PER_RUN = 4


def epoch_millis_utc(value):
    """Interpreta *GMT* como UTC, nunca como hora local del runner."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if 1_000_000_000_000 <= value <= 10_000_000_000_000:
            return int(value)
        if 1_000_000_000 <= value <= 10_000_000_000:
            return int(value * 1000)
        return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return int(parsed.timestamp() * 1000)
        except (TypeError, ValueError, OverflowError):
            return None
    return None


def local_iso(ms):
    return (datetime.fromtimestamp(ms / 1000, TZ).isoformat(timespec="seconds")
            if ms is not None else None)


def valid_number(value, lower, upper):
    return (value if isinstance(value, (int, float)) and not isinstance(value, bool)
            and lower <= value <= upper else None)


def parse_hrv_readings(raw):
    """[UTC epoch ms, VFC ms]. No rellena huecos ni genera muestras."""
    if not isinstance(raw, dict):
        return []
    dedup = {}
    for entry in raw.get("hrvReadings") or []:
        if not isinstance(entry, dict):
            continue
        ts = epoch_millis_utc(entry.get("readingTimeGMT"))
        value = valid_number(entry.get("hrvValue"), 1, 500)
        if ts is None or value is None:
            continue
        try:
            datetime.fromtimestamp(ts / 1000, TZ)
        except (ValueError, OverflowError, OSError):
            continue
        dedup[ts] = int(value) if float(value).is_integer() else round(value, 2)
    return [[ts, dedup[ts]] for ts in sorted(dedup)]


def build_record(raw, night_date, generated_at):
    """Una noche pertenece al día solicitado, aunque empiece el día anterior."""
    day = night_date.isoformat() if isinstance(night_date, date) else str(night_date)
    readings = parse_hrv_readings(raw)
    summary = (raw.get("hrvSummary") or {}) if isinstance(raw, dict) else {}
    if not isinstance(summary, dict):
        summary = {}
    baseline = summary.get("baseline") or {}
    if not isinstance(baseline, dict):
        baseline = {}

    start = epoch_millis_utc(raw.get("sleepStartTimestampGMT")) if isinstance(raw, dict) else None
    end = epoch_millis_utc(raw.get("sleepEndTimestampGMT")) if isinstance(raw, dict) else None
    if start is None:
        start = epoch_millis_utc(raw.get("startTimestampGMT")) if isinstance(raw, dict) else None
    if end is None:
        end = epoch_millis_utc(raw.get("endTimestampGMT")) if isinstance(raw, dict) else None

    nightly_avg = valid_number(summary.get("lastNightAvg"), 1, 500)
    weekly_avg = valid_number(summary.get("weeklyAvg"), 1, 500)
    highest_5min = valid_number(summary.get("lastNight5MinHigh"), 1, 500)
    return {
        "date": day,
        "generated_at": generated_at,
        "source": "Garmin Connect get_hrv_data",
        "sample_count": len(readings),
        "night_avg_ms": nightly_avg,
        "weekly_avg_ms": weekly_avg,
        "highest_5min_ms": highest_5min,
        "garmin_status": summary.get("status"),
        "baseline_ms": {
            "balanced_low": valid_number(baseline.get("balancedLow"), 1, 500),
            "balanced_upper": valid_number(baseline.get("balancedUpper"), 1, 500),
        },
        "sleep_start_local": local_iso(start),
        "sleep_end_local": local_iso(end),
        "first_sample_local": local_iso(readings[0][0]) if readings else None,
        "last_sample_local": local_iso(readings[-1][0]) if readings else None,
        "samples": readings,
        "note": "VFC durante sueño; muestras Garmin por bloques aproximados de 5 min. No hay interpolación ni medición continua de VFC diurna.",
    }


def has_data(record):
    return bool(record.get("sample_count")) or record.get("night_avg_ms") is not None


def dates_to_fetch(today, stored_days, cursor=0):
    """Reconsulta las últimas 2 noches; rellena huecos del resto rotando."""
    recent = [today - timedelta(days=i) for i in range(RETENTION_DAYS)]
    fresh = recent[:2]
    previous = recent[2:]
    if not previous:
        return fresh, 0
    start = cursor % len(previous)
    rotated = previous[start:] + previous[:start]
    chosen = [day for day in rotated if not has_data(stored_days.get(day.isoformat(), {}))]
    # Se avanza siempre, incluso si Garmin aún no dispone de esos datos.
    new_cursor = (start + BACKFILL_PER_RUN) % len(previous)
    return fresh + chosen[:BACKFILL_PER_RUN], new_cursor


def load_store(path=FILE):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("days"), dict):
            return data
    except (OSError, ValueError):
        pass
    return {"timezone": "Europe/Madrid", "days": {}, "backfill_cursor": 0}


def collect(api, now=None, store=None):
    now = now or datetime.now(TZ)
    today = now.astimezone(TZ).date() if now.tzinfo else now.replace(tzinfo=TZ).date()
    base = store if isinstance(store, dict) else load_store()
    saved = base.get("days", {})
    saved = dict(saved) if isinstance(saved, dict) else {}
    dates, next_cursor = dates_to_fetch(today, saved, base.get("backfill_cursor", 0))
    errors = {}
    unavailable = []
    for day in dates:
        key = day.isoformat()
        try:
            raw = api.get_hrv_data(key)
            record = build_record(raw, day, now.isoformat())
            if has_data(record):
                # Conserva un registro anterior con mayor cobertura si la API
                # devuelve menos lecturas y no mejora los campos de resumen.
                previous = saved.get(key, {})
                if record["sample_count"] == 0 and previous.get("sample_count", 0) > 0:
                    previous.update({k: v for k, v in record.items()
                                     if k in ("night_avg_ms", "weekly_avg_ms", "highest_5min_ms")
                                     and v is not None})
                    saved[key] = previous
                else:
                    saved[key] = record
            else:
                unavailable.append(key)
        except Exception as exc:
            errors[key] = f"{type(exc).__name__}: {exc}"
    cutoff = (today - timedelta(days=RETENTION_DAYS - 1)).isoformat()
    saved = {k: v for k, v in sorted(saved.items()) if cutoff <= k <= today.isoformat()}
    valid_averages = [(day, row["night_avg_ms"]) for day, row in saved.items()
                      if row.get("night_avg_ms") is not None and day < today.isoformat()]
    avg_7_nights = valid_averages[-7:]
    return {
        "timezone": "Europe/Madrid",
        "generated_at": now.isoformat(),
        "retention_days": RETENTION_DAYS,
        "format": "samples: [UTC_unix_epoch_milliseconds, HRV_milliseconds]",
        "night_association": "Garmin HRV calendarDate, NO día natural de la marca temporal",
        "backfill_cursor": next_cursor,
        "days": saved,
        "last_7_completed_nights": {
            "dates": [d for d, _ in avg_7_nights],
            "nightly_averages_mean_ms": (round(sum(v for _, v in avg_7_nights) / len(avg_7_nights), 1)
                                         if avg_7_nights else None),
            "nights_present": len(avg_7_nights),
        },
        "unavailable_dates": unavailable,
        "fetch_errors": errors,
    }


def main():
    token = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if not token:
        raise RuntimeError("No está disponible GARMIN_TOKENS_B64")
    token_dir = Path.home() / ".garminconnect"
    token_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    token_file = token_dir / "garmin_tokens.json"
    token_file.write_bytes(base64.b64decode(token))
    token_file.chmod(0o600)
    from garminconnect import Garmin
    api = Garmin()
    api.login(str(token_dir))
    payload = collect(api)
    FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    today = datetime.now(TZ).date().isoformat()
    rec = payload["days"].get(today, {})
    print(json.dumps({
        "saved_to": str(FILE),
        "generated_at": payload["generated_at"],
        "days_stored": len(payload["days"]),
        "today_readings": rec.get("sample_count", 0),
        "latest_sample_local": rec.get("last_sample_local"),
        "unavailable_dates": payload["unavailable_dates"],
        "fetch_errors": payload["fetch_errors"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
