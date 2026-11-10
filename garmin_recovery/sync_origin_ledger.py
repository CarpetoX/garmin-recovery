"""Registro de Syncs cuyo origen se verificó (V8.15).

El Sync de cada franja lo lanza Apps Script con `workflow_dispatch` firmado (HMAC). `dispatch_auth` lo verifica dentro
del propio run, pero la API de ejecuciones de GitHub no expone esa verificación: el monitor solo ve «workflow_dispatch»
y no podía distinguir Apps Script de un lanzamiento sin firmar, así que marcaba cada franja como «recuperada a mano»
(aviso) aunque se hubiera disparado a su hora. Este registro guarda, por `run_id`, el resultado de la verificación para
que el monitor lo use. Solo se anotan runs verificados; nada se infiere del tipo de evento.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

FILE = "sync_origin_ledger.json"
KEEP_DAYS = 30


def load(path: str | Path = FILE) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"runs": []}
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        return {"runs": []}
    return data


def verified_run_ids(data: dict | None) -> set[str]:
    """IDs de Sync con origen Apps Script verificado por HMAC."""
    out = set()
    for r in (data or {}).get("runs") or []:
        if isinstance(r, dict) and r.get("verified") is True and r.get("origin_source") == "apps_script_backup":
            out.add(str(r.get("run_id")))
    return out


def record(origin: dict, run_id: str, now: datetime, path: str | Path = FILE) -> bool:
    """Añade el run si su origen está verificado; poda entradas de más de KEEP_DAYS. Devuelve si escribió."""
    if not (isinstance(origin, dict) and origin.get("source_verified") is True
            and origin.get("origin_source") == "apps_script_backup" and str(run_id).strip()):
        return False
    data = load(path)
    cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
    runs = [r for r in data["runs"] if isinstance(r, dict) and str(r.get("recorded_at", "")) >= cutoff
            and str(r.get("run_id")) != str(run_id)]
    runs.append({"run_id": str(run_id), "verified": True, "origin_source": "apps_script_backup",
                 "auth_method": origin.get("auth_method"), "cycle_id": origin.get("cycle_id"),
                 "requested_at": origin.get("requested_at"), "recorded_at": now.isoformat()})
    out = {"schema_version": 1, "note": ("Syncs cuyo origen Apps Script se verificó por HMAC dentro del run. "
                                          "Un run ausente no está verificado; no se deduce nada del tipo de evento."),
           "runs": sorted(runs, key=lambda r: r["recorded_at"])}
    Path(path).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def from_lineage(path: str | Path) -> tuple[dict | None, str]:
    """(origen verificado, run_id) del Sync raíz según la filiación de la cadena; (None, "") si no consta."""
    try:
        lin = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, ""
    root = lin.get("root") if isinstance(lin, dict) else None
    if not isinstance(root, dict):
        return None, ""
    origin = root.get("origin_v291") if isinstance(root.get("origin_v291"), dict) else None
    return origin, str(root.get("run_id") or "")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--origin-file", default=".garmin_origin_v291.json")
    p.add_argument("--out", default=FILE)
    p.add_argument("--from-lineage", default=None,
                   help="V8.16: filiación de la cadena; anota el Sync raíz desde el paso CrossFit, sin commit propio en el Sync")
    a = p.parse_args(argv)
    if a.from_lineage:
        origin, run_id = from_lineage(a.from_lineage)
    else:
        try:
            origin = json.loads(Path(a.origin_file).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            origin = None
        run_id = os.environ.get("GITHUB_RUN_ID", "")
    wrote = record(origin, run_id, datetime.now(timezone.utc), a.out)
    print(json.dumps({"sync_origin_ledger": "recorded" if wrote else "not_verified_skipped"}))


if __name__ == "__main__":
    main()
