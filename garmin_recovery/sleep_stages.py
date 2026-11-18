"""V9.7: plausibilidad de las fases de sueño de Garmin. Puro, sin red.

Garmin a veces no separa bien las fases, sobre todo en el sueño de día tras un turno de noche: devuelve 0 min de
REM en episodios de varias horas, o ninguna fase. Esas fases no son una medición fiable: se marcan como dudosas y
no se muestran ni se comparan como si fueran reales. La duración y la puntuación de Garmin se conservan, pero se
avisa de que la puntuación puede estar condicionada por esas fases. No toca los modelos de recuperación.
"""
from __future__ import annotations

MIN_HOURS = 3.0  # por debajo, un episodio corto puede no tener REM de verdad
MAX_DEEP_SHARE = 0.5  # más de la mitad del episodio en sueño profundo no es plausible


def _num(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _h(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def check(hours, deep_min, rem_min) -> dict | None:
    """None si las fases son plausibles o no hay fases; si no, ``{"code", "text"}`` con el motivo."""
    h, deep, rem = _num(hours), _num(deep_min), _num(rem_min)
    if h is None or h < MIN_HOURS or deep is None or rem is None:
        return None
    if deep == 0 and rem == 0:
        return {"code": "no_stages", "text": f"Garmin no separó las fases en un episodio de {_h(h)} h."}
    if rem == 0:
        return {"code": "rem_zero", "text": f"Garmin marca 0 min de REM en {_h(h)} h de sueño; no es plausible y suele ser un "
                                            "fallo de detección (frecuente en el sueño de día tras un turno de noche)."}
    if deep > h * 60 * MAX_DEEP_SHARE:
        return {"code": "deep_excess", "text": f"Garmin marca {deep:.0f} min de sueño profundo en {_h(h)} h; más de la mitad del "
                                               "episodio no es plausible."}
    return None


NOTE = ("Fases dudosas: no se muestran ni se comparan. La duración es la de Garmin; su puntuación de sueño puede estar "
        "penalizada por esas fases.")
