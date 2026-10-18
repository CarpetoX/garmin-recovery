#!/usr/bin/env python3
"""Idempotent, fail-closed auto-dispatch for the existing V2.9.6 shadow publisher.

Only reads the production ledger and the remote mirror state; NEVER writes main,
archives, or the shadow branch. HTTP 204 means dispatch accepted, NOT published.
The existing shadow workflow independently verifies all records before writing.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
from urllib import error, parse, request

from .cycle_shards import load_source

BRANCH = 'garmin-v296-shadow'
EVENT = 'garmin-shadow-publish'
FORMAT = 'shadow_persist_candidate_v1'
SHA256 = re.compile(r'^[0-9a-f]{64}$')
API_VERSION = '2022-11-28'


class AutoShadowError(RuntimeError):
    pass


def validate_state(state, digest, count):
    """Return decision without ever classifying malformed state as missing."""
    if not isinstance(state, dict) or state.get('format') != FORMAT or state.get('version') != '2.9.6':
        raise AutoShadowError('Estado del espejo inexistente o incompatible: intervencion manual requerida')
    if (state.get('full_original_retained') is not True
            or state.get('production_cutover') is not False
            or state.get('authorizes_replacing_report_cycles') is not False):
        raise AutoShadowError('El espejo remoto no garantiza conservacion de produccion')
    old_count = state.get('certificate_count')
    old_digest = state.get('source_file_sha256')
    if (type(old_count) is not int or old_count < 0 or not isinstance(old_digest, str)
            or not SHA256.fullmatch(old_digest)):
        raise AutoShadowError('Metadatos del espejo remoto invalidos')
    if old_count > count:
        raise AutoShadowError('STOP: el historial de main tiene menos certificados que el espejo')
    if old_digest == digest:
        if old_count != count:
            raise AutoShadowError('STOP: mismo SHA-256 con conteo de certificados diferente')
        return 'already_mirrored'
    return 'dispatch_required'


def github_request(url, token, method='GET', payload=None, opener=request.urlopen):
    body = json.dumps(payload, separators=(',', ':')).encode('utf-8') if payload is not None else None
    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': API_VERSION,
        'User-Agent': 'Garmin-V296-Shadow-Auto-Dispatch',
    }
    req = request.Request(url, data=body, method=method, headers=headers)
    try:
        with opener(req, timeout=20) as response:
            return response.status, response.read()
    except error.HTTPError as exc:
        raise AutoShadowError('GitHub API HTTP ' + str(exc.code) + ' al comprobar o solicitar el espejo') from None
    except error.URLError as exc:
        raise AutoShadowError('No fue posible contactar a GitHub: ' + type(exc.reason).__name__) from None


def fetch_mirror_state(repo, token, opener=request.urlopen):
    # 404 is NOT treated as an empty mirror: never re-bootstrap a deleted branch.
    url = 'https://api.github.com/repos/' + repo + '/contents/mirror/state.json?ref=' + parse.quote(BRANCH)
    code, raw = github_request(url, token, opener=opener)
    if code != 200:
        raise AutoShadowError('Respuesta inesperada al obtener el estado del espejo')
    try:
        envelope = json.loads(raw)
        if envelope.get('encoding') != 'base64':
            raise ValueError('GitHub no entrego base64')
        encoded = envelope['content']
        if not isinstance(encoded, str):
            raise ValueError('GitHub content no es una cadena')
        state = json.loads(base64.b64decode(''.join(encoded.split()), validate=True))
    except (AttributeError, TypeError, KeyError, ValueError, UnicodeDecodeError, binascii.Error) as exc:
        raise AutoShadowError('Estado remoto ilegible; no se iniciara ninguna publicacion') from exc
    return state


def dispatch_if_needed(ledger_path, repo, token, opener=request.urlopen, run_id=None):
    if not repo or '/' not in repo or not token:
        raise AutoShadowError('Faltan GITHUB_REPOSITORY o GH_TOKEN')
    # load_source verifies all IDs, snapshots and stored snapshot SHA-256.
    ledger, blob = load_source(ledger_path)
    digest = hashlib.sha256(blob).hexdigest()
    count = ledger['count']
    remote = fetch_mirror_state(repo, token, opener)
    decision = validate_state(remote, digest, count)
    info = {'version': '2.9.6-auto', 'source_sha256': digest,
            'certificates': count, 'target_branch': BRANCH,
            'production_cutover': False, 'main_modified': False}
    if decision == 'already_mirrored':
        return {**info, 'status': 'already_mirrored_no_dispatch'}
    payload = {'event_type': EVENT,
               'client_payload': {'source_sha256': digest, 'source_cycle_count': count,
                                  'monitor_run_id': str(run_id or '')[:30]}}
    code, _ = github_request('https://api.github.com/repos/' + repo + '/dispatches',
                             token, method='POST', payload=payload, opener=opener)
    if code != 204:
        raise AutoShadowError('GitHub no acepto el dispatch del espejo: HTTP ' + str(code))
    return {**info, 'status': 'dispatch_accepted_not_yet_published', 'http_status': code}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('report_cycles.json'))
    a = p.parse_args(argv)
    result = dispatch_if_needed(a.source, os.environ.get('GITHUB_REPOSITORY', ''),
                                os.environ.get('GH_TOKEN', ''),
                                run_id=os.environ.get('GITHUB_RUN_ID'))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (AutoShadowError, ValueError, OSError) as exc:
        raise SystemExit('V2.9.6 auto-shadow: ' + str(exc)) from exc
