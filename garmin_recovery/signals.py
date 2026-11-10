"""Señales a favor y en contra del día (V8.3). Módulo puro.

Cuando los modelos no coinciden (p. ej. recuperación oficial 88 y Training Readiness de Garmin 39), la app no debe
reducirlo a un semáforo: enseña qué señales son favorables, cuáles restrictivas y por qué la decisión queda donde
queda. Solo usa cifras presentes en los datos; no cambia la puntuación ni la decisión.
"""
from __future__ import annotations

TR_GAP = 30           # diferencia oficial − Training Readiness que se considera discrepancia
RECOVERY_HOURS = 24   # tiempo de recuperación de Garmin que se considera restrictivo
FEEDBACK_ES = {"VERY_GOOD": "muy bueno", "GOOD": "bueno", "MODERATE": "moderado", "POOR": "bajo", "VERY_POOR": "muy bajo"}
FAVORABLE = {"VERY_GOOD", "GOOD"}
TR_LEVEL_ES = {"PRIME": "óptimo", "HIGH": "alto", "MODERATE": "moderado", "LOW": "bajo", "POOR": "muy bajo"}


def _n(v, d=0):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return "—"
    s = f"{v:.{d}f}" if d else f"{round(v):d}"
    return s.replace(".", ",")


def compute(result: dict, garmin_day: dict | None) -> dict:
    dec = (result or {}).get("decision") or {}
    reg = {m.get("id"): m for m in dec.get("registry") or [] if isinstance(m, dict)}
    official = (reg.get("recovery_assessment_v2") or {}).get("score")
    hybrid = (reg.get("readiness_hybrid") or {}).get("score")
    g = garmin_day if isinstance(garmin_day, dict) else {}
    tr = g.get("training_readiness") if isinstance(g.get("training_readiness"), dict) else {}
    hs = g.get("hrv_status") if isinstance(g.get("hrv_status"), dict) else {}
    sd = g.get("sleep_detail") if isinstance(g.get("sleep_detail"), dict) else {}
    tr_score = tr.get("score")
    fav, res = [], []

    # Garmin Training Readiness y sus factores
    factors = [("sleep", "Sueño según Garmin", "sleep_factor_feedback", "sleep_factor_percent"),
               ("acwr", "Carga aguda/crónica de Garmin", "acwr_factor_feedback", "acwr_factor_percent"),
               ("hrv", "HRV según Garmin", "hrv_factor_feedback", "hrv_factor_percent"),
               ("recovery", "Tiempo de recuperación de Garmin", "recovery_time_feedback", "recovery_time_factor_percent"),
               ("stress", "Estrés de los últimos días", "stress_history_factor_feedback", "stress_history_factor_percent")]
    for key, label, fb_key, pct_key in factors:
        fb = tr.get(fb_key)
        if not fb:
            continue
        txt = f"{label}: {FEEDBACK_ES.get(fb, str(fb).lower())} ({_n(tr.get(pct_key))} %)"
        if key == "recovery" and isinstance(tr.get("recovery_time_hours"), (int, float)):
            txt += f", {_n(tr['recovery_time_hours'])} h pendientes"
        (fav if fb in FAVORABLE else res).append(txt)

    # Estado de HRV de Garmin: noche frente a rango y media semanal
    base = hs.get("baseline") if isinstance(hs.get("baseline"), dict) else {}
    lo, hi = base.get("balanced_low"), base.get("balanced_upper")
    night, week = hs.get("last_night_avg"), hs.get("weekly_avg")
    if isinstance(night, (int, float)) and isinstance(lo, (int, float)) and isinstance(hi, (int, float)):
        if night > hi:
            fav.append(f"HRV de anoche {_n(night)} ms, por encima de tu rango equilibrado ({_n(lo)}–{_n(hi)})")
        elif night < lo:
            res.append(f"HRV de anoche {_n(night)} ms, por debajo de tu rango equilibrado ({_n(lo)}–{_n(hi)})")
        else:
            fav.append(f"HRV de anoche {_n(night)} ms, dentro de tu rango ({_n(lo)}–{_n(hi)})")
    if isinstance(week, (int, float)) and isinstance(lo, (int, float)) and week < lo:
        res.append(f"Media de HRV de 7 días {_n(week)} ms, por debajo de tu rango ({_n(lo)}–{_n(hi)}): "
                   "Garmin la marca como «desequilibrada»")

    if isinstance(sd.get("sleep_hours"), (int, float)):
        h = sd["sleep_hours"]
        txt = f"Sueño de anoche {int(h)} h {round((h - int(h)) * 60):02d} min"
        (fav if h >= 7 else res).append(txt)

    gap = (official - tr_score) if isinstance(official, (int, float)) and isinstance(tr_score, (int, float)) else None
    rec_h = tr.get("recovery_time_hours")
    show = bool((gap is not None and abs(gap) >= TR_GAP) or hs.get("status") == "UNBALANCED"
                or (isinstance(rec_h, (int, float)) and rec_h >= RECOVERY_HOURS and dec.get("zone") == "green"))
    why = None
    if gap is not None and abs(gap) >= TR_GAP:
        why = (f"La recuperación oficial ({_n(official)}) mira sobre todo cómo has dormido y tu HRV y FC de anoche frente a tu "
               f"normalidad; el Training Readiness de Garmin ({_n(tr_score)}, {TR_LEVEL_ES.get(tr.get('level'), 'sin nivel')}) "
               "pesa además el tiempo de recuperación pendiente y la HRV de la semana. Garmin solo es contexto: no entra en la "
               "decisión, que sale del más prudente de los modelos oficial, híbrido y experimental.")
    return {"show": show, "official": official, "hybrid": hybrid, "garmin": tr_score,
            "garmin_level": TR_LEVEL_ES.get(tr.get("level")), "zone": dec.get("zone"),
            "favorable": fav, "restrictive": res, "why": why,
            "advice": ("Señales mezcladas: aunque la decisión permita intensidad, sube la carga solo si el calentamiento "
                       "responde bien y para si notas las piernas pesadas o la FC más alta de lo normal.")
            if show and res and dec.get("zone") == "green" else None}
