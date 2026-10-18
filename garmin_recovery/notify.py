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
from datetime import datetime, timedelta
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


def night_shift_tip(root: Path, result: dict, now: datetime) -> str | None:
    """Consejo de sueño antes de un turno de noche (TN), sin cifras fisiológicas en el aviso.

    Solo si hoy hay TN y aún no ha empezado (15:00). La condición usa internamente la deuda de sueño
    reciente; el texto no la expone.
    """
    trend = result.get("trend_28d") or []
    today = result.get("date") or now.date().isoformat()
    row = next((t for t in reversed(trend) if isinstance(t, dict) and t.get("date") == today), None)
    if not row or row.get("shift") != "TN" or now.hour >= 15:
        return None
    from . import sleep_need
    from .config import DEFAULTS
    ext = _read(root / "garmin_extended.json").get("days")
    need = sleep_need.compute(trend, ext if isinstance(ext, dict) else {}, today, DEFAULTS["sleep_need_hours"])
    debt = need.get("debt_7n_h") if need.get("available") else None
    short = (row.get("sleep_hours") or 99) < DEFAULTS["sleep_need_hours"] - 1
    if short or (debt is not None and debt >= 3):
        return "Hoy TN: valora una siesta de 20–90 min antes de las 15:00 y evita cargas altas antes del turno."
    return "Hoy TN: si entrenas, que sea antes del mediodía y deja margen para descansar antes del turno."


def rpe_pending_tip(result: dict, now: datetime) -> str | None:
    """Aviso de sesiones sin RPE: las de hoy a partir de las 12:00; antes, las de ayer. Sin cifras fisiológicas."""
    today = result.get("date") or now.date().isoformat()
    day = today if now.hour >= 12 else (datetime.fromisoformat(today) - timedelta(days=1)).date().isoformat()
    pending = [x for x in result.get("sessions_28d") or []
               if isinstance(x, dict) and x.get("date") == day and x.get("rpe") is None and not x.get("removed")]
    if not pending:
        return None
    n = len(pending)
    when = "de hoy" if day == today else "de ayer"
    cierre = "antes del cierre de las 22:45" if day == today else "para que entre en el informe"
    return f"{n} {'sesiones' if n > 1 else 'sesión'} {when} sin RPE: cuéntamelo {cierre}."


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
    try:
        tip = night_shift_tip(root, result, now)
    except Exception:  # noqa: BLE001 — el consejo es opcional
        tip = None
    if tip:
        body += "\n" + tip
    try:
        pend = rpe_pending_tip(result, now)
    except Exception:  # noqa: BLE001 — opcional
        pend = None
    if pend:
        body += "\n" + pend
    return {"title": "Informe nuevo · " + now.strftime("%H:%M"), "message": body,
            "priority": priority, "tags": [tag], "click": SITE_URL + "informe_completo.html"}


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
