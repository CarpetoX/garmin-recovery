"""Tipo de una sesión entera (V8.7). Módulo puro: una sola regla para la app, los informes y el esfuerzo relativo.

La hoja nombra cada actividad como «Tipo - formato o ejercicios» (REGISTRO_ENTRENAMIENTOS.md), así que el prefijo manda:

* **WOD** (o metcon): siempre WOD, aunque lleve movimientos de halterofilia dentro (hang clean, squat snatch…).
* **Calentamiento** y **Técnica**: por su nombre, aunque el texto mencione el WOD que preparan.
* **Halterofilia**: la sesión entera, con todos sus ejercicios (también el front squat de un complex); nunca se parte.
* **Fuerza**: salvo que la sesión sea de levantamientos olímpicos (p. ej. «Fuerza - Squat snatch»), que es halterofilia.

Sin prefijo reconocible se decide por palabras: formato de WOD → WOD; movimiento olímpico → Halterofilia; ejercicio
de fuerza → Fuerza; técnica o movilidad → Técnica; si no, «Sin detalle».
"""
from __future__ import annotations

import re

from .progression import norm

OLYMPIC = re.compile(r"\b(snatch|clean|jerk|arrancada|cargada|envion|halterofilia)\b")
WOD = re.compile(r"\b(wod|amrap|for time|rft|metcon|chipper|emom|e\d+mom|e\d+mo\d+m|tabata)\b")
STRENGTH = re.compile(r"\b(fuerza|sentadilla|squat|peso muerto|deadlift|press|banca|prensa|dominadas?|pull ?ups?|chin ?ups?"
                      r"|curl|remo|zancadas?)\b")
TECHNIQUE = re.compile(r"\b(tecnica|skill|movilidad)\b")
WARMUP = re.compile(r"\b(calentamiento|warm ?up)\b")
PREFIX = {"calentamiento": "Calentamiento", "warmup": "Calentamiento", "warm": "Calentamiento",
          "tecnica": "Técnica", "skill": "Técnica", "movilidad": "Técnica",
          "wod": "WOD", "metcon": "WOD", "halterofilia": "Halterofilia"}
KINDS = ("WOD", "Fuerza", "Halterofilia", "Técnica", "Calentamiento", "Sin detalle")


def _head(label: str) -> str:
    """Primera palabra del tipo: lo que va antes de « - » o «:» en el nombre de la hoja."""
    raw = re.split(r"\s[-–—]\s|:", str(label or ""), maxsplit=1)[0]
    words = norm(raw).split()
    return words[0] if words else ""


def categorize(label=None, name=None, exercises=()) -> str:
    """Tipo de la sesión a partir de su nombre en la hoja (``label``), el de Garmin (``name``) y sus ejercicios."""
    lab = str(label or "")
    olympic_ex = any(OLYMPIC.search(norm(e)) for e in exercises or () if e)
    head = _head(lab)
    if head in PREFIX:
        return PREFIX[head]
    if head == "fuerza":
        return "Halterofilia" if OLYMPIC.search(norm(lab)) or olympic_ex else "Fuerza"
    text = norm(f"{lab} {name or ''}")
    if WOD.search(text):
        return "WOD"
    if OLYMPIC.search(text) or olympic_ex:
        return "Halterofilia"
    if STRENGTH.search(text):
        return "Fuerza"
    if TECHNIQUE.search(text):
        return "Técnica"
    if WARMUP.search(text):
        return "Calentamiento"
    return "Sin detalle"


def is_olympic_session(label=None, exercises=()) -> bool:
    """¿Va la sesión de fuerza entera a Halterofilia? (los metcons tienen su propia tarjeta)."""
    return categorize(label, None, exercises) == "Halterofilia"
