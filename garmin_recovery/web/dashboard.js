(function(){
const D = JSON.parse(document.getElementById('data').textContent);
const R = D.readiness, L = D.load, T = D.trend_28d || [];
const $ = id => document.getElementById(id);
const fmt = (v, d=0) => v == null || Number.isNaN(v) ? '—' : Number(v).toLocaleString('es-ES', {maximumFractionDigits:d, minimumFractionDigits:d});
const sign = (v, d=0) => v == null ? '—' : (v > 0 ? '+' : '') + fmt(v, d);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const shiftEs = t => ({free: 'libre', 'post-TN': 'tras TN', unknown: 'sin registrar'})[t] || t;
const dshort = iso => { const [y,m,d] = iso.split('-'); return `${+d}/${+m}`; };
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const zoneTxt = {green:'verde', yellow:'ámbar', red:'rojo', unavailable:'pendiente'};

// ---------- Cabecera y héroe ----------
const gen = new Date(D.generated_at);
$('sub').textContent = `${new Date(D.date+'T12:00').toLocaleDateString('es-ES',{weekday:'long', day:'numeric', month:'long'})} · actualizado ${gen.toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'})}`;
$('badge').textContent = `Modelo experimental · ${D.mode === 'shadow' ? 'en paralelo' : 'activo'}`;
$('badge').title = `Versión ${D.model_version}`;
const DEC = D.decision || {zone: R.zone, guidance: R.guidance, registry: [], divergence: []};
const official = (DEC.registry || []).find(m => m.role === 'oficial') || {};
$('score').innerHTML = official.score == null ? '—' : `${fmt(official.score)}<small>/100</small>`;
(function(){ const a = $('heroarc'); if (!a) return; const c = 2 * Math.PI * 52, v = official.score == null ? 0 : Math.max(0, Math.min(100, official.score));
  a.style.strokeDasharray = c.toFixed(1); a.style.strokeDashoffset = c.toFixed(1);
  requestAnimationFrame(() => requestAnimationFrame(() => { a.style.strokeDashoffset = (c * (1 - v / 100)).toFixed(1); })); })();
$('zone-label').textContent = DEC.guidance.label + (DEC.agreement === 'total' ? ' · los 3 modelos de la app coinciden' : ' · se aplica el modelo más prudente');
const reasons = (R.reasons || []).map(r => r.split(':')[0].replace(/_/g,' '));
const DC = R.data_confidence || {}, RC = R.recommendation_confidence || {};
$('confidence').textContent = `Datos: confianza ${DC.level || '—'} · Recomendación: confianza ${RC.level || R.confidence}` + (reasons.length ? ` · ${reasons.join(', ')}` : '') + ` · historial ${D.history.days} días`;
$('guidance').textContent = DEC.guidance.text;
$('rx').innerHTML = `<span>RPE máx. <b>${DEC.guidance.rpe_max}</b></span><span>Volumen <b>${esc(DEC.guidance.volume)}</b></span>` +
  (DEC.agreement === 'total' ? '' : '<span class="warn-chip">⚠ Los modelos discrepan: se aplica el más prudente</span>');
// V8.5: lo que ya llevas hoy, para que «intensidad permitida» no se lea igual a las 9:00 que tras cuatro sesiones
(function(){
  const day = (D.sessions_28d || []).filter(s => s.date === D.date && !s.removed);
  if (!day.length) return;
  const mins = day.reduce((a, s) => a + (s.duration_min || 0), 0);
  const rp = day.map(s => s.rpe).filter(v => v != null), top = rp.length ? Math.max(...rp) : null;
  const srpe = day.reduce((a, s) => a + (s.srpe || 0), 0), cap = DEC.guidance.rpe_max;
  let msg = '', cls = '';
  if (top != null && cap != null && top > cap) { msg = `Has pasado del máximo de hoy (RPE ${fmt(top, 1)} sobre ${cap}): el resto del día, recuperación.`; cls = 'neg'; }
  else if (top != null && top >= 8) { msg = 'Ya has hecho una sesión dura hoy: lo que añadas, suave.'; cls = 'warn'; }
  const el = document.createElement('p'); el.className = 'today-done ' + cls; el.id = 'hoy-llevas';
  el.innerHTML = `<b>Hoy llevas</b> ${day.length} ${day.length === 1 ? 'sesión' : 'sesiones'} · ${fmt(mins)} min` +
    (top != null ? ` · RPE máx. ${fmt(top, top % 1 ? 1 : 0)}` : '') + (srpe ? ` · sRPE ${fmt(srpe)}` : '') + (msg ? `<br>${msg}` : '');
  $('rx').insertAdjacentElement('afterend', el);
})();
$('v3-title').textContent = `Modelo experimental (en pruebas) · ${R.score == null ? 'sin puntuación' : fmt(R.score) + '/100 · ' + zoneTxt[R.zone]}`;
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
  {label:'Carga 7 días (Intervals)', value: fmt(L.week_load), unit:'', delta: `${L.week_sessions} sesiones` + (L.week_change_pct != null ? ` · ${sign(L.week_change_pct)} % vs. semana previa` : '')},
  {label:'Forma (carga reciente vs. habitual)', value: L.form_interpretable ? sign(L.form_pct) : sign(L.tsb, 1), unit: L.form_interpretable ? '%' : '', delta: L.form_interpretable ? `zona ${L.form_zone} · CTL ${fmt(L.ctl,1)}` : `CTL ${fmt(L.ctl,1)} · aún sin carga crónica suficiente`},
];
const spark = key => { const v = T.slice(-14).map(d => d[key]).filter(x => x != null); if (v.length < 3) return '';
  const lo = Math.min(...v), hi = Math.max(...v), r = hi - lo || 1, pts = v.map((a, i) => [i / (v.length - 1) * 80, 4 + (1 - (a - lo) / r) * 20]);
  return `<svg class="spark" viewBox="0 0 80 28" aria-hidden="true"><path d="${smooth(pts)}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linecap="round"/><circle cx="${pts[pts.length-1][0]}" cy="${pts[pts.length-1][1].toFixed(1)}" r="2.6" fill="var(--series-1)"/></svg>`; };
const sparkKeys = ['hrv_rolling_ms', 'resting_hr', 'sleep_hours', 'load', null];
$('tiles').innerHTML = tiles.map((t, i) => `<div class="card tile"><div class="label">${t.label}</div><div class="value">${t.value}<small>${t.unit}</small>${sparkKeys[i] ? spark(sparkKeys[i]) : ''}</div><div class="delta">${esc(t.delta)}</div></div>`).join('');

// ---------- Medidores ----------
const tone = s => s == null ? 'var(--muted)' : s >= 70 ? 'var(--good)' : s >= 50 ? 'var(--warning)' : 'var(--critical)';
$('meters').innerHTML = Object.entries(C).map(([k, c]) => `
  <div class="meter-row"><div class="name">${esc(c.label)} <span class="weight">(${Math.round(c.weight*100)} %)</span></div>
  <div class="meter" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${c.score ?? ''}" aria-label="${esc(c.label)}"><i style="width:${c.score ?? 0}%;background:${tone(c.score)}"></i></div>
  <div class="val">${c.score == null ? '<span class="weight">sin datos</span>' : fmt(c.score)}</div></div>`).join('');

// ---------- Tres indicadores: Recuperación · Sueño · Carga ----------
(function(){
  const ring = (pct, color) => { const r = 27, c = 2 * Math.PI * r, v = pct == null ? 0 : Math.max(0, Math.min(100, pct));
    return `<svg viewBox="0 0 64 64" width="68" height="68" aria-hidden="true"><circle cx="32" cy="32" r="${r}" fill="none" stroke="var(--glass-chip, var(--surface-2))" stroke-width="7"/>` +
      `<circle cx="32" cy="32" r="${r}" fill="none" stroke="${color}" stroke-width="7" stroke-linecap="round" stroke-dasharray="${(c * v / 100).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 32 32)"/></svg>`; };
    const hv = H.score, sl = S.sleep_score;
  const last7 = T.slice(-7), mx = Math.max(1, ...last7.map(t => t.srpe || 0));
  const bars = last7.map(t => `<i style="height:${Math.max(3, Math.round((t.srpe || 0) / mx * 28))}px" title="${dshort(t.date)}: ${t.srpe ? fmt(t.srpe) : 'sin registro'}"></i>`).join('');
  $('rings').innerHTML =
    `<div class="card ring-card"><div class="rw">${ring(sl, tone(sl))}<div class="ring-num">${fmt(sl)}</div></div><div class="ring-label">Sueño</div><div class="ring-sub">${fmt(S.hours, 1)} h · puntuación</div></div>` +
    `<div class="card ring-card"><div class="rw">${ring(hv, tone(hv))}<div class="ring-num">${fmt(hv)}</div></div><div class="ring-label">HRV</div><div class="ring-sub">${fmt(H.today_ms)} ms hoy · puntuación</div></div>` +
    `<div class="card ring-card"><div class="bars7" role="img" aria-label="sRPE de los últimos 7 días">${bars}</div><div class="ring-num">${fmt(L.week_srpe)}</div><div class="ring-label">Carga 7 días</div><div class="ring-sub">sRPE · ${L.week_sessions} sesiones</div></div>`;
})();


// ---------- Motor de gráficos ----------
const tip = $('tip');
// V7.21: animaciones. Las gráficas se dibujan al entrar en pantalla; con «reducir movimiento» no se anima nada.
const RM = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
const LINES = 'path.ln, polyline.pg-line, polyline.wt-line';
function playIn(h) {
  h.querySelectorAll(LINES).forEach(p => { let L = 0; try { L = p.getTotalLength(); } catch (e) {}
    if (!(L > 0)) return; p.style.transition = 'none'; p.style.strokeDasharray = L; p.style.strokeDashoffset = L; });
  h.getBoundingClientRect();  // fija el estado inicial antes de animar
  requestAnimationFrame(() => { h.classList.add('play');
    h.querySelectorAll(LINES).forEach(p => { p.style.transition = ''; p.style.strokeDashoffset = 0; }); });
}
const IOA = (!RM && 'IntersectionObserver' in window) ? new IntersectionObserver(es => es.forEach(e => {
  if (e.isIntersecting) { IOA.unobserve(e.target); playIn(e.target); } }), {threshold: .3}) : null;
function animIn(h) { if (!IOA || !h || h.dataset.anim) return; h.dataset.anim = '1'; h.classList.add('pre'); IOA.observe(h); }
function chart(el, opt){
  const draw = () => {
    const W = el.clientWidth, Hh = el.clientHeight, m = {t:10, r:12, b:22, l:34};
    const iw = W - m.l - m.r, ih = Hh - m.t - m.b, n = T.length;
    if (!n || W < 50) { el.innerHTML = '<div class="empty">Sin datos</div>'; return; }
    const vals = [];
    (opt.series || []).forEach(s => T.forEach(d => { if (d[s.key] != null) vals.push(d[s.key]); }));
    if (opt.stack) T.forEach(d => { const t = opt.stack.reduce((a, se) => a + (d[se.key] || 0), 0); if (t > 0) vals.push(t); });
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
    // marcas de contexto: franja en los turnos de noche y triángulo en los días con una sesión de RPE ≥ 8
    if (!opt.noMarks) {
      const hard = new Set((D.sessions_28d || []).filter(q => q.rpe != null && q.rpe >= 8).map(q => q.date));
      T.forEach((d, i) => {
        if (d.shift === 'TN') s += `<rect x="${x(i) - bw/2}" y="${m.t}" width="${bw}" height="${ih}" fill="var(--series-2)" fill-opacity=".11"/>`;
        if (hard.has(d.date)) s += `<path d="M${x(i) - 4},${m.t + ih} l4,-7 l4,7Z" fill="var(--text-2)"/>`;
      });
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
    if (opt.stack) { const w = Math.min(24, bw * .62);
      T.forEach((d, i) => { let acc = 0; opt.stack.forEach(se => { const v = d[se.key]; if (!v || v <= 0) return;
        const top = y(acc + v), base = y(acc); s += `<rect class="br" style="--i:${i}" x="${x(i) - w/2}" y="${top}" width="${w}" height="${Math.max(1, base - top)}" fill="${se.color}" rx="2"/>`; acc += v; }); }); }
    (opt.series || []).forEach(se => {
      const col = `var(${se.color || '--series-1'})`;
      if (se.kind === 'tick') {
        const w = Math.min(24, bw * .62) + 10;
        T.forEach((d, i) => { const v = d[se.key]; if (v == null) return;
          s += `<line x1="${x(i) - w/2}" x2="${x(i) + w/2}" y1="${y(v)}" y2="${y(v)}" stroke="${col}" stroke-width="3" stroke-linecap="round"/>`; });
      } else if (se.kind === 'bar') {
        const w = Math.min(24, bw * .62);
        T.forEach((d, i) => { const v = d[se.key]; if (v == null || v <= 0) return;
          const top = y(v), base = y(Math.max(lo, 0)), h = Math.max(1, base - top), rr = Math.min(4, w / 2, h);
          s += `<path class="br" style="--i:${i}" d="M${x(i) - w/2},${base}V${top + rr}Q${x(i) - w/2},${top} ${x(i) - w/2 + rr},${top}H${x(i) + w/2 - rr}Q${x(i) + w/2},${top} ${x(i) + w/2},${top + rr}V${base}Z" fill="${col}"/>`; });
      } else {
        const segs = []; let cur = [];
        T.forEach((d, i) => { const v = d[se.key]; if (v == null) { if (cur.length) segs.push(cur); cur = []; } else cur.push([x(i), y(v)]); });
        if (cur.length) segs.push(cur);
        if (se.kind !== 'dots') segs.forEach(g => { if (g.length > 1) { const d = smooth(g);
          if (se.area) s += `<path class="fd" d="${d}L${g[g.length-1][0]},${y(lo)}L${g[0][0]},${y(lo)}Z" fill="${col}" fill-opacity=".13"/>`;
          s += `<path class="ln" d="${d}" fill="none" stroke="${col}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>`; } });
        if (se.kind === 'dots' || se.markers) T.forEach((d, i) => { const v = d[se.key]; if (v != null) s += `<circle class="fd" cx="${x(i)}" cy="${y(v)}" r="4" fill="${col}" stroke="var(--surface)" stroke-width="2"/>`; });
      }
    });
    s += `<line class="xh" x1="0" x2="0" y1="${m.t}" y2="${m.t + ih}" stroke="var(--text-3)" stroke-width="1" opacity="0"/>`;
    s += `<rect x="${m.l}" y="0" width="${iw}" height="${Hh}" fill="transparent"/></svg>`;
    el.innerHTML = s;
    animIn(el);
    const svg = el.querySelector('svg'), xh = svg.querySelector('.xh');
    const move = ev => {
      const rect = svg.getBoundingClientRect(), px = ev.clientX - rect.left;
      const i = Math.max(0, Math.min(n - 1, Math.floor((px - m.l) / bw)));
      const d = T[i];
      xh.setAttribute('x1', x(i)); xh.setAttribute('x2', x(i)); xh.setAttribute('opacity', .5);
      tip.innerHTML = `<b>${new Date(d.date + 'T12:00').toLocaleDateString('es-ES',{weekday:'short', day:'numeric', month:'short'})}</b>` + (d.shift ? ` · turno ${esc(shiftEs(d.shift))}` : '') + '<br>' + opt.tip(d);
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
function smooth(g){ // curva suave (Catmull-Rom → Bézier) que no se sale de los puntos
  if (g.length < 3) return 'M' + g.map(p => p.join(',')).join('L');
  let d = `M${g[0][0]},${g[0][1]}`;
  for (let i = 0; i < g.length - 1; i++) { const p0 = g[i - 1] || g[i], p1 = g[i], p2 = g[i + 1], p3 = g[i + 2] || p2, k = 0.18;
    d += `C${(p1[0] + (p2[0] - p0[0]) * k).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) * k).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) * k).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) * k).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)}`; }
  return d; }
function niceStep(raw){ const p = Math.pow(10, Math.floor(Math.log10(raw || 1))), f = raw / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }

chart($('c-score'), {label:'Disponibilidad 28 días', min:0, max:100, refs:[{y:70},{y:50}],
  series:[{key:'score', markers:true, area:true}], tip: d => d.score == null ? 'Sin puntuación (datos incompletos)' : `Puntuación <b>${fmt(d.score)}</b> · ${zoneTxt[d.zone]}` + (d.garmin_readiness != null ? `<br>Garmin Training Readiness ${fmt(d.garmin_readiness)}` : '')});
chart($('c-hrv'), {label:'HRV nocturna', band:['hrv_low_ms','hrv_high_ms'],
  series:[{key:'hrv_rolling_ms'}, {key:'hrv_ms', kind:'dots'}], tip: d => `Noche <b>${fmt(d.hrv_ms)} ms</b><br>Media 7 días ${fmt(d.hrv_rolling_ms,1)} ms` + (d.hrv_low_ms != null ? `<br>Rango normal ${fmt(d.hrv_low_ms)}–${fmt(d.hrv_high_ms)} ms` : '')});
const rhrBase = K.baseline_resting_hr;
chart($('c-rhr'), {label:'FC en reposo', refs: rhrBase != null ? [{y: rhrBase, label:`mediana ${fmt(rhrBase)}`}] : [],
  series:[{key:'resting_hr', markers:true}], tip: d => `Reposo <b>${fmt(d.resting_hr)} lpm</b>` + (d.night_hr != null ? `<br>Nocturna ${fmt(d.night_hr,1)} lpm` : '')});
$('sleep-sub').textContent = `horas por noche · línea = necesidad configurada (${fmt(S.need_hours,1)} h)`;
chart($('c-sleep'), {label:'Sueño', zero:true, refs:[{y:S.need_hours, label:`${fmt(S.need_hours,1)} h`}],
  series:[{key:'sleep_hours', kind:'bar'}], tip: d => `Sueño <b>${fmt(d.sleep_hours,1)} h</b>` + (d.sleep_score != null ? `<br>Puntuación ${fmt(d.sleep_score)}` : '')});
T.forEach(d => { d.deep_h = d.deep_min != null ? d.deep_min / 60 : null; d.rem_h = d.rem_min != null ? d.rem_min / 60 : null;
  d.rest_h = (d.deep_min != null && d.rem_min != null && d.sleep_hours != null) ? Math.max(0, d.sleep_hours - d.deep_min / 60 - d.rem_min / 60) : null; });
chart($('c-stages'), {label:'Sueño por fases', zero:true, refs:[{y:S.need_hours, label:`${fmt(S.need_hours,1)} h`}],
  stack:[{key:'deep_h', color:'var(--series-1)'}, {key:'rem_h', color:'#1baf7a'}, {key:'rest_h', color:'var(--muted)'}],
  tip: d => d.deep_h == null ? 'Sin fases registradas esa noche' : `Profundo <b>${fmt(d.deep_h,1)} h</b><br>REM <b>${fmt(d.rem_h,1)} h</b><br>Resto ${fmt(d.rest_h,1)} h<br>Total ${fmt(d.sleep_hours,1)} h`});

// ---------- Lectura de cada gráfica: últimos 7 días frente a los 28 ----------
(function(){
  const avg = (arr, k) => { const v = arr.map(d => d[k]).filter(x => x != null); return v.length ? {m: v.reduce((a, b) => a + b, 0) / v.length, n: v.length} : null; };
  const read = (id, key, o) => { const el = $(id); if (!el) return;
    let a = avg(T.slice(-7), key); const b = avg(T, key);
    if (o.rolling) { const last = [...T].reverse().find(d => d[o.rolling] != null); if (last && a) a = {m: last[o.rolling], n: a.n}; }  // misma cifra que la tarjeta
    if (!a || !b || a.n < 4 || b.n < 10) { el.hidden = true; return; }
    const diff = a.m - b.m, dir = Math.abs(diff) < o.eps ? 0 : diff > 0 ? 1 : -1, good = dir === 0 ? null : (o.better === 0 ? null : dir === o.better);
    const cls = dir === 0 ? 'neu' : good === null ? 'neu' : good ? 'pos' : 'neg', arrow = dir === 0 ? '→' : dir > 0 ? '↑' : '↓';
    const word = dir === 0 ? 'estable' : dir > 0 ? 'sube' : 'baja';
    el.className = 'read ' + cls;
    el.innerHTML = `<b>${arrow} ${word}</b> · últimos 7 días ${fmt(a.m, o.dec)} ${o.unit} · media 28 días ${fmt(b.m, o.dec)} ${o.unit}`; };
  read('r-hrv', 'hrv_ms', {eps: 1.5, dec: 0, unit: 'ms', better: 1, rolling: 'hrv_rolling_ms'});
  read('r-rhr', 'resting_hr', {eps: 0.8, dec: 1, unit: 'lpm', better: -1});
  read('r-sleep', 'sleep_hours', {eps: 0.25, dec: 1, unit: 'h', better: 1});
  read('r-load', 'load', {eps: 4, dec: 0, unit: '', better: 0});
})();

// ---------- Mapa de calor de 28 días ----------
(function(){
  const el = $('heat'); if (!el || !T.length) return;
  const maxLoad = Math.max(1, ...T.map(d => d.load || 0)), need = S.need_hours || 7.5;
  const zc = v => v == null ? null : v >= 70 ? 'var(--good)' : v >= 50 ? 'var(--warning)' : 'var(--critical)';
  const sc = h => h == null ? null : h >= need ? 'var(--good)' : h >= need - 1 ? 'var(--warning)' : 'var(--critical)';
  const rows = [
    ['Recuperación', d => ({c: zc(d.score), t: d.score == null ? 'sin puntuación' : fmt(d.score) + '/100'})],
    ['Sueño', d => ({c: sc(d.sleep_hours), t: d.sleep_hours == null ? 'sin dato' : fmt(d.sleep_hours, 1) + ' h'})],
    ['Carga', d => ({c: d.load ? 'var(--series-2)' : null, o: d.load ? (0.25 + 0.75 * d.load / maxLoad) : 1, t: d.load ? 'carga ' + fmt(d.load) : 'sin carga registrada'})]];
  el.innerHTML = '<h2>Mapa de 28 días</h2><p class="h2sub">cada columna es un día · recuperación y sueño por color (verde / ámbar / rojo), carga por intensidad · vacío = sin dato</p><div class="heat">' +
    rows.map(([name, f]) => `<div class="hrow"><span class="hl">${name}</span><div class="hcells">` + T.map(d => { const r = f(d);
      return `<i style="${r.c ? `background:${r.c};opacity:${r.o ?? 1}` : ''}" title="${dshort(d.date)} · ${r.t}"></i>`; }).join('') + '</div></div>').join('') +
    `<div class="hrow"><span class="hl"></span><div class="hax"><span>${dshort(T[0].date)}</span><span>${dshort(T[T.length - 1].date)}</span></div></div></div>`;
})();

// ---------- Carga semanal frente a tu rango de las 3 semanas previas ----------
(function(){
  const el = $('weekload'); if (!el) return;
  const win = o => { const r = T.slice(T.length - 7 * (o + 1), T.length - 7 * o), n = r.filter(d => d.load != null).length;
    const sum = r.reduce((x, d) => x + (d.load || 0), 0); return {sum, full: n >= 6 && sum > 0}; };  // completa = ≥ 6 de 7 días con dato y alguna carga (una semana sin registro no prueba descanso)
  const w0 = win(0), prevAll = [win(1), win(2), win(3)].filter(w => w.full).map(w => w.sum);
  if (T.length < 14 || !w0.full || prevAll.length < 2) { el.innerHTML = '<h2>Carga semanal</h2><p class="h2sub">Aún no hay suficientes semanas completas para comparar (hacen falta la actual y al menos 2 anteriores con datos).</p>'; return; }
  const cur = w0.sum, lo = Math.min(...prevAll), hi = Math.max(...prevAll), top = Math.max(cur, hi) * 1.2 || 1;
  const pos = v => Math.max(0, Math.min(100, v / top * 100)).toFixed(1);
  const state = cur > hi * 1.1 ? ['por encima de tu rango reciente', 'neg'] : cur < lo * 0.9 ? ['por debajo de tu rango reciente', 'neu'] : ['dentro de tu rango reciente', 'pos'];
  el.innerHTML = `<h2>Carga semanal</h2><p class="h2sub">suma de carga de los últimos 7 días frente al rango de tus semanas anteriores completas (hasta 3) · según las sesiones registradas</p>
    <div class="wl"><div class="wl-track"><i class="wl-band" style="left:${pos(lo)}%;width:${(pos(hi) - pos(lo)).toFixed(1)}%"></i><b class="wl-mark ${state[1]}" style="left:${pos(cur)}%"></b></div>
    <div class="wl-axis"><span>0</span><span>rango previo ${fmt(lo)}–${fmt(hi)}</span><span>${fmt(top)}</span></div></div>
    <p class="read ${state[1]}"><b>${fmt(cur)}</b> esta semana · ${state[0]}</p>`;
})();

chart($('c-load'), {label:'Carga diaria', zero:true,
  series:[{key:'load', kind:'bar', color:'--series-2'}], tip: d => `Carga <b>${fmt(d.load)}</b> · ${d.sessions} sesión(es)` + (d.srpe ? `<br>sRPE ${fmt(d.srpe)}` : '')});

// ---------- Tablas ----------
const typeEs = t => ({HighIntensityIntervalTraining:'HIIT', WeightTraining:'Fuerza', Run:'Carrera', Ride:'Bici', Walk:'Caminar', Swim:'Natación'})[t] || t || '—';
const sess = D.sessions_28d && D.sessions_28d.length ? D.sessions_28d.slice().sort((a, b) => (b.start_local || b.date || '').localeCompare(a.start_local || a.date || '')) : (D.recent_sessions || []);  // V7.29: los 28 días
const HRC = (D.hr_curves && D.hr_curves.activities) || {};
const hasCurve = s => !!(HRC[s.id] && HRC[s.id].available);
const EFF = D.session_effort || {};
const effTxt = {alto: 'RPE alto para tu FC', bajo: 'RPE bajo para tu FC'};
const effTip = {alto: 'Te costó más de lo habitual para la FC registrada en este tipo de sesión.',
                bajo: 'La FC fue alta para el esfuerzo que marcaste en este tipo de sesión.'};
const MRES = D.metcon_results || {};  // V8.9: rondas y repeticiones de cada metcon
const mres = id => MRES[id] ? `<span class="sres">${esc(MRES[id])}</span>` : '';
const effFlag = id => { const e = EFF[id]; return e && e.flag ? e : null; };
// ♥ que late a la FC media de la sesión (un latido = 60 / FC segundos)
const beat = hr => `<span class="hrmark${hr > 0 ? ' beat' : ''}" aria-hidden="true"${hr > 0 ? ` style="--beat:${(60 / hr).toFixed(3)}s"` : ''}>♥</span>`;
$('sessions').innerHTML = sess.length ? `<thead><tr><th>Fecha</th><th>Tipo</th><th>Sesión</th><th class="num">Min</th><th class="num">Carga</th><th class="num">FC media</th><th class="num">RPE</th><th class="num">sRPE</th></tr></thead><tbody>` +
  sess.map(s => `<tr${hasCurve(s) ? ` class="clk" tabindex="0" role="button" data-id="${esc(s.id)}" aria-label="Ver la FC de la sesión"` : ''}><td>${dshort(s.date)} ${s.start_local ? s.start_local.slice(11,16) : ''}</td><td>${esc(s.category && s.category !== 'Sin detalle' ? s.category : typeEs(s.type))}</td><td>${hasCurve(s) ? beat(s.avg_hr) + ' ' : ''}${esc(s.label || s.name || '')}${mres(s.id)}${effFlag(s.id) ? ` <span class="effflag ${effFlag(s.id).flag}">${effTxt[effFlag(s.id).flag]}</span>` : ''}</td><td data-l="Min" class="num">${fmt(s.duration_min)}</td><td data-l="Carga" class="num">${fmt(s.load)}</td><td data-l="FC" class="num">${fmt(s.avg_hr)}</td><td data-l="RPE" class="num">${fmt(s.rpe,1)}</td><td data-l="sRPE" class="num">${fmt(s.srpe)}</td></tr>`).join('') + '</tbody>'
  : '<tbody><tr><td class="empty">Sin sesiones registradas</td></tr></tbody>';

// ---------- Detalle de FC de una sesión ----------
function showHr(id, anchor) {
  const c = HRC[id], s = sess.find(x => x.id === id) || (D.sessions_28d || []).find(x => x.id === id), box = $('hrdetail');
  if (!c || !c.available) { box.hidden = true; return; }
  if (anchor) anchor.insertAdjacentElement('afterend', box); else $('tab-entrenos').appendChild(box);
  const pts = c.points, W = 340, H = 190, m = {t: 10, r: 8, b: 24, l: 34}, iw = W - m.l - m.r, ih = H - m.t - m.b;
  const tmax = Math.max(pts[pts.length - 1][0], c.duration_s || 0), ys = pts.map(p => p[1]);
  const lo = Math.floor((Math.min(...ys) - 8) / 10) * 10, hi = Math.ceil((Math.max(...ys) + 6) / 10) * 10;
  const x = t => m.l + t / tmax * iw, y = v => m.t + ih - (v - lo) / (hi - lo) * ih;
  const zb = c.zone_bounds || [], zc = ['#9a9990', '#3987e5', '#1baf7a', '#fab219', '#d95926', '#d03b3b', '#d03b3b'];
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Frecuencia cardíaca durante la sesión" style="width:100%;height:auto;display:block;touch-action:pan-y">`;
  zb.forEach((b, i) => { const bot = Math.max(lo, i === 0 ? lo : zb[i - 1]), top = Math.min(hi, b);  // icu_hr_zones = límite superior de cada zona
    if (top > bot) svg += `<rect x="${m.l}" y="${y(top)}" width="${iw}" height="${y(bot) - y(top)}" fill="${zc[i] || zc[6]}" opacity=".10"/>`; });
  for (let v = lo; v <= hi; v += 20) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${m.l - 5}" y="${y(v) + 4}" text-anchor="end" font-size="10" fill="var(--text-3)">${v}</text>`;
  const step = tmax > 5400 ? 1200 : tmax > 2400 ? 600 : 300;
  for (let t = 0; t <= tmax; t += step) svg += `<text x="${x(t)}" y="${H - 7}" text-anchor="middle" font-size="10" fill="var(--text-3)">${Math.round(t / 60)}′</text>`;
  svg += `<path class="ln" d="M${pts.map(p => x(p[0]).toFixed(1) + ',' + y(p[1]).toFixed(1)).join('L')}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>` +
    `<line id="hrx" y1="${m.t}" y2="${m.t + ih}" stroke="var(--text-3)" opacity="0"/><rect id="hrhit" x="${m.l}" y="0" width="${iw}" height="${H}" fill="transparent"/></svg>`;
  const zs = c.zone_seconds || [], ztot = zs.reduce((a, b) => a + (b || 0), 0);
  const zdon = (() => { if (!(ztot > 0)) return ''; const r = 38, cc = 2 * Math.PI * r; let off = 0, arcs = '';
    zs.forEach((sec, i) => { if (!(sec > 0)) return; const len = sec / ztot * cc;
      arcs += `<circle class="zarc" style="--d:${(off / cc * 0.9).toFixed(2)}s" data-to="${len.toFixed(2)} ${(cc - len).toFixed(2)}" cx="50" cy="50" r="${r}" fill="none" stroke="${zc[i] || zc[6]}" stroke-width="14" stroke-dasharray="${RM ? len.toFixed(2) + ' ' + (cc - len).toFixed(2) : '0 ' + cc.toFixed(2)}" stroke-dashoffset="${(-off).toFixed(2)}" transform="rotate(-90 50 50)"/>`; off += len; });
    const top = zs.reduce((b, v, i) => v > zs[b] ? i : b, 0);
    return `<svg viewBox="0 0 100 100" width="104" height="104" role="img" aria-label="Reparto del tiempo por zonas de FC">${arcs}<text x="50" y="48" text-anchor="middle" font-size="15" font-weight="650" fill="var(--text)">Z${top + 1}</text><text x="50" y="62" text-anchor="middle" font-size="8" fill="var(--text-3)">${Math.round(zs[top] / ztot * 100)} %</text></svg>`; })();
  const zrows = ztot > 0 ? zs.map((sec, i) => sec > 0 ? `<div class="zrow"><span>Z${i + 1}${zb[i] != null ? ` · hasta ${zb[i]}` : ''}</span><i style="width:${Math.max(2, Math.round(sec / ztot * 100))}%;background:${zc[i] || zc[6]}"></i><b>${Math.round(sec / 60)} min</b></div>` : '').join('') : '';
  box.innerHTML = `<h2>${esc((s && (s.label || s.name)) || c.name || 'Sesión')}</h2><p class="h2sub">${dshort(c.date)} ${c.start_local ? c.start_local.slice(11,16) : ''} · ${beat(c.avg_hr)} FC media <b>${fmt(c.avg_hr)}</b> · máx. <b>${fmt(c.max_hr)}</b> lpm · ${fmt((c.duration_s || 0) / 60)} min${s && s.rpe != null ? ' · RPE ' + fmt(s.rpe, 1) : ''}</p>` +
    (effFlag(id) ? `<p class="effflag ${effFlag(id).flag}">${effTxt[effFlag(id).flag]}. ${effTip[effFlag(id).flag]}</p>` : '') +
    `<div class="hrwrap">${svg}<div class="hrtip" id="hrtip"></div></div>` +
    (zrows ? `<h3 class="zh">Tiempo por zona de FC</h3><div class="zdonut">${zdon}<div class="zrows">${zrows}</div></div>` : '') +
    `<p class="h2sub" style="margin-top:8px">Un punto cada ${c.step_s} s (Intervals.icu). Las zonas son las de tu perfil. Es una vista de la sesión: no cambia la decisión del día.</p>`;
  box.hidden = false;
  if (!RM) { const hw = box.querySelector('.hrwrap'); hw.classList.add('pre'); playIn(hw);
    requestAnimationFrame(() => requestAnimationFrame(() => box.querySelectorAll('.zarc').forEach(a => a.setAttribute('stroke-dasharray', a.dataset.to)))); }
  const svgEl = box.querySelector('svg'), xh = $('hrx'), tp = $('hrtip');
  const mv = ev => { const r = svgEl.getBoundingClientRect(), t = Math.max(0, Math.min(tmax, ((ev.clientX - r.left) / r.width * W - m.l) / iw * tmax));
    let b = pts[0]; pts.forEach(p => { if (Math.abs(p[0] - t) < Math.abs(b[0] - t)) b = p; });
    xh.setAttribute('x1', x(b[0])); xh.setAttribute('x2', x(b[0])); xh.setAttribute('opacity', .5);
    tp.innerHTML = `<b>${b[1]} lpm</b> · min ${Math.floor(b[0] / 60)}:${String(b[0] % 60).padStart(2, '0')}`; tp.style.opacity = 1; };
  const hit = $('hrhit'); hit.addEventListener('pointermove', mv); hit.addEventListener('pointerdown', mv);
  hit.addEventListener('pointerleave', () => { tp.style.opacity = 0; xh.setAttribute('opacity', 0); });
  box.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
$('sessions').addEventListener('click', e => { const tr = e.target.closest('tr.clk'); if (tr) showHr(tr.dataset.id); });
// V7.20: la FC de cada sesión en las tarjetas de fuerza, halterofilia y metcons
const TE_TXT = v => v == null ? '—' : v < 1 ? 'sin efecto' : v < 2 ? 'leve' : v < 3 ? 'mantiene' : v < 4 ? 'mejora' : v < 5 ? 'mejora mucho' : 'sobrecarga';
const teBar = (name, v) => `<span class="te-i"><span class="te-n">${name}</span><i class="te-t"><i style="width:${v == null ? 0 : Math.min(100, v / 5 * 100)}%"></i></i><b>${v == null ? '—' : fmt(v, 1)}</b><small>${TE_TXT(v)}</small></span>`;
function miniHr(c) {
  const pts = c.points || [], W = 300, H = 46;
  if (pts.length < 2) return '';
  const tmax = Math.max(pts[pts.length - 1][0], c.duration_s || 0) || 1, ys = pts.map(p => p[1]);
  const lo = Math.min(...ys) - 4, hi = Math.max(...ys) + 4, y = v => 2 + (H - 4) * (1 - (v - lo) / (hi - lo));
  const d = pts.map(p => (p[0] / tmax * W).toFixed(1) + ',' + y(p[1]).toFixed(1)).join('L');
  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true" class="hrspark"><path class="fd" d="M0,${H}L${d}L${W},${H}Z" fill="var(--series-1)" opacity=".12"/><path class="ln" d="M${d}" fill="none" stroke="var(--series-1)" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
}
document.querySelectorAll('.hrmini').forEach(el => {
  const id = el.dataset.id, c = HRC[id], e = effFlag(id);
  let h = '';
  if (c && c.available) h += `<button type="button" class="hrbtn" data-id="${esc(id)}" aria-label="Ver la curva de FC y las zonas de la sesión">${miniHr(c)}<span class="hrmeta">${beat(c.avg_hr)} FC media <b>${fmt(c.avg_hr)}</b> · máx. <b>${fmt(c.max_hr)}</b> lpm<span class="hrmore">curva y zonas ›</span></span></button>`;
  const te = (D.training_effect || {})[id];  // V8.1: efecto de entrenamiento de Garmin (0–5)
  if (te) h += `<div class="te" title="Efecto de entrenamiento de Garmin, de 0 a 5"><span class="te-cap">Efecto de entrenamiento</span>${teBar('Aeróbico', te.aerobic)}${teBar('Anaeróbico', te.anaerobic)}${te.label ? `<span class="te-l">${esc(te.label)}</span>` : ''}</div>`;
  if (e) h += `<p class="effflag ${e.flag}" title="${esc(effTip[e.flag])}">${effTxt[e.flag]}</p>`;
  if (h) { el.innerHTML = h; el.hidden = false; }
  if (c && c.available) { const chip = el.closest('article') && el.closest('article').querySelector('.hrchip'); if (chip) chip.remove(); }  // la FC ya va con su curva
});
document.addEventListener('click', e => { const b = e.target.closest('.hrbtn'); if (b) showHr(b.dataset.id, b.closest('article')); });
document.querySelectorAll('.hrspark, svg.bars, svg.pg-svg, svg.wt-svg').forEach(animIn);
$('sessions').addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { const tr = e.target.closest('tr.clk'); if (tr) { e.preventDefault(); showHr(tr.dataset.id); } } });
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
  T.slice().reverse().map(d => `<tr><td>${dshort(d.date)}</td><td>${esc(shiftEs(d.shift || ''))}</td><td class="num">${fmt(d.score)}</td><td class="num">${fmt(d.hrv_ms)}</td><td class="num">${fmt(d.hrv_rolling_ms,1)}</td><td class="num">${fmt(d.resting_hr)}</td><td class="num">${fmt(d.sleep_hours,1)}</td><td class="num">${fmt(d.load)}</td></tr>`).join('') + '</tbody>';

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
  <tr><td>Coherencia experimental / oficial (HRV, FC, sueño)</td><td>${cons.status === 'ok' ? 'idénticos' : esc(cons.status || '—')} ${okTxt(cons.status === 'ok')}</td></tr>
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
      (d.shift ? ` · turno ${esc(shiftEs(d.shift))}` : '') + `<br>Decisión: <b>${z ? zoneTxt[z] : '—'}</b>${d.decision_zone ? '' : ' (modelo experimental; decisión no guardada ese día)'}` +
      (r.cap != null ? ` · RPE máx. ${r.cap}` : '') + `<br>Sueño ${fmt(d.sleep_hours,1)} h · HRV ${fmt(d.hrv_ms)} ms · FC reposo ${fmt(d.resting_hr)} lpm` +
      (ss.length ? `<div class="scroll"><table><thead><tr><th>Hora</th><th>Sesión</th><th class="num">Min</th><th class="num">RPE</th><th class="num">sRPE</th></tr></thead><tbody>` +
        ss.map(x => `<tr><td>${x.start_local ? x.start_local.slice(11,16) : ''}</td><td class="cal-name">${esc(x.label || x.name || '')}${mres(x.id)}</td><td class="num">${fmt(x.duration_min)}</td><td class="num">${fmt(x.rpe,1)}</td><td class="num">${fmt(x.srpe)}</td></tr>`).join('') + '</tbody></table></div>'
        : '<br><span class="weight">Sin sesiones registradas.</span>');
  };
  cal.addEventListener('click', ev => { const b = ev.target.closest('button[data-i]'); if (b) show(+b.dataset.i); });
  show(T.length - 1);
}

$('footer').innerHTML = `<b>Metodología.</b> HRV en ln(rMSSD): media de 7 días frente a tu línea base de hasta 60 días con banda de cambio mínimo relevante (±0,5 DE). FC en reposo y nocturna en desviaciones robustas (mediana/MAD). Sueño frente a ${fmt(S.need_hours,1)} h de necesidad y deuda de ${'3'} noches. La carga solo puntúa cuando la carga crónica (CTL) permite interpretar la forma. Sin datos de hoy o con sueño sin confirmar no se autoriza intensidad alta.<br>${esc(R.disclaimer)} · App ${esc(D.app_version)} · Historial desde ${esc(D.history.first_date || '—')} (${D.history.sessions} sesiones).` +
  ((D.web_failures || []).length ? `<br>Bloques no disponibles en esta publicación: ${esc([...new Set(D.web_failures.map(f => f.block))].join(', '))}. El resto de la web no depende de ellos.` : '');
})();

// Entrenos: selector Fuerza · Halterofilia · Metcons · Sesiones
(function(){
  const seg = document.querySelector('.seg');
  const panes = document.querySelectorAll('[data-pane].tbpane');
  if (!seg){ panes.forEach(p => { p.hidden = false; }); return; }
  function pick(k){
    seg.querySelectorAll('button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.pane === k)));
    panes.forEach(p => { if (p.dataset.pane === k) p.hidden = false; else p.hidden = true; });
    { const h = document.getElementById('hrdetail'); if (h) h.hidden = true; }
    try { sessionStorage.setItem('entrenos-pane', k); } catch(e){}
  }
  seg.addEventListener('click', e => { const b = e.target.closest('button'); if (b) pick(b.dataset.pane); });
  let k = 'fuerza'; try { k = sessionStorage.getItem('entrenos-pane') || k; } catch(e){}
  pick(seg.querySelector('[data-pane="' + k + '"]') ? k : 'fuerza');
})();

// Pestañas: Hoy · Tendencias · Entrenos · Sistema (los enlaces antiguos como #plan o #calidad siguen funcionando)
(function(){
  const tabs = ['hoy','tendencias','entrenos','sistema'];
  function show(raw){
    const h = (raw || '').replace('#','');
    let t = tabs.includes(h) ? h : null, target = null;
    if (!t && h){ target = document.getElementById(h); const p = target && target.closest('.tab'); t = p ? p.dataset.tab : null; }
    t = t || 'hoy';
    tabs.forEach(n => {
      document.getElementById('tab-' + n).classList.toggle('on', n === t);
      const a = document.querySelector('.tabbar [data-tab="' + n + '"]');
      a.classList.toggle('on', n === t); a.setAttribute('aria-current', n === t ? 'page' : 'false');
    });
    if (target && target.tagName === 'DETAILS') target.open = true;
    if (target) target.scrollIntoView(); else window.scrollTo(0, 0);
  }
  addEventListener('hashchange', () => show(location.hash));
  show(location.hash);
})();

// ==== V8.0 · Menos texto a la vista: las explicaciones se pliegan bajo «Ver detalle» (no se borra nada) ====
(function(){
  const CARD_FOLD = '.h2sub, .pg-note, .marks-note, .tip-line, .notes, .meta';  // las lecturas (.read) son la conclusión de cada gráfica: a la vista
  const ITEM_FOLD = '.why, .pg-note';
  const ITEM = 'article, .plan li, .plan-day, .cal-day';
  const keep = el => el.closest('#hrdetail, .tbhead, .hero, details.more, table, .tip, .hrmini') ||
                     ((el.textContent || '').trim().length <= 40 && el.matches('.h2sub'));
  // 1) Dentro de cada sesión, día o tarjeta pequeña: se abre al tocarla
  document.querySelectorAll(ITEM).forEach(item => {
    const parts = [...item.querySelectorAll(ITEM_FOLD)].filter(el => !el.closest('#hrdetail') && el.closest(ITEM) === item);
    if (!parts.length) return;
    parts.forEach(el => el.classList.add('fold-item'));
    const hint = document.createElement('span'); hint.className = 'fold-hint'; hint.textContent = '+ detalle';
    item.appendChild(hint); item.classList.add('has-fold'); item.tabIndex = item.tabIndex >= 0 ? item.tabIndex : 0;
    const toggle = e => { if (e.target.closest('button, a, .hrbtn, summary')) return; item.classList.toggle('open'); };
    item.addEventListener('click', toggle);
    item.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(e); } });
  });
  // 2) En cada tarjeta: subtítulos explicativos, notas y lecturas pasan a «Ver detalle»
  document.querySelectorAll('section.card').forEach(card => {
    if (card.id === 'hrdetail') return;
    const parts = [...card.querySelectorAll(CARD_FOLD)].filter(el => !keep(el) && !el.classList.contains('fold-item') && !el.closest(ITEM));
    if (!parts.length) return;
    const d = document.createElement('details'); d.className = 'more';
    d.innerHTML = '<summary>Ver detalle</summary><div class="more-body"></div>';
    const body = d.querySelector('.more-body');
    parts.forEach(el => body.appendChild(el));
    card.appendChild(d);
  });
  // 3) Metodología del pie
  const f = document.getElementById('footer');
  if (f && f.textContent.trim() && !f.closest('details')) {
    const d = document.createElement('details'); d.className = 'more';
    d.innerHTML = '<summary>Metodología y versión</summary>';
    f.parentNode.insertBefore(d, f); d.appendChild(f);
  }
})();

// ==== V8.0 · Apariencia: oscuro (por defecto), claro o automático ====
(function(){
  const host = document.getElementById('tab-sistema'); if (!host) return;
  const cur = () => document.documentElement.getAttribute('data-theme') || 'dark';
  const sec = document.createElement('section'); sec.className = 'card'; sec.id = 'apariencia';
  sec.innerHTML = '<h2>Apariencia</h2><div class="theme-seg" role="group" aria-label="Tema de la app">' +
    [['dark', 'Oscuro'], ['light', 'Claro'], ['auto', 'Automático']].map(([k, l]) => `<button type="button" data-t="${k}">${l}</button>`).join('') + '</div>';
  host.insertBefore(sec, host.firstChild);
  const paint = () => sec.querySelectorAll('button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.t === cur())));
  sec.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.t === 'dark') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', b.dataset.t);
    try { localStorage.setItem('gr-theme', b.dataset.t); } catch (err) {}
    paint(); });
  paint();
})();

// ==== V8.1 · «Qué mide y cómo leerlo» en cada tarjeta (dentro de «Ver detalle») y glosario en Sistema ====
(function(){
  const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const EXPLAIN = [
    [/^Disponibilidad de hoy/, 'Puntuación oficial (0–100) de lo preparado que está tu cuerpo hoy: compara tu HRV, FC en reposo y nocturna, sueño, carga reciente y estrés con tu propia normalidad. La zona y los límites (RPE máximo y volumen) salen del más prudente de los tres modelos, así que un solo indicador malo puede bajarla aunque los demás estén bien.'],
    [/^Señales a favor y en contra/, 'Aparece cuando los modelos no coinciden (por ejemplo, la recuperación oficial alta y el Training Readiness de Garmin bajo). Muestra qué señales de hoy son favorables y cuáles restrictivas, con sus cifras. No cambia la decisión: sirve para afinar la sesión, sobre todo cuanto más larga sea la columna «En contra».'],
    [/^Cambios recientes/, 'Cada tarjeta compara el valor de hoy con el de ayer. La flecha va en verde si el cambio es bueno para la recuperación (HRV que sube, FC que baja…) y en rojo si es malo. La curva enseña los últimos 7 días para ver si es algo puntual o una tendencia.'],
    [/^Resumen de hoy · Claude/, 'Texto redactado por Claude con las cifras del último ciclo certificado. No añade datos nuevos: interpreta los que ves en la app. Si el ciclo cambia, se marca como desactualizado.'],
    [/^Hoy en breve|^En tres líneas/, 'Resumen automático por reglas a partir de la decisión del día; aparece cuando no hay resumen de Claude del ciclo vigente.'],
    [/^Por qué esta puntuación/, 'Los factores que más han movido la puntuación de hoy, del que más pesa al que menos. ↓ empeora la recuperación, ↑ la mejora y → es neutro.'],
    [/^Respiración nocturna/, 'Respiraciones por minuto mientras duermes, medidas por el reloj. Cambia muy poco de una noche a otra: una subida de 2 o más sobre tu normal suele anticipar fatiga, estrés, alcohol o un resfriado, sobre todo si a la vez baja la HRV. Es informativa: no cambia la puntuación.'],
    [/^Esta noche/, 'Horas de sueño que conviene dormir esta noche: tu base (7,5 h) más un recargo por la carga de ayer y por la deuda de las últimas noches, menos las siestas que registró Garmin. Es una estimación orientativa.'],
    [/^Próximos 7 días/, 'Plan por reglas según tus turnos y la decisión de hoy: como mucho 3 sesiones duras (RPE ≥ 8) a la semana, separadas 48 h y solo en días libres, y descanso después de un turno de noche. Se recalcula en cada informe.'],
    [/^Peso/, 'Lecturas de la báscula Xiaomi que muestras o dictas. El peso varía 1–2 kg en el mismo día por comida, líquidos y entreno: compara solo lecturas hechas a la misma hora, mejor por la mañana en ayunas.'],
    [/^Últimas 4 semanas/, 'Calendario de 28 días. El color es la decisión de cada día y el número, el RPE de la sesión más dura. Un anillo rojo marca que entrenaste por encima del máximo recomendado ese día. Toca un día para ver su detalle.'],
    [/^Disponibilidad · 28 días/, 'Puntuación oficial de cada día. Las bandas de color son las zonas, las franjas tenues los turnos de noche y los triángulos los días con una sesión de RPE 8 o más. Sirve para ver cómo responde tu cuerpo a los bloques duros y a los turnos.'],
    [/^Carga semanal/, 'Carga de los últimos 7 días frente a la habitual de las últimas 4 semanas (ACWR). Dentro de la banda verde la progresión es razonable. Muy por encima, la carga ha subido de golpe; muy por debajo, estás descargando.'],
    [/^Mapa de 28 días/, 'Cada columna es un día y cada fila un componente: recuperación, sueño y carga. Verde es bueno, amarillo regular, rojo malo y gris sin dato. Ayuda a ver qué falla más a menudo.'],
    [/^HRV nocturna/, 'Variabilidad de la frecuencia cardiaca durante el sueño (rMSSD, en ms). Una HRV más alta de lo normal suele indicar buena recuperación. Compárala siempre con tu propio rango (la banda) y fíjate en la media de 7 días: una noche suelta varía mucho por alcohol, cenas tarde o estrés.'],
    [/^FC en reposo/, 'Pulsaciones más bajas en reposo (lpm). Si sube 5 o más sobre tu mediana varios días seguidos suele indicar fatiga, mal sueño, estrés o el inicio de una enfermedad. La FC nocturna es la media durante el sueño.'],
    [/^Sueño por fases/, 'Profundo, REM y ligero estimados por Garmin a partir del movimiento y la FC. La duración total es fiable; el reparto entre fases es orientativo.'],
    [/^Sueño/, 'Horas dormidas cada noche frente a tu necesidad configurada (7,5 h), contando el sueño de día tras un turno de noche. La deuda es lo que falta acumulado de las últimas noches.'],
    [/^Carga diaria/, 'Carga cardiaca de cada día según Intervals.icu (TRIMP). ATL es la fatiga de los últimos 7 días y CTL la forma de las últimas 6 semanas; su diferencia (TSB, forma) indica si vienes cargado (negativo) o fresco (positivo).'],
    [/^RPE frente al máximo/, 'La barra es el RPE de tu sesión más dura de cada día y la raya, el máximo que permitía la decisión de ese día. Una barra roja indica que entrenaste por encima de lo recomendado.'],
    [/^Esta semana/, 'Totales de los últimos 7 días frente a los 7 anteriores. sRPE es la carga interna: RPE × minutos de cada sesión, sumado.'],
    [/^Equilibrio de carga/, 'Garmin reparte tu carga de 4 semanas según la intensidad cardiaca: aeróbica baja (base, zonas 1–2), aeróbica alta (tempo y umbral) y anaeróbica (esfuerzos máximos cortos). La banda verde es el rango que recomienda para tu nivel. En CrossFit es normal tener mucha anaeróbica; si pasa del techo, conviene meter sesiones suaves y largas.'],
    [/^VO2max/, 'Consumo máximo de oxígeno estimado por Garmin (ml/kg/min): mide tu capacidad aeróbica. Garmin lo calcula sobre todo en carreras y bici con GPS; en HIIT y fuerza apenas lo actualiza, por eso puede salir plano aunque mejores.'],
    [/^Últimos 7 días/, 'Número de sesiones de cada tipo en la última semana y el RPE medio de los metcons.'],
    [/^Volumen de/, 'Kilos levantados con barra cada semana (repeticiones × carga). Solo cuenta la barra con carga total; las mancuernas y las máquinas no se suman porque no son comparables.'],
    [/^Progresión por ejercicio/, 'La mejor serie de cada ejercicio que repites, comparada con la sesión anterior: ▲ sube la carga o las repeticiones, = igual y ▼ baja. Solo compara series con las mismas repeticiones.'],
    [/^Sesiones de (fuerza|halterofilia)/, 'Cada sesión con sus series («10 @ 60» = 10 repeticiones con 60 kg) y la mejor serie a la derecha. Debajo, la FC de la sesión y el efecto de entrenamiento de Garmin.'],
    [/^Metcons/, 'Cada WOD con su formato, resultado y tiempos. El cronómetro oficial y el tiempo grabado por el reloj se guardan por separado. Solo se pueden comparar WOD que repiten formato y ejercicios.'],
    [/^Técnica y otras/, 'Calentamientos, técnica y sesiones sin ejercicios estructurados. No llevan RPE ni cuentan como RPE pendiente, pero sí suman a la carga cardiaca.'],
    [/^Sesiones de los últimos 28 días/, 'Todas las sesiones con su duración, carga cardiaca, FC media, RPE y sRPE (RPE × minutos). Toca una fila con ♥ para ver la curva de FC y las zonas.'],
    [/^Ciclo completo/, 'Estado de la última cadena de datos: Sync (Intervals), FC (Garmin), Analítica, CrossFit, publicación de la web y aviso al móvil.'],
    [/^Puntualidad/, 'Cada franja de Sync (08:30, 16:45 y 22:45) con la hora real del Sync y del informe. El margen es lo que sobró hasta la hora objetivo del informe.'],
    [/^Modelo experimental/, 'Modelo v3 en pruebas. Se calcula en paralelo y entra en la decisión solo si es más prudente que el oficial. Cada barra es un componente con su peso entre paréntesis.'],
  ];
  const EXTRA = [
    ['Efecto de entrenamiento', 'Escala de Garmin de 0 a 5 que indica cuánto mejora una sesión tu capacidad aeróbica y anaeróbica: 0–0,9 sin efecto · 1–1,9 leve · 2–2,9 mantiene · 3–3,9 mejora · 4–4,9 mejora mucho · 5 sobrecarga.'],
    ['RPE', 'Esfuerzo percibido de la sesión de 0 a 10, el que dictas tú. La técnica y los calentamientos no lo llevan.'],
    ['sRPE', 'Carga interna de Foster: RPE × minutos de la sesión. Refleja mejor que la FC la carga de la fuerza.'],
    ['Body Battery', 'Energía estimada por Garmin (0–100) a partir de la HRV, el estrés y el sueño. Solo es una medición nueva cuando el reloj ha sincronizado.'],
    ['Estrés medio', 'Índice de estrés de Garmin (0–100) calculado con la HRV durante el día. Por encima de tu media suele acompañar a peor recuperación.'],
    ['Forma (TSB)', 'CTL − ATL: forma menos fatiga. Negativa = vienes cargado; positiva = fresco. Solo se interpreta con al menos 6 semanas de historial.'],
  ];
  const find = t => (EXPLAIN.find(([re]) => re.test(t)) || [])[1];
  document.querySelectorAll('.card').forEach(card => {
    if (card.id === 'hrdetail' || card.id === 'apariencia' || card.id === 'glosario') return;
    const h = card.querySelector(':scope > h2, :scope h2');
    const title = (h ? h.textContent : card.getAttribute('aria-label') || '').trim();
    const txt = title && find(title);
    if (!txt) return;
    let d = card.querySelector(':scope > details.more');
    if (!d) { d = document.createElement('details'); d.className = 'more'; d.innerHTML = '<summary>Ver detalle</summary><div class="more-body"></div>'; card.appendChild(d); }
    const p = document.createElement('p'); p.className = 'explain'; p.innerHTML = '<b>Qué mide y cómo leerlo.</b> ' + esc(txt);
    d.querySelector('.more-body').prepend(p);
  });
  const host = document.getElementById('tab-sistema'); if (!host) return;
  const NAMES = ["Disponibilidad (puntuación de hoy)", "Señales a favor y en contra", "Cambios recientes", "Resumen de Claude", "Hoy en breve", "Por qué esta puntuación", "Respiración nocturna", "Esta noche (sueño necesario)", "Próximos 7 días", "Peso", "Últimas 4 semanas", "Disponibilidad · 28 días", "Carga semanal (ACWR)", "Mapa de 28 días", "HRV nocturna", "FC en reposo y nocturna", "Sueño por fases", "Sueño y deuda", "Carga diaria, ATL y CTL", "RPE frente al máximo del día", "Esta semana", "Equilibrio de carga · 4 semanas", "VO2max", "Últimos 7 días (Entrenos)", "Volumen de fuerza y halterofilia", "Progresión por ejercicio", "Sesiones de fuerza y halterofilia", "Metcons", "Técnica y otras", "Sesiones de los últimos 28 días", "Ciclo completo", "Puntualidad", "Modelo experimental"];
  const names = EXPLAIN.map(([, t], i) => [NAMES[i] || '', t]);
  const sec = document.createElement('section'); sec.className = 'card'; sec.id = 'glosario';
  sec.innerHTML = '<h2>Qué significa cada dato</h2><details class="more"><summary>Ver glosario</summary><dl class="gloss">' +
    names.concat(EXTRA).map(([n, t]) => `<dt>${esc(n)}</dt><dd>${esc(t)}</dd>`).join('') + '</dl></details>';
  const ap = document.getElementById('apariencia');
  host.insertBefore(sec, ap ? ap.nextSibling : host.firstChild);
})();
