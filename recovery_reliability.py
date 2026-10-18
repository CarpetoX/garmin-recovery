"""Compatibilidad: este módulo vive ahora en ``garmin_recovery/reliability.py``.

Los workflows y otros módulos lo siguen importando o ejecutando con el nombre antiguo; el archivo se
sustituye a sí mismo por el módulo del paquete (mismos objetos, mismo comportamiento).
"""
import sys

if __name__ == "__main__":
    from garmin_recovery import reliability
    reliability.main()
else:
    from garmin_recovery import reliability
    sys.modules[__name__] = reliability
