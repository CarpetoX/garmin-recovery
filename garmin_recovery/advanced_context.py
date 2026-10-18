"""Contexto del día (turno, sueño) y construcción de los registros diarios."""
from datetime import timedelta
import base64
import json
import os
from .advanced_core import PATHS, load_json, num, parse_dt


def decode_context_map():
    merged = {}

    file_data = load_json(PATHS["context"], {})
    if isinstance(file_data, dict):
        file_days = file_data.get("days", file_data)
        if isinstance(file_days, dict):
            merged.update(file_days)

    raw = os.environ.get("DAY_CONTEXT_B64", "").strip()
    if raw:
        try:
            data = json.loads(base64.b64decode(raw).decode("utf-8"))
            if isinstance(data, dict):
                env_days = data.get("days", data)
                if isinstance(env_days, dict):
                    merged.update(env_days)
        except Exception:
            pass

    from .shift_calendar import context_map as shift_context_map
    return shift_context_map({
        str(k): str(v) for k, v in merged.items() if isinstance(v, str)
    })

def infer_sleep_context(hr_row):
    if not isinstance(hr_row, dict):
        return "unknown"

    start = parse_dt(hr_row.get("sleep_start_local"))
    end = parse_dt(hr_row.get("sleep_end_local"))

    if not start or not end:
        return "unknown"

    if end <= start:
        end += timedelta(days=1)

    midpoint = start + (end - start) / 2

    if 8 <= midpoint.hour < 18 or 6 <= start.hour < 18:
        return "day_sleep"

    return "night_sleep"

def bb_latest(raw):
    if not isinstance(raw, dict):
        return None

    values = raw.get("bodyBatteryValuesArray") or []
    out = []

    for item in values:
        if not isinstance(item, (list, tuple)):
            continue

        candidate = None
        if len(item) >= 3 and num(item[2]) is not None:
            candidate = num(item[2])
        elif len(item) >= 2 and num(item[1]) is not None:
            candidate = num(item[1])

        if candidate is not None:
            out.append(candidate)

    return out[-1] if out else None

def stress_avg(raw):
    if not isinstance(raw, dict):
        return None

    return (
        num(raw.get("avgStressLevel"))
        or num(raw.get("averageStressLevel"))
    )

def sleep_hours_from_wellness(row):
    secs = num(row.get("sleepSecs")) if isinstance(row, dict) else None
    return round(secs / 3600, 2) if secs is not None else None

def build_day_records(wellness, heart, extended, stress, bb, context_map):
    well_by_date = {
        x.get("id"): x
        for x in wellness
        if isinstance(x, dict) and isinstance(x.get("id"), str)
    }

    hr_days = heart.get("days", {}) if isinstance(heart, dict) else {}
    ext_days = extended.get("days", {}) if isinstance(extended, dict) else {}
    stress_days = stress.get("days", {}) if isinstance(stress, dict) else {}
    bb_days = bb.get("days", {}) if isinstance(bb, dict) else {}

    all_dates = sorted(
        set(well_by_date)
        | set(hr_days)
        | set(ext_days)
        | set(stress_days)
        | set(bb_days)
    )

    records = {}

    for ds in all_dates:
        w = well_by_date.get(ds, {})
        h = hr_days.get(ds, {}) if isinstance(hr_days.get(ds), dict) else {}
        e = ext_days.get(ds, {}) if isinstance(ext_days.get(ds), dict) else {}
        am = (
            e.get("activity_metrics")
            if isinstance(e.get("activity_metrics"), dict)
            else {}
        )

        context = context_map.get(ds) or infer_sleep_context(h)

        records[ds] = {
            "date": ds,
            "context": context,
            "hrv": num(w.get("hrv")),
            "resting_hr": num(w.get("restingHR")) or num(h.get("resting_hr")),
            "sleep_hours": sleep_hours_from_wellness(w),
            "sleep_score": num(w.get("sleepScore")),
            "respiration": num(w.get("respiration")),
            "steps": num(w.get("steps")),
            "daytime_hr": num(h.get("daytime_avg_hr")),
            "nighttime_hr": num(h.get("nighttime_avg_hr")),
            "day_minus_night_bpm": num(h.get("day_minus_night_bpm")),
            "hr_partial_day": bool(h.get("partial_day")),
            "day_hr_samples": int(num(h.get("daytime_sample_count")) or 0),
            "night_hr_samples": int(num(h.get("nighttime_sample_count")) or 0),
            "sleep_window_available": bool(h.get("sleep_window_available")),
            "stress_avg": stress_avg(stress_days.get(ds)),
            "body_battery_latest": bb_latest(bb_days.get(ds)),
            "training_load_garmin": (
                num(am.get("total_training_load"))
                if isinstance(am, dict)
                else None
            ),
            "activity_count": (
                int(num(am.get("activity_count")) or 0)
                if isinstance(am, dict)
                else 0
            ),
        }

    return records
