"""V5 security boundary: validate certificate and emit NON-PERSONAL status only.
Never upload this output as an authenticated personal dashboard payload.
"""
import argparse
import json
from pathlib import Path

EXPECTED = ('sync', 'heart', 'advanced', 'crossfit')

def inspect_certificate(cert):
    errors = []
    if cert.get('status') != 'ready':
        errors.append('certificate_not_ready')
    if not isinstance(cert.get('cycle_id'), str) or not cert['cycle_id']:
        errors.append('cycle_id_missing')
    chain = cert.get('chain')
    if not isinstance(chain, dict):
        errors.append('chain_missing')
    else:
        for stage in EXPECTED:
            item = chain.get(stage)
            if not isinstance(item, dict) or not isinstance(item.get('id'), int):
                errors.append(f'{stage}_run_missing')
            elif stage != 'crossfit' and item.get('conclusion') != 'success':
                errors.append(f'{stage}_not_success')
            elif stage == 'crossfit' and item.get('conclusion') not in ('success', 'publishing_in_same_job'):
                errors.append('crossfit_invalid_state')
    return {'eligible_for_further_verification': not errors, 'errors': errors,
            'note': 'NOT a proof of hashes, commit success, freshness, identity or delivery'}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--certificate', type=Path, required=True)
    args = p.parse_args()
    result = inspect_certificate(json.loads(args.certificate.read_text(encoding='utf-8')))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['eligible_for_further_verification'] else 2)

if __name__ == '__main__':
    main()
