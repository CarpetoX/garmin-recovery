"""Estado final de cada ciclo: cadena de datos, publicación web y entrega de la notificación.

El certificado del ciclo (``report_ready.json``) cubre Sync, FC, analítica y CrossFit. Este módulo añade lo que ocurre
después: si la web se desplegó y si ntfy aceptó el aviso. Escribe ``delivery_status.json``.

Alcance honesto: «notificación enviada» significa que el servidor ntfy aceptó el mensaje (HTTP 2xx); no hay acuse de
lectura en el móvil. Las funciones de decisión son puras; la red solo se usa en ``main`` y se inyecta en las pruebas.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
CHAIN = ("sync", "heart", "advanced", "crossfit")
CHAIN_OK = {"success", "publishing_in_same_job"}
NOTIFY_LINE = re.compile(r'\{"notify":\s*"([a-z_]+)"(?:,\s*"http":\s*(\d+))?')
LABELS = {"sync": "Sync", "heart": "Frecuencia cardíaca", "advanced": "Analítica", "crossfit": "CrossFit",
          "web": "Web publicada", "notification": "Notificación"}


def chain_stages(ready: dict) -> dict:
    out = {}
    chain = ready.get("chain") or {}
    for k in CHAIN:
        c = (chain.get(k) or {}).get("conclusion")
        out[k] = {"state": "ok" if c in CHAIN_OK else ("unknown" if c is None else "failed"), "conclusion": c}
    return out


def web_stage(pages_run: dict | None) -> dict:
    if not pages_run:
        return {"state": "unknown", "note": "no se encontró un despliegue posterior al ciclo"}
    st, concl = pages_run.get("status"), pages_run.get("conclusion")
    if st != "completed":
        return {"state": "pending", "note": "despliegue en curso", "run_id": pages_run.get("id")}
    return {"state": "ok" if concl == "success" else "failed", "conclusion": concl, "run_id": pages_run.get("id"),
            "at": pages_run.get("updated_at")}


def notify_from_log(text: str | None) -> dict:
    """Lee la línea JSON que imprime ``notify.main`` en el registro del paso."""
    if not text:
        return {"state": "unknown", "note": "registro del paso no disponible"}
    found = NOTIFY_LINE.findall(text)
    if not found:
        return {"state": "unknown", "note": "el paso no imprimió resultado"}
    kind, http = found[-1]
    if kind == "enviado":
        return {"state": "ok", "http": int(http) if http else None,
                "note": "ntfy aceptó el mensaje; no hay acuse de lectura en el móvil"}
    if kind == "error":
        return {"state": "failed", "note": "falló el envío a ntfy"}
    return {"state": "skipped", "note": {"sin_tema": "sin tema ntfy configurado",
                                         "sin_informe_nuevo": "no había informe nuevo y válido que avisar"}.get(kind, kind)}


def overall(stages: dict) -> str:
    states = {k: v["state"] for k, v in stages.items()}
    if any(s == "failed" for s in states.values()):
        return "failed"
    if any(s == "pending" for s in states.values()):
        return "pending"
    if all(s == "ok" for s in states.values()):
        return "complete"
    if all(s in ("ok", "skipped") for s in states.values()):
        return "complete_without_notification"
    return "unconfirmed"


def assess(ready: dict, pages_run: dict | None, notify_log: str | None, now: datetime) -> dict:
    stages = chain_stages(ready)
    stages["web"] = web_stage(pages_run)
    stages["notification"] = notify_from_log(notify_log)
    return {"schema_version": 1, "cycle_id": ready.get("cycle_id"), "evaluated_at": now.isoformat(),
            "state": overall(stages), "stages": stages,
            "scope": "Notificación enviada = aceptada por ntfy; no prueba que se haya leído."}


# ------------------------------------------------------------------ red (solo main)
def _headers(token: str) -> dict:
    return {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "Garmin-Cycle-Delivery"}


class _NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.remove_header("Authorization")  # la URL firmada del registro no admite el token
        return new


def api_json(url: str, token: str):
    with urllib.request.urlopen(urllib.request.Request(url, headers=_headers(token)), timeout=25) as r:
        return json.load(r)


def api_text(url: str, token: str) -> str:
    opener = urllib.request.build_opener(_NoAuthRedirect)
    with opener.open(urllib.request.Request(url, headers=_headers(token)), timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def find_pages_run(runs: list, after: datetime) -> dict | None:
    """Primer despliegue de Pages creado desde el cierre de CrossFit (el más antiguo posterior)."""
    cands = []
    for r in runs:
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError, AttributeError):
            continue
        if created >= after:
            cands.append((created, r))
    return min(cands, key=lambda x: x[0])[1] if cands else None


def main(root: str = ".", fetch_json=api_json, fetch_text=api_text, sleep=time.sleep, wait_s: int = 300) -> int:
    root_p = Path(root)
    repo, token = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GH_TOKEN", "")
    try:
        ready = json.loads((root_p / "report_ready.json").read_text(encoding="utf-8"))
        cf = (ready.get("chain") or {}).get("crossfit") or {}
        cf_id = os.environ.get("TRIGGER_RUN_ID") or str(cf.get("id") or "")
        base = f"https://api.github.com/repos/{repo}"
        after = datetime.fromisoformat(cf.get("started_at") or ready["verified_at"])
        if os.environ.get("TRIGGER_RUN_ID"):
            # el certificado puede ser de un ciclo anterior (Sync fuera de franja): el despliegue que cuenta es el
            # posterior a la ejecución de CrossFit que disparó este monitor
            try:
                run = fetch_json(f"{base}/actions/runs/{cf_id}", token)
                after = datetime.fromisoformat((run.get("run_started_at") or run["created_at"]).replace("Z", "+00:00"))
            except (OSError, ValueError, KeyError):
                pass
        notify_log = None
        try:
            jobs = fetch_json(f"{base}/actions/runs/{cf_id}/jobs", token).get("jobs") or []
            job = next((j for j in jobs if any("ntfy" in (s.get("name") or "") for s in j.get("steps") or [])), None)
            if job:
                notify_log = fetch_text(f"{base}/actions/jobs/{job['id']}/logs", token)
        except (OSError, ValueError, KeyError):
            notify_log = None
        pages = None
        for _ in range(max(1, wait_s // 15)):
            try:
                pages = find_pages_run(fetch_json(f"{base}/actions/workflows/pages.yml/runs?per_page=20", token)
                                       .get("workflow_runs") or [], after)
            except (OSError, ValueError, KeyError):
                pages = None
            if pages and pages.get("status") == "completed":
                break
            sleep(15)
        status = assess(ready, pages, notify_log, datetime.now(TZ))
        (root_p / "delivery_status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"delivery": status["state"], "cycle_id": status["cycle_id"]}, ensure_ascii=False))
    except (OSError, ValueError, KeyError) as exc:  # nunca bloquea el monitor
        print(json.dumps({"delivery": "error", "detail": type(exc).__name__}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
