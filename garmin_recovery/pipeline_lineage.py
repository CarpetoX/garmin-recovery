#!/usr/bin/env python3
"""V2.9: explicit workflow_run ancestry, propagated through GitHub run artifacts.

Each job publishes a 14-day GitHub artifact containing this JSON. An incoming
workflow_run.id is authoritative ONLY for its direct upstream run; older
ancestors are verified against the previous run's artifact, never guessed from
nearby timestamps. Missing artifacts yield PARTIAL, not fabricated links.

This file describes provenance; it is not proof that a ChatGPT report was sent.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

STAGES = ('sync', 'heart', 'advanced', 'crossfit')
UPSTREAM = {'heart': ('sync', 'Garmin Recovery Sync'),
            'advanced': ('heart', 'Garmin Heart Rate Enrichment'),
            'crossfit': ('advanced', 'Garmin Advanced Analytics')}


def valid_run_id(value):
    return str(value).isdigit() and int(value) > 0 and not isinstance(value, bool)


def parse_event(text):
    try:
        out = json.loads(text)
    except (TypeError, ValueError) as e:
        raise ValueError('GitHub event JSON unreadable') from e
    if not isinstance(out, dict):
        raise ValueError('GitHub event must be an object')
    return out


def _stage_row(run_id, event_name, parent_id=None):
    return {'run_id': int(run_id), 'event': event_name,
            'parent_run_id': int(parent_id) if parent_id is not None else None}


def create(stage, run_id, event_name, event=None, parent=None):
    """Return an immutable-in-spirit lineage snapshot; no GitHub API required."""
    if stage not in STAGES or not valid_run_id(run_id):
        raise ValueError('Invalid stage or run ID')
    if not isinstance(event_name, str) or not event_name:
        raise ValueError('Invalid event name')
    event = event or {}
    if not isinstance(event, dict):
        raise ValueError('Invalid event payload')
    root = {'run_id': int(run_id), 'event': event_name,
            'origin_certainty': 'event_type_only'}
    evidence = []
    parent_run = None
    status = 'independent_unverified'
    stages = {stage: _stage_row(run_id, event_name)}
    if stage == 'sync':
        if event_name not in ('schedule', 'workflow_dispatch', 'repository_dispatch'):
            raise ValueError('Sync event type unsupported')
        root['origin_certainty'] = ('github_schedule' if event_name == 'schedule'
                                    else 'dispatch_sender_unverified')
        status = 'root_recorded'
    elif event_name == 'workflow_run':
        payload = event.get('workflow_run')
        if not isinstance(payload, dict):
            raise ValueError('Missing upstream workflow_run payload')
        parent_run = payload.get('id')
        if not valid_run_id(parent_run):
            raise ValueError('Invalid upstream workflow_run.id')
        predecessor, expected_name = UPSTREAM[stage]
        if payload.get('name') != expected_name or payload.get('conclusion') != 'success':
            raise ValueError('Unexpected parent workflow name or conclusion')
        parent_run = int(parent_run)
        stages[stage] = _stage_row(run_id, event_name, parent_run)
        evidence.append({'from': predecessor, 'to': stage,
                         'parent_run_id': parent_run, 'child_run_id': int(run_id),
                         'evidence': 'github_workflow_run_event'})
        status = 'partial_unverified_parent_artifact'
        if isinstance(parent, dict):
            previous = parent.get('stages')
            if (parent.get('schema_version') == 1 and isinstance(previous, dict)
                    and isinstance(previous.get(predecessor), dict)
                    and previous[predecessor].get('run_id') == parent_run
                    and parent.get('status') in ('root_recorded', 'exact_chain_verified')):
                if any(k not in STAGES[:STAGES.index(stage)] for k in previous):
                    raise ValueError('Parent lineage contains impossible future stages')
                stages = {**previous, stage: stages[stage]}
                root = parent.get('root')
                if not isinstance(root, dict) or not valid_run_id(root.get('run_id')):
                    raise ValueError('Parent root is invalid')
                evidence = [*(parent.get('links') or []), *evidence]
                status = 'exact_chain_verified'
            else:
                status = 'partial_parent_mismatch'
    elif event_name == 'workflow_dispatch':
        # A manual run has no trustworthy parent regardless of timestamps.
        pass
    else:
        raise ValueError('Unexpected event for non-root stage')
    return {'schema_version': 1, 'version': '2.9', 'status': status,
            'stage': stage, 'run_id': int(run_id), 'parent_run_id': parent_run,
            'root': root, 'stages': stages, 'links': evidence,
            'exact_link_count': len(evidence),
            'complete_chain_verified': status == 'exact_chain_verified' and len(stages) == 4,
            'note': ('Exact parent link is from GITHUB_EVENT_PATH; further ancestors '
                     'need matching previous-run artifact. No timestamp inference; '
                     'no ChatGPT delivery acknowledgment.')}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=STAGES, required=True)
    parser.add_argument('--parent', default='.lineage_parent/pipeline_lineage_v29.json')
    parser.add_argument('--out', default='pipeline_lineage_v29.json')
    args = parser.parse_args(argv)
    event_name = os.environ.get('GITHUB_EVENT_NAME', '')
    event_path = os.environ.get('GITHUB_EVENT_PATH', '')
    event = parse_event(Path(event_path).read_text(encoding='utf-8')) if event_path else {}
    parent_path = Path(args.parent)
    parent = None
    if parent_path.is_file():
        try:
            parent = json.loads(parent_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            parent = {'status': 'corrupt_parent_artifact'}
    snapshot = create(args.stage, os.environ.get('GITHUB_RUN_ID', ''), event_name, event, parent)
    snapshot['generated_at'] = datetime.now(timezone.utc).isoformat()
    Path(args.out).write_text(json.dumps(snapshot, indent=2, ensure_ascii=False,
                                         allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': snapshot['status'], 'stage': args.stage,
                      'exact_link_count': snapshot['exact_link_count'],
                      'complete_chain_verified': snapshot['complete_chain_verified']}))


if __name__ == '__main__':
    main()
