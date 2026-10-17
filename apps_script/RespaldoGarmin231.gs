/**
 * Garmin Recovery V2.9.4 — reemplaza COMPLETAMENTE RespaldoGarmin231.gs (17-10-2026).
 * NO elimines Code.gs. Conserva los nombres públicos existentes del activador.
 * Cambios V2.9.4 (puntualidad):
 *  - Apps Script es el disparador principal: actúa desde la hora exacta de la
 *    franja (antes esperaba 10 min a un cron de GitHub que llega 2–5 h tarde).
 *  - Activador cada 5 min (antes 10) y reintentos a los ~6 min (antes 12–15).
 *  - Si la franja ya está certificada no vuelve a consultar GitHub.
 *  - Repara sus activadores (ActivadoresGarmin.gs) y consulta 20 ejecuciones, no 70.
 * Detecta éxito, ejecución pendiente y fallo.
 * A diferencia de V2.3.1, un HTTP 204 no se interpreta como sincronización exitosa.
 * Reintenta fallos confirmados con enfriamiento y límite, sin repetir éxitos.
 */
const GARMIN231_CONFIG = Object.freeze({
  zone: 'Europe/Madrid', repo: 'CarpetoX/garmin-recovery',
  branch: 'main', workflow: 'sync.yml',
  slots: [
    { id: '0830', minutes: 510, label: '08:30' },
    { id: '1645', minutes: 1005, label: '16:45' },
    { id: '2245', minutes: 1365, label: '22:45' }
  ],
  startDelayMinutes: 0,
  maxDelayMinutes: 150,
  priorRunToleranceMinutes: 2,
  maxAttempts: 3,
  retryCooldownMinutes: 6,
  visibilityGraceMinutes: 4,
  downstreamGraceMinutes: 6,
  chain: ['sync.yml', 'garmin-heart-rate.yml', 'advanced-analytics-rpe.yml', 'crossfit-insights.yml'],
  runsPerPage: 20,
  propertyPrefix: 'GARMIN231_BACKUP_'
});

/** Compatibilidad: la instalación de activadores está ahora en ActivadoresGarmin.gs. */
function instalarRespaldoGarmin231() {
  return instalarActivadoresGarmin();
}


function comprobarConexionRespaldoGarmin231() {
  const runs = garmin231ObtenerEjecuciones_();
  const downstream = GARMIN231_CONFIG.chain.slice(1).map(name => ({
    workflow: name, runs: garmin231ObtenerEjecucionesWorkflow_(name).length
  }));
  const certificate = garmin231ObtenerCertificado_();
  const out = {
    acceso: 'correcto', version: '2.9.4', comprobado: new Date().toISOString(),
    ejecuciones: runs.length,
    ultimo_estado: runs[0] ? runs[0].status : 'sin_datos',
    ultimo_evento: runs[0] ? runs[0].event : 'sin_datos',
    fases_accesibles: downstream,
    ultimo_certificado: certificate && certificate.status === 'ready' ? certificate.cycle_id : null
  };
  console.log(JSON.stringify(out));
  return out;
}


/** Función que ejecuta el activador. No lanzar manualmente para forzar el Sync. */
function verificarRespaldoGarmin231() {
  try { garminAsegurarActivadores_(false); }
  catch (err) { console.warn('Revisión de activadores: ' + String(err && err.message || err).slice(0, 150)); }
  const now = new Date();
  const stamp = Utilities.formatDate(now, GARMIN231_CONFIG.zone, 'yyyy-MM-dd');
  // Se admite la ventana nocturna que cruza medianoche y el cambio de hora.
  let chosen = null;
  [stamp, garmin231FechaLocalAnterior_(now)].forEach(dateKey => {
    GARMIN231_CONFIG.slots.forEach(slot => {
      const start = Utilities.parseDate(dateKey + ' ' + slot.label,
        GARMIN231_CONFIG.zone, 'yyyy-MM-dd HH:mm');
      const delay = (now.getTime() - start.getTime()) / 60000;
      if (delay >= GARMIN231_CONFIG.startDelayMinutes && delay <= GARMIN231_CONFIG.maxDelayMinutes &&
          (!chosen || start.getTime() > chosen.slotStart.getTime())) {
        chosen = { slot: slot, dateKey: dateKey, slotStart: start };
      }
    });
  });
  if (!chosen) return;  // Fuera de ventanas: sin acceso API.
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(4000)) return;
  try {
    const props = PropertiesService.getScriptProperties();
    const key = GARMIN231_CONFIG.propertyPrefix + chosen.dateKey + '_' + chosen.slot.id;
    let memory;
    try { memory = JSON.parse(props.getProperty(key) || '{}'); }
    catch (err) { memory = {}; }
    const cycleId = chosen.dateKey + '-' + chosen.slot.id;
    // Franja ya certificada en una ejecución anterior: no hace falta consultar GitHub.
    if (memory.state === 'report_ready') return;
    // El certificado confirma TODAS las fases. Success de Sync por sí solo NO basta.
    const certificate = garmin231ObtenerCertificado_();
    if (garmin231CertificadoCoincide_(certificate, cycleId)) {
      props.setProperty(key, JSON.stringify(Object.assign({}, memory, {
        state: 'report_ready', completedRunId: certificate.chain.sync.id,
        verifiedAt: now.toISOString()
      })));
      console.log(cycleId + ': certificado final listo; respaldo no necesario.');
      return;
    }
    const workflows = GARMIN231_CONFIG.chain.map(name => garmin231ObtenerEjecucionesWorkflow_(name));
    const sinceMs = chosen.slotStart.getTime() - GARMIN231_CONFIG.priorRunToleranceMinutes * 60000;
    const runsByStage = workflows.map(list => list.filter(run => {
      const ms = Date.parse(run.created_at || '');
      return Number.isFinite(ms) && ms >= sinceMs && ms <= now.getTime() + 60000;
    }));
    const decision = garmin231EvaluarCadena_(runsByStage, memory, now.getTime(),
      chosen.slotStart.getTime(), GARMIN231_CONFIG);
    const label = chosen.dateKey + ' ' + chosen.slot.label;
    if (decision.kind === 'wait') {
      console.log(label + ': esperando (' + decision.reason + ').');
      return;
    }
    if (decision.kind === 'exhausted') {
      props.setProperty(key, JSON.stringify(Object.assign({}, memory, {
        state: 'exhausted', reason: decision.reason, checkedAt: now.toISOString()
      })));
      console.error(label + ': no existe certificado final y el respaldo agotó los intentos o ventana; revisar fases GitHub.');
      return;
    }
    if (decision.kind === 'dispatch') {
      garmin231DispararSync_(cycleId); // Solo si GitHub acepta con HTTP 204 se registra intento.
      const attempts = (Number(memory.attempts) || 0) + 1;
      props.setProperty(key, JSON.stringify({
        state: 'dispatch_requested', attempts: attempts,
        lastDispatchAt: now.toISOString(), reason: decision.reason,
        slot: chosen.dateKey + 'T' + chosen.slot.label
      }));
      console.warn(label + ': dispatch GitHub solicitado (intento ' + attempts +
        '/' + GARMIN231_CONFIG.maxAttempts + '; motivo: ' + decision.reason + ').');
    }
  } catch (error) {
    console.error('Garmin respaldo: ' + String(error && error.message || error).slice(0, 190));
    throw error;
  } finally {
    lock.releaseLock();
  }
}


/**
 * Función PURA. Sin certificado vigente, la cadena NO está confirmada.
 * Restaura el origen (Sync) solo cuando no hay fases activas ni en el período
 * de cortesía para que una fase posterior se publique. Máx. tres dispatch.
 * El origen de workflow_dispatch no se puede certificar por la API REST.
 */
function garmin231EvaluarCadena_(stages, memory, nowMs, slotMs, cfg) {
  const lists = Array.isArray(stages) ? stages : [];
  const attempted = Number(memory.attempts) || 0;
  const lastDispatch = Date.parse(memory.lastDispatchAt || '');
  const elapsed = Number.isFinite(lastDispatch) ? (nowMs - lastDispatch) / 60000 : Infinity;
  if (elapsed < cfg.visibilityGraceMinutes) return { kind: 'wait', reason: 'dispatch_visibility_grace' };
  if (elapsed < cfg.retryCooldownMinutes) return { kind: 'wait', reason: 'retry_cooldown' };
  // Cualquier fase ejecutándose indica que todavía puede publicarse el certificado.
  const active = lists.some(list => (list || []).some(r =>
    ['queued', 'in_progress', 'requested', 'waiting', 'pending'].includes(r.status)));
  if (active) return { kind: 'wait', reason: 'pipeline_still_running' };
  const newestRun = [];
  for (let i = 0; i < cfg.chain.length; i++) {
    const entries = (lists[i] || []).slice().sort((a,b) => Date.parse(b.created_at) - Date.parse(a.created_at));
    newestRun.push(entries.length ? entries[0] : null);
  }
  // Nunca despachar mientras GitHub aún podría estar iniciando la siguiente fase
  // o publicar report_ready.json tras su commit.
  const lastStage = newestRun.filter(Boolean).reduce((a,b) =>
    (!a || Date.parse(b.updated_at || b.created_at) > Date.parse(a.updated_at || a.created_at)) ? b : a, null);
  const lastSeen = lastStage ? Date.parse(lastStage.updated_at || lastStage.created_at) : NaN;
  if (Number.isFinite(lastSeen) && (nowMs - lastSeen) / 60000 < cfg.downstreamGraceMinutes)
    return { kind: 'wait', reason: 'downstream_or_certificate_grace' };
  if (attempted >= cfg.maxAttempts) return { kind: 'exhausted', reason: 'max_attempts_without_certificate' };
  if ((nowMs - slotMs) / 60000 > cfg.maxDelayMinutes) return { kind: 'exhausted', reason: 'window_expired' };
  if (!newestRun[0]) return { kind: 'dispatch', reason: 'scheduled_sync_missing' };
  if (newestRun[0].conclusion !== 'success') return { kind: 'dispatch', reason: 'root_sync_unsuccessful' };
  if (newestRun.some((run,i) => i > 0 && run &&
      ['failure','timed_out','cancelled','action_required','startup_failure'].includes(run.conclusion)))
    return { kind: 'dispatch', reason: 'downstream_failed_no_certificate' };
  if (newestRun.some((run,i) => i > 0 && !run))
    return { kind: 'dispatch', reason: 'downstream_missing_no_certificate' };
  return { kind: 'dispatch', reason: 'pipeline_completed_but_certificate_missing' };
}


/** Leer report_ready.json directamente de GitHub; 404 = aún no publicado. */
function garmin231ObtenerCertificado_() {
  const c = GARMIN231_CONFIG;
  const url = 'https://api.github.com/repos/' + c.repo +
    '/contents/report_ready.json?ref=' + encodeURIComponent(c.branch);
  const response = UrlFetchApp.fetch(url, {
    method: 'get', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + garmin231Token_(),
      Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }
  });
  const http = response.getResponseCode();
  if (http === 404) return null;
  if (http !== 200) throw new Error('Certificado GitHub: HTTP ' + http);
  const obj = JSON.parse(response.getContentText());
  if (obj.encoding !== 'base64' || !obj.content) throw new Error('Formato inesperado del certificado.');
  const raw = Utilities.newBlob(Utilities.base64Decode(obj.content.replace(/\s+/g, '')))
    .getDataAsString('UTF-8');
  return JSON.parse(raw);
}


function garmin231CertificadoCoincide_(obj, cycleId) {
  return Boolean(obj && obj.status === 'ready' && obj.cycle_id === cycleId &&
    obj.chain && ['sync','heart','advanced','crossfit'].every(k =>
      obj.chain[k] && Number(obj.chain[k].id) > 0));
}


function garmin231FechaLocalAnterior_(now) {
  const y = new Date(now.getTime() - 86400000);
  return Utilities.formatDate(y, GARMIN231_CONFIG.zone, 'yyyy-MM-dd');
}


function garmin231Token_() {
  const props = PropertiesService.getScriptProperties();
  const token = ['GITHUB_TOKEN', 'GH_TOKEN', 'GH_PAT', 'GITHUB_PAT']
    .map(k => props.getProperty(k)).find(Boolean);
  if (!token) throw new Error('Falta GITHUB_TOKEN en Propiedades de secuencia de comandos.');
  return token;
}


function garmin231ObtenerEjecuciones_() {
  return garmin231ObtenerEjecucionesWorkflow_(GARMIN231_CONFIG.workflow);
}


function garmin231ObtenerEjecucionesWorkflow_(workflow) {
  const c = GARMIN231_CONFIG;
  const url = 'https://api.github.com/repos/' + c.repo +
    '/actions/workflows/' + encodeURIComponent(workflow) + '/runs?per_page=' + c.runsPerPage;
  const response = UrlFetchApp.fetch(url, {
    method: 'get', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + garmin231Token_(),
      Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' }
  });
  if (response.getResponseCode() !== 200)
    throw new Error('Consulta GitHub HTTP ' + response.getResponseCode() + '.');
  const json = JSON.parse(response.getContentText());
  if (!Array.isArray(json.workflow_runs)) throw new Error('GitHub sin workflow_runs.');
  return json.workflow_runs;
}



/** V2.9.1 - Apps Script autenticado usando el API de workflow_dispatch existente.
 * GITHUB_TOKEN y GARMIN_ORIGIN_KEY_V291 se leen de Propiedades del script.
 * El nombre del trigger verificarRespaldoGarmin231 NO cambia.
 */
function garmin231DispararSync_(cycleId) {
  const c = GARMIN231_CONFIG;
  if (!/^\d{4}-\d{2}-\d{2}-(0830|1645|2245)$/.test(String(cycleId || ''))) {
    throw new Error('Ciclo Garmin invalido: no se envia dispatch.');
  }
  const key = PropertiesService.getScriptProperties().getProperty('GARMIN_ORIGIN_KEY_V291');
  if (!key || key.length < 32) {
    throw new Error('Configura GARMIN_ORIGIN_KEY_V291 (al menos 32 caracteres) en Propiedades del script.');
  }
  const requestAt = new Date().toISOString();
  const requestId = Utilities.getUuid();
  const originSource = 'apps_script_backup';
  const message = ['garmin-v291', originSource, cycleId, requestAt, requestId].join('\n');
  const digest = Utilities.computeHmacSha256Signature(message, key, Utilities.Charset.UTF_8);
  const signature = digest.map(function(b) {
    return ('0' + (b & 255).toString(16)).slice(-2);
  }).join('');
  const url = 'https://api.github.com/repos/' + c.repo +
    '/actions/workflows/' + encodeURIComponent(c.workflow) + '/dispatches';
  const response = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      ref: c.branch,
      inputs: {
        origin_source: originSource,
        cycle_id: cycleId,
        requested_at: requestAt,
        request_id: requestId,
        origin_proof: signature
      }
    }),
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + garmin231Token_(),
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28'
    }
  });
  if (response.getResponseCode() !== 204) {
    throw new Error('GitHub rechazo dispatch firmado: HTTP ' + response.getResponseCode() +
      ': ' + response.getContentText().slice(0, 200));
  }
  // La aceptación 204 no implica que la cadena haya terminado correctamente.
  console.log('V2.9.1: solicitud de respaldo firmada aceptada para ciclo ' + cycleId +
    ' request_id=' + requestId);
}
