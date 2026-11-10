"""Datos de Garmin que ya se descargan y no se mostraban (V8.1). Módulo puro: solo lee ``garmin_extended.json``.

* **Respiración nocturna** (resp/min): valor de anoche frente a la mediana de los días anteriores. Una subida de
  ≥ 2 resp/min sobre tu normal se marca; si coincide con HRV baja, se señala como aviso combinado. Informativo:
  no cambia la puntuación ni la decisión.
* **Equilibrio de carga de 4 semanas** (Garmin): aeróbica baja, aeróbica alta y anaeróbica con sus bandas objetivo.
* **VO2max** (estimación de Garmin) y su tendencia.
* **Efecto de entrenamiento** aeróbico y anaeróbico de cada sesión, enlazado con Intervals por el ID externo de
  Garmin (``external_id``) y, si falta, por la hora de inicio.
"""
from __future__ import annotations

from datetime import date, timedelta

RESP_DELTA = 2.0      # resp/min sobre la mediana para marcar «alta»
RESP_MIN_BASE = 7     # noches mínimas para tener referencia
HRV_LOW_PCT = -15     # HRV de hoy un 15 % por debajo de su mediana = «baja»

LOAD_KEYS = {"aerobic_low": "monthlyLoadAerobicLow", "aerobic_high": "monthlyLoadAerobicHigh",
             "anaerobic": "monthlyLoadAnaerobic"}
FEEDBACK_ES = {
    "BALANCED": "equilibrada", "AEROBIC_LOW_SHORTAGE": "falta aeróbica baja", "AEROBIC_HIGH_SHORTAGE": "falta aeróbica alta",
    "ANAEROBIC_SHORTAGE": "falta anaeróbica", "AEROBIC_LOW_FOCUS": "centrada en aeróbica baja",
    "AEROBIC_HIGH_FOCUS": "centrada en aeróbica alta", "ANAEROBIC_FOCUS": "centrada en anaeróbica", "NO_DATA": "sin datos",
}
TE_LABEL_ES = {"RECOVERY": "recuperación", "BASE": "base aeróbica", "TEMPO": "tempo", "THRESHOLD": "umbral",
               "VO2MAX": "VO2max", "ANAEROBIC_CAPACITY": "capacidad anaeróbica", "SPRINT": "esprint",
               "LACTATE_THRESHOLD": "umbral", "NO_BENEFIT": "sin beneficio"}


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _get(d, *path):
    for p in path:
        d = d.get(p) if isinstance(d, dict) else None
    return d


def _suffix(flat: dict, key: str):
    """Los campos de Garmin llevan el ID del reloj en la ruta (``…DTOMap.<id>.monthlyLoadAnaerobic``)."""
    for k, v in (flat or {}).items():
        if k.endswith("." + key) or k == key:
            return v
    return None


def respiration(days: dict, today: str, hrv_today=None, hrv_median=None) -> dict:
    series = [{"date": k, "value": _num(_get(days[k], "sleep_detail", "avg_respiration"))} for k in sorted(days)]
    series = [p for p in series if p["value"] is not None and p["date"] <= today][-28:]
    if not series:
        return {"available": False}
    last = series[-1]
    base = [p["value"] for p in series if p["date"] < last["date"]]
    med = _median(base) if len(base) >= RESP_MIN_BASE else None
    delta = round(last["value"] - med, 1) if med is not None else None
    high = delta is not None and delta >= RESP_DELTA
    hrv_pct = (100 * (hrv_today - hrv_median) / hrv_median) if hrv_today and hrv_median else None
    hrv_low = hrv_pct is not None and hrv_pct <= HRV_LOW_PCT
    state = "alta_y_hrv_baja" if high and hrv_low else "alta" if high else "normal" if med is not None else "sin_referencia"
    return {"available": True, "date": last["date"], "value": last["value"], "median": med, "delta": delta,
            "n_base": len(base), "state": state, "is_today": last["date"] == today,
            "hrv_pct": round(hrv_pct) if hrv_pct is not None else None,
            "lowest": _num(_get(days[last["date"]], "sleep_detail", "lowest_respiration")),
            "highest": _num(_get(days[last["date"]], "sleep_detail", "highest_respiration")),
            "series": series}


def load_balance(days: dict, today: str) -> dict:
    for k in sorted((d for d in days if d <= today), reverse=True):
        ts = days[k].get("training_status") or {}
        vals = {n: _num(_suffix(ts, key)) for n, key in LOAD_KEYS.items()}
        if all(v is not None for v in vals.values()):
            out = {"available": True, "date": k, "parts": []}
            for n, key in LOAD_KEYS.items():
                lo, hi = _num(_suffix(ts, key + "TargetMin")), _num(_suffix(ts, key + "TargetMax"))
                v = vals[n]
                state = None if lo is None or hi is None else "bajo" if v < lo else "alto" if v > hi else "en rango"
                out["parts"].append({"id": n, "value": round(v), "target_min": lo, "target_max": hi, "state": state,
                                     "near_top": bool(hi and state == "en rango" and v >= 0.9 * hi)})
            fb = _suffix(ts, "trainingBalanceFeedbackPhrase")
            out["feedback"] = FEEDBACK_ES.get(str(fb), str(fb).replace("_", " ").lower() if fb else None)
            return out
    return {"available": False}


def vo2max(days: dict, today: str) -> dict:
    series = []
    for k in sorted(d for d in days if d <= today):
        v = _num(_suffix(days[k].get("training_status") or {}, "vo2MaxPreciseValue"))
        if v is not None:
            series.append({"date": k, "value": round(v, 1)})
    if not series:
        return {"available": False}
    first, last = series[0], series[-1]
    return {"available": True, "value": last["value"], "date": last["date"], "since": first["date"],
            "change": round(last["value"] - first["value"], 1), "series": series}


def training_effect(days: dict, activities: list) -> dict:
    """``{id Intervals: {aerobic, anaerobic, label}}``."""
    by_garmin, by_start = {}, {}
    for k in days:
        for a in _get(days[k], "activity_metrics", "activities") or []:
            if not isinstance(a, dict):
                continue
            te = {"aerobic": _num(a.get("aerobic_training_effect")), "anaerobic": _num(a.get("anaerobic_training_effect")),
                  "label": TE_LABEL_ES.get(str(a.get("training_effect_label")), None)}
            if te["aerobic"] is None and te["anaerobic"] is None:
                continue
            te = {k2: (round(v, 1) if isinstance(v, float) else v) for k2, v in te.items()}
            if a.get("activity_id") is not None:
                by_garmin[str(a["activity_id"])] = te
            if a.get("start_time_local"):
                by_start[str(a["start_time_local"]).replace(" ", "T")[:16]] = te
    out = {}
    for act in activities or []:
        if not isinstance(act, dict) or not act.get("id"):
            continue
        te = by_garmin.get(str(act.get("external_id") or "")) or by_start.get(str(act.get("start_date_local") or "")[:16])
        if te:
            out[str(act["id"])] = te
    return out


def build(extended: dict | None, activities: list | None, today: str, trend: list | None = None) -> dict:
    days = (extended or {}).get("days") or {}
    if not isinstance(days, dict) or not today:
        return {"available": False}
    hrv = [t.get("hrv_ms") for t in (trend or []) if isinstance(t, dict) and t.get("date", "") < today and _num(t.get("hrv_ms"))]
    hrv_today = next((_num(t.get("hrv_ms")) for t in (trend or []) if isinstance(t, dict) and t.get("date") == today), None)
    cut = (date.fromisoformat(today) - timedelta(days=28)).isoformat()
    hrv_med = _median([h for t, h in ((t, t.get("hrv_ms")) for t in (trend or []) if isinstance(t, dict))
                       if h and cut <= t.get("date", "") < today]) if hrv else None
    return {"available": True, "respiration": respiration(days, today, hrv_today, hrv_med),
            "load_balance": load_balance(days, today), "vo2max": vo2max(days, today),
            "training_effect": training_effect(days, activities or [])}
