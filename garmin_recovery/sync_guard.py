"""¿Hace falta el Sync de respaldo del cron de GitHub? (V8.6)

El cron «30 8» de GitHub es solo un respaldo del Apps Script y llega siempre tarde (entre las 12:20 y las 15:30 en
octubre de 2026). Si para entonces el ciclo de las 08:30 de hoy ya está certificado, ese Sync no aporta nada y su
cadena solo gasta minutos (y el 27/10 acabó en un certificado fallido). Este control, solo para el evento
``schedule``, responde ``skip=true`` en ese caso; el workflow cancela entonces su propia ejecución para que la
cadena no arranque. Ante cualquier duda (archivo ilegible, sin ciclo de hoy) se sincroniza.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")


def morning_certified(cycles: dict, today: str) -> str | None:
    for c in (cycles or {}).get("cycles") or []:
        cid = str((c or {}).get("cycle_id") or "") if isinstance(c, dict) else ""
        if cid.startswith(f"{today}-0830"):
            return cid
    return None


def decide(event: str, root: Path, now: datetime) -> dict:
    if event != "schedule":
        return {"skip": False, "reason": f"evento {event or 'desconocido'}: se sincroniza siempre"}
    try:
        cycles = json.loads((root / "report_cycles.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"skip": False, "reason": "report_cycles.json ilegible: se sincroniza por si acaso"}
    today = now.astimezone(TZ).date().isoformat()
    cid = morning_certified(cycles, today)
    if cid:
        return {"skip": True, "cycle_id": cid,
                "reason": f"el ciclo {cid} ya está certificado: el Sync de respaldo del cron no hace falta"}
    return {"skip": False, "reason": "el ciclo de las 08:30 de hoy no consta: el respaldo sincroniza"}


def main() -> int:
    out = decide(os.environ.get("GITHUB_EVENT_NAME", ""), Path("."), datetime.now(TZ))
    level = "notice" if out["skip"] else "debug"
    if out["skip"]:
        print(f"::{level} title=Sync de respaldo innecesario::{out['reason']}")
    print(json.dumps(out, ensure_ascii=False))
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"skip={'true' if out['skip'] else 'false'}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
