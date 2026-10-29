"""Tramos dentro de una misma actividad de Garmin (V8.10).

Cuando el reloj graba dos partes en una sola actividad (p. ej. técnica y después un WOD), cada parte va en
su propia fila de la hoja con el mismo ID y, en el Detalle JSON, ``"segment": {"start_s": 2420, "end_s": 2656}``
(segundos desde el inicio de la actividad de Garmin). Así:

* el sRPE se calcula solo con los tramos que tienen RPE (RPE × minutos del tramo), no con toda la grabación;
* la tarjeta del metcon muestra los minutos y la FC de su tramo;
* el ID repetido no se avisa como duplicado, porque es intencionado.
"""
from __future__ import annotations

import json


def _num(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip():
        try:
            return float(v.strip().replace(",", "."))
        except ValueError:
            return None
    return None


def _detail(d):
    if isinstance(d, str) and d.strip():
        try:
            d = json.loads(d)
        except ValueError:
            return {}
    return d if isinstance(d, dict) else {}


def segment(detail) -> tuple[float, float] | None:
    """(inicio, fin) en segundos si el detalle declara un tramo válido."""
    seg = _detail(detail).get("segment")
    if not isinstance(seg, dict):
        return None
    a, b = _num(seg.get("start_s")), _num(seg.get("end_s"))
    if a is None or b is None or a < 0 or b <= a:
        return None
    return a, b


def scored_seconds(blocks) -> float | None:
    """Segundos con RPE cuando la actividad está dividida en tramos.

    ``blocks``: pares (rpe, detalle). Devuelve ``None`` (usar la duración grabada) si no hay tramos o si
    algún bloque con RPE no declara el suyo.
    """
    blocks = [(_num(r), _detail(d)) for r, d in blocks or []]
    if not any(segment(d) for _, d in blocks):
        return None
    scored = [(r, segment(d)) for r, d in blocks if r is not None]
    if not scored or any(s is None for _, s in scored):
        return None
    return sum(b - a for _, (a, b) in scored)


def scored_seconds_from_rows(rows, activity_id) -> float | None:
    """Igual que ``scored_seconds`` a partir de las filas A–H de la hoja (``source_rows_AH``)."""
    aid = str(activity_id)
    blocks = [(r.get("RPE"), r.get("Detalle JSON")) for r in rows or []
              if isinstance(r, dict) and str(r.get("ID actividad") or "").strip() == aid]
    return scored_seconds(blocks)


def split_ids(rows) -> set[str]:
    """IDs con varias filas en la hoja y todas con tramo declarado: duplicado intencionado."""
    by: dict[str, list] = {}
    for r in rows or []:
        if isinstance(r, dict) and str(r.get("ID actividad") or "").strip():
            by.setdefault(str(r["ID actividad"]).strip(), []).append(r)
    return {k for k, v in by.items() if len(v) > 1 and all(segment(r.get("Detalle JSON")) for r in v)}


def hr_in(curve: dict | None, start: float, end: float) -> dict | None:
    """FC media y máxima del tramo a partir de la curva de Intervals ([[segundo, lpm], …])."""
    pts = (curve or {}).get("points") if isinstance(curve, dict) else None
    vals = [p[1] for p in pts or [] if isinstance(p, (list, tuple)) and len(p) >= 2
            and isinstance(p[0], (int, float)) and isinstance(p[1], (int, float)) and start <= p[0] <= end]
    if len(vals) < 3:
        return None
    return {"average": sum(vals) / len(vals), "max": max(vals)}


def mmss(seconds) -> str:
    s = int(round(seconds))
    return f"{s // 60}:{s % 60:02d}"
