"""Días de descanso confirmados por el atleta (V8.14). Puro (sin reloj ni red).

Los días vienen de `descansos_registro.json` (lo que el atleta dice en el chat: «hoy descanso»). Solo así un día sin
sesiones cuenta como descanso: un día sin registro sigue sin demostrar nada. Si un día confirmado tiene sesiones
sincronizadas, se marca como conflicto y no cuenta como descanso.
"""
from __future__ import annotations

import json
from datetime import date as _date, timedelta
from pathlib import Path

FILE = "descansos_registro.json"


def load(root: str | Path) -> dict | None:
    p = Path(root) / FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None  # una lista o un texto por error de edición no rompe la cadena


def confirmed(registro: dict | None, today: str) -> dict[str, dict]:
    """Fecha → entrada, solo fechas válidas que no son futuras."""
    out = {}
    entries = registro.get("entries") if isinstance(registro, dict) else None
    for e in entries if isinstance(entries, list) else []:
        if not isinstance(e, dict):
            continue
        d = str(e.get("date") or "")[:10]
        try:
            _date.fromisoformat(d)
        except ValueError:
            continue
        if d <= today:
            out[d] = e
    return out


def annotate(series: list[dict], registro: dict | None, today: str) -> list[dict]:
    """Añade `rest_confirmed` (True/False) a cada día de la tendencia; un día con sesiones nunca es descanso."""
    days = confirmed(registro, today)
    for row in series or []:
        if isinstance(row, dict):
            row["rest_confirmed"] = row.get("date") in days and not (row.get("sessions") or 0)
    return series


def summary(registro: dict | None, today: str, sessions: list[dict] | None = None) -> dict:
    """Descansos confirmados en 7 y 28 días y fechas confirmadas que tienen sesiones (conflictos)."""
    days = confirmed(registro, today)
    with_sessions = {s.get("date") for s in sessions or [] if isinstance(s, dict) and not s.get("removed")}
    t = _date.fromisoformat(today)
    since7, since28 = (t - timedelta(days=6)).isoformat(), (t - timedelta(days=27)).isoformat()
    ok = sorted(d for d in days if d not in with_sessions)
    return {"source": FILE, "dates_28d": [d for d in ok if d >= since28],
            "last7": sum(1 for d in ok if d >= since7), "last28": sum(1 for d in ok if d >= since28),
            "today": today in ok, "conflicts": sorted(d for d in days if d in with_sessions and d >= since28),
            "note": "Solo cuentan los días que el atleta confirma; un día sin registro no demuestra descanso."}
