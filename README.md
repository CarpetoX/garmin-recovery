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
| Auxiliar | `garmin-shadow-publish-v296.yml` | Espejo de publicación (V2.9.6), disparo manual o `repository_dispatch` |
| Auxiliar | `garmin-certified-reports.yml` | Informes certificados bajo demanda (V3.9) |

> Nota: en `.github/workflows` hay hoy **ocho** archivos: los seis permanentes y dos auxiliares sin `schedule` ni `workflow_run`.

## App de seguimiento V5 (nuevo, en modo sombra)

Paquete `garmin_recovery/` que se ejecuta dentro de *Advanced Analytics* (paso no bloqueante, `continue-on-error`) y genera:

| Salida | Contenido |
|---|---|
| `history/daily.csv` | Registro diario canónico persistente (HRV, FC, sueño, estrés, carga, sensaciones, turno, fuente por métrica). Upsert por fecha; nunca borra datos. |
| `history/sessions.csv` | Sesiones por ID de actividad con duración, carga, FC, RPE y sRPE (Foster). |
| `app/readiness_v3.json` | Disponibilidad de hoy, componentes, factores, carga (ATL/CTL/TSB, monotonía, strain, ACWR) y tendencia de 28 días. |
| `app/dashboard.html` | Panel autocontenido (claro/oscuro, móvil) para abrir en el navegador. |

**Modelo readiness v3** (`garmin_recovery/readiness.py`):

- HRV en ln(rMSSD): media de 7 días frente a tu línea base (hasta 60 días previos a esa semana) con banda de cambio mínimo relevante ±0,5 DE. Una noche mala pesa menos que una semana mala.
- FC en reposo y nocturna en desviaciones robustas (mediana/MAD); sueño frente a la necesidad configurada y deuda de 3 noches; carga solo cuando la CTL permite interpretar la forma; sensaciones de Intervals.icu (1 = mejor, 4 = peor).
- Puntuaciones continuas (`75 + 12,5·z`), ponderadas y renormalizadas. Zonas: verde ≥ 70, ámbar 50–69, rojo < 50, con RPE máximo y volumen recomendados.
- Salvaguardas: sin HRV/sueño/FC de hoy o sueño sin confirmar → `pending` (no autoriza intensidad alta); línea base < 7 noches → sin puntuación; < 14 → `provisional`, nunca verde; sueño < 5 h nunca verde.
- Avisos según turno (TN y post-TN) desde `shift_calendar.json`.
- **Dos confianzas separadas** (V5.1): *datos* (completos y cubiertos 7 días) y *recomendación* (histórico mínimo: media ≥ 14 noches, alta ≥ 28; nunca alta mientras `model_validated` sea `false`).

**Certificado del informe** (`certificate` en `app/readiness_v3.json`, V5.1): ciclo y runs de la cadena, hora real de sincronización (detecta Sync fuera de franja), antigüedad de cada medición por su marca temporal, huellas SHA-256 de las fuentes, coherencia v3/v2 de los valores de hoy y estado de entrega declarado como no verificable desde los datos. **Integridad del entrenamiento** (`training_integrity`): sesiones ↔ RPE emparejadas por ID exacto, RPE sin actividad, fechas discrepantes y sesiones sin RPE (no se rellenan ni estiman).

Uso local:

```bash
python -m garmin_recovery run              # escribe history/ y app/
python -m garmin_recovery run --dry-run    # solo calcula e imprime el resumen
python -m unittest discover -p 'test_*.py' # toda la batería, incluida test_app_readiness_v5
```

Umbrales en `garmin_recovery/config.py`; para personalizarlos crear `app_config.json` en la raíz con solo las claves a cambiar (p. ej. `{"sleep_need_hours": 8}`).

El modelo v3 **no sustituye** `recovery_assessment.json` ni los informes: corre en paralelo para compararlo con el v2 antes de promoverlo.

**Privacidad:** este repositorio es público y contiene datos fisiológicos, calendario de turnos e identificadores de Intervals y de la hoja de Google. Se recomienda hacerlo privado (GitHub Actions sigue funcionando igual).

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
