/**
 * Garmin Recovery V2.9.4 — ActivadoresGarmin.gs (NUEVO archivo, 17-10-2026).
 *
 * Objetivo: que el Sync salga a la hora de cada franja y que un activador
 * perdido o duplicado se repare solo.
 *
 * - instalarActivadoresGarmin(): EJECUTAR UNA VEZ a mano tras pegar los tres
 *   archivos. Recrea los activadores con el intervalo nuevo (5 min).
 * - garminAsegurarActivadores_(): la llaman los dos vigilantes; si falta uno de
 *   los activadores lo crea, y si hay duplicados deja solo uno.
 * - repararActivadoresGarmin(): activador diario (07:00–08:00). Repara
 *   activadores y borra memorias de franjas de más de 14 días para que las
 *   Propiedades del script no lleguen a su límite de 500 KB.
 *
 * No envía ningún Sync, no escribe en GitHub y no toca GITHUB_TOKEN ni
 * GARMIN_ORIGIN_KEY_V291. Sin permisos nuevos (ya existe script.scriptapp).
 */
const GARMIN_ACTIVADORES = Object.freeze({
  wanted: [
    { handler: 'verificarRespaldoGarmin231', everyMinutes: 5 },
    { handler: 'vigilarPostSuenoGarmin', everyMinutes: 5 },
    { handler: 'repararActivadoresGarmin', dailyAtHour: 7 }
  ],
  legacy: ['garminGithubWatchdog', 'comprobarRespaldoGarmin'],
  cleanupPrefixes: ['GARMIN231_BACKUP_', 'GARMIN_POSTSUENO_V2413_'],
  keepDays: 14,
  checkEveryMinutes: 30,
  zone: 'Europe/Madrid'
});

function garminCrearActivador_(w) {
  const builder = ScriptApp.newTrigger(w.handler).timeBased();
  if (w.everyMinutes) {
    builder.everyMinutes(w.everyMinutes).create();
  } else {
    builder.atHour(w.dailyAtHour).everyDays(1).inTimezone(GARMIN_ACTIVADORES.zone).create();
  }
}

/** Crea los que falten y elimina duplicados. Devuelve los cambios hechos. */
function garminAsegurarActivadores_(force) {
  const cache = CacheService.getScriptCache();
  if (!force && cache.get('GARMIN_ACTIVADORES_OK')) return [];
  const changes = [];
  const triggers = ScriptApp.getProjectTriggers();
  GARMIN_ACTIVADORES.wanted.forEach(w => {
    const mine = triggers.filter(t => t.getHandlerFunction() === w.handler);
    if (!mine.length) {
      garminCrearActivador_(w);
      changes.push('creado ' + w.handler);
    }
    mine.slice(1).forEach(t => {
      ScriptApp.deleteTrigger(t);
      changes.push('duplicado eliminado ' + w.handler);
    });
  });
  triggers.filter(t => GARMIN_ACTIVADORES.legacy.includes(t.getHandlerFunction())).forEach(t => {
    changes.push('antiguo eliminado ' + t.getHandlerFunction());
    ScriptApp.deleteTrigger(t);
  });
  cache.put('GARMIN_ACTIVADORES_OK', '1', GARMIN_ACTIVADORES.checkEveryMinutes * 60);
  if (changes.length) console.warn('Activadores reparados: ' + changes.join('; '));
  return changes;
}

/** Borra memorias de franjas antiguas (nunca toca tokens ni claves). */
function garminLimpiarPropiedades_() {
  const props = PropertiesService.getScriptProperties();
  const limit = new Date(Date.now() - GARMIN_ACTIVADORES.keepDays * 86400000);
  const limitKey = Utilities.formatDate(limit, GARMIN_ACTIVADORES.zone, 'yyyy-MM-dd');
  let removed = 0;
  props.getKeys().forEach(k => {
    const prefix = GARMIN_ACTIVADORES.cleanupPrefixes.find(p => k.indexOf(p) === 0);
    if (!prefix) return;
    const day = k.slice(prefix.length, prefix.length + 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(day) && day < limitKey) {
      props.deleteProperty(k);
      removed += 1;
    }
  });
  return removed;
}

/** Activador diario. */
function repararActivadoresGarmin() {
  const changes = garminAsegurarActivadores_(true);
  const removed = garminLimpiarPropiedades_();
  const out = { version: '2.9.4', changes: changes, old_properties_removed: removed,
                checked_at: new Date().toISOString() };
  console.log(JSON.stringify(out));
  return out;
}

/** EJECUTAR UNA VEZ tras pegar los archivos: recrea los activadores a 5 min. */
function instalarActivadoresGarmin() {
  const handlers = GARMIN_ACTIVADORES.wanted.map(w => w.handler).concat(GARMIN_ACTIVADORES.legacy);
  ScriptApp.getProjectTriggers().forEach(t => {
    if (handlers.includes(t.getHandlerFunction())) ScriptApp.deleteTrigger(t);
  });
  GARMIN_ACTIVADORES.wanted.forEach(garminCrearActivador_);
  CacheService.getScriptCache().remove('GARMIN_ACTIVADORES_OK');
  const removed = garminLimpiarPropiedades_();
  const out = {
    version: '2.9.4', installed: GARMIN_ACTIVADORES.wanted.map(w => w.handler),
    total_triggers: ScriptApp.getProjectTriggers().length, old_properties_removed: removed
  };
  console.log(JSON.stringify(out));
  return out;
}
