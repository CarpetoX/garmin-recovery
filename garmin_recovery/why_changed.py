"""«Por qué ha cambiado» la preparación respecto al día anterior. Solo diferencias observadas; sin causalidad."""
from __future__ import annotations

# (clave, etiqueta, decimales, unidad, umbral mínimo para mencionarlo, sentido favorable: +1 sube=mejor, -1 baja=mejor)
FIELDS = (("hrv_ms", "HRV", 0, " ms", 4, 1), ("resting_hr", "FC en reposo", 0, " lpm", 2, -1),
          ("night_hr", "FC nocturna", 1, " lpm", 3, -1), ("sleep_hours", "Sueño", 1, " h", 0.7, 1),
          ("sleep_score", "Puntuación de sueño", 0, "", 8, 1), ("stress_avg", "Estrés medio", 0, "", 8, -1))


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def compute(trend: list, today: str) -> dict:
    rows = sorted((t for t in trend if isinstance(t, dict) and t.get("date", "") <= today), key=lambda t: t["date"])
    if len(rows) < 2 or rows[-1]["date"] != today:
        return {"available": False}
    cur, prev = rows[-1], rows[-2]
    if cur.get("sleep_context") == "day_sleep" or prev.get("state") == "pending":
        return {"available": False, "reason": "El día anterior no tiene una medición completa."}
    items = []
    for key, label, dec, unit, thr, sign in FIELDS:
        a, b = _num(cur.get(key)), _num(prev.get(key))
        if a is None or b is None or abs(a - b) < thr:
            continue
        items.append({"label": label, "from": b, "to": a, "delta": round(a - b, 2), "dec": dec, "unit": unit,
                      "favorable": (a - b) * sign > 0})
    return {"available": True, "prev_date": prev["date"], "score_from": _num(prev.get("score")),
            "score_to": _num(cur.get("score")), "zone_from": prev.get("zone"), "zone_to": cur.get("zone"), "items": items}


def to_markdown(r: dict) -> str:
    if not r.get("available"):
        return "Cambios respecto a ayer: " + r.get("reason", "sin datos comparables.")
    f = lambda v, d: f"{v:.{d}f}".replace(".", ",")  # noqa: E731
    head = ""
    if r["score_from"] is not None and r["score_to"] is not None:
        head = f"Modelo experimental: {f(r['score_from'], 0)} → {f(r['score_to'], 0)} ({r['zone_from']} → {r['zone_to']}). "
    if not r["items"]:
        return head + "Ningún indicador cambió lo bastante frente a ayer como para destacarlo."
    lines = [f"- {i['label']}: {f(i['from'], i['dec'])} → {f(i['to'], i['dec'])}{i['unit']} "
             f"({'favorable' if i['favorable'] else 'desfavorable'})" for i in r["items"]]
    return head + "Cambios notables frente a ayer:\n\n" + "\n".join(lines) + "\n\nSon diferencias observadas, no causas."
