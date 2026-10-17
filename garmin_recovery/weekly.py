"""Resumen semanal (``app/informe_semanal.md``): los últimos 7 días frente a los 7 anteriores.

Se regenera en cada ciclo con la semana móvil que termina hoy; el del domingo por la noche
es el cierre de la semana. Usa solo ``readiness_v3.json`` (tendencia, sesiones, carga y
validación) y las series de fuerza de ``crossfit_insights.json``; no inventa datos: lo que
falta se muestra como «—» o como cobertura incompleta.
"""
from __future__ import annotations

from datetime import date, timedelta

from .readiness import GUIDANCE

ZONE_ES = {"green": "verde", "yellow": "ámbar", "red": "rojo", "unavailable": "pendiente"}


def _f(v, digits=1, unit=""):
    if v is None:
        return "—"
    txt = f"{v:.{digits}f}".replace(".", ",") if digits else f"{round(v):d}"
    return txt + unit


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _delta(cur, prev, digits=1, unit=""):
    if cur is None or prev is None:
        return ""
    d = cur - prev
    return f" ({'+' if d >= 0 else '−'}{_f(abs(d), digits)}{unit} vs. semana previa)"


def _window(rows, end: date, days: int, offset: int = 0):
    lo = (end - timedelta(days=offset + days - 1)).isoformat()
    hi = (end - timedelta(days=offset)).isoformat()
    return [r for r in rows if lo <= (r.get("date") or "") <= hi]


def weekly_summary(result: dict, strength: list | None = None) -> dict:
    today = date.fromisoformat(result["date"])
    trend = result.get("trend_28d") or []
    sessions = [s for s in result.get("sessions_28d") or [] if not s.get("removed")]
    cur, prev = _window(trend, today, 7), _window(trend, today, 7, 7)
    s_cur, s_prev = _window(sessions, today, 7), _window(sessions, today, 7, 7)
    need = (((result.get("readiness") or {}).get("components") or {}).get("sleep") or {}).get("need_hours") or 7.5

    zones = {}
    for r in cur:
        z = r.get("decision_zone")
        if z:
            zones[z] = zones.get(z, 0) + 1
    over, checked = [], 0
    for r in cur:
        z = r.get("decision_zone")
        cap = (GUIDANCE.get(z) or {}).get("rpe_max") if z else None
        rpes = [s.get("rpe") for s in s_cur if s.get("date") == r["date"] and s.get("rpe") is not None]
        if cap is not None and rpes:
            checked += 1
        if cap is not None and rpes and max(rpes) > cap:
            over.append({"date": r["date"], "rpe": max(rpes), "cap": cap})

    def load_sum(rows, key):
        vals = [s.get(key) for s in rows if s.get(key) is not None]
        return sum(vals) if vals else None

    week = {
        "start": (today - timedelta(days=6)).isoformat(), "end": today.isoformat(),
        "zones": zones, "days_with_decision": sum(zones.values()), "over_cap": over, "cap_checked_days": checked,
        "trained_days": len({s.get("date") for s in s_cur}),
        "sessions": len(s_cur), "sessions_prev": len(s_prev),
        "minutes": load_sum(s_cur, "duration_min"), "minutes_prev": load_sum(s_prev, "duration_min"),
        "load": load_sum(s_cur, "load"), "load_prev": load_sum(s_prev, "load"),
        "srpe": load_sum(s_cur, "srpe"), "srpe_prev": load_sum(s_prev, "srpe"),
        "rpe_coverage": (sum(1 for s in s_cur if s.get("rpe") is not None), len(s_cur)),
        "hrv": _mean([r.get("hrv_ms") for r in cur]), "hrv_prev": _mean([r.get("hrv_ms") for r in prev]),
        "hrv_rolling_end": (cur[-1].get("hrv_rolling_ms") if cur else None),
        "hrv_range": ((cur[-1].get("hrv_low_ms"), cur[-1].get("hrv_high_ms")) if cur else (None, None)),
        "rhr": _mean([r.get("resting_hr") for r in cur]), "rhr_prev": _mean([r.get("resting_hr") for r in prev]),
        "sleep": _mean([r.get("sleep_hours") for r in cur]), "sleep_prev": _mean([r.get("sleep_hours") for r in prev]),
        "short_nights": sum(1 for r in cur if r.get("sleep_hours") is not None and r["sleep_hours"] < need),
        "need": need,
        "nights_hrv": sum(1 for r in cur if r.get("hrv_ms") is not None),
        "nights_sleep": sum(1 for r in cur if r.get("sleep_hours") is not None),
        "shifts": [r.get("shift") for r in cur if r.get("shift")],
        "strength": sorted((x for x in strength or [] if x.get("date") and week_start(today) <= x["date"] <= today.isoformat()
                            and x.get("peak_declared_load_kg")), key=lambda x: x["date"]),
        "load_state": result.get("load") or {},
        "validation": (result.get("model_validation") or {}).get("verdict"),
    }
    return week


def week_start(today: date) -> str:
    return (today - timedelta(days=6)).isoformat()


def build_weekly(result: dict, strength: list | None = None, report_id: str | None = None) -> str:
    w = weekly_summary(result, strength)
    d = lambda s: f"{s[8:10]}/{s[5:7]}"  # noqa: E731
    load = w["load_state"]
    z = w["zones"]
    zones_txt = " · ".join(f"{ZONE_ES[k]} {z[k]}" for k in ("green", "yellow", "red", "unavailable") if z.get(k)) or "sin decisiones registradas"
    rk, rn = w["rpe_coverage"]
    md = [f"# Resumen semanal · {d(w['start'])}–{d(w['end'])}", "",
          "_Semana móvil que termina hoy, comparada con los 7 días anteriores. Fuente: `app/readiness_v3.json`"
          + (f" (informe `{report_id}`)" if report_id else "") + "._", "",
          "## En una frase", ""]
    hard = len(w["over_cap"])
    sentence = [f"{w['sessions']} sesiones" + (f" ({'+' if w['sessions'] >= w['sessions_prev'] else '−'}{abs(w['sessions'] - w['sessions_prev'])})" if w['sessions_prev'] else "")]
    if w["hrv_rolling_end"] is not None and None not in w["hrv_range"]:
        lo, hi = w["hrv_range"]
        band = "por debajo de" if w["hrv_rolling_end"] < lo else "por encima de" if w["hrv_rolling_end"] > hi else "dentro de"
        sentence.append(f"HRV de 7 días {band} tu rango normal")
    if w["nights_sleep"]:
        sentence.append(f"{w['short_nights']} de {w['nights_sleep']} noches con datos por debajo de {_f(w['need'])} h de sueño")
    else:
        sentence.append("sin datos de sueño esta semana")
    if not w["cap_checked_days"]:
        sentence.append("RPE máximo aún sin comprobar (no hay decisiones registradas en días entrenados)")
    elif hard:
        sentence.append(f"{hard} de {w['cap_checked_days']} días comprobados por encima del RPE máximo")
    else:
        sentence.append(f"ningún día por encima del RPE máximo ({w['cap_checked_days']} de {w['trained_days']} días entrenados comprobados)")
    md += ["- " + "; ".join(sentence) + ".", f"- Decisión registrada en {w['days_with_decision']}/7 días: {zones_txt}.", ""]

    md += ["## Entrenamiento", "", "| | Esta semana | Semana previa |", "|---|--:|--:|",
           f"| Sesiones | {w['sessions']} | {w['sessions_prev']} |",
           f"| Minutos | {_f(w['minutes'], 0)} | {_f(w['minutes_prev'], 0)} |",
           f"| Carga (Intervals) | {_f(w['load'], 0)} | {_f(w['load_prev'], 0)} |",
           f"| sRPE (RPE × min) | {_f(w['srpe'], 0)} | {_f(w['srpe_prev'], 0)} |", "",
           f"Monotonía {_f(load.get('monotony'), 2)} · strain {_f(load.get('strain'), 0)} · ACWR {_f(load.get('acwr'), 2)}"
           f" · RPE registrado en {rk}/{rn} sesiones.", ""]
    if w["over_cap"]:
        md += ["**Días por encima del RPE máximo de la decisión:** "
               + ", ".join(f"{d(o['date'])} (RPE {_f(o['rpe'])} > {o['cap']})" for o in w["over_cap"]) + ".", ""]

    md += ["## Recuperación", "", "| | Esta semana | Semana previa |", "|---|--:|--:|",
           f"| HRV media | {_f(w['hrv'], 1, ' ms')} | {_f(w['hrv_prev'], 1, ' ms')} |",
           f"| FC en reposo media | {_f(w['rhr'], 1, ' lpm')} | {_f(w['rhr_prev'], 1, ' lpm')} |",
           f"| Sueño medio | {_f(w['sleep'], 2, ' h')} | {_f(w['sleep_prev'], 2, ' h')} |", ""]
    lo, hi = w["hrv_range"]
    if w["hrv_rolling_end"] is not None and None not in (lo, hi):
        md += [f"HRV de 7 días hoy: {_f(w['hrv_rolling_end'], 1, ' ms')} (rango normal {_f(lo, 1)}–{_f(hi, 1)} ms)."
               + (f" Turnos: {', '.join(w['shifts'])}." if w["shifts"] else ""), ""]

    md += ["## Fuerza de la semana", ""]
    if w["strength"]:
        md += ["| Fecha | Ejercicio | Carga máx. declarada | Series |", "|---|---|--:|--:|"]
        for x in w["strength"]:
            md.append(f"| {d(x['date'])} | {x.get('exercise') or '—'} | {_f(x.get('peak_declared_load_kg'), 1, ' kg')} | "
                      f"{x.get('known_sets') or '—'}/{x.get('total_sets') or '—'} |")
        md += ["", "_Carga máxima declarada, no 1RM; solo es comparable con el mismo ejercicio e implemento._", ""]
    else:
        md += ["_Sin series de fuerza con carga registradas esta semana._", ""]

    md += ["## Calidad de los datos", "",
           f"- Noches con HRV: {w['nights_hrv']}/7 · con sueño: {w['nights_sleep']}/7.",
           f"- Sesiones con RPE: {rk}/{rn}.", ""]
    if w["validation"]:
        md += ["## Validación de modelos", "", w["validation"], ""]
    md += ["_No es un diagnóstico médico._", ""]
    return "\n".join(md)
