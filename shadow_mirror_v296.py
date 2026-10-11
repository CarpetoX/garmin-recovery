#!/usr/bin/env python3
"""Garmin Recovery V2.9.6: preparar espejo PERSISTIBLE en fase de ensayo.

Esta herramienta NO reemplaza, recorta, escribe o borra report_cycles.json.
NO hace commits. NO publica datos por su cuenta. Se debe ejecutar en una
carpeta temporal y publicar el espejo con un workflow separado, solo tras
validacion y autorizacion. Compatible con lectores V2.9.6 existentes.

Uso:
  python shadow_mirror_v296.py --plan --ledger report_cycles.json
  python shadow_mirror_v296.py --prepare --ledger report_cycles.json --out nuevo_espejo
  python shadow_mirror_v296.py --prepare --ledger report_cycles.json \
      --previous espejo_anterior --out nuevo_espejo
  python shadow_mirror_v296.py --verify --ledger report_cycles.json \
      --candidate nuevo_espejo [--previous espejo_anterior]

El espejo consta de archive/index.json, archive/shards/...,
compact-preview.json y state.json. No se descarta ningun certificado.
"""
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from cycle_shards_v296 import (
    DEFAULT_LIMIT_BYTES, ShardError, canonical_hash, encoded,
    load_source, prepare as shard_prepare, sha_bytes, verify_archive,
)
from ledger_access_v296 import read_compatible
from ledger_compact_preview_v296 import write_preview

VERSION = '2.9.6'
FORMAT = 'shadow_persist_candidate_v1'


def _root_fields(ledger):
    return {k: v for k, v in ledger.items() if k not in ('cycles', 'count')}


def _previous_root(previous):
    if previous is None:
        return None, None
    previous = Path(previous)
    if not previous.is_dir():
        raise ShardError('Espejo anterior inexistente: no autorizar arranque silencioso')
    state_path = previous / 'state.json'
    try:
        state = json.loads(state_path.read_bytes())
    except (OSError, ValueError) as exc:
        raise ShardError('Estado del espejo anterior no disponible') from exc
    if (not isinstance(state, dict) or state.get('format') != FORMAT
            or state.get('version') != VERSION
            or state.get('production_cutover') is not False
            or state.get('full_original_retained') is not True):
        raise ShardError('Estado del espejo anterior incompatible')
    ledger, report = read_compatible(
        previous / 'missing-report-cycles.json', mode='shards_only',
        preview_path=previous / 'compact-preview.json',
        archive_dir=previous / 'archive',
    )
    if (state.get('certificate_count') != len(ledger['cycles'])
            or state.get('source_ledger_sha256') != canonical_hash(ledger)):
        raise ShardError('Espejo anterior con estado incoherente')
    return ledger, state


def _extension(old, new):
    if old is None:
        return 0
    if _root_fields(old) != _root_fields(new):
        raise ShardError('Los metadatos globales historicos cambiaron')
    old_rows = old['cycles']
    new_rows = new['cycles']
    positions = {c['cycle_id']: i for i, c in enumerate(new_rows)}
    last = -1
    for row in old_rows:
        pos = positions.get(row['cycle_id'])
        if pos is None:
            raise ShardError('Certificado antiguo desaparecido: ' + row['cycle_id'])
        if pos <= last:
            raise ShardError('Se altero el orden relativo de certificados anteriores')
        if canonical_hash(new_rows[pos]) != canonical_hash(row):
            raise ShardError('Certificado antiguo modificado: ' + row['cycle_id'])
        last = pos
    return len(old_rows)


def plan(source, previous=None):
    ledger, src_bytes = load_source(source)
    prev, _ = _previous_root(previous)
    old_count = _extension(prev, ledger)
    return {
        'version': VERSION,
        'status': 'safe_shadow_plan',
        'certificates_now': len(ledger['cycles']),
        'certificates_preserved': old_count,
        'new_certificates': len(ledger['cycles']) - old_count,
        'source_sha256': sha_bytes(src_bytes),
        'source_bytes': len(src_bytes),
        'source_writes': 0,
        'production_cutover': False,
    }


def _file_reuse_count(previous, candidate):
    if previous is None:
        return 0
    before = Path(previous) / 'archive'
    after = Path(candidate) / 'archive'
    before_manifest = json.loads((before / 'index.json').read_bytes())
    after_manifest = json.loads((after / 'index.json').read_bytes())
    old_sha = {x['path']: x['file_sha256'] for x in before_manifest['shards']}
    return sum(old_sha.get(x['path']) == x['file_sha256']
               for x in after_manifest['shards'])


def verify_candidate(source, candidate, previous=None):
    ledger, original_bytes = load_source(source)
    prev, _ = _previous_root(previous)
    old_count = _extension(prev, ledger)
    candidate = Path(candidate)
    try:
        state = json.loads((candidate / 'state.json').read_bytes())
    except (OSError, ValueError) as exc:
        raise ShardError('No se puede leer estado de candidato') from exc
    if not isinstance(state, dict):
        raise ShardError('Estado candidato no es objeto JSON')
    if (state.get('format') != FORMAT or state.get('version') != VERSION
            or state.get('production_cutover') is not False
            or state.get('full_original_retained') is not True
            or state.get('source_file_sha256') != sha_bytes(original_bytes)
            or state.get('source_ledger_sha256') != canonical_hash(ledger)
            or type(state.get('certificate_count')) is not int
            or state['certificate_count'] != len(ledger['cycles'])
            or type(state.get('certificates_preserved')) is not int
            or state['certificates_preserved'] != old_count):
        raise ShardError('Candidato no corresponde al origen actual o al espejo anterior')
    original, check = read_compatible(source, mode='shadow_compare',
                     preview_path=candidate / 'compact-preview.json',
                     archive_dir=candidate / 'archive')
    if original != ledger or check['certificates'] != len(ledger['cycles']):
        raise ShardError('Candidato no reconstruye el original completo')
    _, audited = verify_archive(candidate / 'archive', source)
    reused = _file_reuse_count(previous, candidate)
    if source and Path(source).read_bytes() != original_bytes:
        raise ShardError('El histórico cambió durante la verificación del candidato')
    return {
        'version': VERSION, 'status': 'candidate_verified',
        'certificates': len(ledger['cycles']),
        'preserved': old_count,
        'new_certificates': len(ledger['cycles']) - old_count,
        'snapshot_checksums_validated': check['snapshots_verified'],
        'legacy_records_preserved': check['legacy_records_preserved'],
        'shard_count': audited['shard_count'],
        'reusable_unchanged_shards': reused,
        'source_sha256': sha_bytes(original_bytes),
        'production_cutover': False,
        'source_modified': False,
        'committed': False,
    }


def prepare_candidate(source, output, previous=None, max_shard_bytes=DEFAULT_LIMIT_BYTES):
    source, output = Path(source), Path(output)
    if output.exists():
        raise ShardError('No sobrescribir el directorio candidato existente')
    if not output.parent.is_dir():
        raise ShardError('Crear previamente el directorio padre de salida')
    if previous is not None and (output.resolve() == Path(previous).resolve()
                                 or output.resolve().is_relative_to(Path(previous).resolve())):
        raise ShardError('La salida no puede ser el espejo anterior ni su subdirectorio')
    original, orig_bytes = load_source(source)
    prev, _ = _previous_root(previous)
    old_count = _extension(prev, original)
    temp = Path(tempfile.mkdtemp(prefix='.garmin-shadow-v296-', dir=output.parent))
    try:
        shard_prepare(source, temp / 'archive', max_shard_bytes)
        write_preview(source, temp / 'archive', temp / 'compact-preview.json')
        state = {
            'format': FORMAT, 'version': VERSION,
            'source_file_sha256': sha_bytes(orig_bytes),
            'source_ledger_sha256': canonical_hash(original),
            'certificate_count': len(original['cycles']),
            'certificates_preserved': old_count,
            'full_original_retained': True,
            'production_cutover': False,
            'authorizes_replacing_report_cycles': False,
        }
        (temp / 'state.json').write_bytes(encoded(state))
        result = verify_candidate(source, temp, previous)
        if output.exists() or source.read_bytes() != orig_bytes:
            raise ShardError('Candidato/origen cambió durante la generación')
        temp.rename(output)
        temp = None
        return {**result, 'candidate': str(output)}
    finally:
        if temp is not None and temp.exists():
            shutil.rmtree(temp)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--plan', action='store_true')
    modes.add_argument('--prepare', action='store_true')
    modes.add_argument('--verify', action='store_true')
    parser.add_argument('--ledger', default='report_cycles.json')
    parser.add_argument('--previous', default=None)
    parser.add_argument('--out', default=None)
    parser.add_argument('--candidate', default=None)
    parser.add_argument('--max-shard-bytes', type=int, default=DEFAULT_LIMIT_BYTES)
    args = parser.parse_args(argv)
    if args.plan:
        result = plan(args.ledger, args.previous)
    elif args.prepare:
        if not args.out:
            parser.error('--prepare requiere --out')
        result = prepare_candidate(args.ledger, args.out, args.previous, args.max_shard_bytes)
    else:
        if not args.candidate:
            parser.error('--verify requiere --candidate')
        result = verify_candidate(args.ledger, args.candidate, args.previous)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    try:
        main()
    except ShardError as exc:
        raise SystemExit('V2.9.6 espejo seguro: ' + str(exc)) from exc
