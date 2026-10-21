"""Índice personal de recuperación y alerta de convergencia, sin reloj: el día llega como argumento.

Extraído de ``advanced.py`` (V7.25) con salida idéntica; ``advanced`` lo envuelve con su ``TODAY``/``NOW``."""
from .advanced_core import num, robust_z
from .advanced_models import current_recovery_time


def personal_recovery_index(records, baselines, daily, *, today_date):
    today = records.get(
        today_date.isoformat(),
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


def convergence_alert(records, baselines, daily, *, today_date):
    today = records.get(
        today_date.isoformat(),
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
