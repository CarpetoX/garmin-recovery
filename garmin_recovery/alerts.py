"""Avisos automáticos en GitHub (issue) cuando algo necesita atención.

Un único issue abierto a la vez («⚠️ Garmin Recovery: atención necesaria»):

* se abre si el informe del ciclo no se pudo publicar (validación fallida), si se ha
  perdido una franja de Sync en las últimas 12 h o si no hay informe nuevo en 11 h (el hueco normal 22:45→08:30 es de casi 10 h);
* si ya está abierto, solo comenta cuando cambia el problema (no repite avisos);
* se cierra solo, con un comentario, cuando todo vuelve a estar bien.

GitHub notifica los issues nuevos al propietario del repositorio (correo o app).
Nunca bloquea la cadena: cualquier error de red se registra y se ignora.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TITLE = "⚠️ Garmin Recovery: atención necesaria"
MARK = "<!-- garmin-alert:"


def problems(root: Path, now: datetime, stale_hours: float = 11, missed_hours: float = 12) -> list[dict]:
    root = Path(root)
    out: list[dict] = []
    try:
        val = json.loads((root / "app" / "validation.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        val = {}
    if val.get("status") == "failed":
        out.append({"key": "validation", "text": "El informe de este ciclo **no se publicó** porque no pasó la validación; "
                    "sigue visible el anterior. Motivos: " + "; ".join(str(e) for e in (val.get("errors") or [])[:5])})
    try:
        data = json.loads((root / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    gen = None
    try:
        gen = datetime.fromisoformat(str(data.get("generated_at")))
    except ValueError:
        pass
    if gen is None or (now - gen) > timedelta(hours=stale_hours):
        when = gen.astimezone(now.tzinfo).strftime("%d/%m %H:%M") if gen else "desconocido"
        out.append({"key": "stale", "text": f"No hay informe nuevo desde {when}. Revisa los activadores de Apps Script "
                    "y las ejecuciones de *Garmin Recovery Sync*."})
    missed = (((data.get("certificate") or {}).get("execution_health") or {}).get("missed_slots")) or []
    recent = []
    for s in missed:
        try:
            t = datetime.fromisoformat(s)
        except (TypeError, ValueError):
            continue
        if timedelta(0) <= now - t <= timedelta(hours=missed_hours):
            recent.append(t.astimezone(now.tzinfo).strftime("%d/%m %H:%M"))
    if recent:
        out.append({"key": "missed:" + ",".join(recent), "text": f"Franja(s) de Sync perdidas: {', '.join(recent)}. "
                    "Apps Script no lanzó el Sync o la cadena no terminó."})
    return out


def _api(method: str, path: str, token: str, body: dict | None = None):
    req = urllib.request.Request(
        "https://api.github.com" + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else None


def sync_issue(found: list[dict], repo: str, token: str, owner: str, api=None, run_url: str = "") -> str:
    """Abre, comenta o cierra el issue de aviso. Devuelve la acción realizada."""
    api = api or _api
    fingerprint = hashlib.sha256("|".join(sorted(p["key"] for p in found)).encode()).hexdigest()[:12]
    issues = api("GET", f"/repos/{repo}/issues?state=open&per_page=50", token) or []
    current = next((i for i in issues if i.get("title") == TITLE and "pull_request" not in i), None)
    body_lines = [f"- {p['text']}" for p in found]
    tail = f"\n\n[Ejecución]({run_url})" if run_url else ""
    if found:
        text = "\n".join(body_lines) + tail + f"\n\n{MARK}{fingerprint} -->"
        if current is None:
            api("POST", f"/repos/{repo}/issues", token,
                {"title": TITLE, "body": f"@{owner}\n\n" + text + "\n\n_Este aviso se cierra solo cuando todo vuelve a ir bien._"})
            return "opened"
        if f"{MARK}{fingerprint} -->" in (current.get("body") or "") + "".join(
                c.get("body") or "" for c in api("GET", f"/repos/{repo}/issues/{current['number']}/comments?per_page=100", token) or []):
            return "unchanged"
        api("POST", f"/repos/{repo}/issues/{current['number']}/comments", token, {"body": text})
        return "commented"
    if current is not None:
        api("POST", f"/repos/{repo}/issues/{current['number']}/comments", token,
            {"body": "✅ Todo vuelve a estar bien: el último informe se publicó y no hay franjas perdidas recientes." + tail})
        api("PATCH", f"/repos/{repo}/issues/{current['number']}", token, {"state": "closed", "state_reason": "completed"})
        return "closed"
    return "ok"


def main(root: str = ".", stale_hours: float = 11) -> int:
    token, repo = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or (repo or "/").split("/")[0]
    run_url = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
               if os.environ.get("GITHUB_RUN_ID") and repo else "")
    found = problems(Path(root), datetime.now(timezone.utc).astimezone(), stale_hours=stale_hours)
    if not token or not repo:
        print(json.dumps({"alert": "sin_credenciales", "problems": [p["key"] for p in found]}))
        return 0
    try:
        action = sync_issue(found, repo, token, owner, run_url=run_url)
    except Exception as exc:  # noqa: BLE001 — un aviso nunca bloquea la cadena
        print(json.dumps({"alert": "error", "detail": f"{type(exc).__name__}: {exc}"[:200]}))
        return 0
    print(json.dumps({"alert": action, "problems": [p["key"] for p in found]}, ensure_ascii=False))
    return 0
