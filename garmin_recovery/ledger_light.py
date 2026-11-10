"""Copias ligeras del registro de ciclos para cualquier lector (V8.9).

``report_cycles.json`` es el original completo y sin pérdidas (``ledger_safety`` impide descartar certificados), pero ya
pesa varios MB y la API de GitHub no devuelve el contenido de archivos de más de 1 MB: herramientas como ChatGPT lo
leen como vacío. Este paso, que solo LEE el original, escribe al lado dos archivos pequeños:

* ``report_cycles_recent.json``: los ciclos de las últimas ``RECENT_HOURS`` horas, completos (con su instantánea
  inmutable y su ``snapshot_sha256``), recortados para quedar por debajo de ``MAX_BYTES``.
* ``report_cycles_index.json``: todos los ciclos sin la instantánea (ID, horas, estado, huella), para saber qué hay.

Antes de copiar, cada instantánea se verifica contra su huella. Si el original es ilegible o una huella no cuadra,
no se escribe nada y sale con 0 (nunca rompe la cadena). La huella es SHA-256 del JSON canónico de ``snapshot``
(claves ordenadas, separadores «,» y «:», UTF-8 sin escapar).
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from .archive_report_cycles import digest

RECENT_HOURS = 72
MAX_BYTES = 900_000  # por debajo del límite de 1 MB de la API de GitHub
INDEX_KEYS = ("cycle_id", "certificate_kind", "parent_cycle_id", "slot_at", "ready_at", "target_report_at", "state",
              "recovery_state", "recovery_confidence", "sync_run_id", "crossfit_run_id", "snapshot_sha256",
              "notification_delivery", "legacy_without_snapshot")
HOW_TO_VERIFY = ("snapshot_sha256 = SHA-256 del JSON canónico de «snapshot»: json.dumps(snapshot, ensure_ascii=False, "
                 "sort_keys=True, separators=(',', ':')) en UTF-8.")


def _when(row: dict):
    try:
        return datetime.fromisoformat(str(row.get("ready_at") or row.get("slot_at")))
    except (TypeError, ValueError):
        return None


def verify(row: dict) -> bool:
    snap = row.get("snapshot")
    return not isinstance(snap, dict) or digest(snap) == row.get("snapshot_sha256")


def build(ledger: dict, now: datetime) -> tuple[dict, dict]:
    rows = [r for r in (ledger or {}).get("cycles") or [] if isinstance(r, dict) and r.get("cycle_id")]
    bad = [r["cycle_id"] for r in rows if not verify(r)]
    if bad:
        raise ValueError("huella de instantánea que no cuadra: " + ", ".join(bad[:5]))
    rows.sort(key=lambda r: str(r.get("slot_at") or ""))
    source = {"file": "report_cycles.json", "count": len(rows), "cycles_digest_sha256": digest(rows),
              "first_cycle_id": rows[0]["cycle_id"] if rows else None, "last_cycle_id": rows[-1]["cycle_id"] if rows else None}
    meta = {"schema_version": 1, "generated_at": now.isoformat(), "source": source, "how_to_verify": HOW_TO_VERIFY,
            "note": "Copia de solo lectura; el original completo y sin pérdidas es report_cycles.json."}
    index = dict(meta, purpose="Índice de todos los ciclos certificados, sin las instantáneas",
                 cycles=[{k: r[k] for k in INDEX_KEYS if k in r} for r in rows])
    cut = now - timedelta(hours=RECENT_HOURS)
    recent = [r for r in rows if (_when(r) or now) >= cut] or rows[-1:]
    out = dict(meta, purpose=f"Ciclos certificados de las últimas {RECENT_HOURS} h, completos y con su instantánea",
               window_hours=RECENT_HOURS, cycles=recent)
    while len(out["cycles"]) > 1 and len(_dump(out)) > MAX_BYTES:  # nunca por encima de 1 MB: fuera los más antiguos
        out["cycles"] = out["cycles"][1:]
    out["count"] = len(out["cycles"])
    return out, index


def _dump(obj) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n").encode("utf-8")


def _write(path: Path, obj) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(_dump(obj))
        json.loads(Path(tmp).read_text(encoding="utf-8"))  # se relee antes de sustituir
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(root: str | Path = ".", now: datetime | None = None) -> int:
    root = Path(root)
    now = now or datetime.now().astimezone()
    try:
        ledger = json.loads((root / "report_cycles.json").read_text(encoding="utf-8"))
        recent, index = build(ledger, now)
        _write(root / "report_cycles_recent.json", recent)
        _write(root / "report_cycles_index.json", index)
        print(json.dumps({"recent": recent["count"], "index": len(index["cycles"]),
                          "recent_bytes": (root / "report_cycles_recent.json").stat().st_size,
                          "index_bytes": (root / "report_cycles_index.json").stat().st_size}))
    except Exception as exc:  # noqa: BLE001 — copia auxiliar: nunca rompe la cadena
        print(f"::warning title=Copias ligeras del registro no actualizadas::{type(exc).__name__}: {str(exc)[:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
