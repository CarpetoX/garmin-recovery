#!/usr/bin/env python3
"""V3.7.3 read-only, non-blocking monitor observation of afternoon cycle.

No dispatch, no modifications to certificate/ledger, no delivery assertions.
The caller supplies GH_TOKEN with Actions read access. Evidence is fetched
independently from the GitHub Actions API, not inferred from the certificate.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from report_cycle_integration_v371 import evaluate

TZ = ZoneInfo('Europe/Madrid')
STAGES = ('sync', 'heart', 'advanced', 'crossfit')


def observe(root, *, now, fetch_run):
    result = {'version': '3.7.3', 'checked_at': now.isoformat(),
              'state': 'not_eligible', 'chatgpt_delivery': 'unverified_no_receipt'}
    try:
        cert = json.loads((root / 'report_ready.json').read_text(encoding='utf-8'))
        ledger = json.loads((root / 'report_cycles.json').read_text(encoding='utf-8'))
        chain = cert.get('chain', {})
        evidence = {}
        for stage in STAGES:
            run_id = chain[stage]['id']
            if type(run_id) is not int or run_id <= 0:
                raise ValueError('Invalid Actions run ID')
            run = fetch_run(run_id)
            evidence[stage] = {'id': run.get('id'), 'status': run.get('status'),
                               'conclusion': run.get('conclusion')}
        result.update(evaluate(cert, ledger, now=now, actions=evidence))
    except (OSError, KeyError, ValueError, TypeError, IndexError) as exc:
        result['reason'] = f'{type(exc).__name__}: {str(exc)[:160]}'
    return result


def github_fetcher(repo, token):
    if not repo or '/' not in repo or not token:
        raise ValueError('GITHUB_REPOSITORY and GH_TOKEN required')
    def fetch(run_id):
        req = urllib.request.Request(
            f'https://api.github.com/repos/{repo}/actions/runs/{run_id}',
            headers={'Authorization': f'Bearer {token}',
                     'Accept': 'application/vnd.github+json',
                     'User-Agent': 'Garmin-Recovery-Observer/3.7.3'},
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    return fetch


def main():
    now = datetime.now(TZ)
    output = Path('cycle_observation_v373.json')
    try:
        fetch = github_fetcher(os.environ.get('GITHUB_REPOSITORY'), os.environ.get('GH_TOKEN'))
        result = observe(Path('.'), now=now, fetch_run=fetch)
    except Exception as exc:  # diagnostics must not break monitoring
        result = {'version': '3.7.3', 'checked_at': now.isoformat(),
                  'state': 'not_eligible', 'reason': f'{type(exc).__name__}: {str(exc)[:160]}',
                  'chatgpt_delivery': 'unverified_no_receipt'}
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0  # observation never gates production


if __name__ == '__main__':
    sys.exit(main())
