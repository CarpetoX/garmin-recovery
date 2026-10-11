# Política de mantenimiento — Garmin Recovery V2.6

## Invariantes

1. Siempre seis workflows permanentes; workflows de actualización temporales se eliminan **después de verificar su resultado**, no durante la ejecución.
2. Un cambio requiere código + pruebas CI + una sincronización completa verificada. No certificar resultados futuros.
3. Los ID de actividad y las marcas temporales de medición deben mantenerse. No se borran registros de entrenamiento, sesiones, sueño ni certificados.
4. `training_feedback.json` representa una instantánea de RPE; en la cadena Advanced→CrossFit el mismo CSV debe utilizarse una sola vez y validarse por huella, run ID y frescura.
5. No generar estimaciones de 1RM a partir del RPE de la sesión ni completar repeticiones de WOD con lo previsto.
6. Los informes generados no son avisos recibidos. Sin acuse externo la entrega sigue como no verificada.
7. El origen de una ejecución `repository_dispatch` o `workflow_dispatch` requiere evidencia del iniciador; no deducir Apps Script de un evento.

## Próximas etapas de refactorización (no ejecutar a ciegas)

- `sync.yml` concentra cientos de líneas y debe modularizarse moviendo **un paso por cambio** a scripts comprobados, conservando IDs, JSON publicados y semántica.
- `report_cycles.json` almacena snapshots y sus SHA-256: conservar todos. Antes de archivar por mes, introducir prueba de lectura/reconstrucción, comprobación SHA y capacidad de reversión. No truncar ni comprimir sin pruebas de recuperación.
- Mantener bajo vigilancia el tamaño del repositorio, duración de workflows, frecuencia real de `schedule`, frescura de datos y fallos del respaldo Apps Script.
- Para cambios sensibles, probar primero en una rama/PR si es posible; nunca sobrescribir el histórico sin copia verificable.

## Validación segura

```bash
python -m compileall -q .
python -m unittest -v test_morning_sleep_gate test_sleep_integration test_quality_v248 test_training_extensions test_rpe_cycle_snapshot
python monitor_v231.py
```

La puntuación de calidad fisiológica de Garmin no representa el porcentaje de CI de GitHub. Históricos de HRV/sueño inmaduros requieren más mediciones, no estimaciones artificiales.
