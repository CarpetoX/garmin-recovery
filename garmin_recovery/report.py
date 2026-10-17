"""Motor de informes: ``app/informe.md`` + gráficas SVG en ``app/charts/``.

GitHub muestra el Markdown con sus gráficas (también en el móvil) y ChatGPT o
Claude pueden leerlo y citarlo tal cual. Todo sale de ``readiness_v3.json``:
mismas cifras que el panel, sin estimaciones nuevas.

Tres variantes según la franja del Sync:
* mañana (08:30) → recuperación nocturna, qué cambió, plan del día;
* tarde (16:45)  → actividad de hoy y si encaja con la decisión;
* noche (22:45)  → balance del día/semana y previsión orientativa para mañana.
"""
from __future__ import annotations

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- utilidades
ZONE_ES = {"green": "verde", "yellow": "ámbar", "red": "rojo", "unavailable": "pendiente"}
ZONE_ICON = {"green": "🟢", "yellow": "🟠", "red": "🔴", "unavailable": "⚪"}
STATUS_HEX = {"green": "#0ca30c", "yellow": "#fab219", "red": "#d03b3b", "unavailable": "#9a9990"}
INK = "#77766f"          # legible sobre fondo claro y oscuro de GitHub
GRID = "rgba(119,118,111,0.28)"
S1, S2 = "#2a78d6", "#eb6834"          # serie principal / secundaria
CATEGORY_COLORS = {"WOD": "#eb6834", "Fuerza": "#2a78d6", "Halterofilia": "#1baf7a",
                   "Técnica": "#eda100", "Sin detalle": "#9a9990"}


def fmt(v, d=0, unit=""):
    if v is None:
        return "—"
    s = f"{float(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s}{unit}"


def signed(v, d=0, unit=""):
    if v is None:
        return "—"
    return ("+" if float(v) > 0 else "") + fmt(v, d, unit)


def dshort(iso: str) -> str:
    y, m, d = iso[:10].split("-")
    return f"{int(d)}/{int(m)}"


def slot_for(result: dict) -> str:
    synced = ((result.get("certificate") or {}).get("cycle") or {}).get("data_synced_at") or result.get("generated_at")
    try:
        hour = datetime.fromisoformat(synced).hour + datetime.fromisoformat(synced).minute / 60
    except (TypeError, ValueError):
        hour = 12
    return "mañana" if hour < 12.5 else "tarde" if hour < 20 else "noche"


def categorize(session: dict) -> str:
    text = f"{session.get('label') or ''} {session.get('name') or ''}".lower()
    if any(k in text for k in ("snatch", "clean", "jerk", "arrancada", "envión", "envion", "cargada", "halterofilia")):
        return "Halterofilia"
    if any(k in text for k in ("wod", "amrap", "for time", "rft", "rounds", "metcon", "chipper", "emom")):
        return "WOD"
    if any(k in text for k in ("fuerza", "sentadilla", "squat", "peso muerto", "deadlift", "press", "banca",
                               "prensa", "dominada", "pull-up")):
        return "Fuerza"
    if any(k in text for k in ("técnica", "tecnica", "skill", "movilidad")):
        return "Técnica"
    return "Sin detalle"


# ---------------------------------------------------------------- SVG
def _nice(raw: float) -> float:
    import math
    if raw <= 0:
        return 1.0
    p = 10 ** math.floor(math.log10(raw))
    f = raw / p
    return (1 if f <= 1 else 2 if f <= 2 else 5 if f <= 5 else 10) * p


class Chart:
    """Gráfica SVG estática con eje común (nunca doble eje)."""

    def __init__(self, dates, values_for_scale, *, zero=False, lo=None, hi=None, w=640, h=230, label=""):
        self.dates, self.w, self.h, self.label = dates, w, h, label
        self.m = {"l": 40, "r": 14, "t": 30, "b": 26}
        vals = [v for v in values_for_scale if v is not None]
        self.empty = not vals or not dates
        if self.empty:
            self.lo, self.hi, self.step = 0, 1, 1
        else:
            a = lo if lo is not None else min(vals)
            b = hi if hi is not None else max(vals)
            if zero:
                a = 0
            if a == b:
                a, b = a - 1, b + 1
            pad = (b - a) * 0.08
            a = a if (lo is not None or zero) else a - pad
            b = b if hi is not None else b + pad
            self.step = _nice((b - a) / 4)
            import math
            self.lo = math.floor(a / self.step) * self.step
            self.hi = math.ceil(b / self.step) * self.step
        self.iw = w - self.m["l"] - self.m["r"]
        self.ih = h - self.m["t"] - self.m["b"]
        self.bw = self.iw / max(1, len(dates))
        self.parts: list[str] = []
        self.legend: list[tuple[str, str, str]] = []

    def x(self, i):
        return self.m["l"] + self.bw * (i + 0.5)

    def y(self, v):
        return self.m["t"] + self.ih - (v - self.lo) / (self.hi - self.lo) * self.ih

    def axes(self):
        v = self.lo
        dec = 1 if self.step < 1 else 0
        while v <= self.hi + 1e-9:
            yy = self.y(v)
            self.parts.append(f'<line x1="{self.m["l"]}" x2="{self.w - self.m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>')
            self.parts.append(f'<text x="{self.m["l"] - 6}" y="{yy + 4:.1f}" text-anchor="end">{fmt(v, dec)}</text>')
            v += self.step
        n = len(self.dates)
        every = max(1, -(-n // 8))
        for i, d in enumerate(self.dates):
            if (n - 1 - i) % every == 0:
                self.parts.append(f'<text x="{self.x(i):.1f}" y="{self.h - 7}" text-anchor="middle">{dshort(d)}</text>')

    def band(self, lows, highs, color=S1):
        pts = [(i, l, h) for i, (l, h) in enumerate(zip(lows, highs)) if l is not None and h is not None]
        if len(pts) < 2:
            return
        top = " L".join(f"{self.x(i):.1f},{self.y(h):.1f}" for i, _, h in pts)
        bot = " L".join(f"{self.x(i):.1f},{self.y(l):.1f}" for i, l, _ in reversed(pts))
        self.parts.append(f'<path d="M{top} L{bot} Z" fill="{color}" fill-opacity="0.12"/>')

    def ref(self, value, text=None):
        if value is None:
            return
        yy = self.y(value)
        self.parts.append(f'<line x1="{self.m["l"]}" x2="{self.w - self.m["r"]}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{INK}" stroke-width="1"/>')
        if text:
            self.parts.append(f'<text x="{self.m["l"] + 4}" y="{yy - 5:.1f}" text-anchor="start">{html.escape(text)}</text>')

    def line(self, values, color=S1, name=None, markers=False):
        seg, segs = [], []
        for i, v in enumerate(values):
            if v is None:
                if seg:
                    segs.append(seg)
                seg = []
            else:
                seg.append((self.x(i), self.y(v)))
        if seg:
            segs.append(seg)
        for s in segs:
            if len(s) > 1:
                d = " L".join(f"{a:.1f},{b:.1f}" for a, b in s)
                self.parts.append(f'<path d="M{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        if markers:
            self.dots(values, color)
        if name:
            self.legend.append(("line", color, name))

    def dots(self, values, color=S1, name=None):
        for i, v in enumerate(values):
            if v is not None:
                self.parts.append(f'<circle cx="{self.x(i):.1f}" cy="{self.y(v):.1f}" r="4" fill="{color}"/>')
        if name:
            self.legend.append(("dot", color, name))

    def stacked_bars(self, stacks):
        """stacks: lista por día de [(valor, color)]; 2 px de separación entre segmentos."""
        w = min(24, self.bw * 0.62)
        for i, segs in enumerate(stacks):
            base = self.y(max(self.lo, 0))
            for k, (v, color) in enumerate(segs):
                if not v or v <= 0:
                    continue
                h = (v / (self.hi - self.lo)) * self.ih
                y0 = base - h
                last = k == len([s for s in segs if s[0]]) - 1
                r = min(4, w / 2, h) if last else 0
                x0 = self.x(i) - w / 2
                gap = 2 if k else 0
                hh = max(0.5, h - gap)
                if r:
                    self.parts.append(
                        f'<path d="M{x0:.1f},{base - gap:.1f}V{y0 + r:.1f}Q{x0:.1f},{y0:.1f} {x0 + r:.1f},{y0:.1f}'
                        f'H{x0 + w - r:.1f}Q{x0 + w:.1f},{y0:.1f} {x0 + w:.1f},{y0 + r:.1f}V{base - gap:.1f}Z" fill="{color}"/>')
                else:
                    self.parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{hh:.1f}" fill="{color}"/>')
                base = y0

    def bars(self, values, color=S1, name=None):
        self.stacked_bars([[(v, color)] if v else [] for v in values])
        if name:
            self.legend.append(("bar", color, name))

    def strip(self, zones):
        """Franja superior con la zona de decisión de cada día (prioridad visual)."""
        for i, z in enumerate(zones):
            if z in STATUS_HEX:
                w = max(2, self.bw - 2)
                self.parts.append(f'<rect x="{self.x(i) - w / 2:.1f}" y="{self.m["t"] - 12}" width="{w:.1f}" height="6" rx="2" fill="{STATUS_HEX[z]}"/>')

    def render(self, empty_text="Sin datos suficientes todavía") -> str:
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
                f'role="img" aria-label="{html.escape(self.label)}" font-family="system-ui,-apple-system,Segoe UI,Roboto,sans-serif" '
                f'font-size="12" fill="{INK}">')
        if self.empty:
            return head + f'<text x="{self.w / 2}" y="{self.h / 2}" text-anchor="middle">{html.escape(empty_text)}</text></svg>\n'
        legend, lx = [], self.m["l"]
        for kind, color, name in self.legend:
            if kind == "line":
                legend.append(f'<line x1="{lx}" x2="{lx + 14}" y1="10" y2="10" stroke="{color}" stroke-width="2"/>')
            elif kind == "dot":
                legend.append(f'<circle cx="{lx + 6}" cy="10" r="4" fill="{color}"/>')
            else:
                legend.append(f'<rect x="{lx}" y="4" width="12" height="12" rx="2" fill="{color}"/>')
            legend.append(f'<text x="{lx + 18}" y="14">{html.escape(name)}</text>')
            lx += 34 + 7 * len(name)
        return head + "".join(self.parts) + "".join(legend) + "</svg>\n"


# ---------------------------------------------------------------- gráficas
def chart_hrv(trend):
    d = [t["date"] for t in trend]
    vals = [t.get("hrv_ms") for t in trend] + [t.get("hrv_low_ms") for t in trend] + [t.get("hrv_high_ms") for t in trend]
    c = Chart(d, vals, label="HRV nocturna")
    if not c.empty:
        c.axes()
        c.band([t.get("hrv_low_ms") for t in trend], [t.get("hrv_high_ms") for t in trend])
        c.legend.append(("bar", "rgba(42,120,214,0.25)", "Rango normal"))
        c.line([t.get("hrv_rolling_ms") for t in trend], S1, "Media 7 días")
        c.dots([t.get("hrv_ms") for t in trend], S1, "Noche (ms)")
    return c.render()


def rolling(values, n=7, min_n=4):
    out = []
    for i in range(len(values)):
        win = [v for v in values[max(0, i - n + 1):i + 1] if v is not None]
        out.append(sum(win) / len(win) if len(win) >= min_n else None)
    return out


def chart_rhr(trend, baseline):
    d = [t["date"] for t in trend]
    c = Chart(d, [t.get("resting_hr") for t in trend] + [t.get("night_hr") for t in trend] + [baseline],
              label="FC en reposo y nocturna")
    if not c.empty:
        c.axes()
        c.ref(baseline, f"mediana reposo {fmt(baseline)}")
        c.line([t.get("resting_hr") for t in trend], S1, "Reposo (lpm)", markers=True)
        c.line([t.get("night_hr") for t in trend], S2, "Nocturna (lpm)")
        c.line(rolling([t.get("resting_hr") for t in trend]), "#1baf7a", "Reposo, media 7 d")
    return c.render()


def chart_sleep(trend, need):
    d = [t["date"] for t in trend]
    c = Chart(d, [t.get("sleep_hours") for t in trend] + [need], zero=True, label="Sueño por noche")
    if not c.empty:
        c.axes()
        day_sleep = [t.get("sleep_hours") if t.get("sleep_context") == "day_sleep" else None for t in trend]
        night = [t.get("sleep_hours") if t.get("sleep_context") != "day_sleep" else None for t in trend]
        c.bars(night, S1, "Sueño nocturno (h)")
        if any(day_sleep):
            c.bars(day_sleep, "#eda100", "Sueño diurno / post-TN (h)")
        c.ref(need, f"necesidad {fmt(need, 1)} h")
        c.line(rolling([t.get("sleep_hours") for t in trend]), S2, "Media 7 días")
    return c.render()


def chart_load(trend, ctl_ok):
    d = [t["date"] for t in trend]
    c = Chart(d, [t.get("load") for t in trend] + [t.get("atl") for t in trend] + [t.get("ctl") for t in trend],
              zero=True, label="Carga diaria, ATL y CTL")
    if not c.empty:
        c.axes()
        c.bars([t.get("load") for t in trend], "rgba(42,120,214,0.45)", "Carga diaria")
        c.line([t.get("atl") for t in trend], S2, "ATL (fatiga, 7 d)")
        c.line([t.get("ctl") for t in trend], S1, "CTL (forma, 42 d)")
        if not ctl_ok:
            c.parts.append(f'<text x="{c.w - c.m["r"]}" y="{c.m["t"] + 12}" text-anchor="end">'
                           f'CTL insuficiente: forma (TSB) no interpretable</text>')
    return c.render()


def chart_sessions(sessions, end: str, days=14):
    last = date.fromisoformat(end)
    dates = [(last - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    by_day = {d: [] for d in dates}
    for s in sessions:
        if s.get("date") in by_day and s.get("load"):
            by_day[s["date"]].append(s)
    stacks, totals, used = [], [], set()
    for d in dates:
        segs = []
        for s in sorted(by_day[d], key=lambda s: s.get("start_local") or ""):
            cat = categorize(s)
            used.add(cat)
            segs.append((s["load"], CATEGORY_COLORS[cat]))
        stacks.append(segs)
        totals.append(sum(v for v, _ in segs) or None)
    c = Chart(dates, totals, zero=True, label="Carga por sesión y tipo")
    if not c.empty:
        c.axes()
        c.stacked_bars(stacks)
        for cat in CATEGORY_COLORS:
            if cat in used:
                c.legend.append(("bar", CATEGORY_COLORS[cat], cat))
    return c.render()


def chart_readiness(trend):
    d = [t["date"] for t in trend]
    c = Chart(d, [0, 100], lo=0, hi=100, label="Disponibilidad: oficial frente a v3")
    c.axes()
    c.strip([t.get("decision_zone") for t in trend])
    c.ref(70)
    c.ref(50)
    c.line([t.get("score") for t in trend], S1, "v3 en pruebas", markers=True)
    c.line([t.get("v2_score") for t in trend], S2, "v2 oficial", markers=True)
    c.legend.append(("bar", STATUS_HEX["red"], "Decisión del día (franja)"))
    return c.render()


def chart_strength(rows):
    """Carga máxima declarada por ejercicio con barra y ≥ 2 sesiones."""
    series = {}
    for r in rows:
        if r.get("equipment") == "barbell" and r.get("peak_declared_load_kg"):
            series.setdefault(r["exercise"], {})[r["date"]] = r["peak_declared_load_kg"]
    series = {k: v for k, v in series.items() if len(v) >= 2}
    if not series:
        return None
    dates = sorted({d for v in series.values() for d in v})
    colors = [S1, S2, "#1baf7a"]
    allv = [x for v in series.values() for x in v.values()]
    c = Chart(dates, allv, label="Progresión de carga máxima")
    c.axes()
    for (name, pts), col in zip(sorted(series.items())[:3], colors):
        c.line([pts.get(d) for d in dates], col, name, markers=True)
    return c.render()


# ---------------------------------------------------------------- texto
def _component(r, key):
    return ((r.get("readiness") or {}).get("components") or {}).get(key) or {}


def what_changed(result) -> list[str]:
    hrv, card, slp, st = (_component(result, k) for k in ("hrv", "cardiac", "sleep", "stress"))
    out = []
    if hrv.get("today_ms") is not None:
        band = {"normal": "dentro de tu rango normal", "suprimida": "por debajo de tu rango normal",
                "elevada": "por encima de tu rango normal"}.get(hrv.get("band"), "rango aún sin calcular")
        out.append(f"**HRV:** {fmt(hrv['today_ms'])} ms esta noche ({signed(hrv.get('today_vs_baseline_pct'))} % vs. base "
                   f"{fmt(hrv.get('baseline_ms'))} ms); media de 7 días {fmt(hrv.get('rolling_ms'), 1)} ms, {band} "
                   f"({fmt(hrv.get('normal_low_ms'))}–{fmt(hrv.get('normal_high_ms'))} ms).")
    if card.get("resting_hr") is not None:
        out.append(f"**FC:** reposo {fmt(card['resting_hr'])} lpm ({signed(card.get('resting_delta_bpm'))} vs. mediana "
                   f"{fmt(card.get('baseline_resting_hr'))}); nocturna {fmt(card.get('night_hr'), 1)} lpm "
                   f"({signed(card.get('night_delta_bpm'), 1)}).")
    if slp.get("hours") is not None:
        out.append(f"**Sueño:** {fmt(slp['hours'], 2)} h, puntuación {fmt(slp.get('sleep_score'))}; deuda "
                   f"{fmt(slp.get('debt_hours'), 1)} h en {slp.get('debt_nights')} noches frente a "
                   f"{fmt(slp.get('need_hours'), 1)} h de necesidad.")
    if st.get("yesterday_avg") is not None:
        out.append(f"**Estrés Garmin ayer:** {fmt(st['yesterday_avg'])} de media (tu mediana {fmt(st.get('baseline_median'))}).")
    return out


def coincident_signals(result) -> str:
    comps = (result.get("readiness") or {}).get("components") or {}
    scored = {k: c for k, c in comps.items() if c.get("z") is not None}
    neg = [c["label"] for c in scored.values() if c["z"] <= -0.5]
    pos = [c["label"] for c in scored.values() if c["z"] >= 0.5]
    txt = f"{len(neg)} de {len(scored)} señales en contra"
    if neg:
        txt += f" ({', '.join(neg)})"
    if pos:
        txt += f"; a favor: {', '.join(pos)}"
    missing = [c["label"] for c in comps.values() if c.get("z") is None]
    if missing:
        txt += f". Sin datos: {', '.join(missing)}"
    return txt + "."


def uncertainty(result) -> list[str]:
    r = result.get("readiness") or {}
    dc, rc = r.get("data_confidence") or {}, r.get("recommendation_confidence") or {}
    out = [f"Confianza de los datos: **{dc.get('level', '—')}**" + (f" ({'; '.join(dc['why'])})" if dc.get("why") else ""),
           f"Confianza de la recomendación: **{rc.get('level', '—')}**" + (f" ({'; '.join(rc['why'])})" if rc.get("why") else "")]
    out += (result.get("decision") or {}).get("divergence") or []
    return out


def shift_notes(result, trend) -> list[str]:
    today = trend[-1] if trend else {}
    notes = list((result.get("readiness") or {}).get("notes") or [])
    return [n for n in notes if "turno" in n.lower()] or ([f"Turno de hoy: {today.get('shift')}."] if today.get("shift") else [])


def sessions_table(sessions, day=None, limit=8) -> str:
    rows = [s for s in sessions if day is None or s.get("date") == day][:limit]
    if not rows:
        return "_Sin sesiones registradas._\n"
    out = ["| Fecha | Tipo | Sesión | Min | Carga | FC media | RPE | sRPE |", "|---|---|---|--:|--:|--:|--:|--:|"]
    for s in rows:
        hhmm = (s.get("start_local") or "")[11:16]
        name = (s.get("label") or s.get("name") or "").replace("|", "/")
        out.append(f"| {dshort(s['date'])} {hhmm} | {categorize(s)} | {name} | {fmt(s.get('duration_min'))} | "
                   f"{fmt(s.get('load'))} | {fmt(s.get('avg_hr'))} | {fmt(s.get('rpe'), 1)} | {fmt(s.get('srpe'))} |")
    return "\n".join(out) + "\n"


EQUIP_ES = {"barbell": "barra", "dumbbell_pair": "mancuernas (par)", "dumbbell": "mancuerna",
            "machine_stack": "máquina de placas", "plate_loaded_machine": "máquina de discos",
            "bodyweight": "peso corporal", "kettlebell": "kettlebell", "unspecified": "sin especificar"}


def format_load(r) -> str:
    """Carga máxima con su unidad real: nunca una cifra ambigua."""
    v, unit = r.get("peak_declared_load_kg"), r.get("load_unit")
    if unit == "peso_corporal" or r.get("equipment") == "bodyweight":
        return "peso corporal"
    if v is None:
        return "—"
    txt = {
        "kg_total_dos_mancuernas": f"{fmt(v, 1)} kg total (2 × {fmt(v / 2, 1)} kg)",
        "kg_total_barra": f"{fmt(v, 1)} kg con barra",
        "kg_indicado_maquina": f"{fmt(v, 1)} kg indicados en máquina",
        "kg_total_dos_lados": f"{fmt(v, 1)} kg total (dos lados)",
    }.get(unit, f"{fmt(v, 1)} kg (unidad sin especificar)")
    if r.get("laterality_unconfirmed"):
        txt += " · lateralidad sin confirmar"
    return txt


def strength_table(rows) -> str:
    if not rows:
        return "_Sin series de fuerza verificadas en la ventana._\n"
    out = ["| Fecha | Ejercicio | Implemento | Carga máx. | Volumen verificado | Series | RPE sesión |",
           "|---|---|---|---|--:|--:|--:|"]
    for r in rows[:12]:
        bodyweight = r.get("equipment") == "bodyweight"
        vol = "—" if bodyweight else fmt(r.get("verified_volume_kg"), 0, " kg") + ("" if r.get("volume_complete") else " (parcial)")
        out.append(f"| {dshort(r['date'])} | {r.get('exercise')} | {EQUIP_ES.get(r.get('equipment'), r.get('equipment') or '—')} | "
                   f"{format_load(r)} | {vol} | {r.get('known_sets') or '—'}/{r.get('total_sets') or '—'} | {fmt(r.get('rpe'), 1)} |")
    out.append("")
    out.append("_Volumen = kg × repeticiones de las series con carga conocida. No se comparan implementos distintos "
               "(barra, mancuernas, máquinas); las máquinas no son comparables con peso libre; el RPE es de la sesión, no de cada serie._")
    return "\n".join(out) + "\n"


def pending_actions(result, strength=None) -> list[str]:
    ti = result.get("training_integrity") or {}
    out = []
    unclear = sorted({r.get("exercise") for r in strength or []
                      if r.get("peak_declared_load_kg") and not r.get("load_unit") and r.get("equipment") in (None, "unspecified")})
    for ex in unclear:
        out.append(f"Indica el implemento y la unidad de carga de **{ex}** (barra, mancuernas por unidad o par, máquina) "
                   "para que su carga sea comparable.")
    for x in ti.get("without_rpe") or []:
        when = f"{dshort(x['start_local'][:10])} {x['start_local'][11:16]}" if x.get("start_local") else "—"
        out.append(f"Añade el RPE de la actividad **{x['id']}** ({when}, {categorize(x)}, {fmt(x.get('duration_min'))} min, "
                   f"carga {fmt(x.get('load'))}) en la pestaña `RPE` de tu hoja, con ese ID exacto. Si fue un calentamiento "
                   "registrado aparte, anótalo así. No se estima.")
    for k in ti.get("rpe_without_activity") or []:
        out.append(f"La fila de RPE con ID **{k}** no coincide con ninguna actividad: revisa el ID.")
    if not (_component(result, "subjective").get("values")):
        out.append("Registra en Intervals.icu fatiga, agujetas, estrés, ánimo y motivación (1 = mejor, 4 = peor).")
    return out


def certificate_block(result) -> list[str]:
    ce = result.get("certificate") or {}
    cy = ce.get("cycle") or {}
    ti = result.get("training_integrity") or {}
    ages = ce.get("data_age") or {}
    lbl = {"confirmed_sleep": "fin del sueño", "sleep_hrv": "última HRV", "heart_rate_live": "última FC",
           "body_battery_live": "último Body Battery"}

    def age(a):
        if a.get("age_minutes") is None:
            return "sin marca"
        m = a["age_minutes"]
        return f"hace {fmt(m)} min" if m < 90 else f"hace {fmt(m / 60, 1)} h"
    synced = cy.get("data_synced_at")
    synced_txt = datetime.fromisoformat(synced).strftime("%H:%M") if synced else "—"
    missed = (ce.get("execution_health") or {}).get("missed_slots") or []
    cons = (ce.get("consistency_v3_v2") or {}).get("status")
    return [
        f"**Ciclo:** {cy.get('cycle_id') or '—'} · datos sincronizados a las {synced_txt}"
        + (" · Sync fuera de franja" if cy.get("data_newer_than_certified_cycle") else ""),
        "**Antigüedad:** " + (" · ".join(f"{lbl.get(k, k)} {age(a)} {'✓' if a.get('state') == 'reciente' else '!'}"
                                          for k, a in ages.items()) or "sin marcas temporales"),
        f"**Integridad:** coherencia v3/v2 {'✓' if cons == 'ok' else '! ' + (cons or 'sin comparar')} · sesiones con RPE "
        f"{ti.get('with_rpe', '—')}/{ti.get('sessions', '—')}"
        + (f" (sin RPE: {', '.join(dshort(x['start_local'][:10]) + ' ' + x['start_local'][11:16] for x in ti.get('without_rpe') or [] if x.get('start_local'))})"
           if ti.get("without_rpe") else ""),
        f"**Ejecución:** {len(missed)} franja(s) de Sync perdidas" + (f" ({', '.join(dshort(s) + ' ' + s[11:16] for s in missed)})" if missed else ""),
        f"**Estado:** {'sin avisos' if ce.get('status') == 'ok' else 'con avisos'} · fuentes con huella SHA-256: "
        f"{len(ce.get('source_sha256') or {})} · entrega: no verificable desde los datos",
    ]


# ---------------------------------------------------------------- snapshots
SNAPSHOT_FIELDS = ["report_id", "generated_at", "date", "slot", "decision_zone", "v2_score", "hybrid_score",
                   "v3_score", "hrv_ms", "resting_hr", "sleep_hours", "week_load", "week_sessions",
                   "sessions_today", "load_today", "rpe_with", "data_synced_at"]


def snapshot(result: dict, report_id: str) -> dict:
    dec = result.get("decision") or {}
    reg = {m["id"]: m for m in dec.get("registry") or []}
    today = result.get("date")
    today_s = [s for s in result.get("recent_sessions") or [] if s.get("date") == today]
    return {
        "report_id": report_id, "generated_at": result.get("generated_at"), "date": today, "slot": slot_for(result),
        "decision_zone": dec.get("zone"),
        "v2_score": (reg.get("recovery_assessment_v2") or {}).get("score"),
        "hybrid_score": (reg.get("readiness_hybrid") or {}).get("score"),
        "v3_score": (result.get("readiness") or {}).get("score"),
        "hrv_ms": _component(result, "hrv").get("today_ms"),
        "resting_hr": _component(result, "cardiac").get("resting_hr"),
        "sleep_hours": _component(result, "sleep").get("hours"),
        "week_load": (result.get("load") or {}).get("week_load"),
        "week_sessions": (result.get("load") or {}).get("week_sessions"),
        "sessions_today": len(today_s), "load_today": round(sum(s.get("load") or 0 for s in today_s), 1),
        "rpe_with": (result.get("training_integrity") or {}).get("with_rpe"),
        "data_synced_at": ((result.get("certificate") or {}).get("cycle") or {}).get("data_synced_at"),
    }


def report_id_for(result: dict) -> str:
    import hashlib
    core = json.dumps({"decision": (result.get("decision") or {}).get("zone"),
                       "scores": [m.get("score") for m in (result.get("decision") or {}).get("registry") or []],
                       "generated_at": result.get("generated_at")}, sort_keys=True)
    try:
        hhmm = datetime.fromisoformat(result.get("generated_at")).strftime("%H%M")
    except (TypeError, ValueError):
        hhmm = "0000"
    return f"GR-{result.get('date')}-{hhmm}-{hashlib.sha256(core.encode()).hexdigest()[:6]}"


def _num(v):
    try:
        return None if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return None


def changes_since(prev: dict | None, cur: dict) -> list[str]:
    if not prev:
        return ["Primer informe con registro de ciclos: la comparación aparecerá desde el siguiente."]
    when = prev.get("generated_at") or ""
    try:
        when_txt = datetime.fromisoformat(when).strftime("%d/%m %H:%M")
    except ValueError:
        when_txt = when
    out = []
    if (prev.get("decision_zone") or None) != (cur.get("decision_zone") or None):
        out.append(f"**Decisión:** {ZONE_ES.get(prev.get('decision_zone'), '—')} → **{ZONE_ES.get(cur.get('decision_zone'), '—')}**.")
    for key, label, d in (("v2_score", "Oficial v2", 0), ("hybrid_score", "Híbrido", 0), ("v3_score", "v3", 0)):
        a, b = _num(prev.get(key)), _num(cur.get(key))
        if a is not None and b is not None and abs(a - b) >= 1:
            out.append(f"{label}: {fmt(a, d)} → {fmt(b, d)} ({signed(b - a, d)}).")
    new_night = prev.get("date") != cur.get("date") or any(
        _num(prev.get(k)) != _num(cur.get(k)) for k in ("hrv_ms", "sleep_hours"))
    if new_night:
        out.append(f"Nueva noche registrada: HRV {fmt(_num(prev.get('hrv_ms')))} → {fmt(_num(cur.get('hrv_ms')))} ms, "
                   f"sueño {fmt(_num(prev.get('sleep_hours')), 2)} → {fmt(_num(cur.get('sleep_hours')), 2)} h, "
                   f"FC reposo {fmt(_num(prev.get('resting_hr')))} → {fmt(_num(cur.get('resting_hr')))} lpm.")
    if prev.get("date") == cur.get("date"):
        ds = int(_num(cur.get("sessions_today")) or 0) - int(_num(prev.get("sessions_today")) or 0)
        dl = (_num(cur.get("load_today")) or 0) - (_num(prev.get("load_today")) or 0)
        if ds > 0:
            out.append(f"Sesiones nuevas desde entonces: **{ds}** (carga +{fmt(dl)}).")
    a, b = _num(prev.get("rpe_with")), _num(cur.get("rpe_with"))
    if a is not None and b is not None and b != a:
        out.append(f"Sesiones con RPE: {fmt(a)} → {fmt(b)}.")
    if not out:
        out.append("Sin cambios en los datos.")
    return [f"Frente al informe {prev.get('report_id') or ''} ({when_txt}):"] + out


# ---------------------------------------------------------------- informe
def build_report(result: dict, crossfit: dict | None = None, previous: dict | None = None,
                 report_id: str | None = None) -> tuple[str, dict[str, str]]:
    trend = result.get("trend_28d") or []
    dec = result.get("decision") or {}
    from .readiness import GUIDANCE
    g = dec.get("guidance") or GUIDANCE["unavailable"]
    reg = {m["id"]: m for m in dec.get("registry") or []}
    slot = slot_for(result)
    today = result.get("date")
    sessions = result.get("recent_sessions") or []
    load = result.get("load") or {}
    card = _component(result, "cardiac")
    slp = _component(result, "sleep")
    strength = [r for r in ((crossfit or {}).get("muscle_load") or {}).get("strength_exercises") or []
                if r.get("date") and r["date"] >= (date.fromisoformat(today) - timedelta(days=27)).isoformat()]
    strength.sort(key=lambda r: r["date"], reverse=True)

    charts = {
        "readiness.svg": chart_readiness(trend),
        "hrv.svg": chart_hrv(trend),
        "rhr.svg": chart_rhr(trend, card.get("baseline_resting_hr")),
        "sleep.svg": chart_sleep(trend, slp.get("need_hours")),
        "load.svg": chart_load(trend, bool(load.get("form_interpretable"))),
        "sessions.svg": chart_sessions(sessions, today),
    }
    strength_svg = chart_strength(strength)
    if strength_svg:
        charts["strength.svg"] = strength_svg

    zone = dec.get("zone", "unavailable")
    try:
        day_txt = date.fromisoformat(today).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        day_txt = str(today)
    titles = {"mañana": "Informe matutino", "tarde": "Informe de seguimiento", "noche": "Cierre diario"}
    report_id = report_id or report_id_for(result)
    md = [f"# {titles[slot]} · {day_txt}", "", f"`{report_id}` · cita este identificador al reenviar el informe.", ""]
    ce = result.get("certificate") or {}
    if ce.get("status") != "ok" and ce.get("issues"):
        md += [f"> ⚠️ Certificado con avisos: {'; '.join(ce['issues'])}.", ""]
    md += [
        f"## {ZONE_ICON.get(zone, '')} Decisión: {ZONE_ES.get(zone, zone)} — {g.get('label', '')}",
        "",
        f"| Oficial v2 | RPE máximo | Volumen | HRV | FC reposo | Sueño | Garmin Readiness |",
        "|--:|--:|--:|--:|--:|--:|--:|",
        f"| {fmt((reg.get('recovery_assessment_v2') or {}).get('score'))}/100 | {g.get('rpe_max', '—')} | {g.get('volume', '—')} | "
        f"{fmt(_component(result, 'hrv').get('today_ms'))} ms | {fmt(card.get('resting_hr'))} lpm | {fmt(slp.get('hours'), 2)} h | "
        f"{fmt((reg.get('garmin_training_readiness') or {}).get('score'))}/100 |",
        "",
        f"**Recomendación:** {g.get('text', '')}",
        "",
        ("Puntuaciones (no equivalentes entre sí): " if dec.get("registry") else "_Sin registro de modelos en este ciclo._") + " · ".join(
            f"{m['label']} **{fmt(m.get('score'))}**" + (f" ({ZONE_ES.get(m['zone'], '—')})" if m.get("zone") else "")
            for m in dec.get("registry") or []) + ". " + (dec.get("rule") or ""),
        "",
    ]
    box = dec.get("crossfit") or []
    if box:
        md += ["## En el box hoy", ""] + [f"- {x}" for x in box] + [""]
    md += ["## Qué ha cambiado desde el informe anterior", ""] + [f"- {x}" if i else x for i, x in
                                                                  enumerate(changes_since(previous, snapshot(result, report_id)))] + [""]

    if slot == "mañana":
        md += ["## Qué ha cambiado respecto a tu línea base", ""] + ([f"- {x}" for x in what_changed(result)] or ["_Sin datos de hoy todavía._"]) + [""]
        md += [f"**Señales coincidentes:** {coincident_signals(result)}", ""]
        md += ["## Incertidumbre", ""] + [f"- {x}" for x in uncertainty(result)] + [""]
        plan = shift_notes(result, trend)
        md += ["## Plan del día", "", f"- {g.get('text', '')} RPE ≤ {g.get('rpe_max', '—')}, volumen {g.get('volume', '—')}."]
        md += [f"- {n}" for n in plan] + [""]
        md += ["## Tendencias", "", "![Disponibilidad](charts/readiness.svg)", ""]
    elif slot == "tarde":
        today_sessions = [s for s in sessions if s.get("date") == today]
        md += ["## Actividad de hoy", "", sessions_table(sessions, day=today)]
        load_today = sum(s.get("load") or 0 for s in today_sessions)
        max_rpe = max([s.get("rpe") or 0 for s in today_sessions] or [0])
        fit = ("Sin sesiones registradas todavía hoy." if not today_sessions else
               f"⚠️ RPE {fmt(max_rpe, 1)} supera el máximo recomendado ({g.get('rpe_max')}): reduce o cambia la sesión restante."
               if g.get("rpe_max") is not None and max_rpe > g["rpe_max"] else
               f"La actividad de hoy (carga {fmt(load_today)}, RPE máx. {fmt(max_rpe, 1)}) encaja con la decisión.")
        md += [f"**¿Encaja con la decisión?** {fit}", ""]
        md += [f"**Carga 7 días:** {fmt(load.get('week_load'))} en {load.get('week_sessions', '—')} sesiones"
               + (f" ({signed(load.get('week_change_pct'))} % vs. semana previa)" if load.get('week_change_pct') is not None else "")
               + f" · sRPE {fmt(load.get('week_srpe'))} · monotonía {fmt(load.get('monotony'), 2)}.", ""]
        md += ["## Gráficas", "", "![Carga](charts/load.svg)", "", "![Sesiones](charts/sessions.svg)", ""]
    else:
        today_sessions = [s for s in sessions if s.get("date") == today]
        md += ["## Balance del día", "", sessions_table(sessions, day=today)]
        md += ["## Balance de la semana", "",
               f"- Carga 7 días: **{fmt(load.get('week_load'))}** en {load.get('week_sessions', '—')} sesiones"
               + (f" ({signed(load.get('week_change_pct'))} % vs. semana previa)" if load.get('week_change_pct') is not None else "") + ".",
               f"- sRPE 7 días {fmt(load.get('week_srpe'))} · monotonía {fmt(load.get('monotony'), 2)} · strain {fmt(load.get('strain'))}.",
               f"- Fatiga acumulada: ATL {fmt(load.get('atl'), 1)}, CTL {fmt(load.get('ctl'), 1)}, TSB {signed(load.get('tsb'), 1)}"
               + ("" if load.get("form_interpretable") else " (CTL insuficiente: la forma no se interpreta todavía)") + ".", ""]
        tomorrow = (date.fromisoformat(today) + timedelta(days=1)).isoformat() if today else None
        shift_tomorrow = ((crossfit or {}).get("_shifts") or {}).get(tomorrow)
        md += ["## Previsión orientativa para mañana", ""]
        target = (slp.get("need_hours") or 7.5) + min(1.0, (slp.get("debt_hours") or 0) / 3)
        md += [f"- Objetivo de sueño esta noche: **{fmt(target, 1)} h** (necesidad + parte de la deuda de {fmt(slp.get('debt_hours'), 1)} h)."]
        if shift_tomorrow:
            md += [f"- Mañana turno **{shift_tomorrow}**" + (": si entrenas, antes del turno, corto y sin máximos." if shift_tomorrow == "TN" else ".")]
        md += ["- La decisión de mañana dependerá del sueño y la HRV de esta noche; no se anticipa.", ""]
        md += ["## Gráficas", "", "![Carga](charts/load.svg)", "", "![Disponibilidad](charts/readiness.svg)", ""]

    md += ["## Recuperación: tendencias de 28 días", "", "![HRV](charts/hrv.svg)", "", "![FC](charts/rhr.svg)", "",
           "![Sueño](charts/sleep.svg)", ""]
    actions = pending_actions(result, strength)
    if actions:
        md += ["## Acciones pendientes", ""] + [f"- {x}" for x in actions] + [""]
    md += ["## Fuerza (últimos 28 días)", "", strength_table(strength)]
    if strength_svg:
        md += ["![Progresión](charts/strength.svg)", "",
               "_Carga máxima declarada por sesión con barra: no es un 1RM y depende del esquema "
               "(p. ej. series pesadas cortas frente a series de volumen)._", ""]
    else:
        md += ["_Progresión: hacen falta ≥ 2 sesiones del mismo ejercicio con barra para trazarla._", ""]
    md += ["## Certificado", "", f"- **Identificador del informe:** `{report_id}`"] + [f"- {x}" for x in certificate_block(result)] + [""]
    md += [f"_{(result.get('readiness') or {}).get('disclaimer') or 'No es un diagnóstico médico.'} Generado {result.get('generated_at', '')[:16].replace('T', ' ')} · "
           f"app {result.get('app_version')} · modelo {result.get('model_version')}. Fuente única: `app/readiness_v3.json`._", ""]
    return "\n".join(md), charts


def write_report(root: Path, out_dir: Path, result: dict) -> None:
    try:
        crossfit = json.loads((Path(root) / "crossfit_insights.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        crossfit = {}
    try:
        shifts = json.loads((Path(root) / "shift_calendar.json").read_text(encoding="utf-8")).get("days") or {}
    except (OSError, ValueError):
        shifts = {}
    crossfit = dict(crossfit, _shifts=shifts)
    import csv
    reports_csv = Path(root) / "history" / "reports.csv"
    previous = None
    if reports_csv.exists():
        with reports_csv.open(encoding="utf-8", newline="") as fh:
            rows = [r for r in csv.DictReader(fh) if (r.get("generated_at") or "") < (result.get("generated_at") or "")]
        previous = rows[-1] if rows else None
    rid = report_id_for(result)
    md, charts = build_report(result, crossfit, previous, rid)
    reports_csv.parent.mkdir(parents=True, exist_ok=True)
    new = not reports_csv.exists()
    with reports_csv.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SNAPSHOT_FIELDS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow({k: ("" if v is None else v) for k, v in snapshot(result, rid).items()})
    cdir = out_dir / "charts"
    cdir.mkdir(parents=True, exist_ok=True)
    for name, svg in charts.items():
        (cdir / name).write_text(svg, encoding="utf-8")
    stale = cdir / "strength.svg"
    if "strength.svg" not in charts and stale.exists():
        stale.unlink()
    (out_dir / "informe.md").write_text(md, encoding="utf-8")
