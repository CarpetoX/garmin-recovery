# Política de mantenimiento — Garmin Recovery V5.7

Revisión: 17/10/2026 · Europe/Madrid. Complementa `README.md` (qué hace la app) y `OPERACION_Y_VALIDACION.md` (operación y trazabilidad).

## Workflows permanentes (ocho)

| Workflow | Disparo | Función |
|---|---|---|
| `sync.yml` (Garmin Recovery Sync) | Apps Script firmado (`repository_dispatch`), cron de respaldo diario (08:30, llega ~13:00), manual | Intervals.icu y RPE; inicia la cadena |
| `garmin-heart-rate.yml` | tras Sync | Garmin: FC, HRV, sueño, estrés, Body Battery |
| `advanced-analytics-rpe.yml` | tras Heart Rate | Recuperación v2, calidad de datos, instantánea de RPE |
| `crossfit-insights.yml` | tras Advanced | Fuerza/WOD, certificado del ciclo, **app V5** (`garmin_recovery`), validación y publicación |
| `monitor-monthly.yml` | watchdog 11:05/19:20/01:20 y dispatch | Salud de la cadena, origen, resumen mensual |
| `garmin-ci.yml` | push/PR | Tests, compilación y validación de topología de workflows |
| `garmin-shadow-publish-v296.yml` | dispatch del monitor, manual | Copia verificada en la rama `garmin-v296-shadow` |
| `garmin-certified-reports.yml` | manual | Verificación de informes certificados |

Los cron usan `timezone: Europe/Madrid`. GitHub los retrasa 2–5 h: Apps Script es el disparador de las tres franjas (código en `apps_script/`) y el cron de Sync queda como un único respaldo diario.

## Invariantes

1. Un cambio de código va en rama + PR, con CI verde antes de fusionar, y se comprueba con un Sync real después.
2. Los IDs de actividad y las marcas temporales de medición se conservan. No se borran filas de `history/*.csv`, sesiones, sueño ni certificados: una sesión eliminada en Intervals se marca `removed=1`.
3. `report_cycles.json` guarda snapshots con SHA-256: conservar todos. No truncar, comprimir ni archivar sin prueba de reconstrucción y reversión.
4. `training_feedback.json` es una instantánea de RPE: en Advanced → CrossFit se usa una sola vez, validada por huella, run ID y frescura.
5. No estimar 1RM desde el RPE de la sesión ni completar repeticiones de WOD con lo prescrito.
6. Un informe generado no es un aviso recibido: sin acuse externo, la entrega a ChatGPT es "no verificada".
7. El origen de un `repository_dispatch` o `workflow_dispatch` requiere evidencia (firma HMAC de Apps Script); no deducirlo del tipo de evento.
8. La decisión del día es siempre `decision.guidance` (la más conservadora de v2, híbrido y v3); `readiness.guidance` es solo del v3 en pruebas. Un rojo prevalece; si falta un modelo o es de otro día, queda pendiente.
9. La app nunca publica salidas sin validar: si `python -m garmin_recovery validate` falla, se restauran `app/` e `history/` anteriores y el motivo queda en `app/validation.json`.
10. Los archivos generados (`app/`, `history/`) solo los escribe la cadena; no se suben a mano.
11. El repositorio es público por decisión del propietario (ChatGPT lo lee). No es un hallazgo de calidad; lo obligatorio es que no haya secretos en el código ni en los datos.

## Código obsoleto

`sync.yml` ya no tiene código Python en línea: `sync_fetch_wellness.py`, `sync_fetch_activities.py` y `sync_daily_analysis.py` (salida idéntica comprobada byte a byte; tests `test_sync_daily_analysis.py` y `test_structure_v59.py`).

`garmin_metrics.py`, `garmin_activity_metrics.py` y `validate_pipeline.py` ya no se ejecutan al importarlos (`main()` + `if __name__ == "__main__"`); misma salida al ejecutarlos.

Un número de versión en el nombre (`recovery_v231.py`, `monitor_v231.py`…) no significa que sobre: muchos siguen importados. Antes de borrar un módulo, comprobar que ningún workflow lo ejecuta y que ningún módulo en uso lo importa (análisis de imports desde los scripts que ejecutan los workflows), y quitar sus tests y referencias en los YAML en el mismo PR.

## Validación local

```bash
python -m compileall -q .
python -m unittest discover -p 'test_*.py'      # batería completa (~700 tests)
python -m garmin_recovery run --dry-run         # calcula sin escribir
python -m garmin_recovery validate              # contrato y coherencia de app/ e history/
```

## Vigilancia continua

- Tamaño del repositorio. Medido el 17/10/2026 (historial completo): 6,4 MB comprimidos tras 11 días y 1.232 commits, unos 0,5 MB/día (~180 MB/año). Git comprime bien las versiones sucesivas de los JSON grandes (165 versiones de `garmin_stress.json` ocupan 282 KB), así que **no hace falta compactar todavía**; revisar al superar ~500 MB.
- Retraso real del cron de GitHub: en 60 ejecuciones llegó entre 2,3 y 5,7 h tarde. El disparador fiable es Apps Script; un vigilante basado en cron de GitHub no recuperaría a tiempo una franja perdida.
- Duración de los workflows.
- Frescura de datos por marca temporal de cada muestra, no por `generated_at`.
- Fallos del disparador de Apps Script (huecos entre ciclos firmados).
- Cobertura de RPE: la monotonía, el strain y el ACWR solo se calculan con ≥ 75 % de sesiones con RPE.
- El v3 sigue en sombra (`model_validated: false`) hasta contrastarlo 4–6 semanas con RPE y rendimiento reales.

La puntuación de calidad fisiológica de Garmin no es el porcentaje de CI de GitHub. Un historial de HRV/sueño inmaduro requiere más mediciones, no estimaciones.

## Plan de migración al paquete `garmin_recovery`

Hoy conviven la cadena antigua (≈ 40 scripts ejecutados por los workflows, más sus dependencias) y el paquete V5, que genera el informe vigente. Se migra **una pieza por PR**, siempre con una prueba de salida idéntica sobre datos reales y sin cambiar los JSON que leen ChatGPT o Apps Script (`report_ready.json`, `recovery_assessment.json`, `shift_calendar.json`, `morning_sleep_status.json`, `app/*`).

| Paso | Qué | Estado |
|---|---|---|
| 0 | `sync.yml` sin código en línea; scripts sin efectos al importarlos | Hecho (V5.9) |
| 1 | Retirar del monitor los informes previos que solo generaban artefactos (V3.9.2.2 enriquecido, V4.0.2 visual) | Hecho (V5.9); sus 9 módulos y 8 tests, borrados en V6.0 |
| 2 | Calcular el v2 dentro del paquete, con pruebas *golden*; el archivo se sigue publicando igual | En curso: 2a hecho (V6.2) — `advanced_analytics.py` vive en `garmin_recovery/advanced.py` (el nombre antiguo es un alias del mismo módulo) con prueba de salida idéntica sobre el día congelado; pendiente 2b: `recovery_v23.py` / `recovery_reliability.py` |
| 3 | Pasar al paquete la extracción de fuerza y WOD de `crossfit_insights.py` (mismas reglas de unidades e implementos) | Pendiente |
| 4 | Unificar certificados y monitor (`report_cycles.json`, `report_ready.json`) en un módulo del paquete, conservando el historial con SHA-256 | Pendiente |
| 5 | Borrar los módulos que ya no ejecute ningún workflow ni importe ningún módulo en uso, con sus tests | En curso: 15 módulos borrados hasta V6.0; se repite tras cada paso |

Regla: si una salida pública cambia, aunque sea un campo, el PR lo declara y se valida antes con un Sync real.
