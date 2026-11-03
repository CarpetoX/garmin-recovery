"""«Por qué ha cambiado» la preparación respecto al día anterior. Solo diferencias observadas; sin causalidad."""
from __future__ import annotations

# (clave, etiqueta, decimales, unidad, umbral mínimo para mencionarlo, sentido favorable: +1 sube=mejor, -1 baja=mejor)
FIELDS = (("hrv_ms", "HRV", 0, " ms", 4, 1), ("resting_hr", "FC en reposo", 0, " lpm", 2, -1),
          ("night_hr", "FC nocturna", 1, " lpm", 3, -1), ("sleep_hours", "Sueño", 1, " h", 0.7, 1),
          ("sleep_score", "Puntuación de sueño", 0, "", 8, 1), ("stress_avg", "Estrés medio", 0, "", 8, -1))


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


MAX_DAYS = 21  # hasta cuántos días atrás se busca un sueño comparable


def _ddmm(d: str) -> str:
    return f"{d[8:10]}/{d[5:7]}"


def compute(trend: list, today: str) -> dict:
    """V8.10: se compara sueño con sueño del mismo tipo. Tras un turno de noche (sueño de día), con el último sueño de
    día tras turno; una noche normal, con la última noche normal (aunque ayer durmieras de día). Antes, tras un TN el
    bloque desaparecía sin explicación."""
    from datetime import date, timedelta
    rows = sorted((t for t in trend if isinstance(t, dict) and t.get("date", "") <= today), key=lambda t: t["date"])
    if len(rows) < 2 or rows[-1]["date"] != today:
        return {"available": False}
    cur = rows[-1]
    day = cur.get("sleep_context") == "day_sleep"
    lo = (date.fromisoformat(today) - timedelta(days=MAX_DAYS)).isoformat()
    same = [r for r in rows[:-1] if (r.get("sleep_context") == "day_sleep") == day and r.get("state") != "pending"
            and r["date"] >= lo]
    if not same:
        return {"available": False, "day_sleep": day,
                "reason": ("Hoy dormiste de día tras el turno de noche y no hay otro sueño así en las últimas tres semanas "
                           "con el que compararlo." if day else "No hay una noche comparable en las últimas tres semanas.")}
    prev = same[-1]
    if day:
        basis, label = "day_sleep", f"tu último sueño tras turno de noche ({_ddmm(prev['date'])})"
    elif prev["date"] == rows[-2]["date"]:
        basis, label = "yesterday", "ayer"
    else:
        basis, label = "last_night", f"tu última noche comparable ({_ddmm(prev['date'])})"
    items = []
    for key, lab, dec, unit, thr, sign in FIELDS:
        a, b = _num(cur.get(key)), _num(prev.get(key))
        if a is None or b is None or abs(a - b) < thr:
            continue
        items.append({"label": lab, "from": b, "to": a, "delta": round(a - b, 2), "dec": dec, "unit": unit,
                      "favorable": (a - b) * sign > 0})
    return {"available": True, "prev_date": prev["date"], "basis": basis, "compare_label": label, "day_sleep": day,
            "score_from": _num(prev.get("score")), "score_to": _num(cur.get("score")), "zone_from": prev.get("zone"),
            "zone_to": cur.get("zone"), "official_from": _num(prev.get("v2_score")), "official_to": _num(cur.get("v2_score")),
            "items": items}


def heading(r: dict) -> str:
    label = (r or {}).get("compare_label") or "ayer"
    return "Qué ha cambiado desde ayer" if label == "ayer" else f"Qué ha cambiado frente a {label}"


def to_markdown(r: dict) -> str:
    if not r.get("available"):
        return "Cambios respecto a ayer: " + r.get("reason", "sin datos comparables.")
    label = r.get("compare_label") or "ayer"
    lead = ("Hoy dormiste de día tras el turno de noche: se compara con tu último sueño tras turno, no con la noche "
            "anterior. " if r.get("basis") == "day_sleep" else "")
    f = lambda v, d: f"{v:.{d}f}".replace(".", ",")  # noqa: E731
    head = ""
    if r["score_from"] is not None and r["score_to"] is not None:
        head = f"Modelo experimental: {f(r['score_from'], 0)} → {f(r['score_to'], 0)} ({r['zone_from']} → {r['zone_to']}). "
    if not r["items"]:
        return lead + head + f"Ningún indicador cambió lo bastante frente a {label} como para destacarlo."
    lines = [f"- {i['label']}: {f(i['from'], i['dec'])} → {f(i['to'], i['dec'])}{i['unit']} "
             f"({'favorable' if i['favorable'] else 'desfavorable'})" for i in r["items"]]
    return lead + head + f"Cambios notables frente a {label}:\n\n" + "\n".join(lines) + "\n\nSon diferencias observadas, no causas."
