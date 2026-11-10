"""Informe visual del ciclo (V8.18): una página ordenada con gráficas, sensaciones y decisión.

Solo usa cifras que ya están en los archivos del ciclo (readiness_v3, recovery_assessment, advanced_analytics,
garmin_*, crossfit_insights, shift_calendar, report_ready). No calcula modelos nuevos ni inventa recomendaciones:
la orientación sale de `decision`. Gráficas en SVG en línea, sin librerías ni red, en claro y oscuro.
"""
from __future__ import annotations

import html
import json
from datetime import date as _date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")

SLOTS = {"0830": "Cierre matinal", "1645": "Informe de tarde", "2245": "Cierre nocturno"}
ZONE = {"green": ("verde", "ok"), "yellow": ("ámbar", "warn"), "red": ("rojo", "bad")}
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


# ---------------------------------------------------------------- utilidades

def _load(root: Path, name: str) -> dict:
    try:
        d = json.loads((root / name).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _day(days, key: str) -> dict:
    if isinstance(days, dict):
        v = days.get(key)
        return v if isinstance(v, dict) else {}
    for d in days or []:
        if isinstance(d, dict) and str(d.get("date") or d.get("calendarDate") or "")[:10] == key:
            return d
    return {}


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def num(v, dec: int = 0) -> str:
    if not isinstance(v, (int, float)) or isinstance(v, bool) or v != v:
        return "—"
    s = f"{v:,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    if s.lstrip("-").strip("0,.") == "":
        s = s.lstrip("-")  # sin «-0»
    return s[:-2] if dec and s.endswith(",0") and dec == 1 else s


def ddmm(s) -> str:
    try:
        d = _date.fromisoformat(str(s)[:10])
    except ValueError:
        return esc(s)
    return f"{DIA[d.weekday()]} {d.day} {MES[d.month - 1]}"


def hhmm(s) -> str:
    t = str(s or "")
    return esc(t[11:16]) if len(t) >= 16 else "—"


def zone_pill(zone, text=None) -> str:
    z = ZONE.get(zone or "", ("—", "na"))
    return f'<span class="pill {z[1]}">{esc(text or z[0])}</span>'


def _iso(s) -> str | None:
    """Fecha AAAA-MM-DD válida (acepta «2026-11-10T00:00»)."""
    t = str(s or "")[:10]
    try:
        _date.fromisoformat(t)
    except ValueError:
        return None
    return t


def _ms_local(ms) -> datetime | None:
    try:
        return datetime.fromtimestamp(ms / 1000, tz=TZ)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _bb_points(values) -> list[tuple[float, float]]:
    out = []
    for e in values or []:
        if isinstance(e, (list, tuple)) and len(e) >= 2 and _fnum(e[0]) is not None and _fnum(e[1]) is not None:
            out.append((e[0], e[1]))
    return out


def _fnum(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v else None


# ---------------------------------------------------------------- gráficas SVG

def bars_h(items: list[tuple[str, float | None, str]], vmax: float = 100) -> str:
    """Barras horizontales etiquetadas: (nombre, valor, clase de color)."""
    rows = ""
    for name, v, cls in items:
        w = 0 if _fnum(v) is None else max(0.0, min(1.0, v / vmax)) * 100
        rows += (f'<div class="hb"><span class="hb-n">{esc(name)}</span><span class="hb-t">'
                 f'<i class="{cls}" style="width:{w:.1f}%"></i></span><b class="hb-v">{num(v)}</b></div>')
    return f'<div class="hbars">{rows}</div>'


def stacked(parts: list[tuple[str, float | None, str]]) -> str:
    """Barra apilada (fases de sueño) con leyenda en minutos."""
    vals = [(n, v, c) for n, v, c in parts if _fnum(v)]
    tot = sum(v for _, v, _ in vals)
    if not tot:
        return '<p class="muted">Fases no disponibles para este episodio.</p>'
    seg = "".join(f'<i class="{c}" style="width:{v / tot * 100:.2f}%" title="{esc(n)}"></i>' for n, v, c in vals)
    leg = "".join(f'<span><i class="sw {c}"></i>{esc(n)} <b>{num(v)} min</b> · {num(v / tot * 100)} %</span>' for n, v, c in vals)
    return f'<div class="stack">{seg}</div><div class="legend">{leg}</div>'


def line_chart(rows: list[dict], series: list[tuple[str, str, str]], band: tuple[str, str] | None = None,
               unit: str = "", h: int = 150, ref: float | None = None, ref_label: str = "") -> str:
    """Línea por días (eje x = fecha). series: (clave, nombre, clase)."""
    pts = [r for r in rows if any(_fnum(r.get(k)) is not None for k, _, _ in series)]
    if len(pts) < 2:
        return '<p class="muted">Sin datos suficientes.</p>'
    W, L, R, T, B = 640, 38, 46, 10, 22
    vals = [r[k] for r in pts for k, _, _ in series if _fnum(r.get(k)) is not None]
    if band:
        vals += [r[x] for r in pts for x in band if _fnum(r.get(x)) is not None]
    if ref is not None:
        vals.append(ref)
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = lo - pad, hi + pad
    rows = [dict(r, date=_iso(r.get("date"))) for r in rows if _iso(r.get("date"))]
    pts = [r for r in rows if any(_fnum(r.get(k)) is not None for k, _, _ in series)]
    if len(pts) < 2:
        return '<p class="muted">Sin datos suficientes.</p>'
    n = len(rows)
    X = lambda i: L + (W - L - R) * (i / max(1, n - 1))  # noqa: E731
    Y = lambda v: T + (h - T - B) * (1 - (v - lo) / (hi - lo))  # noqa: E731
    idx = {r["date"]: i for i, r in enumerate(rows)}
    g = ""
    for t in (lo + (hi - lo) * f for f in (0.15, 0.5, 0.85)):
        g += f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}"/><text class="tick" x="{L - 6}" y="{Y(t) + 4:.1f}" text-anchor="end">{num(t)}</text>'
    if band:
        a, b = band
        bp = [r for r in rows if _fnum(r.get(a)) is not None and _fnum(r.get(b)) is not None]
        if len(bp) >= 2:
            up = " ".join(f"{X(idx[r['date']]):.1f},{Y(r[b]):.1f}" for r in bp)
            dn = " ".join(f"{X(idx[r['date']]):.1f},{Y(r[a]):.1f}" for r in reversed(bp))
            g += f'<polygon class="band" points="{up} {dn}"/>'
    if ref is not None:
        g += (f'<line class="ref" x1="{L}" x2="{W - R}" y1="{Y(ref):.1f}" y2="{Y(ref):.1f}"/>'
              f'<text class="tick" x="{W - R + 4}" y="{Y(ref) + 4:.1f}">{esc(ref_label)}</text>')
    for k, _name, cls in series:
        p = [r for r in rows if _fnum(r.get(k)) is not None]
        if len(p) < 2:
            continue
        d = " ".join(f"{X(idx[r['date']]):.1f},{Y(r[k]):.1f}" for r in p)
        g += f'<polyline class="ln {cls}" points="{d}"/>'
        lr = p[-1]
        g += (f'<circle class="dot {cls}" cx="{X(idx[lr["date"]]):.1f}" cy="{Y(lr[k]):.1f}" r="3.5"/>'
              f'<text class="end {cls}" x="{X(idx[lr["date"]]) + 6:.1f}" y="{Y(lr[k]) + 4:.1f}">{num(lr[k])}{esc(unit)}</text>')
    step = max(1, n // 6)
    for i, r in enumerate(rows):
        if (n - 1 - i) % step == 0:
            dd = _date.fromisoformat(r["date"])
            g += f'<text class="tick" x="{X(i):.1f}" y="{h - 6}" text-anchor="middle">{dd.day} {MES[dd.month - 1]}</text>'
    leg = "".join(f'<span><i class="sw {c}"></i>{esc(nm)}</span>' for _, nm, c in series)
    return f'<svg class="chart" viewBox="0 0 {W} {h}" role="img">{g}</svg><div class="legend">{leg}</div>'


def day_bars(rows: list[dict], key: str, h: int = 140, label=None, cls_fn=None, ref: float | None = None,
             ref_label: str = "") -> str:
    """Barras por día con etiqueta debajo; label(r) devuelve el texto cuando no hay valor (p. ej. «desc.»)."""
    rows = [dict(r, date=_iso(r.get("date"))) for r in rows if _iso(r.get("date"))]
    if not rows:
        return '<p class="muted">Sin datos.</p>'
    W, L, R, T, B = 640, 8, 40, 16, 34
    vals = [r[key] for r in rows if (_fnum(r.get(key)) or 0) > 0]
    hi = max(vals + ([ref] if ref else []) + [1])
    n = len(rows)
    bw = (W - L - R) / n
    g = ""
    if ref is not None:
        y = T + (h - T - B) * (1 - ref / hi)
        g += (f'<line class="ref" x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}"/>'
              f'<text class="tick" x="{W - R + 4}" y="{y + 4:.1f}">{esc(ref_label)}</text>')
    for i, r in enumerate(rows):
        x = L + i * bw
        v = _fnum(r.get(key))
        dd = _date.fromisoformat(r["date"])
        if v and v > 0:
            bh = (h - T - B) * v / hi
            c = cls_fn(r) if cls_fn else "s1"
            g += (f'<rect class="bar {c}" x="{x + bw * 0.15:.1f}" y="{h - B - bh:.1f}" width="{bw * 0.7:.1f}" height="{bh:.1f}" rx="3"/>'
                  f'<text class="val" x="{x + bw / 2:.1f}" y="{h - B - bh - 4:.1f}" text-anchor="middle">{num(v, 1 if v < 20 else 0)}</text>')
        else:
            g += f'<text class="empty" x="{x + bw / 2:.1f}" y="{h - B - 4}" text-anchor="middle">{esc(label(r) if label else "—")}</text>'
        g += (f'<text class="tick" x="{x + bw / 2:.1f}" y="{h - 18}" text-anchor="middle">{DIA[dd.weekday()]}</text>'
              f'<text class="tick" x="{x + bw / 2:.1f}" y="{h - 5}" text-anchor="middle">{dd.day}</text>')
    return f'<svg class="chart" viewBox="0 0 {W} {h}" role="img">{g}</svg>'


def range_bars(items: list[tuple[str, float | None, float | None, float | None]]) -> str:
    """Valor frente a un rango objetivo (balance de carga Garmin)."""
    vmax = max([x for it in items for x in it[1:] if _fnum(x)] + [1]) * 1.1
    rows = ""
    for name, v, a, b in items:
        band = (f'<em style="left:{a / vmax * 100:.1f}%;width:{(b - a) / vmax * 100:.1f}%"></em>'
                if _fnum(a) is not None and _fnum(b) is not None else "")
        over = _fnum(v) is not None and _fnum(b) is not None and v > b
        w = 0 if _fnum(v) is None else v / vmax * 100
        rows += (f'<div class="hb"><span class="hb-n">{esc(name)}</span><span class="hb-t rng">{band}'
                 f'<i class="{"bad" if over else "s1"}" style="width:{w:.1f}%"></i></span><b class="hb-v">{num(v)}</b></div>'
                 f'<p class="hb-sub">objetivo {num(a)}–{num(b)}{" · por encima" if over else ""}</p>')
    return f'<div class="hbars">{rows}</div>'


def bb_curve(values: list) -> str:
    pts = _bb_points(values)
    if len(pts) < 2:
        return '<p class="muted">Sin curva de Body Battery.</p>'
    W, h, L, R, T, B = 640, 120, 30, 40, 10, 22
    t0, t1 = pts[0][0], pts[-1][0]
    X = lambda t: L + (W - L - R) * ((t - t0) / max(1, t1 - t0))  # noqa: E731
    Y = lambda v: T + (h - T - B) * (1 - v / 100)  # noqa: E731
    line = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in pts)
    area = f"{X(t0):.1f},{Y(0):.1f} {line} {X(t1):.1f},{Y(0):.1f}"
    g = "".join(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                f'<text class="tick" x="{L - 6}" y="{Y(v) + 4:.1f}" text-anchor="end">{v}</text>' for v in (25, 50, 75))
    g += f'<polygon class="area" points="{area}"/><polyline class="ln s1" points="{line}"/>'
    for t, v in pts:
        dt = _ms_local(t) if t > 1e11 else None
        hh = dt.strftime("%H:%M") if dt else ""
        g += f'<circle class="dot s1" cx="{X(t):.1f}" cy="{Y(v):.1f}" r="3"/>'
        if (t, v) in (pts[0], pts[-1]) or v == max(p[1] for p in pts):
            g += f'<text class="val" x="{X(t):.1f}" y="{Y(v) - 7:.1f}" text-anchor="middle">{v}</text>'
            g += f'<text class="tick" x="{X(t):.1f}" y="{h - 5}" text-anchor="middle">{hh}</text>'
    return f'<svg class="chart" viewBox="0 0 {W} {h}" role="img">{g}</svg>'


# ---------------------------------------------------------------- datos

def _sessions_today(cf: dict, rv3: dict, today: str) -> list[dict]:
    blocks: dict[str, list] = {}
    for a in cf.get("activities") or []:
        if isinstance(a, dict) and a.get("date") == today:
            blocks[str(a.get("activity_id"))] = [b for b in a.get("manual_blocks") or [] if isinstance(b, dict)]
    out = []
    for s in sorted([s for s in rv3.get("recent_sessions") or [] if s.get("date") == today and not s.get("removed")],
                    key=lambda s: s.get("start_local") or ""):
        bl = blocks.get(str(s.get("id"))) or []
        out.append({**s, "notes": [b.get("notes") for b in bl if b.get("notes")],
                    "sensations": [b.get("sensations") for b in bl if b.get("sensations")]})
    return out


def _sensations(cf: dict, today: str, days: int = 28) -> list[dict]:
    since = (_date.fromisoformat(today) - timedelta(days=days - 1)).isoformat()
    out, seen = [], set()
    for a in cf.get("activities") or []:
        if not isinstance(a, dict) or (a.get("date") or "") < since:
            continue
        for b in a.get("manual_blocks") or []:
            s = (b or {}).get("sensations")
            if s and (a["date"], s) not in seen:
                seen.add((a["date"], s))
                out.append({"date": a["date"], "text": s, "activity": b.get("activity"), "rpe": b.get("rpe")})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def _shift(cal: dict, d: str) -> str | None:
    v = (cal.get("days") or {}).get(d) if isinstance(cal.get("days"), dict) else None
    return v if isinstance(v, str) and v else None


# ---------------------------------------------------------------- página

def build(root: str | Path = ".") -> str:
    root = Path(root)
    rv3 = _load(root, "app/readiness_v3.json")
    today = str(rv3.get("date") or "")[:10]
    if not today:
        raise ValueError("readiness_v3.json sin fecha")
    ready = _load(root, "report_ready.json")
    ra, aa = _load(root, "recovery_assessment.json"), _load(root, "advanced_analytics.json")
    ext = _day(_load(root, "garmin_extended.json").get("days"), today)
    bb = _day(_load(root, "garmin_body_battery.json").get("days"), today)
    st = _day(_load(root, "garmin_stress.json").get("days"), today)
    hr = _load(root, "garmin_heart_rate.json")
    cf, cal = _load(root, "crossfit_insights.json"), _load(root, "shift_calendar.json")
    dec = rv3.get("decision") or {}
    gd = dec.get("guidance") or {}
    trend = [dict(r, date=_iso(r.get("date"))) for r in rv3.get("trend_28d") or [] if isinstance(r, dict) and _iso(r.get("date"))]
    tday = next((r for r in trend if r["date"] == today), {})
    cur, base = ra.get("current") or {}, ra.get("baseline_28d") or {}
    hyb, pri = aa.get("readiness_hybrid") or {}, aa.get("personal_recovery_index") or {}
    tr = ext.get("training_readiness") or {}
    sd = ext.get("sleep_detail") or {}
    cycle = str(ready.get("cycle_id") or "")
    slot = SLOTS.get(cycle[-4:], "Informe")
    load = rv3.get("load") or {}
    sess = _sessions_today(cf, rv3, today)
    srpe_today = sum(s.get("srpe") or 0 for s in sess)
    rpes = [s["rpe"] for s in sess if _fnum(s.get("rpe")) is not None]

    # ---------- cabecera
    cert_ok = ready.get("status") == "ready"
    head = (f'<header class="top"><p class="eyebrow">Garmin Recovery · {esc(slot)}</p>'
            f'<h1>{ddmm(today)}</h1><div class="chips">'
            f'<span class="pill {"ok" if cert_ok else "warn"}">Ciclo {"certificado" if cert_ok else esc(ready.get("status") or "sin certificar")}</span>'
            f'<span class="chip">{esc(cycle or "—")}</span><span class="chip">verificado {hhmm(ready.get("verified_at"))}</span></div></header>')

    # ---------- decisión
    zone = dec.get("zone")
    decision = (f'<section class="card hero z-{ZONE.get(zone or "", ("", "na"))[1]}"><div class="hero-top">'
                f'<div><p class="eyebrow">Decisión del día</p><h2>{esc(gd.get("label") or "—")}</h2></div>{zone_pill(zone)}</div>'
                f'<div class="kv"><span>RPE máximo <b>{num(gd.get("rpe_max"))}</b></span><span>Volumen <b>{esc(gd.get("volume") or "—")}</b></span>'
                f'<span>Acuerdo entre modelos <b>{esc(dec.get("agreement") or "—")}</b></span></div>'
                f'<p>{esc(gd.get("text") or "")}</p>'
                + ("<ul>" + "".join(f"<li>{esc(t)}</li>" for t in dec.get("crossfit") or []) + "</ul>" if dec.get("crossfit") else "")
                + '<p class="muted">La decisión es la más prudente entre el modelo oficial, el híbrido y el experimental. No es un diagnóstico médico.</p></section>')

    # ---------- tiles
    hrv, hrv_med = _fnum(cur.get("hrv_ms")), _fnum((base.get("hrv_ms") or {}).get("median"))
    tiles = [
        ("Recuperación oficial", f'{num(tday.get("v2_score"))}<small>/100</small>', f'confianza {esc({"high": "alta", "medium": "media", "low": "baja"}.get(str(ra.get("confidence")), ra.get("confidence") if isinstance(ra.get("confidence"), str) else "—"))}'),
        ("Híbrido Garmin + local", f'{num(hyb.get("score"))}<small>/100</small>', f'Garmin {num(hyb.get("garmin_score"))} · local {num(hyb.get("local_score"))}'),
        ("Sueño", f'{num(cur.get("sleep_hours"), 1)}<small> h</small>', f'puntuación {num(cur.get("sleep_score"))} · mediana {num((base.get("sleep_hours") or {}).get("median"), 1)} h'),
        ("HRV", f'{num(hrv)}<small> ms</small>', f'mediana 28 d {num(hrv_med)} ms'),
        ("Carga de hoy (sRPE)", f'{num(srpe_today)}', f'{len(sess)} sesiones · RPE medio {num(sum(rpes) / len(rpes), 1) if rpes else "—"}'),
    ]
    tiles_html = '<section class="tiles">' + "".join(
        f'<div class="tile"><span class="t-l">{esc(a)}</span><span class="t-v">{b}</span><span class="t-s">{c}</span></div>' for a, b, c in tiles) + "</section>"

    # ---------- modelos
    def zc(score):
        return "ok" if (score or 0) >= 70 else "warn" if (score or 0) >= 50 else "bad"
    models = bars_h([("Oficial", tday.get("v2_score"), zc(tday.get("v2_score"))), ("Híbrido", hyb.get("score"), zc(hyb.get("score"))),
                     ("Experimental V3", (rv3.get("readiness") or {}).get("score"), zc((rv3.get("readiness") or {}).get("score"))),
                     ("Índice personal", pri.get("score"), "s2"), ("Garmin Readiness", tr.get("score"), "s2")])
    rt = ext.get("recovery_time") or {}
    models_card = (f'<section class="card"><h2>Recuperación por modelo</h2><p class="sub">0–100 · los dos primeros deciden; el resto es referencia</p>{models}'
                   f'<p class="muted">Tiempo de recuperación Garmin: {num(rt.get("hours"), 1)} h (actualizado a las {hhmm(tr.get("timestamp_local"))}; '
                   'no cuenta las sesiones posteriores).</p></section>')

    # ---------- sueño
    sleep_rows = trend[-14:]
    sleep_card = ('<section class="card"><h2>Sueño</h2>'
                  f'<p class="sub">{hhmm(cur.get("sleep_start_local"))} → {hhmm(cur.get("sleep_end_local"))} · '
                  f'{num(cur.get("sleep_hours"), 1)} h · puntuación {num(cur.get("sleep_score"))}</p>'
                  + stacked([("Profundo", sd.get("deep_minutes"), "c-deep"), ("Ligero", sd.get("light_minutes"), "c-light"),
                             ("REM", sd.get("rem_minutes"), "c-rem"), ("Despierto", sd.get("awake_minutes"), "c-awake")])
                  + '<h3>Horas por noche, 14 días</h3>'
                  + day_bars(sleep_rows, "sleep_hours", ref=_fnum((base.get("sleep_hours") or {}).get("median")), ref_label="mediana",
                             cls_fn=lambda r: "warn" if (r.get("sleep_score") or 100) < 60 else "s1")
                  + '<p class="muted">Barras en ámbar: puntuación de sueño por debajo de 60.</p></section>')

    # ---------- HRV y FC
    roll = hr.get("rolling") or {}
    fct = ('<table class="tbl"><thead><tr><th></th><th>Hoy</th><th>3 d</th><th>7 d</th><th>28 d</th></tr></thead><tbody>'
           f'<tr><th>FC nocturna</th><td>{num(cur.get("night_hr"), 1)}</td>'
           + "".join(f'<td>{num((roll.get(k) or {}).get("nighttime_avg_hr"), 1)}</td>' for k in ("3d", "7d", "28d"))
           + f'</tr><tr><th>FC en reposo</th><td>{num(cur.get("resting_hr"))}</td><td>—</td>'
           f'<td>{num((base.get("resting_hr") or {}).get("last7_mean"), 1)}</td><td>{num((base.get("resting_hr") or {}).get("median"), 1)}</td></tr>'
           '</tbody></table><p class="muted">FC en reposo a 28 días = mediana; a 7 días = media. La FC diurna de hoy es parcial y no se usa como reposo.</p>')
    hrv_card = ('<section class="card"><h2>HRV y frecuencia cardiaca</h2><p class="sub">28 días · la banda es tu rango normal de HRV</p>'
                + line_chart(trend, [("hrv_ms", "HRV (ms)", "s1"), ("hrv_rolling_ms", "Media 7 d", "s3")], band=("hrv_low_ms", "hrv_high_ms"))
                + '<h3>FC en reposo y nocturna</h3>'
                + line_chart(trend, [("resting_hr", "FC reposo", "s2"), ("night_hr", "FC nocturna", "s4")], unit="", h=130)
                + fct + "</section>")

    # ---------- estrés y body battery
    vals = bb.get("bodyBatteryValuesArray") or []
    bbp = _bb_points(vals)
    last_bb = bbp[-1][1] if bbp else None
    last_dt = _ms_local(bbp[-1][0]) if bbp else None
    bb_card = ('<section class="card"><h2>Estrés y Body Battery</h2>'
               f'<div class="kv"><span>Estrés medio <b>{num(st.get("avgStressLevel"))}</b></span><span>máximo <b>{num(st.get("maxStressLevel"))}</b></span>'
               f'<span>Body Battery +{num(bb.get("charged"))} / −{num(bb.get("drained"))}</span>'
               f'<span>último <b>{num(last_bb)}</b> a las {last_dt.strftime("%H:%M") if last_dt else "—"}</span></div>'
               + bb_curve(vals) + '<p class="muted">Última medición sincronizada, no una lectura en directo.</p></section>')

    # ---------- carga
    def label(r):
        return "desc." if r.get("rest_confirmed") else "—"
    ts = ext.get("training_status") or {}

    def tsv(suffix):
        return next((v for k, v in ts.items() if k.endswith(suffix)), None)
    lb = [("Aeróbica baja", tsv("monthlyLoadAerobicLow"), tsv("monthlyLoadAerobicLowTargetMin"), tsv("monthlyLoadAerobicLowTargetMax")),
          ("Aeróbica alta", tsv("monthlyLoadAerobicHigh"), tsv("monthlyLoadAerobicHighTargetMin"), tsv("monthlyLoadAerobicHighTargetMax")),
          ("Anaeróbica", tsv("monthlyLoadAnaerobic"), tsv("monthlyLoadAnaerobicTargetMin"), tsv("monthlyLoadAnaerobicTargetMax"))]
    load_card = ('<section class="card"><h2>Carga</h2><p class="sub">sRPE diario (RPE × minutos) · «desc.» = descanso confirmado · «—» = sin registro</p>'
                 + day_bars(trend[-14:], "srpe", label=label, h=150)
                 + f'<div class="kv"><span>7 días <b>{num(load.get("week_srpe"))}</b> sRPE</span><span>{num(load.get("week_sessions"))} sesiones</span>'
                 f'<span>ACWR <b>{num(load.get("acwr"), 2)}</b></span><span>monotonía <b>{num(load.get("monotony"), 2)}</b></span></div>'
                 + (('<h3>Balance de carga Garmin, 4 semanas</h3>' + range_bars(lb)) if any(_fnum(x[1]) for x in lb) else "")
                 + '</section>')

    # ---------- entrenamiento de hoy
    srows = ""
    for s in sess:
        rp = s.get("rpe")
        pill = (f'<span class="pill {"bad" if rp >= 9 else "warn" if rp >= 7.5 else "ok"}">RPE {num(rp, 1)}</span>'
                if _fnum(rp) is not None else '<span class="pill na">sin RPE</span>')
        notes = "".join(f"<p>{esc(n)}</p>" for n in s.get("notes") or [])
        sens = "".join(f'<p class="sens">💬 {esc(x)}</p>' for x in s.get("sensations") or [])
        srows += (f'<details class="sess"><summary><span class="s-t">{hhmm(s.get("start_local"))}</span>'
                  f'<span class="s-n">{esc(s.get("label") or s.get("name"))}<small>{num(s.get("duration_min"), 1)} min · FC {num(s.get("avg_hr"))}/{num(s.get("max_hr"))} · '
                  f'sRPE {num(s.get("srpe"))}</small></span>{pill}</summary><div class="s-b">{sens}{notes or "<p class=muted>Sin detalle dictado.</p>"}</div></details>')
    today_card = ('<section class="card"><h2>Entrenamiento de hoy</h2>'
                  f'<p class="sub">{len(sess)} sesiones · {num(sum(s.get("duration_min") or 0 for s in sess), 1)} min grabados · toca una sesión para ver el detalle</p>'
                  + (srows or '<p class="muted">Sin sesiones registradas hoy.</p>') + "</section>")

    # ---------- sensaciones: encuesta diaria completa, índice de bienestar y lectura descriptiva
    from . import sensations as _sn
    survey = _sn.load(root)
    win = _sn.window(survey, today, 14)
    todays = _sn.by_date(survey, today).get(today)
    an = _sn.analysis(survey, today, trend, zone)
    lvl_cls = ["l0", "l1", "l2", "l3"]

    def _ans(e, k, labels):
        lv = _sn.level(e, k)
        return (lvl_cls[lv], labels[lv]) if lv is not None else ("na", "—")
    if todays:
        chips = "".join(f'<div class="sv"><span class="sv-q">{esc(name)}</span><span class="sv-a {_ans(todays, k, labels)[0]}">'
                        f'{esc(_ans(todays, k, labels)[1])}</span></div>' for k, name, labels in _sn.ITEMS)
        zones_html = ('<p class="zones">📍 ' + ", ".join(esc(z) for z in todays.get("zonas") or []) + '</p>') if todays.get("zonas") else ""
        idx = an.get("today")
        idx_html = (f'<div class="wb"><span class="wb-v {"ok" if idx >= 70 else "warn" if idx >= 50 else "bad"}">{idx}</span>'
                    f'<span class="wb-l">índice de bienestar<small>0–100 · media 14 días {num(an.get("mean14"))}</small></span></div>'
                    if idx is not None else "")
        survey_html = (f'<p class="sub">Encuesta de hoy{(" · " + esc(todays.get("time"))) if todays.get("time") else ""}</p>'
                       + idx_html + f'<div class="svs">{chips}</div>' + zones_html
                       + (f'<p class="sens">💬 {esc(todays.get("note"))}</p>' if todays.get("note") else ""))
    else:
        survey_html = ('<p class="hint">Hoy no has respondido la encuesta. Te la mando cuando me dictes el entreno, '
                       'o pídemela en el chat («encuesta de sensaciones»).</p>')
    obs = an.get("observations") or []
    lr = an.get("load_relation")
    reading = ""
    if obs or lr:
        reading = ('<h3>Lectura</h3><ul class="obs">'
                   + "".join(f'<li class="o-{esc(o["level"])}">{esc(o["text"])}</li>' for o in obs)
                   + (f'<li class="o-info">Tras días de carga alta (sRPE &gt; {num(lr["threshold_srpe"])}) tu bienestar medio es '
                      f'{lr["after_high"]}; tras días más suaves, {lr["after_low"]} ({lr["pairs"]} días). Es descriptivo, no prueba causa.</li>' if lr else "")
                   + '</ul>')
    elif todays:
        reading = '<p class="muted">Con más días de encuesta aparecerán tendencias y la relación con tu carga (a partir de 7 días).</p>'
    grid = ""
    if any(r[k] is not None for r in win for k, _, _ in _sn.ITEMS):
        head_row = "".join(f'<span class="mx-d">{DIA[_date.fromisoformat(r["date"]).weekday()][0]}<br>{_date.fromisoformat(r["date"]).day}</span>' for r in win)
        rows_m = "".join(f'<span class="mx-q">{esc(name)}</span>' + "".join(
            f'<span class="mx-c {lvl_cls[r[k]] if r[k] is not None else "na"}" title="{esc(labels[r[k]] if r[k] is not None else "sin encuesta")}"></span>'
            for r in win) for k, name, labels in _sn.ITEMS)
        grid = ('<h3>Últimos 14 días</h3><div class="mx" style="grid-template-columns:7.5em repeat(14,1fr)"><span></span>'
                + head_row + rows_m + '</div><div class="legend"><span><i class="sw l0"></i>bien</span><span><i class="sw l1"></i>leve</span>'
                '<span><i class="sw l2"></i>moderado</span><span><i class="sw l3"></i>alto</span><span><i class="sw na"></i>sin encuesta</span></div>')
    bd_s = _sn.by_date(survey, today)
    idx_rows = [{"date": r["date"], "wb": _sn.wellbeing(bd_s.get(r["date"])), "rec": r.get("v2_score")} for r in trend]
    idx_chart = ""
    if sum(1 for r in idx_rows if r["wb"] is not None) >= 2:
        idx_chart = ('<h3>Bienestar frente a recuperación oficial, 28 días</h3>'
                     + line_chart(idx_rows, [("wb", "Bienestar (encuesta)", "s4"), ("rec", "Recuperación oficial", "s1")], h=140))
    sens = _sensations(cf, today)
    sens_rows = "".join(f'<li><span class="s-d">{ddmm(x["date"])}</span><span>{esc(x["text"])}'
                        f'<small>{esc(x.get("activity") or "")}{(" · RPE " + num(x["rpe"], 1)) if _fnum(x.get("rpe")) is not None else ""}</small></span></li>'
                        for x in sens[:8])
    sens_card = ('<section class="card"><h2>Sensaciones</h2><p class="sub">lo que tú dices, sin modelos · no entra en la puntuación de recuperación</p>'
                 + survey_html + reading + grid + idx_chart
                 + (f'<h3>Dictadas con el entreno · 28 días</h3><ul class="sens-l">{sens_rows}</ul>' if sens_rows else "")
                 + "</section>")

    # ---------- turnos
    t = _date.fromisoformat(today)
    hours = cal.get("shift_hours") if isinstance(cal.get("shift_hours"), dict) else {}

    def sh(d):
        code = _shift(cal, d.isoformat())
        if not code:
            return '<span class="chip">libre</span>'
        hh = hours.get(code) if isinstance(hours.get(code), dict) else {}
        return f'<span class="chip strong">{esc(code)} {esc(hh.get("start", ""))}–{esc(hh.get("end", ""))}</span>'
    shifts = ('<section class="card"><h2>Turnos</h2><div class="shifts">'
              + "".join(f'<div><span class="s-d">{lbl}</span>{sh(t + timedelta(days=i))}<small>{ddmm((t + timedelta(days=i)).isoformat())}</small></div>'
                        for i, lbl in enumerate(("Hoy", "Mañana", "Pasado")))
              + '</div><p class="muted">La decisión de mañana se recalcula tras el próximo sueño confirmado.</p></section>')

    # ---------- traza
    ch = ready.get("chain") or {}
    trace = ('<footer class="trace"><p>Ciclo ' + esc(cycle) + ' · certificado ' + esc(ready.get("status") or "—") + ' a las '
             + hhmm(ready.get("verified_at")) + ' · runs ' + " / ".join(esc((ch.get(k) or {}).get("id")) for k in ("sync", "heart", "advanced", "crossfit"))
             + '</p><p><a href="./">Panel</a> · <a href="informe_completo.html">Informe completo en texto</a></p>'
             '<p>Solo cifras de los archivos del ciclo; sin causalidad entre comparaciones. No es un diagnóstico médico.</p></footer>')

    body = (head + decision + tiles_html + '<div class="grid">' + models_card + sleep_card + "</div>" + hrv_card
            + '<div class="grid">' + bb_card + load_card + "</div>" + today_card + '<div class="grid">' + sens_card + shifts + "</div>" + trace)
    return PAGE.replace("{{TITLE}}", esc(f"{slot} · {ddmm(today)}")).replace("{{BODY}}", body)


PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{{TITLE}}</title><style>
:root{color-scheme:light;--bg:#f6f6f4;--surface:#fcfcfb;--surface-2:#f0efec;--line:#e4e3df;--text:#0b0b0b;--text-2:#52514e;--text-3:#73726c;
--s1:#2a78d6;--s2:#8a63d2;--s3:#0f8a7e;--s4:#d0642c;--ok:#1f8a4c;--warn:#b7791f;--bad:#c2410c;--ok-w:#e3f3e9;--warn-w:#fbf0dc;--bad-w:#fbe5dc;
--deep:#1e4fa0;--light:#7fb0ea;--rem:#8a63d2;--awake:#e0a54a}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--surface-2:#242422;--line:#30302d;--text:#f2f2ef;--text-2:#b9b8b2;--text-3:#8f8e88;
--s1:#5fa0f0;--s2:#a98bea;--s3:#38b8a8;--s4:#ef8a52;--ok:#4cc27c;--warn:#e3a645;--bad:#f07a4a;--ok-w:#18301f;--warn-w:#33280f;--bad-w:#3a1d12;
--deep:#3f78d0;--light:#8cbcf0;--rem:#a98bea;--awake:#e8b25e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:960px;margin:0 auto;padding:16px max(16px,env(safe-area-inset-left)) 40px max(16px,env(safe-area-inset-right));display:flex;flex-direction:column;gap:14px}
h1{margin:2px 0 8px;font-size:28px;line-height:1.15;text-transform:capitalize}h2{margin:0 0 2px;font-size:18px}h3{margin:16px 0 6px;font-size:14px;color:var(--text-2)}
.eyebrow{margin:0;font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.sub{margin:0 0 10px;color:var(--text-2);font-size:13px}.muted{color:var(--text-3);font-size:12px;margin:8px 0 0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px;min-width:0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:14px}
.chips{display:flex;flex-wrap:wrap;gap:6px}.chip{padding:2px 10px;border-radius:999px;background:var(--surface-2);font-size:12px;color:var(--text-2)}
.chip.strong{color:var(--text);font-weight:600}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;white-space:nowrap}
.pill.ok{background:var(--ok-w);color:var(--ok)}.pill.warn{background:var(--warn-w);color:var(--warn)}.pill.bad{background:var(--bad-w);color:var(--bad)}.pill.na{background:var(--surface-2);color:var(--text-2)}
.hero{border-width:2px}.hero.z-ok{border-color:var(--ok)}.hero.z-warn{border-color:var(--warn)}.hero.z-bad{border-color:var(--bad)}
.hero-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.hero h2{font-size:24px}.hero ul{margin:8px 0 0;padding-left:20px}
.kv{display:flex;flex-wrap:wrap;gap:6px 16px;margin:10px 0 4px;font-size:13px;color:var(--text-2)}.kv b{color:var(--text);font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr));gap:10px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px;display:flex;flex-direction:column;gap:2px}
.t-l{font-size:12px;color:var(--text-2)}.t-v{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.1}.t-v small{font-size:13px;color:var(--text-2);font-weight:500}.t-s{font-size:12px;color:var(--text-3)}
.hbars{display:flex;flex-direction:column;gap:8px}.hb{display:grid;grid-template-columns:8.5em 1fr 2.6em;align-items:center;gap:8px;font-size:13px}
.hb-t{position:relative;height:12px;border-radius:6px;background:var(--surface-2);overflow:hidden}.hb-t i{position:absolute;inset:0 auto 0 0;border-radius:6px}
.hb-t em{position:absolute;top:0;bottom:0;background:var(--line);border-left:2px solid var(--text-3);border-right:2px solid var(--text-3)}
.hb-v{text-align:right;font-variant-numeric:tabular-nums}.hb-sub{margin:-4px 0 2px 9.2em;font-size:11px;color:var(--text-3)}
i.ok{background:var(--ok)}i.warn{background:var(--warn)}i.bad{background:var(--bad)}i.s1{background:var(--s1)}i.s2{background:var(--s2)}i.s3{background:var(--s3)}i.s4{background:var(--s4)}
.stack{display:flex;height:22px;border-radius:8px;overflow:hidden;margin:6px 0 8px}.stack i{display:block;height:100%}
.c-deep{background:var(--deep)}.c-light{background:var(--light)}.c-rem{background:var(--rem)}.c-awake{background:var(--awake)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--text-2);margin-top:4px}.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{display:inline-block;width:10px;height:10px;border-radius:3px}
.chart{width:100%;height:auto;display:block;overflow:visible}
.chart .grid{stroke:var(--line);stroke-width:1}.chart .ref{stroke:var(--text-3);stroke-dasharray:4 4}.chart .band{fill:var(--s1);opacity:.12}
.chart .tick{fill:var(--text-3);font-size:11px}.chart .val{fill:var(--text-2);font-size:11px;font-weight:600}.chart .empty{fill:var(--text-3);font-size:11px}
.chart .ln{fill:none;stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}.chart .area{fill:var(--s1);opacity:.14}
.ln.s1{stroke:var(--s1)}.ln.s2{stroke:var(--s2)}.ln.s3{stroke:var(--s3)}.ln.s4{stroke:var(--s4)}
.dot.s1,.end.s1{fill:var(--s1)}.dot.s2,.end.s2{fill:var(--s2)}.dot.s3,.end.s3{fill:var(--s3)}.dot.s4,.end.s4{fill:var(--s4)}.end{font-size:11px;font-weight:700}
.bar.s1{fill:var(--s1)}.bar.warn{fill:var(--warn)}
.tbl{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px;font-variant-numeric:tabular-nums}.tbl th,.tbl td{padding:6px 4px;border-bottom:1px solid var(--line);text-align:right}
.tbl th:first-child{text-align:left;color:var(--text-2);font-weight:500}.tbl thead th{color:var(--text-3);font-weight:500;font-size:12px}
.sess{border-top:1px solid var(--line)}.sess summary{display:grid;grid-template-columns:3.2em 1fr auto;gap:10px;align-items:center;padding:10px 0;cursor:pointer;list-style:none}
.sess summary::-webkit-details-marker{display:none}.s-t{font-variant-numeric:tabular-nums;color:var(--text-2);font-weight:600}
.s-n{min-width:0}.s-n small{display:block;color:var(--text-3);font-size:12px}.s-b{padding:0 0 10px 4.2em;font-size:13px;color:var(--text-2)}.s-b p{margin:4px 0}
.sens{color:var(--text)!important}.hint{background:var(--surface-2);border-radius:10px;padding:10px 12px;font-size:13px;margin:0 0 10px}
.sens-l{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}.sens-l li{display:grid;grid-template-columns:6.5em 1fr;gap:8px;font-size:13px}
.sens-l small{display:block;color:var(--text-3);font-size:12px}.s-d{color:var(--text-2);font-size:12px;text-transform:capitalize}
.svs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.sv{display:flex;flex-direction:column;gap:2px;background:var(--surface-2);border-radius:10px;padding:8px 10px}
.sv-q{font-size:12px;color:var(--text-2)}.sv-a{font-weight:700;font-size:14px}.sv-a.l0{color:var(--ok)}.sv-a.l1{color:var(--s1)}.sv-a.l2{color:var(--warn)}.sv-a.l3{color:var(--bad)}
.mx{display:grid;gap:3px;align-items:center;font-size:11px}.mx-d{text-align:center;color:var(--text-3);line-height:1.1;text-transform:capitalize}.mx-q{color:var(--text-2);font-size:12px}
.mx-c{display:block;height:16px;border-radius:4px}.l0{background:var(--ok)}.l1{background:var(--light)}.l2{background:var(--warn)}.l3{background:var(--bad)}
.mx-c.na,.sw.na{background:var(--surface-2);border:1px dashed var(--line)}
.sv-a.l0,.sv-a.l1,.sv-a.l2,.sv-a.l3{background:none}
.wb{display:flex;align-items:center;gap:12px;margin:0 0 10px}.wb-v{font-size:34px;font-weight:800;font-variant-numeric:tabular-nums;line-height:1}
.wb-v.ok{color:var(--ok)}.wb-v.warn{color:var(--warn)}.wb-v.bad{color:var(--bad)}.wb-l{font-size:13px;font-weight:600}.wb-l small{display:block;font-weight:400;color:var(--text-3);font-size:12px}
.zones{margin:8px 0 0;font-size:13px}.obs{margin:0;padding-left:18px;font-size:13px;display:flex;flex-direction:column;gap:4px}
.obs .o-bad::marker{color:var(--bad)}.obs .o-warn::marker{color:var(--warn)}.obs .o-info::marker{color:var(--s1)}
.shifts{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.shifts>div{display:flex;flex-direction:column;gap:4px;align-items:flex-start}.shifts small{color:var(--text-3);font-size:11px}
.trace{font-size:12px;color:var(--text-3);padding:4px 2px}.trace a{color:var(--s1)}.trace p{margin:2px 0}
@media (max-width:480px){.hb{grid-template-columns:7em 1fr 2.4em}.hb-sub{margin-left:7.6em}.s-b{padding-left:0}h1{font-size:24px}}
</style></head><body><main>{{BODY}}</main></body></html>"""


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--out", default="app/informe_visual.html")
    a = p.parse_args(argv)
    Path(a.out).write_text(build(a.root), encoding="utf-8")
    print(a.out)


if __name__ == "__main__":
    main()
