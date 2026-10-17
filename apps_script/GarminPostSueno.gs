/**
 * Garmin Recovery - vigilancia post-sueño v2.9.4 (dispatch firmado V2.9.1).
 *
 * Cambios v2.9.4 (17-10-2026, puntualidad del informe de las 09:05):
 * - Nuevo sondeo a las 08:50 en días normales: si a las 08:30 el sueño aún no
 *   estaba confirmado, hay una segunda oportunidad ANTES de que se lea el informe.
 * - Activador cada 5 min (antes 15): cada sondeo se hace en su hora, no hasta
 *   14 min después.
 * - "Sync reciente" pasa de 25 a 15 min para que el sondeo de las 08:50 no quede
 *   bloqueado por el Sync de las 08:30.
 * - Repara los activadores del proyecto (ActivadoresGarmin.gs).
 *
 * SUSTITUIR el contenido del archivo .gs que YA define vigilarPostSuenoGarmin.
 * NO crear un segundo archivo que defina esa función.
 * NO reinstalar ni borrar activadores: el nombre de la función se conserva.
 * NO modificar RespaldoGarmin231.gs, Code.gs ni Watchdogs.gs.
 *
 * Ventanas originales v2.4.13:
 * - Días normales: 09:15, 10:00, 10:45, 11:30, 12:15.
 * - Tras turno TN: 09:00 a 18:00, cada hora.
 * - Respeta confirmación definitiva, margen de 30 min, ejecución reciente,
 *   ejecución en curso y protección contra repetir un mismo sondeo.
 *
 * Cambio v2.9.3: solicita Sync mediante workflow_dispatch con los cinco
 * campos firmados que ya verifica garmin_dispatch_auth_v291.py de GitHub.
 * El protocolo V2.9.1 denomina al remitente verificado 'apps_script_backup'
 * para TODOS los disparos de Apps Script firmados, incluidos post-sueño.
 * El subtipo 'post-sueño' se registra en el log local, no se atribuye en GitHub.
 * HTTP 204 significa solicitud aceptada, NO cadena terminada.
 * Ningún sondeo equivale a verificar el despertar directamente en Garmin.
 */
const POSTSUENO_GARMIN = Object.freeze({
  repo: 'CarpetoX/garmin-recovery',
  branch: 'main',
  workflow: 'sync.yml',
  zone: 'Europe/Madrid',
  triggerFunction: 'vigilarPostSuenoGarmin',
  regularSlots: ['08:50', '09:15', '10:00', '10:45', '11:30', '12:15'],
  postNightSlots: ['09:00', '10:00', '11:00', '12:00', '13:00',
                   '14:00', '15:00', '16:00', '17:00', '18:00'],
  recentSyncMinutes: 15,
  propsPrefix: 'GARMIN_POSTSUENO_V2413_', // Conserva los bloqueos históricos
  signingKeyProperty: 'GARMIN_ORIGIN_KEY_V291'
});

function _postSuenoGitHub_(path, options) {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('Falta GITHUB_TOKEN en Propiedades del script');
  const request = Object.assign({
    method: 'get',
    muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Garmin-PostSueno/2.9.4'
    }
  }, options || {});
  const url = 'https://api.github.com/repos/' + POSTSUENO_GARMIN.repo + path;
  const response = UrlFetchApp.fetch(url, request);
  const status = response.getResponseCode();
  if (status < 200 || status >= 300) {
    throw new Error('GitHub HTTP ' + status + ' consultando ' + path +
                    ': ' + response.getContentText().slice(0, 260));
  }
  return {status: status, body: response.getContentText()};
}

function _postSuenoJSON_(path) {
  const result = _postSuenoGitHub_('/contents/' + path + '?ref=' + POSTSUENO_GARMIN.branch);
  const file = JSON.parse(result.body);
  if (file.encoding !== 'base64' || !file.content) {
    throw new Error('GitHub no devolvió contenido válido para ' + path);
  }
  const bytes = Utilities.base64Decode(file.content.replace(/\s/g, ''));
  return JSON.parse(Utilities.newBlob(bytes).getDataAsString('UTF-8'));
}

function _postSuenoFecha_(when, pattern) {
  return Utilities.formatDate(when, POSTSUENO_GARMIN.zone, pattern);
}

function _postSuenoMinutos_(str) {
  const parts = String(str).split(':');
  return Number(parts[0]) * 60 + Number(parts[1]);
}

function _postSuenoElegirTurno_(now, nightShift) {
  const hours = _postSuenoMinutos_(_postSuenoFecha_(now, 'HH:mm'));
  const slots = nightShift ? POSTSUENO_GARMIN.postNightSlots : POSTSUENO_GARMIN.regularSlots;
  const due = slots.filter(t => _postSuenoMinutos_(t) <= hours);
  if (!due.length) return null;
  const last = due[due.length - 1];
  const maxLag = 29; // Mantener la ventana original, sin recuperar sondeos antiguos
  return hours - _postSuenoMinutos_(last) <= maxLag ? last : null;
}

function _postSuenoUltimoSync_() {
  const response = _postSuenoGitHub_(
    '/actions/workflows/sync.yml/runs?branch=main&per_page=5');
  const parsed = JSON.parse(response.body);
  if (!Array.isArray(parsed.workflow_runs)) {
    throw new Error('GitHub no facilitó workflow_runs');
  }
  return parsed.workflow_runs[0] || null;
}

/** El identificador firmado se refiere al horario oficial activo del día. */
function _postSuenoCycleId_(now) {
  const date = _postSuenoFecha_(now, 'yyyy-MM-dd');
  const localMinutes = _postSuenoMinutos_(_postSuenoFecha_(now, 'HH:mm'));
  const slot = localMinutes >= 22 * 60 + 45 ? '2245' :
               localMinutes >= 16 * 60 + 45 ? '1645' : '0830';
  return date + '-' + slot;
}

/** Solo construye el payload de autenticación, no hace peticiones a GitHub. */
function _postSuenoFirmaV291_(now) {
  const key = PropertiesService.getScriptProperties().getProperty(
    POSTSUENO_GARMIN.signingKeyProperty);
  if (typeof key !== 'string' || key.length < 32) {
    throw new Error('Falta GARMIN_ORIGIN_KEY_V291 (mínimo 32 caracteres) en Propiedades del script');
  }
  const requestAt = now.toISOString();
  const requestId = Utilities.getUuid();
  const originSource = 'apps_script_backup'; // Valor reconocido por el verificador V2.9.1
  const cycleId = _postSuenoCycleId_(now);
  const message = ['garmin-v291', originSource, cycleId, requestAt, requestId].join('\n');
  const digest = Utilities.computeHmacSha256Signature(
    message, key, Utilities.Charset.UTF_8);
  const signature = digest.map(function(b) {
    return ('0' + (b & 255).toString(16)).slice(-2);
  }).join('');
  return {
    ref: POSTSUENO_GARMIN.branch,
    inputs: {
      origin_source: originSource,
      cycle_id: cycleId,
      requested_at: requestAt,
      request_id: requestId,
      origin_proof: signature
    }
  };
}

function _postSuenoDecidir_(dryRun) {
  const now = new Date();
  const today = _postSuenoFecha_(now, 'yyyy-MM-dd');
  const localMinutes = _postSuenoMinutos_(_postSuenoFecha_(now, 'HH:mm'));
  if (localMinutes < 8 * 60 + 50 || localMinutes > 18 * 60 + 29) {
    return {state: 'fuera_de_sondeo', today: today};
  }

  const yesterday = _postSuenoFecha_(new Date(now.getTime() - 86400000), 'yyyy-MM-dd');
  const shifts = _postSuenoJSON_('shift_calendar.json');
  const postNight = Boolean(shifts && shifts.days && shifts.days[yesterday] === 'TN');
  const slot = _postSuenoElegirTurno_(now, postNight);
  if (!slot) return {state: 'fuera_de_sondeo', today: today, postNight: postNight};

  const props = PropertiesService.getScriptProperties();
  const key = POSTSUENO_GARMIN.propsPrefix + today + '_' + slot.replace(':', '');
  if (props.getProperty(key)) {
    return {state: 'turno_ya_comprobado', today: today, slot: slot, postNight: postNight};
  }

  const sleep = _postSuenoJSON_('morning_sleep_status.json');
  if (sleep.date === today && sleep.state === 'confirmed_ready' &&
      sleep.is_definitive === true && sleep.wake_confirmed === true) {
    return {state: 'sueno_ya_confirmado', today: today, slot: slot,
            sleep_end: sleep.sleep_end_local, postNight: postNight};
  }
  if (sleep.date === today && sleep.state === 'confirmed_wait_30m' &&
      sleep.earliest_definitive_at) {
    const due = new Date(sleep.earliest_definitive_at).getTime();
    if (Number.isFinite(due) && now.getTime() < due) {
      return {state: 'esperando_30_minutos', today: today, slot: slot,
              earliest: sleep.earliest_definitive_at, postNight: postNight};
    }
  }

  const latest = _postSuenoUltimoSync_();
  if (latest) {
    if (['queued', 'in_progress', 'waiting', 'requested', 'pending'].includes(latest.status)) {
      return {state: 'sync_en_ejecucion', today: today, slot: slot,
              run_id: latest.id, postNight: postNight};
    }
    const started = Date.parse(latest.created_at || '');
    const minutes = (now.getTime() - started) / 60000;
    if (Number.isFinite(minutes) && minutes >= 0 &&
        minutes < POSTSUENO_GARMIN.recentSyncMinutes) {
      return {state: 'sync_reciente', today: today, slot: slot,
              run_id: latest.id, age_minutes: Math.round(minutes), postNight: postNight};
    }
  }

  if (dryRun) {
    return {state: 'listo_para_solicitar_sync', today: today,
            slot: slot, postNight: postNight, no_dispatch: true,
            signed_workflow_dispatch: true, cycle_id: _postSuenoCycleId_(now)};
  }

  // Se evita repository_dispatch sin firma; V2.9.1 valida workflow_dispatch firmado.
  const signed = _postSuenoFirmaV291_(now);
  const response = _postSuenoGitHub_(
    '/actions/workflows/' + POSTSUENO_GARMIN.workflow + '/dispatches', {
      method: 'post', contentType: 'application/json',
      payload: JSON.stringify(signed)
    });
  if (response.status !== 204) {
    throw new Error('GitHub no aceptó workflow_dispatch firmado: HTTP ' + response.status);
  }

  // HTTP 204 no certifica Sync, FC, Advanced ni CrossFit.
  props.setProperty(key, new Date().toISOString());
  console.log('Post-sueño: solicitud firmada aceptada para ciclo ' + signed.inputs.cycle_id +
              ' sondeo=' + slot + ' (sin afirmar ejecución ni entrega)');
  return {state: 'sync_solicitado_no_certificado', today: today, slot: slot,
          postNight: postNight, event_type: 'workflow_dispatch',
          signed: true, cycle_id: signed.inputs.cycle_id};
}

/** Activador EXISTENTE: no crear otro. */
function vigilarPostSuenoGarmin() {
  try { garminAsegurarActivadores_(false); }
  catch (err) { console.warn('Revisión de activadores: ' + String(err && err.message || err).slice(0, 150)); }
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(7000)) return {state: 'otra_revision_en_curso'};
  try {
    const result = _postSuenoDecidir_(false);
    console.log(JSON.stringify(result));
    return result;
  } finally {
    lock.releaseLock();
  }
}

/** Diagnóstico de sueño sin disparar Sync ni cambiar activadores. */
function diagnosticarPostSuenoGarmin() {
  const result = _postSuenoDecidir_(true);
  console.log(JSON.stringify(result));
  return result;
}

/** Diagnóstico de la firma sin publicar el secreto ni lanzar Sync. */
function comprobarFirmaPostSuenoGarmin() {
  const now = new Date();
  const signed = _postSuenoFirmaV291_(now);
  const inputs = signed.inputs;
  const ok = (signed.ref === 'main' &&
              /^\d{4}-\d{2}-\d{2}-(0830|1645|2245)$/.test(inputs.cycle_id) &&
              /^[0-9a-fA-F-]{36}$/.test(inputs.request_id) &&
              /^[0-9a-f]{64}$/.test(inputs.origin_proof));
  if (!ok) throw new Error('Formato local de la firma no válido.');
  const result = {
    version: '2.9.4-post-sleep',
    signing_configured: true,
    local_signature_format_valid: true,
    cycle_id: inputs.cycle_id,
    workflow: POSTSUENO_GARMIN.workflow,
    dispatch_event: 'workflow_dispatch',
    no_dispatch: true,
    note: 'Comprueba firma local, no prueba correspondencia del secreto remoto ni ejecución GitHub.'
  };
  console.log(JSON.stringify(result));
  return result;
}

/** Compatibilidad: usar instalarActivadoresGarmin() (ActivadoresGarmin.gs). */
function instalarVigilanciaPostSuenoGarmin() {
  return instalarActivadoresGarmin();
}

/** Versión anterior del instalador (15 min), conservada solo como referencia. */
function instalarVigilanciaPostSuenoGarminV293_() {
  if (!PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN')) {
    throw new Error('Configura GITHUB_TOKEN previamente; no pegues el token en el código.');
  }
  const handler = POSTSUENO_GARMIN.triggerFunction;
  const matching = ScriptApp.getProjectTriggers().filter(
    item => item.getHandlerFunction() === handler);
  if (matching.length) {
    console.log('La vigilancia post-sueño ya tiene ' + matching.length +
                ' activador(es); no se crea otro.');
    return {status: 'ya_instalado', count: matching.length};
  }
  const existingMorning = ScriptApp.getProjectTriggers().map(
    item => item.getHandlerFunction()).filter(name =>
      name !== handler &&
      (/(garmin.*(morning|sueno|sleep|despertar))|((morning|sueno|sleep|despertar).*garmin)/i.test(name)));
  if (existingMorning.length) {
    throw new Error('Ya hay un vigilante matutino; revisar activadores antes de instalar: ' +
                    existingMorning.join(', '));
  }
  ScriptApp.newTrigger(handler).timeBased().everyMinutes(15).create();
  console.log('Vigilancia post-sueño instalada cada 15 minutos; solo actúa en ventanas programadas.');
  return {status: 'instalado', interval_minutes: 15};
}

/** Desinstala SOLO el activador post-sueño; no ejecutar durante esta actualización. */
function desinstalarVigilanciaPostSuenoGarmin() {
  const handler = POSTSUENO_GARMIN.triggerFunction;
  let removed = 0;
  ScriptApp.getProjectTriggers().forEach(item => {
    if (item.getHandlerFunction() === handler) {
      ScriptApp.deleteTrigger(item);
      removed += 1;
    }
  });
  console.log('Eliminados ' + removed + ' activadores post-sueño.');
  return {removed: removed};
}
