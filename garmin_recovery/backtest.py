"""Validación prospectiva de los modelos (v2 oficial, híbrido, v3 y decisión).

Pregunta: ¿la puntuación de la mañana anticipa cómo te sienta el entrenamiento ese día?

* **Predicción** (``history/model_predictions.csv``): la puntuación y zona de cada modelo
  *antes* de la primera sesión del día. Se actualiza mientras no hayas entrenado (p. ej.
  cuando se confirma el sueño) y se congela en cuanto aparece una sesión. Nunca se
  reconstruye hacia atrás: solo cuenta lo que el modelo dijo de verdad en su momento.
* **Resultado principal: esfuerzo percibido relativo.** Para cada sesión con RPE y carga de
  FC: ln(sRPE / carga), estandarizado dentro de su tipo de sesión (WOD, fuerza…) con tu
  propio historial (mediana/MAD). Si el mismo trabajo cardiaco te cuesta más de lo
  habitual, el valor es positivo. Un modelo útil tiene correlación **negativa** con él.
* **Resultado secundario:** sensaciones de la mañana siguiente en Intervals (1 = mejor,
  4 = peor), solo si las registras.
* **Adherencia:** días entrenados por encima del RPE máximo de la decisión.

La correlación es la de Spearman con intervalo al 90 % (aproximación de Fisher). No se
emite veredicto hasta tener ``min_validation_days`` días con entrenamiento y RPE, y la
promoción del v3 sigue siendo manual (``model_validated`` en la configuración).
"""
from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path

from .stats import mad_sigma, median

PRED_FIELDS = ["date", "recorded_at", "slot", "frozen", "after_training", "decision_zone", "rpe_cap",
               "v2_score", "v2_zone", "hybrid_score", "hybrid_zone", "v3_score", "v3_zone", "v3_state"]
MODELS = [("recovery_assessment_v2", "v2", "Oficial v2"), ("readiness_hybrid", "hybrid", "Híbrido"),
          ("readiness_v3", "v3", "v3 (en pruebas)")]
ZONE_SCORE = {"red": 0, "unavailable": 1, "yellow": 2, "green": 3}


# ------------------------------------------------------------------ predicciones
def read_predictions(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["date"]: r for r in csv.DictReader(fh) if r.get("date")}


def write_predictions(path: Path, rows: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PRED_FIELDS, lineterminator="\n")
        w.writeheader()
        for d in sorted(rows):
            w.writerow({k: ("" if rows[d].get(k) is None else rows[d].get(k)) for k in PRED_FIELDS})
    tmp.replace(path)


def prediction_row(result: dict, slot: str, trained: bool) -> dict:
    dec = result.get("decision") or {}
    reg = {m["id"]: m for m in dec.get("registry") or []}
    row = {"date": result.get("date"), "recorded_at": result.get("generated_at"), "slot": slot,
           "frozen": 1 if trained else 0, "after_training": 1 if trained else 0,
           "decision_zone": dec.get("zone"), "rpe_cap": (dec.get("guidance") or {}).get("rpe_max"),
           "v3_state": (result.get("readiness") or {}).get("state")}
    for mid, key, _ in MODELS:
        m = reg.get(mid) or {}
        row[f"{key}_score"] = m.get("score")
        row[f"{key}_zone"] = m.get("zone")
    return row


def record_prediction(rows: dict, result: dict, slot: str) -> dict:
    """Añade o actualiza la predicción de hoy; nunca toca una predicción congelada."""
    today = result.get("date")
    trained = any(s.get("date") == today for s in result.get("sessions_28d") or [])
    current = rows.get(today)
    if current is None:
        rows[today] = prediction_row(result, slot, trained)
    elif str(current.get("frozen")) != "1":
        if trained:
            current["frozen"] = 1  # conserva la última predicción previa al entrenamiento
        else:
            rows[today] = prediction_row(result, slot, False)
    return rows


# ------------------------------------------------------------------ resultados
def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def effort_by_day(sessions: dict, categorize) -> dict:
    """Media diaria del esfuerzo relativo z = ln(sRPE/carga) estandarizado por tipo de sesión."""
    raw = []
    for s in sessions.values():
        srpe, load = _f(s.get("srpe")), _f(s.get("load"))
        if s.get("removed") or not s.get("date") or not srpe or not load or srpe <= 0 or load <= 0:
            continue
        raw.append((s["date"], categorize(s), math.log(srpe / load)))
    by_cat: dict = {}
    for _, cat, v in raw:
        by_cat.setdefault(cat, []).append(v)
    days: dict = {}
    for d, cat, v in raw:
        ref = by_cat[cat]
        if len(ref) < 5:
            continue  # sin referencia suficiente para ese tipo de sesión
        sigma = mad_sigma(ref)
        if not sigma:
            continue
        days.setdefault(d, []).append((v - median(ref)) / sigma)
    return {d: sum(z) / len(z) for d, z in days.items()}


def max_rpe_by_day(sessions: dict) -> dict:
    out: dict = {}
    for s in sessions.values():
        rpe = _f(s.get("rpe"))
        if s.get("removed") or rpe is None or not s.get("date"):
            continue
        out[s["date"]] = max(out.get(s["date"], 0), rpe)
    return out


def next_morning_feel(daily: dict, d: str):
    nxt = daily.get((date.fromisoformat(d) + timedelta(days=1)).isoformat()) or {}
    vals = [_f(nxt.get(k)) for k in ("fatigue", "soreness", "mood", "motivation")]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


# ------------------------------------------------------------------ estadística
def _ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(pairs):
    """ρ de Spearman con IC 90 % (Fisher). None si n < 5 o sin variación."""
    n = len(pairs)
    if n < 5:
        return None
    rx, ry = _ranks([p[0] for p in pairs]), _ranks([p[1] for p in pairs])
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if not sxx or not syy:
        return None
    rho = max(-0.999999, min(0.999999, sxy / math.sqrt(sxx * syy)))
    se = 1 / math.sqrt(n - 3) if n > 3 else float("inf")
    z = math.atanh(rho)
    lo, hi = math.tanh(z - 1.645 * se), math.tanh(z + 1.645 * se)
    return {"rho": round(rho, 2), "ci90": [round(lo, 2), round(hi, 2)], "n": n}


# ------------------------------------------------------------------ evaluación
def evaluate(predictions: dict, daily: dict, sessions: dict, today: str, cfg: dict, categorize) -> dict:
    need = cfg.get("min_validation_days", 20)
    effort = effort_by_day(sessions, categorize)
    max_rpe = max_rpe_by_day(sessions)
    usable = {d: p for d, p in predictions.items()
              if d <= today and str(p.get("after_training")) != "1"}
    models = []
    for _, key, label in MODELS + [("decision", "decision", "Decisión operativa")]:
        if key == "decision":
            score = lambda p: ZONE_SCORE.get(p.get("decision_zone"))
        else:
            score = lambda p, k=key: _f(p.get(f"{k}_score"))
        eff = [(score(p), effort[d]) for d, p in usable.items() if score(p) is not None and d in effort]
        feel = [(score(p), next_morning_feel(daily, d)) for d, p in usable.items()
                if d < today and score(p) is not None and next_morning_feel(daily, d) is not None]
        by_zone: dict = {}
        zkey = "decision_zone" if key == "decision" else f"{key}_zone"
        for d, p in usable.items():
            if d in effort and p.get(zkey):
                by_zone.setdefault(p[zkey], []).append(effort[d])
        models.append({"id": key, "label": label, "effort": spearman(eff), "next_feel": spearman(feel),
                       "n_effort": len(eff), "n_feel": len(feel),
                       "effort_by_zone": {z: {"n": len(v), "mean_z": round(sum(v) / len(v), 2)}
                                          for z, v in sorted(by_zone.items())}})
    trained_days = [d for d in usable if d in max_rpe]
    exceeded = [d for d in trained_days
                if _f(usable[d].get("rpe_cap")) is not None and max_rpe[d] > _f(usable[d]["rpe_cap"])]
    n_eff = max((m["n_effort"] for m in models), default=0)
    v2 = next(m for m in models if m["id"] == "v2")
    v3 = next(m for m in models if m["id"] == "v3")
    if n_eff < need:
        status, verdict = "acumulando", (f"Acumulando datos: {n_eff}/{need} días con entrenamiento, RPE y "
                                          "predicción de la mañana. Aún no hay veredicto.")
    else:
        e2, e3 = v2["effort"], v3["effort"]
        useful3 = e3 is not None and e3["ci90"][1] < 0
        better = useful3 and (e2 is None or e3["rho"] <= e2["rho"] - 0.10)
        if better:
            status, verdict = "v3_mejor", ("El v3 anticipa mejor que el v2 el esfuerzo relativo. Puede "
                                           "valorarse promoverlo (model_validated: true).")
        elif useful3:
            status, verdict = "v3_util", "El v3 es útil, pero no claramente mejor que el v2: se mantiene el v2."
        else:
            status, verdict = "v3_no_probado", "El v3 todavía no muestra relación clara con el esfuerzo: se mantiene el v2."
    return {
        "method": "spearman_ic90_fisher", "outcome": "esfuerzo_relativo_ln_srpe_por_carga_z_por_tipo",
        "expected_sign": "negativo", "min_days": need, "status": status, "verdict": verdict,
        "predictions": len(predictions), "first_prediction": min(predictions) if predictions else None,
        "training_days": len(trained_days), "days_over_cap": len(exceeded), "models": models,
    }


def update(root: Path, result: dict, slot: str, daily: dict, sessions: dict, cfg: dict, write: bool) -> dict:
    from .report import categorize
    path = Path(root) / cfg["history_dir"] / "model_predictions.csv"
    rows = record_prediction(read_predictions(path), result, slot)
    if write:
        write_predictions(path, rows)
    return evaluate(rows, daily, sessions, result["date"], cfg, categorize)
