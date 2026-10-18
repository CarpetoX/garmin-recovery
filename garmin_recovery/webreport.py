"""Página interactiva del informe completo (``informe_completo.html``).

Toma el Markdown del informe como fuente de verdad, lo reparte en secciones plegables con índice fijo y sustituye las
imágenes por gráficas interactivas (valores al tocar, selector de 7/14/28 días) dibujadas con los mismos datos
embebidos en la página. Sin red ni librerías: HTML, CSS y JavaScript propios. Sin JavaScript se ven las imágenes SVG.
"""
from __future__ import annotations

import html
import json
import re

from . import mdhtml

FIELDS = ("date", "hrv_ms", "hrv_low_ms", "hrv_high_ms", "hrv_rolling_ms", "resting_hr", "night_hr", "sleep_hours",
          "sleep_context", "deep_min", "rem_min", "load", "srpe", "sessions", "atl", "ctl", "score", "v2_score",
          "hybrid_score", "decision_zone", "shift")
INTERACTIVE = {"readiness.svg": "recovery", "hrv.svg": "hrv", "rhr.svg": "rhr", "sleep.svg": "sleep",
               "sleep_stages.svg": "stages", "load.svg": "load", "rpe.svg": "rpe"}
SECTION = re.compile(r"^## (.+)$", re.M)


def _data(result: dict) -> dict:
    rpe_by_day: dict[str, float] = {}
    for s in result.get("sessions_28d") or []:
        r = s.get("rpe")
        d = (s.get("date") or "")[:10]
        if isinstance(r, (int, float)) and d and s.get("removed") in (0, "0", None, False):
            rpe_by_day[d] = max(rpe_by_day.get(d, 0), float(r))
    trend = []
    for t in result.get("trend_28d") or []:
        row = {k: t.get(k) for k in FIELDS}
        row["rpe_max"] = rpe_by_day.get(t.get("date"))
        trend.append(row)
    from .config import DEFAULTS
    return {"trend": trend, "need": DEFAULTS["sleep_need_hours"]}


def _weights(result: dict) -> str:
    comps = ((result.get("readiness") or {}).get("components")) or {}
    rows = []
    for c in comps.values():
        if isinstance(c, dict) and c.get("label"):
            sc = c.get("score")
            rows.append(f"{c['label']}|{'' if sc is None else round(sc)}|{round((c.get('weight') or 0) * 100)}")
    return "\n".join(rows)


SUBTITLES = {"Resumen": "lo esencial en 5 líneas", "1.": "estado del ciclo y calidad de los datos",
             "2.": "HRV, FC y modelos frente a tu normalidad", "3.": "duración, puntuación y fases",
             "4.": "FC, estrés y Body Battery", "5.": "carga y sesiones recientes", "6.": "series, cargas y metcons",
             "7.": "turnos, señales y recomendaciones", "8.": "plan de mejora y de 7 días", "Conclusión": "cierre y traza del ciclo", "Análisis de Claude": "explicación en llano y plan de 7 días"}
SHORT = {"Resumen": "Resumen", "Análisis de Claude": "Claude", "1.": "Calidad", "2.": "Recuperación", "3.": "Sueño", "4.": "FC", "5.": "CrossFit",
         "6.": "Fuerza", "7.": "Balance", "8.": "Mejora", "Conclusión": "Conclusión"}


# Lo que más se consulta primero: qué hacer hoy, cómo estás, sueño y carga; el detalle técnico y la certificación al final.
ORDER = ("7.", "Análisis de Claude", "2.", "3.", "5.", "8.", "4.", "6.", "Resumen", "1.", "Conclusión")
OPEN = ("7.", "Análisis de Claude")


def _rank(title: str) -> int:
    return next((i for i, k in enumerate(ORDER) if title.startswith(k)), len(ORDER))


ICONS = {'7.': '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>', '2.': '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>', '3.': '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>', '5.': '<path d="M6.5 6.5v11M17.5 6.5v11M3.5 9v6M20.5 9v6M6.5 12h11"/>', '8.': '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>', '4.': '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>', '6.': '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', 'Resumen': '<path d="M4 6h16M4 12h16M4 18h10"/>', '1.': '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>', 'Conclusión': '<path d="M5 12l5 5L20 7"/>'}
ICONS["Análisis de Claude"] = ('<path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z"/>'
                               '<path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>')


def _lookup(table: dict, title: str) -> str:
    return next((v for k, v in table.items() if title.startswith(k)), "")


BADGE_WORDS = {"ok": ("Correcto", "READY", "Disponible", "high", "alta", "Validado"),
               "warn": ("con avisos", "medium", "media", "Pendiente", "pendiente"), "bad": ("Fallo", "failed", "low", "baja", "No disponible")}
EMOJI_CLS = {"🟢": "ok", "🟡": "warn", "🔴": "bad", "⚪": "neu"}
CELL = re.compile(r"<td>(?:(🟢|🟡|🔴|⚪)\s*)?([^<]*)</td>")


def badges(body_html: str) -> str:
    """Convierte las celdas de estado (✓ Correcto, READY, 🟢 al día…) en insignias de color; el texto no cambia."""
    def sub(m):
        emoji, text = m.group(1), m.group(2).strip()
        cls = EMOJI_CLS.get(emoji) if emoji else next((c for c, words in BADGE_WORDS.items()
                                                       if any(text == w or text.startswith(w + " ") for w in words)), None)
        if not cls or not text:
            return m.group(0)
        return f'<td><span class="bdg {cls}">{text}</span></td>'
    return CELL.sub(sub, body_html)


def _slug_label(title: str) -> str:
    short = _lookup(SHORT, title)
    if short:
        return short
    t = re.sub(r"^\d+\.\s*", "", title).strip()
    return t if len(t) <= 22 else t[:21].rstrip() + "…"


def build(md: str, result: dict) -> str:
    parts = SECTION.split(md)
    head, titles, bodies = parts[0], parts[1::2], parts[2::2]
    charts = INTERACTIVE
    weights = _weights(result)
    chips, sections = [], []
    order = sorted(range(len(titles)), key=lambda j: (_rank(titles[j]), j))
    for i in order:
        title, body = titles[i], bodies[i]
        if title.startswith("2.") and weights:
            body = "\n```weights\n" + weights + "\n```\n" + body
        sid = f"s{i}"
        chips.append(f'<a href="#{sid}">{html.escape(_slug_label(title))}</a>')
        opened = " open" if title.startswith(OPEN) else ""
        shown = re.sub(r"^\d+\.\s*", "", title)
        sub = _lookup(SUBTITLES, title)
        ic = _lookup(ICONS, title)
        icon_html = (f'<i class="ico" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" '
                     f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ic}</svg></i>' if ic else "")
        sub_html = f"<small>{html.escape(sub)}</small>" if sub else ""
        sections.append(f'<details class="sec" id="{sid}"{opened}><summary>{icon_html}<span><h2>{mdhtml.inline(shown)}</h2>{sub_html}</span></summary>'
                        f'<div class="body">{badges(mdhtml.render(body, interactive=charts))}</div></details>')
    data = json.dumps(_data(result), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return PAGE.replace("{{HEAD}}", mdhtml.render(head, interactive=charts)).replace("{{CHIPS}}", "".join(chips)) \
        .replace("{{SECTIONS}}", "\n".join(sections)).replace("{{DATA}}", data).replace("{{CSS}}", CSS).replace("{{JS}}", JS)


CSS = """
:root{color-scheme:light dark;--bg:#f6f6f4;--surface:#fff;--surface-2:#efefec;--line:#dcdcd6;--text:#1b1b19;--text-2:#55554e;--text-3:#63625c;
--s1:#2a78d6;--s1w:rgba(42,120,214,.16);--s2:#d95926;--s3:#1baf7a;--s4:#9a9990;--good:#0ca30c;--warn:#fab219;--crit:#d03b3b}
@media(prefers-color-scheme:dark){:root{--bg:#121211;--surface:#1a1a19;--surface-2:#242422;--line:#30302d;--text:#f0efec;--text-2:#c3c2b7;--text-3:#aeada3;--s1:#3987e5;--s1w:rgba(57,135,229,.2)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:860px;margin:0 auto;padding:12px 16px 56px}.back{font-size:13px;color:var(--text-3)}.back a{color:inherit}
h1{font-size:22px;margin:10px 0 2px;letter-spacing:-.01em}.wrap>p:first-of-type{color:var(--text-2);font-size:13px;margin:0 0 12px}
nav.bar{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(6px);padding:8px 0;border-bottom:1px solid var(--line);margin:0 -16px 12px;padding-left:16px;padding-right:16px}
.chips{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding-bottom:6px}.chips::-webkit-scrollbar{display:none}
.chips a,.seg button,.tools button{white-space:nowrap;font-size:13px;color:var(--text-2);background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:4px 12px;text-decoration:none;cursor:pointer;font-family:inherit}
.chips a:active,.tools button:active{background:var(--surface-2)}
.tools{display:flex;gap:8px;align-items:center;justify-content:space-between;flex-wrap:wrap}.seg{display:flex;gap:4px}
.seg button[aria-pressed=true]{background:var(--s1);border-color:var(--s1);color:#fff}
details.sec{background:var(--surface);border:1px solid var(--line);border-radius:14px;margin:12px 0;scroll-margin-top:96px}
details.sec>summary{list-style:none;cursor:pointer;padding:14px 16px;display:flex;align-items:center;gap:12px}details.sec>summary>span{flex:1;min-width:0}.ico{display:grid;place-items:center;flex:0 0 36px;height:36px;border-radius:12px;background:var(--glass-chip,var(--surface-2));color:var(--s1)}
details.sec>summary::-webkit-details-marker{display:none}details.sec>summary::after{content:"▾";color:var(--text-3);transition:transform .15s}
details.sec:not([open])>summary::after{transform:rotate(-90deg)}.body tbody tr:nth-child(even){background:var(--glass-chip,var(--surface-2))}.body tbody tr:nth-child(even) td{border-bottom-color:transparent}.bdg{display:inline-block;padding:1px 10px;border-radius:999px;font-size:12.5px;font-weight:600;background:var(--glass-chip,var(--surface-2));white-space:nowrap}.bdg::before{content:"";display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:var(--s4)}.bdg.ok::before{background:var(--good)}.bdg.warn::before{background:var(--warn)}.bdg.bad::before{background:var(--crit)}
.body td:first-child,.body th:first-child{border-radius:8px 0 0 8px}.body td:last-child,.body th:last-child{border-radius:0 8px 8px 0}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}details.sec,.kpi{animation:rise .4s cubic-bezier(.22,.8,.24,1) both}@media(prefers-reduced-motion:reduce){details.sec,.kpi{animation:none}}details.sec h2{font-size:16px;margin:0;font-weight:640}details.sec summary small{display:block;font-size:12.5px;color:var(--text-3);margin-top:1px}.body{padding:0 16px 16px}.body h3{font-size:14.5px;margin:18px 0 6px}
.body p{margin:.5em 0}.body ul,.body ol{padding-left:20px}.body li{margin:.3em 0}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
th{color:var(--text-2);font-weight:600;font-size:12.5px}code{background:var(--surface-2);padding:1px 5px;border-radius:4px;font-size:.9em}
pre{background:var(--surface-2);padding:10px;overflow-x:auto;border-radius:8px;font-size:12.5px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(135px,1fr));gap:8px;margin:12px 0}
.kpi{background:var(--surface);border:1px solid var(--line);border-left:5px solid var(--s4);border-radius:10px;padding:12px 14px;display:flex;flex-direction:column;gap:1px}
.kpi span{font-size:12px;color:var(--text-3)}.kpi strong{font-size:1.4rem;line-height:1.2;font-variant-numeric:tabular-nums;letter-spacing:-.01em}.kpi small{color:var(--text-3);font-size:12px}
.kpi.green{border-left-color:var(--good)}.kpi.yellow{border-left-color:var(--warn)}.kpi.red{border-left-color:var(--crit)}
.fig{margin:14px 0}.fig .cap{font-size:13px;color:var(--text-2);margin:0 0 4px;font-weight:600}.fig .leg{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--text-2);margin:2px 0 4px}
.fig .leg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.fig img{width:100%;height:auto;background:#fff;border-radius:8px}
figure{margin:12px 0}figure>img{display:block;width:100%;max-width:100%;height:auto;border-radius:12px}
.body img,.body svg{max-width:100%}
.ichart{position:relative;width:100%;height:200px}.ichart svg{display:block;width:100%;height:100%;overflow:visible}
.empty{display:grid;place-items:center;height:100%;color:var(--text-3);font-size:13px}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:6px 9px;font-size:12px;line-height:1.4;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;opacity:0;transition:opacity .08s;z-index:6}
.wts{margin:10px 0}.wts .row{display:grid;grid-template-columns:minmax(110px,190px) 1fr 52px;gap:10px;align-items:center;padding:5px 0;font-size:13px}
.wts .m{height:8px;border-radius:4px;background:var(--surface-2);overflow:hidden}.wts .m i{display:block;height:100%;border-radius:4px}
.wts small{color:var(--text-3)}.wts .t{font-size:13px;font-weight:600;margin:0 0 4px}
/* ---- Liquid glass (igual que el panel); opaco si no hay desenfoque o se piden menos transparencias ---- */
:root{--glass:rgba(255,255,255,.58);--glass-edge:rgba(255,255,255,.75);--glass-shadow:0 8px 30px rgba(20,30,60,.10);
--glass-hi:inset 0 1px 0 rgba(255,255,255,.85),inset 0 -1px 0 rgba(255,255,255,.25);--glass-chip:rgba(90,100,120,.12);
--blob-a:rgba(66,133,244,.30);--blob-b:rgba(255,140,90,.22);--blob-c:rgba(60,200,150,.20)}
@media(prefers-color-scheme:dark){:root{--glass:rgba(34,36,44,.55);--glass-edge:rgba(255,255,255,.14);--glass-shadow:0 10px 34px rgba(0,0,0,.40);
--glass-hi:inset 0 1px 0 rgba(255,255,255,.14),inset 0 -1px 0 rgba(255,255,255,.04);--glass-chip:rgba(255,255,255,.09);
--blob-a:rgba(57,135,229,.34);--blob-b:rgba(217,89,38,.22);--blob-c:rgba(40,170,120,.20)}}
@supports((-webkit-backdrop-filter:blur(1px)) or (backdrop-filter:blur(1px))){
body{background:radial-gradient(60vmax 50vmax at 8% -5%,var(--blob-a),transparent 60%),radial-gradient(55vmax 45vmax at 100% 12%,var(--blob-b),transparent 60%),
radial-gradient(60vmax 50vmax at 30% 105%,var(--blob-c),transparent 60%),var(--bg);background-attachment:fixed}
details.sec,.kpi{background:var(--glass);border-color:var(--glass-edge);box-shadow:var(--glass-hi),var(--glass-shadow);
-webkit-backdrop-filter:blur(22px) saturate(170%);backdrop-filter:blur(22px) saturate(170%)}
details.sec{border-radius:22px}.kpi{border-radius:16px}
nav.bar{background:var(--glass);border:1px solid var(--glass-edge);border-radius:22px;box-shadow:var(--glass-hi),var(--glass-shadow);
-webkit-backdrop-filter:blur(22px) saturate(170%);backdrop-filter:blur(22px) saturate(170%);margin:0 0 12px;padding:8px 12px;top:8px}
.chips a,.seg button,.tools button{background:var(--glass-chip);border-color:transparent}
.seg button[aria-pressed=true]{background:var(--s1);color:#fff}
code,pre,.wts .m{background:var(--glass-chip)}
}
@media(prefers-reduced-transparency:reduce){body{background:var(--bg)!important}
details.sec,.kpi,nav.bar{background:var(--surface)!important;-webkit-backdrop-filter:none!important;backdrop-filter:none!important}}
@media print{nav.bar,.tools{display:none}details.sec{break-inside:avoid}details.sec:not([open])>.body{display:block}}
"""

JS = r"""
(function(){
const D=JSON.parse(document.getElementById('d').textContent),ALL=D.trend,NEED=D.need;let T=ALL.slice(-28);
const fmt=(v,d=0)=>v==null?'—':Number(v).toFixed(d).replace('.',',');
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dshort=s=>{const p=s.split('-');return (+p[2])+'/'+(+p[1])};
const hm=m=>m==null?'—':Math.floor(m/60)+' h '+String(Math.round(m%60)).padStart(2,'0')+' min';
const tip=document.getElementById('tip');
const ZN={green:'verde',yellow:'ámbar',red:'rojo',unavailable:'pendiente'};
const CH={
 recovery:{label:'Recuperación',min:0,max:100,refs:[{y:70,t:'verde'},{y:50,t:'rojo'}],
  series:[{k:'v2_score',c:'--s2',n:'Oficial',m:1},{k:'hybrid_score',c:'--s3',n:'Híbrido',m:1},{k:'score',c:'--s1',n:'Experimental',m:1}],
  tip:d=>`Oficial <b>${fmt(d.v2_score)}</b><br>Híbrido <b>${fmt(d.hybrid_score)}</b><br>Experimental <b>${fmt(d.score)}</b><br>Decisión: ${ZN[d.decision_zone]||'—'}`},
 hrv:{label:'HRV nocturna',band:['hrv_low_ms','hrv_high_ms'],series:[{k:'hrv_rolling_ms',c:'--s1',n:'Media 7 días'},{k:'hrv_ms',c:'--s1',n:'Noche (ms)',dots:1}],band_n:'Rango normal',
  tip:d=>`Noche <b>${fmt(d.hrv_ms)} ms</b><br>Media 7 días ${fmt(d.hrv_rolling_ms,1)} ms`+(d.hrv_low_ms!=null?`<br>Rango normal ${fmt(d.hrv_low_ms)}–${fmt(d.hrv_high_ms)} ms`:'')},
 rhr:{label:'FC en reposo y nocturna',series:[{k:'resting_hr',c:'--s1',n:'Reposo (lpm)',m:1},{k:'night_hr',c:'--s2',n:'Nocturna (lpm)'}],
  tip:d=>`Reposo <b>${fmt(d.resting_hr)} lpm</b><br>Nocturna ${fmt(d.night_hr,1)} lpm`},
 sleep:{label:'Sueño por noche',zero:1,refs:()=>[{y:NEED,t:'necesidad '+fmt(NEED,1)+' h'}],series:[{k:'sleep_hours',c:'--s1',n:'Horas',bar:1}],
  tip:d=>`Sueño <b>${fmt(d.sleep_hours,1)} h</b>`+(d.sleep_context==='day_sleep'?' (diurno)':'')+`<br>Necesidad ${fmt(NEED,1)} h`},
 stages:{label:'Sueño por fases',zero:1,stack:[{k:'deep_min',c:'--s1',n:'Profundo'},{k:'rem_min',c:'--s3',n:'REM'},{k:'rest',c:'--s4',n:'Resto (ligero y vigilia)'}],
  prep:d=>{d.rest=d.sleep_hours!=null&&d.deep_min!=null&&d.rem_min!=null?Math.max(0,d.sleep_hours*60-d.deep_min-d.rem_min):null;return d},
  tip:d=>`Profundo <b>${hm(d.deep_min)}</b><br>REM <b>${hm(d.rem_min)}</b><br>Resto ${hm(d.rest)}<br>Total ${hm(d.sleep_hours==null?null:d.sleep_hours*60)}`},
 load:{label:'Carga diaria',zero:1,series:[{k:'srpe',c:'--s2',n:'sRPE del día',bar:1},{k:'atl',c:'--s1',n:'ATL (7 d)'},{k:'ctl',c:'--s3',n:'CTL (42 d)'}],
  tip:d=>`sRPE <b>${fmt(d.srpe)}</b> · ${d.sessions||0} sesión(es)<br>ATL ${fmt(d.atl,1)} · CTL ${fmt(d.ctl,1)}`},
 rpe:{label:'RPE de la sesión más dura',min:0,max:10,refs:[{y:8,t:'RPE 8'}],series:[{k:'rpe_max',c:'--s2',n:'RPE máx. del día',bar:1}],
  tip:d=>d.rpe_max==null?'Sin sesión con RPE':`RPE <b>${fmt(d.rpe_max,1)}</b> · ${d.sessions||0} sesión(es)`}
};
const niceStep=r=>{const p=Math.pow(10,Math.floor(Math.log10(r||1))),f=r/p;return(f<=1?1:f<=2?2:f<=5?5:10)*p};
function draw(el,o){
 const W=el.clientWidth,H=el.clientHeight,m={t:10,r:10,b:22,l:34},iw=W-m.l-m.r,ih=H-m.t-m.b,n=T.length;
 const rows=T.map(d=>o.prep?o.prep(Object.assign({},d)):d);
 const vals=[];(o.series||[]).forEach(s=>rows.forEach(d=>{if(d[s.k]!=null)vals.push(d[s.k])}));
 if(o.stack)rows.forEach(d=>{const t=o.stack.reduce((a,s)=>a+(d[s.k]||0),0);if(t>0)vals.push(t)});
 if(o.band)rows.forEach(d=>{if(d[o.band[0]]!=null)vals.push(d[o.band[0]],d[o.band[1]])});
 const refs=typeof o.refs==='function'?o.refs():(o.refs||[]);refs.forEach(r=>vals.push(r.y));
 if(!n||W<50||!vals.length){el.innerHTML='<div class="empty">Sin datos suficientes todavía</div>';return}
 let lo=o.min!=null?o.min:Math.min(...vals),hi=o.max!=null?o.max:Math.max(...vals);if(o.zero)lo=0;if(hi===lo){hi+=1;lo-=1}
 const pad=(hi-lo)*.08;if(o.min==null&&!o.zero)lo-=pad;if(o.max==null)hi+=pad;
 const st=niceStep((hi-lo)/4);lo=Math.floor(lo/st)*st;hi=Math.ceil(hi/st)*st;
 const bw=iw/n,x=i=>m.l+bw*(i+.5),y=v=>m.t+ih-(v-lo)/(hi-lo)*ih;
 let s=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(o.label)}">`;
 for(let v=lo;v<=hi+1e-9;v+=st){s+=`<line x1="${m.l}" x2="${W-m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${m.l-6}" y="${y(v)+4}" text-anchor="end" font-size="11" fill="var(--text-3)">${fmt(v,st<1?1:0)}</text>`}
 const every=Math.max(1,Math.ceil(n/Math.max(2,Math.floor(iw/46))));
 rows.forEach((d,i)=>{if((n-1-i)%every===0)s+=`<text x="${x(i)}" y="${H-6}" text-anchor="middle" font-size="11" fill="var(--text-3)">${dshort(d.date)}</text>`});
 if(o.band){const p=rows.map((d,i)=>[i,d[o.band[0]],d[o.band[1]]]).filter(q=>q[1]!=null);
  if(p.length>1)s+=`<path d="M${p.map(q=>x(q[0])+','+y(q[2])).join('L')}L${p.slice().reverse().map(q=>x(q[0])+','+y(q[1])).join('L')}Z" fill="var(--s1w)"/>`}
 refs.forEach(r=>{s+=`<line x1="${m.l}" x2="${W-m.r}" y1="${y(r.y)}" y2="${y(r.y)}" stroke="var(--text-3)" stroke-dasharray="4 3"/>`+(r.t?`<text x="${W-m.r}" y="${y(r.y)-4}" text-anchor="end" font-size="11" fill="var(--text-2)">${esc(r.t)}</text>`:'')});
 const bar=(i,v0,v1,col,w)=>{const t=y(v1),b=y(v0),h=Math.max(1,b-t);return `<rect x="${x(i)-w/2}" y="${t}" width="${w}" height="${h}" rx="${Math.min(3,w/2)}" fill="var(--${col.slice(2)})"/>`};
 const bwid=Math.min(24,bw*.62);
 if(o.stack)rows.forEach((d,i)=>{let acc=0;o.stack.forEach(se=>{const v=d[se.k];if(!v||v<=0)return;s+=bar(i,Math.max(lo,0)+acc,Math.max(lo,0)+acc+v,se.c,bwid);acc+=v})});
 (o.series||[]).forEach(se=>{const col='var('+se.c+')';
  if(se.bar){rows.forEach((d,i)=>{const v=d[se.k];if(v==null||v<=0)return;const hot=o.label.indexOf('RPE')===0&&v>=8;
    s+=`<rect x="${x(i)-bwid/2}" y="${y(v)}" width="${bwid}" height="${Math.max(1,y(Math.max(lo,0))-y(v))}" rx="3" fill="${hot?'var(--crit)':col}"/>`});return}
  const segs=[];let cur=[];rows.forEach((d,i)=>{const v=d[se.k];if(v==null){if(cur.length)segs.push(cur);cur=[]}else cur.push([x(i),y(v)])});if(cur.length)segs.push(cur);
  if(!se.dots)segs.forEach(g=>{if(g.length>1)s+=`<path d="M${g.map(p=>p.join(',')).join('L')}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`});
  if(se.dots||se.m)rows.forEach((d,i)=>{const v=d[se.k];if(v!=null)s+=`<circle cx="${x(i)}" cy="${y(v)}" r="3.8" fill="${col}" stroke="var(--surface)" stroke-width="2"/>`})});
 s+=`<line class="xh" y1="${m.t}" y2="${m.t+ih}" stroke="var(--text-3)" opacity="0"/><rect x="${m.l}" y="0" width="${iw}" height="${H}" fill="transparent"/></svg>`;
 el.innerHTML=s;
 const svg=el.querySelector('svg'),xh=svg.querySelector('.xh');
 const mv=ev=>{const r=svg.getBoundingClientRect(),i=Math.max(0,Math.min(n-1,Math.floor((ev.clientX-r.left-m.l)/bw))),d=rows[i];
  xh.setAttribute('x1',x(i));xh.setAttribute('x2',x(i));xh.setAttribute('opacity',.5);
  tip.innerHTML=`<b>${new Date(d.date+'T12:00').toLocaleDateString('es-ES',{weekday:'short',day:'numeric',month:'short'})}</b>`+(d.shift?` · turno ${esc(d.shift)}`:'')+'<br>'+o.tip(d);
  tip.style.opacity=1;const tw=tip.offsetWidth;let left=r.left+scrollX+x(i)+12;if(left+tw>scrollX+document.documentElement.clientWidth-8)left=r.left+scrollX+x(i)-tw-12;
  tip.style.left=Math.max(8,left)+'px';tip.style.top=(r.top+scrollY+m.t-4)+'px'};
 svg.addEventListener('pointermove',mv);svg.addEventListener('pointerdown',mv);
 svg.addEventListener('pointerleave',()=>{tip.style.opacity=0;xh.setAttribute('opacity',0)});
}
function legend(o){const it=[];if(o.band)it.push(`<span><i style="background:var(--s1w);border:1px solid var(--s1)"></i>${o.band_n||'Rango'}</span>`);
 (o.series||[]).forEach(s=>it.push(`<span><i style="background:var(${s.c})"></i>${esc(s.n)}</span>`));
 (o.stack||[]).forEach(s=>it.push(`<span><i style="background:var(${s.c})"></i>${esc(s.n)}</span>`));return it.join('')}
const els=[...document.querySelectorAll('.ichart')];
els.forEach(el=>{const o=CH[el.dataset.chart];el.parentNode.querySelector('.leg').innerHTML=legend(o)});
const all=()=>els.forEach(el=>draw(el,CH[el.dataset.chart]));
all();new ResizeObserver(()=>all()).observe(document.body);
document.querySelectorAll('.seg button').forEach(b=>b.addEventListener('click',()=>{
 T=ALL.slice(-(+b.dataset.n));document.querySelectorAll('.seg button').forEach(x=>x.setAttribute('aria-pressed',x===b));all()}));
const secs=[...document.querySelectorAll('details.sec')];
document.getElementById('toggle').addEventListener('click',e=>{const open=secs.some(s=>!s.open);secs.forEach(s=>s.open=open);e.target.textContent=open?'Contraer todo':'Expandir todo';all()});
secs.forEach(s=>s.addEventListener('toggle',()=>all()));
document.querySelectorAll('.chips a').forEach(a=>a.addEventListener('click',()=>{const t=document.querySelector(a.getAttribute('href'));if(t&&!t.open){t.open=true;all()}}));
})();
"""

PAGE = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe completo · Garmin Recovery</title><link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#121211">
<style>{{CSS}}</style></head><body><div class="wrap"><p class="back"><a href="./">← Panel</a></p>
{{HEAD}}
<nav class="bar" aria-label="Secciones"><div class="chips">{{CHIPS}}</div>
<div class="tools"><div class="seg" role="group" aria-label="Periodo de las gráficas"><button data-n="7" aria-pressed="false">7 d</button><button data-n="14" aria-pressed="false">14 d</button><button data-n="28" aria-pressed="true">28 d</button></div>
<button id="toggle" type="button">Expandir todo</button></div></nav>
<main>{{SECTIONS}}</main></div><div class="tip" id="tip" role="tooltip"></div>
<script type="application/json" id="d">{{DATA}}</script><script>{{JS}}</script></body></html>
"""
