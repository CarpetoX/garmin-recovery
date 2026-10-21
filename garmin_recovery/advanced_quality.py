"""Calidad y cobertura de los datos fisiológicos, sin reloj: el día y la hora llegan como argumentos.

Extraído de ``advanced.py`` (V7.25) con salida idéntica; ``advanced`` lo envuelve con su ``TODAY``/``NOW``."""
from datetime import timedelta

from .advanced_core import METRICS, num


def data_quality(records, activities, heart, daily, advanced_inputs, *, today_date, now_dt):
    issues = []
    today = records.get(
        today_date.isoformat(),
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
    post_tn = bool(resolve_day(today_date.isoformat()).get("post_tn"))
    pending_limit_hour = 18 if post_tn else 10
    day_start_pending = now_dt.hour < pending_limit_hour and (
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
            today_date - timedelta(days=i)
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
        "generated_at": now_dt.isoformat(),
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
