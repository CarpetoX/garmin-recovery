"""Avisos automáticos en GitHub (issue) cuando algo necesita atención.

Un único issue abierto a la vez («⚠️ Garmin Recovery: atención necesaria»):

* **cadena** (CrossFit Insights, cada ciclo): avisa si el job falló antes de publicar o si
  el informe no pasó la validación. Solo un ciclo que publica bien puede cerrar estos avisos.
* **vigilancia** (monitor programado, tras calcular `workflow_health.json`): avisa si no hay
  informe nuevo en 11 h (el hueco normal 22:45→08:30 es de casi 10 h) o si se perdió una
  franja de Sync en las últimas 12 h. No puede cerrar avisos de la cadena.
* Cada ejecución solo cambia los problemas de su ámbito; el issue guarda los problemas
  activos en una marca oculta, comenta solo si cambian y se cierra cuando no queda ninguno.

GitHub notifica los issues nuevos al propietario (mención). Nunca bloquea la cadena.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TITLE = "⚠️ Garmin Recovery: atención necesaria"
TZ = ZoneInfo("Europe/Madrid")
KEYS_RE = re.compile(r"<!-- garmin-keys:([^>]*) -->")
SCOPES = {"chain": ("chain_failed", "validation", "stale", "missed:", "garmin", "intervals"),
          "watchdog": ("stale", "missed:", "garmin", "intervals")}


def _in_scope(key: str, scope: str) -> bool:
    return any(key == k or (k.endswith(":") and key.startswith(k)) for k in SCOPES[scope])


def _read(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except (OSError, ValueError):
        return {}


def _dt(v):
    try:
        d = datetime.fromisoformat(str(v))
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=TZ)


def problems(root: Path, now: datetime, scope: str = "chain", job_status: str = "success",
             stale_hours: float = 11, missed_hours: float = 12) -> list[dict]:
    root, now = Path(root), now.astimezone(TZ)
    ok_job = job_status in ("", "success")
    out: list[dict] = []
    if scope == "chain" and not ok_job:
        out.append({"key": "chain_failed", "text": "La cadena *CrossFit Insights* falló en este ciclo antes de publicar: "
                    "sigue visible el informe anterior. Revisa la ejecución enlazada."})
    if scope == "chain" and ok_job:
        val = _read(root / "app" / "validation.json")
        if val.get("status") == "failed":
            out.append({"key": "validation", "text": "El informe de este ciclo **no se publicó** porque no pasó la validación; "
                        "sigue visible el anterior. Motivos: " + "; ".join(str(e) for e in (val.get("errors") or [])[:5])})
    data = _read(root / "app" / "readiness_v3.json")
    gen = _dt(data.get("generated_at"))
    if ok_job and (gen is None or now - gen > timedelta(hours=stale_hours)):
        when = gen.astimezone(TZ).strftime("%d/%m %H:%M") if gen else "desconocido"
        out.append({"key": "stale", "text": f"No hay informe nuevo desde {when}. Revisa los activadores de Apps Script "
                    "y las ejecuciones de *Garmin Recovery Sync*."})
    out += source_problems(root, now)
    missed = set((((data.get("certificate") or {}).get("execution_health") or {}).get("missed_slots")) or [])
    for alert in _read(root / "workflow_health.json").get("alerts") or []:
        if isinstance(alert, dict) and alert.get("code") == "sync_slot_not_recovered":
            missed |= {s for s in alert.get("slots") or [] if isinstance(s, str)}
    recent = sorted(t.astimezone(TZ) for t in (_dt(s) for s in missed)
                    if t is not None and timedelta(0) <= now - t <= timedelta(hours=missed_hours))
    for t in recent:
        out.append({"key": "missed:" + t.strftime("%Y-%m-%dT%H:%M"),
                    "text": f"Franja de Sync perdida: {t.strftime('%d/%m %H:%M')} (Apps Script no lanzó el Sync o la cadena no terminó)."})
    return out


def source_problems(root: Path, now: datetime) -> list[dict]:
    """Garmin o Intervals.icu desconectados: sus datos publicados dejan de avanzar."""
    out = []
    limit = (now - timedelta(days=1)).date().isoformat()
    gs = _read(root / "garmin_status.json")
    last = max((str(gs.get(k) or "") for k in ("latest_heart_rate_date", "latest_stress_date", "latest_extended_date")), default="")
    # un error aislado (p. ej. 429) vale solo si los datos publicados ya están atrasados
    if gs and last and last < limit:
        err = str(gs.get("error") or "")[:160]
        hint = (" Parece un problema de acceso: renueva el secreto `GARMIN_TOKENS_B64` en GitHub."
                if any(w in err.lower() for w in ("token", "auth", "401", "403", "login", "garmin_tokens")) else "")
        out.append({"key": "garmin", "text": f"Garmin no aporta datos nuevos (último día {last or '—'}"
                    + (f"; error: {err}" if err else "") + ")." + hint})
    try:
        wellness = json.loads((root / "wellness.json").read_text(encoding="utf-8"))
        # solo cuentan filas con datos de Garmin (HRV, FC en reposo o sueño), no las que traen solo carga
        newest = max((str(x.get("id") or "") for x in wellness if isinstance(x, dict)
                      and any(x.get(k) not in (None, "", 0) for k in ("hrv", "restingHR", "sleepSecs"))), default="")
    except (OSError, ValueError, TypeError):
        newest = None
    if newest is not None and newest < limit:
        out.append({"key": "intervals", "text": f"Intervals.icu no aporta datos nuevos (último día {newest or '—'}). "
                    "Revisa el secreto `INTERVALS_API_KEY` y la sincronización Garmin → Intervals."})
    status = _read(root / "intervals_status.json")
    failing = [f"{name} ({e.get('kind') or '?'}{', HTTP ' + str(e['http']) if e.get('http') else ''}, "
               f"{e.get('consecutive_failures')} seguidos)"
               for name, e in status.items()
               if isinstance(e, dict) and e.get("status") == "error" and int(e.get("consecutive_failures") or 0) >= 3]
    if failing:
        text = ("Intervals.icu falla de forma repetida: " + "; ".join(failing)
                + ". Se están usando los últimos datos descargados.")
        hit = next((p for p in out if p["key"] == "intervals"), None)
        if hit:
            hit["text"] += " " + text
        else:
            out.append({"key": "intervals", "text": text})
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


def _find_issue(api, repo, token):
    for page in range(1, 6):
        batch = api("GET", f"/repos/{repo}/issues?state=open&per_page=100&page={page}", token) or []
        hit = next((i for i in batch if i.get("title") == TITLE and "pull_request" not in i), None)
        if hit or len(batch) < 100:
            return hit
    return None


def _active_keys(api, repo, token, issue) -> set[str]:
    texts = [issue.get("body") or ""] + [c.get("body") or "" for c in
                                         api("GET", f"/repos/{repo}/issues/{issue['number']}/comments?per_page=100", token) or []]
    for t in reversed(texts):  # la marca más reciente manda
        m = KEYS_RE.search(t)
        if m:
            return {k for k in m.group(1).split(",") if k}
    return set()


def sync_issue(found: list[dict], repo: str, token: str, owner: str, scope: str = "chain",
               api=None, run_url: str = "") -> str:
    """Abre, comenta o cierra el issue de aviso. Devuelve la acción realizada."""
    api = api or _api
    current = _find_issue(api, repo, token)
    previous = _active_keys(api, repo, token, current) if current else set()
    texts = {p["key"]: p["text"] for p in found}
    active = {k for k in previous if not _in_scope(k, scope)} | set(texts)
    tail = f"\n\n[Ejecución]({run_url})" if run_url else ""
    marker = f"\n\n<!-- garmin-keys:{','.join(sorted(active))} -->"
    if active:
        kept = sorted(active - set(texts))
        lines = [f"- {texts[k]}" for k in sorted(texts)] + [f"- Sigue pendiente: `{k}`" for k in kept]
        if current is None:
            api("POST", f"/repos/{repo}/issues", token,
                {"title": TITLE, "body": f"@{owner}\n\n" + "\n".join(lines) + tail
                 + "\n\n_Este aviso se cierra solo cuando todo vuelve a ir bien._" + marker})
            return "opened"
        if active == previous:
            return "unchanged"
        api("POST", f"/repos/{repo}/issues/{current['number']}/comments", token,
            {"body": "Cambio en los avisos:\n\n" + "\n".join(lines) + tail + marker})
        return "commented"
    if current is not None:
        api("POST", f"/repos/{repo}/issues/{current['number']}/comments", token,
            {"body": "✅ Sin avisos activos: el último informe se publicó y no hay franjas perdidas en las últimas 12 h." + tail
             + "\n\n<!-- garmin-keys: -->"})
        api("PATCH", f"/repos/{repo}/issues/{current['number']}", token, {"state": "closed", "state_reason": "completed"})
        return "closed"
    return "ok"


def main(root: str = ".", scope: str = "chain") -> int:
    token, repo = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER") or (repo or "/").split("/")[0]
    run_url = (f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
               if os.environ.get("GITHUB_RUN_ID") and repo else "")
    try:
        found = problems(Path(root), datetime.now(TZ), scope=scope, job_status=os.environ.get("CHAIN_STATUS", "success"))
        if not token or not repo:
            print(json.dumps({"alert": "sin_credenciales", "problems": [p["key"] for p in found]}))
            return 0
        action = sync_issue(found, repo, token, owner, scope=scope, run_url=run_url)
    except Exception as exc:  # noqa: BLE001 — un aviso nunca bloquea la cadena
        print(json.dumps({"alert": "error", "detail": f"{type(exc).__name__}: {exc}"[:200]}))
        return 0
    print(json.dumps({"alert": action, "scope": scope, "problems": [p["key"] for p in found]}, ensure_ascii=False))
    return 0
