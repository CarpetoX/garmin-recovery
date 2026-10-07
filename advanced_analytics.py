import os
import json
import math
import base64
import statistics
import urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime.now(TZ)
TODAY = NOW.date()

PATHS = {
    "activities": Path("activities.json"),
    "wellness": Path("wellness.json"),
    "heart_rate": Path("garmin_heart_rate.json"),
    "extended": Path("garmin_extended.json"),
    "stress": Path("garmin_stress.json"),
    "body_battery": Path("garmin_body_battery.json"),
    "daily": Path("daily_summary.json"),
    "weekly": Path("weekly_summary.json"),
    "hrr": Path("activity_hr_recovery.json"),
    "advanced": Path("advanced_analytics.json"),
    "quality": Path("data_quality.json"),
    "context": Path("day_context.json"),
    "feedback": Path("training_feedback.json"),
}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, allow_nan=False)


def num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def safe_date(value):
    if isinstance(value, str) and len(value) >= 10:
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except Exception:
            return None
    return None


def parse_dt(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def percentile(values, p):
    xs = sorted(v for v in (num(x) for x in values) if v is not None)
    if not xs:
        return None
    if len(xs) == 1:
        return round(xs[0], 2)
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return round(xs[lo], 2)
    value = xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
    return round(value, 2)


def robust_stats(values):
    xs = [v for v in (num(x) for x in values) if v is not None]
    if not xs:
        return {"n": 0, "median": None, "mean": None, "p10": None, "p90": None, "mad": None}
    med = statistics.median(xs)
    mad = statistics.median([abs(x - med) for x in xs])
    return {
        "n": len(xs),
        "median": round(med, 2),
        "mean": round(statistics.fmean(xs), 2),
        "p10": percentile(xs, 0.10),
        "p90": percentile(xs, 0.90),
        "mad": round(mad, 2),
    }


def robust_z(value, stats):
    value = num(value)
    if value is None or not isinstance(stats, dict):
        return None
    med = num(stats.get("median"))
    mad = num(stats.get("mad"))
    if med is None or mad in (None, 0):
        return None
    return round(0.6745 * (value - med) / mad, 2)


def linear_slope(values):
    pts = [(i, num(v)) for i, v in enumerate(values) if num(v) is not None]
    if len(pts) < 3:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    xbar = statistics.fmean(xs)
    ybar = statistics.fmean(ys)
    den = sum((x - xbar) ** 2 for x in xs)
    if den == 0:
        return None
    return round(sum((x - xbar) * (y - ybar) for x, y in pts) / den, 3)


def decode_context_map():
    merged = {}
    file_data = load_json(PATHS["context"], {})
    if isinstance(file_data, dict):
        merged.update(file_data.get("days", file_data) if isinstance(file_data.get("days", file_data), dict) else {})
    raw = os.environ.get("DAY_CONTEXT_B64", "").strip()
    if raw:
        try:
            data = json.loads(base64.b64decode(raw).decode("utf-8"))
            if isinstance(data, dict):
                merged.update(data.get("days", data) if isinstance(data.get("days", data), dict) else {})
        except Exception:
            pass
    return {str(k): str(v) for k, v in merged.items() if isinstance(v, str)}


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
    # Day-sleep is a useful proxy for night-shift/post-night-shift physiology.
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
    return num(raw.get("avgStressLevel")) or num(raw.get("averageStressLevel"))


def sleep_hours_from_wellness(row):
    secs = num(row.get("sleepSecs")) if isinstance(row, dict) else None
    return round(secs / 3600, 2) if secs is not None else None


def build_day_records(wellness, heart, extended, stress, bb, context_map):
    well_by_date = {x.get("id"): x for x in wellness if isinstance(x, dict) and isinstance(x.get("id"), str)}
    hr_days = heart.get("days", {}) if isinstance(heart, dict) else {}
    ext_days = extended.get("days", {}) if isinstance(extended, dict) else {}
    stress_days = stress.get("days", {}) if isinstance(stress, dict) else {}
    bb_days = bb.get("days", {}) if isinstance(bb, dict) else {}

    all_dates = sorted(set(well_by_date) | set(hr_days) | set(ext_days) | set(stress_days) | set(bb_days))
    records = {}
    for ds in all_dates:
        w = well_by_date.get(ds, {})
        h = hr_days.get(ds, {}) if isinstance(hr_days.get(ds), dict) else {}
        e = ext_days.get(ds, {}) if isinstance(ext_days.get(ds), dict) else {}
        am = e.get("activity_metrics") if isinstance(e.get("activity_metrics"), dict) else {}
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
            "training_load_garmin": num(am.get("total_training_load")) if isinstance(am, dict) else None,
            "activity_count": int(num(am.get("activity_count")) or 0) if isinstance(am, dict) else 0,
        }
    return records


METRICS = (
    "hrv", "resting_hr", "sleep_hours", "sleep_score", "respiration",
    "daytime_hr", "nighttime_hr", "stress_avg", "body_battery_latest",
)


def rolling_robust(records):
    result = {}
    for window in (3, 7, 28):
        dates = [(TODAY - timedelta(days=i)).isoformat() for i in range(window - 1, -1, -1)]
        block = {"from": dates[0], "to": dates[-1], "metrics": {}}
        for metric in METRICS:
            vals = [records.get(ds, {}).get(metric) for ds in dates]
            stats = robust_stats(vals)
            stats["slope_per_day"] = linear_slope(vals)
            block["metrics"][metric] = stats
        result[f"{window}d"] = block
    return result


def baselines_by_context(records):
    start = TODAY - timedelta(days=27)
    eligible = [r for ds, r in records.items() if safe_date(ds) and start <= safe_date(ds) <= TODAY]
    groups = {"overall": eligible}
    for r in eligible:
        groups.setdefault(r.get("context") or "unknown", []).append(r)
    out = {}
    for label, rows in groups.items():
        metrics = {}
        for metric in METRICS:
            metrics[metric] = robust_stats([r.get(metric) for r in rows])
        out[label] = {"days": len(rows), "metrics": metrics}
    return out


def get_garmin_activity_map(extended):
    out = {}
    days = extended.get("days", {}) if isinstance(extended, dict) else {}
    for ds, row in days.items():
        if not isinstance(row, dict):
            continue
        am = row.get("activity_metrics") or {}
        for a in am.get("activities") or []:
            if not isinstance(a, dict):
                continue
            aid = a.get("activity_id")
            if aid is not None:
                out[str(aid)] = a
    return out


def rpe_of(activity):
    for key in ("session_rpe", "icu_rpe", "perceived_exertion"):
        value = num(activity.get(key)) if isinstance(activity, dict) else None
        if value is not None:
            return value
    return None


def zone_high_pct(activity):
    zones = activity.get("icu_hr_zone_times") if isinstance(activity, dict) else None
    if not isinstance(zones, list):
        return None
    vals = [num(x) or 0 for x in zones]
    total = sum(vals)
    if total <= 0:
        return None
    high = sum(vals[3:]) if len(vals) >= 4 else 0
    return round(100 * high / total, 1)


def stream_request(activity_id, api_key):
    url = f"https://intervals.icu/api/v1/activity/{activity_id}/streams"
    token = base64.b64encode(f"API_KEY:{api_key}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": "Basic " + token, "Accept": "application/json", "User-Agent": "Garmin-Recovery-Advanced/1.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def stream_dict(payload):
    out = {}
    if not isinstance(payload, list):
        return out
    for item in payload:
        if isinstance(item, dict) and isinstance(item.get("type"), str) and isinstance(item.get("data"), list):
            out[item["type"]] = item["data"]
    return out


def nearest_value(times, values, target, tolerance=15):
    best = None
    best_dist = None
    for t, v in zip(times, values):
        t = num(t); v = num(v)
        if t is None or v is None:
            continue
        dist = abs(t - target)
        if best_dist is None or dist < best_dist:
            best_dist = dist; best = v
    if best_dist is None or best_dist > tolerance:
        return None
    return best


def hrr_from_activity(activity, cached=None, streams=None):
    direct = activity.get("icu_hrr") if isinstance(activity, dict) else None
    direct = direct if isinstance(direct, dict) else {}
    start_time = num(direct.get("start_time"))
    start_bpm = num(direct.get("start_bpm"))
    direct_hrr1 = num(direct.get("hrr"))
    if direct_hrr1 is None:
        end_bpm = num(direct.get("end_bpm"))
        if start_bpm is not None and end_bpm is not None:
            direct_hrr1 = start_bpm - end_bpm

    result = {
        "available": direct_hrr1 is not None,
        "anchor_time_sec": start_time,
        "anchor_hr": start_bpm,
        "hrr_1min": round(direct_hrr1, 1) if direct_hrr1 is not None else None,
        "hrr_2min": None,
        "hrr_3min": None,
        "hrr_5min": None,
        "method": "intervals_icu_hrr" if direct_hrr1 is not None else None,
        "stream_extended": False,
    }
    if isinstance(cached, dict):
        for key in ("hrr_2min", "hrr_3min", "hrr_5min", "stream_extended", "stream_error"):
            if key in cached:
                result[key] = cached[key]
    if not streams or start_time is None:
        return result
    sd = stream_dict(streams)
    times = sd.get("time")
    hrs = sd.get("heartrate") or sd.get("fixed_heartrate")
    if not isinstance(times, list) or not isinstance(hrs, list) or not times or not hrs:
        return result
    anchor = start_bpm or nearest_value(times, hrs, start_time, tolerance=20)
    if anchor is None:
        return result
    for mins in (1, 2, 3, 5):
        target_hr = nearest_value(times, hrs, start_time + mins * 60, tolerance=20)
        if target_hr is not None:
            result[f"hrr_{mins}min"] = round(anchor - target_hr, 1)
    result["anchor_hr"] = round(anchor, 1)
    result["stream_extended"] = any(result.get(f"hrr_{m}min") is not None for m in (2, 3, 5))
    if result["stream_extended"]:
        result["method"] = "intervals_icu_hrr_plus_streams"
    result["available"] = result.get("hrr_1min") is not None or result["stream_extended"]
    return result


def update_hrr_cache(activities):
    cache = load_json(PATHS["hrr"], {"generated_at": None, "activities": {}})
    if not isinstance(cache, dict):
        cache = {"generated_at": None, "activities": {}}
    cache.setdefault("activities", {})
    api_key = os.environ.get("INTERVALS_API_KEY", "").strip()
    calls = 0
    session_rows = []
    # newest first, cap stream calls to avoid unnecessary API traffic
    ordered = sorted([a for a in activities if isinstance(a, dict)], key=lambda a: a.get("start_date_local") or "", reverse=True)
    for activity in ordered:
        aid = str(activity.get("id") or "")
        if not aid:
            continue
        existing = cache["activities"].get(aid)
        streams = None
        should_fetch = bool(api_key and calls < 8 and activity.get("has_heartrate") and isinstance(activity.get("icu_hrr"), dict) and not (isinstance(existing, dict) and existing.get("stream_extended")))
        error = None
        if should_fetch:
            try:
                streams = stream_request(aid, api_key)
                calls += 1
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                calls += 1
        hrr = hrr_from_activity(activity, cached=existing, streams=streams)
        if error:
            hrr["stream_error"] = error
        hrr["activity_id"] = aid
        hrr["date"] = (activity.get("start_date_local") or "")[:10] or None
        hrr["activity_name"] = activity.get("name")
        hrr["generated_at"] = NOW.isoformat()
        cache["activities"][aid] = hrr
        session_rows.append(hrr)
    cache["generated_at"] = NOW.isoformat()
    cache["stream_calls_this_run"] = calls
    save_json(PATHS["hrr"], cache)
    return cache


def activity_analysis(activities, extended, hrr_cache):
    garmin_map = get_garmin_activity_map(extended)
    rows = []
    for a in activities:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "")
        external_id = str(a.get("external_id") or "")
        garmin = garmin_map.get(external_id, {})
        duration_sec = num(a.get("moving_time")) or num(a.get("elapsed_time")) or 0
        duration_min = round(duration_sec / 60, 1) if duration_sec else None
        rpe = rpe_of(a)
        srpe = round(rpe * duration_min, 1) if rpe is not None and duration_min is not None else None
        trimp = num(a.get("trimp"))
        gload = num(garmin.get("activity_training_load")) if isinstance(garmin, dict) else None
        hr_load = num(a.get("hr_load"))
        exercise_sets = garmin.get("exercise_sets") if isinstance(garmin, dict) else None
        row = {
            "activity_id": aid,
            "garmin_activity_id": external_id or None,
            "date": (a.get("start_date_local") or "")[:10] or None,
            "start_local": a.get("start_date_local"),
            "name": a.get("name"),
            "type": a.get("type"),
            "internal_load": {
                "rpe": rpe,
                "session_rpe_load": srpe,
                "trimp": trimp,
                "intervals_training_load": num(a.get("icu_training_load")),
                "hr_load": hr_load,
                "garmin_activity_load": gload,
                "average_hr": num(a.get("average_heartrate")),
                "max_hr": num(a.get("max_heartrate")),
                "high_zone_pct": zone_high_pct(a),
                "aerobic_training_effect": num(garmin.get("aerobic_training_effect")) if isinstance(garmin, dict) else None,
                "anaerobic_training_effect": num(garmin.get("anaerobic_training_effect")) if isinstance(garmin, dict) else None,
            },
            "work_output_proxies": {
                "duration_minutes": duration_min,
                "distance": num(a.get("distance")) or num(a.get("icu_distance")),
                "calories": num(a.get("calories")),
                "total_reps": num(garmin.get("total_reps_garmin")) if isinstance(garmin, dict) else None,
                "volume_kg": num(exercise_sets.get("volume_kg")) if isinstance(exercise_sets, dict) else None,
                "active_sets": num(exercise_sets.get("active_sets")) if isinstance(exercise_sets, dict) else None,
            },
            "heart_rate_recovery": hrr_cache.get("activities", {}).get(aid),
            "ratios": {
                "rpe_per_trimp": round(rpe / trimp, 3) if rpe is not None and trimp not in (None, 0) else None,
                "srpe_per_garmin_load": round(srpe / gload, 3) if srpe is not None and gload not in (None, 0) else None,
            },
        }
        rows.append(row)

    # Compare session load ratios with personal median, only when enough observations exist.
    for ratio_key in ("rpe_per_trimp", "srpe_per_garmin_load"):
        values = [r["ratios"].get(ratio_key) for r in rows if r["ratios"].get(ratio_key) is not None]
        baseline = robust_stats(values[-28:])
        if baseline["n"] >= 5:
            for r in rows:
                value = r["ratios"].get(ratio_key)
                r["ratios"][ratio_key + "_robust_z"] = robust_z(value, baseline)
    return rows


def weekly_load_metrics(activity_rows):
    start = TODAY - timedelta(days=6)
    days = [start + timedelta(days=i) for i in range(7)]
    day_srpe = {d.isoformat(): 0.0 for d in days}
    day_tl = {d.isoformat(): 0.0 for d in days}
    srpe_sessions = 0
    for r in activity_rows:
        d = safe_date(r.get("date"))
        if not d or d < start or d > TODAY:
            continue
        internal = r.get("internal_load", {})
        srpe = num(internal.get("session_rpe_load"))
        tl = num(internal.get("intervals_training_load"))
        if srpe is not None:
            day_srpe[d.isoformat()] += srpe; srpe_sessions += 1
        if tl is not None:
            day_tl[d.isoformat()] += tl
    source = "session_rpe_load" if srpe_sessions >= 3 else "intervals_training_load"
    values = list(day_srpe.values()) if source == "session_rpe_load" else list(day_tl.values())
    total = sum(values)
    mean = statistics.fmean(values) if values else 0
    sd = statistics.pstdev(values) if len(values) >= 2 else 0
    active_days = sum(1 for v in values if v > 0)
    complete = all(ds <= TODAY.isoformat() for ds in (d.isoformat() for d in days))
    monotony = round(mean / sd, 2) if total > 0 and sd > 0 and active_days >= 3 else None
    strain = round(total * monotony, 1) if monotony is not None else None
    return {
        "period": {"from": days[0].isoformat(), "to": days[-1].isoformat()},
        "source": source,
        "daily_load": dict(zip([d.isoformat() for d in days], [round(v, 1) for v in values])),
        "active_days": active_days,
        "sessions_with_rpe": srpe_sessions,
        "total_load": round(total, 1),
        "monotony": monotony,
        "strain": strain,
        "valid_for_interpretation": bool(complete and active_days >= 3 and monotony is not None),
        "note": "Monotony/strain are contextual training-load descriptors, not medical thresholds.",
    }


def day_median(records, metric, dates):
    vals = [records.get(d.isoformat(), {}).get(metric) for d in dates]
    xs = [num(v) for v in vals if num(v) is not None]
    return statistics.median(xs) if xs else None


def training_response_24_48(records, activity_rows):
    by_date = {}
    for r in activity_rows:
        ds = r.get("date")
        if not ds:
            continue
        by_date.setdefault(ds, []).append(r)
    out = []
    for ds, sessions in sorted(by_date.items()):
        d = safe_date(ds)
        if not d:
            continue
        pre_dates = [d - timedelta(days=i) for i in (3, 2, 1)]
        base = {m: day_median(records, m, pre_dates) for m in ("hrv", "nighttime_hr", "resting_hr", "sleep_hours", "sleep_score")}
        loads = {
            "intervals_training_load": round(sum(num(x.get("internal_load", {}).get("intervals_training_load")) or 0 for x in sessions), 1),
            "garmin_activity_load": round(sum(num(x.get("internal_load", {}).get("garmin_activity_load")) or 0 for x in sessions), 1),
            "trimp": round(sum(num(x.get("internal_load", {}).get("trimp")) or 0 for x in sessions), 1),
            "session_rpe_load": round(sum(num(x.get("internal_load", {}).get("session_rpe_load")) or 0 for x in sessions), 1),
        }
        item = {"date": ds, "sessions": len(sessions), "loads": loads, "baseline_previous_3d": {k: round(v, 2) if v is not None else None for k, v in base.items()}, "response": {}}
        for lag in (1, 2):
            rec = records.get((d + timedelta(days=lag)).isoformat(), {})
            hrv = num(rec.get("hrv")); nh = num(rec.get("nighttime_hr")); rh = num(rec.get("resting_hr")); sh = num(rec.get("sleep_hours")); ss = num(rec.get("sleep_score"))
            response = {
                "hrv_pct": round(100 * (hrv - base["hrv"]) / base["hrv"], 1) if hrv is not None and base["hrv"] not in (None, 0) else None,
                "nighttime_hr_delta": round(nh - base["nighttime_hr"], 1) if nh is not None and base["nighttime_hr"] is not None else None,
                "resting_hr_delta": round(rh - base["resting_hr"], 1) if rh is not None and base["resting_hr"] is not None else None,
                "sleep_hours_delta": round(sh - base["sleep_hours"], 2) if sh is not None and base["sleep_hours"] is not None else None,
                "sleep_score_delta": round(ss - base["sleep_score"], 1) if ss is not None and base["sleep_score"] is not None else None,
            }
            adverse = []
            if response["hrv_pct"] is not None and response["hrv_pct"] <= -10: adverse.append("hrv_down")
            if response["nighttime_hr_delta"] is not None and response["nighttime_hr_delta"] >= 5: adverse.append("night_hr_up")
            if response["resting_hr_delta"] is not None and response["resting_hr_delta"] >= 5: adverse.append("resting_hr_up")
            if response["sleep_hours_delta"] is not None and response["sleep_hours_delta"] <= -1: adverse.append("sleep_duration_down")
            if response["sleep_score_delta"] is not None and response["sleep_score_delta"] <= -10: adverse.append("sleep_score_down")
            response["adverse_signals"] = adverse
            response["physiological_cost_signal"] = "high" if len(adverse) >= 3 else "moderate" if len(adverse) == 2 else "mild" if len(adverse) == 1 else "none"
            item["response"][f"{lag*24}h"] = response
        out.append(item)
    return out[-35:]


def current_recovery_time(daily):
    if not isinstance(daily, dict):
        return None
    gm = daily.get("garmin_metrics") or {}
    rt = gm.get("recovery_time") if isinstance(gm, dict) else None
    if isinstance(rt, dict):
        return num(rt.get("hours")) or (num(rt.get("minutes")) / 60 if num(rt.get("minutes")) is not None else None)
    return None


def personal_recovery_index(records, baselines, daily):
    today = records.get(TODAY.isoformat(), {})
    overall = baselines.get("overall", {}).get("metrics", {})
    context = today.get("context") or "unknown"
    context_metrics = baselines.get(context, {}).get("metrics", {})
    use_context = baselines.get(context, {}).get("days", 0) >= 5
    ref = context_metrics if use_context else overall
    components = []
    spec = [
        ("hrv", +1, 10), ("nighttime_hr", -1, 10), ("resting_hr", -1, 7),
        ("sleep_hours", +1, 7), ("sleep_score", +1, 7), ("stress_avg", -1, 6),
        ("body_battery_latest", +1, 5),
    ]
    score = 50.0
    for metric, direction, weight in spec:
        z = robust_z(today.get(metric), ref.get(metric, {}))
        if z is None:
            continue
        effect = max(-1.5, min(1.5, z)) / 1.5
        points = weight * direction * effect
        score += points
        components.append({"metric": metric, "value": today.get(metric), "robust_z": z, "points": round(points, 1)})
    recovery_hours = current_recovery_time(daily)
    if recovery_hours is not None:
        points = 4 if recovery_hours < 12 else -4 if recovery_hours >= 24 else -8 if recovery_hours >= 36 else 0
        # Correct ordering for >=36.
        if recovery_hours >= 36: points = -8
        elif recovery_hours >= 24: points = -4
        elif recovery_hours < 12: points = 4
        components.append({"metric": "recovery_time_hours", "value": recovery_hours, "points": points})
        score += points
    gm = daily.get("garmin_metrics") if isinstance(daily, dict) else {}
    tr = gm.get("training_readiness") if isinstance(gm, dict) else None
    gr = num(tr.get("score")) if isinstance(tr, dict) else None
    if gr is not None:
        points = max(-10, min(10, (gr - 50) * 0.2))
        components.append({"metric": "garmin_training_readiness", "value": gr, "points": round(points, 1)})
        score += points
    score = int(round(max(0, min(100, score))))
    baseline_days = baselines.get(context, {}).get("days", 0) if use_context else baselines.get("overall", {}).get("days", 0)
    confidence = "high" if len(components) >= 6 and baseline_days >= 21 else "medium" if len(components) >= 4 and baseline_days >= 7 else "low"
    return {"score": score, "context": context, "baseline_used": context if use_context else "overall", "components": components, "confidence": confidence, "provisional": confidence != "high"}


def convergence_alert(records, baselines, daily):
    today = records.get(TODAY.isoformat(), {})
    ref = baselines.get("overall", {}).get("metrics", {})
    checks = [
        ("hrv_low", "hrv", -1, -1.0),
        ("night_hr_high", "nighttime_hr", +1, 1.0),
        ("resting_hr_high", "resting_hr", +1, 1.0),
        ("sleep_hours_low", "sleep_hours", -1, -1.0),
        ("sleep_score_low", "sleep_score", -1, -1.0),
        ("stress_high", "stress_avg", +1, 1.0),
        ("body_battery_low", "body_battery_latest", -1, -1.0),
    ]
    signals = []
    strong = False
    for name, metric, direction, threshold in checks:
        z = robust_z(today.get(metric), ref.get(metric, {}))
        if z is None:
            continue
        triggered = z <= threshold if direction < 0 else z >= threshold
        if triggered:
            signals.append({"signal": name, "value": today.get(metric), "robust_z": z})
            if abs(z) >= 1.5: strong = True
    rt = current_recovery_time(daily)
    if rt is not None and rt >= 24:
        signals.append({"signal": "recovery_time_high", "value_hours": round(rt, 1)})
        if rt >= 36: strong = True
    severity = "red" if len(signals) >= 4 or (len(signals) >= 3 and strong) else "yellow" if len(signals) >= 3 else "none"
    return {"severity": severity, "signal_count": len(signals), "signals": signals, "rule": "Alerts require converging/persistent signals; isolated changes are not treated as diagnostic."}


def data_quality(records, activities, heart, daily, advanced_inputs):
    issues = []
    today = records.get(TODAY.isoformat(), {})
    score = 100
    if not today:
        issues.append("missing_today_record"); score -= 30
    if today and not today.get("sleep_window_available"):
        issues.append("missing_sleep_window"); score -= 15
    if today and today.get("night_hr_samples", 0) < 60:
        issues.append("low_night_hr_coverage"); score -= 10
    if today and today.get("day_hr_samples", 0) < 120 and not today.get("hr_partial_day"):
        issues.append("low_day_hr_coverage"); score -= 10
    if not isinstance(activities, list):
        issues.append("activities_invalid"); score -= 20
    elif not activities:
        issues.append("activities_empty"); score -= 5
    if not isinstance(heart, dict) or not heart.get("days"):
        issues.append("heart_rate_history_missing"); score -= 25
    dates_28 = [(TODAY - timedelta(days=i)).isoformat() for i in range(28)]
    coverage = {}
    for metric in METRICS:
        n = sum(1 for ds in dates_28 if num(records.get(ds, {}).get(metric)) is not None)
        coverage[metric] = {"days_present": n, "days_expected": 28, "pct": round(100*n/28, 1)}
    if coverage["hrv"]["days_present"] < 7:
        issues.append("short_hrv_baseline"); score -= 5
    if coverage["nighttime_hr"]["days_present"] < 7:
        issues.append("short_night_hr_baseline"); score -= 5
    latest = {}
    for name, obj in advanced_inputs.items():
        if isinstance(obj, dict):
            latest[name] = obj.get("generated_at")
    status = "good" if score >= 85 else "usable" if score >= 65 else "limited" if score >= 45 else "critical"
    confidence = "high" if score >= 85 else "medium" if score >= 65 else "low"
    return {"generated_at": NOW.isoformat(), "score": max(0, score), "status": status, "confidence": confidence, "issues": issues, "coverage_28d": coverage, "today": {"heart_rate_partial_day": bool(today.get("hr_partial_day")), "day_hr_samples": today.get("day_hr_samples"), "night_hr_samples": today.get("night_hr_samples"), "sleep_window_available": today.get("sleep_window_available")}, "source_generated_at": latest}


def pearson(xs, ys):
    pairs = [(num(x), num(y)) for x, y in zip(xs, ys) if num(x) is not None and num(y) is not None]
    if len(pairs) < 4:
        return None
    a = [x for x, _ in pairs]; b = [y for _, y in pairs]
    am = statistics.fmean(a); bm = statistics.fmean(b)
    den = math.sqrt(sum((x-am)**2 for x in a) * sum((y-bm)**2 for y in b))
    if den == 0:
        return None
    return round(sum((x-am)*(y-bm) for x, y in pairs) / den, 3)


def performance_calibration(activity_rows, records, baselines, responses):
    # Learns which pre-session signals/load are associated with a larger 24 h recovery cost.
    response_by_date = {x.get("date"): x for x in responses if isinstance(x, dict)}
    observations = []
    overall = baselines.get("overall", {}).get("metrics", {})
    by_date = {}
    for r in activity_rows:
        if r.get("date"):
            by_date.setdefault(r["date"], []).append(r)
    for ds, sessions in sorted(by_date.items()):
        resp = response_by_date.get(ds, {}).get("response", {}).get("24h", {})
        if not isinstance(resp, dict):
            continue
        # Continuous cost score; higher means more adverse next-day change.
        components = []
        if num(resp.get("hrv_pct")) is not None: components.append(max(0, -num(resp["hrv_pct"]) / 10))
        if num(resp.get("nighttime_hr_delta")) is not None: components.append(max(0, num(resp["nighttime_hr_delta"]) / 5))
        if num(resp.get("resting_hr_delta")) is not None: components.append(max(0, num(resp["resting_hr_delta"]) / 5))
        if num(resp.get("sleep_hours_delta")) is not None: components.append(max(0, -num(resp["sleep_hours_delta"])))
        if num(resp.get("sleep_score_delta")) is not None: components.append(max(0, -num(resp["sleep_score_delta"]) / 10))
        if len(components) < 2:
            continue
        rec = records.get(ds, {})
        internal = [x.get("internal_load", {}) for x in sessions]
        observation = {
            "date": ds,
            "recovery_cost_24h": round(sum(components), 2),
            "pre_hrv_z": robust_z(rec.get("hrv"), overall.get("hrv", {})),
            "pre_night_hr_z": robust_z(rec.get("nighttime_hr"), overall.get("nighttime_hr", {})),
            "pre_sleep_hours_z": robust_z(rec.get("sleep_hours"), overall.get("sleep_hours", {})),
            "pre_stress_z": robust_z(rec.get("stress_avg"), overall.get("stress_avg", {})),
            "intervals_training_load": sum(num(x.get("intervals_training_load")) or 0 for x in internal),
            "garmin_activity_load": sum(num(x.get("garmin_activity_load")) or 0 for x in internal),
            "session_rpe_load": sum(num(x.get("session_rpe_load")) or 0 for x in internal),
        }
        observations.append(observation)

    features = ("pre_hrv_z", "pre_night_hr_z", "pre_sleep_hours_z", "pre_stress_z", "intervals_training_load", "garmin_activity_load", "session_rpe_load")
    correlations = {}
    for feature in features:
        corr = pearson([o.get(feature) for o in observations], [o.get("recovery_cost_24h") for o in observations])
        present = sum(1 for o in observations if num(o.get(feature)) is not None)
        correlations[feature] = {"r": corr, "n": present}

    usable = [(k, v["r"]) for k, v in correlations.items() if v["r"] is not None and v["n"] >= 8]
    learned_weights = {}
    if usable:
        denom = sum(abs(r) for _, r in usable) or 1
        learned_weights = {k: round(r / denom, 3) for k, r in usable}

    n = len(observations)
    status = "mature" if n >= 30 else "active" if n >= 12 else "collecting"
    return {
        "status": status,
        "observations": n,
        "minimum_for_correlations": 8,
        "recommended_for_stable_model": 30,
        "correlations_with_next_day_recovery_cost": correlations,
        "learned_relative_weights": learned_weights,
        "note": "Personal calibration learns associations with next-day recovery cost. It remains descriptive, not diagnostic, and is not allowed to override data-quality guardrails."
    }


def hrr_trends(hrr_cache):
    rows = [x for x in hrr_cache.get("activities", {}).values() if isinstance(x, dict) and x.get("available")]
    rows.sort(key=lambda x: (x.get("date") or "", x.get("activity_id") or ""))
    result = {}
    for n in (7, 28):
        subset = rows[-n:]
        block = {"sessions": len(subset), "metrics": {}}
        for key in ("hrr_1min", "hrr_2min", "hrr_3min", "hrr_5min"):
            vals = [x.get(key) for x in subset]
            stats = robust_stats(vals)
            stats["slope_per_session"] = linear_slope(vals)
            block["metrics"][key] = stats
        result[f"last_{n}_sessions"] = block
    return result


def main():
    activities = load_json(PATHS["activities"], [])
    wellness = load_json(PATHS["wellness"], [])
    heart = load_json(PATHS["heart_rate"], {})
    extended = load_json(PATHS["extended"], {})
    stress = load_json(PATHS["stress"], {})
    bb = load_json(PATHS["body_battery"], {})
    daily = load_json(PATHS["daily"], {})
    weekly = load_json(PATHS["weekly"], {})
    if not isinstance(activities, list): activities = []
    if not isinstance(wellness, list): wellness = []

    context_map = decode_context_map()
    records = build_day_records(wellness, heart, extended, stress, bb, context_map)
    rolling = rolling_robust(records)
    baselines = baselines_by_context(records)
    hrr_cache = update_hrr_cache(activities)
    session_rows = activity_analysis(activities, extended, hrr_cache)
    weekly_load = weekly_load_metrics(session_rows)
    response = training_response_24_48(records, session_rows)
    recovery_index = personal_recovery_index(records, baselines, daily)
    alert = convergence_alert(records, baselines, daily)
    quality = data_quality(records, activities, heart, daily, {"heart_rate": heart, "extended": extended, "daily": daily, "weekly": weekly})
    calibration = performance_calibration(session_rows, records, baselines, response)
    hrr_trend = hrr_trends(hrr_cache)

    advanced = {
        "generated_at": NOW.isoformat(),
        "timezone": "Europe/Madrid",
        "methodology_version": "1.0",
        "data_quality": quality,
        "day_context": {
            "today": records.get(TODAY.isoformat(), {}).get("context"),
            "explicit_context_days": len(context_map),
            "privacy_note": "Exact MT/TN/free labels are read only from optional day_context.json or DAY_CONTEXT_B64; no work schedule is embedded in this public repository.",
        },
        "robust_trends": rolling,
        "baselines_by_context": baselines,
        "personal_recovery_index": recovery_index,
        "convergence_alert": alert,
        "weekly_load": weekly_load,
        "training_response_24_48h": response,
        "activity_analysis": session_rows[-60:],
        "heart_rate_recovery": {
            "activities_with_hrr": sum(1 for x in hrr_cache.get("activities", {}).values() if isinstance(x, dict) and x.get("available")),
            "activities_with_extended_hrr": sum(1 for x in hrr_cache.get("activities", {}).values() if isinstance(x, dict) and x.get("stream_extended")),
            "stream_calls_this_run": hrr_cache.get("stream_calls_this_run", 0),
            "history_file": str(PATHS["hrr"]),
            "trends": hrr_trend,
        },
        "personal_calibration": calibration,
        "interpretation_rules": {
            "robust_z": "Uses median/MAD when available to reduce distortion from outliers.",
            "alerts": "Require converging signals; no single metric is diagnostic.",
            "hrr": "HRR1 uses Intervals.icu icu_hrr when available. HRR2/3/5 are reported only if the activity stream actually contains those time points.",
            "load": "Work-output fields are proxies; Garmin/Intervals training load, TRIMP and sRPE are internal-load measures and are not double-counted as external work.",
        },
    }

    save_json(PATHS["advanced"], advanced)
    save_json(PATHS["quality"], quality)

    if isinstance(daily, dict):
        daily["advanced_analytics"] = {
            "generated_at": NOW.isoformat(),
            "data_quality": quality,
            "personal_recovery_index": recovery_index,
            "convergence_alert": alert,
            "robust_trends": rolling,
            "heart_rate_recovery": advanced["heart_rate_recovery"],
            "weekly_load": weekly_load,
        }
        save_json(PATHS["daily"], daily)

    if isinstance(weekly, dict):
        weekly["advanced_analytics"] = {
            "generated_at": NOW.isoformat(),
            "data_quality": quality,
            "baselines_by_context": baselines,
            "weekly_load": weekly_load,
            "training_response_24_48h": response,
            "heart_rate_recovery": advanced["heart_rate_recovery"],
            "personal_calibration": calibration,
        }
        save_json(PATHS["weekly"], weekly)

    print(json.dumps({"status": "success", "generated_at": NOW.isoformat(), "quality": quality["status"], "recovery_index": recovery_index, "alert": alert, "hrr": advanced["heart_rate_recovery"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
