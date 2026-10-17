"""Panel HTML autocontenido (sin dependencias externas ni red).

Los datos se incrustan como JSON y los gráficos se dibujan en el navegador
con SVG a la anchura real del contenedor (legibles también en el móvil).
"""
from __future__ import annotations

import html
import json

ZONE_UI = {
    "green": ("good", "✓"), "yellow": ("warning", "!"),
    "red": ("critical", "✕"), "unavailable": ("muted", "…"),
}


def _esc(value) -> str:
    return html.escape("" if value is None else str(value))


def render(result: dict) -> str:
    payload = json.dumps(result, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    rd = result["readiness"]
    zone = (result.get("decision") or {}).get("zone") or rd["zone"]
    tone, icon = ZONE_UI.get(zone, ZONE_UI["unavailable"])
    title = "Rendimiento y recuperación"
    return TEMPLATE.replace("{{TITLE}}", title) \
        .replace("{{DATE}}", _esc(result["date"])) \
        .replace("{{TONE}}", tone).replace("{{ICON}}", icon) \
        .replace("{{DATA}}", payload)


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
:root{
  color-scheme: light;
  --bg:#f6f6f4; --surface:#fcfcfb; --surface-2:#f0efec; --line:#e4e3df;
  --text:#0b0b0b; --text-2:#52514e; --text-3:#77766f;
  --series-1:#2a78d6; --series-1-wash:rgba(42,120,214,.12); --series-2:#eb6834;
  --good:#0ca30c; --warning:#fab219; --critical:#d03b3b; --muted:#9a9990;
  --good-ink:#006300; --warning-ink:#7a5200; --critical-ink:#a32727;
  --radius:14px;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --bg:#121211; --surface:#1a1a19; --surface-2:#242422; --line:#30302d;
    --text:#f0efec; --text-2:#c3c2b7; --text-3:#9a998f;
    --series-1:#3987e5; --series-1-wash:rgba(57,135,229,.16); --series-2:#d95926;
    --good-ink:#5fd35f; --warning-ink:#fab219; --critical-ink:#f08080;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --bg:#121211; --surface:#1a1a19; --surface-2:#242422; --line:#30302d;
  --text:#f0efec; --text-2:#c3c2b7; --text-3:#9a998f;
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

  <div class="grid">
    <section class="card hero tone-{{TONE}}" aria-label="Disponibilidad de hoy">
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

    <section class="grid cols-2">
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

    <section class="card" aria-label="Calidad y trazabilidad del informe">
      <h2>Calidad y trazabilidad del informe</h2>
      <p class="h2sub" id="cert-sub"></p>
      <div class="grid cols-2" style="gap:12px 24px">
        <div><div class="scroll"><table id="cert"></table></div></div>
        <div><div class="scroll"><table id="integrity"></table></div></div>
      </div>
    </section>

    <section class="card">
      <h2>Sesiones recientes</h2>
      <p class="h2sub">sRPE = RPE × minutos (Foster), solo con RPE registrado por ID de actividad</p>
      <div class="scroll"><table id="sessions"></table></div>
    </section>

    <section class="card">
      <h2>Modelos y regla de decisión</h2>
      <p class="h2sub" id="rule"></p>
      <div class="scroll"><table id="compare"></table></div>
      <details style="margin-top:14px"><summary>Ver datos diarios (28 días)</summary><div class="scroll" style="margin-top:8px"><table id="daily"></table></div></details>
    </section>
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
      if (se.kind === 'bar') {
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
      tip.innerHTML = `<b>${new Date(d.date + 'T12:00').toLocaleDateString('es-ES',{weekday:'short', day:'numeric', month:'short'})}</b>` + (d.shift ? ` · turno ${d.shift}` : '') + '<br>' + opt.tip(d);
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

$('footer').innerHTML = `<b>Metodología.</b> HRV en ln(rMSSD): media de 7 días frente a tu línea base de hasta 60 días con banda de cambio mínimo relevante (±0,5 DE). FC en reposo y nocturna en desviaciones robustas (mediana/MAD). Sueño frente a ${fmt(S.need_hours,1)} h de necesidad y deuda de ${'3'} noches. La carga solo puntúa cuando la carga crónica (CTL) permite interpretar la forma. Sin datos de hoy o con sueño sin confirmar no se autoriza intensidad alta.<br>${esc(R.disclaimer)} · App ${esc(D.app_version)} · Historial desde ${esc(D.history.first_date || '—')} (${D.history.sessions} sesiones).`;
})();
</script>
</body>
</html>
"""
