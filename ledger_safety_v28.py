"""Fail-closed, lossless, atomic certificate ledger persistence for Garmin Recovery."""
import json
import os
import tempfile
from pathlib import Path
from archive_report_cycles import ArchiveError, digest, inspect, validate_cycle

class LedgerSafetyError(RuntimeError):
    pass

def read_ledger(path):
    """Return (ledger, version); absent is allowed, corrupt existing is not."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return None, 1
    except (OSError, ValueError) as exc:
        raise LedgerSafetyError('Histórico existente ilegible; no sobrescribir') from exc
    if not isinstance(data, dict) or not isinstance(data.get('cycles'), list):
        raise LedgerSafetyError('Histórico existente con estructura inválida')
    rows = data['cycles']
    ids = [x.get('cycle_id') for x in rows if isinstance(x, dict)]
    if len(ids) != len(rows) or any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise LedgerSafetyError('Histórico existente con IDs inválidos o duplicados')
    version = data.get('schema_version', 1)
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise LedgerSafetyError('Versión de histórico no válida')
    if version >= 2:
        try:
            inspect(path)
        except ArchiveError as exc:
            raise LedgerSafetyError('El histórico falla la auditoría SHA-256; no sobrescribir') from exc
    elif data.get('count') is not None and data['count'] != len(rows):
        raise LedgerSafetyError('Contador legacy incoherente')
    return data, version

def atomic_write_ledger(path, items):
    """Write v2 ledger, checking all old records and actual temporary file."""
    path = Path(path)
    if not isinstance(items, list):
        raise LedgerSafetyError('Se esperaba una lista completa de certificados')
    existing, version = read_ledger(path)
    old_rows = existing['cycles'] if existing else []
    if not path.parent.is_dir():
        raise LedgerSafetyError('Directorio del histórico no existe')
    new_rows = {}
    for row in items:
        try:
            validate_cycle(row)
        except ArchiveError as exc:
            raise LedgerSafetyError('Certificado nuevo no válido') from exc
        if row['cycle_id'] in new_rows:
            raise LedgerSafetyError('Certificado duplicado; no sobrescribir')
        new_rows[row['cycle_id']] = row
    for old in old_rows:
        old_id = old['cycle_id']
        if old_id not in new_rows:
            raise LedgerSafetyError('Se intentó descartar un certificado existente: ' + old_id)
        if version >= 2 and digest(new_rows[old_id]) != digest(old):
            raise LedgerSafetyError('Un certificado anterior fue modificado: ' + old_id)
    payload = {
        'schema_version': 2, 'ledger_version': '2.8.0',
        'purpose': 'Historical data-readiness ledger (not an outgoing notification receipt)',
        'cycles': sorted(items, key=lambda x: x.get('slot_at', '')),
        'count': len(items),
    }
    fd, temp_name = tempfile.mkstemp(prefix='.report_cycles-v28-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
            f.flush()
            os.fsync(f.fileno())
        try:
            result, _, _ = inspect(temp_name)
        except ArchiveError as exc:
            raise LedgerSafetyError('El histórico temporal no supera auditoría') from exc
        if digest(result['cycles']) != digest(payload['cycles']):
            raise LedgerSafetyError('La restauración de prueba no coincide')
        recent, _ = read_ledger(path)
        if digest(recent) != digest(existing):
            raise LedgerSafetyError('El histórico original cambió durante la escritura')
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {'cycles_preserved': len(old_rows), 'cycles_now': len(items),
            'truncation': False, 'ledger_sha256': digest(payload['cycles'])}
