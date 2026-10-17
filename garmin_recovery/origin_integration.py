#!/usr/bin/env python3
"""Add verified V2.9.2 origin telemetry to the existing health monitor.

The original monitor writes workflow_health.json. This module runs AFTER it,
reads the same published readiness + CrossFit lineage snapshots, and adds an
advisory V2.9.2 report. It never rewrites the existing schedule or SLO verdict.
A GitHub workflow_dispatch is NOT proof of a person manually starting Sync.
"""
import argparse
import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .origin_monitor import report as origin_report


def _json_object(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        if isinstance(value, dict):
            return value, None
        return None, 'not_a_json_object'
    except FileNotFoundError:
        return None, 'file_not_published'
    except (OSError, ValueError):
        return None, 'unreadable_json'


def integrate(health, lineage=None, certificate=None, now=None):
    """Return (new health, separate origin report), never alter input objects."""
    if not isinstance(health, dict):
        raise ValueError('workflow_health.json must be a JSON object')
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Monitor time must be timezone-aware')
    augmented = copy.deepcopy(health)
    if isinstance(lineage, dict) and isinstance(certificate, dict):
        analysis = origin_report(lineage, certificate, now)
        analysis['status'] = ('verified_current_cycle' if analysis['data_ready'] and
                              analysis['origin']['verified'] else
                              'unattributed_current_cycle' if analysis['data_ready'] else
                              'lineage_or_certificate_unmatched')
    else:
        analysis = {
            'version': '2.9.2', 'checked_at': now.isoformat(),
            'status': 'missing_lineage_or_certificate',
            'cycle_id': certificate.get('cycle_id') if isinstance(certificate, dict) else None,
            'origin': {'source': 'unknown', 'verified': False,
                       'evidence': 'missing_input'},
            'lineage_complete_verified': False,
            'data_ready': False,
            'punctuality': {'sync_delay_minutes': None, 'data_ready_delay_minutes': None},
            'chatgpt_delivery': 'unconfirmed_without_receipt',
            'historical_7_28d_slo': 'unavailable_without_complete_observation_window',
        }
    progress = augmented.get('pipeline_progress')
    progress = progress if isinstance(progress, dict) else {}
    cert_chain = certificate.get('chain') if isinstance(certificate, dict) else None
    cert_chain = cert_chain if isinstance(cert_chain, dict) else {}
    cert_sync = cert_chain.get('sync')
    cert_sync = cert_sync if isinstance(cert_sync, dict) else {}
    certified_sync = cert_sync.get('id')
    observed_sync = progress.get('sync_run_id')
    if observed_sync is not None and certified_sync is not None and observed_sync != certified_sync:
        # A valid *previous* cycle cannot be claimed as the current in-flight one.
        analysis['status'] = 'previous_cycle_only'
        analysis['latest_pipeline_matches_certificate'] = False
    else:
        analysis['latest_pipeline_matches_certificate'] = (observed_sync is not None and observed_sync == certified_sync)

    augmented['origin_monitor_v292'] = analysis
    metrics = augmented.get('operational_quality_v28')
    if isinstance(metrics, dict):
        metrics['origin_monitor_v292'] = {
            'cycle_id': analysis['cycle_id'], 'status': analysis['status'],
            'source': analysis['origin']['source'],
            'source_verified': analysis['origin']['verified'],
            'proof': analysis['origin']['evidence'],
            'latest_pipeline_matches_certificate': analysis['latest_pipeline_matches_certificate'],
            'sync_delay_minutes': analysis['punctuality']['sync_delay_minutes'],
            'data_ready_delay_minutes': analysis['punctuality']['data_ready_delay_minutes'],
        }
        # Do not change bounded-window metrics or remove blockers for past slots.
    slots = augmented.get('schedule_v231')
    if isinstance(slots, dict):
        slots['dispatch_classification_v292'] = (
            'workflow_dispatch_without_proof_is_unattributed_not_manual')
        # V2.3.x used this misleading name for all workflow_dispatch events.
        # Preserve it to avoid breaking old readers, clearly mark its semantics.
        if 'recovered_by_manual' in slots:
            slots['legacy_recovered_by_manual_meaning'] = (
                'unattributed_workflow_dispatch_events_not_confirmed_human_actions')
        slots['recovered_by_confirmed_manual'] = []  # No evidence of human identity in run event.
    for alert in augmented.get('alerts') or []:
        if isinstance(alert, dict) and alert.get('code') == 'cron_missed_dispatch_recovered':
            alert['dispatch_actor_interpretation_v292'] = (
                'not_proven_manual; see origin_monitor_v292 for current cycle proof')
    return augmented, analysis


def _atomic_json(path, obj):
    """Refuse partial/truncated JSON on disk; same-dir replace is atomic."""
    dest = Path(path)
    encoded = json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=dest.parent,
                                         prefix=f'.{dest.name}.', suffix='.tmp',
                                         delete=False) as fh:
            name = fh.name
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(name, dest)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--health', default='workflow_health.json')
    parser.add_argument('--lineage', default='pipeline_lineage_v29.json')
    parser.add_argument('--certificate', default='report_ready.json')
    parser.add_argument('--origin-report', default='origin_monitor_v292.json')
    args = parser.parse_args(argv)
    health, error = _json_object(args.health)
    if error:
        raise SystemExit('Current monitor did not produce valid workflow_health.json: ' + error)
    lineage, lineage_error = _json_object(args.lineage)
    ready, cert_error = _json_object(args.certificate)
    new_health, analysis = integrate(health, lineage, ready)
    if lineage_error or cert_error:
        analysis['missing_inputs'] = {'lineage': lineage_error, 'certificate': cert_error}
        new_health['origin_monitor_v292'] = analysis
    _atomic_json(args.origin_report, analysis)
    _atomic_json(args.health, new_health)
    print(json.dumps({'status': analysis['status'],
                      'cycle_id': analysis['cycle_id'],
                      'origin': analysis['origin']['source'],
                      'source_verified': analysis['origin']['verified']}))


if __name__ == '__main__':
    main()
