"""Compatibilidad: este módulo vive ahora en ``garmin_recovery/report_audit.py``.

Los workflows y otros módulos lo siguen importando o ejecutando con el nombre antiguo; el archivo se
sustituye a sí mismo por el módulo del paquete (mismos objetos, mismo comportamiento).
"""
import runpy
import sys

if __name__ == "__main__":
    runpy.run_module("garmin_recovery.report_audit", run_name="__main__")
else:
    from garmin_recovery import report_audit
    sys.modules[__name__] = report_audit
