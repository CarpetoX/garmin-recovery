"""V9.8: catálogo de ejercicios. Puro salvo `load`, que lee ``catalogo_ejercicios.json``.

Un mismo ejercicio apuntado con nombres distintos («press inclinado con mancuernas», «press banca inclinado con
mancuernas»…) partía su historial en varios. El catálogo da un nombre canónico a cada alias y unifica unidades
equivalentes (``kg_lastre`` = ``lastre_kg``). Un nombre que no está en el catálogo se deja tal cual: nunca se
adivina que dos ejercicios sean el mismo.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

FILE = "catalogo_ejercicios.json"


def norm(text) -> str:
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+]+", " ", t)).strip()


@lru_cache(maxsize=8)
def _load(path: str) -> tuple[dict, dict, dict]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    names, patterns = {}, {}
    for ex in data.get("exercises") or []:
        if not isinstance(ex, dict) or not ex.get("name"):
            continue
        canon = str(ex["name"])
        for alias in [canon, *(ex.get("aliases") or [])]:
            names.setdefault(norm(alias), canon)
        if ex.get("pattern"):
            patterns[norm(canon)] = str(ex["pattern"])
    units = {str(k): str(v) for k, v in (data.get("unit_aliases") or {}).items()}
    return names, units, patterns


def catalog(root: str | Path = ".") -> tuple[dict, dict, dict]:
    return _load(str(Path(root) / FILE))


def canonical(name, root: str | Path = ".") -> str:
    """Nombre canónico del ejercicio; el original si no está en el catálogo."""
    raw = str(name or "").strip()
    canon = catalog(root)[0].get(norm(raw), raw)
    return raw if norm(canon) == norm(raw) else canon  # mismo nombre con otra grafía: se respeta tal cual


def canonical_unit(unit, root: str | Path = ".") -> str:
    u = str(unit or "")
    return catalog(root)[1].get(u, u)


def pattern(name, root: str | Path = ".") -> str | None:
    return catalog(root)[2].get(norm(canonical(name, root)))
