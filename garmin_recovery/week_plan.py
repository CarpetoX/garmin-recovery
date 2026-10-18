"""Plan orientativo de 7 días que combina turnos, sesiones duras recientes y la decisión del día.

Reglas simples y explícitas (no es una prescripción personalizada):
- como máximo 3 sesiones duras (RPE ≥ 8) por semana móvil, separadas ≥ 48 h;
- las duras solo en días libres con turno confirmado; nunca tras una TN ni en un turno largo (MT);
- con zona roja o RPE máximo ≤ 6 hoy no se planifica nada duro;
- un turno sin confirmar se trata con prudencia (moderado).
"""
from __future__ import annotations

from datetime import date, timedelta

HARD_RPE = 8
MAX_HARD_PER_WEEK = 3
MIN_GAP_DAYS = 2
DAYS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def plan(today: str, shifts: dict, sessions: list, zone: str | None, rpe_max, legs: dict | None = None) -> list[dict]:
    t0 = date.fromisoformat(today)
    hard_days = sorted({date.fromisoformat(s["date"]) for s in sessions
                        if isinstance(s, dict) and _num(s.get("rpe")) is not None and s["rpe"] >= HARD_RPE
                        and s.get("date") and t0 - timedelta(days=6) <= date.fromisoformat(s["date"]) <= t0})
    trained_today = any(isinstance(s, dict) and s.get("date") == today for s in sessions)
    last_hard = hard_days[-1] if hard_days else None
    restricted_today = zone in ("red", "unavailable") or (_num(rpe_max) is not None and rpe_max <= 6)
    out = []
    for i in range(7):
        d = t0 + timedelta(days=i)
        info = shifts.get(d.isoformat()) or {}
        shift, post_tn = info.get("shift", "unknown"), bool(info.get("post_tn"))
        label = "post-TN" if post_tn and shift in ("free", "unknown") else shift
        kind, why = "moderate", "turno sin confirmar: prudencia"
        if i == 0 and trained_today:
            kind, why = "light", "ya has entrenado hoy"
        elif i == 0 and restricted_today:
            kind, why = "light", "la decisión de hoy limita la intensidad"
        elif post_tn:
            kind, why = "rest", "día posterior a una TN: prioriza dormir"
        elif shift == "TN":
            kind, why = "moderate", "TN por la tarde: si entrenas, por la mañana y moderado"
        elif shift == "MT":
            kind, why = "light", "turno largo: movilidad o descanso"
        elif shift == "free":
            gap_ok = last_hard is None or (d - last_hard).days >= MIN_GAP_DAYS
            in_window = sum(1 for h in hard_days if d - timedelta(days=6) <= h < d)
            next_info = shifts.get((d + timedelta(days=1)).isoformat()) or {}
            legs_blocked = bool(legs) and d.isoformat() < legs["until"]
            if legs_blocked:
                kind, why = "moderate", "día libre; tren superior o aeróbico tras la serie dura reciente de piernas"
            elif in_window < MAX_HARD_PER_WEEK and gap_ok:
                kind, why = "hard", "día libre con margen para una sesión exigente"
                hard_days.append(d)
                last_hard = d
            else:
                kind, why = "moderate", "día libre; sesión moderada para respetar el espaciado" if not gap_ok else "día libre; ya hay 3 sesiones duras en los últimos 7 días"
            if next_info.get("shift") == "TN" and kind == "hard":
                why += " (mañana TN: acuéstate pronto)"
        if legs and d.isoformat() < legs["until"]:
            u = legs["until"]
            why += f" · sin piernas pesadas hasta el {u[8:]}/{u[5:7]}"
        out.append({"date": d.isoformat(), "dow": DAYS[d.weekday()], "shift": label, "kind": kind, "why": why})
    return out


KIND_ES = {"hard": "🔥 Exigente", "moderate": "🟡 Moderada", "light": "🟢 Suave / movilidad", "rest": "🛌 Descanso"}


def to_markdown(rows: list[dict]) -> str:
    lines = ["| Día | Turno | Sesión sugerida | Motivo |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['dow']} {r['date'][8:]}/{r['date'][5:7]} | {r['shift']} | {KIND_ES[r['kind']]} | {r['why']} |")
    return "\n".join(lines) + ("\n\nPlan orientativo por reglas (máx. 3 sesiones con RPE ≥ 8 por semana, separadas ≥ 48 h, solo en días libres). "
                              "Se recalcula en cada informe y la decisión del día manda sobre él.")
