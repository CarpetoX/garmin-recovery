"""Historial persistente en CSV (diffable, sin binarios en Git).

Las fuentes de la cadena guardan ventanas móviles de 14–30 días; para tener
líneas base de 60 días y carga crónica hace falta acumular. Política:

* ``upsert`` por clave (fecha o ID de actividad); nunca se borran filas.
* Un valor nuevo no nulo sustituye al anterior; un nulo nunca borra un dato.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .records import DAILY_FIELDS, SESSION_FIELDS, TEXT_FIELDS, num


def _typed(row: dict, fields: list[str]) -> dict:
    out = {}
    for f in fields:
        raw = row.get(f)
        if raw in (None, ""):
            out[f] = None
        elif f in TEXT_FIELDS:
            out[f] = raw
        else:
            value = num(raw)
            out[f] = int(value) if value is not None and f in ("sessions", "rpe_sessions") else value
    return out


def read_table(path: Path, fields: list[str], key: str) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [_typed(r, fields) for r in csv.DictReader(fh)]
    return {r[key]: r for r in rows if r.get(key)}


def merge(existing: dict, fresh: dict) -> dict:
    out = {k: dict(v) for k, v in existing.items()}
    for key, row in fresh.items():
        target = out.setdefault(key, {})
        for field in row.get("_clear") or ():  # vaciado explícito y declarado (V7.20: sesión sin RPE a propósito)
            target[field] = None
        for field, value in row.items():
            if field == "_clear":
                continue
            if value is not None:
                target[field] = value
            else:
                target.setdefault(field, None)
    return out


def _fmt(value):
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if value != int(value) else str(int(value))
    return str(value)


def write_table(path: Path, table: dict, fields: list[str], key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for k in sorted(table):
            writer.writerow({f: _fmt(table[k].get(f)) for f in fields})
    tmp.replace(path)


def update_history(history_dir: str | Path, day_records: dict, sessions: list[dict],
                   write: bool = True) -> tuple[dict, dict]:
    hdir = Path(history_dir)
    daily_path, sess_path = hdir / "daily.csv", hdir / "sessions.csv"
    daily = merge(read_table(daily_path, DAILY_FIELDS, "date"), day_records)
    sess = merge(read_table(sess_path, SESSION_FIELDS, "id"), {s["id"]: s for s in sessions})
    if write:
        write_table(daily_path, daily, DAILY_FIELDS, "date")
        write_table(sess_path, sess, SESSION_FIELDS, "id")
    return daily, sess


def flag_removed_sessions(sessions: dict, fresh: list[dict]) -> dict:
    """Marca como eliminadas las sesiones que faltan en la fuente dentro de su ventana.

    No se borra ninguna fila (política del repo). Se ignora el día más antiguo de la
    ventana por si la fuente lo trae incompleto; si la fuente viene vacía no se marca nada."""
    dates = sorted(s["date"] for s in fresh if s.get("date"))
    if not dates:
        return sessions
    fresh_ids = {s["id"] for s in fresh}
    for sid, s in sessions.items():
        if sid in fresh_ids:
            s["removed"] = 0
        elif (s.get("date") or "") > dates[0]:
            s["removed"] = 1
    return sessions


def recompute_daily_load(daily: dict, sessions: dict) -> dict:
    """La carga diaria se deriva siempre del historial completo de sesiones."""
    from .records import aggregate_sessions
    agg = aggregate_sessions(s for s in sessions.values() if not s.get("removed"))
    keys = ("sessions", "duration_min", "load", "srpe", "rpe_sessions")
    for row in daily.values():  # un día cuyas sesiones se eliminaron no conserva carga antigua
        for k in keys:
            row[k] = None
    for day, values in agg.items():
        row = daily.setdefault(day, {f: None for f in DAILY_FIELDS} | {"date": day})
        row.update(values)
    return daily
