"""Decisión operativa del día y registro de modelos.

En el repositorio conviven varias puntuaciones con escalas y propósitos
distintos. Este módulo declara explícitamente cuál es cada una (versión,
rol, regla) y deriva UNA decisión operativa con una regla conservadora:

* Modelo oficial: ``recovery_assessment_v2`` (política del repositorio),
  hasta que el v3 se valide frente al rendimiento real.
* Zona operativa = la MÁS CONSERVADORA entre el oficial (v2), el híbrido
  (que incorpora Garmin Training Readiness) y el v3 en sombra.
* Orden de prudencia (de más a menos estricto): rojo → pendiente → ámbar →
  verde. Un rojo de cualquier modelo prevalece siempre; si ninguno es rojo y
  alguno está pendiente, sin datos o es de otro día, la decisión es "pendiente"
  (no autoriza intensidad alta).

Así una discrepancia entre modelos nunca produce una recomendación más
exigente que la del modelo más prudente.
"""
from __future__ import annotations

# Ordenado por la exigencia de su pauta (RPE máx. 4 < 6 < 7 < 9): el menor gana.
ORDER = {"red": 0, "unavailable": 1, "yellow": 2, "green": 3}
ZONE_ES = {"unavailable": "pendiente", "red": "rojo", "yellow": "ámbar", "green": "verde"}


CROSSFIT = {
    "green": ["Sesión planificada completa: halterofilia pesada, fuerza y WOD a intensidad alta si el calentamiento responde.",
              "Calentamiento progresivo; si la barra va lenta en las aproximaciones, baja a la pauta ámbar."],
    "yellow": ["Halterofilia técnica al ≤ 80 % de tus cargas habituales, sin singles pesados.",
               "Fuerza submáxima: deja 2–3 repeticiones en reserva, sin series al fallo.",
               "WOD a ritmo controlado (sin all-out ni lucha contra el cap); recorta un 20–30 % de volumen."],
    "red": ["Sin WOD ni cargas pesadas: movilidad, técnica con PVC o barra vacía.",
            "Si te mueves, zona 2 suave en remo, bici o caminata (30–40 min, poder hablar)."],
    "unavailable": ["Hasta tener datos: solo técnica ligera y movilidad; nada de intensidad alta."],
}


def _zone(status, state=None) -> str | None:
    if state == "pending":
        return "unavailable"
    s = str(status or "").lower()
    return s if s in ORDER else None


def model_registry(readiness_v3: dict, legacy: dict, daily_summary: dict, garmin_readiness,
                   today: str | None = None) -> list[dict]:
    ds = daily_summary or {}
    hybrid = ds.get("readiness_hybrid") or {}
    compat = ds.get("readiness_model") or {}
    v2_date = (legacy.get("current") or {}).get("date")
    ds_date = ds.get("date")
    v2_stale = bool(today and v2_date and v2_date != today)
    ds_stale = bool(today and ds_date and ds_date != today)
    registry = [
        {"id": "recovery_assessment_v2", "label": "Recuperación v2 (oficial)",
         "version": legacy.get("methodology_version"), "role": "oficial", "used_in_decision": True,
         "score": legacy.get("score"), "zone": _zone(legacy.get("status"), legacy.get("state")),
         "state": legacy.get("state"), "confidence": legacy.get("confidence"),
         "rule": "85 menos penalizaciones por HRV, FC reposo, sueño y FC nocturna; salvaguardas de frescura."},
        {"id": "readiness_hybrid", "label": "Híbrido Garmin + local",
         "version": "V2.2", "role": "salvaguarda", "used_in_decision": True,
         "score": hybrid.get("score"), "zone": _zone(hybrid.get("status")),
         "state": None, "confidence": hybrid.get("local_confidence"),
         "rule": "55 % Garmin Training Readiness + 45 % local; Garmin < 35 fuerza rojo."},
        {"id": "readiness_v3", "label": "Disponibilidad v3 (en pruebas)",
         "version": readiness_v3.get("model_version"), "role": "sombra", "used_in_decision": True,
         "score": readiness_v3.get("score"), "zone": readiness_v3.get("zone"),
         "state": readiness_v3.get("state"), "confidence": readiness_v3.get("confidence"),
         "rule": "Componentes continuos: HRV 7 días vs. rango normal, FC, sueño, estrés, carga y sensaciones."},
        {"id": "readiness_model", "label": "Modelo de compatibilidad",
         "version": "V2.2", "role": "compatibilidad", "used_in_decision": False,
         "score": compat.get("score"), "zone": _zone(compat.get("status")),
         "state": None, "confidence": compat.get("confidence"),
         "rule": "Puntuación heredada; el propio repo indica no usarla para decidir."},
        {"id": "garmin_training_readiness", "label": "Garmin Training Readiness",
         "version": "Garmin", "role": "contexto", "used_in_decision": False,
         "score": garmin_readiness, "zone": None, "state": None, "confidence": None,
         "rule": "Métrica propietaria (ya incluida en el híbrido); escala distinta, solo contexto."},
    ]
    # Un modelo de otro día no autoriza nada hoy: cuenta como sin datos (→ pendiente). Su puntuación
    # no se registra como de hoy; un rojo de ayer sí sigue limitando (criterio prudente).
    for m, stale, d in ((registry[0], v2_stale, v2_date), (registry[1], ds_stale, ds_date), (registry[3], ds_stale, ds_date)):
        if stale:
            m.update(stale_score=m["score"], stale_zone=m["zone"], score=None,
                     zone="red" if m["zone"] == "red" else None, state="desactualizado", stale_date=d)
    return registry


def operative_zone(zones: list) -> str:
    """Zona más prudente; un modelo sin datos cuenta como "pendiente", nunca anula un rojo."""
    effective = [z if z in ORDER else "unavailable" for z in zones] or ["unavailable"]
    return min(effective, key=lambda z: ORDER[z])


def operative_decision(readiness_v3: dict, legacy: dict, daily_summary: dict,
                       garmin_readiness, guidance_table: dict, model_validated: bool,
                       today: str | None = None) -> dict:
    registry = model_registry(readiness_v3, legacy, daily_summary, garmin_readiness, today)
    voting = [m for m in registry if m["used_in_decision"]]
    zones = [m["zone"] for m in voting]
    missing = [m["id"] for m in voting if m["zone"] is None]
    zone = operative_zone(zones)
    deciding = [m["id"] for m in voting if (m["zone"] or "unavailable") == zone]
    v3_zone = readiness_v3.get("zone")
    divergence = []
    if v3_zone in ORDER and zone in ORDER and ORDER[v3_zone] > ORDER[zone]:
        divergence.append(f"El v3 ({ZONE_ES[v3_zone]}) es más permisivo que la decisión ({ZONE_ES[zone]}); "
                          "se aplica la más conservadora.")
    spread = [m["zone"] for m in voting if m["zone"] in ORDER]
    agreement = "total" if len(set(spread)) == 1 and not missing else "parcial"
    guidance = dict(guidance_table[zone])
    return {
        "zone": zone, "zone_es": ZONE_ES[zone], "guidance": guidance, "crossfit": CROSSFIT[zone],
        "official_model": "recovery_assessment_v2" if not model_validated else "readiness_v3",
        "rule": ("Zona operativa = la más conservadora entre v2 (oficial), híbrido y v3. Un rojo prevalece "
                 "siempre; si no hay rojo y algún modelo está pendiente, sin datos o es de otro día, queda pendiente. "
                 "Un rojo de otro día sigue limitando hasta que llegue el dato de hoy."),
        "decided_by": deciding, "missing_models": missing,
        "agreement": agreement, "divergence": divergence,
        "registry": registry,
    }
