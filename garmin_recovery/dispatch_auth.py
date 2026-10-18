#!/usr/bin/env python3
"""V2.9.1: authenticate Apps Script dispatches without disrupting manual runs.

A normal workflow_dispatch without signed fields stays unattributed; its event
name alone is never proof of a human caller. Signed calls include an HMAC of
source/cycle/timestamp/nonce, verified before Sync accesses any data source.
The secret and incoming signature are NEVER written to output reports.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_SLOTS = {'0830', '1645', '2245'}
KEY_NAME = 'GARMIN_ORIGIN_KEY_V291'
MAX_AGE_SECONDS = 1800  # GitHub may queue a valid run for a while.
MAX_FUTURE_SECONDS = 120
REQUIRED = ('origin_source', 'cycle_id', 'requested_at', 'request_id', 'origin_proof')
UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
CYCLE_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}-(0830|1645|2245)$')
UTC_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')


class InvalidOrigin(ValueError):
    """Invalid signed request; never run Sync on such a request."""


def canonical_message(origin_source, cycle_id, requested_at, request_id):
    return '\n'.join(('garmin-v291', origin_source, cycle_id, requested_at, request_id)).encode('utf-8')


def signed_fields(event_name, event):
    if event_name == 'workflow_dispatch':
        return event.get('inputs') or {}
    if event_name == 'repository_dispatch':
        return event.get('client_payload') or {}
    return {}


def classify(event_name, event, key=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise InvalidOrigin('Validation time must be timezone-aware')
    if not isinstance(event, dict):
        raise InvalidOrigin('GitHub event must be a JSON object')
    base = {'schema_version': 1, 'version': '2.9.1',
            'github_event': event_name, 'source_verified': False,
            'auth_method': None, 'origin_source': 'unknown',
            'cycle_id': None, 'request_id': None, 'requested_at': None}
    if event_name == 'schedule':
        base.update(origin_source='github_schedule', source_verified=True,
                    auth_method='github_event_type')
        return base
    if event_name not in ('workflow_dispatch', 'repository_dispatch'):
        raise InvalidOrigin('Unsupported Sync trigger')
    if event_name == 'repository_dispatch' and event.get('action') not in (None, 'garmin-sync'):
        raise InvalidOrigin('Unexpected repository_dispatch event type')
    fields = signed_fields(event_name, event)
    if not isinstance(fields, dict):
        raise InvalidOrigin('Dispatch fields must be a JSON object')
    signed_present = any(fields.get(name) for name in REQUIRED)
    if not signed_present:
        base['origin_source'] = 'workflow_dispatch_unattributed' if event_name == 'workflow_dispatch' else 'repository_dispatch_unattributed'
        return base
    if any(not isinstance(fields.get(name), str) or not fields[name] for name in REQUIRED):
        raise InvalidOrigin('Incomplete signed provenance fields')
    origin = fields['origin_source']
    cycle = fields['cycle_id']
    request_time = fields['requested_at']
    request_id = fields['request_id']
    proof = fields['origin_proof']
    if origin != 'apps_script_backup':
        raise InvalidOrigin('Unexpected signed origin')
    if not CYCLE_PATTERN.fullmatch(cycle):
        raise InvalidOrigin('Invalid cycle ID')
    if not UUID_PATTERN.fullmatch(request_id):
        raise InvalidOrigin('Invalid request ID')
    if not UTC_PATTERN.fullmatch(request_time):
        raise InvalidOrigin('Timestamp must be UTC RFC3339')
    if len(proof) != 64 or any(c not in '0123456789abcdefABCDEF' for c in proof):
        raise InvalidOrigin('Invalid signature format')
    try:
        timestamp = datetime.fromisoformat(request_time.replace('Z', '+00:00'))
        cycle_date = datetime.strptime(cycle[:10], '%Y-%m-%d').date()
    except ValueError as exc:
        raise InvalidOrigin('Invalid timestamp or cycle date') from exc
    age = (now - timestamp).total_seconds()
    if not -MAX_FUTURE_SECONDS <= age <= MAX_AGE_SECONDS:
        raise InvalidOrigin('Signed request outside accepted freshness window')
    # Distinguish a signed callback for one schedule slot from an unrelated date.
    if abs((timestamp.date() - cycle_date).days) > 1:
        raise InvalidOrigin('Cycle date does not match signed request')
    if not isinstance(key, str) or len(key) < 32:
        raise InvalidOrigin('Missing signing key or key too short')
    expected = hmac.new(key.encode('utf-8'),
                        canonical_message(origin, cycle, request_time, request_id),
                        hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, proof.lower()):
        raise InvalidOrigin('HMAC verification failed')
    base.update(source_verified=True, origin_source='apps_script_backup',
                auth_method='hmac_sha256_shared_secret_v291',
                cycle_id=cycle, requested_at=request_time, request_id=request_id)
    return base


def attach_lineage(path, origin_path, run_id):
    lineage = json.loads(Path(path).read_text(encoding='utf-8'))
    origin = json.loads(Path(origin_path).read_text(encoding='utf-8'))
    if lineage.get('stage') != 'sync' or str(lineage.get('run_id')) != str(run_id):
        raise InvalidOrigin('Lineage snapshot does not match current Sync run')
    root = lineage.get('root')
    if not isinstance(root, dict) or str(root.get('run_id')) != str(run_id):
        raise InvalidOrigin('Lineage root mismatch')
    if origin.get('github_event') != lineage.get('stages', {}).get('sync', {}).get('event'):
        raise InvalidOrigin('Origin event mismatch')
    root['origin_v291'] = origin
    if origin.get('source_verified') and origin.get('origin_source') == 'apps_script_backup':
        root['origin_certainty'] = 'apps_script_hmac_sha256_v291'
    Path(path).write_text(json.dumps(lineage, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return lineage


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='.garmin_origin_v291.json')
    parser.add_argument('--attach-lineage', default=None)
    parser.add_argument('--origin-file', default='.garmin_origin_v291.json')
    args = parser.parse_args(argv)
    if args.attach_lineage:
        result = attach_lineage(args.attach_lineage, args.origin_file, os.environ.get('GITHUB_RUN_ID', ''))
        print(json.dumps({'stage': 'sync', 'attached_origin': result['root']['origin_v291']['origin_source']}))
        return
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path:
        raise InvalidOrigin('Missing GitHub event payload path')
    event = json.loads(Path(event_path).read_text(encoding='utf-8'))
    result = classify(os.environ.get('GITHUB_EVENT_NAME', ''), event,
                      os.environ.get(KEY_NAME))
    result['checked_at'] = datetime.now(timezone.utc).isoformat()
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'origin': result['origin_source'],
                      'verified': result['source_verified'],
                      'auth_method': result['auth_method'],
                      'cycle_id': result['cycle_id']}))


if __name__ == '__main__':
    main()
