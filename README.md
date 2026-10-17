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
| `app/readiness_v3.json` | Disponibilidad de hoy, componentes, factores, carga (ATL/CTL/TSB de Intervals; monotonía, strain y ACWR sobre sRPE) y tendencia de 28 días. |
| `app/dashboard.html` | Panel autocontenido (claro/oscuro, móvil) para abrir en el navegador. |

**Modelo readiness v3** (`garmin_recovery/readiness.py`):

- HRV en ln(rMSSD): media de 7 días frente a tu línea base (mediana de hasta 60 días previos a esa semana) con banda de cambio mínimo relevante ±0,5 σ robusta (MAD). Una noche mala pesa menos que una semana mala, y una lectura aislada anómala no ensancha el rango normal.
- FC en reposo y nocturna en desviaciones robustas (mediana/MAD); sueño frente a la necesidad configurada y deuda de 3 noches; carga solo cuando la CTL permite interpretar la forma; sensaciones de Intervals.icu (1 = mejor, 4 = peor).
- Puntuaciones continuas (`75 + 12,5·z`), ponderadas y renormalizadas. Zonas: verde ≥ 70, ámbar 50–69, rojo < 50, con RPE máximo y volumen recomendados.
- Salvaguardas: sin HRV/sueño/FC de hoy o sueño sin confirmar → `pending` (no autoriza intensidad alta); línea base < 7 noches → sin puntuación; < 14 (`provisional_below_n`) → `provisional`, nunca verde; sueño < 5 h nunca verde.
- Avisos según turno (TN y post-TN) desde `shift_calendar.json`.
- **Dos confianzas separadas** (V5.1): *datos* (completos y cubiertos 7 días) y *recomendación* (histórico mínimo: media ≥ 14 noches, alta ≥ 28; nunca alta mientras `model_validated` sea `false`).

**Informe del ciclo** (V5.3, `app/informe.md` + `app/charts/*.svg`): GitHub lo muestra con sus gráficas, también en el móvil, y ChatGPT o Claude lo pueden leer y citar. Tiene tres variantes según la hora del Sync: *mañana* (qué cambió frente a tu línea base, señales coincidentes, incertidumbre y plan), *tarde* (actividad de hoy y si encaja con la decisión) y *noche* (balance del día y la semana y previsión orientativa). Lleva hasta 7 gráficas: disponibilidad oficial frente a v3 con franja de decisión, HRV con rango normal, FC en reposo y nocturna, sueño (nocturno frente a diurno/post-TN), carga con ATL/CTL, carga por sesión y tipo (WOD, fuerza, halterofilia, técnica) y progresión de fuerza. Termina con el certificado. La app se ejecuta al final de *CrossFit Insights*, tras el certificado del ciclo, y guarda cada día en `history/daily.csv` las puntuaciones de v2, el híbrido y v3 y la zona de decisión.

**V5.6, validación antes de publicar:** después de generar el informe, `python -m garmin_recovery validate` comprueba 30 puntos, entre ellos:
- el contrato de `readiness_v3.json`;
- que la decisión sea la más conservadora de los modelos;
- que ningún ajuste del plan supere el RPE máximo;
- que las fechas estén ordenadas y lleguen hasta hoy;
- que el identificador GR sea correcto en la cabecera, el certificado y `reports.csv`, sin duplicados;
- que la recomendación del Markdown coincida con `decision.guidance`;
- que las gráficas enlazadas existan y sean SVG válidos, y que el historial no tenga duplicados.

Si alguna comprobación falla, CrossFit Insights restaura el `app/` y el `history/` anteriores, de modo que nunca se publica un informe roto, y guarda el motivo en `app/validation.json`.

**V5.7, correcciones de la auditoría de calidad** (un test por corrección en `test_audit_fixes_v57.py`):
- **Decisión:** un rojo prevalece sobre un modelo pendiente (antes daba "pendiente" con RPE 6); v2 e híbrido de otro día cuentan como desactualizados y no deciden.
- **Publicación segura:** el paso de validación ya no puede saltarse la restauración si la app falla; el aviso a la rutina solo sale si la validación pasa. El validador comprueba además que la pauta corresponda a la zona, que el JSON, el Markdown y `reports.csv` sean del mismo ciclo y que la salida tenga menos de 60 min.
- **Modelo:** línea base de HRV robusta (mediana/MAD); monotonía, strain y ACWR sobre sRPE (Foster), con ACWR por medias 7/28 días solo con 28 días de historial; EWMA propia sin sesgo de arranque.
- **Informe:** la gráfica de sesiones usa los 14 días completos (antes, como mucho 12 sesiones); halterofilia en ámbar al ≤ 80 % en todo el informe.
- **Plan:** entiende `80 % 1RM`, `2x20` (kg por implemento), `150,160`, `167,5` y `RPE 7-8`; en ámbar quita al menos una serie (2 × → 1 ×).
- **Historial:** las sesiones borradas en Intervals se marcan `removed=1` (no se borra ninguna fila) y dejan de contar en la carga; `--now` con otra zona horaria usa la fecha de Madrid.

**V5.5, plan ajustado:** la app lee la pestaña `Planificados` de la hoja RPE CrossFit (secreto `PLANNED_CSV_URL`, con la pestaña publicada como CSV; también vale un `planned_sessions.csv` en la raíz) y ajusta cada sesión de hoy a la decisión del día:
- **Verde:** se mantiene.
- **Ámbar:** 75 % de las series; fuerza al 90 % y halterofilia al 80 % de la carga prevista, redondeadas a 2,5 kg; WOD al 75 % del tiempo.
- **Rojo o pendiente:** técnica con PVC o barra vacía, o zona 2.

Nunca supera el RPE máximo de la decisión. Por la tarde compara lo planificado con lo hecho (por ID de actividad) y por la noche avisa de lo planificado para mañana. Columnas de `Planificados`: Fecha, Hora, Actividad, Formato (p. ej. `5 × 3`), Carga prevista (kg) (p. ej. `150–160`), Estado (vacío o `PREVISTO`; `REALIZADO…` lo excluye), RPE real, Notas, Tipo (Fuerza/Halterofilia/WOD/Técnica/Aeróbico/Movilidad), Ejercicio principal, RPE objetivo, Duración (min), Unidad de carga, ID actividad. Las actividades marcadas en la hoja como calentamiento o técnica "sin RPE" ya no cuentan como RPE pendiente.

**V5.4, calidad de datos del informe:** cada informe lleva un identificador (`GR-AAAA-MM-DD-HHMM-xxxxxx`) para poder citarlo y rastrearlo. Incluye "Qué ha cambiado desde el informe anterior", calculado a partir de `history/reports.csv`, una foto por ciclo. Las cargas de fuerza se muestran con su unidad real: total y por mancuerna, con barra, indicada en máquina o en máquina de discos. Hay una sección de acciones pendientes: RPE que faltan por ID exacto, ejercicios con la unidad sin especificar y sensaciones sin registrar. Se añaden pautas específicas para el box según la zona y las gráficas de recuperación con medias de 7 días en todas las franjas.

**Decisión operativa y registro de modelos** (`decision`, V5.2): conviven varias puntuaciones (v2 oficial, híbrido Garmin + local, v3 en pruebas, compatibilidad V2.2 y Garmin Training Readiness). `decision.registry` declara versión, rol, escala y regla de cada una, y la **zona operativa es la más conservadora entre v2, híbrido y v3**: un rojo prevalece siempre; si no hay rojo y alguno está pendiente, sin datos o es de otro día, la decisión queda pendiente. La recomendación del día es `decision.guidance`, nunca `readiness.guidance`. El v3 incluye desde V5.2 el estrés de Garmin del día anterior (completo) frente a tu línea base.

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
