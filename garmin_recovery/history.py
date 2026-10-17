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
        for field, value in row.items():
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


def recompute_daily_load(daily: dict, sessions: dict) -> dict:
    """La carga diaria se deriva siempre del historial completo de sesiones."""
    from .records import aggregate_sessions
    agg = aggregate_sessions(sessions.values())
    for day, values in agg.items():
        row = daily.setdefault(day, {f: None for f in DAILY_FIELDS} | {"date": day})
        row.update(values)
    return daily
