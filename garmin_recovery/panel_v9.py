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
    return {"free": "libre", "TN": "TN", "MT": "MT", "post-TN": "post-TN"}.get(label)


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
    hi = max(w["srpe"] for w in weeks) or 1
    rows = ""
    for w in weeks:
        m = _date.fromisoformat(w["monday"])
        rows += (f'<div class="wk"><span class="wk-l">{m.day} {MES[m.month - 1]}</span><span class="wk-t"><i style="width:{w["srpe"] / hi * 100:.1f}%"></i></span>'
                 f'<span class="wk-v">{num(w["srpe"])}</span><span class="wk-s">{_ses(w["sessions"])} · {w["days"]} días entrenados · {w["hard"]} con RPE ≥ 8</span></div>')
    return f'<div class="wks">{rows}</div>'


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
        if ctx in ("TN", "MT"):
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
    tab_hoy = hero + '<div class="grid">' + normal_card + '<div class="col">' + sens_card + load_card + "</div></div>" + day_card

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
    tab_rec = '<div class="grid">' + models + sleep + "</div>" + hrv + '<div class="grid">' + shift_card + energy + "</div>"

    # =================== ENTRENOS
    weeks = complete_weeks(result.get("sessions_28d") or [], today)
    wk_tk = ""
    if len(weeks) >= 2:
        a, b = weeks[-1], weeks[-2]
        wk_tk = takeaway(f'Última semana completa: {a["sessions"]} sesiones y {num(a["srpe"])} de sRPE; la anterior, {b["sessions"]} y {num(b["srpe"])}.')

    def rest_label(r):
        return "desc." if r.get("rest_confirmed") else "—"
    train_load = card("¿Cómo se reparte mi carga?",
                      day_bars(trend[-14:], "srpe", label=rest_label, h=170, w=420)
                      + "<h3>Semanas completas (lunes a domingo)</h3>" + wk_tk + _week_bars(weeks),
                      "sRPE = RPE × minutos (solo sesiones con RPE) · «desc.» descanso confirmado · «—» sin registro")
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
    tab_pro = '<div class="grid">' + maxes + skills + "</div>" + '<div class="grid">' + weight + wbc + "</div>"

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
.spark{width:120px;height:40px}.sk{padding:8px 0;border-top:1px solid var(--line)}.sk:first-of-type{border-top:0}.sk small{display:block;color:var(--text-3);font-size:12px}.sk p{margin:4px 0;font-size:13px}
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
