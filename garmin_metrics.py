import os
import json
import base64
import statistics
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import Counter

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime.now(TZ)
TODAY = NOW.date()

STATUS_PATH = Path("garmin_status.json")
STRESS_PATH = Path("garmin_stress.json")
BB_PATH = Path("garmin_body_battery.json")
EXTENDED_PATH = Path("garmin_extended.json")
HEART_RATE_PATH = Path("garmin_heart_rate.json")


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


def first_numeric_sample(item):
    """Extract Body Battery level from common Garmin array formats."""
    if not isinstance(item, (list, tuple)):
        return None
    if len(item) >= 3 and number(item[2]) is not None:
        return item[2]
    if len(item) >= 2 and number(item[1]) is not None:
        return item[1]
    return None


def epoch_ms(value):
    if number(value) is not None:
        return int(value)
    if isinstance(value, str):
        try:
            return int(
                datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
            )
        except Exception:
            return None
    return None


def hr_samples(raw):
    samples = []
    if not isinstance(raw, dict):
        return samples

    for item in raw.get("heartRateValues") or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        timestamp = epoch_ms(item[0])
        bpm = number(item[1])
        if timestamp is None or bpm is None:
            continue
        if 20 <= bpm <= 250:
            samples.append((timestamp, float(bpm)))
    return samples


def sleep_window_gmt(raw):
    if not isinstance(raw, dict):
        return None, None
    dto = raw.get("dailySleepDTO") or {}
    start = epoch_ms(dto.get("sleepStartTimestampGMT"))
    end = epoch_ms(dto.get("sleepEndTimestampGMT"))
    if start is None or end is None or end <= start:
        return None, None
    return start, end


def local_iso_from_ms(value):
    value = epoch_ms(value)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, TZ).isoformat()
    except Exception:
        return None


def inside_window(timestamp, start, end):
    return start is not None and end is not None and start <= timestamp <= end


def heart_rate_summary(
    hr_today_raw,
    hr_previous_raw,
    sleep_today_raw,
    sleep_next_raw=None,
    partial_day=False,
):
    """Split Garmin HR samples using the real Garmin sleep window.

    The sleep record associated with a calendar date can start during the
    previous calendar day. Therefore nighttime HR uses samples from both the
    previous and current day. For completed past days, the next sleep window
    is also excluded from daytime HR so evening sleep is not misclassified.
    """
    today_samples = hr_samples(hr_today_raw)
    previous_samples = hr_samples(hr_previous_raw)

    sleep_start, sleep_end = sleep_window_gmt(sleep_today_raw)
    next_sleep_start, next_sleep_end = sleep_window_gmt(sleep_next_raw)

    nighttime = []
    if sleep_start is not None and sleep_end is not None:
        for timestamp, bpm in previous_samples + today_samples:
            if inside_window(timestamp, sleep_start, sleep_end):
                nighttime.append(bpm)

    daytime = []
    for timestamp, bpm in today_samples:
        sleeping = (
            inside_window(timestamp, sleep_start, sleep_end)
            or inside_window(timestamp, next_sleep_start, next_sleep_end)
        )
        if not sleeping:
            daytime.append(bpm)

    def mean(values):
        return round(statistics.fmean(values), 1) if values else None

    daytime_avg = mean(daytime)
    nighttime_avg = mean(nighttime)

    return {
        "resting_hr": (
            number(hr_today_raw.get("restingHeartRate"))
            if isinstance(hr_today_raw, dict)
            else None
        ),
        "overall_min_hr": (
            number(hr_today_raw.get("minHeartRate"))
            if isinstance(hr_today_raw, dict)
            else None
        ),
        "overall_max_hr": (
            number(hr_today_raw.get("maxHeartRate"))
            if isinstance(hr_today_raw, dict)
            else None
        ),
        "daytime_avg_hr": daytime_avg,
        "daytime_min_hr": round(min(daytime), 1) if daytime else None,
        "daytime_max_hr": round(max(daytime), 1) if daytime else None,
        "daytime_sample_count": len(daytime),
        "nighttime_avg_hr": nighttime_avg,
        "nighttime_min_hr": round(min(nighttime), 1) if nighttime else None,
        "nighttime_max_hr": round(max(nighttime), 1) if nighttime else None,
        "nighttime_sample_count": len(nighttime),
        "day_minus_night_bpm": (
            round(daytime_avg - nighttime_avg, 1)
            if daytime_avg is not None and nighttime_avg is not None
            else None
        ),
        "sleep_start_local": local_iso_from_ms(sleep_start),
        "sleep_end_local": local_iso_from_ms(sleep_end),
        "sleep_window_available": sleep_start is not None and sleep_end is not None,
        "partial_day": bool(partial_day),
    }


def weighted_hr_average(
    days,
    value_field,
    count_field,
    selected_dates,
    exclude_partial_days=False,
):
    weighted_sum = 0.0
    sample_count = 0
    days_present = 0
    partial_days_excluded = 0

    for day in selected_dates:
        row = days.get(day.isoformat())
        if not isinstance(row, dict):
            continue
        if exclude_partial_days and row.get("partial_day"):
            partial_days_excluded += 1
            continue

        value = number(row.get(value_field))
        count = number(row.get(count_field))
        if value is None or count in (None, 0):
            continue
        weighted_sum += value * count
        sample_count += int(count)
        days_present += 1

    return {
        "average": round(weighted_sum / sample_count, 1) if sample_count else None,
        "days_present": days_present,
        "sample_count": sample_count,
        "partial_days_excluded": partial_days_excluded,
    }


def heart_rate_rolling(days, end_date):
    """Rolling HR summaries.

    Daytime rolling averages exclude partial calendar days so an unfinished
    day does not distort the personal baseline. Nighttime HR is retained for
    the current day because the sleep window is already complete after waking.
    """
    result = {}

    for window in (3, 7, 28):
        selected_dates = [
            end_date - timedelta(days=i)
            for i in range(window - 1, -1, -1)
        ]

        daytime = weighted_hr_average(
            days,
            "daytime_avg_hr",
            "daytime_sample_count",
            selected_dates,
            exclude_partial_days=True,
        )
        nighttime = weighted_hr_average(
            days,
            "nighttime_avg_hr",
            "nighttime_sample_count",
            selected_dates,
            exclude_partial_days=False,
        )

        day_avg = daytime["average"]
        night_avg = nighttime["average"]

        result[f"{window}d"] = {
            "daytime_avg_hr": day_avg,
            "nighttime_avg_hr": night_avg,
            "day_minus_night_bpm": (
                round(day_avg - night_avg, 1)
                if day_avg is not None and night_avg is not None
                else None
            ),
            "daytime_days_present": daytime["days_present"],
            "nighttime_days_present": nighttime["days_present"],
            "daytime_sample_count": daytime["sample_count"],
            "nighttime_sample_count": nighttime["sample_count"],
            "daytime_partial_days_excluded": daytime["partial_days_excluded"],
            "from": selected_dates[0].isoformat(),
            "to": selected_dates[-1].isoformat(),
            "note": "Daytime rolling excludes partial days; nighttime rolling may include the current completed sleep window.",
        }

    return result


def stress_summary(raw):
    if not isinstance(raw, dict):
        return None

    values = raw.get("stressValuesArray") or raw.get("stressValues") or []
    levels = []
    if isinstance(values, list):
        for item in values:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
                and number(item[1]) is not None
                and item[1] >= 0
            ):
                levels.append(item[1])

    p90 = None
    if levels:
        ordered = sorted(levels)
        p90 = ordered[min(len(ordered) - 1, int(0.90 * (len(ordered) - 1)))]

    return {
        "average_stress": number(raw.get("avgStressLevel", raw.get("averageStressLevel"))),
        "max_stress": number(raw.get("maxStressLevel")),
        "stress_duration_secs": number(raw.get("stressDuration")),
        "rest_stress_duration_secs": number(raw.get("restStressDuration")),
        "sample_count": len(levels),
        "sample_mean": round(statistics.fmean(levels), 1) if levels else None,
        "sample_p90": round(p90, 1) if p90 is not None else None,
    }


def body_battery_summary(raw):
    if not isinstance(raw, dict):
        return None

    values = raw.get("bodyBatteryValuesArray") or []
    samples = []
    latest_ts = None
    if isinstance(values, list):
        for item in values:
            level = first_numeric_sample(item)
            if level is not None:
                samples.append(level)
                latest_ts = item[0] if item else latest_ts

    return {
        "charged": number(raw.get("charged")),
        "drained": number(raw.get("drained")),
        "latest": samples[-1] if samples else None,
        "highest": max(samples) if samples else None,
        "lowest": min(samples) if samples else None,
        "sample_count": len(samples),
        "latest_sample_timestamp": latest_ts,
        "start_local": raw.get("startTimestampLocal"),
        "end_local": raw.get("endTimestampLocal"),
    }


def summarize_readiness(raw):
    if not isinstance(raw, dict):
        return None
    recovery_minutes = number(raw.get("recoveryTime"))
    return {
        "score": number(raw.get("score")),
        "level": raw.get("level"),
        "timestamp_local": raw.get("timestampLocal"),
        "input_context": raw.get("inputContext"),
        "feedback_short": raw.get("feedbackShort"),
        "feedback_long": raw.get("feedbackLong"),
        "sleep_score": number(raw.get("sleepScore")),
        "sleep_factor_percent": number(raw.get("sleepScoreFactorPercent")),
        "sleep_factor_feedback": raw.get("sleepScoreFactorFeedback"),
        "recovery_time_minutes": recovery_minutes,
        "recovery_time_hours": (
            round(recovery_minutes / 60, 1) if recovery_minutes is not None else None
        ),
        "recovery_time_factor_percent": number(raw.get("recoveryTimeFactorPercent")),
        "recovery_time_feedback": raw.get("recoveryTimeFactorFeedback"),
        "recovery_time_change_phrase": raw.get("recoveryTimeChangePhrase"),
        "acwr_factor_percent": number(raw.get("acwrFactorPercent")),
        "acwr_factor_feedback": raw.get("acwrFactorFeedback"),
        "hrv_factor_percent": number(raw.get("hrvFactorPercent")),
        "hrv_factor_feedback": raw.get("hrvFactorFeedback"),
        "stress_history_factor_percent": number(raw.get("stressHistoryFactorPercent")),
        "stress_history_factor_feedback": raw.get("stressHistoryFactorFeedback"),
    }


def summarize_hrv(raw):
    if not isinstance(raw, dict):
        return None
    summary = raw.get("hrvSummary") or {}
    baseline = summary.get("baseline") or {}
    return {
        "last_night_avg": number(summary.get("lastNightAvg")),
        "weekly_avg": number(summary.get("weeklyAvg")),
        "last_night_5_min_high": number(summary.get("lastNight5MinHigh")),
        "status": summary.get("status"),
        "feedback": summary.get("feedbackPhrase"),
        "baseline": {
            "low_upper": number(baseline.get("lowUpper")),
            "balanced_low": number(baseline.get("balancedLow")),
            "balanced_upper": number(baseline.get("balancedUpper")),
            "marker_value": number(baseline.get("markerValue")),
        },
        "sleep_start_local": raw.get("sleepStartTimestampLocal"),
        "sleep_end_local": raw.get("sleepEndTimestampLocal"),
        "reading_count": (
            len(raw.get("hrvReadings") or [])
            if isinstance(raw.get("hrvReadings"), list)
            else None
        ),
    }


def score_component(scores, key):
    value = scores.get(key)
    if isinstance(value, dict):
        return {
            "value": number(value.get("value")),
            "qualifier": value.get("qualifierKey"),
        }
    return None


def summarize_sleep(raw):
    if not isinstance(raw, dict):
        return None
    dto = raw.get("dailySleepDTO") or {}
    scores = dto.get("sleepScores") or {}

    sleep_secs = number(dto.get("sleepTimeSeconds"))
    nap_secs = number(dto.get("napTimeSeconds"))
    deep = number(dto.get("deepSleepSeconds"))
    light = number(dto.get("lightSleepSeconds"))
    rem = number(dto.get("remSleepSeconds"))
    awake = number(dto.get("awakeSleepSeconds"))

    return {
        "sleep_hours": round(sleep_secs / 3600, 2) if sleep_secs is not None else None,
        "nap_minutes": round(nap_secs / 60, 1) if nap_secs is not None else None,
        "deep_minutes": round(deep / 60, 1) if deep is not None else None,
        "light_minutes": round(light / 60, 1) if light is not None else None,
        "rem_minutes": round(rem / 60, 1) if rem is not None else None,
        "awake_minutes": round(awake / 60, 1) if awake is not None else None,
        "sleep_start_local": dto.get("sleepStartTimestampLocal"),
        "sleep_end_local": dto.get("sleepEndTimestampLocal"),
        "sleep_window_confirmed": dto.get("sleepWindowConfirmed"),
        "avg_sleep_hrv": number(dto.get("avgSleepHRV")),
        "avg_spo2": number(dto.get("avgSpO2")),
        "avg_respiration": number(dto.get("averageRespirationValue")),
        "lowest_respiration": number(dto.get("lowestRespirationValue")),
        "highest_respiration": number(dto.get("highestRespirationValue")),
        "score_components": {
            "overall": score_component(scores, "overall"),
            "total_duration": score_component(scores, "totalDuration"),
            "stress": score_component(scores, "stress"),
            "awake_count": score_component(scores, "awakeCount"),
            "rem_percentage": score_component(scores, "remPercentage"),
            "restlessness": score_component(scores, "restlessness"),
            "light_percentage": score_component(scores, "lightPercentage"),
            "deep_percentage": score_component(scores, "deepPercentage"),
        },
    }


def select_scalars(obj, keywords, max_fields=100):
    found = {}

    def walk(value, path=""):
        if len(found) >= max_fields:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                next_path = f"{path}.{key}" if path else key
                walk(child, next_path)
        elif isinstance(value, list):
            for idx, child in enumerate(value[:20]):
                walk(child, f"{path}[{idx}]")
        elif value is None or isinstance(value, (str, int, float, bool)):
            leaf = path.rsplit(".", 1)[-1].lower()
            if any(word in leaf for word in keywords):
                found[path] = value

    walk(obj)
    return found or None


TRAINING_KEYWORDS = (
    "status", "phrase", "feedback", "load", "acwr", "ratio", "acute", "chronic",
    "aerobic", "anaerobic", "focus", "optimal", "target", "vo2", "fitness",
    "recovery", "strain", "balance"
)


def summarize_training_payload(raw):
    if not isinstance(raw, (dict, list)):
        return None
    return select_scalars(raw, TRAINING_KEYWORDS, max_fields=120)


def summarize_bb_events(raw):
    if not isinstance(raw, list):
        return None

    event_keywords = (
        "type", "name", "start", "end", "duration", "bodybattery",
        "body_battery", "value", "charge", "drain", "activity", "sleep", "nap"
    )
    events = []
    type_counter = Counter()

    for event in raw[:60]:
        if not isinstance(event, dict):
            continue
        selected = select_scalars(event, event_keywords, max_fields=30) or {}
        event_type = (
            event.get("eventType")
            or event.get("type")
            or event.get("activityType")
            or event.get("eventName")
            or event.get("activityName")
        )
        if event_type:
            type_counter[str(event_type)] += 1
        if selected:
            events.append(selected)

    return {
        "event_count": len(raw),
        "event_type_counts": dict(type_counter),
        "events": events,
    }


def call_optional(label, func, errors):
    try:
        return func()
    except Exception as exc:
        errors[label] = f"{type(exc).__name__}: {exc}"
        return None


status = {
    "generated_at": NOW.isoformat(),
    "timezone": "Europe/Madrid",
    "status": "error",
    "error": None,
    "latest_stress_date": None,
    "latest_body_battery_date": None,
    "latest_extended_date": None,
    "latest_heart_rate_date": None,
}

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

    stress_store = load_json(STRESS_PATH, {"timezone": "Europe/Madrid", "days": {}})
    if not isinstance(stress_store, dict):
        stress_store = {"timezone": "Europe/Madrid", "days": {}}
    stress_store.setdefault("days", {})

    bb_store = load_json(BB_PATH, {"timezone": "Europe/Madrid", "days": {}})
    if not isinstance(bb_store, dict):
        bb_store = {"timezone": "Europe/Madrid", "days": {}}
    bb_store.setdefault("days", {})

    extended_store = load_json(EXTENDED_PATH, {"timezone": "Europe/Madrid", "days": {}})
    if not isinstance(extended_store, dict):
        extended_store = {"timezone": "Europe/Madrid", "days": {}}
    extended_store.setdefault("days", {})

    heart_store = load_json(HEART_RATE_PATH, {"timezone": "Europe/Madrid", "days": {}})
    if not isinstance(heart_store, dict):
        heart_store = {"timezone": "Europe/Madrid", "days": {}}
    heart_store.setdefault("days", {})

    if stress_store["days"]:
        stress_dates = [TODAY - timedelta(days=1), TODAY]
    else:
        stress_dates = [TODAY - timedelta(days=i) for i in range(6, -1, -1)]

    stress_errors = {}
    for day in stress_dates:
        date_str = day.isoformat()
        try:
            payload = api.get_stress_data(date_str)
            if isinstance(payload, dict) and payload:
                stress_store["days"][date_str] = payload
        except Exception as exc:
            stress_errors[date_str] = f"{type(exc).__name__}: {exc}"

    bb_start = TODAY - timedelta(days=6 if not bb_store["days"] else 1)
    body_battery_error = None
    try:
        payload = api.get_body_battery(bb_start.isoformat(), TODAY.isoformat())
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    date_str = item.get("date")
                    if date_str:
                        bb_store["days"][date_str] = item
    except Exception as exc:
        body_battery_error = f"{type(exc).__name__}: {exc}"

    today_str = TODAY.isoformat()
    extended_errors = {}

    readiness_raw = call_optional(
        "training_readiness",
        lambda: api.get_morning_training_readiness(today_str),
        extended_errors,
    )
    hrv_raw = call_optional(
        "hrv_status",
        lambda: api.get_hrv_data(today_str),
        extended_errors,
    )
    sleep_raw = call_optional(
        "sleep_detail",
        lambda: api.get_sleep_data(today_str),
        extended_errors,
    )

    target_hr_dates = [TODAY - timedelta(days=i) for i in range(28)]
    missing_hr_dates = []
    for day in target_hr_dates:
        existing_hr = heart_store["days"].get(day.isoformat())
        if (
            not isinstance(existing_hr, dict)
            or existing_hr.get("daytime_avg_hr") is None
            or existing_hr.get("nighttime_avg_hr") is None
        ):
            missing_hr_dates.append(day)

    requested_hr_dates = missing_hr_dates[:7] + [TODAY - timedelta(days=1), TODAY]
    heart_dates = []
    seen_dates = set()
    for day in requested_hr_dates:
        key = day.isoformat()
        if key not in seen_dates:
            seen_dates.add(key)
            heart_dates.append(day)

    heart_rate_errors = {}
    hr_cache = {}
    sleep_cache = {TODAY.isoformat(): sleep_raw}

    def get_hr_cached(day):
        key = day.isoformat()
        if key not in hr_cache:
            hr_cache[key] = api.get_heart_rates(key)
        return hr_cache[key]

    def get_sleep_cached(day):
        key = day.isoformat()
        if key not in sleep_cache:
            sleep_cache[key] = api.get_sleep_data(key)
        return sleep_cache[key]

    for day in heart_dates:
        date_str = day.isoformat()
        try:
            hr_today_raw = get_hr_cached(day)
            hr_previous_raw = get_hr_cached(day - timedelta(days=1))
            sleep_today_hr = get_sleep_cached(day)

            sleep_next_hr = None
            if day < TODAY:
                try:
                    sleep_next_hr = get_sleep_cached(day + timedelta(days=1))
                except Exception:
                    sleep_next_hr = None

            summary = heart_rate_summary(
                hr_today_raw=hr_today_raw,
                hr_previous_raw=hr_previous_raw,
                sleep_today_raw=sleep_today_hr,
                sleep_next_raw=sleep_next_hr,
                partial_day=(day == TODAY),
            )
            if summary is not None:
                summary["date"] = date_str
                summary["generated_at"] = NOW.isoformat()
                heart_store["days"][date_str] = summary
        except Exception as exc:
            heart_rate_errors[date_str] = f"{type(exc).__name__}: {exc}"

    today_hr = heart_store["days"].get(today_str)
    hr_rolling = heart_rate_rolling(heart_store["days"], TODAY)

    daily_training_status_raw = call_optional(
        "daily_training_status",
        lambda: api.get_daily_training_status(today_str),
        extended_errors,
    )
    training_status_raw = call_optional(
        "training_status",
        lambda: api.get_training_status(today_str),
        extended_errors,
    )
    load_balance_raw = call_optional(
        "four_week_load_balance",
        lambda: api.get_training_four_week_load_balance(today_str),
        extended_errors,
    )
    bb_events_raw = call_optional(
        "body_battery_events",
        lambda: api.get_body_battery_events(today_str),
        extended_errors,
    )

    readiness_summary = summarize_readiness(readiness_raw)
    hrv_summary = summarize_hrv(hrv_raw)
    sleep_summary = summarize_sleep(sleep_raw)
    daily_training_status_summary = summarize_training_payload(daily_training_status_raw)
    training_status_summary = summarize_training_payload(training_status_raw)
    load_balance_summary = summarize_training_payload(load_balance_raw)
    bb_events_summary = summarize_bb_events(bb_events_raw)

    recovery_time = None
    if readiness_summary:
        recovery_time = {
            "minutes": readiness_summary.get("recovery_time_minutes"),
            "hours": readiness_summary.get("recovery_time_hours"),
            "factor_percent": readiness_summary.get("recovery_time_factor_percent"),
            "feedback": readiness_summary.get("recovery_time_feedback"),
            "change_phrase": readiness_summary.get("recovery_time_change_phrase"),
        }

    extended_today = {
        "generated_at": NOW.isoformat(),
        "training_readiness": readiness_summary,
        "recovery_time": recovery_time,
        "hrv_status": hrv_summary,
        "sleep_detail": sleep_summary,
        "training_status": training_status_summary,
        "daily_training_status": daily_training_status_summary,
        "four_week_load_balance": load_balance_summary,
        "body_battery_events": bb_events_summary,
        "availability": {
            "training_readiness": readiness_summary is not None,
            "recovery_time": recovery_time is not None and recovery_time.get("minutes") is not None,
            "hrv_status": hrv_summary is not None,
            "sleep_detail": sleep_summary is not None,
            "training_status": training_status_summary is not None or daily_training_status_summary is not None,
            "four_week_load_balance": load_balance_summary is not None,
            "body_battery_events": bb_events_summary is not None,
        },
        "fetch_errors": extended_errors,
    }

    extended_store["days"][today_str] = extended_today

    stress_store["generated_at"] = NOW.isoformat()
    bb_store["generated_at"] = NOW.isoformat()
    extended_store["generated_at"] = NOW.isoformat()
    heart_store["generated_at"] = NOW.isoformat()
    heart_store["rolling"] = hr_rolling

    save_json(STRESS_PATH, stress_store)
    save_json(BB_PATH, bb_store)
    save_json(EXTENDED_PATH, extended_store)
    save_json(HEART_RATE_PATH, heart_store)

    today_stress = stress_summary(stress_store["days"].get(today_str))
    today_bb = body_battery_summary(bb_store["days"].get(today_str))

    daily = load_json("daily_summary.json", {})
    if isinstance(daily, dict):
        existing = daily.get("garmin_metrics")
        if not isinstance(existing, dict):
            existing = {}

        existing.update({
            "source": "Garmin Connect",
            "generated_at": NOW.isoformat(),
            "stress": today_stress,
            "body_battery": today_bb,
            "training_readiness": readiness_summary,
            "recovery_time": recovery_time,
            "hrv_status": hrv_summary,
            "sleep_detail": sleep_summary,
            "heart_rate": today_hr,
            "heart_rate_rolling": hr_rolling,
            "training_status": training_status_summary,
            "daily_training_status": daily_training_status_summary,
            "four_week_load_balance": load_balance_summary,
            "body_battery_events": bb_events_summary,
            "extended_availability": extended_today["availability"],
            "extended_fetch_errors": extended_errors,
            "heart_rate_fetch_errors": heart_rate_errors,
            "note": (
                "Métricas propietarias de Garmin: interpretar como señales contextuales "
                "junto con sueño, HRV, FC, carga, RPE y sensaciones; no como diagnóstico."
            ),
        })
        daily["garmin_metrics"] = existing

        if isinstance(daily.get("recovery_today"), dict) and isinstance(today_hr, dict):
            daily["recovery_today"]["avg_daytime_hr"] = today_hr.get("daytime_avg_hr")
            daily["recovery_today"]["avg_sleeping_hr"] = today_hr.get("nighttime_avg_hr")
            daily["recovery_today"]["daytime_min_hr"] = today_hr.get("daytime_min_hr")
            daily["recovery_today"]["daytime_max_hr"] = today_hr.get("daytime_max_hr")
            daily["recovery_today"]["nighttime_min_hr"] = today_hr.get("nighttime_min_hr")
            daily["recovery_today"]["nighttime_max_hr"] = today_hr.get("nighttime_max_hr")
            daily["recovery_today"]["day_minus_night_bpm"] = today_hr.get("day_minus_night_bpm")
            daily["recovery_today"]["heart_rate_partial_day"] = today_hr.get("partial_day")
            daily["recovery_today"]["heart_rate_3d"] = hr_rolling.get("3d")
            daily["recovery_today"]["heart_rate_7d"] = hr_rolling.get("7d")
            daily["recovery_today"]["heart_rate_28d"] = hr_rolling.get("28d")

        save_json("daily_summary.json", daily)

    weekly = load_json("weekly_summary.json", {})
    if isinstance(weekly, dict):
        week_start = TODAY - timedelta(days=6)
        per_day = {}

        for i in range(7):
            date_str = (week_start + timedelta(days=i)).isoformat()
            ext = extended_store["days"].get(date_str)
            per_day[date_str] = {
                "stress": stress_summary(stress_store["days"].get(date_str)),
                "body_battery": body_battery_summary(bb_store["days"].get(date_str)),
                "heart_rate": heart_store["days"].get(date_str),
                "extended": ext,
            }

        weekly["garmin"] = {
            "source": "Garmin Connect",
            "generated_at": NOW.isoformat(),
            "days": per_day,
            "stress_days_present": sum(
                1 for value in per_day.values() if value["stress"] is not None
            ),
            "body_battery_days_present": sum(
                1 for value in per_day.values() if value["body_battery"] is not None
            ),
            "extended_days_present": sum(
                1 for value in per_day.values() if value["extended"] is not None
            ),
            "heart_rate_days_present": sum(
                1 for value in per_day.values() if value["heart_rate"] is not None
            ),
            "heart_rate_rolling": hr_rolling,
        }

        weekly_recovery = weekly.get("recovery")
        if isinstance(weekly_recovery, dict):
            rolling_7d = hr_rolling.get("7d") or {}
            weekly_recovery["avg_daytime_hr"] = rolling_7d.get("daytime_avg_hr")
            weekly_recovery["avg_sleeping_hr"] = rolling_7d.get("nighttime_avg_hr")

        save_json("weekly_summary.json", weekly)

    core_ok = today_stress is not None or today_bb is not None
    extended_ok_count = sum(1 for value in extended_today["availability"].values() if value)

    status["status"] = "success" if core_ok else "partial"
    status["latest_stress_date"] = max(stress_store["days"].keys(), default=None)
    status["latest_body_battery_date"] = max(bb_store["days"].keys(), default=None)
    status["latest_extended_date"] = max(extended_store["days"].keys(), default=None)
    status["latest_heart_rate_date"] = max(heart_store["days"].keys(), default=None)
    status["stress_fetch_errors"] = stress_errors
    status["body_battery_fetch_error"] = body_battery_error
    status["extended_metrics_available"] = extended_ok_count
    status["extended_availability"] = extended_today["availability"]
    status["extended_fetch_errors"] = extended_errors
    status["heart_rate_fetch_errors"] = heart_rate_errors
    status["heart_rate_rolling"] = hr_rolling

    if status["status"] == "partial":
        status["error"] = (
            "No se obtuvieron Stress ni Body Battery para hoy; "
            "se preservaron los datos previos."
        )

except Exception as exc:
    status["error"] = f"{type(exc).__name__}: {exc}"

save_json(STATUS_PATH, status)
print(json.dumps(status, ensure_ascii=False))

if status.get("status") == "error":
    raise SystemExit(1)
