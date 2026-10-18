/**
 * Garmin Recovery - registro de RPE desde la web (v1).
 *
 * Recibe el RPE que escribes en el panel (tarjeta «Registrar RPE») y lo apunta en la hoja
 * «RPE CrossFit - Registro», pestaña RPE, como indica REGISTRO_ENTRENAMIENTOS.md.
 *
 * INSTALACIÓN (una vez, ~3 min):
 * 1. En la hoja: Extensiones > Apps Script. Crea un archivo nuevo «RegistroRPEWeb.gs» y pega esto.
 *    (Si prefieres un proyecto aparte, funciona igual: define SHEET_ID abajo o en Propiedades.)
 * 2. Configuración del proyecto > Propiedades del script: añade RPE_WEB_TOKEN con una clave larga
 *    inventada por ti (20+ caracteres). No la subas a GitHub: el repositorio es público.
 * 3. Implementar > Nueva implementación > Aplicación web.
 *    Ejecutar como: Yo.  Quién tiene acceso: Cualquier usuario.  Copia la URL que termina en /exec.
 * 4. En el panel, tarjeta «Registrar RPE» > Configurar: pega la URL y la clave. Se guardan solo en tu móvil.
 *
 * SEGURIDAD: sin la clave nadie puede escribir. Solo se acepta un RPE de 0 a 10 y un ID tipo i123456.
 * Nunca borra filas. Si el ID ya tiene RPE, rechaza el cambio salvo que la web envíe «overwrite».
 * Si cambias de clave, vuelve a pegarla en el panel.
 */
const RPE_WEB_TAB = 'RPE';
const RPE_WEB_DEFAULT_SHEET_ID = '1vbxls-yyBOs8_gAmp9ld2WI_Ss9jvXNMFbxV5TKWX_k';

function rpeWebJson_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function rpeWebSpreadsheet_() {
  const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID') || RPE_WEB_DEFAULT_SHEET_ID;
  return SpreadsheetApp.openById(id);
}

/** Comprobación desde el navegador: abre la URL /exec y debe responder {"ok":true,...}. */
function doGet() {
  return rpeWebJson_({ ok: true, service: 'registro-rpe-web', v: 1 });
}

/** Lógica pura (sin Apps Script) para poder probarla: devuelve {error} o {row:[...]}. */
function rpeWebValidate_(p, today) {
  const id = String(p.activity_id || '').trim();
  if (!/^i\d{3,12}$/.test(id)) return { error: 'ID de actividad no válido' };
  const rpe = Number(String(p.rpe).replace(',', '.'));
  if (!isFinite(rpe) || rpe < 0 || rpe > 10) return { error: 'El RPE debe estar entre 0 y 10' };
  if (Math.round(rpe * 2) !== rpe * 2) return { error: 'El RPE admite enteros o medios (8,5)' };
  const date = String(p.date || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return { error: 'Fecha no válida' };
  const clip = (s, n) => String(s || '').replace(/[\r\n]+/g, ' ').trim().slice(0, n);
  const text = (s) => { const t = clip(s, 400); return /^[=+\-@]/.test(t) ? "'" + t : t; }; // sin fórmulas
  return {
    row: [date, id, text(p.name || 'Actividad'), rpe, text(p.feelings), text(p.notes), today, ''],
  };
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  try {
    lock.waitLock(15000);
    const p = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    const secret = PropertiesService.getScriptProperties().getProperty('RPE_WEB_TOKEN');
    if (!secret || String(p.token || '') !== secret) return rpeWebJson_({ ok: false, error: 'Clave incorrecta' });
    const today = Utilities.formatDate(new Date(), 'Europe/Madrid', 'yyyy-MM-dd');
    const v = rpeWebValidate_(p, today);
    if (v.error) return rpeWebJson_({ ok: false, error: v.error });
    const sheet = rpeWebSpreadsheet_().getSheetByName(RPE_WEB_TAB);
    if (!sheet) return rpeWebJson_({ ok: false, error: 'No existe la pestaña ' + RPE_WEB_TAB });
    const last = sheet.getLastRow();
    const ids = last > 1 ? sheet.getRange(2, 2, last - 1, 1).getValues().map((r) => String(r[0]).trim()) : [];
    const at = ids.indexOf(v.row[1]);
    let rowNo;
    if (at >= 0) {
      rowNo = at + 2;
      const prev = String(sheet.getRange(rowNo, 4).getValue()).trim();
      if (prev !== '' && !p.overwrite) {
        return rpeWebJson_({ ok: false, exists: true, error: 'Esa actividad ya tiene RPE ' + prev + '.' });
      }
      // solo RPE, sensaciones y notas; nunca se toca el Detalle JSON ni se borran filas
      sheet.getRange(rowNo, 4, 1, 3).setValues([[v.row[3], v.row[4], v.row[5]]]);
      sheet.getRange(rowNo, 7).setValue(v.row[6]);
    } else {
      sheet.appendRow(v.row);
      rowNo = sheet.getLastRow();
      sheet.getRange(rowNo, 1).setNumberFormat('yyyy-mm-dd');  // la fecha se queda como AAAA-MM-DD
      sheet.getRange(rowNo, 7).setNumberFormat('yyyy-mm-dd');
    }
    const back = sheet.getRange(rowNo, 1, 1, 7).getDisplayValues()[0]; // releer lo escrito
    return rpeWebJson_({ ok: true, row: rowNo, saved: { date: back[0], id: back[1], rpe: back[3] } });
  } catch (err) {
    return rpeWebJson_({ ok: false, error: 'Error: ' + err });
  } finally {
    try { lock.releaseLock(); } catch (x) { /* sin bloqueo */ }
  }
}
