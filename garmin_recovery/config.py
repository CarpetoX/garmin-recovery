"""Configuración central con valores por defecto y sobrescritura opcional.

Los umbrales del modelo viven aquí, no repartidos por los scripts. Para
personalizarlos, crear ``app_config.json`` en la raíz con solo las claves que
se quieran cambiar (fusión profunda sobre ``DEFAULTS``).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULTS: dict = {
    "timezone": "Europe/Madrid",
    # Ventanas del modelo
    "baseline_days": 60,          # línea base personal (excluye el día evaluado)
    "rolling_days": 7,            # media móvil de HRV (enfoque ln rMSSD 7 días)
    "min_baseline_n": 7,          # por debajo: no hay puntuación
    "mature_baseline_n": 21,      # desde aquí: confianza alta
    "min_rolling_n": 4,           # noches mínimas para la media móvil de 7 días
    "swc_factor": 0.5,            # cambio mínimo relevante = 0.5 · DE de la base
    # Sueño
    "sleep_need_hours": 7.5,
    "sleep_debt_nights": 3,
    # Carga
    "atl_days": 7,
    "ctl_days": 42,
    "min_ctl_for_form": 15.0,     # con CTL menor, la "forma" (TSB %) no es interpretable
    "min_load_coverage_days": 28, # días de historial de sesiones para ACWR propio
    # Composición de la puntuación (se renormaliza con los componentes disponibles)
    "weights": {
        "hrv": 0.35,
        "cardiac": 0.15,
        "sleep": 0.25,
        "load": 0.15,
        "subjective": 0.10,
    },
    "zones": {"green": 70, "red": 50},
    # Rutas
    "history_dir": "history",
    "output_dir": "app",
    "history_retention_days": 3650,
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(root: str | Path = ".", filename: str = "app_config.json") -> dict:
    path = Path(root) / filename
    override: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                override = loaded
        except (OSError, ValueError):
            override = {}
    return _merge(DEFAULTS, override)
