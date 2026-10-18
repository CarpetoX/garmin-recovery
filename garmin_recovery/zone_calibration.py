"""Calibración de la zona del día con tu propio historial.

Para cada zona (verde/amarillo/rojo) mira cómo fue tu HRV de la noche siguiente frente a la mediana
de tu ventana. Solo informa con ≥5 días por zona; no ajusta ningún umbral por sí misma.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, median

from .correlations import WINDOW_DAYS, _num

MIN_DAYS = 5
ZONES = ("green", "yellow", "red")


def compute(rows: list[dict], today: str) -> dict:
    lo = (date.fromisoformat(today) - timedelta(days=WINDOW_DAYS)).isoformat()
    by = {r["date"]: r for r in rows if lo <= r.get("date", "") <= today}
    hrvs = [h for h in (_num(r.get("hrv_ms")) for r in by.values()) if h is not None]
    if len(hrvs) < 10:
        return {"available": False, "reason": "Hacen falta al menos 10 noches con HRV en 90 días."}
    ref = median(hrvs)
    out = {z: [] for z in ZONES}
    for d, r in by.items():
        zone = r.get("decision_zone")
        nxt = by.get((date.fromisoformat(d) + timedelta(days=1)).isoformat())
        h = _num(nxt.get("hrv_ms")) if nxt else None
        if zone in out and h is not None:
            out[zone].append(h - ref)
    zones = {z: {"n": len(v), "ok": len(v) >= MIN_DAYS, "mean_delta_ms": round(mean(v), 1) if len(v) >= MIN_DAYS else None}
             for z, v in out.items()}
    return {"available": True, "ref_hrv_ms": round(ref, 1), "zones": zones}


def to_markdown(r: dict) -> str:
    if not r.get("available"):
        return "Calibración de la zona: " + r.get("reason", "sin datos.")
    names = {"green": "🟢 Verde", "yellow": "🟡 Amarillo", "red": "🔴 Rojo"}
    lines = [f"HRV de la noche siguiente frente a tu mediana de 90 días ({str(r['ref_hrv_ms']).replace('.', ',')} ms):", "",
             "| Zona del día | Días | HRV siguiente noche vs mediana |", "|---|---|---|"]
    for z in ZONES:
        i = r["zones"][z]
        val = (("+" if i["mean_delta_ms"] > 0 else "") + str(i["mean_delta_ms"]).replace(".", ",") + " ms") if i["ok"] \
            else f"datos insuficientes (mín. {MIN_DAYS})"
        lines.append(f"| {names[z]} | {i['n']} | {val} |")
    return "\n".join(lines) + "\n\nSolo descriptivo: sirve para ver si la zona se corresponde con tu recuperación posterior; no cambia umbrales."
