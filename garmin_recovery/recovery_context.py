"""V8.13: intensidad semanal, recuperación según el tipo de día (turnos) y contexto de hoy.

- Intensidad semanal: sesiones con RPE, cuántas a RPE ≥ 8 y días suaves (sin sesión o con RPE ≤ 5 / sin puntuar).
- Tipo de día: post-TN (el día siguiente a un turno de noche), día de TN, día de MT o libre, según
  ``shift_calendar.json``. Se comparan medias de recuperación (puntuación, VFC, sueño) y de RPE por tipo,
  solo con al menos ``MIN_DAYS`` días por grupo.
- Hoy: tipo de día, turno de mañana y si ayer la sesión más dura superó el máximo que permitía la decisión.
Es descriptivo: no atribuye causas.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

HARD_RPE = 8
EASY_RPE = 5
WEEKS = 6
MIN_DAYS = 3
RPE_MAX = {"green": 9, "yellow": 7, "red": 4, "unavailable": 6}
TYPES = [("post_tn", "Post-TN"), ("tn", "Día de TN"), ("mt", "Día de MT"), ("libre", "Libre")]


def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x


def _csv(path: Path) -> list[dict]:
    try:
        with path.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except OSError:
        return []


def _week(d: str) -> str:
    y, w, _ = date.fromisoformat(d).isocalendar()
    return f"{y}-S{w:02d}"


def _monday(d: str) -> date:
    x = date.fromisoformat(d)
    return x - timedelta(days=x.weekday())


def weekly_intensity(sessions: list[dict], today: str, weeks: int = WEEKS) -> list[dict]:
    """Semanas ISO (de la más antigua a la actual): sesiones, puntuadas, duras, días entrenados y días suaves."""
    start = _monday(today) - timedelta(weeks=weeks - 1)
    by_day: dict[str, list] = {}
    for s in sessions:
        d = str(s.get("date") or "")[:10]
        if not d or s.get("removed") in (1, "1") or d > today or date.fromisoformat(d) < start:
            continue
        by_day.setdefault(d, []).append(_f(s.get("rpe")))
    first = min(by_day) if by_day else None
    out = []
    for k in range(weeks):
        mon = start + timedelta(weeks=k)
        if first is None or (mon + timedelta(days=6)).isoformat() < first:
            continue  # semanas anteriores al primer registro: no son «días suaves», es que no había datos
        days = [(mon + timedelta(days=i)).isoformat() for i in range(7)]
        elapsed = [d for d in days if d <= today]
        rpes = [r for d in elapsed for r in by_day.get(d, [])]
        scored = [r for r in rpes if r is not None]
        hard = sum(1 for r in scored if r >= HARD_RPE)
        easy = sum(1 for d in elapsed if not by_day.get(d) or all(r is None or r <= EASY_RPE for r in by_day[d]))
        out.append({"week": _week(days[0]), "monday": days[0], "current": today in days, "days": len(elapsed),
                    "sessions": len(rpes), "scored": len(scored), "hard": hard,
                    "hard_pct": round(100 * hard / len(scored)) if scored else None,
                    "trained_days": sum(1 for d in elapsed if by_day.get(d)), "easy_days": easy})
    return out


def day_type(d: str, shifts: dict) -> str:
    prev = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
    if shifts.get(prev) == "TN":
        return "post_tn"
    return {"TN": "tn", "MT": "mt"}.get(shifts.get(d), "libre")


def by_day_type(daily: list[dict], sessions: list[dict], shifts: dict, today: str) -> dict:
    sess_by_day: dict[str, list] = {}
    for s in sessions:
        r = _f(s.get("rpe"))
        if r is not None and s.get("removed") not in (1, "1"):
            sess_by_day.setdefault(str(s.get("date"))[:10], []).append(r)
    groups = {k: {"score": [], "hrv": [], "sleep": [], "rpe": [], "days": 0} for k, _ in TYPES}
    for row in daily:
        d = str(row.get("date") or "")[:10]
        if not d or d > today:
            continue
        g = groups[day_type(d, shifts)]
        score = _f(row.get("v3_score")) or _f(row.get("hybrid_score"))
        if score is None and _f(row.get("hrv_ms")) is None:
            continue  # día sin datos de recuperación
        g["days"] += 1
        for key, val in (("score", score), ("hrv", _f(row.get("hrv_ms"))), ("sleep", _f(row.get("sleep_hours")))):
            if val is not None:
                g[key].append(val)
        g["rpe"] += sess_by_day.get(d, [])
    rows = []
    for k, label in TYPES:
        g = groups[k]
        ok = g["days"] >= MIN_DAYS
        rows.append({"type": k, "label": label, "days": g["days"], "enough": ok,
                     "score": round(mean(g["score"])) if ok and g["score"] else None,
                     "hrv": round(mean(g["hrv"])) if ok and g["hrv"] else None,
                     "sleep": round(mean(g["sleep"]), 1) if ok and g["sleep"] else None,
                     "rpe": round(mean(g["rpe"]), 1) if ok and g["rpe"] else None, "sessions": len(g["rpe"])})
    return {"rows": rows, "available": sum(1 for r in rows if r["enough"]) >= 2}


def today_context(result: dict, daily: list[dict], sessions: list[dict], shifts: dict) -> dict:
    today = str(result.get("date") or "")[:10]
    t = day_type(today, shifts)
    tomorrow = shifts.get((date.fromisoformat(today) + timedelta(days=1)).isoformat())
    lines = []
    if t == "post_tn":
        lines.append("Vienes de turno de noche: el sueño de día suele recuperar menos; si el semáforo no está en verde, prioriza técnica o un bloque suave sin RPE.")
    elif t == "tn":
        lines.append("Hoy tienes turno de noche: si entrenas, que sea pronto y sin agotarte antes del turno.")
    if tomorrow == "TN":
        lines.append("Mañana tienes turno de noche: evita acabar hoy muy cargado.")
    yday = (date.fromisoformat(today) - timedelta(days=1)).isoformat()
    zone = next((r.get("decision_zone") for r in daily if str(r.get("date"))[:10] == yday), None)
    rpes = [r for s in sessions if str(s.get("date"))[:10] == yday and (r := _f(s.get("rpe"))) is not None]
    over = None
    if zone in RPE_MAX and rpes and max(rpes) > RPE_MAX[zone]:
        over = {"rpe": max(rpes), "max": RPE_MAX[zone]}
        lines.append(f"Ayer la sesión más dura fue RPE {max(rpes):g} con un máximo recomendado de {RPE_MAX[zone]}.")
    return {"type": t, "type_label": dict(TYPES)[t], "tomorrow": tomorrow, "lines": lines, "over_yesterday": over}


def build(root: str | Path, result: dict) -> dict:
    root = Path(root)
    today = str(result.get("date") or "")[:10]
    from . import shift_calendar
    cal = shift_calendar.load_calendar(str(root / "shift_calendar.json"))
    shifts = {}
    for k in range(-90, 2):
        d = date.fromisoformat(today) + timedelta(days=k)
        label = shift_calendar.resolve_day(d, cal)["label"]
        shifts[d.isoformat()] = label if label in ("TN", "MT") else None
    daily = _csv(root / "history" / "daily.csv")
    sessions = _csv(root / "history" / "sessions.csv")
    if not sessions:
        sessions = [s for s in result.get("sessions_28d") or [] if isinstance(s, dict)]
    return {"weekly": weekly_intensity(sessions, today), "day_types": by_day_type(daily, sessions, shifts, today),
            "today": today_context(result, daily, sessions, shifts)}
