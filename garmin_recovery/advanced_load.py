"""Carga semanal de las actividades (7 días frente a 28), sin reloj: el día llega como argumento.

Extraído de ``advanced.py`` (V7.25) con salida idéntica; ``advanced`` lo envuelve con su ``TODAY``/``NOW``."""
import statistics
from datetime import timedelta

from .advanced_core import num, safe_date


def weekly_load_metrics(activity_rows, *, today_date):
    start = today_date - timedelta(days=6)
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

        if not d or d < start or d > today_date:
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
        ds <= today_date.isoformat()
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
