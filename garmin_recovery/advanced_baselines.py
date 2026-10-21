"""Líneas base robustas de 7/28 días y por contexto (turno, sueño), sin reloj: el día llega como argumento.

Extraído de ``advanced.py`` (V7.25) con salida idéntica; ``advanced`` lo envuelve con su ``TODAY``/``NOW``."""
from datetime import timedelta

from .advanced_core import METRICS, linear_slope, robust_stats, safe_date


def rolling_robust(records, *, today_date):
    result = {}

    for window in (3, 7, 28):
        dates = [
            (today_date - timedelta(days=i)).isoformat()
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


def baselines_by_context(records, *, today_date):
    """Use only completed historical days; never include TODAY in its own baseline."""
    start = today_date - timedelta(days=28)

    eligible = [
        r
        for ds, r in records.items()
        if safe_date(ds)
        and start <= safe_date(ds) < today_date
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
