#!/usr/bin/env python3
"""Garmin Recovery V2.9.6: lector INDEPENDIENTE de índice + fragmentos.

FASE EXPERIMENTAL. Reconstruye un ledger v2 en memoria usando solo el índice
compacto y sus fragmentos verificados, sin necesitar report_cycles.json.
No sustituye la ruta de lectura/escritura de producción ni publica datos.
"""
import argparse
import json
from pathlib import Path

from cycle_shards_v296 import (
    ShardError, canonical_hash, load_source, sha_bytes, verify_archive,
)
from ledger_compact_preview_v296 import FORMAT, VERSION, _read_index, _safe_refs

PREVIEW_STATE = 'READ_ONLY_PREVIEW_DO_NOT_REPLACE_REPORT_CYCLES'


def reconstruct(preview_path, archive_dir, original_path=None):
    """Devuelve (ledger completo, diagnóstico), sin escribir ningún archivo.

    Compara todos los elementos del índice contra los fragmentos en disco,
    valida el SHA-256 de cada snapshot y las identidades SHA del conjunto.
    original_path es opcional: demuestra reconstrucción sin ledger principal.
    """
    try:
        preview = json.loads(Path(preview_path).read_bytes())
    except (OSError, ValueError) as exc:
        raise ShardError('Índice compacto ilegible') from exc
    if not isinstance(preview, dict):
        raise ShardError('Índice compacto: se esperaba un objeto JSON')
    if (preview.get('preview_version') != VERSION
            or preview.get('schema_version') != 3
            or preview.get('format') != FORMAT
            or preview.get('migration_state') != PREVIEW_STATE
            or preview.get('snapshot_payloads_stored_only_in_shards') is not True):
        raise ShardError('Índice compacto incompatible; no autorizar producción')

    ledger, info = verify_archive(archive_dir, source=None)
    archive_index, archive_index_bytes = _read_index(archive_dir)
    records = ledger['cycles']
    refs = _safe_refs(archive_index, len(records))
    source_count = preview.get('source_cycle_count')
    if type(source_count) is not int or source_count != len(records):
        raise ShardError('Número de ciclos compacto incorrecto')
    if (preview.get('shard_index_name') != 'index.json'
            or preview.get('shard_index_bytes_sha256') != sha_bytes(archive_index_bytes)
            or preview.get('source_bytes_sha256') != archive_index.get('source_file_sha256')
            or preview.get('source_ledger_sha256') != canonical_hash(ledger)
            or preview.get('source_cycles_sha256') != canonical_hash(records)
            or preview.get('root_metadata') != {k: v for k, v in ledger.items() if k != 'cycles'}):
        raise ShardError('El índice compacto no coincide con los fragmentos')
    entries = preview.get('cycles')
    if not isinstance(entries, list) or len(entries) != len(records):
        raise ShardError('Faltan registros en el índice compacto')
    for i, (entry, row, ref) in enumerate(zip(entries, records, refs, strict=False)):
        if (not isinstance(entry, dict)
                or set(entry) != {'record_index', 'cycle_id', 'shard_ref', 'metadata'}
                or type(entry.get('record_index')) is not int
                or entry['record_index'] != i
                or entry.get('cycle_id') != row['cycle_id']
                or entry.get('shard_ref') != ref
                or entry.get('metadata') != {k: v for k, v in row.items() if k != 'snapshot'}):
            raise ShardError('Índice compacto corrupto o desordenado')

    original_verified = False
    if original_path is not None:
        original, original_bytes = load_source(original_path)
        if (original != ledger
                or sha_bytes(original_bytes) != preview.get('source_bytes_sha256')):
            raise ShardError('El original ya no coincide con el índice preparado')
        original_verified = True

    return ledger, {
        'version': VERSION,
        'status': 'read_only_independent_reconstruction_verified',
        'certificates': len(records),
        'snapshots_verified': sum(isinstance(c.get('snapshot'), dict) for c in records),
        'legacy_records_preserved': sum(c.get('legacy_without_snapshot') is True for c in records),
        'shards_verified': info['shard_count'],
        'ledger_sha256': canonical_hash(ledger),
        'original_cross_checked': original_verified,
        'source_writes': 0,
        'production_cutover': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', type=Path, required=True)
    parser.add_argument('--archive-dir', type=Path, required=True)
    parser.add_argument('--original', type=Path, default=None)
    args = parser.parse_args(argv)
    _, diagnostic = reconstruct(args.preview, args.archive_dir, args.original)
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))
    return diagnostic


if __name__ == '__main__':
    try:
        main()
    except ShardError as exc:
        raise SystemExit('V2.9.6 lector seguro: ' + str(exc)) from exc
