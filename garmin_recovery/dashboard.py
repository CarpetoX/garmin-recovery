"""Panel HTML autocontenido (sin dependencias externas ni red).

Los datos se incrustan como JSON y los gráficos se dibujan en el navegador
con SVG a la anchura real del contenedor (legibles también en el móvil).
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ZONE_UI = {
    "green": ("good", "✓"), "yellow": ("warning", "!"),
    "red": ("critical", "✕"), "unavailable": ("muted", "…"),
}


def _kg(v) -> str:
    return f"{v:g}".replace(".", ",")


def _ddmm(date_s: str) -> str:
    return f"{date_s[8:10]}/{date_s[5:7]}"


def _prog_svg(points: list[dict], big: bool = False) -> str:
    """Mejor carga por sesión: línea con puntos (la última destacada); en grande, con la carga y la fecha de cada punto."""
    from datetime import date as _d
    w, h = (300, 120) if big else (110, 34)
    padx, pady = (26, 22) if big else (5, 5)
    xs = [(_d.fromisoformat(p["date"]) - _d.fromisoformat(points[0]["date"])).days for p in points]
    span = max(xs) or 1
    vals = [p["top_load"] for p in points]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1.0

    def px(i):
        return padx + (xs[i] / span) * (w - 2 * padx)

    def py(i):
        return h - pady - ((vals[i] - lo) / rng) * (h - 2 * pady) if hi != lo else h / 2
    pts = " ".join(f"{px(i):.1f},{py(i):.1f}" for i in range(len(points)))
    dots = "".join(f'<circle cx="{px(i):.1f}" cy="{py(i):.1f}" r="{4 if (big and i == len(points) - 1) or (not big and i == len(points) - 1) else 2.6}" '
                   f'class="{"pg-last" if i == len(points) - 1 else "pg-dot"}"/>' for i in range(len(points)))
    labels = ""
    if big:
        for i, p in enumerate(points):
            labels += (f'<text x="{px(i):.1f}" y="{py(i) - 8:.1f}" text-anchor="middle" class="pg-val">{_kg(p["top_load"])}</text>'
                       f'<text x="{px(i):.1f}" y="{h - 4}" text-anchor="middle" class="pg-date">{_ddmm(p["date"])}</text>')
    label = "Mejor carga por sesión: " + ", ".join(f'{_ddmm(p["date"])} {_kg(p["top_load"])} kg' for p in points)
    return (f'<svg class="pg-svg{" big" if big else ""}" viewBox="0 0 {w} {h}" role="img" aria-label="{_esc(label)}">'
            f'<polyline points="{pts}" class="pg-line"/>{dots}{labels}</svg>')


def _progression_html(prog: dict | None, kind: str | None = None) -> str:
    """Progresión por ejercicio repetido: resumen, una fila con gráfica por ejercicio y lo aún no repetido.
    `kind`: None = todos, "fuerza" o "halterofilia" (se filtra por el nombre del ejercicio)."""
    if not isinstance(prog, dict) or not prog.get("items"):
        return ""
    from . import progression as _pg, training_blocks as _tb
    items = prog["items"]
    if kind:
        items = [x for x in items if _tb.is_olympic(x["name"]) == (kind == "halterofilia")]
        if not items:
            return ""
    summ = _pg.summary(items) if kind else (prog.get("summary") or {})
    comp = [s for s in items if s["comparable"]]
    once = [s for s in items if not s["comparable"]]
    mark = {"up": ("▲", "sube"), "down": ("▼", "baja"), "flat": ("=", "igual")}
    rows = ""
    for s in comp:
        pts = s["points"]
        last = pts[-1]
        sym, word = mark[s["state"]]
        d = s["delta_prev"]
        delta = f'{sym} {word}' + (f' {"+" if d > 0 else "−"}{_kg(abs(d))} kg' if abs(d) > 0.01 else "")
        notes = []
        if s.get("new_best"):
            notes.append("Es tu mejor carga registrada en este ejercicio.")
        if s.get("rep_scheme_differs"):
            notes.append(f'Las repeticiones de la mejor serie cambian ({_kg(pts[-2]["top_reps"])} → {_kg(last["top_reps"])}): compara con cautela.')
        if s.get("volume_change_pct") is not None:
            notes.append(f'Volumen frente a la sesión anterior: {s["volume_change_pct"]:+d} %.')
        elif not (last["volume_complete"] and pts[-2]["volume_complete"]):
            notes.append("Volumen no comparable: hay series sin carga registrada.")
        table = "".join(
            f'<tr><td>{_ddmm(p["date"])}</td><td class="num">{_kg(p["top_load"])} kg × {_kg(p["top_reps"])}</td>'
            f'<td class="num">{p["work_sets"]}</td><td class="num">{_kg(round(p["volume"]))}{"" if p["volume_complete"] else "*"}</td>'
            f'<td class="num">{_kg(p["rpe"]) if p["rpe"] is not None else "—"}</td></tr>' for p in reversed(pts))
        name = s["name"][:1].upper() + s["name"][1:]
        rows += (f'<details class="pg"><summary><span class="pg-name">{_esc(name)}<small>{_esc(s["unit"])} · {s["sessions"]} sesiones</small></span>'
                 f'{_prog_svg(pts)}<span class="pg-now">{_kg(last["top_load"])} kg<small class="pg-d {s["state"]}">{_esc(delta)}</small></span></summary>'
                 f'<div class="pg-body">{_prog_svg(pts, True)}'
                 '<div class="scroll"><table><tr><th>Fecha</th><th>Mejor serie</th><th>Series</th><th>Volumen kg</th><th>RPE</th></tr>'
                 f'{table}</table></div>'
                 + "".join(f'<p class="pg-note">{_esc(n)}</p>' for n in notes)
                 + ('<p class="pg-note">* volumen mínimo: alguna serie sin carga registrada.</p>' if not last["volume_complete"] else "")
                 + "</div></details>")
    stats = ""
    if summ.get("available"):
        stats = (f'<p class="pg-sum"><b>{summ["up"]}</b> ▲ suben · <b>{summ["flat"]}</b> = igual · <b>{summ["down"]}</b> ▼ bajan'
                 f'<small>mejor carga frente a la sesión anterior, {summ["comparable"]} ejercicios repetidos</small></p>')
    else:
        stats = '<p class="pg-sum"><small>Aún no hay ningún ejercicio repetido en dos sesiones con cargas registradas.</small></p>'
    once_html = ""
    if once:
        lis = "".join(f'<li>{_esc(s["name"][:1].upper() + s["name"][1:])} <span class="weight">{_kg(s["points"][-1]["top_load"])} kg · '
                      f'{_ddmm(s["points"][-1]["date"])}</span></li>' for s in once)
        once_html = (f'<details class="pg-once"><summary>Todavía sin repetir ({len(once)})</summary><ul class="clean">{lis}</ul>'
                     '<p class="pg-note">Aparecerán arriba cuando los hagas en otra sesión.</p></details>')
    caution = f'<p class="h2sub pg-caution">{_esc(summ["caution"])}</p>' if summ.get("caution") else ""
    return ('<section class="card" id="progresion' + ("-" + kind if kind else "") + '" aria-label="Progresión por ejercicio"><h2>Progresión por ejercicio</h2>'
            '<p class="h2sub">mejor carga de cada sesión en los ejercicios con carga registrada · el historial se conserva aunque pasen los 28 días</p>'
            + stats + rows + once_html + caution + "</section>")


def _bars_svg(items: list[dict], unit: str = "", label: str = "") -> str:
    """Barras verticales sencillas: items = {label, value, text, soft (semana en curso), mark (valor mínimo)}."""
    w, h, padt, padb = 300, 118, 18, 20
    n = len(items)
    top = max((i["value"] for i in items), default=0) or 1
    slot = w / max(n, 1)
    bw = min(34.0, slot * 0.62)
    out = ""
    for k, it in enumerate(items):
        cx = slot * k + slot / 2
        bh = (h - padt - padb) * it["value"] / top
        y = h - padb - bh
        cls = "bar soft" if it.get("soft") else "bar"
        if it["value"] > 0:
            out += (f'<path d="M{cx - bw / 2:.1f},{h - padb:.1f} V{y + 4:.1f} q0,-4 4,-4 h{bw - 8:.1f} q4,0 4,4 V{h - padb:.1f}Z" class="{cls}">'
                    f'<title>{_esc(it["label"])}: {_esc(it["text"])}</title></path>')
            out += f'<text x="{cx:.1f}" y="{y - 4:.1f}" text-anchor="middle" class="bar-val">{_esc(it["text"])}</text>'
        else:
            out += f'<text x="{cx:.1f}" y="{h - padb - 4:.1f}" text-anchor="middle" class="bar-val none">—</text>'
        out += f'<text x="{cx:.1f}" y="{h - 5}" text-anchor="middle" class="bar-lab">{_esc(it["label"])}</text>'
    out += f'<line x1="0" x2="{w}" y1="{h - padb}" y2="{h - padb}" class="bar-axis"/>'
    return f'<svg class="bars" viewBox="0 0 {w} {h}" role="img" aria-label="{_esc(label)}">{out}</svg>'


def _rpe_pill(rpe) -> str:
    if not isinstance(rpe, (int, float)):
        return '<span class="rpe-pill none">RPE —</span>'
    tone = "hi" if rpe >= 9 else "mid" if rpe >= 7 else "lo"
    return f'<span class="rpe-pill {tone}">RPE {_kg(rpe)}</span>'


def _day_name(date_s: str) -> str:
    from datetime import date as _d
    d = _d.fromisoformat(date_s)
    return ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")[d.weekday()] + " " + _ddmm(date_s)


def _weekly_html(weeks: list[dict], title: str, sub: str) -> str:
    if not weeks or not any(w["volume"] for w in weeks):
        return ""
    items = [{"label": _ddmm(w["start"]), "value": w["volume"], "soft": w["current"],
              "text": (f'{w["volume"]:,}'.replace(",", ".") + ("*" if not w["complete"] else ""))} for w in weeks]
    lab = f"{title}: " + ", ".join(f'semana del {_ddmm(w["start"])} {w["volume"]} kg' for w in weeks)
    note = ("* hay series sin carga registrada: es un mínimo. " if any(not w["complete"] for w in weeks) else "")
    return (f'<section class="card"><h2>{_esc(title)}</h2><p class="h2sub">{_esc(sub)}</p>{_bars_svg(items, "kg", lab)}'
            f'<p class="pg-note">kg × repeticiones con carga registrada · semanas desde el lunes indicado · la clara es la semana en curso. {note}'
            'Volumen mínimo verificado, sin atribuir causas.</p></section>')


def _hr_slot(activity_id) -> str:
    """Hueco para la FC de la sesión (V7.20): el script lo rellena con la curva de Intervals si existe."""
    return f'<div class="hrmini" data-id="{_esc(activity_id)}" hidden></div>' if activity_id else ""


def _lifts_html(sessions: list[dict], title: str, empty: str) -> str:
    if not sessions:
        return f'<section class="card"><h2>{_esc(title)}</h2><p class="h2sub">{_esc(empty)}</p></section>'
    cards = ""
    for s in sessions:
        rows = ""
        for e in s["exercises"]:
            name = e["name"][:1].upper() + e["name"][1:]
            vol = (f'{_kg(round(e["volume"]))} kg' + ("" if e["volume_complete"] else "*")) if e["unit"] == "barra" else ""
            rows += (f'<li><div class="lf-top"><span class="lf-name">{_esc(name)}<small>{_esc(e["unit"])}</small></span>'
                     f'<span class="lf-best">{_kg(e["top_load"])} kg<small>× {_kg(e["top_reps"])}</small></span></div>'
                     f'<p class="lf-sets">{_esc(e["sets"])}</p>'
                     f'<p class="lf-meta">{e["work_sets"]} series' + (f' · volumen {vol}' if vol else "") + "</p></li>")
        cards += (f'<article class="lf"><header><b>{_day_name(s["date"])}</b>{_rpe_pill(s["rpe"])}</header>'
                  f'<p class="lf-title">{_esc(s["title"])}</p><ul class="clean">{rows}</ul>{_hr_slot(s.get("activity_id"))}</article>')
    return (f'<section class="card"><h2>{_esc(title)}</h2><p class="h2sub">series como repeticiones @ kg · «3× 8 @ 60» = tres series · mejor serie a la derecha</p>{cards}'
            '<p class="pg-note">Solo se muestra lo confirmado en el registro de cada sesión; las barras vacías de calentamiento no cuentan. '
            '* volumen mínimo: alguna serie sin carga.</p></section>')


def _metcons_html(metcons: list[dict]) -> str:
    if not metcons:
        return '<section class="card"><h2>Metcons</h2><p class="h2sub">Aún no hay metcons registrados con detalle.</p></section>'
    rp = list(reversed([m for m in metcons if isinstance(m["rpe"], (int, float))][:8]))
    chart = ""
    if len(rp) >= 2:
        items = [{"label": _ddmm(m["date"]), "value": float(m["rpe"]), "text": _kg(m["rpe"]), "soft": False} for m in rp]
        lab = "RPE por metcon: " + ", ".join(f'{_ddmm(m["date"])} {_kg(m["rpe"])}' for m in rp)
        chart = f'<p class="mc-cap">RPE de los últimos {len(rp)} metcons</p>{_bars_svg(items, "", lab)}'
    cards = ""
    for m in metcons:
        presc = "".join(f"<li>{_esc(x)}</li>" for x in m["prescription"])
        times = "".join(f'<span class="rx-chip">{_esc(t)}</span>' for t in m["timing"])
        if m["minutes"] is not None:
            times += f'<span class="rx-chip">{_kg(m["minutes"])} min grabados</span>'
        hr = m.get("hr") or {}
        if hr.get("average") and hr.get("max"):
            times += f'<span class="rx-chip hrchip">FC {_kg(round(hr["average"]))} / {_kg(round(hr["max"]))} lpm</span>'
        rounds = ""
        if m["rounds"]:
            vals = m["rounds"]["values"]
            its = [{"label": f"R{i + 1}", "value": v, "text": _kg(v), "soft": False} for i, v in enumerate(vals)]
            rounds = (f'<p class="mc-cap">{_esc(m["rounds"]["label"][:1].upper() + m["rounds"]["label"][1:])}</p>'
                      + _bars_svg(its, "", "Repeticiones por ronda: " + ", ".join(_kg(v) for v in vals)))
        cards += (f'<article class="mc"><header><span class="mc-fmt">{_esc(m["format"])}' + (" · parejas" if m["partner"] else "")
                  + f'</span><span class="mc-date">{_day_name(m["date"])}</span>{_rpe_pill(m["rpe"])}</header>'
                  + (f'<ul class="mc-presc clean">{presc}</ul>' if presc else "")
                  + (f'<p class="mc-res">{_esc(m["result"])}</p>' if m["result"] else '<p class="mc-res none">Resultado no registrado</p>')
                  + (f'<div class="chips">{times}</div>' if times else "") + rounds
                  + (f'<p class="pg-note">{_esc(m["note"])}</p>' if m["note"] else "") + _hr_slot(m.get("activity_id")) + "</article>")
    return ('<section class="card"><h2>Metcons</h2><p class="h2sub">fórmula, resultado y tiempos tal como constan · el cronómetro oficial y el reloj se muestran por separado</p>'
            + chart + cards + '<p class="pg-note">Los metcons no son comparables entre sí salvo que repitan formato y ejercicios.</p></section>')


def _training_html(tb: dict | None, prog: dict | None) -> str:
    """Entrenos: resumen de 7 días y un selector Fuerza · Halterofilia · Metcons · Sesiones."""
    if not isinstance(tb, dict):
        return _progression_html(prog)
    s = tb.get("summary7") or {}
    chips = (f'<li><b>{s.get("fuerza", 0)}</b><span>fuerza</span></li><li><b>{s.get("halterofilia", 0)}</b><span>halterofilia</span></li>'
             f'<li><b>{s.get("metcons", 0)}</b><span>metcons</span></li>'
             f'<li><b>{_kg(s["metcon_rpe_mean"]) if s.get("metcon_rpe_mean") is not None else "—"}</b><span>RPE medio metcons</span></li>')
    head = (f'<section class="card tbhead"><h2>Últimos 7 días</h2><ul class="tbsum">{chips}</ul>'
            '<div class="seg" role="tablist" aria-label="Tipo de entrenamiento">'
            '<button role="tab" data-pane="fuerza" aria-selected="true">Fuerza</button>'
            '<button role="tab" data-pane="halterofilia" aria-selected="false">Halterofilia</button>'
            '<button role="tab" data-pane="metcons" aria-selected="false">Metcons</button>'
            '<button role="tab" data-pane="sesiones" aria-selected="false">Sesiones</button></div></section>')
    fz, hl = tb.get("fuerza") or {}, tb.get("halterofilia") or {}
    panes = {
        "fuerza": (_weekly_html(fz.get("weekly"), "Volumen de fuerza", "barra, por semana")
                   + _progression_html(prog, "fuerza")
                   + _lifts_html(fz.get("sessions"), "Sesiones de fuerza", "Aún no hay sesiones de fuerza con cargas registradas.")),
        "halterofilia": (_weekly_html(hl.get("weekly"), "Volumen de halterofilia", "barra, por semana")
                         + _progression_html(prog, "halterofilia")
                         + _lifts_html(hl.get("sessions"), "Sesiones de halterofilia", "Aún no hay sesiones de halterofilia con cargas registradas.")),
        "metcons": _metcons_html(tb.get("metcons") or []),
    }
    return head + "".join(f'<div class="tbpane" data-pane="{k}"{"" if k == "fuerza" else " hidden"}>{v}</div>' for k, v in panes.items())


def _weight_svg(points: list[dict]) -> str:
    from datetime import date as _d
    w, h, px_, py_ = 300, 130, 24, 26
    xs = [(_d.fromisoformat(p["date"]) - _d.fromisoformat(points[0]["date"])).days for p in points]
    span = max(xs) or 1
    vals = [p["weight"] for p in points]
    lo, hi = min(vals) - 0.6, max(vals) + 0.6

    def X(i):
        return px_ + xs[i] / span * (w - 2 * px_)

    def Y(v):
        return h - py_ - (v - lo) / (hi - lo) * (h - 2 * py_ - 6)
    line = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
    dots = labs = ""
    for i, p in enumerate(points):
        last = i == len(points) - 1
        cls = "wt-last" if last else "wt-dot" + (" derived" if p["derived"] else "")
        dots += f'<circle cx="{X(i):.1f}" cy="{Y(p["weight"]):.1f}" r="{4.5 if last else 3.4}" class="{cls}"><title>{_ddmm(p["date"])}: {_kg(p["weight"])} kg{" (calculado)" if p["derived"] else ""}</title></circle>'
        labs += (f'<text x="{X(i):.1f}" y="{Y(p["weight"]) - 9:.1f}" text-anchor="middle" class="pg-val">{_kg(p["weight"])}</text>'
                 f'<text x="{X(i):.1f}" y="{h - 6}" text-anchor="middle" class="pg-date">{_ddmm(p["date"])}</text>')
    label = "Peso: " + ", ".join(f'{_ddmm(p["date"])} {_kg(p["weight"])} kg' for p in points)
    return (f'<svg class="wt-svg" viewBox="0 0 {w} {h}" role="img" aria-label="{_esc(label)}">'
            f'<polyline points="{line}" class="wt-line"/>{dots}{labs}</svg>')


def _weight_html(wt: dict | None) -> str:
    if not isinstance(wt, dict):
        return ""
    cur = f'{_kg(wt["current"])} kg'
    stats = f'<li><b>{cur}</b><span>última medición · {_ddmm(wt["current_date"])}</span></li>'
    if wt.get("mean7") is not None:
        stats += f'<li><b>{_kg(wt["mean7"])} kg</b><span>media de {wt["n7"]} lecturas en 7 días</span></li>'
    if "delta_prev" in wt:
        d = wt["delta_prev"]
        sign = "+" if d > 0 else "−" if d < 0 else ""
        stats += f'<li><b>{sign}{_kg(abs(d))} kg</b><span>frente al {_ddmm(wt["prev_date"])}</span></li>'
    if "delta_first" in wt and wt["first_date"] != wt.get("prev_date"):
        d = wt["delta_first"]
        sign = "+" if d > 0 else "−" if d < 0 else ""
        stats += f'<li><b>{sign}{_kg(abs(d))} kg</b><span>en {wt["span_days"]} días</span></li>'
    stale = '<p class="pg-note">La última medición tiene más de 7 días.</p>' if wt.get("stale") else ""
    chart = _weight_svg(wt["points"]) if len(wt["points"]) >= 2 else ""
    derived = '<p class="pg-note">El punto hueco está calculado a partir de una diferencia que muestra la app, no es una lectura directa.</p>' if wt.get("has_derived") else ""
    return ('<section class="card" id="peso" aria-label="Peso corporal"><h2>Peso</h2>'
            '<p class="h2sub">báscula Xiaomi · Zepp Life · lo que muestras o dictas</p>'
            f'<ul class="tbsum wt-stats">{stats}</ul>{chart}{stale}{derived}'
            '<p class="pg-note">Compara lecturas hechas a la misma hora (mejor por la mañana, en ayunas): el peso varía 1–2 kg en el día por comida, '
            'hidratación y entrenos. Descriptivo, sin causas; no es una valoración médica.</p></section>')


def _glance_html(chips: list[dict] | None) -> str:
    if not chips:
        return ""
    cells = "".join(f'<li class="gl {_esc(c["tone"])}"><span class="gl-l"><i aria-hidden="true"></i>{_esc(c["label"])}</span>'
                    f'<span class="gl-v">{_esc(c["value"])}</span><span class="gl-s">{_esc(c["sub"])}</span></li>' for c in chips)
    return f'<section class="glance" aria-label="De un vistazo"><ul class="clean">{cells}</ul></section>'


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def render(result: dict, extras: dict | None = None) -> str:
    """``extras`` (solo la web publicada): puntualidad, histórico, fuerza y etiquetas PWA."""
    from .report import rpe_by_day
    extras = extras or {}
    data = dict(result)
    if extras.get("hr_curves"):
        data["hr_curves"] = extras["hr_curves"]
    if extras.get("session_effort"):
        data["session_effort"] = extras["session_effort"]
    data["_rpe_days"] = rpe_by_day(result.get("sessions_28d") or [], result.get("trend_28d") or [], result["date"], 28)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    rd = result["readiness"]
    zone = (result.get("decision") or {}).get("zone") or rd["zone"]
    tone, icon = ZONE_UI.get(zone, ZONE_UI["unavailable"])
    title = "Rendimiento y recuperación"
    extra = _extra_sections(result, extras)
    head = PWA_HEAD if extras.get("pwa") else ""
    values = {"TITLE": title, "HEAD": head, "BANNER": extra["banner"], "HOYTOP": extra["hoytop"], "CAMBIOS": extra["cambios"], "HOY": extra["hoy"], "TEND": extra["tendencias"],
              "ENT": extra["entrenos"], "SIS": extra["sistema"], "DATE": _esc(result["date"]),
              "TONE": tone, "ICON": icon, "DATA": payload}
    # una sola pasada: el contenido sustituido nunca se vuelve a interpretar como marcador
    return re.sub(r"\{\{(TITLE|HEAD|BANNER|HOYTOP|CAMBIOS|HOY|TEND|ENT|SIS|DATE|TONE|ICON|DATA)\}\}", lambda m: values[m.group(1)], TEMPLATE)


PWA_HEAD = """<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#2a78d6">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Recuperación">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-180.png">
<script>if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}))}</script>"""


def _punctuality_html(pun: dict | None) -> str:
    if not pun or not pun.get("total"):
        return ""
    rows = "".join(
        f"<tr><td>{_esc(x['date'][8:10] + '/' + x['date'][5:7])}</td><td>{_esc(x['slot'])}</td>"
        f"<td class='num'>{_esc(x['sync'] or '—')}</td><td class='num'>{_esc(x['ready'] or 'sin informe')}</td>"
        f"<td class='num'>{'—' if x['minutes_margin'] is None else _esc(str(x['minutes_margin']) + ' min')} "
        f"{'<span class=pos>✓</span>' if x['on_time'] else '<span class=neg>!</span>'}</td></tr>" for x in pun["slots"])
    return (f'<section class="card"><h2>Puntualidad · {pun["on_time"]} de {pun["total"]} a tiempo</h2>'
            '<p class="h2sub">informe listo antes de que ChatGPT lo lea (09:05, 17:10, 23:10) · últimos 7 días</p>'
            '<div class="scroll"><table><thead><tr><th>Fecha</th><th>Franja</th><th class="num">Sync</th>'
            f'<th class="num">Informe</th><th class="num">Margen</th></tr></thead><tbody>{rows}</tbody></table></div></section>')


def _history_html(items: list | None) -> str:
    if not items:
        return ""
    zone_es = {"green": "verde", "yellow": "ámbar", "red": "rojo", "unavailable": "pendiente"}
    lis = "".join(
        f"<li><a href='{_esc(x['url'])}' rel='noopener'><span class='hz z-{_esc(x.get('zone') or 'unavailable')}'></span>"
        f"{_esc(x['label'])}</a> <span class='weight'>{_esc(zone_es.get(x.get('zone'), '—'))}"
        f"{' · ' + _esc(x['report_id']) if x.get('report_id') else ''}</span></li>" for x in items)
    return ('<section class="card" id="informes"><h2>Informes anteriores</h2><p class="h2sub">cada enlace abre el informe tal como se '
            f'publicó, con sus gráficas, en GitHub</p><ul class="clean hist">{lis}</ul></section>')


def _delivery_html(d: dict | None) -> str:
    """Estado final del ciclo: una línea de semáforos (✓ / … / ✗) con la hora cuando consta, y el alcance de «notificación enviada»."""
    if not d or not d.get("stages"):
        return ""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    icon = {"ok": "✓", "pending": "…", "failed": "✗", "skipped": "–", "unknown": "?"}
    cls = {"ok": "ok", "pending": "wait", "failed": "bad", "skipped": "", "unknown": ""}
    names = {"sync": "Sync", "heart": "FC", "advanced": "Analítica", "crossfit": "CrossFit", "web": "Web", "notification": "Aviso"}
    title = {"complete": "Ciclo completo", "complete_without_notification": "Ciclo completo (sin aviso)",
             "pending": "Ciclo en curso", "failed": "Ciclo con fallos", "unconfirmed": "Ciclo sin confirmar del todo"}.get(d.get("state"), "Estado del ciclo")

    def hour(v):
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Madrid")).strftime("%H:%M")
        except (ValueError, TypeError):
            return ""
    steps = "".join(
        f"<li class='{cls.get(v.get('state'), '')}' title='{_esc(v.get('note') or '')}'><span class='sd' aria-hidden='true'>{icon.get(v.get('state'), '?')}</span>"
        f"{names.get(k, k)}<small>{hour(v.get('at')) or '&nbsp;'}</small></li>" for k, v in d["stages"].items())
    return ('<section class="card" id="ciclo" aria-label="Estado final del ciclo"><h2>' + _esc(title) + '</h2>'
            f'<p class="h2sub">ciclo {_esc(d.get("cycle_id") or "—")} · {_esc(d.get("scope") or "")}</p>'
            f'<ol class="steps">{steps}</ol></section>')


def _days_html(days: list | None) -> str:
    if not days:
        return ""
    zone_es = {"green": "verde", "yellow": "ámbar", "red": "rojo", "unavailable": "pendiente"}
    lis = "".join(
        f"<li><a href='dia/{_esc(x['date'])}.html'><span class='hz z-{_esc(x.get('zone') or 'unavailable')}'></span>"
        f"{_esc(x['date'][8:10] + '/' + x['date'][5:7])}</a> <span class='weight'>{_esc(zone_es.get(x.get('zone'), '—'))}"
        f"{' · ' + str(round(x['score'])) if isinstance(x.get('score'), (int, float)) else ''}</span></li>" for x in days)
    return ('<section class="card" id="dias"><h2>Panel de días anteriores</h2><p class="h2sub">abre el panel tal como quedó el último '
            f'informe de cada día (últimos {len(days)} días)</p><ul class="clean hist">{lis}</ul></section>')


def _tonight_html(t: dict | None) -> str:
    """Tarjeta «Esta noche»: necesidad de sueño estimada, componentes y consejo de turno."""
    if not t or not t.get("need"):
        return ""
    n = t["need"]
    f = lambda v: f"{v:.1f}".replace(".", ",")  # noqa: E731
    rows = [("Base", f(n["base_h"])), ("Carga de ayer", "+" + f(n["load_add_h"])),
            ("Deuda reciente (3 noches)", "+" + f(n["debt_add_h"])),
            ("Siesta de hoy", ("−" + f(n["nap_today_h"])) if n.get("naps_known") else "sin dato")]
    lis = "".join(f"<li><span>{_esc(a)}</span><b>{_esc(b)} h</b></li>" if b != "sin dato" else f"<li><span>{_esc(a)}</span><b>sin dato</b></li>"
                  for a, b in rows)
    tip = f"<p class='tip-line'>{_esc(t['tip'])}</p>" if t.get("tip") else ""
    return ('<section class="card" id="noche" aria-label="Esta noche"><h2>Esta noche</h2>'
            '<p class="h2sub">necesidad de sueño estimada (heurística sin validar)</p>'
            f'<div class="big">{f(n["need_tonight_h"])} <small>h</small></div>'
            f'<p class="h2sub">deuda de las últimas 3 noches: {f(n["debt_3n_h"])} h · de 7 noches: {f(n["debt_7n_h"])} h '
            '(incluyen el sueño diurno tras turno y descuentan siestas)</p>'
            f'<p class="h2sub">el modelo experimental cuenta solo 3 noches y no descuenta siestas: {f(n["debt_3n_model_h"])} h</p>'
            f'<ul class="clean parts">{lis}</ul>{tip}</section>')


def _plan_html(plan: list | None) -> str:
    if not plan:
        return ""
    kind = {"hard": ("Exigente", "k-hard"), "moderate": ("Moderada", "k-mod"), "light": ("Suave", "k-light"), "rest": ("Descanso", "k-rest")}
    items = "".join(
        f"<li class='{kind[r['kind']][1]}'><div class='pd'>{_esc(r['dow'])}<br><b>{_esc(r['date'][8:10])}</b></div>"
        f"<div><b>{kind[r['kind']][0]}</b> · <span class='weight'>{_esc(r['shift'])}</span><br>"
        f"<span class='why'>{_esc(r['why'])}</span></div></li>" for r in plan)
    return ('<section class="card" id="plan" aria-label="Próximos 7 días"><h2>Próximos 7 días</h2>'
            '<p class="h2sub">plan orientativo por reglas: turnos, sesiones duras recientes y la decisión de hoy · '
            f'máx. 3 sesiones con RPE ≥ 8 por semana</p><ol class="clean plan">{items}</ol></section>')


def _spark(values: list, ok: bool) -> str:
    vals = [v for v in values if isinstance(v, (int, float))]
    if len(vals) < 3:
        return ""
    lo, hi = min(vals), max(vals)
    r = (hi - lo) or 1
    n = len(values)
    pts = [(i / (n - 1) * 80, 4 + (1 - (v - lo) / r) * 20) for i, v in enumerate(values) if isinstance(v, (int, float))]
    d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    x, y = pts[-1]
    return (f"<svg class='chg-sp' viewBox='0 0 80 28' aria-hidden='true'><path d='{d}' fill='none' stroke-width='2' stroke-linecap='round' "
            f"stroke-linejoin='round'/><circle cx='{x:.1f}' cy='{y:.1f}' r='3'/></svg>")


def _changes_html(c: dict | None, official: tuple | None = None, trend: list | None = None) -> str:
    """Apartado «Cambios recientes»: una tarjeta por indicador que cambia frente a ayer, con valor de hoy, diferencia,
    flecha de color (favorable / desfavorable) y la curva de los últimos 7 días. Diferencias observadas, sin causas."""
    if not c or not c.get("available"):
        return ""
    from .why_changed import FIELDS
    f = lambda v, d: f"{v:.{d}f}".replace(".", ",")  # noqa: E731
    keys = {label: key for key, label, *_ in FIELDS}
    rows = [t for t in (trend or []) if isinstance(t, dict)]
    last7 = lambda k: [t.get(k) for t in rows[-7:]]  # noqa: E731
    cards = []
    if official:
        cards.append(("Recuperación", f(official[1], 0), "", f"{official[1] - official[0]:+.0f}".replace("-", "−"), official[1] >= official[0],
                      _spark(last7("v2_score"), True), official[1] >= official[0]))
    for i in c["items"]:
        delta = i.get("delta") if i.get("delta") is not None else i["to"] - i["from"]
        chip = "" if delta is None else (f"{delta:+.{i['dec']}f}".replace(".", ",").replace("-", "−") + (i["unit"] or ""))
        cards.append((i["label"], f(i["to"], i["dec"]), i["unit"].strip(), chip, i["favorable"], _spark(last7(keys.get(i["label"], "")), i["favorable"]),
                      (delta or 0) >= 0))
    if not cards:
        return ('<section class="card chg" id="cambios" aria-label="Cambios recientes"><h2>Cambios recientes</h2>'
                '<p class="h2sub">Ningún indicador cambió lo bastante frente a ayer como para destacarlo.</p></section>')
    body = "".join(
        f"<div class='chg-card {'pos' if ok else 'neg'}'><div class='chg-top'><span class='chg-l'>{_esc(lab)}</span>"
        f"<i class='chg-ar' aria-hidden='true'>{'↑' if up else '↓'}</i></div>"
        f"<div class='chg-val'><b>{_esc(val)}</b><small>{_esc(unit)}</small></div>"
        f"<div class='chg-bot'><span class='chg-chip'>{_esc(chip)}</span>{sp}</div></div>"
        for lab, val, unit, chip, ok, sp, up in cards)
    return ('<section class="card chg" id="cambios" aria-label="Cambios recientes"><h2>Cambios recientes</h2>'
            '<p class="h2sub">hoy frente a ayer · verde = favorable, rojo = desfavorable · curva = últimos 7 días · diferencias observadas, no causas</p>'
            f'<div class="chg-grid">{body}</div></section>')


def _extra_sections(result: dict, extras: dict | None = None) -> dict:
    """Resumen de tres líneas, RPE frente al máximo del día y la semana (mismo contenido que el informe)."""
    import re
    from .readiness import GUIDANCE
    if (extras or {}).get("snapshot"):
        return {"banner": (f'<section class="card" style="margin-bottom:16px"><b>Instantánea del {_esc(extras["snapshot"])}</b> · '
                           '<a href="../index.html">← Volver al panel actual</a></section>'),
                "hoytop": "", "cambios": "", "hoy": "", "tendencias": "", "entrenos": "", "sistema": ""}
    from .report import summary_block
    from .weekly import weekly_summary
    dec = result.get("decision") or {}
    zone = dec.get("zone") or "unavailable"
    g = dec.get("guidance") or GUIDANCE.get(zone) or GUIDANCE["unavailable"]
    extras = extras or {}
    lines = [x[2:] for x in summary_block(result, dec, g, zone) if x.startswith("> **")]

    def md_inline(t):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(t))
    summary = "".join(f"<p style='margin:4px 0'>{md_inline(x)}</p>" for x in lines)
    try:
        w = weekly_summary(result)
    except Exception:  # noqa: BLE001 — la tarjeta semanal nunca rompe el panel
        w = None
    week = ""
    if w:
        def f(v, dg=0):
            return "—" if v is None else (f"{v:.{dg}f}".replace(".", ","))
        rows = [("Sesiones", w["sessions"], w["sessions_prev"], 0), ("Minutos", w["minutes"], w["minutes_prev"], 0),
                ("sRPE", w["srpe"], w["srpe_prev"], 0), ("HRV media (ms)", w["hrv"], w["hrv_prev"], 1),
                ("FC reposo (lpm)", w["rhr"], w["rhr_prev"], 1), ("Sueño medio (h)", w["sleep"], w["sleep_prev"], 2)]
        week = ("<table><thead><tr><th></th><th class='num'>Esta semana</th><th class='num'>Semana previa</th></tr></thead><tbody>"
                + "".join(f"<tr><td>{_esc(n)}</td><td class='num'>{f(a, d)}</td><td class='num'>{f(b, d)}</td></tr>"
                          for n, a, b, d in rows) + "</tbody></table>")
    full_html = ('<a class="cta" href="informe_completo.html"><span class="cta-ico">📄</span>'
                 '<span><strong>Abrir el informe completo</strong><small>resumen, 7 secciones y recomendaciones</small></span>'
                 '<span class="cta-go" aria-hidden="true">›</span></a>' if extras.get("full_report") else "")
    from .brief import official_change
    changes = _changes_html(extras.get("changes"), official_change(result.get("trend_28d") or [], result.get("date") or ""),
                           result.get("trend_28d") or [])
    try:
        from . import brief
        sents = brief.compose(result, extras.get("tonight"))
    except Exception as exc:  # noqa: BLE001 — opcional
        from . import optional_blocks
        optional_blocks.failed("web:brief", exc)
        sents = []
    brief_html = ('<section class="card brief" aria-label="Hoy en breve"><h2>Hoy en breve</h2>'
                  + "".join(f"<p>{md_inline(x)}</p>" for x in sents) + "</section>") if sents else ""
    ai = extras.get("ai_lead")
    ai_lines = [ai] if isinstance(ai, str) else [x for x in (ai or []) if isinstance(x, str) and x.strip()]
    ai_html = ('<section class="card brief ai" aria-label="Análisis de Claude"><h2>Resumen de hoy · Claude</h2>'
               + "".join(f"<p>{md_inline(x)}</p>" for x in ai_lines)
               + '<p class="h2sub">redactado por un modelo de IA con los datos del ciclo · detalle y plan de 7 días en el informe completo</p></section>') if ai_lines else ""
    try:
        from . import glance
        glance_html = _glance_html(glance.compose(result, extras.get("glance_shifts"), extras.get("progression")))
    except Exception as exc:  # noqa: BLE001 — opcional
        from . import optional_blocks
        optional_blocks.failed("web:glance", exc)
        glance_html = ""
    # el resumen de reglas solo es el respaldo cuando no hay resumen de Claude del ciclo vigente
    top_block = glance_html + changes + (ai_html or brief_html) + ('' if ai_html or (extras.get('changes') and extras['changes'].get('available')) else f'<section class="card" aria-label="Resumen de hoy"><h2>En tres líneas</h2>{summary}</section>')
    calendar_html = ('<section class="card" id="calendario" aria-label="Calendario"><h2>Últimas 4 semanas</h2>'
            '<p class="h2sub">color = decisión del día (o modelo experimental, atenuado, si no se guardó) · número = RPE máximo · '
            'anillo rojo = por encima del máximo · toca un día para ver el detalle</p>'
            '<div class="cal-head"><span>L</span><span>M</span><span>X</span><span>J</span><span>V</span><span>S</span><span>D</span></div>'
            '<div class="cal" id="cal"></div><div class="cal-detail" id="cal-detail"></div></section>')
    week_html = ('<section class="grid cols-2" id="semana"><div class="card"><h2>RPE frente al máximo del día</h2>'
            '<p class="h2sub">barra = sesión más dura · raya = máximo que permitía la decisión · rojo = por encima</p>'
            '<div class="legend"><span><i class="key-dot"></i>Dentro</span><span><i class="key-dot" style="background:var(--critical)"></i>Por encima</span>'
            '<span><i class="key-ref" style="border-top:3px solid var(--text-2)"></i>Máximo del día</span></div>'
            '<div class="chart" id="c-rpe"></div></div>'
            '<div class="card"><h2>Esta semana</h2><p class="h2sub">últimos 7 días frente a los 7 anteriores · detalle en '
            f'<code>informe_semanal.md</code></p><div class="scroll">{week}</div></div></section>')
    # Una pestaña por pregunta: ¿qué hago hoy? · ¿cómo voy? · ¿qué he entrenado? · ¿funciona el sistema?
    return {"banner": "",
            "hoytop": top_block, "cambios": changes,
            "hoy": full_html + _tonight_html(extras.get("tonight")) + _plan_html(extras.get("plan")),
            "tendencias": _weight_html(extras.get("weight")) + calendar_html + week_html,
            "entrenos": _training_html(extras.get("training_blocks"), extras.get("progression")),
            "sistema": _delivery_html(extras.get("delivery")) + _punctuality_html(extras.get("punctuality"))
                       + _days_html(extras.get("days")) + _history_html(extras.get("history"))}


_TEMPLATE_HTML = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
{{HEAD}}
<style>
{{CSS}}
</style>
</head>
<body>
<script>document.documentElement.classList.add('js')</script>
<div class="wrap">
  <header>
    <div>
      <h1>{{TITLE}}</h1>
      <div class="sub" id="sub">{{DATE}}</div>
    </div>
    <span class="badge" id="badge">Modelo experimental</span>
  </header>

  {{BANNER}}

  <div class="grid tab on" id="tab-hoy" data-tab="hoy">
    <section class="card hero tone-{{TONE}}" id="hoy" aria-label="Disponibilidad de hoy">
      <div class="hero-main">
        <div class="heroring"><svg viewBox="0 0 120 120" aria-hidden="true"><circle class="trk" cx="60" cy="60" r="52"/><circle class="arc" id="heroarc" cx="60" cy="60" r="52" transform="rotate(-90 60 60)"/></svg>
        <div class="score" id="score">—</div></div>
        <div class="hero-txt">
          <div class="h2sub">Decisión de hoy · puntuación oficial</div>
          <div class="pill"><span class="dot" aria-hidden="true">{{ICON}}</span><span class="pill-text" id="zone-label"></span></div>
          <div class="meta" id="confidence"></div>
        </div>
      </div>
      <div class="hero-side">
        <p class="guidance" id="guidance"></p>
        <div class="rx" id="rx"></div>
      </div>
    </section>

    {{HOYTOP}}

    <section class="rings" id="rings" aria-label="Sueño, HRV y carga"></section>

    <section class="card" id="porque" aria-label="Por qué esta puntuación">
      <h2>Por qué esta puntuación</h2>
      <p class="h2sub">lo que más ha pesado hoy frente a tu normalidad</p>
      <ul class="clean drivers" id="drivers"></ul>
      <ul class="clean notes" id="notes" style="margin-top:10px"></ul>
    </section>

    {{HOY}}
  </div>

  <div class="grid tab" id="tab-tendencias" data-tab="tendencias">
    <section class="grid tiles" id="tiles" aria-label="Indicadores clave"></section>
    <p class="marks-note" id="marks-note"><i class="mk-tn" aria-hidden="true"></i> turno de noche · <i class="mk-hard" aria-hidden="true">▲</i> día con una sesión de RPE 8 o más</p>
    {{TEND}}
    <section class="card">
      <h2>Disponibilidad · 28 días</h2>
      <p class="h2sub">Recalculada con el modelo experimental; líneas en 50 y 70 (rojo / verde)</p>
      <div class="chart" id="c-score"></div>
    </section>

    <section class="card" id="weekload" aria-label="Carga semanal"></section>

    <section class="card" id="heat" aria-label="Mapa de calor de 28 días"></section>

    <section class="grid cols-2" id="graficas">
      <div class="card">
        <h2>HRV nocturna</h2>
        <p class="h2sub">ms · banda = tu rango normal (línea base ± cambio mínimo relevante)</p>
        <div class="read" id="r-hrv"></div>
        <div class="legend"><span><i class="key-dot"></i>Noche</span><span><i class="key-line"></i>Media 7 días</span><span><i class="key-band"></i>Rango normal</span></div>
        <div class="chart" id="c-hrv"></div>
      </div>
      <div class="card">
        <h2>FC en reposo</h2>
        <p class="h2sub">lpm · más baja suele indicar mejor recuperación</p>
        <div class="read" id="r-rhr"></div>
        <div class="chart" id="c-rhr"></div>
      </div>
      <div class="card">
        <h2>Sueño</h2>
        <p class="h2sub" id="sleep-sub">horas por noche</p>
        <div class="read" id="r-sleep"></div>
        <div class="chart" id="c-sleep"></div>
      </div>
      <div class="card">
        <h2>Carga diaria</h2>
        <p class="h2sub">carga de entrenamiento (Intervals.icu) por día</p>
        <div class="read" id="r-load"></div>
        <div class="chart" id="c-load"></div>
      </div>
      <div class="card" style="grid-column:1/-1">
        <h2>Sueño por fases</h2>
        <p class="h2sub">horas por noche · línea = necesidad · las noches sin fases registradas quedan vacías</p>
        <div class="legend"><span><i class="key-dot" style="background:var(--series-1)"></i>Profundo</span><span><i class="key-dot" style="background:#1baf7a"></i>REM</span><span><i class="key-dot" style="background:var(--muted)"></i>Resto (ligero y vigilia)</span></div>
        <div class="chart" id="c-stages"></div>
      </div>
    </section>
  </div>

  <div class="grid tab" id="tab-entrenos" data-tab="entrenos">
    {{ENT}}
    <section class="card tbpane" data-pane="sesiones" hidden>
      <h2>Sesiones recientes</h2>
      <p class="h2sub">sRPE = RPE × minutos (Foster), solo con RPE registrado por ID de actividad</p>
      <div class="scroll"><table id="sessions"></table></div>
    </section>
    <section class="card" id="hrdetail" hidden aria-live="polite"></section>
  </div>

  <div class="grid tab" id="tab-sistema" data-tab="sistema">
    {{SIS}}
    <section class="card">
      <h2 id="v3-title">Modelo experimental (en pruebas)</h2>
      <p class="h2sub">Componentes 0–100 · 75 = tu normalidad · peso entre paréntesis</p>
      <div id="meters"></div>
    </section>
    <details class="card fold" id="calidad" aria-label="Calidad y trazabilidad del informe">
      <summary><h2>Calidad y trazabilidad del informe</h2></summary>
      <p class="h2sub" id="cert-sub"></p>
      <div class="grid cols-2" style="gap:12px 24px">
        <div><div class="scroll"><table id="cert"></table></div></div>
        <div><div class="scroll"><table id="integrity"></table></div></div>
      </div>
    </details>

    <details class="card fold">
      <summary><h2>Modelos y regla de decisión</h2></summary>
      <p class="h2sub" id="rule"></p>
      <div class="scroll"><table id="compare"></table></div>
      <details style="margin-top:14px"><summary>Ver datos diarios (28 días)</summary><div class="scroll" style="margin-top:8px"><table id="daily"></table></div></details>
    </details>
  </div>

  <footer id="footer"></footer>
</div>
<nav class="tabbar" aria-label="Secciones">
  <a href="#hoy" data-tab="hoy" class="on"><span aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12h4l2.5-6 4 12 2.5-6H21"/></svg></span>Hoy</a>
  <a href="#tendencias" data-tab="tendencias"><span aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg></span>Tendencias</a>
  <a href="#entrenos" data-tab="entrenos"><span aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6.5 6.5v11M17.5 6.5v11M3.5 9v6M20.5 9v6M6.5 12h11"/></svg></span>Entrenos</a>
  <a href="#sistema" data-tab="sistema"><span aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/></svg></span>Sistema</a>
</nav>
<div class="tip" id="tip" role="tooltip"></div>

<script id="data" type="application/json">{{DATA}}</script>
<script>
{{JS}}
</script>
</body>
</html>
"""


def _asset(name: str) -> str:
    """CSS y JS de la web (``garmin_recovery/web/``), incrustados en la página: sigue siendo un único HTML sin red."""
    return (Path(__file__).with_name("web") / name).read_text(encoding="utf-8").rstrip("\n")


# La plantilla se compone al importar: el HTML resultante es idéntico al de cuando el CSS y el JS vivían aquí.
TEMPLATE = _TEMPLATE_HTML.replace("{{CSS}}", _asset("dashboard.css"), 1).replace("{{JS}}", _asset("dashboard.js"), 1)
