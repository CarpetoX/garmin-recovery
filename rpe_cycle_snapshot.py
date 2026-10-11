"""Verified single-source RPE snapshot for chained Garmin Recovery workflows.

Never infer identity by date; never silently substitute stale/other run rows.
Pure functions facilitate CI tests without Google or Garmin credentials.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone

COLUMNS = ('Fecha', 'ID actividad', 'Actividad', 'RPE', 'Sensaciones',
           'Notas', 'Registrado', 'Detalle JSON')


class SnapshotError(ValueError):
    pass


def canonical_digest(rows):
    encoded = json.dumps(rows, sort_keys=True, ensure_ascii=False,
                         separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise SnapshotError('RPE CSV sin filas utilizables')
    seen_rows = set()
    rpe_by_id = {}
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or any(col not in row for col in COLUMNS):
            raise SnapshotError(f'RPE fila {index}: cabeceras A:H incompletas')
        activity_id = str(row.get('ID actividad') or '').strip().casefold()
        if not activity_id:
            raise SnapshotError(f'RPE fila {index}: falta ID actividad')
        if not str(row.get('Fecha') or '').strip():
            raise SnapshotError(f'RPE fila {index}: falta fecha')
        signature = canonical_digest([row])
        if signature in seen_rows:
            raise SnapshotError('Fila RPE exactamente duplicada para ' + activity_id)
        seen_rows.add(signature)
        # Several distinct blocks can share one Garmin activity, but their RPE
        # must not contradict each other. Preserve all blocks for CrossFit.
        rpe = str(row.get('RPE') or '').strip().replace(',', '.')
        if rpe:
            try:
                numeric_rpe = float(rpe)
            except ValueError as exc:
                raise SnapshotError('RPE no numérico para ' + activity_id) from exc
            if not 0 <= numeric_rpe <= 10:
                raise SnapshotError('RPE fuera de rango para ' + activity_id)
            if activity_id in rpe_by_id and rpe_by_id[activity_id] != numeric_rpe:
                raise SnapshotError('RPE contradictorio entre bloques de ' + activity_id)
            rpe_by_id[activity_id] = numeric_rpe
    return rows


def parse_timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return result if result.tzinfo is not None else None
    except (ValueError, TypeError):
        return None


def verified_snapshot(feedback, advanced, expected_run_id, now=None, max_age_minutes=40):
    """Use exactly the rows fetched by the corresponding Advanced Analytics run.

    On mismatch raise SnapshotError so CrossFit refuses to overwrite the last good
    report. A direct/manual CrossFit run can still use its original live CSV path.
    """
    if not expected_run_id:
        raise SnapshotError('Falta ID de la ejecución padre Advanced Analytics')
    if not isinstance(feedback, dict) or not isinstance(advanced, dict):
        raise SnapshotError('Falta instantánea de RPE o Advanced Analytics')
    if str(feedback.get('advanced_run_id') or '') != str(expected_run_id):
        raise SnapshotError('La instantánea RPE pertenece a otra ejecución Advanced')
    rows = validate_rows(feedback.get('source_rows_AH'))
    if canonical_digest(rows) != feedback.get('source_rows_sha256'):
        raise SnapshotError('Huella SHA-256 de RPE no coincide')
    if feedback.get('remote_fetch_error'):
        raise SnapshotError('RPE remoto tuvo errores de lectura')
    if int(feedback.get('remote_rows_loaded') or 0) != len(rows):
        raise SnapshotError('Conteo de filas RPE incoherente')
    advanced_rpe = advanced.get('rpe_feedback') or {}
    if not isinstance(advanced_rpe, dict) or advanced_rpe.get('remote_fetch_error'):
        raise SnapshotError('Advanced Analytics no confirmó la lectura RPE')
    if str(advanced_rpe.get('advanced_run_id') or '') != str(expected_run_id):
        raise SnapshotError('La analítica Advanced pertenece a otra ejecución')
    if advanced_rpe.get('source_rows_sha256') != canonical_digest(rows):
        raise SnapshotError('La analítica Advanced usó otra instantánea RPE')
    if int(advanced_rpe.get('remote_rows_loaded') or 0) != len(rows):
        raise SnapshotError('Advanced Analytics usó otro número de filas')
    last_date = max(str(row['Fecha']) for row in rows)
    if feedback.get('remote_latest_date') != last_date or advanced_rpe.get('remote_latest_date') != last_date:
        raise SnapshotError('Fecha máxima de RPE inconsistente')
    checked = parse_timestamp(feedback.get('source_fetched_at'))
    advanced_at = parse_timestamp(advanced.get('generated_at'))
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or checked is None or advanced_at is None:
        raise SnapshotError('Faltan timestamps con huso horario')
    if not timedelta(minutes=-2) <= now - checked <= timedelta(minutes=max_age_minutes):
        raise SnapshotError('Instantánea RPE antigua o futura')
    if not timedelta(minutes=-2) <= advanced_at - checked <= timedelta(minutes=max_age_minutes):
        raise SnapshotError('Advanced y RPE tienen tiempos incoherentes')
    if not timedelta(minutes=-2) <= now - advanced_at <= timedelta(minutes=max_age_minutes):
        raise SnapshotError('La generación de Advanced es demasiado antigua')
    return rows


# GitHub exposes the triggering workflow_run JSON in GITHUB_EVENT_PATH.
# Reading it directly removes the need to edit workflow YAML or add secrets.
from pathlib import Path


def parent_run_id_from_event(event_path):
    if not event_path:
        raise SnapshotError('Falta GITHUB_EVENT_PATH para verificar el padre Advanced')
    try:
        event = json.loads(Path(event_path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise SnapshotError('Evento GitHub ilegible o no válido') from exc
    run = event.get('workflow_run') if isinstance(event, dict) else None
    if not isinstance(run, dict) or run.get('name') != 'Garmin Advanced Analytics':
        raise SnapshotError('Evento sin padre Garmin Advanced Analytics válido')
    if run.get('conclusion') != 'success':
        raise SnapshotError('Advanced Analytics padre no finalizó correctamente')
    run_id = run.get('id')
    if type(run_id) is not int or run_id <= 0:
        raise SnapshotError('ID de ejecución padre ausente o inválido')
    return str(run_id)
