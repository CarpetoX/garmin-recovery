# Apps Script (copia de referencia)

Copia del proyecto **garmin-recovery** de Google Apps Script, que es el disparador principal del Sync. Lo que se ejecuta es el código del editor de Apps Script; esta carpeta sirve para tener historial de cambios y poder recuperarlo. No contiene secretos: `GITHUB_TOKEN` y `GARMIN_ORIGIN_KEY_V291` se leen de las Propiedades del script y **nunca** deben escribirse aquí.

| Archivo | Función | Activador |
|---|---|---|
| `RespaldoGarmin231.gs` | Envía el Sync firmado (HMAC) a la hora de cada franja (08:30, 16:45, 22:45) y reintenta si la cadena falla, hasta 3 veces y 150 min | `verificarRespaldoGarmin231`, cada 5 min |
| `GarminPostSueno.gs` | Repite el Sync por la mañana mientras el sueño no esté confirmado (08:50, 09:15… 12:15; tras turno de noche, 09:00–18:00) | `vigilarPostSuenoGarmin`, cada 5 min |
| `ActivadoresGarmin.gs` | Recrea activadores perdidos, elimina duplicados y borra memorias de franjas de más de 14 días | `repararActivadoresGarmin`, diario 07:00–08:00 |
| `Code.gs`, `Watchdogs.gs` | Solo diagnóstico; las funciones antiguas no hacen nada | ninguno |
| `appsscript.json` | Zona Europe/Madrid, V8, permisos `script.external_request` y `script.scriptapp` | — |

**Instalar o cambiar intervalos:** pegar los archivos en el editor y ejecutar una vez `instalarActivadoresGarmin()`.

**Historial**
- V2.9.4 (17/10/2026): el Sync sale a la hora de la franja (antes, entre 10 y 20 min tarde), con reintentos a los ~6 min, un sondeo post-sueño a las 08:50, autorreparación de activadores y limpieza de propiedades. Comprobado con un simulador de los servicios de Apps Script y de GitHub.
- V2.9.1–2.9.3 (11/10/2026): Sync firmado con HMAC, verificado por `garmin_dispatch_auth_v291.py`.

Nota: la copia recibida de `Code.gs` terminaba a mitad de `probarDisparoManual()`. Aquí se ha cerrado esa función (`return result; }`); el original en el editor está completo.
