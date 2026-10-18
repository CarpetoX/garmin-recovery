"""Recuperación de la FC (HRR) y análisis de actividades."""
import base64
import json
import urllib.request
from .advanced_core import linear_slope, num, robust_stats, robust_z


def get_garmin_activity_map(extended):
    out = {}
    days = extended.get("days", {}) if isinstance(extended, dict) else {}

    for _, row in days.items():
        if not isinstance(row, dict):
            continue

        am = row.get("activity_metrics") or {}

        for activity in am.get("activities") or []:
            if not isinstance(activity, dict):
                continue

            aid = activity.get("activity_id")
            if aid is not None:
                out[str(aid)] = activity

    return out

def rpe_of(activity):
    for key in (
        "session_rpe",
        "icu_rpe",
        "perceived_exertion",
    ):
        value = (
            num(activity.get(key))
            if isinstance(activity, dict)
            else None
        )

        if value is not None:
            return value

    return None

def zone_high_pct(activity):
    zones = (
        activity.get("icu_hr_zone_times")
        if isinstance(activity, dict)
        else None
    )

    if not isinstance(zones, list):
        return None

    vals = [num(x) or 0 for x in zones]
    total = sum(vals)

    if total <= 0:
        return None

    high = sum(vals[3:]) if len(vals) >= 4 else 0
    return round(100 * high / total, 1)

def stream_request(activity_id, api_key):
    url = (
        f"https://intervals.icu/api/v1/activity/"
        f"{activity_id}/streams"
    )

    token = base64.b64encode(
        f"API_KEY:{api_key}".encode()
    ).decode()

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": "Basic " + token,
            "Accept": "application/json",
            "User-Agent": "Garmin-Recovery-Advanced/1.1",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(
            response.read().decode("utf-8")
        )

def stream_dict(payload):
    out = {}

    if not isinstance(payload, list):
        return out

    for item in payload:
        if (
            isinstance(item, dict)
            and isinstance(item.get("type"), str)
            and isinstance(item.get("data"), list)
        ):
            out[item["type"]] = item["data"]

    return out

def nearest_value(times, values, target, tolerance=15):
    best = None
    best_dist = None

    for t, v in zip(times, values, strict=False):
        t = num(t)
        v = num(v)

        if t is None or v is None:
            continue

        dist = abs(t - target)

        if best_dist is None or dist < best_dist:
            best_dist = dist
            best = v

    if best_dist is None or best_dist > tolerance:
        return None

    return best

def hrr_from_activity(activity, cached=None, streams=None):
    direct = (
        activity.get("icu_hrr")
        if isinstance(activity, dict)
        else None
    )
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
        "hrr_1min": (
            round(direct_hrr1, 1)
            if direct_hrr1 is not None
            else None
        ),
        "hrr_2min": None,
        "hrr_3min": None,
        "hrr_5min": None,
        "method": (
            "intervals_icu_hrr"
            if direct_hrr1 is not None
            else None
        ),
        "stream_extended": False,
    }

    if isinstance(cached, dict):
        for key in (
            "hrr_2min",
            "hrr_3min",
            "hrr_5min",
            "stream_extended",
            "stream_error",
        ):
            if key in cached:
                result[key] = cached[key]

        if result.get("stream_extended"):
            result["method"] = "intervals_icu_hrr_plus_streams"

    if not streams or start_time is None:
        return result

    sd = stream_dict(streams)
    times = sd.get("time")
    hrs = sd.get("heartrate") or sd.get("fixed_heartrate")

    if (
        not isinstance(times, list)
        or not isinstance(hrs, list)
        or not times
        or not hrs
    ):
        return result

    anchor = (
        start_bpm
        or nearest_value(
            times,
            hrs,
            start_time,
            tolerance=20,
        )
    )

    if anchor is None:
        return result

    for mins in (1, 2, 3, 5):
        target_hr = nearest_value(
            times,
            hrs,
            start_time + mins * 60,
            tolerance=20,
        )

        if target_hr is not None:
            result[f"hrr_{mins}min"] = round(
                anchor - target_hr,
                1,
            )

    result["anchor_hr"] = round(anchor, 1)
    result["stream_extended"] = any(
        result.get(f"hrr_{m}min") is not None
        for m in (2, 3, 5)
    )

    if result["stream_extended"]:
        result["method"] = "intervals_icu_hrr_plus_streams"

    result["available"] = (
        result.get("hrr_1min") is not None
        or result["stream_extended"]
    )

    return result

def activity_analysis(activities, extended, hrr_cache):
    garmin_map = get_garmin_activity_map(extended)
    rows = []

    for activity in activities:
        if not isinstance(activity, dict):
            continue

        aid = str(activity.get("id") or "")
        external_id = str(
            activity.get("external_id") or ""
        )

        garmin = garmin_map.get(
            external_id,
            {},
        )

        duration_sec = (
            num(activity.get("moving_time"))
            or num(activity.get("elapsed_time"))
            or 0
        )

        duration_min = (
            round(duration_sec / 60, 1)
            if duration_sec
            else None
        )

        rpe = rpe_of(activity)

        srpe = (
            round(rpe * duration_min, 1)
            if rpe is not None
            and duration_min is not None
            else None
        )

        trimp = num(activity.get("trimp"))
        gload = (
            num(garmin.get("activity_training_load"))
            if isinstance(garmin, dict)
            else None
        )
        hr_load = num(activity.get("hr_load"))
        exercise_sets = (
            garmin.get("exercise_sets")
            if isinstance(garmin, dict)
            else None
        )

        row = {
            "activity_id": aid,
            "garmin_activity_id": external_id or None,
            "date": (
                (activity.get("start_date_local") or "")[:10]
                or None
            ),
            "start_local": activity.get("start_date_local"),
            "name": activity.get("name"),
            "type": activity.get("type"),
            "internal_load": {
                "rpe": rpe,
                "session_rpe_load": srpe,
                "trimp": trimp,
                "intervals_training_load": num(
                    activity.get("icu_training_load")
                ),
                "hr_load": hr_load,
                "garmin_activity_load": gload,
                "average_hr": num(
                    activity.get("average_heartrate")
                ),
                "max_hr": num(
                    activity.get("max_heartrate")
                ),
                "high_zone_pct": zone_high_pct(activity),
                "aerobic_training_effect": (
                    num(
                        garmin.get(
                            "aerobic_training_effect"
                        )
                    )
                    if isinstance(garmin, dict)
                    else None
                ),
                "anaerobic_training_effect": (
                    num(
                        garmin.get(
                            "anaerobic_training_effect"
                        )
                    )
                    if isinstance(garmin, dict)
                    else None
                ),
            },
            "work_output_proxies": {
                "duration_minutes": duration_min,
                "distance": (
                    num(activity.get("distance"))
                    or num(activity.get("icu_distance"))
                ),
                "calories": num(activity.get("calories")),
                "total_reps": (
                    num(garmin.get("total_reps_garmin"))
                    if isinstance(garmin, dict)
                    else None
                ),
                "volume_kg": (
                    num(exercise_sets.get("volume_kg"))
                    if isinstance(exercise_sets, dict)
                    else None
                ),
                "active_sets": (
                    num(exercise_sets.get("active_sets"))
                    if isinstance(exercise_sets, dict)
                    else None
                ),
            },
            "heart_rate_recovery": (
                hrr_cache
                .get("activities", {})
                .get(aid)
            ),
            "ratios": {
                "rpe_per_trimp": (
                    round(rpe / trimp, 3)
                    if rpe is not None
                    and trimp not in (None, 0)
                    else None
                ),
                "srpe_per_garmin_load": (
                    round(srpe / gload, 3)
                    if srpe is not None
                    and gload not in (None, 0)
                    else None
                ),
            },
        }

        rows.append(row)

    for ratio_key in (
        "rpe_per_trimp",
        "srpe_per_garmin_load",
    ):
        values = [
            r["ratios"].get(ratio_key)
            for r in rows
            if r["ratios"].get(ratio_key) is not None
        ]

        baseline = robust_stats(values[-28:])

        if baseline["n"] >= 5:
            for row in rows:
                value = row["ratios"].get(ratio_key)
                row["ratios"][
                    ratio_key + "_robust_z"
                ] = robust_z(
                    value,
                    baseline,
                )

    return rows

def hrr_trends(hrr_cache):
    rows = [
        x
        for x in hrr_cache
        .get("activities", {})
        .values()
        if isinstance(x, dict)
        and x.get("available")
    ]

    rows.sort(
        key=lambda x: (
            x.get("date") or "",
            x.get("activity_id") or "",
        )
    )

    result = {}

    for n in (7, 28):
        subset = rows[-n:]
        block = {
            "sessions": len(subset),
            "metrics": {},
        }

        for key in (
            "hrr_1min",
            "hrr_2min",
            "hrr_3min",
            "hrr_5min",
        ):
            vals = [
                x.get(key)
                for x in subset
            ]

            stats = robust_stats(vals)
            stats["slope_per_session"] = (
                linear_slope(vals)
            )

            block["metrics"][key] = stats

        result[
            f"last_{n}_sessions"
        ] = block

    return result
