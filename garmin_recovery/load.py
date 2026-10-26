"""Carga de entrenamiento: ATL/CTL/TSB, monotonía, strain y ACWR.

Prioridad de fuente para fitness/fatiga: Intervals.icu (calcula sobre todo el
historial del atleta) y, si falta, EWMA propia sobre ``history/sessions.csv``.
La "forma" (TSB relativo a CTL) solo se interpreta con CTL suficiente: con
CTL muy baja cualquier sesión produce porcentajes extremos sin significado.
"""
from __future__ import annotations

from datetime import date, timedelta

from .stats import clamp, ewma, mean, r, sd


def _series(daily: dict, start: date, end: date, field: str) -> list[float]:
    out, d = [], start
    while d <= end:
        out.append((daily.get(d.isoformat()) or {}).get(field) or 0.0)
        d += timedelta(days=1)
    return out


def form_zone(form_pct: float | None) -> str | None:
    """Zonas de forma de Intervals.icu (TSB/CTL en %)."""
    if form_pct is None:
        return None
    if form_pct > 20:
        return "transicion"
    if form_pct > 5:
        return "fresco"
    if form_pct >= -10:
        return "neutro"
    if form_pct >= -30:
        return "optimo"
    return "riesgo_alto"


def compute_load(daily: dict, sessions: dict, today: str, cfg: dict) -> dict:
    end = date.fromisoformat(today)
    session_dates = sorted(s["date"] for s in sessions.values() if s.get("date"))
    coverage_start = date.fromisoformat(session_dates[0]) if session_dates else end
    coverage_days = (end - coverage_start).days + 1

    loads = _series(daily, coverage_start, end, "load")

    def seeded(series, days):
        if not series:
            return None
        head = series[:days]
        return ewma(series, days, seed=sum(head) / len(head))[-1]
    own_atl = seeded(loads, cfg["atl_days"])
    own_ctl = seeded(loads, cfg["ctl_days"])

    row = daily.get(today) or {}
    prev = daily.get((end - timedelta(days=1)).isoformat()) or {}
    icu_ctl = row.get("icu_ctl") if row.get("icu_ctl") is not None else prev.get("icu_ctl")
    icu_atl = row.get("icu_atl") if row.get("icu_atl") is not None else prev.get("icu_atl")
    if icu_ctl is not None and icu_atl is not None:
        ctl, atl, source = icu_ctl, icu_atl, "intervals_icu"
    elif coverage_days >= cfg["ctl_days"]:
        ctl, atl, source = own_ctl, own_atl, "historial_propio"
    else:
        ctl, atl, source = own_ctl, own_atl, "historial_propio_corto"
    tsb = ctl - atl if ctl is not None and atl is not None else None
    form_valid = ctl is not None and ctl >= cfg["min_ctl_for_form"] and source != "historial_propio_corto"
    form_pct = 100 * tsb / ctl if form_valid and tsb is not None and ctl else None

    last7 = _series(daily, end - timedelta(days=6), end, "load")
    prev7 = _series(daily, end - timedelta(days=13), end - timedelta(days=7), "load")
    srpe7 = _series(daily, end - timedelta(days=6), end, "srpe")
    srpe28 = _series(daily, end - timedelta(days=27), end, "srpe")
    # Carga interna (sRPE de Foster) para monotonía, strain y ACWR: la carga de FC de
    # Intervals infravalora la fuerza (p. ej. 10×2 pesado a RPE 9 = carga 4, sRPE 138).
    # Un día con sesiones sin RPE cuenta como sRPE 0: solo se calcula con cobertura de RPE suficiente.
    def rpe_coverage(days):
        start = (end - timedelta(days=days - 1)).isoformat()
        win = [s_ for s_ in sessions.values() if start <= (s_.get("date") or "") <= today and not s_.get("rpe_na")]
        known = sum(1 for s_ in win if s_.get("rpe") is not None)
        return 100.0 * known / len(win) if win else None
    min_cov = cfg.get("min_srpe_coverage_pct", 75)
    srpe_cov, srpe_cov28 = rpe_coverage(7), rpe_coverage(28)
    m7, s7 = mean(srpe7), sd(srpe7)
    monotony = (m7 / s7 if any(srpe7) and s7 and s7 > 0 and srpe_cov is not None and srpe_cov >= min_cov
                else None)
    week_load = sum(last7)
    prev_week = sum(prev7) if coverage_days >= 14 else None
    change_pct = 100 * (week_load - prev_week) / prev_week if prev_week else None

    # ACWR por medias móviles 7/28 días de sRPE: sin sesgo de arranque y solo con 28 días de historial.
    acwr = None
    rpe_dates = sorted(s_["date"] for s_ in sessions.values() if s_.get("date") and s_.get("rpe") is not None)
    rpe_days = (end - date.fromisoformat(rpe_dates[0])).days + 1 if rpe_dates else 0
    chronic = sum(srpe28) / 28 if srpe28 else 0
    if (rpe_days >= cfg["min_load_coverage_days"] and chronic > 0
            and srpe_cov28 is not None and srpe_cov28 >= min_cov):
        acwr = (sum(srpe7) / 7) / chronic

    # Componente de readiness: solo con forma interpretable o ACWR propio.
    z = None
    basis = None
    if form_pct is not None:
        z = clamp(form_pct / 15.0, -3.0, 1.0)
        basis = "forma_tsb"
    elif acwr is not None:
        z = clamp(-(acwr - 1.0) * 3.0, -3.0, 1.0)
        basis = "acwr"

    days_since_rest = 0
    d = end
    while (daily.get(d.isoformat()) or {}).get("load") and days_since_rest < 60:
        days_since_rest += 1
        d -= timedelta(days=1)

    return {
        "source": source, "coverage_days": coverage_days,
        "ctl": r(ctl), "atl": r(atl), "tsb": r(tsb),
        "form_pct": r(form_pct), "form_zone": form_zone(form_pct),
        "form_interpretable": form_pct is not None,
        "week_load": r(week_load), "prev_week_load": r(prev_week),
        "week_change_pct": r(change_pct),
        "week_srpe": r(sum(srpe7)) if any(srpe7) else None,
        "week_sessions": sum(int((daily.get((end - timedelta(days=i)).isoformat()) or {}).get("sessions") or 0) for i in range(7)),
        "monotony": r(monotony, 2), "strain": r(sum(srpe7) * monotony) if monotony else None,
        "internal_load_basis": "srpe_foster", "srpe_coverage_7d_pct": r(srpe_cov, 0), "srpe_coverage_28d_pct": r(srpe_cov28, 0),
        "acwr": r(acwr, 2), "acwr_basis": "srpe_media_7_vs_28",
        "consecutive_training_days": days_since_rest,
        "component_z": r(z, 2), "component_basis": basis,
        "notes": ([] if form_pct is not None else
                  [f"CTL {r(ctl)} < {cfg['min_ctl_for_form']}: la forma (TSB %) no se interpreta todavía; "
                   "la carga no penaliza la puntuación hasta tener carga crónica suficiente."]),
    }
