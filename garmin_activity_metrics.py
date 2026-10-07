import os
import json
import base64
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime.now(TZ)
TODAY = NOW.date()

EXTENDED_PATH = Path("garmin_extended.json")
STATUS_PATH = Path("garmin_status.json")
DAILY_PATH = Path("daily_summary.json")
WEEKLY_PATH = Path("weekly_summary.json")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def activity_id_of(raw):
    if not isinstance(raw, dict):
        return None
    return raw.get("activityId") or raw.get("activityID") or raw.get("id")


def activity_date_of(raw):
    if not isinstance(raw, dict):
        return None
    value = raw.get("startTimeLocal") or raw.get("startTimeGMT")
    if isinstance(value, str) and len(value) >= 10:
        return value[:10]
    value = raw.get("calendarDate")
    return value if isinstance(value, str) else None


def activity_type_key(raw):
    if not isinstance(raw, dict):
        return None
    activity_type = raw.get("activityType") or {}
    if isinstance(activity_type, dict):
        return activity_type.get("typeKey")
    return str(activity_type) if activity_type else None


def looks_like_strength_activity(raw):
    if not isinstance(raw, dict):
        return False
    type_key = activity_type_key(raw) or ""
    name = raw.get("activityName") or ""
    haystack = f"{type_key} {name}".lower()

    return (
        any(
            word in haystack
            for word in (
                "strength",
                "crossfit",
                "cross fit",
                "functional",
                "weight",
                "hiit",
                "fitness",
                "gym",
                "fuerza",
                "cardio",
            )
        )
        or number(raw.get("totalSets")) not in (None, 0)
        or number(raw.get("totalReps")) not in (None, 0)
    )


def summarize_exercise_sets(raw):
    if not isinstance(raw, dict):
        return None

    sets = raw.get("exerciseSets")
    if not isinstance(sets, list):
        return None

    active_sets = []
    rest_sets = 0
    total_reps = 0
    total_volume_kg = 0.0
    total_work_seconds = 0.0
    total_rest_seconds = 0.0
    exercise_totals = {}

    for item in sets[:150]:
        if not isinstance(item, dict):
            continue

        set_type = str(item.get("setType") or "").upper()
        duration = number(item.get("duration"))
        reps = number(item.get("repetitionCount"))
        weight_grams = number(item.get("weight"))
        weight_kg = round(weight_grams / 1000, 2) if weight_grams is not None else None

        exercises = item.get("exercises") or []
        exercise = exercises[0] if isinstance(exercises, list) and exercises else {}
        if not isinstance(exercise, dict):
            exercise = {}

        category = exercise.get("category")
        exercise_name = exercise.get("name") or category or "UNKNOWN"

        compact = {
            "set_type": set_type or None,
            "exercise": exercise_name,
            "category": category,
            "reps": reps,
            "weight_kg": weight_kg,
            "duration_seconds": duration,
            "start_time": item.get("startTime"),
        }

        if set_type == "REST":
            rest_sets += 1
            if duration is not None:
                total_rest_seconds += duration
            continue

        active_sets.append(compact)

        if reps is not None:
            total_reps += reps
        if duration is not None:
            total_work_seconds += duration
        if reps is not None and weight_kg is not None:
            total_volume_kg += reps * weight_kg

        bucket = exercise_totals.setdefault(
            str(exercise_name),
            {
                "sets": 0,
                "reps": 0,
                "volume_kg": 0.0,
                "max_weight_kg": None,
            },
        )
        bucket["sets"] += 1

        if reps is not None:
            bucket["reps"] += reps

        if reps is not None and weight_kg is not None:
            bucket["volume_kg"] += reps * weight_kg

        if weight_kg is not None:
            previous = bucket["max_weight_kg"]
            bucket["max_weight_kg"] = (
                weight_kg if previous is None else max(previous, weight_kg)
            )

    for bucket in exercise_totals.values():
        bucket["volume_kg"] = round(bucket["volume_kg"], 1)

    return {
        "total_sets": len(sets),
        "active_sets": len(active_sets),
        "rest_sets": rest_sets,
        "total_reps": total_reps,
        "volume_kg": round(total_volume_kg, 1),
        "work_minutes": round(total_work_seconds / 60, 1),
        "rest_minutes": round(total_rest_seconds / 60, 1),
        "exercises": exercise_totals,
        "sets": active_sets[:80],
    }


def merge_activity_load(activity, load_item):
    result = dict(activity) if isinstance(activity, dict) else {}

    if not isinstance(load_item, dict):
        return result

    for key in (
        "activityTrainingLoad",
        "trainingEffectLabel",
        "trainingEffectLabelSrvrCalc",
        "aerobicTrainingEffect",
        "anaerobicTrainingEffect",
    ):
        if result.get(key) is None and load_item.get(key) is not None:
            result[key] = load_item.get(key)

    return result


def summarize_activity(raw, exercise_sets=None):
    if not isinstance(raw, dict):
        return None

    activity_type = raw.get("activityType") or {}
    if not isinstance(activity_type, dict):
        activity_type = {}

    duration = number(raw.get("duration"))
    moving = number(raw.get("movingDuration"))

    return {
        "activity_id": activity_id_of(raw),
        "activity_name": raw.get("activityName"),
        "start_time_local": raw.get("startTimeLocal"),
        "activity_type": activity_type.get("typeKey"),
        "duration_minutes": round(duration / 60, 1) if duration is not None else None,
        "moving_minutes": round(moving / 60, 1) if moving is not None else None,
        "average_hr": number(raw.get("averageHR")),
        "max_hr": number(raw.get("maxHR")),
        "calories": number(raw.get("calories")),
        "aerobic_training_effect": number(raw.get("aerobicTrainingEffect")),
        "anaerobic_training_effect": number(raw.get("anaerobicTrainingEffect")),
        "training_effect_label": (
            raw.get("trainingEffectLabel")
            or raw.get("trainingEffectLabelSrvrCalc")
        ),
        "activity_training_load": number(raw.get("activityTrainingLoad")),
        "total_sets_garmin": number(raw.get("totalSets")),
        "active_sets_garmin": number(raw.get("activeSets")),
        "total_reps_garmin": number(raw.get("totalReps")),
        "total_volume_garmin": number(raw.get("totalVolume")),
        "exercise_sets": exercise_sets,
    }


def summarize_activity_day(items):
    activities = [item for item in items if isinstance(item, dict)]

    loads = [
        number(item.get("activity_training_load"))
        for item in activities
        if number(item.get("activity_training_load")) is not None
    ]
    aerobic_te = [
        number(item.get("aerobic_training_effect"))
        for item in activities
        if number(item.get("aerobic_training_effect")) is not None
    ]
    anaerobic_te = [
        number(item.get("anaerobic_training_effect"))
        for item in activities
        if number(item.get("anaerobic_training_effect")) is not None
    ]

    return {
        "activity_count": len(activities),
        "total_training_load": round(sum(loads), 1) if loads else None,
        "max_aerobic_training_effect": max(aerobic_te) if aerobic_te else None,
        "max_anaerobic_training_effect": max(anaerobic_te) if anaerobic_te else None,
        "activities": activities,
    }


def update_status(success, error=None, days_present=0, set_errors=None):
    status = load_json(STATUS_PATH, {})
    if not isinstance(status, dict):
        status = {}

    status["activity_metrics_generated_at"] = NOW.isoformat()
    status["activity_metrics_available"] = bool(success)
    status["activity_metrics_days_present"] = days_present
    status["activity_metrics_error"] = error
    status["activity_strength_set_errors"] = set_errors or {}

    save_json(STATUS_PATH, status)


try:
    token_b64 = os.environ.get("GARMIN_TOKENS_B64", "").strip()
    if not token_b64:
        raise RuntimeError("GARMIN_TOKENS_B64 no está disponible")

    token_dir = Path.home() / ".garminconnect"
    token_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    token_file = token_dir / "garmin_tokens.json"
    token_file.write_bytes(base64.b64decode(token_b64))
    token_file.chmod(0o600)

    from garminconnect import Garmin

    api = Garmin()
    api.login(str(token_dir))

    start_date = TODAY - timedelta(days=6)
    start_str = start_date.isoformat()
    today_str = TODAY.isoformat()

    activities_raw = api.get_activities_by_date(
        start_str,
        today_str,
        sortorder="asc",
    )

    try:
        training_load_raw = api.get_training_load_activities(
            start_str,
            today_str,
        )
    except Exception:
        training_load_raw = []

    load_by_id = {}
    load_by_start = {}

    if isinstance(training_load_raw, list):
        for item in training_load_raw:
            if not isinstance(item, dict):
                continue

            item_id = activity_id_of(item)
            if item_id is not None:
                load_by_id[str(item_id)] = item

            start_value = item.get("startTimeLocal") or item.get("startTimeGMT")
            if isinstance(start_value, str):
                load_by_start[start_value] = item

    activity_days = {}
    strength_set_errors = {}
    strength_set_calls = 0

    if not isinstance(activities_raw, list):
        activities_raw = []

    for activity in activities_raw:
        if not isinstance(activity, dict):
            continue

        activity_id = activity_id_of(activity)
        start_value = activity.get("startTimeLocal") or activity.get("startTimeGMT")

        load_item = None
        if activity_id is not None:
            load_item = load_by_id.get(str(activity_id))
        if load_item is None and isinstance(start_value, str):
            load_item = load_by_start.get(start_value)

        merged = merge_activity_load(activity, load_item)

        exercise_sets_summary = None

        if (
            activity_id is not None
            and looks_like_strength_activity(merged)
            and strength_set_calls < 12
        ):
            strength_set_calls += 1
            try:
                sets_raw = api.get_activity_exercise_sets(activity_id)
                exercise_sets_summary = summarize_exercise_sets(sets_raw)
            except Exception as exc:
                strength_set_errors[str(activity_id)] = (
                    f"{type(exc).__name__}: {exc}"
                )

        summary = summarize_activity(merged, exercise_sets_summary)
        date_str = activity_date_of(merged)

        if summary is not None and date_str:
            activity_days.setdefault(date_str, []).append(summary)

    extended = load_json(
        EXTENDED_PATH,
        {"timezone": "Europe/Madrid", "days": {}},
    )
    if not isinstance(extended, dict):
        extended = {"timezone": "Europe/Madrid", "days": {}}
    extended.setdefault("days", {})

    for i in range(7):
        date_str = (start_date + timedelta(days=i)).isoformat()

        day_entry = extended["days"].get(date_str)
        if not isinstance(day_entry, dict):
            day_entry = {
                "generated_at": NOW.isoformat(),
                "availability": {},
            }

        day_entry["activity_metrics"] = summarize_activity_day(
            activity_days.get(date_str, [])
        )

        availability = day_entry.get("availability")
        if not isinstance(availability, dict):
            availability = {}
        availability["activity_metrics"] = True

        day_entry["availability"] = availability
        extended["days"][date_str] = day_entry

    extended["generated_at"] = NOW.isoformat()
    save_json(EXTENDED_PATH, extended)

    today_activity_metrics = summarize_activity_day(
        activity_days.get(today_str, [])
    )
    today_activity_metrics["strength_set_fetch_errors"] = strength_set_errors

    daily = load_json(DAILY_PATH, {})
    if isinstance(daily, dict):
        garmin_metrics = daily.get("garmin_metrics")
        if not isinstance(garmin_metrics, dict):
            garmin_metrics = {}

        garmin_metrics["activity_metrics"] = today_activity_metrics

        availability = garmin_metrics.get("extended_availability")
        if not isinstance(availability, dict):
            availability = {}
        availability["activity_metrics"] = True

        garmin_metrics["extended_availability"] = availability
        garmin_metrics["activity_metrics_generated_at"] = NOW.isoformat()

        daily["garmin_metrics"] = garmin_metrics
        save_json(DAILY_PATH, daily)

    weekly = load_json(WEEKLY_PATH, {})
    if isinstance(weekly, dict):
        garmin = weekly.get("garmin")
        if not isinstance(garmin, dict):
            garmin = {}

        days = garmin.get("days")
        if not isinstance(days, dict):
            days = {}

        for i in range(7):
            date_str = (start_date + timedelta(days=i)).isoformat()
            day = days.get(date_str)
            if not isinstance(day, dict):
                day = {}
            day["extended"] = extended["days"].get(date_str)
            days[date_str] = day

        garmin["days"] = days
        garmin["activity_metrics_generated_at"] = NOW.isoformat()
        garmin["activity_metrics_days_present"] = sum(
            1
            for date_str in days
            if isinstance(days.get(date_str), dict)
            and isinstance(days[date_str].get("extended"), dict)
            and isinstance(
                days[date_str]["extended"].get("activity_metrics"),
                dict,
            )
        )

        weekly["garmin"] = garmin
        save_json(WEEKLY_PATH, weekly)

    update_status(
        True,
        error=None,
        days_present=len(activity_days),
        set_errors=strength_set_errors,
    )

    print(
        json.dumps(
            {
                "status": "success",
                "generated_at": NOW.isoformat(),
                "days_present": len(activity_days),
                "today": today_activity_metrics,
                "strength_set_fetch_errors": strength_set_errors,
            },
            ensure_ascii=False,
        )
    )

except Exception as exc:
    error_text = f"{type(exc).__name__}: {exc}"
    update_status(
        False,
        error=error_text,
        days_present=0,
        set_errors={},
    )
    print(
        json.dumps(
            {
                "status": "error",
                "generated_at": NOW.isoformat(),
                "error": error_text,
            },
            ensure_ascii=False,
        )
    )
