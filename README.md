# Garmin Recovery — plataforma de recuperación y CrossFit

Registro Garmin/Intervals + RPE de Google Sheets y resúmenes reproducibles. Zona horaria operativa: **Europe/Madrid**. Arquitectura conservadora: **seis workflows permanentes**; no añadir automatizaciones permanentes por cada actualización.

## Arquitectura y ejecución

| Orden | Workflow | Función |
|---|---|---|
| 1 | `sync.yml` | Actividades Intervals y resumen diario/semanal |
| 2 | `garmin-heart-rate.yml` | FC, HRV y sueño Garmin |
| 3 | `advanced-analytics-rpe.yml` | RPE, recuperación y calidad de datos |
| 4 | `crossfit-insights.yml` | Fuerza, WOD, informes y certificados de datos preparados |
| Independiente | `monitor-monthly.yml` | Control de salud y vigilancia de sincronizaciones |
| Independiente | `garmin-ci.yml` | Pruebas, sin sincronizar datos personales |

**Sync:** 08:30, 16:45, 22:45. **Objetivos de informe:** 09:05, 17:10, 23:10. **Watchdog:** 11:05, 19:20, 01:20. Los cron no prueban por sí solos que GitHub haya iniciado una ejecución. Los horarios deben evaluarse en Europe/Madrid y con marcas de tiempo reales.

## Fuente de datos y trazabilidad

- Garmin/Intervals aporta mediciones y sesiones; Google Sheets pestaña `RPE` aporta ejercicios detallados y RPE por **ID exacto** de actividad. No emparejar sólo por fecha.
- Advanced Analytics recupera el CSV y lo deja en `training_feedback.json` con huella SHA-256 y su `GITHUB_RUN_ID`.
- CrossFit Insights activado por la ejecución anterior lee **esa misma fotografía** y verifica ID, huella, hora y conteos usando GITHUB_EVENT_PATH, sin modificar YAML. Nunca debe hacer una segunda descarga independiente en un ciclo encadenado. Una ejecución manual independiente mantiene la lectura en vivo.
- `report_ready.json` acredita datos preparados, **no** entrega de una notificación en ChatGPT. Las muestras recientes se evalúan por su timestamp real, no por la fecha del archivo.
- No comparar kilos de barra, polea o máquina entre sí; el RPE general no es RIR de cada serie.

## Cómo operar y mantener

1. Para actualizar todo: ejecutar `Garmin Recovery Sync` en `main` y **esperar los cuatro workflows** en verde. No ejecutar Advanced Analytics aisladamente tras más de 60 minutos de la última Sync.
2. Confirmar que `training_feedback.json` y `crossfit_insights.json` contienen la misma actividad e ID; revisar el origen del RPE y las fechas.
3. Si falla una etapa, leer el paso concreto y conservar los últimos archivos válidos. No aumentar el límite de frescura simplemente para pintar el workflow de verde.
4. Tras editar Python o YAML, verificar `Garmin Recovery CI` en el commit; luego probar una cadena completa. No se deben borrar scripts históricos por el número que llevan en el nombre.
5. Los cambios en Google Apps Script requieren ver el `Code.gs` real y comprobar su trigger. Un `workflow_dispatch` no prueba quién lo activó.
6. Antes de declarar autonomía: tres ciclos automáticos consecutivos verificados y seguimiento mensual de la fiabilidad.

Ver [MAINTENIMIENTO.md](MAINTENIMIENTO.md) y [OPERACION_Y_VALIDACION.md](OPERACION_Y_VALIDACION.md).
