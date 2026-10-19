"""Franja de turnos de hoy y mañana (V7.13). Módulo puro: recibe el calendario y la fecha; no lee reloj ni red."""
from __future__ import annotations

from datetime import date, timedelta

from .shift_calendar import HOURS, primary_shift


def _h(text: str) -> float:
    hh, mm = text.split(":")
    return int(hh) + int(mm) / 60


def _blocks(day: date, cal: dict) -> list[dict]:
    """Bloques [inicio, fin) en horas desde las 00:00 de `day`; el turno de noche de ayer entra por la izquierda."""
    out = []
    prev, _ = primary_shift(day - timedelta(days=1), cal)
    if prev == "TN":
        out.append({"code": "TN", "start": 0.0, "end": _h(HOURS["TN"]["end"])})
    cur, _ = primary_shift(day, cal)
    if cur in HOURS:
        h = HOURS[cur]
        end = _h(h["end"]) + 24 * h["end_day_offset"]
        out.append({"code": cur, "start": _h(h["start"]), "end": min(end, 24.0)})
    return out


def _free(blocks: list[dict]) -> list[tuple[float, float]]:
    gaps, t = [], 0.0
    for b in sorted(blocks, key=lambda x: x["start"]):
        if b["start"] - t >= 1:
            gaps.append((t, b["start"]))
        t = max(t, b["end"])
    if 24 - t >= 1:
        gaps.append((t, 24.0))
    return gaps


def compute(cal: dict, today: str, now_hour: float | None = None) -> dict:
    """Dos filas (hoy y mañana) con sus bloques y huecos libres. `unknown` si el día no consta en el calendario."""
    d0 = date.fromisoformat(today[:10])
    rows = []
    for i, label in enumerate(("Hoy", "Mañana")):
        day = d0 + timedelta(days=i)
        code, _ = primary_shift(day, cal)
        blocks = _blocks(day, cal)
        rows.append({"label": label, "date": day.isoformat(), "code": code, "known": code != "unknown",
                     "blocks": blocks, "free": _free(blocks) if code != "unknown" else [],
                     "now": now_hour if (i == 0 and now_hour is not None) else None})
    return {"rows": rows, "available": any(r["known"] for r in rows)}
