"""Compatibilidad: este módulo vive ahora en ``garmin_recovery/monitor_clarity.py``.

Los workflows y otros módulos lo siguen importando o ejecutando con el nombre antiguo; el archivo se
sustituye a sí mismo por el módulo del paquete (mismos objetos, mismo comportamiento).
"""
import runpy
import sys

if __name__ == "__main__":
    runpy.run_module("garmin_recovery.monitor_clarity", run_name="__main__")
else:
    from garmin_recovery import monitor_clarity
    sys.modules[__name__] = monitor_clarity
