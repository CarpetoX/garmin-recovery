"""Modelo de disponibilidad v3.

Principios (coherentes con la política fisiológica del repositorio):

* HRV en ln(rMSSD): media móvil de 7 días frente a la línea base personal
  robusta (mediana y MAD, insensible a noches anómalas)
  (hasta 60 días previos a esa semana) con banda de cambio mínimo relevante
  (± 0.5 DE). Una sola noche mala no hunde la puntuación; una tendencia sí.
* Puntuaciones continuas por componente (sin escalones bruscos):
  ``componente = clamp(75 + 12.5 · z, 0, 100)``; z = 0 es tu normalidad.
* Composición ponderada y renormalizada con los componentes disponibles.
* Salvaguardas: sin HRV/sueño/FC reposo de hoy o sueño sin confirmar →
  ``pending`` (nunca autoriza intensidad alta); base < 7 noches → sin
  puntuación; base < 14 → ``provisional`` y nunca verde.
* Es una herramienta de entrenamiento, no un diagnóstico médico.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from . import MODEL_VERSION
from .stats import clamp, cv_pct, mad_sigma, mean, median, r, robust_z

COMPONENT_LABELS = {
    "hrv": "Variabilidad cardiaca (HRV)",
    "cardiac": "FC en reposo y nocturna",
    "sleep": "Sueño",
    "stress": "Estrés del día anterior (Garmin)",
    "load": "Carga de entrenamiento",
    "subjective": "Sensaciones (Intervals)",
}


def _window(daily: dict, end: date, days: int, include_end: bool) -> list[dict]:
    rows = []
    start = end - timedelta(days=days if not include_end else days - 1)
    d = start
    last = end if include_end else end - timedelta(days=1)
    while d <= last:
        row = daily.get(d.isoformat())
        if row:
            rows.append(row)
        d += timedelta(days=1)
    return rows


def _baseline_rows(daily: dict, today: date, cfg: dict) -> list[dict]:
    """Línea base: hasta ``baseline_days`` días ANTERIORES a la ventana móvil.

    Excluir la última semana evita que una mala racha contamine su propia
    referencia (y la haga parecer normal)."""
    window_start = today - timedelta(days=cfg["rolling_days"] - 1)
    return _window(daily, window_start, cfg["baseline_days"], include_end=False)


def _values(rows, field):
    return [row[field] for row in rows if row.get(field) is not None]


def component_score(z: float | None) -> float | None:
    return None if z is None else clamp(75 + 12.5 * z, 0, 100)


def hrv_component(daily: dict, today: date, cfg: dict) -> dict:
    base_rows = _baseline_rows(daily, today, cfg)
    base_ln = [math.log(v) for v in _values(base_rows, "hrv_ms") if v > 0]
    roll_rows = _window(daily, today, cfg["rolling_days"], include_end=True)
    roll_ln = [math.log(v) for v in _values(roll_rows, "hrv_ms") if v > 0]
    current = (daily.get(today.isoformat()) or {}).get("hrv_ms")
    out = {"n_baseline": len(base_ln), "n_rolling": len(roll_ln), "today_ms": current}
    if len(base_ln) < 3 or not current:
        return out | {"z": None}
    # Línea base robusta (mediana/MAD): una noche anómala (p. ej. 20 ms) no ensancha el rango normal.
    m, s = median(base_ln), mad_sigma(base_ln) or 0.0
    swc = cfg["swc_factor"] * s
    ln_today = math.log(current)
    # Una sola noche no puede dominar: su z se acota antes de combinar con la tendencia.
    z_today = clamp((ln_today - m) / s, -4.0, 2.0) if s else 0.0
    roll = mean(roll_ln) if len(roll_ln) >= cfg["min_rolling_n"] else None
    z_roll = (roll - m) / s if roll is not None and s else None
    z = 0.5 * z_today + 0.5 * z_roll if z_roll is not None else z_today
    band = None
    if roll is not None:
        band = "normal" if abs(roll - m) <= swc else ("suprimida" if roll < m else "elevada")
    return out | {
        # Por encima de lo habitual no suma sin límite (posible saturación parasimpática)
        "z": clamp(z, -4.0, 1.5),
        "baseline_ms": r(math.exp(m)), "rolling_ms": r(math.exp(roll)) if roll is not None else None,
        "normal_low_ms": r(math.exp(m - swc)), "normal_high_ms": r(math.exp(m + swc)),
        "today_vs_baseline_pct": r(100 * (current / math.exp(m) - 1)),
        "rolling_vs_baseline_pct": r(100 * (math.exp(roll) / math.exp(m) - 1)) if roll is not None else None,
        "band": band, "cv_7d_pct": r(cv_pct(roll_ln), 2) if len(roll_ln) >= 3 else None,
    }


def cardiac_component(daily: dict, today: date, cfg: dict) -> dict:
    base_rows = _baseline_rows(daily, today, cfg)
    row = daily.get(today.isoformat()) or {}
    rhr, night = row.get("resting_hr"), row.get("night_hr")
    base_rhr, base_night = _values(base_rows, "resting_hr"), _values(base_rows, "night_hr")
    z_rhr = robust_z(rhr, base_rhr) if len(base_rhr) >= cfg["min_baseline_n"] else None
    z_night = robust_z(night, base_night) if len(base_night) >= cfg["min_baseline_n"] else None
    parts = [-z for z in (z_rhr, z_night) if z is not None]
    z = clamp(mean(parts), -4.0, 1.0) if parts else None
    return {
        "z": z, "resting_hr": rhr, "night_hr": night,
        "baseline_resting_hr": r(median(base_rhr)), "baseline_night_hr": r(median(base_night)),
        "resting_delta_bpm": r(rhr - median(base_rhr)) if rhr is not None and base_rhr else None,
        "night_delta_bpm": r(night - median(base_night)) if night is not None and base_night else None,
        "n_baseline": len(base_rhr),
    }


def sleep_component(daily: dict, today: date, cfg: dict) -> dict:
    need = cfg["sleep_need_hours"]
    row = daily.get(today.isoformat()) or {}
    hours, score = row.get("sleep_hours"), row.get("sleep_score")
    nights = _window(daily, today, cfg["sleep_debt_nights"], include_end=True)
    debt = sum(max(0.0, need - n["sleep_hours"]) for n in nights if n.get("sleep_hours") is not None)
    parts = []
    if hours is not None:
        parts.append(clamp(hours - need, -4.0, 0.5))           # −1 por hora por debajo
    if score is not None:
        parts.append(clamp((score - 75) / 12.0, -4.0, 1.0))
    if nights:
        parts.append(clamp(-debt / 2.0, -3.0, 0.0))            # 2 h de deuda = −1
    return {"z": mean(parts) if hours is not None else None, "hours": hours, "sleep_score": score,
            "need_hours": need, "debt_hours": r(debt, 2),
            "debt_nights": len([n for n in nights if n.get("sleep_hours") is not None]),
            "context": row.get("sleep_context")}


def stress_component(daily: dict, today: date, cfg: dict) -> dict:
    """Estrés medio de Garmin del día ANTERIOR (completo) frente a tu línea base.

    El de hoy está incompleto por la mañana; el de ayer sí es comparable."""
    yesterday = today - timedelta(days=1)
    value = (daily.get(yesterday.isoformat()) or {}).get("stress_avg")
    base_rows = _window(daily, yesterday, cfg["baseline_days"], include_end=False)
    base = _values(base_rows, "stress_avg")
    z = robust_z(value, base) if len(base) >= cfg["min_baseline_n"] else None
    return {"z": clamp(-z, -4.0, 1.0) if z is not None else None, "yesterday_avg": value,
            "baseline_median": r(median(base)), "n_baseline": len(base)}


def subjective_component(daily: dict, today: date) -> dict:
    row = daily.get(today.isoformat()) or {}
    fields = ("soreness", "fatigue", "stress_subjective", "mood", "motivation")
    values = {f: row.get(f) for f in fields if row.get(f) is not None}
    m = mean(list(values.values()))
    return {"z": clamp(2.0 - m, -2.0, 1.0) if m is not None else None, "values": values}


ESSENTIAL = ("hrv_ms", "sleep_hours", "resting_hr")


def data_confidence(daily: dict, today: date, missing: list, reasons: list) -> dict:
    """¿Son completos y actuales los DATOS de hoy? (independiente del modelo)."""
    week = [(daily.get((today - timedelta(days=i)).isoformat()) or {}) for i in range(7)]
    coverage = {k: sum(1 for row in week if row.get(k) is not None) for k in ESSENTIAL}
    worst = min(coverage.values())
    unconfirmed = any(r.startswith("sueno_no_confirmado") for r in reasons)
    if missing or unconfirmed:
        level = "baja"
    elif worst >= 6:
        level = "alta"
    elif worst >= 4:
        level = "media"
    else:
        level = "baja"
    why = []
    if missing:
        why.append("faltan datos de hoy: " + ", ".join(missing))
    if unconfirmed:
        why.append("sueño de hoy sin confirmar")
    if worst < 6:
        why.append(f"cobertura 7 días: {worst}/7 noches en la métrica más incompleta")
    return {"level": level, "coverage_7d": coverage, "why": why}


def recommendation_confidence(state: str, n_base: int, n_rolling: int, cfg: dict) -> dict:
    """¿Cuánto fiarse de la RECOMENDACIÓN? Depende del histórico y de la validación del modelo."""
    t = cfg["recommendation_thresholds"]
    why = []
    if state == "pending":
        level = "baja"
        why.append("sin evaluación completa hoy")
    elif n_base >= t["alta_baseline_n"] and n_rolling >= t["alta_rolling_n"]:
        level = "alta"
    elif n_base >= t["media_baseline_n"]:
        level = "media"
        why.append(f"línea base de {n_base} noches (alta desde {t['alta_baseline_n']})")
    else:
        level = "baja"
        why.append(f"línea base de {n_base} noches (mínimo {t['media_baseline_n']} para media)")
    if level == "alta" and not cfg.get("model_validated"):
        level = "media"
        why.append("modelo v3 aún sin validar frente a tu rendimiento real (modo sombra)")
    return {"level": level, "baseline_nights": n_base, "rolling_nights": n_rolling,
            "model_validated": bool(cfg.get("model_validated")), "why": why}


def zone_for(score: float | None, cfg: dict) -> str:
    if score is None:
        return "unavailable"
    if score >= cfg["zones"]["green"]:
        return "green"
    return "yellow" if score >= cfg["zones"]["red"] else "red"


GUIDANCE = {
    "green": {"label": "Listo para entrenar", "rpe_max": 9, "volume": "100 %",
              "text": "Entrena según lo planificado. Intensidad alta permitida si el calentamiento responde bien."},
    "yellow": {"label": "Entrenar con control", "rpe_max": 7, "volume": "70–80 %",
               "text": "Mantén técnica y fuerza submáxima; reduce volumen un 20–30 % y evita series al fallo y WOD máximos."},
    "red": {"label": "Prioriza recuperar", "rpe_max": 4, "volume": "0–50 %",
            "text": "Movilidad, zona 2 suave (30–40 min) o descanso. Sin cargas máximas ni WOD intensos."},
    "unavailable": {"label": "Pendiente de datos", "rpe_max": 6, "volume": "según sensaciones",
                    "text": "Faltan datos de hoy: no se autoriza intensidad alta. Reevaluar tras sincronizar el sueño."},
}


def _drivers(components: dict) -> list[dict]:
    texts = []
    hrv, card, slp, load = (components.get(k) or {} for k in ("hrv", "cardiac", "sleep", "load"))
    if hrv.get("z") is not None:
        pct = hrv.get("rolling_vs_baseline_pct") if hrv.get("rolling_vs_baseline_pct") is not None else hrv.get("today_vs_baseline_pct")
        band = {"normal": "dentro de tu rango normal", "suprimida": "por debajo de tu rango normal",
                "elevada": "por encima de tu rango normal"}.get(hrv.get("band"), "")
        texts.append({"component": "hrv", "z": hrv["z"],
                      "text": f"HRV {hrv['today_ms']:.0f} ms hoy; media 7 días {pct:+.0f} % vs. tu base {band}".strip()})
    if card.get("z") is not None and card.get("resting_delta_bpm") is not None:
        texts.append({"component": "cardiac", "z": card["z"],
                      "text": f"FC en reposo {card['resting_hr']:.0f} lpm ({card['resting_delta_bpm']:+.0f} vs. tu mediana)"})
    if slp.get("z") is not None:
        extra = f", deuda {slp['debt_hours']:.1f} h en {slp['debt_nights']} noches" if slp.get("debt_hours") else ""
        score = f", puntuación {slp['sleep_score']:.0f}" if slp.get("sleep_score") is not None else ""
        texts.append({"component": "sleep", "z": slp["z"],
                      "text": f"Sueño {slp['hours']:.1f} h{score}{extra}"})
    st = components.get("stress") or {}
    if st.get("z") is not None and st.get("yesterday_avg") is not None:
        texts.append({"component": "stress", "z": st["z"],
                      "text": f"Estrés Garmin ayer {st['yesterday_avg']:.0f} de media (tu mediana {st['baseline_median']:.0f})"})
    if load.get("z") is not None:
        texts.append({"component": "load", "z": load["z"],
                      "text": f"Forma {load.get('form_pct'):+.0f} % ({load.get('form_zone')})" if load.get("form_pct") is not None
                      else f"ACWR {load.get('acwr')}"})
    return sorted(texts, key=lambda t: t["z"])


def assess(daily: dict, today_str: str, cfg: dict, load: dict | None = None,
           morning: dict | None = None, apply_morning_gate: bool = True) -> dict:
    today = date.fromisoformat(today_str)
    row = daily.get(today_str) or {}
    components = {
        "hrv": hrv_component(daily, today, cfg),
        "cardiac": cardiac_component(daily, today, cfg),
        "sleep": sleep_component(daily, today, cfg),
        "stress": stress_component(daily, today, cfg),
        "load": (load or {}) | {"z": (load or {}).get("component_z")},
        "subjective": subjective_component(daily, today),
    }
    for name, comp in components.items():
        comp["score"] = r(component_score(comp.get("z")))
        comp["weight"] = cfg["weights"][name]
        comp["label"] = COMPONENT_LABELS[name]

    missing = [k for k in ("hrv_ms", "sleep_hours", "resting_hr") if row.get(k) is None]
    n_base = components["hrv"]["n_baseline"]
    reasons = []
    if missing:
        reasons.append("faltan_datos_hoy:" + ",".join(missing))
    if apply_morning_gate and morning and morning.get("date") == today_str and not morning.get("is_definitive"):
        reasons.append(f"sueno_no_confirmado:{morning.get('state')}")
    if n_base < cfg["min_baseline_n"]:
        reasons.append(f"linea_base_insuficiente:{n_base}<{cfg['min_baseline_n']}")

    available = {k: c for k, c in components.items() if c["score"] is not None}
    score = None
    if not reasons and available:
        total_w = sum(c["weight"] for c in available.values())
        score = sum(c["score"] * c["weight"] for c in available.values()) / total_w

    state = "pending" if reasons else ("provisional" if n_base < cfg.get("provisional_below_n", 14) else "assessed")
    zone = zone_for(score, cfg)
    caps = []
    if state == "provisional" and zone == "green":
        zone, caps = "yellow", caps + ["provisional_nunca_verde"]
    if row.get("sleep_hours") is not None and row["sleep_hours"] < 5 and zone == "green":
        zone, caps = "yellow", caps + ["sueno_menor_5h"]
    hrv = components["hrv"]
    if hrv.get("band") == "suprimida" and (components["cardiac"].get("z") or 0) <= -1.5 and zone == "green":
        zone, caps = "yellow", caps + ["hrv_suprimida_y_fc_alta"]

    data_conf = data_confidence(daily, today, missing, reasons)
    rec_conf = recommendation_confidence(state, n_base, hrv.get("n_rolling", 0), cfg)
    confidence = rec_conf["level"]
    guidance = dict(GUIDANCE[zone])
    notes = []
    if state == "provisional":
        notes.append("Línea base aún corta: interpretación provisional, nunca autoriza verde.")
    shift = row.get("shift")
    prev_shift = (daily.get((today - timedelta(days=1)).isoformat()) or {}).get("shift")
    if shift == "TN":
        notes.append("Hoy turno de noche: si entrenas, que sea antes del turno, corto y sin máximos.")
    if prev_shift == "TN":
        notes.append("Post-turno de noche: prioriza dormir; cualquier sesión, suave.")
    if not components["subjective"]["values"]:
        notes.append("Sin sensaciones registradas hoy: anota fatiga, agujetas, estrés, ánimo y motivación en Intervals.icu para afinar el modelo.")

    return {
        "model_version": MODEL_VERSION, "date": today_str,
        "state": state, "zone": zone, "score": r(score, 0) if score is not None else None,
        "confidence": confidence,
        "data_confidence": data_conf, "recommendation_confidence": rec_conf,
        "reasons": reasons, "safety_caps": caps,
        "guidance": guidance, "notes": notes, "drivers": _drivers(components),
        "components": components, "missing_today": missing,
        "disclaimer": "Herramienta de entrenamiento basada en tendencias personales; no es un diagnóstico médico.",
    }
