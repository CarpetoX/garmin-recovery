"""Caducidad del acceso a Garmin (secreto GARMIN_TOKENS_B64) sin exponer el token.

Busca en el JSON del secreto fechas de caducidad: claims `exp` de cualquier JWT y campos numéricos cuyo nombre
indique caducidad (``expires_at``, ``expiration``…). Solo se devuelve la fecha más próxima y los días que
faltan; jamás el contenido. Si no encuentra ninguna, lo indica (no es un fallo).
"""
from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime, timezone

EXPIRY_HINTS = ("expires_at", "expire_at", "expiration", "expiry", "exp")


def _jwt_exp(value):
    if not isinstance(value, str) or value.count(".") != 2:
        return None
    try:
        payload = value.split(".")[1]
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return None
    exp = data.get("exp") if isinstance(data, dict) else None
    return exp if isinstance(exp, (int, float)) and not isinstance(exp, bool) else None


def _walk(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and str(k).lower() in EXPIRY_HINTS:
                found.append(float(v))
            else:
                _walk(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _walk(v, found)
    elif isinstance(obj, str):
        exp = _jwt_exp(obj)
        if exp is not None:
            found.append(float(exp))


def inspect(token_b64: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    try:
        obj = json.loads(base64.b64decode(token_b64, validate=True).decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeDecodeError):
        return {"state": "unreadable"}
    found: list[float] = []
    _walk(obj, found)
    stamps = []
    for v in found:
        v = v / 1000 if v > 1e11 else v          # milisegundos → segundos
        if 1e9 < v < 4e9:                        # descarta duraciones (p. ej. expires_in = 3600)
            stamps.append(v)
    if not stamps:
        return {"state": "no_expiry_found"}
    # la caducidad que importa es la del último elemento que se puede renovar: el mayor de los hallados
    # solo avisa el más lejano, porque los tokens de acceso cortos se renuevan solos
    latest = datetime.fromtimestamp(max(stamps), timezone.utc)
    days = (latest - now).total_seconds() / 86400
    return {"state": "expired" if days < 0 else "ok", "latest_expiry": latest.date().isoformat(), "days_left": round(days, 1)}
