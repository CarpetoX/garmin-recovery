"""Registro de bloques opcionales que fallan (informe y web): antes se tragaban en silencio.

``failed`` guarda el fallo y emite una anotación de GitHub Actions (``::warning::``); el informe lista los bloques
afectados para que se vea que falta una sección. No usa la hora ni la red.
"""
from __future__ import annotations

import sys

_FAILURES: list[dict] = []


def reset() -> None:
    _FAILURES.clear()


def failed(block: str, exc: BaseException) -> None:
    entry = {"block": block, "error": type(exc).__name__}
    _FAILURES.append(entry)
    print(f"::warning title=Bloque opcional no disponible::{block} ({type(exc).__name__}: {str(exc)[:120]})", file=sys.stderr)


def failures() -> list[dict]:
    return list(_FAILURES)


def to_markdown() -> str:
    """Línea para el informe ('' si no falló nada)."""
    if not _FAILURES:
        return ""
    names = ", ".join(dict.fromkeys(f["block"] for f in _FAILURES))
    return f"\n_Bloques opcionales no disponibles en este ciclo: {names}. El resto del informe no depende de ellos._"
