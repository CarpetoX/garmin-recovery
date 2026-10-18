"""Descarga resistente de Intervals.icu: reintentos, clasificación del fallo y estado publicado.

Un fallo pasajero (429, 5xx, red) se reintenta; si persiste y ya hay datos previos, la cadena sigue con
ellos y el fallo queda en ``intervals_status.json`` (el aviso salta tras varios fallos seguidos). Un fallo de
acceso (401/403) nunca se reintenta. Sin datos previos, el error se propaga como antes.
"""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
STATUS = "intervals_status.json"
RETRIES = 3
BACKOFF = (2, 6)  # segundos entre intentos


class IngestError(Exception):
    def __init__(self, kind: str, message: str, http: int | None = None):
        super().__init__(message)
        self.kind, self.http = kind, http


def classify(exc: Exception) -> tuple[str, int | None]:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code in (401, 403):
            return "auth", exc.code
        if exc.code == 429:
            return "rate_limit", exc.code
        if exc.code >= 500:
            return "server", exc.code
        return "client", exc.code
    if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)):
        return "network", None
    if isinstance(exc, (ValueError, json.JSONDecodeError)):
        return "schema", None
    return "unknown", None


def fetch_json(url: str, key: str, retries: int = RETRIES, sleep=None):
    auth = base64.b64encode(f"API_KEY:{key}".encode()).decode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"Authorization": "Basic " + auth, "Accept": "application/json",
                                                   "User-Agent": "Garmin-Recovery-Sync/3.1"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode()
            return json.loads(body) if body else []
        except Exception as exc:  # noqa: BLE001 - se clasifica y se relanza como IngestError
            kind, http = classify(exc)
            last = IngestError(kind, f"{type(exc).__name__}: {str(exc)[:140]}", http)
            if kind in ("auth", "client", "schema") or attempt == retries - 1:
                break
            (sleep or time.sleep)(BACKOFF[min(attempt, len(BACKOFF) - 1)])
    raise last


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def write_status(source: str, ok: bool, error: IngestError | None = None, newest: str | None = None,
                 root: Path = Path("."), now: datetime | None = None) -> dict:
    path = Path(root) / STATUS
    data = _read(path)
    now = (now or datetime.now(TZ)).isoformat(timespec="seconds")
    prev = data.get(source) if isinstance(data.get(source), dict) else {}
    if ok:
        entry = {"status": "ok", "last_ok_at": now, "consecutive_failures": 0, "newest_date": newest}
    else:
        entry = {"status": "error", "kind": error.kind if error else "unknown", "http": error.http if error else None,
                 "message": str(error)[:160] if error else "", "last_ok_at": prev.get("last_ok_at"),
                 "last_error_at": now, "consecutive_failures": int(prev.get("consecutive_failures") or 0) + 1,
                 "newest_date": prev.get("newest_date")}
    data[source] = entry
    data["generated_at"] = now
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return entry


def newest_date(rows, field: str) -> str | None:
    vals = [str(r.get(field) or "")[:10] for r in rows if isinstance(r, dict) and r.get(field)]
    return max(vals) if vals else None


TRANSIENT = ("rate_limit", "server", "network")


def fetch_or_keep(source: str, url: str, key: str, previous_file: str, root: Path = Path(".")):
    """Datos nuevos, o ``None`` si el fallo es pasajero y hay datos previos que conservar.

    Los fallos de acceso (401/403) o de petición no se toleran: se anotan y se relanzan para que la cadena
    falle y salte el aviso de inmediato.
    """
    try:
        return fetch_json(url, key)
    except IngestError as err:
        write_status(source, False, err, root=root)
        if err.kind in TRANSIENT and (Path(root) / previous_file).exists():
            print(f"AVISO {source}: {err.kind} ({err.http or '-'}); se conservan los datos previos de {previous_file}")
            return None
        raise
