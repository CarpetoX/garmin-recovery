"""¿Hay algo nuevo que publicar? (V8.4)

Tras el sueño, el Apps Script repite el Sync cada ~65 min hasta que se confirma (≈ 10 cadenas al día en vez de 3).
Cada cadena lanzaba después el monitor, una publicación de la web y la rutina de Claude aunque nada hubiera cambiado.
Este paso compara la «huella» de lo que ves en la app con la de la última publicación y solo deja seguir si cambió
o si este ciclo escribió un certificado nuevo. Ante cualquier duda o error, publica (falla abierto).

Uso en el workflow: ``python -m garmin_recovery.publish_gate`` escribe ``publish_gate.json`` y la salida
``publish=true|false`` en ``$GITHUB_OUTPUT``.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE = Path("publish_gate.json")
NEW_CERT_MINUTES = 20


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def fingerprint(root: Path) -> dict:
    """Lo que cambia lo que ves: decisión, puntuación, sueño, ciclo y sesiones con su RPE (últimos 3 días)."""
    r = _read(root / "app" / "readiness_v3.json")
    rd, dec = r.get("readiness") or {}, r.get("decision") or {}
    sleep = _read(root / "morning_sleep_status.json")
    ready = _read(root / "report_ready.json")
    today = str(r.get("date") or "")
    try:
        since = (datetime.fromisoformat(today) - timedelta(days=2)).date().isoformat()
    except ValueError:
        since = ""
    sessions = sorted((str(s.get("id")), s.get("rpe"), bool(s.get("rpe_na"))) for s in r.get("sessions_28d") or []
                      if isinstance(s, dict) and str(s.get("date") or "") >= since)
    # El análisis de Claude no entra: su propio push ya vuelve a publicar la web.
    return {"date": today, "zone": dec.get("zone"), "state": rd.get("state"), "score": rd.get("score"),
            "sleep": [sleep.get("state"), sleep.get("is_definitive"), sleep.get("sleep_end_local")],
            "cycle": ready.get("cycle_id"), "sessions": sessions}


def digest(fp: dict) -> str:
    return hashlib.sha256(json.dumps(fp, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def decide(root: Path, now: datetime) -> dict:
    fp = fingerprint(root)
    h = digest(fp)
    prev = _read(root / STATE)
    ready = _read(root / "report_ready.json")
    new_cert = False
    try:
        va = datetime.fromisoformat(str(ready.get("verified_at")))
        new_cert = timedelta(0) <= now - va <= timedelta(minutes=NEW_CERT_MINUTES)
    except (TypeError, ValueError):
        pass
    changed = h != prev.get("published_digest")
    publish = bool(new_cert or changed)
    reason = "certificado nuevo" if new_cert else "datos cambiados" if changed else "sin cambios desde la última publicación"
    return {"publish": publish, "reason": reason, "digest": h, "previous_digest": prev.get("published_digest"),
            "checked_at": now.isoformat(), "fingerprint": fp,
            "published_digest": h if publish else prev.get("published_digest"),
            "published_at": now.isoformat() if publish else prev.get("published_at")}


def main(root: str | Path = ".") -> int:
    root = Path(root)
    now = datetime.now(timezone.utc).astimezone()
    try:
        out = decide(root, now)
    except Exception as exc:  # noqa: BLE001 — falla abierto: ante la duda, se publica
        out = {"publish": True, "reason": f"error en el control ({type(exc).__name__}): se publica", "checked_at": now.isoformat()}
        print(f"::warning title=Control de publicación::{type(exc).__name__}: {exc}")
    (root / STATE).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"publish={'true' if out['publish'] else 'false'}\n")
    print(json.dumps({"publish": out["publish"], "reason": out["reason"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
