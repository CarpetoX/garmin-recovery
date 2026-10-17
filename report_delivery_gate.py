"""Compatibilidad: este módulo vive ahora en ``garmin_recovery/delivery_gate.py``.

Los workflows y otros módulos lo siguen importando o ejecutando con el nombre antiguo; el archivo se
sustituye a sí mismo por el módulo del paquete (mismos objetos, mismo comportamiento).
"""
import runpy
import sys

if __name__ == "__main__":
    runpy.run_module("garmin_recovery.delivery_gate", run_name="__main__")
else:
    from garmin_recovery import delivery_gate
    sys.modules[__name__] = delivery_gate
