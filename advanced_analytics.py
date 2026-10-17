"""Compatibilidad: el cálculo v2 vive ahora en ``garmin_recovery/advanced.py``.

Este archivo sigue existiendo porque los workflows y otros módulos lo importan o ejecutan
(``python advanced_analytics.py``, ``import advanced_analytics``). Se sustituye a sí mismo por el
módulo del paquete para que ``NOW``, ``TODAY`` y las funciones sean los mismos objetos.
"""
import sys

from garmin_recovery import advanced

if __name__ == "__main__":
    advanced.main()
else:
    sys.modules[__name__] = advanced
