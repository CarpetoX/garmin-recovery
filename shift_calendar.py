"""Calendario único de turnos para recuperación y CrossFit Garmin.

Los meses confirmados tienen días libres por defecto. Fuera de ellos no
se presume que el usuario esté libre: se informa «unknown».
El día posterior a una TN se etiqueta post-TN cuando no hay nuevo turno,
y se conserva el turno real si también trabaja ese día.
"""
import calendar
import json
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path

FILE = Path('shift_calendar.json')
VALID_SHIFTS = {'MT', 'TN', 'free'}
LEGACY = VALID_SHIFTS | {'post-TN'}
HOURS = {'MT': {'start': '08:00', 'end': '22:00', 'end_day_offset': 0},
         'TN': {'start': '15:00', 'end': '08:00', 'end_day_offset': 1}}


def parse_day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise ValueError('Fecha inválida')


@lru_cache(maxsize=1)
def load_calendar(path=None):
    location = Path(path) if path else FILE
    if not location.is_file():
        return {'days': {}, 'confirmed_months': [], 'source_available': False}
    data = json.loads(location.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or not isinstance(data.get('days'), dict):
        raise ValueError('shift_calendar.json debe contener un objeto days')
    days, months = {}, []
    for ds, label in data['days'].items():
        if parse_day(ds).isoformat() != ds or label not in VALID_SHIFTS:
            raise ValueError(f'Turno inválido para {ds}: {label}')
        days[ds] = label
    raw_months = data.get('confirmed_months', [])
    if not isinstance(raw_months, list):
        raise ValueError('confirmed_months debe ser una lista')
    for month in raw_months:
        if not isinstance(month, str) or len(month) != 7 or date.fromisoformat(month + '-01').strftime('%Y-%m') != month:
            raise ValueError(f'Mes confirmado inválido: {month}')
        months.append(month)
    return {'days': days, 'confirmed_months': sorted(set(months)), 'source_available': True}


def primary_shift(day, cal, legacy=None):
    key = parse_day(day).isoformat()
    if key in cal['days']:
        return cal['days'][key], 'shift_calendar.json'
    if key[:7] in cal['confirmed_months']:
        return 'free', 'confirmed_month'
    previous = (legacy or {}).get(key)
    if previous in LEGACY:
        return ('free' if previous == 'post-TN' else previous), 'legacy_context'
    return 'unknown', 'unspecified'


def resolve_day(day, cal=None, legacy=None):
    d = parse_day(day)
    cal = cal if cal is not None else load_calendar()
    shift, source = primary_shift(d, cal, legacy)
    prev_shift, _ = primary_shift(d - timedelta(days=1), cal, legacy)
    post_tn = prev_shift == 'TN' or (legacy or {}).get(d.isoformat()) == 'post-TN'
    label = 'post-TN' if post_tn and shift in ('free', 'unknown') else shift
    return {'date': d.isoformat(), 'label': label, 'shift': shift,
            'post_tn': post_tn, 'source': source,
            'start': HOURS.get(shift, {}).get('start'),
            'end': HOURS.get(shift, {}).get('end'),
            'end_day_offset': HOURS.get(shift, {}).get('end_day_offset', 0)}


def context_map(legacy=None, cal=None):
    cal = cal if cal is not None else load_calendar()
    legacy = legacy if isinstance(legacy, dict) else {}
    days = set(legacy) | set(cal['days'])
    for month in cal['confirmed_months']:
        year, number = map(int, month.split('-'))
        days.update(f'{month}-{day:02d}' for day in range(1, calendar.monthrange(year, number)[1] + 1))
    # El día siguiente a una TN se resuelve también al cambiar de mes.
    for day, label in cal['days'].items():
        if label == 'TN':
            days.add((parse_day(day) + timedelta(days=1)).isoformat())
    return {day: resolve_day(day, cal, legacy)['label'] for day in sorted(days) if _valid_day(day)}


def _valid_day(day):
    try:
        return parse_day(day).isoformat() == day
    except (TypeError, ValueError):
        return False
