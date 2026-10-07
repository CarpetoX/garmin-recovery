import json
import math
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime.now(TZ)

REQUIRED = [
    Path("daily_summary.json"),
    Path("weekly_summary.json"),
    Path("garmin_status.json"),
    Path("garmin_heart_rate.json"),
    Path("advanced_analytics.json"),
    Path("data_quality.json"),
]

errors = []
warnings = []
objects = {}


def load_required(path):
    if not path.exists():
        errors.append(f"missing:{path}")
        return None

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        errors.append(
            f"invalid_json:{path}:{type(exc).__name__}:{exc}"
        )
        return None


for path in REQUIRED:
    obj = load_required(path)
    if obj is not None:
        objects[str(path)] = obj


def walk(value, path="root"):
    if isinstance(value, dict):
        for key, child in value.items():
            walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            walk(child, f"{path}[{idx}]")
    elif (
        isinstance(value, float)
        and not math.isfinite(value)
    ):
        errors.append(f"non_finite:{path}")


for name, obj in objects.items():
    walk(obj, name)


def parse_dt(value):
    if not isinstance(value, str) or not value:
        return None

    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)

    return dt.astimezone(TZ)


def check_freshness(name, obj, max_minutes=60):
    if not isinstance(obj, dict):
        return

    generated_at = obj.get("generated_at")
    dt = parse_dt(generated_at)

    if dt is None:
        errors.append(
            f"missing_or_invalid_generated_at:{name}:{generated_at}"
        )
        return

    age_minutes = (
        NOW - dt
    ).total_seconds() / 60

    if age_minutes < -5:
        errors.append(
            f"generated_at_in_future:{name}:{round(age_minutes, 1)}m"
        )
    elif age_minutes > max_minutes:
        errors.append(
            f"stale:{name}:{round(age_minutes, 1)}m"
        )


for filename in (
    "daily_summary.json",
    "weekly_summary.json",
    "garmin_status.json",
    "garmin_heart_rate.json",
    "advanced_analytics.json",
    "data_quality.json",
):
    check_freshness(
        filename,
        objects.get(filename),
        max_minutes=60,
    )


hr = objects.get(
    "garmin_heart_rate.json",
    {},
)

if isinstance(hr, dict):
    for ds, row in (
        hr.get("days") or {}
    ).items():
        if not isinstance(row, dict):
            errors.append(
                f"hr_day_not_object:{ds}"
            )
            continue

        for key in (
            "daytime_avg_hr",
            "nighttime_avg_hr",
            "resting_hr",
        ):
            value = row.get(key)

            if (
                value is not None
                and not (20 <= value <= 250)
            ):
                errors.append(
                    f"implausible_hr:{ds}:{key}:{value}"
                )

        for key in (
            "daytime_sample_count",
            "nighttime_sample_count",
        ):
            value = row.get(key)

            if (
                value is not None
                and value < 0
            ):
                errors.append(
                    f"negative_sample_count:{ds}:{key}:{value}"
                )

    rolling = hr.get("rolling") or {}
    for window in ("3d", "7d", "28d"):
        if window not in rolling:
            errors.append(
                f"heart_rate_missing_rolling:{window}"
            )


garmin_status = objects.get(
    "garmin_status.json",
    {},
)

if isinstance(garmin_status, dict):
    status = garmin_status.get("status")

    if status == "error":
        errors.append(
            f"garmin_status_error:{garmin_status.get('error')}"
        )
    elif status == "partial":
        warnings.append(
            f"garmin_status_partial:{garmin_status.get('error')}"
        )
    elif status != "success":
        errors.append(
            f"garmin_status_unknown:{status}"
        )

    if (
        garmin_status.get(
            "activity_metrics_available"
        )
        is not True
    ):
        errors.append(
            "garmin_activity_metrics_not_available"
        )

    if garmin_status.get(
        "activity_metrics_error"
    ):
        errors.append(
            "garmin_activity_metrics_error:"
            + str(
                garmin_status.get(
                    "activity_metrics_error"
                )
            )
        )

    for key in (
        "latest_stress_date",
        "latest_body_battery_date",
        "latest_extended_date",
        "latest_heart_rate_date",
    ):
        if not garmin_status.get(key):
            warnings.append(
                f"garmin_status_missing:{key}"
            )


adv = objects.get(
    "advanced_analytics.json",
    {},
)

if isinstance(adv, dict):
    for key in (
        "data_quality",
        "readiness_hybrid",
        "robust_trends",
        "baselines_by_context",
        "personal_recovery_index",
        "convergence_alert",
        "weekly_load",
        "heart_rate_recovery",
    ):
        if key not in adv:
            errors.append(
                f"advanced_missing_key:{key}"
            )

    q = adv.get("data_quality") or {}
    score = (
        q.get("score")
        if isinstance(q, dict)
        else None
    )

    if (
        score is not None
        and not (0 <= score <= 100)
    ):
        errors.append(
            f"quality_score_out_of_range:{score}"
        )

    pri = (
        adv.get("personal_recovery_index")
        or {}
    )
    pri_score = (
        pri.get("score")
        if isinstance(pri, dict)
        else None
    )

    if (
        pri_score is not None
        and not (0 <= pri_score <= 100)
    ):
        errors.append(
            f"recovery_index_out_of_range:{pri_score}"
        )

    hybrid = (
        adv.get("readiness_hybrid")
        or {}
    )
    hybrid_score = (
        hybrid.get("score")
        if isinstance(hybrid, dict)
        else None
    )

    if hybrid_score is None:
        errors.append(
            "hybrid_readiness_missing_score"
        )
    elif not (0 <= hybrid_score <= 100):
        errors.append(
            f"hybrid_readiness_out_of_range:{hybrid_score}"
        )

    hybrid_status = (
        hybrid.get("status")
        if isinstance(hybrid, dict)
        else None
    )

    if hybrid_status not in {
        "green",
        "yellow",
        "red",
    }:
        errors.append(
            f"hybrid_readiness_bad_status:{hybrid_status}"
        )

    rpe = adv.get("rpe_feedback") or {}
    if isinstance(rpe, dict):
        remote_error = rpe.get(
            "remote_fetch_error"
        )
        if remote_error:
            warnings.append(
                f"rpe_remote_fetch_error:{remote_error}"
            )


quality = objects.get(
    "data_quality.json",
    {},
)

if isinstance(quality, dict):
    score = quality.get("score")
    status = quality.get("status")
    confidence = quality.get("confidence")

    if score is None:
        errors.append(
            "data_quality_missing_score"
        )
    elif not (0 <= score <= 100):
        errors.append(
            f"data_quality_score_out_of_range:{score}"
        )

    if status not in {
        "good",
        "usable",
        "limited",
        "critical",
    }:
        errors.append(
            f"data_quality_bad_status:{status}"
        )

    if confidence not in {
        "high",
        "medium",
        "low",
    }:
        errors.append(
            f"data_quality_bad_confidence:{confidence}"
        )

    coverage = (
        quality.get("coverage_28d")
        or {}
    )

    key_days = [
        (
            coverage.get(metric, {})
            .get("days_present")
        )
        for metric in (
            "hrv",
            "sleep_hours",
            "nighttime_hr",
        )
    ]

    key_days = [
        int(x)
        for x in key_days
        if isinstance(x, (int, float))
    ]

    if key_days and min(key_days) < 7:
        if confidence == "high":
            errors.append(
                "data_quality_high_confidence_with_immature_baseline"
            )
        if score is not None and score > 74:
            errors.append(
                "data_quality_score_too_high_for_immature_baseline"
            )


daily = objects.get(
    "daily_summary.json",
    {},
)

weekly = objects.get(
    "weekly_summary.json",
    {},
)

if isinstance(daily, dict):
    if "advanced_analytics" not in daily:
        errors.append(
            "daily_missing_advanced_analytics"
        )

    if "readiness_hybrid" not in daily:
        errors.append(
            "daily_missing_readiness_hybrid"
        )

    dq = daily.get("data_quality") or {}

    if dq.get("wellness_is_today") is not True:
        errors.append(
            "daily_wellness_is_not_today"
        )

    missing = (
        dq.get("missing_key_metrics")
        if isinstance(dq, dict)
        else None
    )

    if isinstance(missing, list) and missing:
        warnings.append(
            "daily_missing_key_metrics:"
            + ",".join(str(x) for x in missing)
        )


if isinstance(weekly, dict):
    if "advanced_analytics" not in weekly:
        errors.append(
            "weekly_missing_advanced_analytics"
        )


if errors:
    print(
        json.dumps(
            {
                "status": "error",
                "errors": errors,
                "warnings": warnings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    sys.exit(1)


print(
    json.dumps(
        {
            "status": "success",
            "errors": [],
            "warnings": warnings,
        },
        ensure_ascii=False,
        indent=2,
    )
)
