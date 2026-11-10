"""V8.13: tarjetas del panel para progreso (benchmarks, máximos estimados, gimnasia), intensidad semanal,
recuperación por tipo de día, contexto de hoy, historial de carga y actividades que parecen tener dos partes."""
from __future__ import annotations


def _h():
    from . import dashboard as d
    return d._esc, d._kg, d._ddmm, d._prog_svg


def benchmarks_html(items: list | None) -> str:
    esc, kg, ddmm, svg = _h()
    if not isinstance(items, list):
        return ""
    if not items:
        body = ('<p class="pg-sum"><small>Aún no hay benchmarks. Cuando repitas un WOD idéntico aparecerá aquí solo; '
                'también puedes decirme «esto es benchmark» al dictar una sesión o un single pesado.</small></p>')
    else:
        mark = {"up": ("▲", "mejora"), "down": ("▼", "empeora"), "flat": ("=", "igual"), None: ("·", "primera vez")}
        body = ""
        for b in items:
            pts = b["points"]
            sym, word = mark[b["state"]]
            spark = svg([{"date": p["date"], "top_load": p["value"]} for p in pts]) if len(pts) >= 2 else ""
            rows = "".join(f'<tr><td>{ddmm(p["date"])}</td><td class="num">{esc(p["text"])}</td>'
                           f'<td class="num">{esc(str(p["rpe"]) or "—")}</td></tr>' for p in reversed(pts))
            note = ("menos tiempo = mejor" if b["better"] == "lower" else "más es mejor") + (" · marcado como benchmark" if b["marked"] else " · WOD repetido")
            body += (f'<details class="pg"><summary><span class="pg-name">{esc(b["name"])}<small>{len(pts)} veces · {esc(note)}</small></span>'
                     f'{spark}<span class="pg-now">{esc(pts[-1]["text"])}<small class="pg-d {b["state"] or "flat"}">{sym} {word}'
                     f'{" · mejor marca" if b["is_best"] else ""}</small></span></summary>'
                     '<div class="pg-body"><div class="scroll"><table><tr><th>Fecha</th><th>Resultado</th><th>RPE</th></tr>'
                     f'{rows}</table></div></div></details>')
    return ('<section class="card" id="benchmarks" aria-label="Benchmarks"><h2>Benchmarks</h2>'
            '<p class="h2sub">pruebas de referencia repetidas: la forma más clara de ver si progresas · solo se comparan consigo mismas</p>'
            + body + '</section>')


def maxes_html(items: list | None) -> str:
    esc, kg, ddmm, svg = _h()
    if not items:
        return ""
    rows = ""
    for m in items:
        ser = m.get("series") or []
        spark = svg([{"date": x["date"], "top_load": x["e1rm"]} for x in ser]) if len(ser) >= 2 else ""
        last = (f'<br><small>última sesión {kg(ser[-1]["e1rm"])} · {ddmm(ser[-1]["date"])}'
                + (f' ({"+" if m["delta"] > 0 else ""}{kg(m["delta"])} vs. anterior)' if m.get("delta") else "") + "</small>") if len(ser) >= 2 else ""
        src = m["e1rm_from"]
        when = ddmm(src["date"]) if src.get("date") else "—"
        frm = f'{kg(src["load"])} × {kg(src["reps"])} · {when}' if src["reps"] > 1 else f'single · {when}'
        single = (f'{kg(m["single"])}<br><small>{ddmm(m["single_date"]) if m.get("single_date") else "—"}</small>'
                  if m["single"] is not None else "—")
        rows += (f'<tr><td>{esc(m["name"][:1].upper() + m["name"][1:])}<br><small>{esc(frm)}</small></td>'
                 f'<td class="num"><b>{kg(m["e1rm"])}</b>{last}</td><td>{spark}</td><td class="num">{single}</td></tr>')
    return ('<section class="card" id="maximos" aria-label="Máximos estimados"><h2>Máximos estimados</h2>'
            '<p class="h2sub">1RM mínimo por Epley con series de 1–10 repeticiones · comparable entre sesiones con esquemas distintos (10x2, singles, EMOM)</p>'
            '<div class="scroll"><table><tr><th>Ejercicio</th><th>1RM est. kg</th><th>Por sesión</th><th>Single kg</th></tr>'
            f'{rows}</table></div><p class="pg-note">Es una estimación por repeticiones, no un máximo probado; con series cerca del fallo '
            'se acerca más; una sesión de volumen (8–10 repeticiones lejos del fallo) sale más baja sin que hayas perdido fuerza. '
            'No se usa el RPE para estimarlo.</p></section>')


def skill_groups_html(groups: list | None) -> str:
    """V8.16: una ficha por habilidad (HSPU, comba, muscle up…) con sesiones, hitos y la evolución del nivel declarado."""
    esc, _, ddmm, _ = _h()
    if not groups:
        return ""
    out = ""
    for g in groups:
        hitos = "".join(f'<li><span aria-hidden="true">🏅</span> {esc(h["title"])} · {ddmm(h["date"])}</li>' for h in g.get("hitos") or [])
        levels = "".join(f'<li>{ddmm(x["date"])} · {esc(x["level"])}</li>' for x in (g.get("levels") or [])[-5:])
        n = g.get("sessions") or 0
        sub = (f'{n} sesión de técnica' if n == 1 else f'{n} sesiones de técnica' if n else 'sin sesiones de técnica registradas') \
            + f' · desde {ddmm(g["first"])}'
        now = esc(g["level"]) if g.get("level") else ("🏅 " + esc(g["hitos"][-1]["title"]) if g.get("hitos") else "—")
        out += (f'<details class="pg"><summary><span class="pg-name">{esc(g["skill"])}<small>{esc(sub)}</small></span>'
                f'<span class="pg-now"><small>{now}</small></span></summary><div class="pg-body">'
                + (f'<p class="mc-cap">Nivel por sesión</p><ul class="clean">{levels}</ul>' if levels else "")
                + (f'<p class="mc-cap">Hitos</p><ul class="clean">{hitos}</ul>' if hitos else "")
                + (('<p class="pg-note">Aún no hay nivel declarado: al dictar técnica, dime el déficit, la banda o las '
                    'repeticiones máximas y aparecerá aquí.</p>') if not levels and n else "") + '</div></details>')
    return ('<section class="card" id="habilidades" aria-label="Habilidades"><h2>Habilidades</h2>'
            '<p class="h2sub">cada habilidad con su evolución y sus hitos · solo lo que has declarado</p>' + out + '</section>')


def skills_html(items: list | None) -> str:
    esc, _, ddmm, _ = _h()
    if not items:
        return ""
    lis = "".join(
        f'<li class="tl-{x["kind"]}"><span class="tl-date">{ddmm(x["date"])}</span><span class="tl-t">'
        + ('<span aria-hidden="true">🏅</span> ' if x["kind"] == "hito" else "") + f'{esc(x["title"])}'
        + (f'<small>{esc(x["sub"])}</small>' if x["sub"] else "") + "</span></li>" for x in items[:20])
    return ('<section class="card" id="gimnasia" aria-label="Gimnasia y técnica"><h2>Gimnasia y técnica</h2>'
            '<p class="h2sub">hitos (🏅) y sesiones de técnica, de la más reciente a la más antigua</p>'
            f'<ul class="clean timeline">{lis}</ul></section>')


def progress_pane(ap: dict | None) -> str:
    if not isinstance(ap, dict):
        return ""
    return (benchmarks_html(ap.get("benchmarks")) + maxes_html(ap.get("maxes"))
            + skill_groups_html(ap.get("skill_groups")) + skills_html(ap.get("skills")))


def intensity_html(rc: dict | None) -> str:
    esc, kg, _, _ = _h()
    weeks = (rc or {}).get("weekly") or []
    if not weeks:
        return ""
    rows = ""
    for w in weeks:
        cls = ' class="soft"' if w["current"] else ""
        cur = " ·" if w["current"] else ""
        pct = " <small>(%d %%)</small>" % w["hard_pct"] if w["hard_pct"] is not None else ""
        rows += (f'<tr{cls}><td>{esc(w["week"][-3:])}{cur}</td><td class="num">{w["sessions"]}</td>'
                 f'<td class="num">{w["hard"]}{pct}</td><td class="num">{w["easy_days"]}/{w["days"]}</td></tr>')
    last = next((w for w in reversed(weeks) if not w["current"]), None)
    note = ""
    if last and last["hard_pct"] is not None and last["hard_pct"] >= 50 and last["easy_days"] <= 2:
        note = '<p class="pg-note warn">La última semana completa tuvo la mitad o más de las sesiones a RPE ≥ 8 y como mucho dos días suaves.</p>'
    return ('<section class="card" id="intensidad" aria-label="Intensidad semanal"><h2>Intensidad semanal</h2>'
            '<p class="h2sub">duras = RPE ≥ 8 (sobre las puntuadas) · suaves = días sin sesión o con todo a RPE ≤ 5 o sin puntuar · «·» = semana en curso</p>'
            '<div class="scroll"><table><tr><th>Semana</th><th>Sesiones</th><th>Duras</th><th>Suaves</th></tr>'
            f'{rows}</table></div>{note}</section>')


def day_types_html(rc: dict | None) -> str:
    esc, kg, _, _ = _h()
    dt = (rc or {}).get("day_types") or {}
    if not dt.get("rows"):
        return ""
    def n(v, d=0):
        return "—" if v is None else (f"{v:.{d}f}".replace(".", ","))
    rows = "".join(
        f'<tr><td>{esc(r["label"])}<br><small>{r["days"]} días</small></td>'
        + (f'<td class="num">{n(r["score"])}</td><td class="num">{n(r["hrv"])}</td><td class="num">{n(r["sleep"], 1)} h</td>'
           f'<td class="num">{n(r["rpe"], 1)}</td>' if r["enough"] else '<td colspan="4"><small>pocos días aún</small></td>')
        + "</tr>" for r in dt["rows"])
    return ('<section class="card" id="tipo-dia" aria-label="Recuperación por tipo de día"><h2>Según el turno</h2>'
            '<p class="h2sub">medias por tipo de día · post-TN = el día después de un turno de noche · RPE = media de las sesiones de ese día</p>'
            '<div class="scroll"><table><tr><th>Día</th><th>Puntuación</th><th>VFC ms</th><th>Sueño</th><th>RPE</th></tr>'
            f'{rows}</table></div><p class="pg-note">Describe lo observado, no la causa. Con más semanas las medias serán más fiables.</p></section>')


def today_html(rc: dict | None) -> str:
    esc = _h()[0]
    t = (rc or {}).get("today") or {}
    lines = t.get("lines") or []
    if not lines:
        return ""
    return ('<section class="card" id="contexto-hoy" aria-label="Contexto de hoy"><h2>Hoy · ' + esc(t.get("type_label") or "") + '</h2>'
            + "".join(f'<p>{esc(x)}</p>' for x in lines) + '</section>')


def load_history_html(ap: dict | None) -> str:
    esc = _h()[0]
    lh = (ap or {}).get("load_history") or {}
    if not lh.get("note"):
        return ""
    return f'<section class="card soft-note" aria-label="Historial de carga"><p class="pg-note">ⓘ {esc(lh["note"])}</p></section>'


def splits_html(items: list | None) -> str:
    esc, _, ddmm, _ = _h()
    if not items:
        return ""
    lis = "".join(f'<li>{ddmm(x["date"])} · {esc(x["label"])} <span class="weight">corte propuesto en {esc(x["cut_mmss"])} '
                  f'({esc(x["reason"])})</span></li>' for x in items)
    return ('<section class="card" id="tramos" aria-label="Actividades con dos partes"><h2>¿Dos partes en una actividad?</h2>'
            '<p class="h2sub">la FC baja y se mantiene en reposo varios minutos a mitad de la actividad · si lo confirmas, la parto en tramos</p>'
            f'<ul class="clean">{lis}</ul></section>')
