"""Panel V9: la portada de la web, rediseñada para leerse de un vistazo.

Cuatro pestañas (Hoy · Recuperación · Entrenos · Progreso). Cada tarjeta responde a una pregunta y dice su conclusión.
Las comparaciones se hacen contra la **misma serie** de la que sale el valor de hoy (tendencia de 28 días) y, por turno,
solo con al menos 5 días comparables; semana contra semana solo con semanas completas. Sin fuentes mezcladas, sin
porcentajes entre ventanas incompletas. El panel anterior sigue disponible como `panel_completo.html`.
"""
from __future__ import annotations

import re
from datetime import date as _date, timedelta
from pathlib import Path

from . import coaching as co
from . import longterm_history as lh
from . import sensations as sn
from .visual_report import (MES, ZONE, _bb_points, _day, _fnum, _iso, _load, _ms_local, _sessions_today, bars_h,
                            bb_curve, day_bars, ddmm, esc, hhmm, line_chart, num, stacked)
from .visual_report import PAGE as _VR_PAGE

MIN_N = 10          # días mínimos para dar un rango habitual
MIN_CONTEXT = 5     # días del mismo turno para compararlos aparte


# ---------------------------------------------------------------- comparaciones

def _quantile(xs: list[float], q: float) -> float:
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = (len(s) - 1) * q
    lo, hi = int(pos), min(int(pos) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def _cal(cal: dict) -> dict:
    return {"days": cal.get("days") if isinstance(cal.get("days"), dict) else {},
            "confirmed_months": [m for m in cal.get("confirmed_months") or [] if isinstance(m, str)]
            if isinstance(cal.get("confirmed_months"), list) else []}


def context_of(day: str, cal: dict) -> str | None:
    """Contexto laboral con la regla de la app (shift_calendar.resolve_day): TN, MT, post-TN o libre.

    Un MT tras un TN sigue siendo MT; un día de un mes sin confirmar es desconocido (None) y no cuenta como libre.
    """
    from .shift_calendar import resolve_day
    try:
        label = resolve_day(day, _cal(cal))["label"]
    except (TypeError, ValueError, KeyError):
        return None
    return {"free": "libre", "TN": "TN", "MT": "MT", "M": "M", "post-TN": "post-TN"}.get(label)


CONTEXT_LABEL = {"TN": "días de TN", "post-TN": "días post-TN", "MT": "días de MT", "libre": "días libres"}


def normal_range(rows: list[dict], key: str, today: str, cal: dict | None = None) -> dict | None:
    """Rango habitual (p10–p90 y mediana) de los días previos a hoy en la misma serie; y el del mismo turno si hay ≥ 5."""
    prev = [r for r in rows if r.get("date") and r["date"] < today and _fnum(r.get(key)) is not None]
    xs = [r[key] for r in prev]
    if len(xs) < MIN_N:
        return None
    out = {"n": len(xs), "p10": _quantile(xs, 0.1), "p50": _quantile(xs, 0.5), "p90": _quantile(xs, 0.9)}
    if cal:
        ctx = context_of(today, cal)
        same = [r[key] for r in prev if ctx and context_of(r["date"], cal) == ctx]
        if ctx and len(same) >= MIN_CONTEXT:
            out["context"] = {"label": CONTEXT_LABEL[ctx], "n": len(same), "p50": _quantile(same, 0.5)}
    return out


def verdict(value, rng: dict | None, higher_is_better: bool) -> tuple[str, str]:
    """(clase, texto) de un valor frente a su rango habitual."""
    if _fnum(value) is None or not rng:
        return "na", "sin referencia suficiente"
    if rng["p10"] <= value <= rng["p90"]:
        return "ok", "dentro de lo habitual"
    better = (value > rng["p90"]) == higher_is_better
    return ("good", "mejor que lo habitual") if better else ("bad", "peor que lo habitual")


def range_row(name: str, value, unit: str, rng: dict | None, higher_is_better: bool, dec: int = 0) -> str:
    cls, txt = verdict(value, rng, higher_is_better)
    if rng and _fnum(value) is not None:
        lo = min(rng["p10"], value)
        hi = max(rng["p90"], value)
        pad = (hi - lo) * 0.15 or 1
        lo, hi = lo - pad, hi + pad
        pos = lambda v: (v - lo) / (hi - lo) * 100  # noqa: E731
        track = (f'<span class="rr-t"><em style="left:{pos(rng["p10"]):.1f}%;width:{pos(rng["p90"]) - pos(rng["p10"]):.1f}%"></em>'
                 f'<b class="rr-m" style="left:{pos(rng["p50"]):.1f}%"></b><i class="rr-d {cls}" style="left:{pos(value):.1f}%"></i></span>')
        ref = f'habitual {num(rng["p10"], dec)}–{num(rng["p90"], dec)} · mediana {num(rng["p50"], dec)} · {rng["n"]} días'
        if rng.get("context"):
            c = rng["context"]
            ref += f' · tus {esc(c["label"])}: {num(c["p50"], dec)} ({c["n"]})'
    else:
        track, ref = '<span class="rr-t empty"></span>', "aún no hay suficientes días para un rango habitual"
    return (f'<div class="rr"><div class="rr-h"><span class="rr-n">{esc(name)}</span><span class="rr-v">{num(value, dec)}'
            f'<small>{esc(unit)}</small></span><span class="rr-s {cls}">{esc(txt)}</span></div>{track}<p class="rr-r">{ref}</p></div>')


def complete_weeks(sessions: list[dict], today: str, n: int = 4) -> list[dict]:
    """Semanas lunes–domingo completas dentro de la ventana de sesiones, con sRPE, sesiones y días entrenados."""
    t = _date.fromisoformat(today)
    this_monday = t - timedelta(days=t.weekday())
    dated = [s for s in sessions if isinstance(s, dict) and _iso(s.get("date")) and not s.get("removed")]
    first = min((_iso(s["date"]) for s in dated), default=None)
    out = []
    for i in range(n, 0, -1):
        mon = this_monday - timedelta(days=7 * i)
        sun = mon + timedelta(days=6)
        if not first or mon.isoformat() < first:
            continue  # semana no cubierta entera por los datos
        ws = [s for s in dated if mon.isoformat() <= _iso(s["date"]) <= sun.isoformat()]
        out.append({"monday": mon.isoformat(), "sessions": len(ws), "days": len({_iso(s["date"]) for s in ws}),
                    "srpe": round(sum(s.get("srpe") or 0 for s in ws)),
                    "hard": sum(1 for s in ws if (_fnum(s.get("rpe")) or 0) >= 8)})
    return out


# ---------------------------------------------------------------- bloques

def card(title: str, body: str, sub: str = "", cls: str = "", ident: str = "") -> str:
    return (f'<section class="card {cls}"{f" id={chr(34)}{ident}{chr(34)}" if ident else ""}><h2>{esc(title)}</h2>'
            + (f'<p class="sub">{sub}</p>' if sub else "") + body + "</section>")


def takeaway(text: str, cls: str = "") -> str:
    return f'<p class="tk {cls}">{text}</p>'


def _ses(n, zero: str = "sin sesiones") -> str:
    n = _fnum(n) or 0
    return zero if not n else ("1 sesión" if n == 1 else f"{num(n)} sesiones")


def _week_bars(weeks: list[dict]) -> str:
    if not weeks:
        return '<p class="muted">Aún no hay semanas completas en la ventana de datos.</p>'
    hi = max((w.get("total", w.get("srpe")) or 0) for w in weeks) or 1
    rows = ""
    for w in weeks:
        m = _date.fromisoformat(w["monday"])
        off = w.get("official", w.get("srpe")) or 0
        est = w.get("estimated") or 0
        rows += (f'<div class="wk"><span class="wk-l">{m.day} {MES[m.month - 1]}</span><span class="wk-t"><i style="width:{off / hi * 100:.1f}%"></i>'
                 f'<i class="est" style="width:{est / hi * 100:.1f}%"></i></span><span class="wk-v">{num(off + est)}</span>'
                 f'<span class="wk-s">{_ses(w["sessions"])} · {w["days"]} días · {w["hard"]} con RPE ≥ 8'
                 + (f' · {num(est)} estimada' if est else "") + '</span></div>')
    return (f'<div class="wks">{rows}</div><p class="legend"><span><i class="sw s1b"></i>con RPE (sRPE)</span>'
            '<span><i class="sw estb"></i>estimada (sin RPE)</span></p>')


def _metcon_compare(m: dict) -> str:
    sim = (m.get("similar") or [None])[0]
    if not sim:
        return ""

    def res(c):
        t = next((x.split(" ", 1)[1] for x in c.get("timing") or [] if isinstance(x, str) and x.startswith("Oficial ")), None)
        return t or str(c.get("result") or "—").split(" · ")[0]
    head = ("Mismo WOD que el " if sim.get("repeat") else "Parecido al ") + ddmm(sim.get("date"))
    return (f'<div class="cmp"><p class="cmp-h">{head} · comparten {esc(", ".join(sim.get("shared") or []))}</p>'
            f'<div class="cmp-g"><span></span><b>Este</b><b>{ddmm(sim.get("date"))}</b>'
            f'<span>Formato</span><span>{esc(m.get("format") or "—")}</span><span>{esc(sim.get("format") or "—")}</span>'
            f'<span>Resultado</span><span>{esc(res(m))}</span><span>{esc(res(sim))}</span>'
            f'<span>RPE</span><span>{num(m.get("rpe"), 1)}</span><span>{num(sim.get("rpe"), 1)}</span></div></div>')


def _spark(points: list[tuple[str, float]], w: int = 160, h: int = 40) -> str:
    pts = [(d, v) for d, v in points if _iso(d) and _fnum(v) is not None]
    if len(pts) < 2:
        return ""
    vs = [v for _, v in pts]
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1
    xs = [i / (len(pts) - 1) * (w - 8) + 4 for i in range(len(pts))]
    ys = [h - 6 - (v - lo) / rng * (h - 12) for v in vs]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys, strict=True))
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" role="img"><polyline class="ln s1" points="{line}"/>'
            f'<circle class="dot s1" cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="3"/></svg>')


def _pick(flat: dict | None, *suffixes: str):
    """Primer valor cuyo nombre de campo (última parte de la ruta) coincide con alguno de los sufijos, sin distinguir mayúsculas."""
    if not isinstance(flat, dict):
        return None
    for suf in suffixes:
        for k, v in flat.items():
            if str(k).rsplit(".", 1)[-1].lower() == suf.lower() and v not in (None, ""):
                return v
    return None


def _hms(sec) -> str:
    sec = _fnum(sec)
    if sec is None or sec <= 0:
        return "—"
    sec = int(round(sec))
    h, m, s_ = sec // 3600, sec % 3600 // 60, sec % 60
    return f"{h}:{m:02d}:{s_:02d}" if h else f"{m}:{s_:02d}"


def garmin_performance(ext: dict) -> list[tuple[str, str, str]]:
    """(métrica, valor, detalle) de lo que Garmin publica en su panel de rendimiento; solo lo que haya llegado."""
    ts = ext.get("training_status") or {}
    pf = ext.get("performance") if isinstance(ext.get("performance"), dict) else {}
    out = []
    vo2 = _pick(ts, "vo2MaxPreciseValue", "vo2MaxValue")
    if _fnum(vo2) is not None:
        out.append(("VO₂ máx.", num(vo2, 1), "estimación de Garmin"))
    fa = _pick(pf.get("fitness_age"), "fitnessAge") or _pick(ts, "fitnessAge")
    ca = _pick(pf.get("fitness_age"), "chronologicalAge")
    if _fnum(fa) is not None:
        ach = _pick(pf.get("fitness_age"), "achievableFitnessAge")
        det = [f"edad real {num(ca)}"] if _fnum(ca) is not None else []
        if _fnum(ach) is not None:
            det.append(f"alcanzable {num(ach, 1)}")
        out.append(("Edad física", num(fa, 1), " · ".join(det)))
    es = _pick(pf.get("endurance_score"), "overallScore", "enduranceScore")
    if _fnum(es) is not None:
        cls = _pick(pf.get("endurance_score"), "classification")
        out.append(("Resistencia (Endurance Score)", num(es), f"clase {esc(cls)}" if cls not in (None, "") else ""))
    hs = _pick(pf.get("hill_score"), "overallScore", "hillScore")
    if _fnum(hs) is not None:
        out.append(("Cuestas (Hill Score)", num(hs), ""))
    rp = pf.get("race_predictions")
    races = [(n, _pick(rp, k)) for n, k in (("5 km", "time5K"), ("10 km", "time10K"), ("Media", "timeHalfMarathon"), ("Maratón", "timeMarathon"))]
    races = [(n, v) for n, v in races if _fnum(v)]
    if races:
        out.append(("Predicción de carrera", " · ".join(f"{n} {_hms(v)}" for n, v in races[:2]), " · ".join(f"{n} {_hms(v)}" for n, v in races[2:])))
    lt = _pick(pf.get("lactate_threshold"), "heartRate", "lactateThresholdHeartRate", "hrValue")
    if _fnum(lt) is not None:
        out.append(("Umbral de lactato", f"{num(lt)} lpm", "carrera"))
    ftp, pw = _pick(pf.get("lactate_threshold"), "functionalThresholdPower"), _pick(pf.get("lactate_threshold"), "powerToWeight")
    if _fnum(ftp) is not None:
        out.append(("Potencia umbral (carrera)", f"{num(ftp)} W", f"{num(pw, 1)} W/kg" if _fnum(pw) is not None else ""))
    dts = ext.get("daily_training_status") or {}
    acute, chronic = _pick(dts, "dailyTrainingLoadAcute"), _pick(dts, "dailyTrainingLoadChronic")
    if _fnum(acute) is not None:
        ratio = _pick(dts, "dailyAcuteChronicWorkloadRatio")
        stt = {"OPTIMAL": "óptimo", "HIGH": "alto", "VERY_HIGH": "muy alto", "LOW": "bajo"}.get(str(_pick(dts, "acwrStatus") or "").upper(), "")
        det = [f"crónica {num(chronic)}"] if _fnum(chronic) is not None else []
        if _fnum(ratio) is not None:
            det.append(f"ratio {num(ratio, 1)}" + (f" ({stt})" if stt else ""))
        out.append(("Carga aguda (7 d)", num(acute), " · ".join(det)))
    lb = ext.get("four_week_load_balance") or {}
    parts = []
    for name, key in (("aeróbica baja", "monthlyLoadAerobicLow"), ("aeróbica alta", "monthlyLoadAerobicHigh"), ("anaeróbica", "monthlyLoadAnaerobic")):
        v, lo, hi = _pick(lb, key), _pick(lb, key + "TargetMin"), _pick(lb, key + "TargetMax")
        if _fnum(v) is not None:
            tag = " ↑" if _fnum(hi) is not None and _fnum(v) > _fnum(hi) else " ↓" if _fnum(lo) is not None and _fnum(v) < _fnum(lo) else ""
            parts.append(f"{name} {num(v)}" + (f" ({num(lo)}–{num(hi)})" if _fnum(lo) is not None and _fnum(hi) is not None else "") + tag)
    if parts:
        ph = re.sub(r"_\d+$", "", str(_pick(lb, "trainingBalanceFeedbackPhrase") or "")).upper()
        es_ph = {"BALANCED": "Equilibrado", "ANAEROBIC_FOCUS": "Enfoque anaeróbico", "AEROBIC_HIGH_FOCUS": "Enfoque aeróbico alto",
                 "AEROBIC_LOW_FOCUS": "Enfoque aeróbico bajo", "ANAEROBIC_SHORTAGE": "Falta anaeróbica", "AEROBIC_HIGH_SHORTAGE": "Falta aeróbica alta",
                 "AEROBIC_LOW_SHORTAGE": "Falta aeróbica baja"}.get(ph, ph.replace("_", " ").lower().capitalize() or "—")
        out.append(("Enfoque de carga (4 sem.)", esc(es_ph), " · ".join(parts)))
    rt = (ext.get("recovery_time") or {}).get("hours")
    if _fnum(rt) is not None:
        out.append(("Tiempo de recuperación", f"{num(rt)} h", "según Garmin"))
    hv = ext.get("hrv_status") or {}
    if _fnum(hv.get("last_night_avg")) is not None:
        hst = {"BALANCED": "Equilibrado", "UNBALANCED": "Desequilibrado", "LOW": "Bajo", "POOR": "Bajo"}.get(str(hv.get("status") or "").upper(), esc(hv.get("status") or ""))
        out.append(("Estado VFC", hst or "—", f'noche {num(hv.get("last_night_avg"))} ms · semana {num(hv.get("weekly_avg"))} ms'))
    im = pf.get("intensity_minutes")
    goal = _pick(im, "weekGoal", "weeklyGoal")
    mod = _pick(im, "weeklyModerate", "moderateMinutes", "moderateValue")
    vig = _pick(im, "weeklyVigorous", "vigorousMinutes", "vigorousValue")
    if _fnum(mod) is not None or _fnum(vig) is not None:
        tot = (_fnum(mod) or 0) + 2 * (_fnum(vig) or 0)
        out.append(("Minutos de intensidad", num(tot), (f"objetivo {num(goal)} · " if _fnum(goal) else "") + "moderados + 2 × vigorosos"))
    st = _pick(ts, "trainingStatusFeedbackPhrase")
    if st:
        key = re.sub(r"_\d+$", "", str(st)).upper()
        es_st = {"PRODUCTIVE": "Productivo", "MAINTAINING": "Mantenimiento", "RECOVERY": "Recuperación", "UNPRODUCTIVE": "Improductivo",
                 "DETRAINING": "Pérdida de forma", "OVERREACHING": "Sobrecarga", "PEAKING": "En pico", "STRAINED": "Exigido",
                 "NO_STATUS": "Sin estado"}.get(key, key.replace("_", " ").lower().capitalize())
        out.append(("Estado de entrenamiento", esc(es_st), "según Garmin"))
    return out


def longterm_card(root, today: str) -> str:
    """V9.4: medianas mensuales desde marzo (historial largo + daily.csv). Describe la evolución; no decide nada."""
    months = lh.monthly(root)
    cur = (today or "")[:7]

    def mlabel(k: str) -> str:
        return MES[int(k[5:7]) - 1] + (" (en curso)" if k == cur else "")

    rows = ""
    for f, name, unit, dec, higher in lh.METRICS:
        pts = [(m["month"], m[f]) for m in months if m.get(f) is not None]
        if len(pts) < 2:
            continue
        first, last = pts[0], pts[-1]
        delta = last[1] - first[1]
        better = None if round(delta, dec) == 0 else (delta > 0) == higher
        chg = (f'<span class="{"up" if better else "down"}">{"+" if delta > 0 else ""}{num(delta, dec)} '
               f'{"mejor" if better else "peor" if better is False else ""}</span>') if better is not None else '<span class="down">igual</span>'
        rows += (f'<div class="mx1"><div><b>{esc(name)}</b><small>{esc(mlabel(first[0]))} → {esc(mlabel(last[0]))} · mediana mensual</small></div>'
                 + _spark([(k + "-15", v) for k, v in pts]) + f'<div class="mx1-v">{num(last[1], dec)}{(" " + unit) if unit else ""}{chg}</div></div>')
    if not rows:
        return card("¿Cómo he cambiado mes a mes?",
                    '<p class="muted">Aparecerá cuando se descargue el historial largo de Garmin (al menos dos meses con datos).</p>')
    head = "".join(f"<th>{esc(n)}</th>" for _, n, *_ in lh.METRICS[:4])
    body = "".join(f'<tr><td>{esc(MES[int(m["month"][5:7]) - 1])} {m["month"][2:4]}</td>'
                   + "".join(f"<td>{num(m.get(f), d)}</td>" for f, _, _, d, _ in lh.METRICS[:4]) + f'<td>{m["days"]}</td></tr>'
                   for m in months if any(m.get(f) is not None for f, *_ in lh.METRICS))
    first_m = next((m["month"] for m in months if any(m.get(f) is not None for f, *_ in lh.METRICS)), None)
    return card("¿Cómo he cambiado mes a mes?", rows
                + f'<details><summary>Mes a mes</summary><table class="tbl"><thead><tr><th>Mes</th>{head}<th>días</th></tr></thead><tbody>{body}</tbody></table></details>'
                + f'<p class="muted">Mediana de cada mes con al menos {lh.MIN_DAYS_PER_MONTH} días con dato; el sueño solo cuenta noches. '
                  'El cambio compara el primer mes con el último; describe, no prueba causa.</p>',
                f"desde {MES[int(first_m[5:7]) - 1]} {first_m[:4]}" if first_m else "")


# ---------------------------------------------------------------- página

def render(root: str | Path, result: dict, extras: dict | None = None) -> str:
    root, ex = Path(root), extras or {}
    today = _iso(result.get("date"))
    if not today:
        raise ValueError("resultado sin fecha")
    ready = _load(root, "report_ready.json")
    ra = _load(root, "recovery_assessment.json")
    aa = _load(root, "advanced_analytics.json")
    ext = _day(_load(root, "garmin_extended.json").get("days"), today)
    bb = _day(_load(root, "garmin_body_battery.json").get("days"), today)
    st = _day(_load(root, "garmin_stress.json").get("days"), today)
    cf, cal = _load(root, "crossfit_insights.json"), _load(root, "shift_calendar.json")
    dec = result.get("decision") or {}
    gd = dec.get("guidance") if isinstance(dec.get("guidance"), dict) else {}
    zone = dec.get("zone")
    zc = ZONE.get(zone or "", ("—", "na"))
    trend = [dict(r, date=_iso(r.get("date"))) for r in result.get("trend_28d") or [] if isinstance(r, dict) and _iso(r.get("date"))]
    tday = next((r for r in trend if r["date"] == today), {})
    cur = ra.get("current") or {}
    sess = _sessions_today(cf, result, today)
    survey = sn.load(root)
    s_by = sn.by_date(survey, today)
    an = sn.analysis(survey, today, trend, zone)
    load = result.get("load") or {}
    t = _date.fromisoformat(today)
    # criterio sobre el historial completo (V9.1)
    hist = co.load_sessions(root)
    est_ratio = co.srpe_trimp_ratio(hist)
    weeks = co.complete_weeks(co.with_estimate(hist, est_ratio), today)
    dl = co.deload(weeks)
    ptn_months = co.post_tn_months(co.load_daily(root), hist, lambda d: context_of(d, cal))
    ptn = co.post_tn_today(ptn_months)
    is_post_tn = context_of(today, cal) == "post-TN"
    alerts = ""
    if is_post_tn:
        alerts += ('<div class="alert warn"><b>Hoy es día post-TN.</b> '
                   + (f'En tus días post-TN la recuperación media es {num(ptn["score"])} ({ptn["days"]} días; el resto, {num(ptn["rest_score"])}) '
                      f'y entrenas a RPE {num(ptn["rpe"], 1)} ({ptn["rpe_sessions"]} sesiones). ' if ptn else "")
                   + 'Mejor técnica, aeróbico suave o siesta antes de entrenar; deja lo intenso para mañana.</div>')
    if dl.get("status") == "due":
        alerts += (f'<div class="alert info"><b>Considera una semana de descarga.</b> Llevas {dl["run"]} semanas completas seguidas sin una '
                   f'semana ligera (≤ {num(dl["threshold"])} de carga, el 70 % de tu media). Orientativo, no un límite.</div>')

    # =================== HOY
    hero = (f'<section class="card hero z-{zc[1]}"><div class="hero-top"><div><p class="eyebrow">Qué hacer hoy</p>'
            f'<h2>{esc(gd.get("label") or "—")}</h2></div><span class="pill {zc[1]}">{esc(zc[0])}</span></div>'
            f'<div class="big3"><div><span>RPE máximo</span><b>{num(gd.get("rpe_max"))}</b></div><div><span>Volumen</span><b>{esc(gd.get("volume") or "—")}</b></div>'
            f'<div><span>Modelos</span><b>{esc({"total": "coinciden", "partial": "parcial"}.get(dec.get("agreement"), dec.get("agreement") or "—"))}</b></div></div>'
            f'<p>{esc(gd.get("text") or "")}</p>'
            + (('<details><summary>Pautas para el box</summary><ul>' + "".join(f"<li>{esc(x)}</li>" for x in dec.get("crossfit") or []) + "</ul></details>")
               if dec.get("crossfit") else "") + "</section>")

    # cómo estás frente a tu normal (misma serie que el valor de hoy)
    wb_rows = [{"date": d, "wb": sn.wellbeing(e)} for d, e in s_by.items()]
    rows_norm = [
        range_row("HRV", tday.get("hrv_ms"), " ms", normal_range(trend, "hrv_ms", today, cal), True),
        range_row("FC en reposo", tday.get("resting_hr"), " lpm", normal_range(trend, "resting_hr", today, cal), False),
        range_row("Sueño", tday.get("sleep_hours"), " h", normal_range(trend, "sleep_hours", today, cal), True, 1),
        range_row("Puntuación de sueño", tday.get("sleep_score"), "", normal_range(trend, "sleep_score", today, cal), True),
        range_row("Bienestar (encuesta)", an.get("today"), "/100", normal_range(wb_rows, "wb", today), True),
    ]
    bad = sum(1 for r in rows_norm if 'rr-s bad' in r)
    good = sum(1 for r in rows_norm if 'rr-s good' in r)
    tk = ("Todo dentro de tu rango habitual." if not bad and not good else
          f"{bad} indicador{'es' if bad != 1 else ''} peor que lo habitual." if bad else f"{good} indicador{'es' if good != 1 else ''} mejor que lo habitual.")
    normal_card = card("¿Cómo estás frente a tu normal?", takeaway(esc(tk), "bad" if bad else "ok") + "".join(rows_norm)
                       + '<p class="legend"><span><i class="sw band"></i>tu rango habitual (10.º–90.º percentil, 28 días)</span>'
                         '<span><i class="sw med"></i>mediana</span><span><i class="sw dot"></i>hoy</span></p>',
                       "la banda es lo normal para ti; el punto, hoy")

    # carga de 7 días frente a la media semanal de 28 días
    s28 = sum(_fnum(r.get("srpe")) or 0 for r in trend)
    s7 = sum(_fnum(r.get("srpe")) or 0 for r in trend if r["date"] > (t - timedelta(days=7)).isoformat())
    weekly_mean = s28 / 4 if len(trend) >= 28 else None
    ratio = s7 / weekly_mean if weekly_mean else None
    load_body = ""
    if ratio is not None:
        w = min(ratio / 2, 1) * 100
        cls = "ok" if 0.8 <= ratio <= 1.3 else "warn"
        load_body = (takeaway(f'Últimos 7 días: <b>{num(s7)}</b> de sRPE, <b>{num(ratio, 2)}×</b> tu semana media de las 4 últimas ({num(weekly_mean)}).', cls)
                     + f'<div class="ratio"><span class="ratio-t"><em style="left:40%;width:25%"></em><b style="left:50%"></b>'
                       f'<i class="{cls}" style="width:{w:.1f}%"></i></span><span class="ratio-l"><span>0×</span><span>1× tu media</span><span>2×</span></span></div>'
                     + '<p class="muted">La franja marca 0,8–1,3×, una referencia orientativa habitual; no es un límite médico.</p>')
    else:
        load_body = '<p class="muted">Aún no hay 28 días de carga para comparar.</p>'
    load_card = card("¿Cuánto estás entrenando?", load_body, f'{num(load.get("week_sessions"))} sesiones en 7 días')

    # sensaciones
    e_today = s_by.get(today)
    if e_today:
        chips = "".join(
            f'<span class="chip-l l{sn.level(e_today, k)}">{esc(n)}: {esc(labels[sn.level(e_today, k)])}</span>'
            for k, n, labels in sn.ITEMS if sn.level(e_today, k) is not None)
        zones = ", ".join(esc(z) for z in sn.zones_of(e_today))
        obs = "".join(f'<li class="o-{esc(o["level"])}">{esc(o["text"])}</li>' for o in an.get("observations") or [])
        cal_txt = an.get("calibration") or {}
        sens_body = (f'<div class="wb"><span class="wb-v {"ok" if (an.get("today") or 0) >= 70 else "warn" if (an.get("today") or 0) >= 50 else "bad"}">'
                     f'{num(an.get("today"))}</span><span class="wb-l">índice de bienestar<small>0–100 · solo con la encuesta completa</small></span></div>'
                     f'<div class="chips">{chips}</div>' + (f'<p class="zones">📍 {zones}</p>' if zones else "")
                     + (f'<ul class="obs">{obs}</ul>' if obs else "")
                     + (f'<p class="muted">Calibrando tu normalidad: {cal_txt.get("surveys", 0)} de {cal_txt.get("needed", 10)} encuestas previas.</p>'
                        if not cal_txt.get("personal") else ""))
    else:
        sens_body = '<p class="hint">Sin encuesta hoy. Te la mando cuando me dictes el entreno.</p>'
    sens_card = card("¿Cómo te sientes?", sens_body, "lo que tú dices · no cambia la puntuación de recuperación")

    # hoy y mañana
    lines = "".join(f'<li><span class="s-t">{hhmm(s.get("start_local"))}</span><span class="s-n">{esc(s.get("label") or s.get("name"))}'
                    f'<small>{num(s.get("duration_min"))} min · sRPE {num(s.get("srpe"))}</small></span>'
                    + (f'<span class="pill {"bad" if s["rpe"] >= 9 else "warn" if s["rpe"] >= 7.5 else "ok"}">RPE {num(s["rpe"], 1)}</span>'
                       if _fnum(s.get("rpe")) is not None else '<span class="pill na">sin RPE</span>') + "</li>" for s in sess)
    hours = cal.get("shift_hours") if isinstance(cal.get("shift_hours"), dict) else {}

    def shift(d):
        ctx = context_of(d.isoformat(), cal)
        if ctx in ("TN", "MT", "M"):
            hh = hours.get(ctx) if isinstance(hours.get(ctx), dict) else {}
            return f'<span class="chip strong">{esc(ctx)} {esc(hh.get("start", ""))}–{esc(hh.get("end", ""))}</span>'
        if ctx is None:
            return '<span class="chip">sin confirmar</span>'
        return f'<span class="chip">{"libre tras TN" if ctx == "post-TN" else "libre"}</span>'
    lead = ex.get("ai_lead") or []
    lead_html = f'<p class="lead">{esc(lead[0])}</p>' if lead and isinstance(lead[0], str) else ""
    day_card = card("Hoy y mañana", lead_html
                    + (f'<ul class="sess-l">{lines}</ul>' if lines else '<p class="muted">Sin sesiones registradas hoy.</p>')
                    + f'<div class="shifts"><div><span class="s-d">Hoy</span>{shift(t)}</div><div><span class="s-d">Mañana</span>{shift(t + timedelta(days=1))}</div>'
                      f'<div><span class="s-d">Pasado</span>{shift(t + timedelta(days=2))}</div></div>')
    tab_hoy = hero + alerts + '<div class="grid">' + normal_card + '<div class="col">' + sens_card + load_card + "</div></div>" + day_card

    # =================== RECUPERACIÓN
    hyb, pri = aa.get("readiness_hybrid") or {}, aa.get("personal_recovery_index") or {}
    tr = ext.get("training_readiness") or {}

    def zcls(v):
        return "ok" if (v or 0) >= 70 else "warn" if (v or 0) >= 50 else "bad"
    v2, v3 = tday.get("v2_score"), (result.get("readiness") or {}).get("score")
    models = card("¿Qué dicen los modelos?", takeaway(f'Decide el más prudente: <b>{esc(zc[0])}</b>.')
                  + bars_h([("Oficial", v2, zcls(v2)), ("Híbrido", hyb.get("score"), zcls(hyb.get("score"))), ("Experimental", v3, zcls(v3)),
                            ("Índice personal", pri.get("score"), "s2"), ("Garmin Readiness", tr.get("score"), "s2")]),
                  "0–100 · deciden oficial, híbrido y experimental (manda el más prudente); el resto es referencia")
    sd = ext.get("sleep_detail") or {}
    sl_rng = normal_range(trend, "sleep_hours", today, cal)
    sleep = card("¿He dormido lo suficiente?",
                 takeaway(f'{num(tday.get("sleep_hours"), 1)} h ({hhmm(cur.get("sleep_start_local"))} → {hhmm(cur.get("sleep_end_local"))}), '
                          f'{verdict(tday.get("sleep_hours"), sl_rng, True)[1]}.')
                 + stacked([("Profundo", sd.get("deep_minutes"), "c-deep"), ("Ligero", sd.get("light_minutes"), "c-light"),
                            ("REM", sd.get("rem_minutes"), "c-rem"), ("Despierto", sd.get("awake_minutes"), "c-awake")])
                 + "<h3>14 noches</h3>" + day_bars(trend[-14:], "sleep_hours", w=420, h=160, ref=sl_rng["p50"] if sl_rng else None, ref_label="mediana",
                                                   cls_fn=lambda r: "warn" if (r.get("sleep_score") or 100) < 60 else "s1")
                 + '<p class="muted">Ámbar: puntuación de sueño por debajo de 60.</p>')
    hrv_rng = normal_range(trend, "hrv_ms", today, cal)
    hrv = card("¿Cómo está mi sistema nervioso?",
               takeaway(f'HRV {num(tday.get("hrv_ms"))} ms, {verdict(tday.get("hrv_ms"), hrv_rng, True)[1]}; '
                        f'FC en reposo {num(tday.get("resting_hr"))} lpm, {verdict(tday.get("resting_hr"), normal_range(trend, "resting_hr", today, cal), False)[1]}.')
               + line_chart(trend, [("hrv_ms", "HRV (ms)", "s1"), ("hrv_rolling_ms", "media 7 días", "s3")], band=("hrv_low_ms", "hrv_high_ms"), w=420, h=190)
               + "<h3>FC en reposo y nocturna</h3>" + line_chart(trend, [("resting_hr", "FC reposo", "s2"), ("night_hr", "FC nocturna", "s4")], h=160, w=420),
               "28 días · banda = tu rango normal de HRV")
    dt = ((ex.get("recovery_context") or {}).get("day_types") or {}).get("rows") or []
    dt_rows = "".join(f'<tr><th>{esc(r.get("label"))}</th><td>{num(r.get("score"))}</td><td>{num(r.get("hrv"))}</td><td>{num(r.get("sleep"), 1)}</td>'
                      f'<td>{num(r.get("rpe"), 1)}</td><td>{num(r.get("days"))}</td></tr>' for r in dt if isinstance(r, dict) and r.get("enough"))
    shift_card = card("¿Cómo me afecta el turno?",
                      ('<table class="tbl"><thead><tr><th></th><th>Recup.</th><th>HRV</th><th>Sueño h</th><th>RPE</th><th>días</th></tr></thead>'
                       f'<tbody>{dt_rows}</tbody></table><p class="muted">Medias por tipo de día; solo tipos con días suficientes. Describe, no prueba causa.</p>')
                      if dt_rows else '<p class="muted">Aún no hay días suficientes por turno.</p>')
    vals = bb.get("bodyBatteryValuesArray") or []
    bbp = _bb_points(vals)
    last_dt = _ms_local(bbp[-1][0]) if bbp else None
    energy = card("¿Cuánta energía me queda?",
                  takeaway(f'Body Battery {num(bbp[-1][1] if bbp else None)} a las {last_dt.strftime("%H:%M") if last_dt else "—"} · '
                           f'estrés medio {num(st.get("avgStressLevel"))}, máximo {num(st.get("maxStressLevel"))}.') + bb_curve(vals, w=420)
                  + '<p class="muted">Última medición sincronizada, no en directo.</p>')
    ptn_rows = "".join(
        f'<tr><th>{MES[int(r["month"][5:7]) - 1]} {r["month"][:4]}</th><td>{num(r["post"]["score"])}</td><td>{num(r["rest"]["score"])}</td>'
        f'<td>{num(r["post"]["rpe"], 1)}</td><td>{num(r["rest"]["rpe"], 1)}</td><td>{r["post"]["days_scored"]} / {r["post"]["sessions"]}</td></tr>' for r in ptn_months)
    ptn_card = card("¿Cómo entreno tras el turno de noche?",
                    (takeaway(f'Tras un TN tu recuperación media es <b>{num(ptn["score"])}</b> ({ptn["days"]} días; resto {num(ptn["rest_score"])}), '
                              f'pero entrenas a RPE <b>{num(ptn["rpe"], 1)}</b> ({ptn["rpe_sessions"]} sesiones). Mejor sesiones suaves esos días.', "warn")
                     if ptn and (ptn["score"] or 0) < (ptn["rest_score"] or 0) else "")
                    + ('<table class="tbl"><thead><tr><th>Mes</th><th>Recup. post-TN</th><th>Recup. resto</th><th>RPE post-TN</th><th>RPE resto</th><th>días / ses.</th></tr></thead>'
                       f'<tbody>{ptn_rows}</tbody></table><p class="muted">Recuperación oficial media (días con puntuación) y RPE medio de las sesiones con RPE de esos días; '
                       'mes a mes para ver si el cambio funciona. Describe, no prueba causa.</p>' if ptn_rows else
                       '<p class="muted">Aún no hay días post-TN con datos.</p>'))
    tab_rec = '<div class="grid">' + models + sleep + "</div>" + hrv + ptn_card + '<div class="grid">' + shift_card + energy + "</div>"

    # =================== ENTRENOS
    wk_tk = ""
    if len(weeks) >= 2:
        a, b = weeks[-1], weeks[-2]
        wk_tk = takeaway(f'Última semana completa: {a["sessions"]} sesiones y {num(a["total"])} de carga; la anterior, {b["sessions"]} y {num(b["total"])}.')
    dl_txt = ({"due": f'<p class="alert info"><b>Semana de descarga recomendable:</b> {dl.get("run")} semanas seguidas por encima de {num(dl.get("threshold"))}.</p>',
               "ok": f'<p class="muted">Última semana ligera (≤ {num(dl.get("threshold"))}): {ddmm(dl.get("last_light")) if dl.get("last_light") else "ninguna en el historial"}. '
                     f'Se sugiere descarga tras {co.HEAVY_RUN} semanas seguidas sin una ligera.</p>'}.get(dl.get("status"), '<p class="muted">Aún no hay 4 semanas completas para valorar la descarga.</p>'))
    ratio_txt = (f'Las sesiones sin RPE se estiman con su TRIMP × {num(est_ratio["ratio"], 1)} (tu relación mediana sRPE/TRIMP en {est_ratio["n"]} sesiones).'
                 if est_ratio else "Aún no hay sesiones suficientes con RPE y TRIMP para estimar la carga de las sesiones sin RPE.")

    def rest_label(r):
        return "D" if r.get("rest_confirmed") else "—"
    train_load = card("¿Cómo se reparte mi carga?",
                      day_bars(trend[-14:], "srpe", label=rest_label, h=170, w=420)
                      + "<h3>Semanas completas (lunes a domingo)</h3>" + wk_tk + _week_bars(weeks) + dl_txt
                      + f'<p class="muted">{ratio_txt}</p>',
                      "sRPE = RPE × minutos (solo sesiones con RPE) · «D» descanso confirmado · «—» sin registro")
    by_day: dict[str, list] = {}
    for s in result.get("sessions_28d") or []:
        if isinstance(s, dict) and _iso(s.get("date")) and _iso(s["date"]) > (t - timedelta(days=7)).isoformat() and not s.get("removed"):
            by_day.setdefault(_iso(s["date"]), []).append(s)
    notes = {}
    for a in cf.get("activities") or []:
        if isinstance(a, dict):
            notes[str(a.get("activity_id"))] = [b.get("notes") for b in a.get("manual_blocks") or [] if isinstance(b, dict) and b.get("notes")]
    days_html = ""
    for d in sorted(by_day, reverse=True):
        items = ""
        for s in sorted(by_day[d], key=lambda x: str(x.get("start_local") or "")):
            rp = s.get("rpe")
            pill = (f'<span class="pill {"bad" if rp >= 9 else "warn" if rp >= 7.5 else "ok"}">RPE {num(rp, 1)}</span>'
                    if _fnum(rp) is not None else '<span class="pill na">sin RPE</span>')
            nt = "".join(f"<p>{esc(n)}</p>" for n in notes.get(str(s.get("id"))) or [])
            items += (f'<details class="sess"><summary><span class="s-t">{hhmm(s.get("start_local"))}</span><span class="s-n">'
                      f'{esc(s.get("label") or s.get("name"))}<small>{num(s.get("duration_min"))} min · FC {num(s.get("avg_hr"))}/{num(s.get("max_hr"))}'
                      f' · sRPE {num(s.get("srpe"))}</small></span>{pill}</summary><div class="s-b">{nt or "<p class=muted>Sin detalle.</p>"}</div></details>')
        days_html += f'<h3 class="day-h">{ddmm(d)}</h3>{items}'
    sessions = card("¿Qué he hecho esta semana?", days_html or '<p class="muted">Sin sesiones en 7 días.</p>', "toca una sesión para ver el detalle")
    mets = [m for m in ((ex.get("training_blocks") or {}).get("metcons") or []) if isinstance(m, dict)][:6]
    met_html = "".join(f'<div class="met"><div class="met-h"><b>{esc(m.get("format") or "Metcon")}</b><span>{ddmm(m.get("date"))}</span>'
                       + (f'<span class="pill {"bad" if m["rpe"] >= 9 else "warn" if m["rpe"] >= 7.5 else "ok"}">RPE {num(m["rpe"], 1)}</span>' if _fnum(m.get("rpe")) is not None else "")
                       + f'</div><p class="met-r">{esc(str(m.get("result") or "—"))}</p>{_metcon_compare(m)}</div>' for m in mets)
    metcons = card("¿Cómo me fueron los WODs?", met_html or '<p class="muted">Sin metcons registrados.</p>',
                   "cada WOD con el más parecido que hayas hecho · orientativo")
    tab_ent = train_load + '<div class="grid">' + sessions + metcons + "</div>"

    # =================== PROGRESO
    ap = ex.get("athlete_progress") or {}
    mx_rows = ""
    for m in [x for x in ap.get("maxes") or [] if isinstance(x, dict)][:8]:
        ser = [(x.get("date"), x.get("e1rm")) for x in m.get("series") or [] if isinstance(x, dict)]
        dlt = m.get("delta")
        mx_rows += (f'<div class="mx1"><div><b>{esc(str(m.get("name", "")).capitalize())}</b><small>{_ses(m.get("sessions"))} · mejor {num(m.get("e1rm"), 1)} kg</small></div>'
                    f'{_spark(ser)}<div class="mx1-v">{num(ser[-1][1] if ser else m.get("e1rm"), 1)}<small> kg</small>'
                    + (f'<span class="{"up" if dlt > 0 else "down"}">{"+" if dlt > 0 else ""}{num(dlt, 1)}</span>' if _fnum(dlt) else "") + "</div></div>")
    maxes = card("¿Me estoy haciendo más fuerte?", (mx_rows or '<p class="muted">Aún no hay series suficientes.</p>')
                 + '<p class="muted">1RM estimado (Epley, series de 10 repeticiones o menos) de cada sesión; una sesión de volumen sale más baja sin perder fuerza.</p>',
                 "último valor y cambio frente a la sesión anterior")
    sk_rows = ""
    for g in (ap.get("skill_groups") or [])[:8]:
        if not isinstance(g, dict):
            continue
        hitos = " ".join(f'<span class="chip">🏅 {esc(h.get("title"))} · {ddmm(h.get("date"))}</span>' for h in g.get("hitos") or [] if isinstance(h, dict))
        sk_rows += (f'<div class="sk"><b>{esc(g.get("skill"))}</b><small>{_ses(g.get("sessions"), "sin sesiones de técnica")} · última {ddmm(g.get("last"))}</small>'
                    + (f'<p>{esc(g.get("level"))}</p>' if g.get("level") else "") + (f'<div class="chips">{hitos}</div>' if hitos else "") + "</div>")
    skills = card("¿Qué habilidades estoy ganando?", sk_rows or '<p class="muted">Sin sesiones de técnica registradas.</p>')
    wt = ex.get("weight") or {}
    wpts = [{"date": _iso(p.get("date")), "w": p.get("weight")} for p in wt.get("points") or [] if isinstance(p, dict) and _iso(p.get("date"))]
    weight = card("¿Cómo va mi peso?",
                  (takeaway(f'{num(wt.get("current"), 1)} kg el {ddmm(wt.get("current_date"))}'
                            + (f' · {"+" if (wt.get("delta_first") or 0) > 0 else ""}{num(wt.get("delta_first"), 1)} kg desde el {ddmm(wt.get("first_date"))}' if _fnum(wt.get("delta_first")) is not None else "") + ".")
                   + line_chart(wpts, [("w", "Peso (kg)", "s4")], h=150, w=420)) if len(wpts) >= 2 else '<p class="muted">Sin registros de peso suficientes.</p>')
    wb28 = [{"date": r["date"], "wb": sn.wellbeing(s_by.get(r["date"])), "rec": r.get("v2_score")} for r in trend]
    wbc = card("¿Coincide lo que siento con lo que mide el reloj?",
               line_chart(wb28, [("wb", "Bienestar (encuesta)", "s4"), ("rec", "Recuperación oficial", "s1")], h=170, w=420)
               if sum(1 for r in wb28 if r["wb"] is not None) >= 2 else
               '<p class="muted">Aparecerá cuando haya al menos dos días con encuesta completa.</p>', "28 días")
    tsum = co.tests_summary(co.load_tests(root), today)
    t_rows = ""
    for r in tsum:
        chg = ""
        if r["change"] == 0:
            chg = '<span class="down">igual</span>'
        elif r["change"] is not None:
            sign = "−" if r["change"] < 0 else "+"
            mag = co.fmt_value(abs(r["change"]), r["unit"])
            chg = f'<span class="{"up" if r["improved"] else "down"}">{sign}{esc(mag)} {"mejor" if r["improved"] else "peor" if r["improved"] is False else ""}</span>'
        t_rows += (f'<div class="mx1"><div><b>{esc(r["name"])}</b><small>{esc(r["scaled"] or "Rx")} · {r["count"]} {"vez" if r["count"] == 1 else "veces"} · '
                   f'última {ddmm(r["last_date"])}{" · <em class=due>toca repetirlo</em>" if r["due"] else ""}</small></div><span></span>'
                   f'<div class="mx1-v">{esc(co.fmt_value(r["last"], r["unit"]))}{chg}</div></div>')
    battery = "".join(f'<li><b>{esc(n)}</b> · {esc(d)}</li>' for n, _, _, d in co.TESTS.values())
    tests = card("¿Mejoro en las pruebas de referencia?",
                 (t_rows or '<p class="hint">Aún no hay tests. Cada 6–8 semanas, haz uno o varios de esta batería y dímelo («test Fran 4:12») para comparar de verdad.</p>')
                 + f'<details><summary>La batería de tests</summary><ul class="obs">{battery}</ul></details>',
                 "lo único que demuestra progreso: repetir la misma prueba")
    gp = garmin_performance(ext)
    gp_card = card("¿Qué dice Garmin de mi forma física?",
                   ('<div class="gp">' + "".join(f'<div class="gp-i"><span>{esc(n)}</span><b>{v}</b><small>{d}</small></div>' for n, v, d in gp) + "</div>"
                    + '<p class="muted">Datos del panel de rendimiento de Garmin Connect, tal como los publica Garmin. Las predicciones de carrera y el umbral de lactato '
                      'se basan en carrera, no en CrossFit.</p>') if gp else '<p class="muted">Aún no han llegado datos del panel de rendimiento de Garmin.</p>')
    tab_pro = ('<div class="grid">' + maxes + tests + "</div>" + longterm_card(root, today) + gp_card + '<div class="grid">' + skills + weight + "</div>" + wbc)

    # =================== montaje
    cert_ok = ready.get("status") == "ready"
    head = (f'<header class="top"><div><p class="eyebrow">Garmin Recovery</p><h1>{ddmm(today)}</h1></div>'
            f'<div class="chips"><span class="pill {"ok" if cert_ok else "warn"}">{"datos certificados" if cert_ok else "datos sin certificar"}</span>'
            f'<span class="chip">actualizado {hhmm(ready.get("verified_at") or result.get("generated_at"))}</span></div></header>')
    tabs = [("hoy", "Hoy", tab_hoy), ("recuperacion", "Recuperación", tab_rec), ("entrenos", "Entrenos", tab_ent), ("progreso", "Progreso", tab_pro)]
    nav = '<nav class="tabs" role="tablist">' + "".join(
        f'<a role="tab" href="#{k}" data-t="{k}">{esc(n)}</a>' for k, n, _ in tabs) + "</nav>"
    panes = "".join(f'<div class="pane" id="p-{k}" data-p="{k}">{body}</div>' for k, _, body in tabs)
    foot = ('<footer class="trace"><p><a href="informe_visual.html">Informe visual</a> · <a href="informe_completo.html">Informe completo</a> · '
            '<a href="panel_completo.html">Panel completo y sistema</a></p>'
            f'<p>Ciclo {esc(ready.get("cycle_id") or "—")} · comparaciones con tu propia serie de 28 días · no es un diagnóstico médico.</p></footer>')
    body = head + nav + panes + foot
    css = re.search(r"<style>(.*?)</style>", _VR_PAGE, re.S).group(1) + CSS
    return PAGE.replace("{{CSS}}", css).replace("{{TITLE}}", esc(f"Garmin Recovery · {ddmm(today)}")).replace("{{BODY}}", body)


CSS = """
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;flex-wrap:wrap}
.tabs{position:sticky;top:0;z-index:5;display:flex;gap:4px;padding:6px;background:var(--surface);border:1px solid var(--line);border-radius:14px;overflow-x:auto}
.tabs a{flex:1;text-align:center;padding:8px 10px;border-radius:10px;color:var(--text-2);text-decoration:none;font-weight:600;font-size:14px;white-space:nowrap}
.tabs a.on{background:var(--s1);color:#fff}.tabs a:focus-visible{outline:2px solid var(--s1);outline-offset:2px}
.pane{display:flex;flex-direction:column;gap:14px}.pane[hidden]{display:none}
.col{display:flex;flex-direction:column;gap:14px;min-width:0}
.big3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0}.big3 div{background:var(--surface-2);border-radius:12px;padding:8px 10px}
.big3 span{display:block;font-size:12px;color:var(--text-2)}.big3 b{font-size:22px;font-variant-numeric:tabular-nums}
.hero details{margin-top:6px;font-size:13px}.hero summary{cursor:pointer;color:var(--s1);font-weight:600}
.tk{margin:0 0 12px;font-size:14px;font-weight:600;padding:8px 12px;border-radius:10px;background:var(--surface-2)}.tk.ok{background:var(--ok-w)}.tk.bad,.tk.warn{background:var(--warn-w)}
.rr{padding:8px 0;border-top:1px solid var(--line)}.rr:first-of-type{border-top:0}
.rr-h{display:grid;grid-template-columns:1fr auto;gap:2px 10px;align-items:baseline}.rr-n{font-weight:600;font-size:14px}
.rr-v{font-size:20px;font-weight:700;text-align:right;font-variant-numeric:tabular-nums}.rr-v small{font-size:12px;color:var(--text-2);font-weight:500}
.rr-s{grid-column:1/-1;font-size:12px;font-weight:600}.rr-s.ok{color:var(--text-2)}.rr-s.good{color:var(--ok)}.rr-s.bad{color:var(--bad)}.rr-s.na{color:var(--text-3)}
.rr-t{position:relative;display:block;height:14px;margin:6px 0 4px;border-radius:7px;background:var(--surface-2)}.rr-t.empty{opacity:.5}
.rr-t em{position:absolute;top:0;bottom:0;background:var(--s1);opacity:.22;border-radius:7px}
.rr-m{position:absolute;top:1px;bottom:1px;width:2px;background:var(--text-3)}
.rr-d{position:absolute;top:50%;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;border:2px solid var(--surface)}
.rr-d.ok{background:var(--s1)}.rr-d.good{background:var(--ok)}.rr-d.bad{background:var(--bad)}.rr-d.na{background:var(--text-3)}
.rr-r{margin:0;font-size:11px;color:var(--text-3)}
.sw.band{background:var(--s1);opacity:.3}.sw.med{background:var(--text-3);width:3px}.sw.dot{background:var(--s1);border-radius:50%}
.ratio-t{position:relative;display:block;height:14px;border-radius:7px;background:var(--surface-2);overflow:hidden}
.ratio-t em{position:absolute;top:0;bottom:0;background:var(--ok);opacity:.18}.ratio-t b{position:absolute;top:0;bottom:0;width:2px;background:var(--text-3)}
.ratio-t i{position:absolute;inset:3px auto 3px 0;border-radius:5px}.ratio-l{display:flex;justify-content:space-between;font-size:11px;color:var(--text-3);margin-top:3px}
.chip-l{padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;background:var(--surface-2)}
.chip-l.l0{color:var(--ok)}.chip-l.l1{color:var(--s1)}.chip-l.l2{color:var(--warn)}.chip-l.l3{color:var(--bad)}
.lead{margin:0 0 10px;font-size:14px}
.sess-l{list-style:none;margin:0 0 12px;padding:0}.sess-l li{display:grid;grid-template-columns:3.2em 1fr auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
.day-h{margin:14px 0 2px;text-transform:capitalize}
.wks{display:flex;flex-direction:column;gap:8px}.wk{display:grid;grid-template-columns:4.2em 1fr 3.4em;gap:4px 8px;align-items:center;font-size:13px}
.wk-t{height:12px;border-radius:6px;background:var(--surface-2);overflow:hidden}.wk-t i{display:block;height:100%;background:var(--s1);border-radius:6px}
.wk-v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums}.wk-s{grid-column:2/-1;font-size:11px;color:var(--text-3)}
.met{padding:10px 0;border-top:1px solid var(--line)}.met:first-of-type{border-top:0}.met-h{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.met-h span:not(.pill){color:var(--text-3);font-size:12px;text-transform:capitalize}.met-r{margin:4px 0;font-size:13px;color:var(--text-2)}
.cmp{margin-top:6px;padding:8px 10px;border-radius:10px;background:var(--surface-2)}.cmp-h{margin:0 0 6px;font-size:12px;font-weight:600;color:var(--text-2)}
.cmp-g{display:grid;grid-template-columns:5.5em 1fr 1fr;gap:3px 8px;font-size:12px}.cmp-g b{font-size:11px;color:var(--text-3);text-transform:capitalize}
.cmp-g span:nth-child(3n+1){color:var(--text-3)}
.mx1{display:grid;grid-template-columns:1fr 120px 5.5em;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}.mx1:first-of-type{border-top:0}
.mx1 small{display:block;color:var(--text-3);font-size:12px}.mx1-v{text-align:right;font-weight:700;font-size:18px;font-variant-numeric:tabular-nums;white-space:nowrap}
.mx1-v span{display:block;font-size:12px}.mx1-v .up{color:var(--ok)}.mx1-v .down{color:var(--text-3)}
.spark{width:120px;height:40px}
.gp{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr));gap:8px}.gp-i{background:var(--surface-2);border-radius:12px;padding:10px 12px;display:flex;flex-direction:column;gap:2px}
.gp-i span{font-size:12px;color:var(--text-2)}.gp-i b{font-size:18px;font-variant-numeric:tabular-nums}.gp-i small{font-size:11px;color:var(--text-3)}
.alert{margin:0;padding:10px 14px;border-radius:12px;font-size:14px;border:1px solid var(--line)}.alert.warn{background:var(--warn-w)}.alert.info{background:var(--surface-2)}
.wk-t{display:flex}.wk-t i:first-child{border-radius:6px 0 0 6px}.wk-t i.est{background:var(--s1);opacity:.35;border-radius:0 6px 6px 0}.sw.s1b{background:var(--s1)}.sw.estb{background:var(--s1);opacity:.35}
em.due{color:var(--warn);font-style:normal;font-weight:600}.card details summary{cursor:pointer;color:var(--s1);font-weight:600;font-size:13px;margin-top:8px}.sk{padding:8px 0;border-top:1px solid var(--line)}.sk:first-of-type{border-top:0}.sk small{display:block;color:var(--text-3);font-size:12px}.sk p{margin:4px 0;font-size:13px}
@media (max-width:480px){.big3 b{font-size:18px}.big3 div{padding:6px 8px}.mx1{grid-template-columns:1fr 5.5em;grid-template-areas:"n v" "s s"}
.mx1>div:first-child{grid-area:n}.mx1 .spark{grid-area:s;width:100%;height:44px}.mx1-v{grid-area:v}}
@media print{.tabs{display:none}.pane[hidden]{display:flex}}
"""

PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#121211"><link rel="manifest" href="manifest.webmanifest"><link rel="apple-touch-icon" href="icon-180.png">
<title>{{TITLE}}</title><style>{{CSS}}</style></head><body><main>{{BODY}}</main>
<script>
(function(){var tabs=[].slice.call(document.querySelectorAll('.tabs a')),panes=[].slice.call(document.querySelectorAll('.pane'));
function show(k){var ok=panes.some(function(p){return p.dataset.p===k});if(!ok)k='hoy';
panes.forEach(function(p){p.hidden=p.dataset.p!==k});tabs.forEach(function(a){var on=a.dataset.t===k;a.classList.toggle('on',on);a.setAttribute('aria-selected',on)});}
window.addEventListener('hashchange',function(){show(location.hash.slice(1));});show(location.hash.slice(1));
if('serviceWorker' in navigator){navigator.serviceWorker.register('sw.js').catch(function(){});}})();
</script></body></html>"""
