#!/usr/bin/env python3
"""V5.1 - Avisa a la rutina de Claude cuando la cadena termina, para que redacte el informe.

Se ejecuta como ÚLTIMO paso de CrossFit Insights (cadena completa en verde).
Es opcional y nunca bloquea: sin los secretos CLAUDE_ROUTINE_URL y
CLAUDE_ROUTINE_TOKEN no hace nada y termina con código 0.

El texto enviado es solo contexto del ciclo (ID, commit, hora); la rutina
lee los datos directamente del repositorio.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BETA_HEADER = "experimental-cc-routine-2026-04-01"
TZ = ZoneInfo("Europe/Madrid")


def build_text(root: Path, env: dict) -> str:
    try:
        ready = json.loads((root / "report_ready.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        ready = {}
    lines = [
        "Cadena Garmin Recovery completada (Sync → Heart → Advanced → CrossFit).",
        f"cycle_id: {ready.get('cycle_id') or 'sin_ciclo_programado'}",
        f"report_ready.status: {ready.get('status') or 'desconocido'}",
        f"commit: {env.get('GITHUB_SHA', 'desconocido')}",
        f"crossfit_run_id: {env.get('GITHUB_RUN_ID', 'desconocido')}",
        f"finalizado: {datetime.now(TZ).isoformat(timespec='seconds')}",
    ]
    return "\n".join(lines)


def main(env: dict | None = None, root: Path | None = None, opener=urllib.request.urlopen) -> int:
    env = dict(os.environ if env is None else env)
    root = root or Path(".")
    url = (env.get("CLAUDE_ROUTINE_URL") or "").strip()
    token = (env.get("CLAUDE_ROUTINE_TOKEN") or "").strip()
    if not url or not token:
        print("Rutina de Claude no configurada (faltan secretos): no se envía aviso.")
        return 0
    if not url.startswith("https://api.anthropic.com/") or not url.rstrip("/").endswith("/fire"):
        print("CLAUDE_ROUTINE_URL no parece un endpoint /fire de rutina; no se envía.", file=sys.stderr)
        return 1
    body = json.dumps({"text": build_text(root, env)}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "anthropic-beta": BETA_HEADER,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
        "User-Agent": "Garmin-Recovery-Routine-Notify/5.1",
    })
    try:
        with opener(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        print(f"La rutina respondió HTTP {exc.code}; el informe no se lanzó.", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"No se pudo avisar a la rutina: {type(exc).__name__}", file=sys.stderr)
        return 1
    # Solo se registra el ID de sesión (acuse de lanzamiento), nunca el token.
    print("Informe lanzado. Sesión:", data.get("claude_code_session_id", "sin_id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
