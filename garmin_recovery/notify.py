"""Aviso al móvil (ntfy) cuando hay un informe nuevo publicado.

Solo se envía si hay un tema configurado (secreto ``NTFY_TOPIC``), el informe pasó la validación y
es de este ciclo (generado hace menos de ``max_age_min`` minutos): una ejecución que no publicó nada
nuevo no repite el aviso del informe anterior. El mensaje lleva solo la decisión y el enlace al panel,
nunca datos fisiológicos. Nunca bloquea la cadena.
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
SITE_URL = "https://carpetox.github.io/garmin-recovery/"
LOOK = {"red": (4, "red_circle"), "yellow": (3, "yellow_circle"), "green": (3, "green_circle")}


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def build_message(root: Path, now: datetime | None = None, max_age_min: float = 90) -> dict | None:
    """Mensaje a enviar o ``None`` si no hay informe nuevo y válido."""
    root, now = Path(root), (now or datetime.now(TZ)).astimezone(TZ)
    result, val = _read(root / "app" / "readiness_v3.json"), _read(root / "app" / "validation.json")
    if not result or val.get("status") == "failed":
        return None
    try:
        age = (now - datetime.fromisoformat(str(result.get("generated_at"))).astimezone(TZ)).total_seconds() / 60
    except (TypeError, ValueError):
        return None
    if not 0 <= age <= max_age_min:
        return None
    dec = result.get("decision") or {}
    zone = dec.get("zone") or "unavailable"
    priority, tag = LOOK.get(zone, (2, "white_circle"))
    label = (dec.get("guidance") or {}).get("label") or dec.get("zone_es") or "Informe disponible"
    rpe = (dec.get("guidance") or {}).get("rpe_max")
    body = label + (f" · RPE máx. {rpe}" if rpe is not None else "")
    return {"title": "Informe nuevo · " + now.strftime("%H:%M"), "message": body,
            "priority": priority, "tags": [tag], "click": SITE_URL}


def send(msg: dict, topic: str, server: str = "https://ntfy.sh", opener=urllib.request.urlopen) -> int:
    body = json.dumps({"topic": topic, **msg}, ensure_ascii=False).encode()
    req = urllib.request.Request(server.rstrip("/"), data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    with opener(req, timeout=15) as r:
        return r.status


def main(root: str = ".") -> int:
    topic = (os.environ.get("NTFY_TOPIC") or "").strip()
    if not topic:
        print(json.dumps({"notify": "sin_tema"}))
        return 0
    try:
        msg = build_message(Path(root))
        if msg is None:
            print(json.dumps({"notify": "sin_informe_nuevo"}))
            return 0
        status = send(msg, topic, os.environ.get("NTFY_SERVER") or "https://ntfy.sh")
        print(json.dumps({"notify": "enviado", "http": status}))
    except Exception as exc:  # noqa: BLE001 — un aviso nunca bloquea la cadena
        print(json.dumps({"notify": "error", "detail": f"{type(exc).__name__}"}))
    return 0
