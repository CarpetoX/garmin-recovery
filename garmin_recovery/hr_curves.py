"""Curva de frecuencia cardíaca de cada sesión (``activity_hr_curves.json``).

Solo visualización: no entra en la decisión ni en ninguna puntuación. La FC sale del stream segundo a segundo de
Intervals.icu (``/activity/{id}/streams``), reducida a un punto cada ``STEP_S`` segundos (media del intervalo).
Si una sesión no tiene FC o el stream falla, queda registrada como no disponible; nunca se inventa una curva.
Módulo sin red ni reloj: ``refresh`` recibe la función de descarga y la hora.
"""
from __future__ import annotations

STEP_S = 10
MAX_NEW_PER_RUN = 10
WINDOW_DAYS = 28


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def downsample(times, hr, step: int = STEP_S) -> list[list[int]]:
    """Media de la FC por tramo de ``step`` s → ``[[segundo, bpm], …]``; ignora ceros y valores ausentes."""
    buckets: dict[int, list[float]] = {}
    for t, h in zip(times, hr, strict=False):
        t, h = _num(t), _num(h)
        if t is None or h is None or h < 30 or h > 230:
            continue
        buckets.setdefault(int(t // step), []).append(h)
    return [[k * step, round(sum(v) / len(v))] for k, v in sorted(buckets.items())]


def _streams(payload) -> dict:
    out = {}
    if isinstance(payload, list):
        for it in payload:
            if isinstance(it, dict) and isinstance(it.get("type"), str) and isinstance(it.get("data"), list):
                out[it["type"]] = it["data"]
    return out


def entry(activity: dict, payload) -> dict:
    """Entrada del archivo para una sesión; ``available`` False si no hay FC utilizable."""
    zones = activity.get("icu_hr_zones")
    ztimes = activity.get("icu_hr_zone_times")
    base = {
        "activity_id": str(activity.get("id")), "date": (activity.get("start_date_local") or "")[:10],
        "start_local": activity.get("start_date_local"), "name": activity.get("name"), "type": activity.get("type"),
        "avg_hr": _num(activity.get("average_heartrate")), "max_hr": _num(activity.get("max_heartrate")),
        "duration_s": _num(activity.get("elapsed_time")) or _num(activity.get("moving_time")),
        "zone_bounds": zones if isinstance(zones, list) else None,
        "zone_seconds": ztimes if isinstance(ztimes, list) else None,
        "step_s": STEP_S,
    }
    st = _streams(payload)
    pts = downsample(st.get("time") or [], st.get("heartrate") or st.get("fixed_heartrate") or [])
    if len(pts) < 3:
        return {**base, "available": False, "points": []}
    return {**base, "available": True, "points": pts}


def refresh(activities: list, cache: dict | None, api_key: str, fetch, today: str, max_new: int = MAX_NEW_PER_RUN) -> dict:
    """Completa la caché con las sesiones de los últimos ``WINDOW_DAYS`` días que aún no tienen curva.

    ``fetch(activity_id, api_key)`` devuelve el JSON de streams. Más recientes primero; como mucho ``max_new`` descargas
    por ejecución (el resto se rellena en las siguientes). Una sesión sin FC se marca ``available: False`` y no se reintenta.
    Un fallo de red no marca nada: se reintenta en el siguiente ciclo.
    """
    from datetime import date, timedelta
    cache = cache if isinstance(cache, dict) else {}
    items = dict(cache.get("activities") or {})
    limit = (date.fromisoformat(today) - timedelta(days=WINDOW_DAYS)).isoformat()
    calls = errors = 0
    for a in sorted((x for x in activities if isinstance(x, dict)), key=lambda x: x.get("start_date_local") or "", reverse=True):
        aid = str(a.get("id") or "")
        day = (a.get("start_date_local") or "")[:10]
        if not aid or day < limit or aid in items:
            continue
        if not a.get("has_heartrate"):
            items[aid] = {**entry(a, None), "available": False, "points": []}
            continue
        if not api_key or calls >= max_new:
            continue
        calls += 1
        try:
            items[aid] = entry(a, fetch(aid, api_key))
        except Exception:  # noqa: BLE001 — red/API: se reintenta en el siguiente ciclo
            errors += 1
    items = {k: v for k, v in items.items() if (v.get("date") or "") >= limit}
    return {"schema_version": 1, "window_days": WINDOW_DAYS, "step_s": STEP_S, "activities": items,
            "fetch_calls_this_run": calls, "fetch_errors_this_run": errors}
