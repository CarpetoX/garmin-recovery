# Política de mantenimiento — Garmin Recovery V5.7

Revisión: 17/10/2026 · Europe/Madrid. Complementa `README.md` (qué hace la app) y `OPERACION_Y_VALIDACION.md` (operación y trazabilidad).

## Workflows permanentes (ocho)

| Workflow | Disparo | Función |
|---|---|---|
| `sync.yml` (Garmin Recovery Sync) | Apps Script firmado (`repository_dispatch`), cron de respaldo 08:30/16:45/22:45, manual | Intervals.icu y RPE; inicia la cadena |
| `garmin-heart-rate.yml` | tras Sync | Garmin: FC, HRV, sueño, estrés, Body Battery |
| `advanced-analytics-rpe.yml` | tras Heart Rate | Recuperación v2, calidad de datos, instantánea de RPE |
| `crossfit-insights.yml` | tras Advanced | Fuerza/WOD, certificado del ciclo, **app V5** (`garmin_recovery`), validación y publicación |
| `monitor-monthly.yml` | watchdog 11:05/19:20/01:20 y dispatch | Salud de la cadena, origen, resumen mensual |
| `garmin-ci.yml` | push/PR | Tests, compilación y validación de topología de workflows |
| `garmin-shadow-publish-v296.yml` | dispatch del monitor, manual | Copia verificada en la rama `garmin-v296-shadow` |
| `garmin-certified-reports.yml` | manual | Verificación de informes certificados |

Los cron usan `timezone: Europe/Madrid`. GitHub puede retrasarlos horas: Apps Script es el disparador principal y el cron, el respaldo.

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

## Código obsoleto

Un número de versión en el nombre (`recovery_v231.py`, `monitor_v231.py`…) no significa que sobre: muchos siguen importados. Antes de borrar un módulo, comprobar que ningún workflow lo ejecuta y que ningún módulo en uso lo importa (análisis de imports desde los scripts que ejecutan los workflows), y quitar sus tests y referencias en los YAML en el mismo PR.

## Validación local

```bash
python -m compileall -q .
python -m unittest discover -p 'test_*.py'      # batería completa (~700 tests)
python -m garmin_recovery run --dry-run         # calcula sin escribir
python -m garmin_recovery validate              # contrato y coherencia de app/ e history/
```

## Vigilancia continua

- Tamaño del repositorio (los JSON de estrés y de ciclos superan 1 MB cada uno), duración de workflows y retraso real del cron.
- Frescura de datos por marca temporal de cada muestra, no por `generated_at`.
- Fallos del disparador de Apps Script (huecos entre ciclos firmados).
- Cobertura de RPE: la monotonía, el strain y el ACWR solo se calculan con ≥ 75 % de sesiones con RPE.
- El v3 sigue en sombra (`model_validated: false`) hasta contrastarlo 4–6 semanas con RPE y rendimiento reales.

La puntuación de calidad fisiológica de Garmin no es el porcentaje de CI de GitHub. Un historial de HRV/sueño inmaduro requiere más mediciones, no estimaciones.
