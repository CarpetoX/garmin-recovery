import os
import json
import statistics
from datetime import datetime, timedelta

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

NOW = datetime.now(TZ)
TODAY = NOW.date()


def rolling_robust(records):
    result = {}

    for window in (3, 7, 28):
        dates = [
            (TODAY - timedelta(days=i)).isoformat()
            for i in range(window - 1, -1, -1)
        ]

        block = {
            "from": dates[0],
            "to": dates[-1],
            "metrics": {},
        }

        for metric in METRICS:
            vals = []
            for ds in dates:
                row = records.get(ds, {})
                if (
                    metric == "daytime_hr"
                    and row.get("hr_partial_day")
                ):
                    vals.append(None)
                else:
                    vals.append(row.get(metric))

            stats = robust_stats(vals)
            stats["slope_per_day"] = linear_slope(vals)

            if metric == "daytime_hr":
                stats["partial_days_excluded"] = sum(
                    1
                    for ds in dates
                    if records.get(ds, {}).get("hr_partial_day")
                )

            block["metrics"][metric] = stats

        result[f"{window}d"] = block

    return result


def baselines_by_context(records):
    """Use only completed historical days; never include TODAY in its own baseline."""
    start = TODAY - timedelta(days=28)

    eligible = [
        r
        for ds, r in records.items()
        if safe_date(ds)
        and start <= safe_date(ds) < TODAY
    ]

    groups = {"overall": eligible}

    for r in eligible:
        groups.setdefault(
            r.get("context") or "unknown",
            [],
        ).append(r)

    out = {}

    for label, rows in groups.items():
        metrics = {}

        for metric in METRICS:
            metrics[metric] = robust_stats(
                [r.get(metric) for r in rows]
            )

        out[label] = {
            "days": len(rows),
            "metrics": metrics,
        }

    return out


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
    start = TODAY - timedelta(days=6)
    days = [
        start + timedelta(days=i)
        for i in range(7)
    ]

    day_srpe = {
        d.isoformat(): 0.0
        for d in days
    }

    day_tl = {
        d.isoformat(): 0.0
        for d in days
    }

    srpe_sessions = 0

    for row in activity_rows:
        d = safe_date(row.get("date"))

        if not d or d < start or d > TODAY:
            continue

        internal = row.get("internal_load", {})
        srpe = num(internal.get("session_rpe_load"))
        tl = num(
            internal.get("intervals_training_load")
        )

        if srpe is not None:
            day_srpe[d.isoformat()] += srpe
            srpe_sessions += 1

        if tl is not None:
            day_tl[d.isoformat()] += tl

    source = (
        "session_rpe_load"
        if srpe_sessions >= 3
        else "intervals_training_load"
    )

    values = (
        list(day_srpe.values())
        if source == "session_rpe_load"
        else list(day_tl.values())
    )

    total = sum(values)
    mean = statistics.fmean(values) if values else 0
    sd = (
        statistics.pstdev(values)
        if len(values) >= 2
        else 0
    )

    active_days = sum(
        1 for v in values if v > 0
    )

    complete = all(
        ds <= TODAY.isoformat()
        for ds in (
            d.isoformat()
            for d in days
        )
    )

    monotony = (
        round(mean / sd, 2)
        if total > 0
        and sd > 0
        and active_days >= 3
        else None
    )

    strain = (
        round(total * monotony, 1)
        if monotony is not None
        else None
    )

    return {
        "period": {
            "from": days[0].isoformat(),
            "to": days[-1].isoformat(),
        },
        "source": source,
        "daily_load": dict(
            zip(
                [d.isoformat() for d in days],
                [round(v, 1) for v in values], strict=False,
            )
        ),
        "active_days": active_days,
        "sessions_with_rpe": srpe_sessions,
        "total_load": round(total, 1),
        "monotony": monotony,
        "strain": strain,
        "valid_for_interpretation": bool(
            complete
            and active_days >= 3
            and monotony is not None
        ),
        "note": (
            "Monotony/strain are contextual "
            "training-load descriptors, not medical thresholds."
        ),
    }


def personal_recovery_index(records, baselines, daily):
    today = records.get(
        TODAY.isoformat(),
        {},
    )

    overall = (
        baselines
        .get("overall", {})
        .get("metrics", {})
    )

    context = today.get("context") or "unknown"

    context_block = baselines.get(
        context,
        {},
    )

    context_metrics = context_block.get(
        "metrics",
        {},
    )

    use_context = (
        context_block.get("days", 0) >= 5
    )

    ref = (
        context_metrics
        if use_context
        else overall
    )

    components = []
    baseline_ns = []

    spec = [
        ("hrv", +1, 10),
        ("nighttime_hr", -1, 10),
        ("resting_hr", -1, 7),
        ("sleep_hours", +1, 7),
        ("sleep_score", +1, 7),
        ("stress_avg", -1, 6),
        ("body_battery_latest", +1, 5),
    ]

    score = 50.0

    for metric, direction, weight in spec:
        stats = ref.get(metric, {})
        z = robust_z(
            today.get(metric),
            stats,
        )

        if z is None:
            continue

        baseline_ns.append(
            int(stats.get("n") or 0)
        )

        effect = (
            max(-1.5, min(1.5, z))
            / 1.5
        )

        points = (
            weight
            * direction
            * effect
        )

        score += points

        components.append({
            "metric": metric,
            "value": today.get(metric),
            "robust_z": z,
            "baseline_n": int(
                stats.get("n") or 0
            ),
            "points": round(points, 1),
        })

    recovery_hours = current_recovery_time(daily)

    if recovery_hours is not None:
        if recovery_hours >= 36:
            points = -8
        elif recovery_hours >= 24:
            points = -4
        elif recovery_hours < 12:
            points = 4
        else:
            points = 0

        components.append({
            "metric": "recovery_time_hours",
            "value": recovery_hours,
            "points": points,
        })

        score += points

    gm = (
        daily.get("garmin_metrics")
        if isinstance(daily, dict)
        else {}
    )

    tr = (
        gm.get("training_readiness")
        if isinstance(gm, dict)
        else None
    )

    gr = (
        num(tr.get("score"))
        if isinstance(tr, dict)
        else None
    )

    if gr is not None:
        points = max(
            -10,
            min(
                10,
                (gr - 50) * 0.2,
            ),
        )

        components.append({
            "metric": "garmin_training_readiness",
            "value": gr,
            "points": round(points, 1),
        })

        score += points

    score = int(
        round(
            max(
                0,
                min(100, score),
            )
        )
    )

    effective_baseline_days = (
        min(baseline_ns)
        if baseline_ns
        else 0
    )

    if (
        len(baseline_ns) >= 5
        and effective_baseline_days >= 21
    ):
        confidence = "high"
    elif (
        len(baseline_ns) >= 4
        and effective_baseline_days >= 7
    ):
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "score": score,
        "context": context,
        "baseline_used": (
            context
            if use_context
            else "overall"
        ),
        "effective_baseline_days": (
            effective_baseline_days
        ),
        "components": components,
        "confidence": confidence,
        "provisional": confidence != "high",
    }


def convergence_alert(records, baselines, daily):
    today = records.get(
        TODAY.isoformat(),
        {},
    )

    ref = (
        baselines
        .get("overall", {})
        .get("metrics", {})
    )

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
    skipped_for_short_baseline = []
    strong = False

    for name, metric, direction, threshold in checks:
        stats = ref.get(metric, {})
        n = int(stats.get("n") or 0)

        if n < 7:
            skipped_for_short_baseline.append({
                "signal": name,
                "metric": metric,
                "baseline_n": n,
            })
            continue

        z = robust_z(
            today.get(metric),
            stats,
        )

        if z is None:
            continue

        triggered = (
            z <= threshold
            if direction < 0
            else z >= threshold
        )

        if triggered:
            signals.append({
                "signal": name,
                "value": today.get(metric),
                "robust_z": z,
                "baseline_n": n,
            })

            if abs(z) >= 1.5:
                strong = True

    rt = current_recovery_time(daily)

    if rt is not None and rt >= 24:
        signals.append({
            "signal": "recovery_time_high",
            "value_hours": round(rt, 1),
        })

        if rt >= 36:
            strong = True

    severity = (
        "red"
        if len(signals) >= 4
        or (
            len(signals) >= 3
            and strong
        )
        else "yellow"
        if len(signals) >= 3
        else "none"
    )

    return {
        "severity": severity,
        "signal_count": len(signals),
        "signals": signals,
        "skipped_for_short_baseline": (
            skipped_for_short_baseline
        ),
        "rule": (
            "Alerts require converging signals and at least "
            "7 historical observations per baseline metric. "
            "Isolated changes are not diagnostic."
        ),
    }


def data_quality(
    records,
    activities,
    heart,
    daily,
    advanced_inputs,
):
    issues = []
    today = records.get(
        TODAY.isoformat(),
        {},
    )

    # V2.4.10: early-day Garmin readings are pending, not missing.
    # Las lecturas del día no se consideran definitivas al inicio de la jornada.
    # La certificación de sueño y recuperación sigue siendo independiente.
    # V2.4.11: post-night-shift sleep may extend into the afternoon.
    # La ausencia de sueno posterior a TN no prueba un fallo de Garmin.
    # Mantener una ventana mas amplia SOLO en dia post-TN.
    # El modelo principal de recuperacion conserva sus bloqueos.
    from .shift_calendar import resolve_day
    post_tn = bool(resolve_day(TODAY.isoformat()).get("post_tn"))
    pending_limit_hour = 18 if post_tn else 10
    day_start_pending = NOW.hour < pending_limit_hour and (
        not today or bool(today.get("hr_partial_day"))
    )
    pending_today = []

    score = 100

    if not today:
        if day_start_pending:
            pending_today.append("today_record_pending_day_start")
        else:
            issues.append("missing_today_record")
            score -= 30

    if (
        today
        and not today.get(
            "sleep_window_available"
        )
    ):
        if day_start_pending:
            pending_today.append("sleep_window_pending_day_start")
        else:
            issues.append("missing_sleep_window")
            score -= 15

    if (
        today
        and today.get(
            "night_hr_samples",
            0,
        ) < 60
    ):
        if day_start_pending:
            pending_today.append("night_hr_pending_day_start")
        else:
            issues.append("low_night_hr_coverage")
            score -= 10

    if (
        today
        and today.get(
            "day_hr_samples",
            0,
        ) < 120
        and not today.get(
            "hr_partial_day"
        )
    ):
        issues.append("low_day_hr_coverage")
        score -= 10

    if not isinstance(activities, list):
        issues.append("activities_invalid")
        score -= 20
    elif not activities:
        issues.append("activities_empty")
        score -= 5

    if (
        not isinstance(heart, dict)
        or not heart.get("days")
    ):
        issues.append(
            "heart_rate_history_missing"
        )
        score -= 25

    # Baseline coverage uses completed historical days only; TODAY is excluded.
    dates_28 = [
        (
            TODAY - timedelta(days=i)
        ).isoformat()
        for i in range(1, 29)
    ]

    coverage = {}

    for metric in METRICS:
        n = sum(
            1
            for ds in dates_28
            if num(
                records
                .get(ds, {})
                .get(metric)
            ) is not None
        )

        coverage[metric] = {
            "days_present": n,
            "days_expected": 28,
            "pct": round(
                100 * n / 28,
                1,
            ),
        }

    if coverage["hrv"]["days_present"] < 7:
        issues.append("short_hrv_baseline")
        score -= 5

    if coverage["nighttime_hr"]["days_present"] < 7:
        issues.append("short_night_hr_baseline")
        score -= 5

    if coverage["sleep_hours"]["days_present"] < 7:
        issues.append("short_sleep_baseline")

    if coverage["sleep_score"]["days_present"] < 7:
        issues.append("short_sleep_score_baseline")

    if coverage["respiration"]["days_present"] < 7:
        issues.append("short_respiration_baseline")

    key_history_days = min(
        coverage["hrv"]["days_present"],
        coverage["sleep_hours"]["days_present"],
        coverage["nighttime_hr"]["days_present"],
    )

    if key_history_days < 7:
        issues.append("baseline_immature")
        score = min(score, 74)
        baseline_maturity = "provisional"
    elif key_history_days < 14:
        score = min(score, 84)
        baseline_maturity = "developing"
    elif key_history_days < 21:
        score = min(score, 89)
        baseline_maturity = "usable"
    else:
        baseline_maturity = "mature"

    # Las lecturas pendientes no equivalen a una recuperación definitiva.
    # No elevar artificialmente la confianza de una jornada incompleta.
    if pending_today:
        score = min(score, 74)

    latest = {}

    for name, obj in advanced_inputs.items():
        if isinstance(obj, dict):
            latest[name] = obj.get(
                "generated_at"
            )

    status = (
        "good"
        if score >= 85
        else "usable"
        if score >= 65
        else "limited"
        if score >= 45
        else "critical"
    )

    confidence = (
        "high"
        if score >= 85
        else "medium"
        if score >= 65
        else "low"
    )

    return {
        "generated_at": NOW.isoformat(),
        "score": max(0, score),
        "status": status,
        "confidence": confidence,
        "baseline_maturity": baseline_maturity,
        "key_history_days": key_history_days,
        "issues": issues,
        "pending_today": pending_today,
        "today_availability_state": (
            "post_tn_sleep_pending" if post_tn and pending_today
            else "early_day_pending" if pending_today else "evaluated"
        ),
        "coverage_28d": coverage,
        "today": {
            "heart_rate_partial_day": bool(
                today.get("hr_partial_day")
            ),
            "day_hr_samples": today.get(
                "day_hr_samples"
            ),
            "night_hr_samples": today.get(
                "night_hr_samples"
            ),
            "sleep_window_available": today.get(
                "sleep_window_available"
            ),
        },
        "source_generated_at": latest,
    }


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
