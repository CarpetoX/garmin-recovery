#!/usr/bin/env python3
"""V2.9.6 phase 4: compact INDEX preview, NOT a production ledger replacement.

Requires a verified copy of the *same* current full report_cycles.json in
shards (cycle_shards_v296.py --prepare). Links each compact metadata record to
its exact original cycle, including per-cycle SHA-256-verified snapshots.

Never writes report_cycles.json, never changes any existing archive shard.
"""
import argparse
import json
from pathlib import Path

from .cycle_shards import (
    ShardError, RE_SHARD, canonical_hash, encoded, load_source,
    sha_bytes, verify_archive,
)

VERSION = '2.9.6'
FORMAT = 'ledger_compact_preview_v1'


def _read_index(root):
    file = Path(root) / 'index.json'
    try:
        content = file.read_bytes()
        index = json.loads(content)
    except (OSError, ValueError) as exc:
        raise ShardError('Indice de fragmentos no disponible o no valido') from exc
    if not isinstance(index, dict) or not isinstance(index.get('shards'), list):
        raise ShardError('Indice de fragmentos sin descriptors')
    return index, content


def _safe_refs(index, count):
    refs = []
    for descriptor in index['shards']:
        if not isinstance(descriptor, dict):
            raise ShardError('Descriptor de fragmento invalido')
        path = descriptor.get('path')
        first = descriptor.get('first_index')
        size = descriptor.get('count')
        if (not isinstance(path, str) or RE_SHARD.fullmatch(path) is None
                or type(first) is not int or type(size) is not int
                or size < 1 or first != len(refs)):
            raise ShardError('Indice de fragmentos discontinuo')
        refs.extend({'path': path, 'offset': i} for i in range(size))
    if len(refs) != count:
        raise ShardError('Indice de fragmentos no cubre todos los ciclos')
    return refs


def build(source, archive_dir):
    source, archive_dir = Path(source), Path(archive_dir)
    original, raw = load_source(source)
    restored, info = verify_archive(archive_dir, source)
    if original != restored:
        raise ShardError('Reconstruccion no coincide con origen')
    index, index_bytes = _read_index(archive_dir)
    refs = _safe_refs(index, len(original['cycles']))
    summaries = []
    for i, (row, ref) in enumerate(zip(original['cycles'], refs, strict=False)):
        meta = {k: v for k, v in row.items() if k != 'snapshot'}
        summaries.append({'record_index': i,
                          'cycle_id': row['cycle_id'],
                          'shard_ref': ref,
                          'metadata': meta})
    root = {k: v for k, v in original.items() if k != 'cycles'}
    report = {
        'preview_version': VERSION,
        'schema_version': 3,
        'format': FORMAT,
        'migration_state': 'READ_ONLY_PREVIEW_DO_NOT_REPLACE_REPORT_CYCLES',
        'root_metadata': root,
        'source_bytes_sha256': sha_bytes(raw),
        'source_ledger_sha256': canonical_hash(original),
        'source_cycle_count': len(original['cycles']),
        'source_cycles_sha256': canonical_hash(original['cycles']),
        'shard_index_bytes_sha256': sha_bytes(index_bytes),
        'shard_index_name': 'index.json',
        'snapshot_payloads_stored_only_in_shards': True,
        'cycles': summaries,
    }
    return report


def verify(source, archive_dir, preview):
    source, archive_dir = Path(source), Path(archive_dir)
    original, original_bytes = load_source(source)
    restored, info = verify_archive(archive_dir, source)
    index, index_bytes = _read_index(archive_dir)
    expected_refs = _safe_refs(index, len(original['cycles']))
    if not isinstance(preview, dict):
        raise ShardError('Preview no es objeto')
    if (preview.get('preview_version') != VERSION or
            preview.get('schema_version') != 3 or
            preview.get('format') != FORMAT or
            preview.get('migration_state') != 'READ_ONLY_PREVIEW_DO_NOT_REPLACE_REPORT_CYCLES' or
            preview.get('snapshot_payloads_stored_only_in_shards') is not True):
        raise ShardError('Estado / formato de preview invalido')
    if (preview.get('shard_index_name') != 'index.json' or
            preview.get('shard_index_bytes_sha256') != sha_bytes(index_bytes) or
            preview.get('source_bytes_sha256') != sha_bytes(original_bytes) or
            preview.get('source_ledger_sha256') != canonical_hash(original) or
            preview.get('source_cycles_sha256') != canonical_hash(original['cycles']) or
            type(preview.get('source_cycle_count')) is not int or
            preview['source_cycle_count'] != len(original['cycles'])):
        raise ShardError('Identidad de historico o indice no coincide')
    root = {k: v for k, v in original.items() if k != 'cycles'}
    if preview.get('root_metadata') != root:
        raise ShardError('Metadatos globales no coinciden')
    summaries = preview.get('cycles')
    if not isinstance(summaries, list) or len(summaries) != len(original['cycles']):
        raise ShardError('Falta algun ciclo en indice compacto')
    for i, (entry, row, ref) in enumerate(zip(summaries, restored['cycles'], expected_refs, strict=False)):
        if not isinstance(entry, dict) or set(entry) != {'record_index','cycle_id','shard_ref','metadata'}:
            raise ShardError('Registro compacto mal formado')
        if (type(entry.get('record_index')) is not int or entry['record_index'] != i or
                entry.get('cycle_id') != row.get('cycle_id') or
                entry.get('shard_ref') != ref or
                entry.get('metadata') != {k: v for k, v in row.items() if k != 'snapshot'}):
            raise ShardError('Ciclo compacto no coincide con fragmento: ' + row['cycle_id'])
    if original != restored:
        raise ShardError('No se pudo reconstruir el origen')
    return {
        'version': VERSION,
        'status': 'compact_preview_verified',
        'cycle_count': len(summaries),
        'snapshots_verified': sum(isinstance(x.get('snapshot'), dict) for x in restored['cycles']),
        'legacy_cycles_preserved': sum(x.get('legacy_without_snapshot') is True for x in restored['cycles']),
        'shard_count': len(index['shards']),
        'source_bytes': len(original_bytes),
        'preview_bytes': len(encoded(preview)),
        'preview_reduction_pct': round(100 * (1 - len(encoded(preview))/len(original_bytes)),1) if original_bytes else None,
        'complete_reconstruction': True,
        'production_modified': False,
    }


def write_preview(source, archive_dir, output):
    output = Path(output)
    if output.exists():
        raise ShardError('No se sobrescribe un preview existente')
    preview = build(source, archive_dir)
    result = verify(source, archive_dir, preview)
    if not output.parent.is_dir():
        raise ShardError('Directorio de salida inexistente')
    try:
        with output.open('xb') as f:
            f.write(encoded(preview))
        actual = json.loads(output.read_bytes())
        verify(source, archive_dir, actual)
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--archive-dir', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', metavar='OUTPUT_FILE')
    group.add_argument('--verify', metavar='EXISTING_PREVIEW')
    args = parser.parse_args(argv)
    if args.prepare:
        result = write_preview(args.ledger, args.archive_dir, args.prepare)
    else:
        try:
            preview = json.loads(Path(args.verify).read_bytes())
        except (OSError, ValueError) as exc:
            raise ShardError('No se pudo leer el preview') from exc
        result = verify(args.ledger, args.archive_dir, preview)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except ShardError as exc:
        raise SystemExit('V2.9.6 compact preview: ' + str(exc)) from exc
