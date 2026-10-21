import os
from pathlib import Path
import json
from datetime import datetime

# Las funciones puras viven en módulos propios; se reexportan aquí para no cambiar a quien usa ``advanced.<nombre>``.
from .advanced_core import (  # noqa: F401
    METRICS,
    PATHS,
    TZ,
    linear_slope,
    load_json,
    num,
    parse_dt,
    pearson,
    percentile,
    robust_stats,
    robust_z,
    safe_date,
    save_json,
)
from .advanced_context import (  # noqa: F401
    bb_latest,
    build_day_records,
    decode_context_map,
    infer_sleep_context,
    sleep_hours_from_wellness,
    stress_avg,
)
from .advanced_hrr import (  # noqa: F401
    activity_analysis,
    get_garmin_activity_map,
    hrr_from_activity,
    hrr_trends,
    nearest_value,
    rpe_of,
    stream_dict,
    stream_request,
    zone_high_pct,
)
from .advanced_models import (  # noqa: F401
    current_recovery_time,
    day_median,
    hybrid_readiness,
    performance_calibration,
    training_response_24_48,
)

from . import advanced_baselines as _baselines, advanced_load as _load, advanced_quality as _quality, advanced_recovery as _recovery  # noqa: E402

NOW = datetime.now(TZ)
TODAY = NOW.date()


def rolling_robust(records):
    return _baselines.rolling_robust(records, today_date=TODAY)


def baselines_by_context(records):
    return _baselines.baselines_by_context(records, today_date=TODAY)


def update_hrr_cache(activities):
    cache = load_json(
        PATHS["hrr"],
        {
            "generated_at": None,
            "activities": {},
        },
    )

    if not isinstance(cache, dict):
        cache = {
            "generated_at": None,
            "activities": {},
        }

    cache.setdefault("activities", {})

    api_key = os.environ.get(
        "INTERVALS_API_KEY",
        "",
    ).strip()

    calls = 0

    ordered = sorted(
        [
            a
            for a in activities
            if isinstance(a, dict)
        ],
        key=lambda a: a.get("start_date_local") or "",
        reverse=True,
    )

    for activity in ordered:
        aid = str(activity.get("id") or "")
        if not aid:
            continue

        existing = cache["activities"].get(aid)
        streams = None

        should_fetch = bool(
            api_key
            and calls < 8
            and activity.get("has_heartrate")
            and isinstance(activity.get("icu_hrr"), dict)
            and not (
                isinstance(existing, dict)
                and existing.get("stream_extended")
            )
        )

        error = None

        if should_fetch:
            try:
                streams = stream_request(
                    aid,
                    api_key,
                )
                calls += 1
            except Exception as exc:
                error = (
                    f"{type(exc).__name__}: {exc}"
                )
                calls += 1

        hrr = hrr_from_activity(
            activity,
            cached=existing,
            streams=streams,
        )

        if error:
            hrr["stream_error"] = error

        hrr["activity_id"] = aid
        hrr["date"] = (
            (activity.get("start_date_local") or "")[:10]
            or None
        )
        hrr["activity_name"] = activity.get("name")
        hrr["generated_at"] = NOW.isoformat()

        cache["activities"][aid] = hrr

    cache["generated_at"] = NOW.isoformat()
    cache["stream_calls_this_run"] = calls

    save_json(PATHS["hrr"], cache)
    return cache


def weekly_load_metrics(activity_rows):
    return _load.weekly_load_metrics(activity_rows, today_date=TODAY)


def personal_recovery_index(records, baselines, daily):
    return _recovery.personal_recovery_index(records, baselines, daily, today_date=TODAY)


def convergence_alert(records, baselines, daily):
    return _recovery.convergence_alert(records, baselines, daily, today_date=TODAY)


def data_quality(records, activities, heart, daily, advanced_inputs):
    return _quality.data_quality(records, activities, heart, daily, advanced_inputs, today_date=TODAY, now_dt=NOW)


def main():
    activities = load_json(
        PATHS["activities"],
        [],
    )
    wellness = load_json(
        PATHS["wellness"],
        [],
    )
    heart = load_json(
        PATHS["heart_rate"],
        {},
    )
    extended = load_json(
        PATHS["extended"],
        {},
    )
    stress = load_json(
        PATHS["stress"],
        {},
    )
    bb = load_json(
        PATHS["body_battery"],
        {},
    )
    daily = load_json(
        PATHS["daily"],
        {},
    )
    weekly = load_json(
        PATHS["weekly"],
        {},
    )

    if not isinstance(activities, list):
        activities = []

    if not isinstance(wellness, list):
        wellness = []

    from .shift_calendar import resolve_day
    context_map = decode_context_map()

    records = build_day_records(
        wellness,
        heart,
        extended,
        stress,
        bb,
        context_map,
    )

    rolling = rolling_robust(records)
    baselines = baselines_by_context(records)

    hrr_cache = update_hrr_cache(
        activities
    )

    try:  # solo visualización (curva de FC por sesión): un fallo no debe tocar la analítica
        from . import hr_curves
        from .advanced_hrr import stream_request
        curves = hr_curves.refresh(
            activities, load_json(Path("activity_hr_curves.json"), {}),
            os.environ.get("INTERVALS_API_KEY", "").strip(), stream_request, TODAY.isoformat())
        save_json(Path("activity_hr_curves.json"), curves)
    except Exception as exc:  # noqa: BLE001
        print(f"::warning::Curvas de FC no actualizadas: {type(exc).__name__}: {exc}")

    session_rows = activity_analysis(
        activities,
        extended,
        hrr_cache,
    )

    weekly_load = weekly_load_metrics(
        session_rows
    )

    response = training_response_24_48(
        records,
        session_rows,
    )

    hybrid = hybrid_readiness(daily)

    recovery_index = personal_recovery_index(
        records,
        baselines,
        daily,
    )

    alert = convergence_alert(
        records,
        baselines,
        daily,
    )

    quality = data_quality(
        records,
        activities,
        heart,
        daily,
        {
            "heart_rate": heart,
            "extended": extended,
            "daily": daily,
            "weekly": weekly,
        },
    )

    calibration = performance_calibration(
        session_rows,
        records,
        baselines,
        response,
    )

    hrr_trend = hrr_trends(
        hrr_cache
    )

    advanced = {
        "generated_at": NOW.isoformat(),
        "timezone": "Europe/Madrid",
        "methodology_version": "1.1",
        "data_quality": quality,
        "day_context": {
            "today": (
                records
                .get(TODAY.isoformat(), {})
                .get("context")
            ),
            "explicit_context_days": len(
                context_map
            ),
            "calendar_source": "shift_calendar.json",
            "work_shift": resolve_day(TODAY.isoformat())["shift"],
            "post_tn": resolve_day(TODAY.isoformat())["post_tn"],
            "calendar_note": (
                "MT/TN/free via shift_calendar.json; DAY_CONTEXT_B64 "
                "continua como respaldo para fechas sin calendario."
            ),
        },
        "readiness_hybrid": hybrid,
        "robust_trends": rolling,
        "baselines_by_context": baselines,
        "personal_recovery_index": recovery_index,
        "convergence_alert": alert,
        "weekly_load": weekly_load,
        "training_response_24_48h": response,
        "activity_analysis": session_rows[-60:],
        "heart_rate_recovery": {
            "activities_with_hrr": sum(
                1
                for x in hrr_cache
                .get("activities", {})
                .values()
                if isinstance(x, dict)
                and x.get("available")
            ),
            "activities_with_extended_hrr": sum(
                1
                for x in hrr_cache
                .get("activities", {})
                .values()
                if isinstance(x, dict)
                and x.get("stream_extended")
            ),
            "stream_calls_this_run": hrr_cache.get(
                "stream_calls_this_run",
                0,
            ),
            "history_file": str(
                PATHS["hrr"]
            ),
            "trends": hrr_trend,
        },
        "personal_calibration": calibration,
        "interpretation_rules": {
            "hybrid_readiness": (
                "LOW local confidence: 70% Garmin + 30% local; "
                "MEDIUM: 55% Garmin + 45% local; HIGH: "
                "40% Garmin + 60% local. Garmin <50/LOW/POOR "
                "or Recovery Time >=24 h prevents green; "
                "Garmin <35 forces red."
            ),
            "robust_z": (
                "Uses historical median/MAD excluding the current "
                "day when available to reduce distortion from outliers."
            ),
            "alerts": (
                "Require converging signals and at least 7 historical "
                "observations per baseline metric; no single metric is diagnostic."
            ),
            "hrr": (
                "HRR1 uses Intervals.icu icu_hrr when available. "
                "HRR2/3/5 are reported only if the activity stream "
                "actually contains those time points."
            ),
            "load": (
                "Work-output fields are proxies; Garmin/Intervals "
                "training load, TRIMP and sRPE are internal-load measures "
                "and are not double-counted as external work."
            ),
        },
    }

    save_json(
        PATHS["advanced"],
        advanced,
    )
    save_json(
        PATHS["quality"],
        quality,
    )

    if isinstance(daily, dict):
        daily["readiness_hybrid"] = hybrid

        daily["advanced_analytics"] = {
            "generated_at": NOW.isoformat(),
            "data_quality": quality,
            "readiness_hybrid": hybrid,
            "personal_recovery_index": recovery_index,
            "convergence_alert": alert,
            "robust_trends": rolling,
            "heart_rate_recovery": advanced[
                "heart_rate_recovery"
            ],
            "weekly_load": weekly_load,
        }

        save_json(
            PATHS["daily"],
            daily,
        )

    if isinstance(weekly, dict):
        weekly["current_readiness_hybrid"] = hybrid

        weekly["advanced_analytics"] = {
            "generated_at": NOW.isoformat(),
            "data_quality": quality,
            "readiness_hybrid": hybrid,
            "baselines_by_context": baselines,
            "weekly_load": weekly_load,
            "training_response_24_48h": response,
            "heart_rate_recovery": advanced[
                "heart_rate_recovery"
            ],
            "personal_calibration": calibration,
        }

        save_json(
            PATHS["weekly"],
            weekly,
        )

    print(
        json.dumps(
            {
                "status": "success",
                "generated_at": NOW.isoformat(),
                "quality": quality["status"],
                "hybrid_readiness": hybrid,
                "recovery_index": recovery_index,
                "alert": alert,
                "hrr": advanced[
                    "heart_rate_recovery"
                ],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
