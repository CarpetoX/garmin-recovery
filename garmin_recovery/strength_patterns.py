"""Carga de fuerza por patrón de movimiento (7 y 28 días) a partir de series declaradas.

Solo suma series conocidas; el volumen en kg solo cuenta barra con carga total y volumen completo,
sin mezclar equipos ni lados no confirmados.
"""
from __future__ import annotations

from datetime import date, timedelta

LABELS = {"squat": "Sentadilla", "hinge": "Bisagra de cadera", "push": "Empuje", "horizontal_push": "Empuje horizontal", "vertical_push": "Empuje vertical",
          "pull": "Tirón", "horizontal_pull": "Tirón horizontal", "vertical_pull": "Tirón vertical",
          "chest_isolation": "Pecho (aislamiento)", "triceps_isolation": "Tríceps (aislamiento)",
          "biceps_isolation": "Bíceps (aislamiento)", "knee_flexion": "Flexión de rodilla",
          "knee_extension": "Extensión de rodilla", "lunge": "Zancada",
          "carry": "Acarreo", "core": "Core", "olympic": "Halterofilia", "olympic_lift": "Halterofilia",
          "single_leg": "Unilateral de pierna", "other": "Otros", "sin_clasificar": "Sin clasificar"}


def _n(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def compute(rows, today: str) -> dict:
    t = date.fromisoformat(today)
    cut = {"7d": (t - timedelta(days=6)).isoformat(), "28d": (t - timedelta(days=27)).isoformat()}
    seen, acc = set(), []
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict):
            continue
        d = str(r.get("date") or "")
        key = (r.get("activity_id"), d, r.get("exercise"), r.get("equipment"))
        if not d or d > today or d < cut["28d"] or not r.get("activity_id") or key in seen:
            continue
        seen.add(key)
        acc.append(r)
    out = {}
    for period, start in cut.items():
        pats: dict = {}
        for r in acc:
            if r["date"] < start:
                continue
            p = pats.setdefault(r.get("movement_pattern") or "sin_clasificar",
                                {"blocks": 0, "sets": 0, "sets_unknown": 0, "bar_kg": 0.0, "bar_partial": False, "days": set()})
            p["blocks"] += 1
            p["days"].add(r["date"])
            # V8.7: series declaradas (también las de peso corporal: 4 × 25 sit-ups son 4 series), no solo las que llevan kilos
            ks = r.get("total_sets") if type(r.get("total_sets")) is int else r.get("known_sets")
            if type(ks) is int and ks >= 0:
                p["sets"] += ks
            else:
                p["sets_unknown"] += 1
            if r.get("equipment") == "barbell" and r.get("load_unit") == "kg_total_barra" and _n(r.get("verified_volume_kg")) is not None:
                if r.get("volume_complete") is True and r.get("laterality_unconfirmed") is not True:
                    p["bar_kg"] += r["verified_volume_kg"]
                else:
                    p["bar_partial"] = True
        out[period] = {k: dict(v, days=len(v["days"])) for k, v in pats.items()}
    return out


def to_markdown(res: dict) -> str:
    pats = sorted(set(res.get("7d", {})) | set(res.get("28d", {})))
    if not pats:
        return "No hay series de fuerza declaradas en los últimos 28 días."
    f = lambda v: f"{v:,.0f}".replace(",", ".")  # noqa: E731
    lines = ["| Patrón | 7 d: bloques · series | 7 d: barra (kg) | 28 d: bloques · series | 28 d: barra (kg) |", "|---|---|---|---|---|"]

    def cell(p):
        if not p:
            return "—", "—"
        extra = "+" if p["sets_unknown"] else ""
        kg = (f(p["bar_kg"]) + (" (parcial)" if p["bar_partial"] else "")) if (p["bar_kg"] or p["bar_partial"]) else "—"
        return f"{p['blocks']} · {p['sets']}{extra}", kg

    for k in pats:
        a, b = cell(res["7d"].get(k)), cell(res["28d"].get(k))
        lines.append(f"| {LABELS.get(k, k)} | {a[0]} | {a[1]} | {b[0]} | {b[1]} |")
    return "\n".join(lines) + ("\n\nSolo series declaradas; «+» indica bloques sin número de series. El volumen en kg cuenta únicamente barra con "
                               "carga total y volumen completo; no se suma entre equipos. Un patrón sin registros no demuestra que no se entrenara.")
