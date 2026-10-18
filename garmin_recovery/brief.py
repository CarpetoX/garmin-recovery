"""«En breve»: explicación de hoy en lenguaje llano, por reglas (sin IA) y solo con cifras presentes en los datos.

Devuelve frases con ``**negrita**`` (el panel las convierte en HTML escapado). Sin reloj ni red.
"""
from __future__ import annotations

ZONE_ES = {"green": "verde", "yellow": "ámbar", "red": "roja", "unavailable": "pendiente"}
OFFICIAL = "recovery_assessment_v2"


def _f(v, d=0) -> str:
    return f"{v:.{d}f}".replace(".", ",")


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def official_change(trend: list, today: str):
    rows = sorted((t for t in trend if isinstance(t, dict) and t.get("date", "") <= today), key=lambda t: t["date"])
    if len(rows) < 2 or rows[-1].get("date") != today:
        return None
    a, b = _num(rows[-1].get("v2_score")), _num(rows[-2].get("v2_score"))
    return (b, a) if a is not None and b is not None else None


def compose(result: dict, tonight: dict | None) -> list[str]:
    dec = result.get("decision") or {}
    g = dec.get("guidance") or {}
    zone = dec.get("zone") or "unavailable"
    reg = {m.get("id"): m for m in dec.get("registry") or [] if isinstance(m, dict)}
    score = _num((reg.get(OFFICIAL) or {}).get("score"))
    conf = (result.get("readiness") or {}).get("confidence")
    out: list[str] = []

    head = f"**{g.get('label') or 'Sin decisión'}.**"
    if score is not None:
        head += f" Tu recuperación oficial es {_f(score)}/100 (zona {ZONE_ES.get(zone, zone)}" + (f", confianza {conf}" if conf else "") + ")."
    out.append(head)

    watch = []
    div = dec.get("divergence") or []
    if div:
        watch.append("los modelos no coinciden del todo y se aplica el más prudente")
    drivers = [d for d in (result.get("readiness") or {}).get("drivers") or [] if isinstance(d, dict) and _num(d.get("z")) is not None]
    low = min(drivers, key=lambda d: d["z"], default=None)
    if low and low["z"] <= -0.5:
        watch.append(low["text"][0].lower() + low["text"][1:])
    notes = (result.get("readiness") or {}).get("notes") or []
    if notes:
        watch.append(notes[0][0].lower() + notes[0][1:].rstrip("."))
    if watch:
        out.append("**A tener en cuenta:** " + "; ".join(watch) + ".")

    need = (tonight or {}).get("need") or {}
    h = _num(need.get("need_tonight_h"))
    tip = (tonight or {}).get("tip")
    if tip and notes and (tip.strip().rstrip(".").lower() in notes[0].lower() or notes[0].strip().rstrip(".").lower() in tip.lower()):
        tip = None  # la misma recomendación ya salió en «A tener en cuenta»
    if h is not None or tip:
        t = "**Esta noche:** " + (f"conviene dormir unas {_f(h, 1)} h" if h is not None else "")
        if tip:
            t += ("; " if h is not None else "") + tip[0].lower() + tip[1:].rstrip(".")
        out.append(t.rstrip(".") + ".")
    return out
