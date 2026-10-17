/**
 * Garmin Recovery V2.9.2 — Watchdogs.gs SOLO DIAGNÓSTICO (11-10-2026).
 *
 * Sustituye el watchdog obsoleto (08:30,14:30,18:30,23:00) por lectura
 * de los certificados actuales. El ÚNICO respaldo general activo permanece
 * en RespaldoGarmin231.gs: verificarRespaldoGarmin231.
 *
 * No crea/elimina activadores, no envía dispatch, no escribe en GitHub.
 * Las funciones públicas antiguas se mantienen como barreras seguras.
 */
const GARMIN_WATCHDOG_DIAGNOSTICS_V292 = Object.freeze({
  repo: 'CarpetoX/garmin-recovery',
  branch: 'main',
  timezone: 'Europe/Madrid',
  syncSlots: ['08:30', '16:45', '22:45'],
  activeBackupHandler: 'verificarRespaldoGarmin231',
  activeSleepHandler: 'vigilarPostSuenoGarmin'
});

function garminWatchdogRead_(path, allow404) {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('Falta GITHUB_TOKEN en Propiedades del script');
  const url = 'https://api.github.com/repos/' +
    GARMIN_WATCHDOG_DIAGNOSTICS_V292.repo + path;
  const response = UrlFetchApp.fetch(url, {
    method: 'get', muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Garmin-Recovery-Watchdog-Diagnostics/2.9.2'
    }
  });
  const status = response.getResponseCode();
  if (status === 404 && allow404 === true) return null;
  if (status !== 200) throw new Error('GitHub GET error HTTP ' + status);
  return JSON.parse(response.getContentText());
}

function garminWatchdogJson_(name) {
  const obj = garminWatchdogRead_(
    '/contents/' + encodeURIComponent(name) + '?ref=main', true);
  if (!obj) return null;
  if (obj.encoding !== 'base64' || !obj.content)
    throw new Error('Formato no válido del archivo ' + name);
  return JSON.parse(Utilities.newBlob(
    Utilities.base64Decode(obj.content.replace(/\s/g, ''))
  ).getDataAsString('UTF-8'));
}

/** Comprobación GET sin reintentos ni activadores. */
function comprobarConexionGithub() {
  const res = garminWatchdogRead_('/actions/workflows/sync.yml', false);
  const out = {
    acceso: 'correcto', version: '2.9.2-watchdog-diagnostics',
    checked_at: new Date().toISOString(),
    workflow: res.name, workflow_status: res.state,
    slots: GARMIN_WATCHDOG_DIAGNOSTICS_V292.syncSlots,
    no_dispatch: true
  };
  console.log(JSON.stringify(out));
  return out;
}

/** Diagnóstico de las fuentes publicadas; no interpreta el evento como actor. */
function diagnosticarWatchdogGarmin() {
  const ready = garminWatchdogJson_('report_ready.json');
  const lineage = garminWatchdogJson_('pipeline_lineage_v29.json');
  const origin = garminWatchdogJson_('origin_monitor_v292.json');
  const health = garminWatchdogJson_('workflow_health.json');
  const handlers = ScriptApp.getProjectTriggers().map(t => t.getHandlerFunction());
  const out = {
    version: '2.9.2-watchdog-diagnostics',
    checked_at: new Date().toISOString(),
    active_triggers: {
      backup: handlers.filter(n => n === 'verificarRespaldoGarmin231').length,
      post_sleep: handlers.filter(n => n === 'vigilarPostSuenoGarmin').length,
      legacy_watchdog: handlers.filter(n => n === 'garminGithubWatchdog').length,
      legacy_code: handlers.filter(n => n === 'comprobarRespaldoGarmin').length
    },
    sync_slots: GARMIN_WATCHDOG_DIAGNOSTICS_V292.syncSlots,
    certificate: ready ? {
      cycle_id: ready.cycle_id, status: ready.status,
      verified_at: ready.verified_at
    } : null,
    chain: lineage ? {
      complete_chain_verified: lineage.complete_chain_verified === true,
      root_run_id: lineage.root && lineage.root.run_id,
      origin_certainty: lineage.root && lineage.root.origin_certainty
    } : null,
    origin: origin ? {
      cycle_id: origin.cycle_id,
      source: origin.origin && origin.origin.source,
      verified: Boolean(origin.origin && origin.origin.verified)
    } : null,
    monitor: health ? {
      checked_at: health.checked_at, status: health.status
    } : null,
    no_dispatch: true
  };
  console.log(JSON.stringify(out));
  return out;
}

/** Si se reactiva por error el antiguo trigger, se detiene sin hacer nada. */
function garminGithubWatchdog() {
  const out = {state: 'legacy_watchdog_disabled',
    replacement: 'verificarRespaldoGarmin231', no_dispatch: true};
  console.warn(JSON.stringify(out));
  return out;
}

/** La instalación de un tercer activador está prohibida por diseño. */
function crearTriggerRespaldoGarmin() {
  const out = {state: 'not_installed', reason: 'Active backup already exists',
    no_trigger_changes: true};
  console.warn(JSON.stringify(out));
  return out;
}

/** Función histórica que antes disparaba Sync; ahora es NO-OP deliberado. */
function probarDispatchGithub() {
  const out = {state: 'legacy_manual_dispatch_disabled', no_dispatch: true,
    reason: 'Evitar ejecuciones duplicadas ajenas a V2.9.1'};
  console.warn(JSON.stringify(out));
  return out;
}
