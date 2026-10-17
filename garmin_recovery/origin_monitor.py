#!/usr/bin/env python3
"""Garmin V2.9.2: read-only report of verified origin and pipeline punctuality.

An unsigned workflow_dispatch is never assumed manual or Apps Script.
Trusted V2.9.1 proof is read from the Sync lineage artifact; HMAC verification
itself belongs to garmin_dispatch_auth_v291.py, before data-source access.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _date(value):
    if not isinstance(value, str):
        return None
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return date if date.tzinfo else None
    except ValueError:
        return None


def origin(lineage):
    root = lineage.get('root') if isinstance(lineage, dict) else None
    root = root if isinstance(root, dict) else {}
    event = root.get('event')
    proof = root.get('origin_v291')
    proof = proof if isinstance(proof, dict) else {}
    if event == 'schedule':
        return {'source': 'github_schedule', 'verified': True,
                'evidence': 'github_event_type', 'event': event}
    if event in ('workflow_dispatch', 'repository_dispatch'):
        if (proof.get('github_event') == event and proof.get('source_verified') is True
                and proof.get('origin_source') == 'apps_script_backup'
                and proof.get('auth_method') == 'hmac_sha256_shared_secret_v291'
                and isinstance(proof.get('cycle_id'), str)):
            return {'source': 'apps_script_backup', 'verified': True,
                    'evidence': 'sync_hmac_validated_v291', 'event': event,
                    'cycle_id': proof['cycle_id']}
        return {'source': 'dispatch_unattributed', 'verified': False,
                'evidence': 'event_type_only', 'event': event}
    return {'source': 'unknown', 'verified': False,
            'evidence': 'no_supported_root_event', 'event': event}


def report(lineage, ready, now=None):
    now = now or datetime.now(timezone.utc)
    if not isinstance(ready, dict) or not isinstance(lineage, dict):
        raise ValueError('Inputs must be JSON objects')
    chain = ready.get('chain')
    chain = chain if isinstance(chain, dict) else {}
    sync = chain.get('sync') if isinstance(chain.get('sync'), dict) else {}
    crossfit = chain.get('crossfit') if isinstance(chain.get('crossfit'), dict) else {}
    root = lineage.get('root') if isinstance(lineage.get('root'), dict) else {}
    linked = (lineage.get('stage') == 'crossfit'
              and lineage.get('complete_chain_verified') is True
              and type(sync.get('id')) is int and sync['id'] > 0
              and sync['id'] == root.get('run_id')
              and crossfit.get('id') == lineage.get('run_id'))
    identity = origin(lineage) if linked else {
        'source': 'unknown', 'verified': False,
        'evidence': 'lineage_certificate_unmatched', 'event': None}
    if identity.get('cycle_id') and identity['cycle_id'] != ready.get('cycle_id'):
        identity = {'source': 'unknown', 'verified': False,
                    'evidence': 'signed_cycle_mismatch', 'event': identity['event']}
    slot = _date(ready.get('slot_at'))
    started = _date(sync.get('started_at')) if linked else None
    certified = _date(ready.get('verified_at')) if linked else None
    def delay(end):
        return round((end - slot).total_seconds() / 60, 2) if slot and end and end >= slot else None
    return {'version': '2.9.2', 'checked_at': now.isoformat(),
            'cycle_id': ready.get('cycle_id'), 'origin': identity,
            'lineage_complete_verified': linked,
            'exact_links': lineage.get('exact_link_count') if linked else None,
            'punctuality': {'sync_delay_minutes': delay(started),
                            'data_ready_delay_minutes': delay(certified)},
            'data_ready': ready.get('status') == 'ready' and linked,
            'chatgpt_delivery': 'unconfirmed_without_receipt',
            'historical_7_28d_slo': 'unavailable_without_complete_observation_window'}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--lineage', default='pipeline_lineage_v29.json')
    parser.add_argument('--certificate', default='report_ready.json')
    parser.add_argument('--out', default='origin_monitor_v292.json')
    args = parser.parse_args(argv)
    lineage = json.loads(Path(args.lineage).read_text(encoding='utf-8'))
    certificate = json.loads(Path(args.certificate).read_text(encoding='utf-8'))
    result = report(lineage, certificate)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'cycle_id': result['cycle_id'], 'origin': result['origin']['source'],
                      'verified': result['origin']['verified']}))


if __name__ == '__main__':
    main()
