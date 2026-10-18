"""Modelos: respuesta al entrenamiento, readiness híbrido y calibración."""
from datetime import timedelta
import statistics
from .advanced_core import num, pearson, robust_z, safe_date


def day_median(records, metric, dates):
    vals = [
        records.get(d.isoformat(), {}).get(metric)
        for d in dates
    ]

    xs = [
        num(v)
        for v in vals
        if num(v) is not None
    ]

    return statistics.median(xs) if xs else None

def training_response_24_48(records, activity_rows):
    by_date = {}

    for row in activity_rows:
        ds = row.get("date")
        if not ds:
            continue

        by_date.setdefault(ds, []).append(row)

    out = []

    for ds, sessions in sorted(by_date.items()):
        d = safe_date(ds)

        if not d:
            continue

        pre_dates = [
            d - timedelta(days=i)
            for i in (3, 2, 1)
        ]

        base = {
            metric: day_median(
                records,
                metric,
                pre_dates,
            )
            for metric in (
                "hrv",
                "nighttime_hr",
                "resting_hr",
                "sleep_hours",
                "sleep_score",
            )
        }

        loads = {
            "intervals_training_load": round(
                sum(
                    num(
                        x.get(
                            "internal_load",
                            {},
                        ).get(
                            "intervals_training_load"
                        )
                    )
                    or 0
                    for x in sessions
                ),
                1,
            ),
            "garmin_activity_load": round(
                sum(
                    num(
                        x.get(
                            "internal_load",
                            {},
                        ).get(
                            "garmin_activity_load"
                        )
                    )
                    or 0
                    for x in sessions
                ),
                1,
            ),
            "trimp": round(
                sum(
                    num(
                        x.get(
                            "internal_load",
                            {},
                        ).get("trimp")
                    )
                    or 0
                    for x in sessions
                ),
                1,
            ),
            "session_rpe_load": round(
                sum(
                    num(
                        x.get(
                            "internal_load",
                            {},
                        ).get(
                            "session_rpe_load"
                        )
                    )
                    or 0
                    for x in sessions
                ),
                1,
            ),
        }

        item = {
            "date": ds,
            "sessions": len(sessions),
            "loads": loads,
            "baseline_previous_3d": {
                k: round(v, 2)
                if v is not None
                else None
                for k, v in base.items()
            },
            "response": {},
        }

        for lag in (1, 2):
            rec = records.get(
                (
                    d + timedelta(days=lag)
                ).isoformat(),
                {},
            )

            hrv = num(rec.get("hrv"))
            nh = num(rec.get("nighttime_hr"))
            rh = num(rec.get("resting_hr"))
            sh = num(rec.get("sleep_hours"))
            ss = num(rec.get("sleep_score"))

            response = {
                "hrv_pct": (
                    round(
                        100
                        * (hrv - base["hrv"])
                        / base["hrv"],
                        1,
                    )
                    if hrv is not None
                    and base["hrv"] not in (None, 0)
                    else None
                ),
                "nighttime_hr_delta": (
                    round(
                        nh - base["nighttime_hr"],
                        1,
                    )
                    if nh is not None
                    and base["nighttime_hr"] is not None
                    else None
                ),
                "resting_hr_delta": (
                    round(
                        rh - base["resting_hr"],
                        1,
                    )
                    if rh is not None
                    and base["resting_hr"] is not None
                    else None
                ),
                "sleep_hours_delta": (
                    round(
                        sh - base["sleep_hours"],
                        2,
                    )
                    if sh is not None
                    and base["sleep_hours"] is not None
                    else None
                ),
                "sleep_score_delta": (
                    round(
                        ss - base["sleep_score"],
                        1,
                    )
                    if ss is not None
                    and base["sleep_score"] is not None
                    else None
                ),
            }

            adverse = []

            if (
                response["hrv_pct"] is not None
                and response["hrv_pct"] <= -10
            ):
                adverse.append("hrv_down")

            if (
                response["nighttime_hr_delta"] is not None
                and response["nighttime_hr_delta"] >= 5
            ):
                adverse.append("night_hr_up")

            if (
                response["resting_hr_delta"] is not None
                and response["resting_hr_delta"] >= 5
            ):
                adverse.append("resting_hr_up")

            if (
                response["sleep_hours_delta"] is not None
                and response["sleep_hours_delta"] <= -1
            ):
                adverse.append("sleep_duration_down")

            if (
                response["sleep_score_delta"] is not None
                and response["sleep_score_delta"] <= -10
            ):
                adverse.append("sleep_score_down")

            response["adverse_signals"] = adverse
            response["physiological_cost_signal"] = (
                "high"
                if len(adverse) >= 3
                else "moderate"
                if len(adverse) == 2
                else "mild"
                if len(adverse) == 1
                else "none"
            )

            item["response"][
                f"{lag * 24}h"
            ] = response

        out.append(item)

    return out[-35:]

def current_recovery_time(daily):
    if not isinstance(daily, dict):
        return None

    gm = daily.get("garmin_metrics") or {}
    rt = (
        gm.get("recovery_time")
        if isinstance(gm, dict)
        else None
    )

    if isinstance(rt, dict):
        hours = num(rt.get("hours"))
        if hours is not None:
            return hours

        minutes = num(rt.get("minutes"))
        if minutes is not None:
            return minutes / 60

    return None

def hybrid_readiness(daily):
    """Persist the user's requested hybrid readiness and guardrails."""
    if not isinstance(daily, dict):
        return None

    local = daily.get("readiness_model") or {}
    gm = daily.get("garmin_metrics") or {}
    garmin = (
        gm.get("training_readiness")
        if isinstance(gm, dict)
        else None
    )

    local_score = (
        num(local.get("score"))
        if isinstance(local, dict)
        else None
    )
    local_confidence = str(
        local.get("confidence") or "low"
    ).lower()

    garmin_score = (
        num(garmin.get("score"))
        if isinstance(garmin, dict)
        else None
    )

    garmin_level = (
        str(garmin.get("level") or "")
        .strip()
        .upper()
        if isinstance(garmin, dict)
        else ""
    )

    if local_score is None and garmin_score is None:
        return None

    weights = {
        "low": {
            "garmin": 0.70,
            "local": 0.30,
        },
        "medium": {
            "garmin": 0.55,
            "local": 0.45,
        },
        "high": {
            "garmin": 0.40,
            "local": 0.60,
        },
    }

    selected = weights.get(
        local_confidence,
        weights["low"],
    )

    if (
        local_score is not None
        and garmin_score is not None
    ):
        raw_score = round(
            selected["garmin"] * garmin_score
            + selected["local"] * local_score
        )
        source_mode = "hybrid"
    elif garmin_score is not None:
        raw_score = round(garmin_score)
        source_mode = "garmin_only"
    else:
        raw_score = round(local_score)
        source_mode = "local_only"

    final_score = int(
        max(0, min(100, raw_score))
    )

    guardrails = []

    if garmin_score is not None and garmin_score < 35:
        final_score = min(final_score, 49)
        guardrails.append(
            "garmin_score_below_35_forces_red"
        )

    elif (
        garmin_score is not None
        and garmin_score < 50
    ) or garmin_level in {"LOW", "POOR"}:
        final_score = min(final_score, 74)
        guardrails.append(
            "garmin_low_prevents_green"
        )

    recovery_hours = current_recovery_time(daily)

    if (
        recovery_hours is not None
        and recovery_hours >= 24
    ):
        final_score = min(final_score, 74)
        guardrails.append(
            "recovery_time_24h_or_more_prevents_green"
        )

    if final_score >= 75:
        status = "green"
        volume = "90-100%"
        recommendation = "normal"
    elif final_score >= 50:
        status = "yellow"
        volume = "65-85%"
        recommendation = "moderate"
    else:
        status = "red"
        volume = "40-60%"
        recommendation = "recovery"

    return {
        "score": final_score,
        "raw_score_before_guardrails": int(
            max(0, min(100, raw_score))
        ),
        "status": status,
        "recommended_volume": volume,
        "recommendation": recommendation,
        "garmin_score": (
            round(garmin_score)
            if garmin_score is not None
            else None
        ),
        "garmin_level": garmin_level or None,
        "local_score": (
            round(local_score)
            if local_score is not None
            else None
        ),
        "local_confidence": local_confidence,
        "weights": (
            selected
            if source_mode == "hybrid"
            else None
        ),
        "source_mode": source_mode,
        "recovery_time_hours": (
            round(recovery_hours, 1)
            if recovery_hours is not None
            else None
        ),
        "guardrails_applied": guardrails,
        "note": (
            "Readiness híbrido para orientar entrenamiento. "
            "No es un diagnóstico médico."
        ),
    }

def performance_calibration(
    activity_rows,
    records,
    baselines,
    responses,
):
    response_by_date = {
        x.get("date"): x
        for x in responses
        if isinstance(x, dict)
    }

    observations = []

    overall = (
        baselines
        .get("overall", {})
        .get("metrics", {})
    )

    by_date = {}

    for row in activity_rows:
        if row.get("date"):
            by_date.setdefault(
                row["date"],
                [],
            ).append(row)

    for ds, sessions in sorted(by_date.items()):
        resp = (
            response_by_date
            .get(ds, {})
            .get("response", {})
            .get("24h", {})
        )

        if not isinstance(resp, dict):
            continue

        components = []

        if num(resp.get("hrv_pct")) is not None:
            components.append(
                max(
                    0,
                    -num(resp["hrv_pct"]) / 10,
                )
            )

        if num(resp.get("nighttime_hr_delta")) is not None:
            components.append(
                max(
                    0,
                    num(resp["nighttime_hr_delta"]) / 5,
                )
            )

        if num(resp.get("resting_hr_delta")) is not None:
            components.append(
                max(
                    0,
                    num(resp["resting_hr_delta"]) / 5,
                )
            )

        if num(resp.get("sleep_hours_delta")) is not None:
            components.append(
                max(
                    0,
                    -num(resp["sleep_hours_delta"]),
                )
            )

        if num(resp.get("sleep_score_delta")) is not None:
            components.append(
                max(
                    0,
                    -num(resp["sleep_score_delta"]) / 10,
                )
            )

        if len(components) < 2:
            continue

        rec = records.get(ds, {})

        internal = [
            x.get("internal_load", {})
            for x in sessions
        ]

        observation = {
            "date": ds,
            "recovery_cost_24h": round(
                sum(components),
                2,
            ),
            "pre_hrv_z": robust_z(
                rec.get("hrv"),
                overall.get("hrv", {}),
            ),
            "pre_night_hr_z": robust_z(
                rec.get("nighttime_hr"),
                overall.get("nighttime_hr", {}),
            ),
            "pre_sleep_hours_z": robust_z(
                rec.get("sleep_hours"),
                overall.get("sleep_hours", {}),
            ),
            "pre_stress_z": robust_z(
                rec.get("stress_avg"),
                overall.get("stress_avg", {}),
            ),
            "intervals_training_load": sum(
                num(
                    x.get(
                        "intervals_training_load"
                    )
                )
                or 0
                for x in internal
            ),
            "garmin_activity_load": sum(
                num(
                    x.get(
                        "garmin_activity_load"
                    )
                )
                or 0
                for x in internal
            ),
            "session_rpe_load": sum(
                num(
                    x.get(
                        "session_rpe_load"
                    )
                )
                or 0
                for x in internal
            ),
        }

        observations.append(observation)

    features = (
        "pre_hrv_z",
        "pre_night_hr_z",
        "pre_sleep_hours_z",
        "pre_stress_z",
        "intervals_training_load",
        "garmin_activity_load",
        "session_rpe_load",
    )

    correlations = {}

    for feature in features:
        corr = pearson(
            [
                o.get(feature)
                for o in observations
            ],
            [
                o.get("recovery_cost_24h")
                for o in observations
            ],
        )

        present = sum(
            1
            for o in observations
            if num(o.get(feature)) is not None
        )

        correlations[feature] = {
            "r": corr,
            "n": present,
        }

    usable = [
        (k, v["r"])
        for k, v in correlations.items()
        if v["r"] is not None
        and v["n"] >= 8
    ]

    learned_weights = {}

    if usable:
        denom = (
            sum(
                abs(r)
                for _, r in usable
            )
            or 1
        )

        learned_weights = {
            k: round(
                r / denom,
                3,
            )
            for k, r in usable
        }

    n = len(observations)

    status = (
        "mature"
        if n >= 30
        else "active"
        if n >= 12
        else "collecting"
    )

    return {
        "status": status,
        "observations": n,
        "minimum_for_correlations": 8,
        "recommended_for_stable_model": 30,
        "correlations_with_next_day_recovery_cost": correlations,
        "learned_relative_weights": learned_weights,
        "note": (
            "Personal calibration learns associations with next-day "
            "recovery cost. It remains descriptive, not diagnostic, "
            "and is not allowed to override data-quality guardrails."
        ),
    }
