"""Margen para el tren inferior tras una serie o ejercicio de piernas muy duro (regla orientativa, sin validar).

El RPE global de una sesión puede ser moderado (7,5) aunque una serie de sentadilla haya sido casi máxima (9,5): la
recuperación general del día no mide esa fatiga muscular. Regla: un ejercicio de tren inferior con RPE >= 9 bloquea otra
sesión pesada de piernas 48 h; con RPE 8–8,9, 24 h. Solo usa el RPE de ejercicio declarado por el atleta.
"""
from __future__ import annotations

from datetime import date, timedelta

LOWER = {"squat", "hinge", "lunge", "knee_flexion", "knee_extension", "olympic"}
HARD, VERY_HARD = 8.0, 9.0


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def compute(crossfit: dict | None, today: str, lookback_days: int = 3) -> dict:
    cf = crossfit if isinstance(crossfit, dict) else {}
    patterns = {}
    for r in (cf.get("muscle_load") or {}).get("strength_exercises") or []:
        if isinstance(r, dict) and r.get("exercise") and r.get("movement_pattern"):
            patterns[str(r["exercise"]).strip().lower()] = r["movement_pattern"]
    t = date.fromisoformat(today)
    best = None
    for a in cf.get("activities") or []:
        if not isinstance(a, dict) or not a.get("date"):
            continue
        try:
            d = date.fromisoformat(a["date"])
        except ValueError:
            continue
        if d > t or (t - d).days > lookback_days:
            continue
        for b in a.get("manual_blocks") or []:
            detail = b.get("detail_json") if isinstance(b, dict) else None
            for e in (detail.get("exercises") if isinstance(detail, dict) else None) or []:
                if not isinstance(e, dict):
                    continue
                rpe = _num(e.get("rpe"))
                name = str(e.get("name") or "").strip()
                if rpe is None or rpe < HARD or patterns.get(name.lower()) not in LOWER:
                    continue
                until = d + timedelta(days=2 if rpe >= VERY_HARD else 1)
                cand = {"until": until.isoformat(), "date": d.isoformat(), "exercise": name, "rpe": rpe,
                        "hours": 48 if rpe >= VERY_HARD else 24}
                if best is None or cand["until"] > best["until"] or (cand["until"] == best["until"] and rpe > best["rpe"]):
                    best = cand
    if best and best["until"] <= today:
        best = None  # el margen ya terminó
    return {"legs": best}


def note(legs: dict | None) -> str | None:
    if not legs:
        return None
    f = lambda v: f"{v:.1f}".replace(".", ",").replace(",0", "")  # noqa: E731
    u = legs["until"]
    return (f"{legs['exercise'].capitalize()} a RPE {f(legs['rpe'])} el {legs['date'][8:]}/{legs['date'][5:7]}: evita otra sesión "
            f"pesada de piernas hasta el {u[8:]}/{u[5:7]} (margen orientativo de {legs['hours']} h, sin validar). "
            "Tren superior, técnica o aeróbico suave sí encajan.")
