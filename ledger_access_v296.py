#!/usr/bin/env python3
"""V2.9.6 - read-only ledger access adapter. Not connected to production.

Explicit modes only:
  legacy_only: read and validate original ledger, the production default.
  shadow_compare: independently reconstruct shards and compare with original.
  shards_only: read only shards without needing the original (future cutover).

NO automatic fallbacks, NO writes, NO reformatting, NO migration. The main
storage writer/readers must NOT be changed until a verified cutover is planned.
"""
import argparse
import json
from pathlib import Path

from cycle_shards_v296 import ShardError, canonical_hash, load_source
from ledger_reader_v296 import reconstruct

VERSION = '2.9.6'
MODES = frozenset({'legacy_only', 'shadow_compare', 'shards_only'})


def read_compatible(legacy_path='report_cycles.json', *, mode='legacy_only',
                    preview_path=None, archive_dir=None):
    """Return (original ledger dict, technical audit). Never modifies files.

    shadow_compare requires same-source hashes AND exact semantic comparison.
    shards_only is *explicit*: no fallback to legacy on corrupt/missing shards.
    No caller is redirected here in production by installing this module.
    """
    if mode not in MODES:
        raise ShardError('Modo de lectura no autorizado; usar legacy_only, shadow_compare o shards_only')
    if mode == 'legacy_only':
        if preview_path is not None or archive_dir is not None:
            raise ShardError('legacy_only no admite rutas de fragmentos: evitar mezclas silenciosas')
        original, raw = load_source(legacy_path)
        return original, {
            'version': VERSION, 'mode': mode, 'status': 'validated_legacy',
            'certificates': len(original['cycles']),
            'source_bytes': len(raw), 'read_only': True, 'production_cutover': False,
            'source_original_verified': True, 'source_writes': 0,
        }

    if not preview_path or not archive_dir:
        raise ShardError('Las rutas de índice y fragmentos son obligatorias')

    if mode == 'shards_only':
        ledger, report = reconstruct(preview_path, archive_dir)
        return ledger, {
            'version': VERSION, 'mode': mode, 'status': 'shards_verified',
            'certificates': len(ledger['cycles']),
            'snapshots_verified': report['snapshots_verified'],
            'legacy_records_preserved': report['legacy_records_preserved'],
            'shard_count': report['shards_verified'],
            'source_original_verified': False,
            'read_only': True, 'production_cutover': False, 'source_writes': 0,
        }

    # Shadow mode: require both representations and NEVER accept drift.
    original, original_bytes = load_source(legacy_path)
    reconstructed, report = reconstruct(preview_path, archive_dir, original_path=legacy_path)
    if original != reconstructed or canonical_hash(original) != canonical_hash(reconstructed):
        raise ShardError('Diferencia entre el histórico original y el fragmentado')
    # Detect a concurrent append/update while shadow verification was running.
    try:
        if Path(legacy_path).read_bytes() != original_bytes:
            raise ShardError('El original cambió durante la comparación; reintentar tras el ciclo')
    except OSError as exc:
        raise ShardError('No se pudo releer el histórico tras la comparación') from exc
    return original, {
        'version': VERSION, 'mode': mode, 'status': 'shadow_cross_checked',
        'certificates': len(original['cycles']),
        'snapshots_verified': report['snapshots_verified'],
        'legacy_records_preserved': report['legacy_records_preserved'],
        'shard_count': report['shards_verified'],
        'source_original_verified': True,
        'read_only': True, 'production_cutover': False, 'source_writes': 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--mode', required=True, choices=sorted(MODES))
    parser.add_argument('--preview', default=None)
    parser.add_argument('--archive-dir', default=None)
    opts = parser.parse_args(argv)
    _, result = read_compatible(opts.ledger, mode=opts.mode,
                                preview_path=opts.preview, archive_dir=opts.archive_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    try:
        main()
    except ShardError as exc:
        raise SystemExit('V2.9.6 lector compatible: ' + str(exc)) from exc
