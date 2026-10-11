#!/usr/bin/env python3
"""Non-destructive audit and reversible monthly COPY archive for Garmin Recovery.

Default: audit only. --prepare exports closed-month copies after SHA-256 verification.
Does not delete, rewrite or shorten report_cycles.json.
"""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


class ArchiveError(ValueError):
    pass


def digest(obj):
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def validate_cycle(cycle):
    if not isinstance(cycle, dict) or not isinstance(cycle.get('cycle_id'), str):
        raise ArchiveError('Certificado sin ID')
    cid = cycle['cycle_id']
    slot = cycle.get('slot_at')
    if not isinstance(slot, str) or len(slot) < 10:
        raise ArchiveError(f'{cid}: falta slot_at')
    try:
        date.fromisoformat(slot[:10])
    except ValueError as exc:
        raise ArchiveError(f'{cid}: fecha inválida') from exc
    snapshot = cycle.get('snapshot')
    if snapshot is None:
        if cycle.get('snapshot_sha256') is not None or cycle.get('legacy_without_snapshot') is not True:
            raise ArchiveError(f'{cid}: snapshot perdido sin registro legacy')
        return 'legacy'
    if not isinstance(snapshot, dict) or digest(snapshot) != cycle.get('snapshot_sha256'):
        raise ArchiveError(f'{cid}: SHA-256 de snapshot incorrecto')
    return 'verified'


def inspect(path):
    try:
        ledger = json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        raise ArchiveError('No se puede leer report_cycles.json') from exc
    if not isinstance(ledger, dict) or not isinstance(ledger.get('cycles'), list):
        raise ArchiveError('Estructura del ledger inválida')
    rows = ledger['cycles']
    if ledger.get('count') != len(rows):
        raise ArchiveError('Contador de certificados incorrecto')
    seen = set()
    states = Counter()
    months = defaultdict(list)
    for row in rows:
        states[validate_cycle(row)] += 1
        cid = row['cycle_id']
        if cid in seen:
            raise ArchiveError(f'ID de ciclo duplicado: {cid}')
        seen.add(cid)
        months[row['slot_at'][:7]].append(row)
    return ledger, dict(sorted(months.items())), states


def audit(path):
    ledger, months, states = inspect(path)
    return {'status': 'ok', 'cycles': len(ledger['cycles']),
            'verified': states['verified'], 'legacy': states['legacy'],
            'months': {k: len(v) for k, v in months.items()},
            'cycles_sha256': digest(ledger['cycles']), 'ledger_modified': False}


def prepare(path, output, today=None):
    """Write CLOSED-month copies to a new directory; verify roundtrip from disk.

    Current-month cycles stay in the live ledger. Existing destinations are never
    overwritten. No live JSON is changed under any circumstances.
    """
    source, dest = Path(path), Path(output)
    if dest.exists():
        raise ArchiveError('Destino ya existente: usar otro directorio')
    ledger, months, _ = inspect(source)
    today = today or date.today()
    selected = {m: rows for m, rows in months.items() if m < today.strftime('%Y-%m')}
    if not selected:
        return {'status': 'no_closed_months', 'source_unchanged': True,
                'cycles_kept': len(ledger['cycles'])}
    original = source.read_bytes()
    dest.mkdir(parents=True, exist_ok=False)
    entries = {}
    for month, rows in selected.items():
        payload = {'schema_version': 1, 'month': month, 'count': len(rows), 'cycles': rows}
        file = dest / f'{month}.json'
        file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        entries[file.name] = digest(payload)
    manifest = {'kind': 'verified_non_destructive_copy',
                'source_bytes_sha256': hashlib.sha256(original).hexdigest(),
                'source_cycles_sha256': digest(ledger['cycles']),
                'source_count': len(ledger['cycles']), 'files': entries,
                'notice': 'No JSON deleted; archived copies are not proof of ChatGPT delivery'}
    (dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False,
                                                 indent=2) + '\n', encoding='utf-8')
    restored = {}
    for name, hash_value in entries.items():
        data = json.loads((dest / name).read_text(encoding='utf-8'))
        if digest(data) != hash_value or len(data['cycles']) != data['count']:
            raise ArchiveError('Error de integridad del archivo ' + name)
        for row in data['cycles']:
            validate_cycle(row)
            restored[row['cycle_id']] = row
    expected = [row for row in ledger['cycles'] if row['slot_at'][:7] in selected]
    if len(restored) != len(expected) or any(
        digest(restored.get(row['cycle_id'])) != digest(row) for row in expected):
        raise ArchiveError('La prueba de restauración ha fallado')
    if source.read_bytes() != original:
        raise ArchiveError('El ledger cambió durante el archivado')
    return {'status': 'prepared_and_verified', 'months': list(selected),
            'cycles_copied': len(expected), 'source_unchanged': True,
            'manifest': str(dest / 'manifest.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--prepare', metavar='NEW_ARCHIVE_DIR', default=None)
    args = parser.parse_args()
    try:
        result = (prepare(args.ledger, args.prepare) if args.prepare
                  else audit(args.ledger))
    except ArchiveError as exc:
        print(json.dumps({'status': 'error', 'reason': str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
