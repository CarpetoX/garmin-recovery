"""Peso corporal (V7.19): serie, media de 7 días y cambios. Puro (sin reloj ni red); `main` no existe: lo carga `site`.

Los valores vienen de `peso_registro.json` (lo que el atleta muestra o dicta). Las lecturas «derivadas» se marcan y no
cuentan para la media; no hay causalidad ni interpretación médica.
"""
from __future__ import annotations

from datetime import date as _date, timedelta


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and 20 <= float(v) <= 400 else None


def build(registro: dict | None, today: str) -> dict | None:
    pts = []
    for e in (registro or {}).get("entries") or []:
        if not isinstance(e, dict) or not e.get("date") or _num(e.get("weight_kg")) is None or str(e["date"]) > today:
            continue
        pts.append({"date": str(e["date"]), "time": e.get("time"), "weight": _num(e["weight_kg"]),
                    "derived": str(e.get("source") or "").lower().startswith("deriv"),
                    "source": e.get("source") or "", "note": e.get("note") or "",
                    "fat_pct": _num(e.get("fat_pct")) if e.get("fat_pct") is not None else None,
                    "muscle_kg": e.get("muscle_kg"), "water_pct": e.get("water_pct")})
    if not pts:
        return None
    pts.sort(key=lambda p: (p["date"], p.get("time") or ""))
    last = pts[-1]
    t = _date.fromisoformat(today)
    direct7 = [p["weight"] for p in pts if not p["derived"] and _date.fromisoformat(p["date"]) >= t - timedelta(days=6)]
    out = {"points": pts, "current": last["weight"], "current_date": last["date"],
           "age_days": (t - _date.fromisoformat(last["date"])).days,
           "mean7": round(sum(direct7) / len(direct7), 1) if len(direct7) >= 2 else None, "n7": len(direct7)}
    if len(pts) >= 2:
        prev, first = pts[-2], pts[0]
        out["delta_prev"] = round(last["weight"] - prev["weight"], 1)
        out["prev_date"] = prev["date"]
        out["delta_first"] = round(last["weight"] - first["weight"], 1)
        out["first_date"] = first["date"]
        out["span_days"] = (_date.fromisoformat(last["date"]) - _date.fromisoformat(first["date"])).days
        out["has_derived"] = any(p["derived"] for p in pts)
    out["stale"] = out["age_days"] > 7
    return out
