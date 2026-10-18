"""Contraste de actividades Garmin ↔ Intervals.icu (últimos días).

Garmin se lee directo; Intervals llega por sincronización. Una actividad que está en Garmin y no
en Intervals (por hora de inicio, ±2 min) aún no puede llevar RPE ni contar en la carga del informe.
Es un respaldo de visibilidad: no crea ni modifica actividades.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

TOLERANCE_MIN = 2


def _dt(v):
    try:
        return datetime.fromisoformat(str(v).replace("Z", "").replace(" ", "T")[:19])
    except (TypeError, ValueError):
        return None


def garmin_activities(ext_days: dict, since: str, until: str) -> list[dict]:
    out = []
    for day, row in (ext_days or {}).items():
        if not isinstance(row, dict) or not (since <= day <= until):
            continue
        for a in (row.get("activity_metrics") or {}).get("activities") or []:
            if isinstance(a, dict) and _dt(a.get("start_time_local")):
                out.append({"id": a.get("activity_id"), "start": _dt(a["start_time_local"]), "name": a.get("activity_name"),
                            "minutes": a.get("duration_minutes")})
    return sorted(out, key=lambda x: x["start"])


def compute(ext_days: dict, intervals: list, today: str, window_days: int = 7) -> dict:
    since = (date.fromisoformat(today) - timedelta(days=window_days - 1)).isoformat()
    g = garmin_activities(ext_days, since, today)
    starts = [s for s in (_dt(x.get("start_date_local")) for x in intervals if isinstance(x, dict)) if s]
    tol = timedelta(minutes=TOLERANCE_MIN)
    missing = [a for a in g if not any(abs(a["start"] - s) <= tol for s in starts)]
    return {"window_days": window_days, "garmin_count": len(g), "missing_in_intervals": missing,
            "intervals_known": bool(starts)}


def to_markdown(r: dict) -> str:
    if not r["garmin_count"]:
        return "Contraste Garmin ↔ Intervals: Garmin no aporta actividades en los últimos %d días." % r["window_days"]
    if not r["missing_in_intervals"]:
        return (f"Contraste Garmin ↔ Intervals: las {r['garmin_count']} actividades de Garmin de los últimos "
                f"{r['window_days']} días constan también en Intervals.")
    lines = [f"Contraste Garmin ↔ Intervals: {len(r['missing_in_intervals'])} de {r['garmin_count']} actividades de Garmin "
             f"({r['window_days']} días) no constan aún en Intervals, así que no cuentan en la carga ni admiten RPE hasta que se sincronicen:"]
    for a in r["missing_in_intervals"][:8]:
        m = f", {a['minutes']:.0f} min" if isinstance(a.get("minutes"), (int, float)) else ""
        lines.append(f"- {a['start'].strftime('%d/%m %H:%M')} · {a.get('name') or 'sin nombre'}{m}")
    return "\n".join(lines)
