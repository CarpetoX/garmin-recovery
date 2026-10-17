"""Estadística mínima, robusta y sin dependencias externas."""
from __future__ import annotations

import math
from typing import Iterable, Sequence


def finite(values: Iterable) -> list[float]:
    out = []
    for v in values:
        if isinstance(v, bool) or v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            out.append(f)
    return out


def mean(values: Sequence[float]) -> float | None:
    vals = finite(values)
    return sum(vals) / len(vals) if vals else None


def sd(values: Sequence[float]) -> float | None:
    vals = finite(values)
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def median(values: Sequence[float]) -> float | None:
    vals = sorted(finite(values))
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


def mad_sigma(values: Sequence[float]) -> float | None:
    """Desviación típica robusta (MAD · 1.4826); recurre a la DE si MAD = 0."""
    vals = finite(values)
    if len(vals) < 3:
        return sd(vals)
    med = median(vals)
    mad = median([abs(v - med) for v in vals])
    if mad and mad > 0:
        return mad * 1.4826
    return sd(vals)


def robust_z(value: float | None, reference: Sequence[float]) -> float | None:
    if value is None:
        return None
    vals = finite(reference)
    if len(vals) < 3:
        return None
    sigma = mad_sigma(vals)
    if not sigma:
        return 0.0
    return (float(value) - median(vals)) / sigma


def cv_pct(values: Sequence[float]) -> float | None:
    vals = finite(values)
    m = mean(vals)
    s = sd(vals)
    if m in (None, 0) or s is None:
        return None
    return 100.0 * s / m


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ewma(series: Sequence[float], days: int, seed: float | None = None) -> list[float]:
    """Media exponencial al estilo ATL/CTL (constante de tiempo ``days``).

    ``seed`` evita el sesgo de arranque desde cero (sin él, una carga constante
    tarda ~3 constantes de tiempo en reflejarse)."""
    k = 1 - math.exp(-1.0 / days)
    out, acc = [], (seed or 0.0)
    for v in series:
        acc = acc + k * ((v or 0.0) - acc)
        out.append(acc)
    return out


def r(value, digits: int = 1):
    return None if value is None else round(float(value), digits)
