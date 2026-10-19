"""«De un vistazo» (V7.16): cuatro o cinco fichas con el estado de la actividad y de los registros. Módulo puro."""
from __future__ import annotations

from datetime import date

SHIFT_TEXT = {"MT": "mañana-tarde 08–22", "TN": "noche 15–08", "free": "libre", "post-TN": "libre tras la noche", "unknown": "sin registrar"}


def _n(v, d=1):
    return f"{v:.{d}f}".rstrip("0").rstrip(".").replace(".", ",") if isinstance(v, (int, float)) else "—"


def _ago(day: str, today: str) -> str:
    n = (date.fromisoformat(today[:10]) - date.fromisoformat(day[:10])).days
    return "hoy" if n == 0 else "ayer" if n == 1 else f"hace {n} días" if n > 1 else "—"


def compose(result: dict, shifts: dict | None = None, progression: dict | None = None) -> list[dict]:
    """Fichas {id, label, value, sub, tone} con tone ∈ good | warning | critical | neutral. Solo cifras presentes en los datos."""
    chips: list[dict] = []
    today = str(result.get("date") or "")[:10]
    sessions = [s for s in (result.get("sessions_28d") or result.get("recent_sessions") or []) if isinstance(s, dict) and s.get("date")]
    sessions.sort(key=lambda s: (s["date"], str(s.get("start_local") or "")))
    if sessions and today:
        last = sessions[-1]
        rpe = last.get("rpe")
        label = str(last.get("name") or last.get("type") or "Sesión")
        chips.append({"id": "ultimo", "label": "Último entreno",
                      "value": label + (f" · RPE {_n(rpe)}" if rpe is not None else " · sin RPE"),
                      "sub": f"{_ago(last['date'], today)}" + (f" · {_n(last.get('duration_min'), 0)} min" if last.get("duration_min") else ""),
                      "tone": "warning" if (rpe is not None and rpe >= 9) or rpe is None else "neutral"})
        week = [s for s in sessions if 0 <= (date.fromisoformat(today) - date.fromisoformat(s["date"][:10])).days <= 6]
        if week:
            miss = sum(1 for s in week if s.get("rpe") is None)
            chips.append({"id": "registros", "label": "Registros de la semana",
                          "value": f"{len(week) - miss} de {len(week)} con RPE",
                          "sub": "al día" if not miss else f"faltan {miss}: dicta el RPE para completar la carga",
                          "tone": "good" if not miss else "warning"})
    load = result.get("load") if isinstance(result.get("load"), dict) else {}
    if load.get("week_sessions") is not None and load.get("week_load") is not None:
        change = load.get("week_change_pct")
        full = (load.get("coverage_days") or 0) >= 14 and (load.get("srpe_coverage_7d_pct") or 0) >= 90
        sub = (f"{change:+.0f} % de carga frente a la semana previa".replace(".", ",") if change is not None and full
               else "sin semana previa completa para comparar")
        chips.append({"id": "semana", "label": "Últimos 7 días", "value": f"{int(load['week_sessions'])} sesiones · carga {_n(load['week_load'], 0)}",
                      "sub": sub, "tone": "warning" if (change is not None and full and change >= 30) else "neutral"})
    if isinstance(shifts, dict) and (shifts.get("today") or shifts.get("tomorrow")):
        t, m = shifts.get("today") or "unknown", shifts.get("tomorrow") or "unknown"
        chips.append({"id": "turno", "label": "Turno", "value": f"Hoy {SHIFT_TEXT.get(t, t)}", "sub": f"Mañana {SHIFT_TEXT.get(m, m)}",
                      "tone": "warning" if t == "TN" or m == "TN" else "neutral"})
    s = (progression or {}).get("summary") if isinstance(progression, dict) else None
    if isinstance(s, dict) and s.get("available"):
        chips.append({"id": "progresion", "label": "Progresión de cargas", "value": f"{s['up']} ▲ · {s['flat']} = · {s['down']} ▼",
                      "sub": f"{s['comparable']} ejercicios repetidos, frente a la sesión anterior",
                      "tone": "good" if s["up"] > s["down"] else "warning" if s["down"] > s["up"] else "neutral"})
    return chips
