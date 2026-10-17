"""Garmin Recovery — capa de aplicación de seguimiento deportivo profesional.

Paquete nuevo y aditivo: lee los JSON/CSV que ya publica la cadena
Sync → Heart → Advanced → CrossFit, construye un registro diario canónico
persistente y calcula un modelo de disponibilidad (readiness) v3 con carga
de entrenamiento. No modifica ni sustituye los archivos publicados por la
cadena existente: sus salidas viven en ``app/`` y ``history/``.

Uso::

    python -m garmin_recovery run            # genera app/ e history/
    python -m garmin_recovery run --dry-run  # calcula sin escribir
"""

APP_VERSION = "6.1.0"
MODEL_VERSION = "readiness-v3.2"
