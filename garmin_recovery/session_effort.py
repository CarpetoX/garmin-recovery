"""RPE frente a FC en cada sesión (V7.20).

Usa el mismo esfuerzo relativo que la validación de modelos (``backtest.effort_by_session``):
z = ln(sRPE / carga de FC), estandarizado dentro de su tipo de sesión con tu propio historial
(mediana/MAD). Con |z| ≥ ``FLAG_Z`` se marca la sesión:

* ``alto``: el RPE que declaraste es alto para la FC registrada (te costó más de lo habitual).
* ``bajo``: el RPE es bajo para la FC registrada.

Es descriptivo: no estima nada que no conste, no cambia la decisión del día y no usa
sesiones sin RPE (no se rellenan).
"""
from __future__ import annotations

from pathlib import Path

FLAG_Z = 1.5

TEXT = {
    "alto": "RPE alto para tu FC: te costó más de lo habitual en este tipo de sesión",
    "bajo": "RPE bajo para tu FC: la FC fue alta para el esfuerzo que marcaste",
}


def classify(z: float | None) -> str | None:
    if z is None:
        return None
    if z >= FLAG_Z:
        return "alto"
    if z <= -FLAG_Z:
        return "bajo"
    return None


def compute(sessions: dict) -> dict:
    """``{id: {"z", "flag", "category", "n_ref"}}`` para las sesiones con RPE y carga de FC."""
    from .backtest import effort_by_session
    from .report import categorize
    out = {}
    for sid, e in effort_by_session(sessions, categorize).items():
        z = round(e["z"], 2)
        out[sid] = {"z": z, "flag": classify(z), "category": e["category"], "n_ref": e["n_ref"]}
    return out


def load(root: str | Path = ".") -> dict:
    """Calcula el esfuerzo relativo desde ``history/sessions.csv``; ``{}`` si no existe."""
    from .history import read_table
    from .records import SESSION_FIELDS
    path = Path(root) / "history" / "sessions.csv"
    if not path.exists():
        return {}
    return compute(read_table(path, SESSION_FIELDS, "id"))
