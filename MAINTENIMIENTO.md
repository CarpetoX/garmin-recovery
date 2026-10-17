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

`sync.yml` se modulariza un paso por cambio: el resumen diario/semanal ya vive en `sync_daily_analysis.py` (salida idéntica comprobada; test `test_sync_daily_analysis.py`). Siguientes candidatos: la descarga de wellness y la de actividades.

Algunos scripts antiguos se ejecutan al importarlos y escriben JSON (p. ej. `garmin_metrics.py`): no importarlos fuera de la cadena.

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
