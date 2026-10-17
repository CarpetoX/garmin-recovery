/**
 * Garmin Recovery V2.9.2 — Code.gs de compatibilidad y diagnóstico (11-10-2026).
 *
 * La copia de seguridad ACTIVA está en RespaldoGarmin231.gs y su handler es
 * verificarRespaldoGarmin231. La vigilancia matutina es vigilarPostSuenoGarmin.
 * Este archivo NO registra activadores, NO envía workflow_dispatch, NO envía
 * repository_dispatch y NO escribe en GitHub.
 *
 * Mantiene funciones públicas históricas para consultas y llamadas accidentales
 * sin permitir que reintroduzcan un segundo respaldo.
 * NO modificar las propiedades GITHUB_TOKEN y GARMIN_ORIGIN_KEY_V291.
 */
const GARMIN_CODE_DIAGNOSTICS_V292 = Object.freeze({
  repository: 'CarpetoX/garmin-recovery',
  branch: 'main',
  timezone: 'Europe/Madrid',
  syncSlots: ['08:30', '16:45', '22:45'],
  reportTargets: ['09:05', '17:10', '23:10'],
  activeBackupHandler: 'verificarRespaldoGarmin231',
  activeSleepHandler: 'vigilarPostSuenoGarmin'
});

/** REST GET exclusivamente; sin registrar tokens ni otros secretos. */
function garminCodeGet_(path, allow404) {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) throw new Error('Falta GITHUB_TOKEN en Propiedades del script');
  const url = 'https://api.github.com/repos/' +
    GARMIN_CODE_DIAGNOSTICS_V292.repository + path;
  const response = UrlFetchApp.fetch(url, {
    method: 'get', muteHttpExceptions: true,
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
      'User-Agent': 'Garmin-Recovery-Code-Diagnostics/2.9.2'
    }
  });
  const status = response.getResponseCode();
  if (status === 404 && allow404 === true) return null;
  if (status !== 200) throw new Error('GitHub GET error HTTP ' + status);
  return JSON.parse(response.getContentText());
}

function garminCodeJson_(file) {
  const result = garminCodeGet_('/contents/' + encodeURIComponent(file) +
    '?ref=' + encodeURIComponent(GARMIN_CODE_DIAGNOSTICS_V292.branch), true);
  if (!result) return null;
  if (result.encoding !== 'base64' || !result.content)
    throw new Error('Contenido JSON inesperado: ' + file);
  const decoded = Utilities.newBlob(
    Utilities.base64Decode(result.content.replace(/\s/g, ''))
  ).getDataAsString('UTF-8');
  return JSON.parse(decoded);
}

/** Diagnóstico de SOLO LECTURA. No modifica activadores ni provoca Sync. */
function comprobarConexionGarmin() {
  const cfg = GARMIN_CODE_DIAGNOSTICS_V292;
  const workflow = garminCodeGet_('/actions/workflows/sync.yml', false);
  const history = garminCodeGet_('/actions/workflows/sync.yml/runs?branch=main&per_page=5', false);
  const runs = Array.isArray(history.workflow_runs) ? history.workflow_runs : [];
  const handlers = ScriptApp.getProjectTriggers().map(function(t) {
    return t.getHandlerFunction();
  });
  const result = {
    acceso: 'correcto', version: '2.9.2-code-diagnostics',
    comprobado: new Date().toISOString(),
    workflow: workflow.name, workflow_status: workflow.state,
    timezone: cfg.timezone, sync_slots: cfg.syncSlots,
    report_targets: cfg.reportTargets,
    active_handlers: {
      backup: handlers.filter(n => n === cfg.activeBackupHandler).length,
      post_sleep: handlers.filter(n => n === cfg.activeSleepHandler).length
    },
    legacy_handlers_found: handlers.filter(n =>
      n === 'comprobarRespaldoGarmin' || n === 'garminGithubWatchdog'),
    last_sync: runs.length ? {
      id: runs[0].id, event: runs[0].event,
      status: runs[0].status, conclusion: runs[0].conclusion,
      created_at: runs[0].created_at
    } : null,
    note: 'workflow_dispatch por si solo no prueba quién lo inició'
  };
  console.log(JSON.stringify(result));
  return result;
}

/** Estado publicado por la canalización; NO intenta recuperarla. */
function diagnosticarRespaldoGarmin() {
  const ready = garminCodeJson_('report_ready.json');
  const origin = garminCodeJson_('origin_monitor_v292.json');
  const health = garminCodeJson_('workflow_health.json');
  const result = {
    version: '2.9.2-code-diagnostics',
    checked_at: new Date().toISOString(),
    sync_slots: GARMIN_CODE_DIAGNOSTICS_V292.syncSlots,
    certificate: ready ? {
      cycle_id: ready.cycle_id, status: ready.status,
      verified_at: ready.verified_at
    } : null,
    origin: origin ? {
      cycle_id: origin.cycle_id, source: origin.origin && origin.origin.source,
      verified: Boolean(origin.origin && origin.origin.verified),
      checked_at: origin.checked_at
    } : null,
    monitor: health ? {
      checked_at: health.checked_at, status: health.status
    } : null,
    no_dispatch: true
  };
  console.log(JSON.stringify(result));
  return result;
}

/** Compatibilidad: el antiguo disparador se transforma en NO-OP seguro. */
function comprobarRespaldoGarmin() {
  const result = {state: 'legacy_backup_disabled',
    replacement: 'verificarRespaldoGarmin231', no_dispatch: true};
  console.warn(JSON.stringify(result));
  return result;
}

/** Compatibilidad: impedir que una función antigua cree otro activador. */
function instalarRespaldoGarmin() {
  const result = {state: 'not_installed',
    reason: 'Use el activador ya existente verificarRespaldoGarmin231',
    no_trigger_changes: true};
  console.warn(JSON.stringify(result));
  return result;
}

/** Compatibilidad: NO lanza GitHub Sync; evita ejecuciones accidentales. */
function probarDisparoManual() {
  const result = {state: 'manual_dispatch_disabled_in_legacy_Code_gs',
    no_dispatch: true, use: 'GitHub Actions para ejecuciones manuales explícitas'};
  console.warn(JSON.stringify(result));
  return result;
}
