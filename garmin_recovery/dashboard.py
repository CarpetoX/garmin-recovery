"""Panel HTML autocontenido (sin dependencias externas ni red).

Los datos se incrustan como JSON y los gráficos se dibujan en el navegador
con SVG a la anchura real del contenedor (legibles también en el móvil).
"""
from __future__ import annotations

import html
import json
import re

ZONE_UI = {
    "green": ("good", "✓"), "yellow": ("warning", "!"),
    "red": ("critical", "✕"), "unavailable": ("muted", "…"),
}


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def render(result: dict, extras: dict | None = None) -> str:
    """``extras`` (solo la web publicada): puntualidad, histórico, fuerza y etiquetas PWA."""
    from .report import rpe_by_day
    extras = extras or {}
    data = dict(result)
    data["_rpe_days"] = rpe_by_day(result.get("sessions_28d") or [], result.get("trend_28d") or [], result["date"], 28)
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    rd = result["readiness"]
    zone = (result.get("decision") or {}).get("zone") or rd["zone"]
    tone, icon = ZONE_UI.get(zone, ZONE_UI["unavailable"])
    title = "Rendimiento y recuperación"
    extra = _extra_sections(result, extras)
    head = PWA_HEAD if extras.get("pwa") else ""
    values = {"TITLE": title, "HEAD": head, "EXTRA": extra, "DATE": _esc(result["date"]),
              "TONE": tone, "ICON": icon, "DATA": payload}
    # una sola pasada: el contenido sustituido nunca se vuelve a interpretar como marcador
    return re.sub(r"\{\{(TITLE|HEAD|EXTRA|DATE|TONE|ICON|DATA)\}\}", lambda m: values[m.group(1)], TEMPLATE)


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
            f'<p class="h2sub">deuda de 7 noches: {f(n["debt_7n_h"])} h · incluye el sueño diurno tras turno y descuenta siestas</p>'
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


def _changes_html(c: dict | None) -> str:
    if not c or not c.get("available"):
        return ""
    f = lambda v, d: f"{v:.{d}f}".replace(".", ",")  # noqa: E731
    head = ""
    if c.get("score_from") is not None and c.get("score_to") is not None:
        head = f"<p><b>Disponibilidad v3:</b> {f(c['score_from'], 0)} → {f(c['score_to'], 0)}</p>"
    if not c["items"]:
        body = "<p class='h2sub'>Ningún indicador cambió lo bastante frente a ayer como para destacarlo.</p>"
    else:
        body = "<ul class='clean chg'>" + "".join(
            f"<li class='{'pos' if i['favorable'] else 'neg'}'><span class='arrow'>{'↑' if i['favorable'] else '↓'}</span>"
            f"<span>{_esc(i['label'])}: {f(i['from'], i['dec'])} → {f(i['to'], i['dec'])}{_esc(i['unit'])}</span></li>"
            for i in c["items"]) + "</ul>"
    return ('<section class="card" aria-label="Qué ha cambiado desde ayer"><h2>Qué ha cambiado desde ayer</h2>'
            f'{head}{body}<p class="h2sub" style="margin-top:8px">diferencias observadas, no causas</p></section>')


def _extra_sections(result: dict, extras: dict | None = None) -> str:
    """Resumen de tres líneas, RPE frente al máximo del día y la semana (mismo contenido que el informe)."""
    import re
    from .readiness import GUIDANCE
    if (extras or {}).get("snapshot"):
        return (f'<section class="card"><b>Instantánea del {_esc(extras["snapshot"])}</b> · '
                '<a href="../index.html">← Volver al panel actual</a></section>')
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
    strength = extras.get("strength_svg")
    strength_html = ("" if not strength else
                     '<section class="card"><h2>Progresión de fuerza</h2><p class="h2sub">1RM mínimo estimado (Epley con '
                     'tu mejor serie) cuando hay repeticiones; si no, carga máxima declarada</p>'
                     f'<div class="svgwrap">{strength}</div></section>')
    full_html = ('<section class="card"><p><a href="informe_completo.html"><strong>📄 Abrir el informe completo</strong></a> '
                 '· resumen, 7 secciones y recomendaciones</p></section>' if extras.get("full_report") else "")
    changes = _changes_html(extras.get("changes"))
    today_block = changes or f'<section class="card" aria-label="Resumen de hoy"><h2>En tres líneas</h2>{summary}</section>'
    return (full_html + today_block + _tonight_html(extras.get("tonight")) + _plan_html(extras.get("plan"))
            + '<section class="card" id="calendario" aria-label="Calendario"><h2>Últimas 4 semanas</h2>'
            '<p class="h2sub">color = decisión del día (o v3 atenuado si no se guardó) · número = RPE máximo · '
            'anillo rojo = por encima del máximo · toca un día para ver el detalle</p>'
            '<div class="cal-head"><span>L</span><span>M</span><span>X</span><span>J</span><span>V</span><span>S</span><span>D</span></div>'
            '<div class="cal" id="cal"></div><div class="cal-detail" id="cal-detail"></div></section>'
            '<section class="grid cols-2" id="semana"><div class="card"><h2>RPE frente al máximo del día</h2>'
            '<p class="h2sub">barra = sesión más dura · raya = máximo que permitía la decisión · rojo = por encima</p>'
            '<div class="legend"><span><i class="key-dot"></i>Dentro</span><span><i class="key-dot" style="background:var(--critical)"></i>Por encima</span>'
            '<span><i class="key-ref" style="border-top:3px solid var(--text-2)"></i>Máximo del día</span></div>'
            '<div class="chart" id="c-rpe"></div></div>'
            '<div class="card"><h2>Esta semana</h2><p class="h2sub">últimos 7 días frente a los 7 anteriores · detalle en '
            f'<code>informe_semanal.md</code></p><div class="scroll">{week}</div></div></section>'
            + strength_html + _punctuality_html(extras.get("punctuality")) + _days_html(extras.get("days")) + _history_html(extras.get("history")))


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
{{HEAD}}
<style>
:root{
  color-scheme: light;
  --bg:#f6f6f4; --surface:#fcfcfb; --surface-2:#f0efec; --line:#e4e3df;
  --text:#0b0b0b; --text-2:#52514e; --text-3:#63625c;
  --series-1:#2a78d6; --series-1-wash:rgba(42,120,214,.12); --series-2:#eb6834;
  --good:#0ca30c; --warning:#fab219; --critical:#d03b3b; --muted:#9a9990;
  --good-ink:#006300; --warning-ink:#7a5200; --critical-ink:#a32727;
  --radius:14px;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --bg:#121211; --surface:#1a1a19; --surface-2:#242422; --line:#30302d;
    --text:#f0efec; --text-2:#c3c2b7; --text-3:#aeada3;
    --series-1:#3987e5; --series-1-wash:rgba(57,135,229,.16); --series-2:#d95926;
    --good-ink:#5fd35f; --warning-ink:#fab219; --critical-ink:#f08080;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --surface-2:#242422; --line:#30302d;
  --text:#f0efec; --text-2:#c3c2b7; --text-3:#aeada3;
  --series-1:#3987e5; --series-1-wash:rgba(57,135,229,.16); --series-2:#d95926;
  --good-ink:#5fd35f; --warning-ink:#fab219; --critical-ink:#f08080;
}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1120px;margin:0 auto;padding:24px 16px 48px}
header{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 16px;margin-bottom:20px}
h1{font-size:22px;line-height:1.2;margin:0;font-weight:650;letter-spacing:-.01em}
.sub{color:var(--text-2);font-size:13px}
.badge{display:inline-block;font-size:12px;color:var(--text-2);background:var(--surface-2);border-radius:999px;padding:2px 10px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:18px;min-width:0}
.grid>*{min-width:0}
.grid{display:grid;gap:16px}
.hero{display:grid;grid-template-columns:minmax(180px,240px) 1fr;gap:24px;align-items:start}
@media (max-width:720px){.hero{grid-template-columns:1fr}}
.score{font-size:64px;line-height:1;font-weight:650;font-variant-numeric:proportional-nums;letter-spacing:-.02em}
.score small{font-size:18px;color:var(--text-3);font-weight:500;margin-left:4px}
.pill{display:inline-flex;align-items:center;gap:8px;margin-top:12px;font-weight:600;font-size:14px}
.dot{width:22px;height:22px;border-radius:50%;display:inline-grid;place-items:center;font-size:13px;color:#fff;font-weight:700}
.tone-good .dot{background:var(--good)} .tone-good .pill-text{color:var(--good-ink)}
.tone-warning .dot{background:var(--warning);color:#1a1a19} .tone-warning .pill-text{color:var(--warning-ink)}
.tone-critical .dot{background:var(--critical)} .tone-critical .pill-text{color:var(--critical-ink)}
.tone-muted .dot{background:var(--muted)} .tone-muted .pill-text{color:var(--text-2)}
.meta{color:var(--text-3);font-size:12px;margin-top:8px}
.guidance{font-size:17px;line-height:1.45;margin:0 0 12px}
.rx{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.rx span{background:var(--surface-2);border-radius:8px;padding:4px 10px;font-size:13px;color:var(--text-2)}
.rx b{color:var(--text);font-weight:600}
ul.clean{list-style:none;padding:0;margin:0}
.drivers li{display:flex;gap:10px;align-items:flex-start;padding:6px 0;border-top:1px solid var(--line);font-size:14px}
.drivers li:first-child{border-top:0}
.arrow{flex:0 0 18px;text-align:center;font-weight:700}
.neg{color:var(--critical-ink)} .pos{color:var(--good-ink)} .neu{color:var(--text-3)}
.notes li{font-size:13px;color:var(--text-2);padding:2px 0}
h2{font-size:15px;margin:0 0 4px;font-weight:620}
.h2sub{font-size:12px;color:var(--text-3);margin:0 0 12px}
.cols-2{grid-template-columns:1fr 1fr} @media (max-width:860px){.cols-2{grid-template-columns:1fr}}
.tiles{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}
.tile .label{font-size:13px;color:var(--text-2)}
.tile .value{font-size:26px;font-weight:620;margin-top:2px;letter-spacing:-.01em}
.tile .value small{font-size:13px;color:var(--text-3);font-weight:500;margin-left:3px}
.tile .delta{font-size:12px;color:var(--text-3);margin-top:2px}
.meter-row{display:grid;grid-template-columns:minmax(120px,190px) 1fr 44px;gap:12px;align-items:center;padding:7px 0}
.meter-row .name{font-size:13px;color:var(--text-2)}
.meter{height:8px;border-radius:4px;background:var(--surface-2);overflow:hidden}
.meter i{display:block;height:100%;border-radius:4px}
.meter-row .val{font-size:13px;text-align:right;font-variant-numeric:tabular-nums}
.weight{font-size:11px;color:var(--text-3)}
.chart{position:relative;width:100%;height:190px}
.chart svg{display:block;width:100%;height:100%;overflow:visible}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--text-2);margin:-4px 0 8px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.key-line{width:14px;height:2px;border-radius:2px;background:var(--series-1)}
.key-dot{width:8px;height:8px;border-radius:50%;background:var(--series-1)}
.key-band{width:14px;height:10px;border-radius:2px;background:var(--series-1-wash)}
.key-ref{width:14px;height:0;border-top:1px solid var(--text-3)}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:6px 9px;font-size:12px;line-height:1.4;box-shadow:0 4px 14px rgba(0,0,0,.12);white-space:nowrap;opacity:0;transition:opacity .08s;z-index:2}
.tip b{font-weight:600}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 8px;border-top:1px solid var(--line);white-space:nowrap}
th{color:var(--text-3);font-weight:500;border-top:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
details summary{cursor:pointer;color:var(--text-2);font-size:13px}
footer{color:var(--text-3);font-size:12px;margin-top:24px;line-height:1.6}
.empty{color:var(--text-3);font-size:13px;padding:24px 0;text-align:center}
.cal-head,.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;max-width:560px}
.cal-head span{font-size:11px;color:var(--text-3);text-align:center}
.cal{margin-top:4px}
.cal button{all:unset;cursor:pointer;height:54px;border-radius:10px;display:grid;place-items:center;position:relative;
  background:var(--surface-2);font-size:13px;font-variant-numeric:tabular-nums;color:var(--text);min-width:0}
.cal button .dn{position:absolute;top:4px;left:6px;font-size:10px;color:var(--text-3)}
.cal button.z-green{background:color-mix(in srgb,var(--good) 30%,transparent)}
.cal button.z-yellow{background:color-mix(in srgb,var(--warning) 34%,transparent)}
.cal button.z-red{background:color-mix(in srgb,var(--critical) 30%,transparent)}
.cal button.z-unavailable{background:color-mix(in srgb,var(--muted) 28%,transparent)}
.cal button.v3{opacity:.55}
.cal button.over{box-shadow:inset 0 0 0 2px var(--critical)}
.cal button.sel{outline:2px solid var(--series-1);outline-offset:1px}
.cal button.empty-day{background:transparent;cursor:default}
.cal button b{font-weight:650}
.cal-detail{margin-top:12px;font-size:14px;min-height:20px}
.cal-detail table{margin-top:6px}
.svgwrap{max-width:680px} .svgwrap svg{width:100%;height:auto}
.hist li{padding:6px 0;border-top:1px solid var(--line);font-size:14px}
.hist li:first-child{border-top:0}
.hist a{color:var(--text);text-decoration:none} .hist a:hover{text-decoration:underline}
.hz{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px;background:var(--muted)}
.hz.z-green{background:var(--good)} .hz.z-yellow{background:var(--warning)} .hz.z-red{background:var(--critical)}
.nav{position:sticky;top:0;z-index:5;display:flex;gap:6px;overflow-x:auto;padding:8px 0;margin:-8px 0 12px;background:var(--bg);-webkit-overflow-scrolling:touch}
.nav a{flex:0 0 auto;font-size:13px;color:var(--text-2);text-decoration:none;background:var(--surface-2);border-radius:999px;padding:6px 14px}
.nav a:hover,.nav a:focus-visible{color:var(--text);outline:2px solid var(--series-1)}
section[id],details[id]{scroll-margin-top:56px}
.fold>summary{list-style:none;cursor:pointer;color:inherit;font-size:inherit} .fold>summary::-webkit-details-marker{display:none}
.fold>summary h2{display:inline} .fold>summary::after{content:" ▾";color:var(--text-3)} .fold[open]>summary::after{content:" ▴"}
.big{font-size:40px;font-weight:650;letter-spacing:-.02em;line-height:1.1;margin:4px 0}
.big small{font-size:16px;color:var(--text-3);font-weight:500}
.parts li{display:flex;justify-content:space-between;padding:5px 0;border-top:1px solid var(--line);font-size:14px}
.parts li:first-child{border-top:0}
.tip-line{margin:10px 0 0;font-size:14px;background:var(--surface-2);border-radius:8px;padding:8px 10px}
.plan{display:grid;gap:8px}
.plan li{display:grid;grid-template-columns:44px 1fr;gap:12px;align-items:center;padding:8px 10px;border-radius:10px;background:var(--surface-2);border-left:4px solid var(--muted)}
.plan .pd{text-align:center;font-size:11px;color:var(--text-3);line-height:1.2} .plan .pd b{font-size:18px;color:var(--text)}
.plan .why{font-size:12px;color:var(--text-2)}
.plan li.k-hard{border-left-color:var(--critical)} .plan li.k-mod{border-left-color:var(--warning)}
.plan li.k-light{border-left-color:var(--good)} .plan li.k-rest{border-left-color:var(--series-1)}
.chg li{display:flex;gap:10px;padding:4px 0;font-size:14px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>{{TITLE}}</h1>
      <div class="sub" id="sub">{{DATE}}</div>
    </div>
    <span class="badge" id="badge">Modelo v3</span>
  </header>

  <nav class="nav" aria-label="Secciones"><a href="#hoy">Hoy</a><a href="#noche">Noche</a><a href="#plan">Plan</a>
    <a href="#calendario">Calendario</a><a href="#graficas">Gráficas</a><a href="#calidad">Calidad</a><a href="#dias">Días</a><a href="#informes">Informes</a></nav>

  <div class="grid">
    <section class="card hero tone-{{TONE}}" id="hoy" aria-label="Disponibilidad de hoy">
      <div>
        <div class="h2sub">Decisión de hoy · puntuación oficial (v2)</div>
        <div class="score" id="score">—</div>
        <div class="pill"><span class="dot" aria-hidden="true">{{ICON}}</span><span class="pill-text" id="zone-label"></span></div>
        <div class="meta" id="confidence"></div>
      </div>
      <div>
        <p class="guidance" id="guidance"></p>
        <div class="rx" id="rx"></div>
        <ul class="clean drivers" id="drivers"></ul>
        <ul class="clean notes" id="notes" style="margin-top:10px"></ul>
      </div>
    </section>

    {{EXTRA}}

    <section class="grid tiles" id="tiles" aria-label="Indicadores clave"></section>

    <section class="grid cols-2">
      <div class="card">
        <h2 id="v3-title">Modelo v3 (en pruebas)</h2>
        <p class="h2sub">Componentes 0–100 · 75 = tu normalidad · peso entre paréntesis</p>
        <div id="meters"></div>
      </div>
      <div class="card">
        <h2>Disponibilidad · 28 días</h2>
        <p class="h2sub">Recalculada con el modelo v3; líneas en 50 y 70 (rojo / verde)</p>
        <div class="chart" id="c-score"></div>
      </div>
    </section>

    <section class="grid cols-2" id="graficas">
      <div class="card">
        <h2>HRV nocturna</h2>
        <p class="h2sub">ms · banda = tu rango normal (línea base ± cambio mínimo relevante)</p>
        <div class="legend"><span><i class="key-dot"></i>Noche</span><span><i class="key-line"></i>Media 7 días</span><span><i class="key-band"></i>Rango normal</span></div>
        <div class="chart" id="c-hrv"></div>
      </div>
      <div class="card">
        <h2>FC en reposo</h2>
        <p class="h2sub">lpm · más baja suele indicar mejor recuperación</p>
        <div class="chart" id="c-rhr"></div>
      </div>
      <div class="card">
        <h2>Sueño</h2>
        <p class="h2sub" id="sleep-sub">horas por noche</p>
        <div class="chart" id="c-sleep"></div>
      </div>
      <div class="card">
        <h2>Carga diaria</h2>
        <p class="h2sub">carga de entrenamiento (Intervals.icu) por día</p>
        <div class="chart" id="c-load"></div>
      </div>
    </section>

    <details class="card fold" id="calidad" aria-label="Calidad y trazabilidad del informe">
      <summary><h2>Calidad y trazabilidad del informe</h2></summary>
      <p class="h2sub" id="cert-sub"></p>
      <div class="grid cols-2" style="gap:12px 24px">
        <div><div class="scroll"><table id="cert"></table></div></div>
        <div><div class="scroll"><table id="integrity"></table></div></div>
      </div>
    </details>

    <section class="card">
      <h2>Sesiones recientes</h2>
      <p class="h2sub">sRPE = RPE × minutos (Foster), solo con RPE registrado por ID de actividad</p>
      <div class="scroll"><table id="sessions"></table></div>
    </section>

    <details class="card fold">
      <summary><h2>Modelos y regla de decisión</h2></summary>
      <p class="h2sub" id="rule"></p>
      <div class="scroll"><table id="compare"></table></div>
      <details style="margin-top:14px"><summary>Ver datos diarios (28 días)</summary><div class="scroll" style="margin-top:8px"><table id="daily"></table></div></details>
    </details>
  </div>

  <footer id="footer"></footer>
</div>
<div class="tip" id="tip" role="tooltip"></div>

<script id="data" type="application/json">{{DATA}}</script>
<script>
(function(){
const D = JSON.parse(document.getElementById('data').textContent);
const R = D.readiness, L = D.load, T = D.trend_28d || [];
const $ = id => document.getElementById(id);
const fmt = (v, d=0) => v == null || Number.isNaN(v) ? '—' : Number(v).toLocaleString('es-ES', {maximumFractionDigits:d, minimumFractionDigits:d});
const sign = (v, d=0) => v == null ? '—' : (v > 0 ? '+' : '') + fmt(v, d);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dshort = iso => { const [y,m,d] = iso.split('-'); return `${+d}/${+m}`; };
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const zoneTxt = {green:'verde', yellow:'ámbar', red:'rojo', unavailable:'pendiente'};

// ---------- Cabecera y héroe ----------
const gen = new Date(D.generated_at);
$('sub').textContent = `${new Date(D.date+'T12:00').toLocaleDateString('es-ES',{weekday:'long', day:'numeric', month:'long'})} · actualizado ${gen.toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'})}`;
$('badge').textContent = `Modelo ${D.model_version} · ${D.mode === 'shadow' ? 'en paralelo' : 'activo'}`;
const DEC = D.decision || {zone: R.zone, guidance: R.guidance, registry: [], divergence: []};
const official = (DEC.registry || []).find(m => m.role === 'oficial') || {};
$('score').innerHTML = official.score == null ? '—' : `${fmt(official.score)}<small>/100</small>`;
$('zone-label').textContent = DEC.guidance.label + (DEC.agreement === 'total' ? ' · modelos de acuerdo' : ' · regla conservadora');
const reasons = (R.reasons || []).map(r => r.split(':')[0].replace(/_/g,' '));
const DC = R.data_confidence || {}, RC = R.recommendation_confidence || {};
$('confidence').textContent = `Datos: confianza ${DC.level || '—'} · Recomendación: confianza ${RC.level || R.confidence}` + (reasons.length ? ` · ${reasons.join(', ')}` : '') + ` · historial ${D.history.days} días`;
$('guidance').textContent = DEC.guidance.text;
$('rx').innerHTML = `<span>RPE máx. <b>${DEC.guidance.rpe_max}</b></span><span>Volumen <b>${esc(DEC.guidance.volume)}</b></span>` +
  (DEC.registry || []).filter(m => m.used_in_decision).map(m => `<span>${esc(m.label.replace(' (oficial)','').replace(' (en pruebas)',''))} <b>${fmt(m.score)}</b></span>`).join('');
$('v3-title').textContent = `Modelo v3 (en pruebas) · ${R.score == null ? 'sin puntuación' : fmt(R.score) + '/100 · ' + zoneTxt[R.zone]}`;
$('drivers').innerHTML = (R.drivers || []).map(d => {
  const cls = d.z <= -0.5 ? 'neg' : d.z >= 0.5 ? 'pos' : 'neu';
  const ar = d.z <= -0.5 ? '↓' : d.z >= 0.5 ? '↑' : '→';
  return `<li><span class="arrow ${cls}" aria-hidden="true">${ar}</span><span>${esc(d.text)}</span></li>`;
}).join('') || '<li><span class="arrow neu">→</span><span>Sin factores calculables hoy.</span></li>';
$('notes').innerHTML = (DEC.divergence || []).concat(R.notes || []).map(n => `<li>${esc(n)}</li>`).join('');

// ---------- KPI ----------
const C = R.components, H = C.hrv, K = C.cardiac, S = C.sleep;
const tiles = [
  {label:'HRV media 7 días', value: fmt(H.rolling_ms ?? H.today_ms), unit:'ms', delta: H.rolling_vs_baseline_pct != null ? `${sign(H.rolling_vs_baseline_pct)} % vs. base ${fmt(H.baseline_ms)} ms` : 'base en construcción'},
  {label:'FC en reposo', value: fmt(K.resting_hr), unit:'lpm', delta: K.resting_delta_bpm != null ? `${sign(K.resting_delta_bpm)} vs. mediana ${fmt(K.baseline_resting_hr)}` : '—'},
  {label:'Sueño', value: fmt(S.hours, 1), unit:'h', delta: `puntuación ${fmt(S.sleep_score)} · deuda ${fmt(S.debt_hours,1)} h`},
  {label:'Carga 7 días', value: fmt(L.week_load), unit:'', delta: `${L.week_sessions} sesiones` + (L.week_change_pct != null ? ` · ${sign(L.week_change_pct)} % vs. semana previa` : '')},
  {label:'Forma (TSB)', value: L.form_interpretable ? sign(L.form_pct) : sign(L.tsb, 1), unit: L.form_interpretable ? '%' : '', delta: L.form_interpretable ? `zona ${L.form_zone} · CTL ${fmt(L.ctl,1)}` : `CTL ${fmt(L.ctl,1)} · aún sin carga crónica suficiente`},
];
$('tiles').innerHTML = tiles.map(t => `<div class="card tile"><div class="label">${t.label}</div><div class="value">${t.value}<small>${t.unit}</small></div><div class="delta">${esc(t.delta)}</div></div>`).join('');

// ---------- Medidores ----------
const tone = s => s == null ? 'var(--muted)' : s >= 70 ? 'var(--good)' : s >= 50 ? 'var(--warning)' : 'var(--critical)';
$('meters').innerHTML = Object.entries(C).map(([k, c]) => `
  <div class="meter-row"><div class="name">${esc(c.label)} <span class="weight">(${Math.round(c.weight*100)} %)</span></div>
  <div class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${c.score ?? ''}" aria-label="${esc(c.label)}"><i style="width:${c.score ?? 0}%;background:${tone(c.score)}"></i></div>
  <div class="val">${c.score == null ? '<span class="weight">sin datos</span>' : fmt(c.score)}</div></div>`).join('');

// ---------- Motor de gráficos ----------
const tip = $('tip');
function chart(el, opt){
  const draw = () => {
    const W = el.clientWidth, Hh = el.clientHeight, m = {t:10, r:12, b:22, l:34};
    const iw = W - m.l - m.r, ih = Hh - m.t - m.b, n = T.length;
    if (!n || W < 50) { el.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    const vals = [];
    opt.series.forEach(s => T.forEach(d => { if (d[s.key] != null) vals.push(d[s.key]); }));
    if (opt.band) T.forEach(d => { if (d[opt.band[0]] != null) vals.push(d[opt.band[0]], d[opt.band[1]]); });
    (opt.refs || []).forEach(r => vals.push(r.y));
    if (!vals.length) { el.innerHTML = '<div class="empty">Sin datos todavía</div>'; return; }
    let lo = opt.min ?? Math.min(...vals), hi = opt.max ?? Math.max(...vals);
    if (opt.zero) lo = 0;
    if (hi === lo) { hi += 1; lo -= 1; }
    const pad = (hi - lo) * 0.08; if (opt.min == null && !opt.zero) lo -= pad; if (opt.max == null) hi += pad;
    const step = niceStep((hi - lo) / 4); lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    const bw = iw / n, x = i => m.l + bw * (i + .5), y = v => m.t + ih - (v - lo) / (hi - lo) * ih;
    let s = `<svg viewBox="0 0 ${W} ${Hh}" role="img" aria-label="${esc(opt.label)}">`;
    for (let v = lo; v <= hi + 1e-9; v += step) {
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-width="1"/>`;
      s += `<text x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end" font-size="11" fill="var(--text-3)">${fmt(v, step < 1 ? 1 : 0)}</text>`;
    }
    const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(iw / 46))));
    T.forEach((d, i) => { if ((n - 1 - i) % every === 0) s += `<text x="${x(i)}" y="${Hh - 6}" text-anchor="middle" font-size="11" fill="var(--text-3)">${dshort(d.date)}</text>`; });
    if (opt.band) {
      const pts = T.map((d, i) => [i, d[opt.band[0]], d[opt.band[1]]]).filter(p => p[1] != null);
      if (pts.length > 1) s += `<path d="M${pts.map(p => `${x(p[0])},${y(p[2])}`).join('L')}L${pts.slice().reverse().map(p => `${x(p[0])},${y(p[1])}`).join('L')}Z" fill="var(--series-1-wash)"/>`;
    }
    (opt.refs || []).forEach(r => {
      s += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(r.y)}" y2="${y(r.y)}" stroke="var(--text-3)" stroke-width="1"/>`;
      if (r.label) s += `<text x="${W - m.r}" y="${y(r.y) - 4}" text-anchor="end" font-size="11" fill="var(--text-2)">${esc(r.label)}</text>`;
    });
    opt.series.forEach(se => {
      const col = `var(${se.color || '--series-1'})`;
      if (se.kind === 'tick') {
        const w = Math.min(24, bw * .62) + 10;
        T.forEach((d, i) => { const v = d[se.key]; if (v == null) return;
          s += `<line x1="${x(i) - w/2}" x2="${x(i) + w/2}" y1="${y(v)}" y2="${y(v)}" stroke="${col}" stroke-width="3" stroke-linecap="round"/>`; });
      } else if (se.kind === 'bar') {
        const w = Math.min(24, bw * .62);
        T.forEach((d, i) => { const v = d[se.key]; if (v == null || v <= 0) return;
          const top = y(v), base = y(Math.max(lo, 0)), h = Math.max(1, base - top), rr = Math.min(4, w / 2, h);
          s += `<path d="M${x(i) - w/2},${base}V${top + rr}Q${x(i) - w/2},${top} ${x(i) - w/2 + rr},${top}H${x(i) + w/2 - rr}Q${x(i) + w/2},${top} ${x(i) + w/2},${top + rr}V${base}Z" fill="${col}"/>`; });
      } else {
        const segs = []; let cur = [];
        T.forEach((d, i) => { const v = d[se.key]; if (v == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push([x(i), y(v)]); });
        if (cur.length) segs.push(cur);
        if (se.kind !== 'dots') segs.forEach(g => { if (g.length > 1) s += `<path d="M${g.map(p => p.join(',')).join('L')}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`; });
        if (se.kind === 'dots' || se.markers) T.forEach((d, i) => { const v = d[se.key]; if (v != null) s += `<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="${col}" stroke="var(--surface)" stroke-width="2"/>`; });
      }
    });
    s += `<line class="xh" x1="0" x2="0" y1="${m.t}" y2="${m.t + ih}" stroke="var(--text-3)" stroke-width="1" opacity="0"/>`;
    s += `<rect x="${m.l}" y="0" width="${iw}" height="${Hh}" fill="transparent"/></svg>`;
    el.innerHTML = s;
    const svg = el.querySelector('svg'), xh = svg.querySelector('.xh');
    const move = ev => {
      const rect = svg.getBoundingClientRect(), px = ev.clientX - rect.left;
      const i = Math.max(0, Math.min(n - 1, Math.floor((px - m.l) / bw)));
      const d = T[i];
      xh.setAttribute('x1', x(i)); xh.setAttribute('x2', x(i)); xh.setAttribute('opacity', .5);
      tip.innerHTML = `<b>${new Date(d.date + 'T12:00').toLocaleDateString('es-ES',{weekday:'short', day:'numeric', month:'short'})}</b>` + (d.shift ? ` · turno ${esc(d.shift)}` : '') + '<br>' + opt.tip(d);
      tip.style.opacity = 1;
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      let left = rect.left + window.scrollX + x(i) + 12; if (left + tw > window.scrollX + document.documentElement.clientWidth - 8) left = rect.left + window.scrollX + x(i) - tw - 12;
      tip.style.left = Math.max(8, left) + 'px'; tip.style.top = (rect.top + window.scrollY + m.t - 4) + 'px';
    };
    svg.addEventListener('pointermove', move); svg.addEventListener('pointerdown', move);
    svg.addEventListener('pointerleave', () => { tip.style.opacity = 0; xh.setAttribute('opacity', 0); });
  };
  draw(); new ResizeObserver(draw).observe(el);
}
function niceStep(raw){ const p = Math.pow(10, Math.floor(Math.log10(raw || 1))), f = raw / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }

chart($('c-score'), {label:'Disponibilidad 28 días', min:0, max:100, refs:[{y:70},{y:50}],
  series:[{key:'score', markers:true}], tip: d => d.score == null ? 'Sin puntuación (datos incompletos)' : `Puntuación <b>${fmt(d.score)}</b> · ${zoneTxt[d.zone]}` + (d.garmin_readiness != null ? `<br>Garmin Training Readiness ${fmt(d.garmin_readiness)}` : '')});
chart($('c-hrv'), {label:'HRV nocturna', band:['hrv_low_ms','hrv_high_ms'],
  series:[{key:'hrv_rolling_ms'}, {key:'hrv_ms', kind:'dots'}], tip: d => `Noche <b>${fmt(d.hrv_ms)} ms</b><br>Media 7 días ${fmt(d.hrv_rolling_ms,1)} ms` + (d.hrv_low_ms != null ? `<br>Rango normal ${fmt(d.hrv_low_ms)}–${fmt(d.hrv_high_ms)} ms` : '')});
const rhrBase = K.baseline_resting_hr;
chart($('c-rhr'), {label:'FC en reposo', refs: rhrBase != null ? [{y: rhrBase, label:`mediana ${fmt(rhrBase)}`}] : [],
  series:[{key:'resting_hr', markers:true}], tip: d => `Reposo <b>${fmt(d.resting_hr)} lpm</b>` + (d.night_hr != null ? `<br>Nocturna ${fmt(d.night_hr,1)} lpm` : '')});
$('sleep-sub').textContent = `horas por noche · línea = necesidad configurada (${fmt(S.need_hours,1)} h)`;
chart($('c-sleep'), {label:'Sueño', zero:true, refs:[{y:S.need_hours, label:`${fmt(S.need_hours,1)} h`}],
  series:[{key:'sleep_hours', kind:'bar'}], tip: d => `Sueño <b>${fmt(d.sleep_hours,1)} h</b>` + (d.sleep_score != null ? `<br>Puntuación ${fmt(d.sleep_score)}` : '')});
chart($('c-load'), {label:'Carga diaria', zero:true,
  series:[{key:'load', kind:'bar', color:'--series-2'}], tip: d => `Carga <b>${fmt(d.load)}</b> · ${d.sessions} sesión(es)` + (d.srpe ? `<br>sRPE ${fmt(d.srpe)}` : '')});

// ---------- Tablas ----------
const typeEs = t => ({HighIntensityIntervalTraining:'HIIT', WeightTraining:'Fuerza', Run:'Carrera', Ride:'Bici', Walk:'Caminar', Swim:'Natación'})[t] || t || '—';
const sess = D.recent_sessions || [];
$('sessions').innerHTML = sess.length ? `<thead><tr><th>Fecha</th><th>Tipo</th><th>Sesión</th><th class="num">Min</th><th class="num">Carga</th><th class="num">FC media</th><th class="num">RPE</th><th class="num">sRPE</th></tr></thead><tbody>` +
  sess.map(s => `<tr><td>${dshort(s.date)} ${s.start_local ? s.start_local.slice(11,16) : ''}</td><td>${esc(typeEs(s.type))}</td><td>${esc(s.label || s.name || '')}</td><td class="num">${fmt(s.duration_min)}</td><td class="num">${fmt(s.load)}</td><td class="num">${fmt(s.avg_hr)}</td><td class="num">${fmt(s.rpe,1)}</td><td class="num">${fmt(s.srpe)}</td></tr>`).join('') + '</tbody>'
  : '<tbody><tr><td class="empty">Sin sesiones registradas</td></tr></tbody>';
const today = T[T.length - 1] || {};
const legacy = D.legacy_v2 || {};
$('rule').textContent = DEC.rule || '';
const roleEs = {oficial:'oficial', salvaguarda:'salvaguarda', sombra:'en pruebas', compatibilidad:'compatibilidad', contexto:'contexto'};
$('compare').innerHTML = `<thead><tr><th>Modelo</th><th>Rol</th><th class="num">Puntuación</th><th>Zona</th><th>Decide</th></tr></thead><tbody>` +
  (DEC.registry || []).map(m => `<tr><td title="${esc(m.rule)}">${esc(m.label)} <span class="weight">${esc(m.version || '')}</span></td><td>${roleEs[m.role] || esc(m.role)}</td><td class="num">${fmt(m.score)}</td><td>${m.zone ? zoneTxt[m.zone] : '—'}</td><td>${m.used_in_decision ? ((DEC.decided_by || []).includes(m.id) ? '<b>sí · fija la zona</b>' : 'sí') : 'no'}</td></tr>`).join('') +
  `<tr><td colspan="5" class="weight">Otras señales</td></tr>
  <tr><td>Estrés medio Garmin (día)</td><td></td><td class="num">${fmt(today.stress_avg)}</td><td colspan="2">día en curso, parcial</td></tr>
  <tr><td>Monotonía / strain 7 días</td><td></td><td class="num">${fmt(L.monotony,2)} / ${fmt(L.strain)}</td><td colspan="2">monotonía &gt; 2 = carga poco variada</td></tr>
  <tr><td>Días seguidos entrenando</td><td></td><td class="num">${L.consecutive_training_days}</td><td colspan="2">—</td></tr></tbody>`;
$('daily').innerHTML = `<thead><tr><th>Fecha</th><th>Turno</th><th class="num">Punt.</th><th class="num">HRV</th><th class="num">HRV 7d</th><th class="num">FC rep.</th><th class="num">Sueño h</th><th class="num">Carga</th></tr></thead><tbody>` +
  T.slice().reverse().map(d => `<tr><td>${dshort(d.date)}</td><td>${esc(d.shift || '')}</td><td class="num">${fmt(d.score)}</td><td class="num">${fmt(d.hrv_ms)}</td><td class="num">${fmt(d.hrv_rolling_ms,1)}</td><td class="num">${fmt(d.resting_hr)}</td><td class="num">${fmt(d.sleep_hours,1)}</td><td class="num">${fmt(d.load)}</td></tr>`).join('') + '</tbody>';

const CE = D.certificate || {}, TI = D.training_integrity || {}, CY = CE.cycle || {};
const okTxt = ok => ok ? '<span class="pos">✓</span>' : '<span class="neg">!</span>';
const ageTxt = a => a.age_minutes == null ? 'sin marca temporal' : (a.age_minutes < 90 ? `hace ${fmt(a.age_minutes)} min` : `hace ${fmt(a.age_minutes/60,1)} h`);
const ageLbl = {confirmed_sleep:'Fin del sueño', sleep_hrv:'Última muestra HRV', heart_rate_live:'Última FC', body_battery_live:'Último Body Battery'};
$('cert-sub').textContent = `Estado: ${CE.status === 'ok' ? 'sin avisos' : 'con avisos'}` + ((CE.issues || []).length ? ` · ${CE.issues.join(' · ')}` : '');
const cons = (CE.consistency_v3_v2 || {});
$('cert').innerHTML = `<thead><tr><th>Comprobación</th><th>Resultado</th></tr></thead><tbody>
  <tr><td>Ciclo certificado</td><td>${esc(CY.cycle_id || '—')} ${okTxt(CY.status === 'ready')}</td></tr>
  <tr><td>Sincronización de los datos</td><td>${CY.data_synced_at ? new Date(CY.data_synced_at).toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'}) : '—'}${CY.data_newer_than_certified_cycle ? ' · Sync fuera de franja' : ''}</td></tr>
  ${Object.entries(CE.data_age || {}).map(([k,a]) => `<tr><td>${ageLbl[k] || k}</td><td>${ageTxt(a)} ${okTxt(a.state === 'reciente')}</td></tr>`).join('')}
  <tr><td>Coherencia v3 / v2 (HRV, FC, sueño)</td><td>${cons.status === 'ok' ? 'idénticos' : esc(cons.status || '—')} ${okTxt(cons.status === 'ok')}</td></tr>
  <tr><td>Huellas SHA-256</td><td>${Object.keys(CE.source_sha256 || {}).length} fuentes</td></tr>
  <tr><td>Entrega del informe</td><td>no verificable desde los datos</td></tr></tbody>`;
$('integrity').innerHTML = `<thead><tr><th>Integridad del entrenamiento (${TI.window_days || 14} días)</th><th class="num"></th></tr></thead><tbody>
  <tr><td>Sesiones con RPE (por ID)</td><td class="num">${TI.with_rpe ?? '—'} / ${TI.sessions ?? '—'} (${fmt(TI.rpe_coverage_pct)} %)</td></tr>
  <tr><td>RPE sin actividad asociada</td><td class="num">${(TI.rpe_without_activity || []).length} ${okTxt(!(TI.rpe_without_activity || []).length)}</td></tr>
  <tr><td>Fechas RPE ≠ actividad</td><td class="num">${(TI.date_mismatch || []).length} ${okTxt(!(TI.date_mismatch || []).length)}</td></tr>
  ${(TI.without_rpe || []).map(x => `<tr><td colspan="2" class="weight">Sin RPE: ${x.start_local ? dshort(x.start_local.slice(0,10)) + ' ' + x.start_local.slice(11,16) : ''} · ${esc(typeEs(x.type))} · ${fmt(x.duration_min)} min · carga ${fmt(x.load)}</td></tr>`).join('')}
  <tr><td colspan="2" class="weight">Datos: ${esc(DC.level || '—')}${(DC.why || []).length ? ' (' + esc(DC.why.join('; ')) + ')' : ''} · Recomendación: ${esc(RC.level || '—')}${(RC.why || []).length ? ' (' + esc(RC.why.join('; ')) + ')' : ''}</td></tr></tbody>`;

// ---------- RPE frente al máximo y calendario ----------
const RPE = {}; (D._rpe_days || []).forEach(r => { RPE[r.date] = r; });
T.forEach(d => { const r = RPE[d.date] || {}; d.rpe_ok = r.rpe != null && !r.over ? r.rpe : null;
  d.rpe_over = r.over ? r.rpe : null; d.rpe_cap = r.cap; d.rpe_type = r.type; });
chart($('c-rpe'), {label:'RPE frente al máximo del día', min:0, max:10,
  series:[{key:'rpe_ok', kind:'bar'}, {key:'rpe_over', kind:'bar', color:'--critical'}, {key:'rpe_cap', kind:'tick', color:'--text-2'}],
  tip: d => (d.rpe_ok ?? d.rpe_over) == null ? 'Sin sesión con RPE' :
    `RPE <b>${fmt(d.rpe_ok ?? d.rpe_over, 1)}</b> · ${esc(d.rpe_type || '')}` + (d.rpe_cap != null ? `<br>Máximo del día ${d.rpe_cap}` + (d.rpe_over != null ? ' · <b>por encima</b>' : ' · dentro') : '<br>Sin decisión guardada ese día')});
const SESS = D.sessions_28d || [];
const cal = $('cal'), det = $('cal-detail');
if (cal && T.length) {
  const first = new Date(T[0].date + 'T12:00'), lead = (first.getDay() + 6) % 7;
  let html = ''; for (let k = 0; k < lead; k++) html += '<button class="empty-day" tabindex="-1" aria-hidden="true"></button>';
  T.forEach((d, i) => {
    const z = d.decision_zone || d.zone || 'unavailable', r = RPE[d.date] || {};
    const cls = `z-${String(z).replace(/[^a-z_]/g, '')}${d.decision_zone ? '' : ' v3'}${r.over ? ' over' : ''}`;
    html += `<button class="${cls}" data-i="${i}" aria-label="${esc(d.date)}"><span class="dn">${+d.date.slice(8)}</span>${r.rpe != null ? `<b>${fmt(r.rpe)}</b>` : (d.sessions ? '•' : '')}</button>`;
  });
  cal.innerHTML = html;
  const show = i => {
    const d = T[i], r = RPE[d.date] || {}, z = d.decision_zone || d.zone;
    cal.querySelectorAll('button').forEach(b => b.classList.toggle('sel', b.dataset.i == i));
    const ss = SESS.filter(x => x.date === d.date);
    det.innerHTML = `<b>${new Date(d.date + 'T12:00').toLocaleDateString('es-ES',{weekday:'long', day:'numeric', month:'long'})}</b>` +
      (d.shift ? ` · turno ${esc(d.shift)}` : '') + `<br>Decisión: <b>${z ? zoneTxt[z] : '—'}</b>${d.decision_zone ? '' : ' (v3; decisión no guardada ese día)'}` +
      (r.cap != null ? ` · RPE máx. ${r.cap}` : '') + `<br>Sueño ${fmt(d.sleep_hours,1)} h · HRV ${fmt(d.hrv_ms)} ms · FC reposo ${fmt(d.resting_hr)} lpm` +
      (ss.length ? `<div class="scroll"><table><thead><tr><th>Hora</th><th>Sesión</th><th class="num">Min</th><th class="num">RPE</th><th class="num">sRPE</th></tr></thead><tbody>` +
        ss.map(x => `<tr><td>${x.start_local ? x.start_local.slice(11,16) : ''}</td><td>${esc(x.label || x.name || '')}</td><td class="num">${fmt(x.duration_min)}</td><td class="num">${fmt(x.rpe,1)}</td><td class="num">${fmt(x.srpe)}</td></tr>`).join('') + '</tbody></table></div>'
        : '<br><span class="weight">Sin sesiones registradas.</span>');
  };
  cal.addEventListener('click', ev => { const b = ev.target.closest('button[data-i]'); if (b) show(+b.dataset.i); });
  show(T.length - 1);
}

$('footer').innerHTML = `<b>Metodología.</b> HRV en ln(rMSSD): media de 7 días frente a tu línea base de hasta 60 días con banda de cambio mínimo relevante (±0,5 DE). FC en reposo y nocturna en desviaciones robustas (mediana/MAD). Sueño frente a ${fmt(S.need_hours,1)} h de necesidad y deuda de ${'3'} noches. La carga solo puntúa cuando la carga crónica (CTL) permite interpretar la forma. Sin datos de hoy o con sueño sin confirmar no se autoriza intensidad alta.<br>${esc(R.disclaimer)} · App ${esc(D.app_version)} · Historial desde ${esc(D.history.first_date || '—')} (${D.history.sessions} sesiones).`;
})();
</script>
</body>
</html>
"""
