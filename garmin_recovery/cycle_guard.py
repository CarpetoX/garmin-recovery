#!/usr/bin/env python3
"""V3.7 read-only afternoon-cycle certificate guard. No delivery assertions."""
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Europe/Madrid')
SOURCES = ('daily_summary.json','weekly_summary.json','garmin_heart_rate.json',
           'recovery_assessment.json','advanced_analytics.json','data_quality.json',
           'crossfit_insights.json')

class CycleNotReady(ValueError):
    pass

def stamp(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.astimezone(TZ) if dt.tzinfo else None
    except (ValueError, AttributeError, TypeError):
        return None

def validate_certificate(cert, *, cycle_id, now, source_data=None):
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(TZ)
    if cert.get('status') != 'ready' or cert.get('cycle_id') != cycle_id:
        raise CycleNotReady('Certificate absent, not ready, or wrong cycle')
    try:
        expected = datetime.strptime(cycle_id, '%Y-%m-%d-%H%M').replace(tzinfo=TZ)
    except ValueError as exc:
        raise CycleNotReady('Invalid cycle identifier') from exc
    if expected.strftime('%H%M') != '1645' or expected.date() != now.date():
        raise CycleNotReady('Not the requested local afternoon cycle')
    verified = stamp(cert.get('verified_at'))
    if not verified or verified < expected or verified > now:
        raise CycleNotReady('Certificate verification is missing or in the future')
    chain = cert.get('chain') or {}
    previous = None
    for stage in ('sync','heart','advanced','crossfit'):
        step = chain.get(stage) or {}
        if not isinstance(step.get('id'), int) or step['id'] <= 0:
            raise CycleNotReady('Missing run ID: ' + stage)
        start, end = stamp(step.get('started_at')), stamp(step.get('finished_at'))
        if not start or not end or end < start or end > now:
            raise CycleNotReady('Invalid stage timing: ' + stage)
        if previous and start < previous - timedelta(minutes=2):
            raise CycleNotReady('Stage chronology mismatch: ' + stage)
        previous = end
        allowed = ('success','publishing_in_same_job') if stage == 'crossfit' else ('success',)
        if step.get('conclusion') not in allowed:
            raise CycleNotReady('Stage not successful: ' + stage)
    times = cert.get('source_generated_at') or {}
    for name in SOURCES:
        t = stamp(times.get(name))
        if not t or t < expected or t > now:
            raise CycleNotReady('Missing/stale/future source: ' + name)
        if source_data is not None:
            obj = source_data.get(name)
            if not isinstance(obj, dict) or obj.get('generated_at') != times[name]:
                raise CycleNotReady('Source timestamp mismatch: ' + name)
    return {'state':'eligible_for_report','cycle_id':cycle_id,
            'verified_at':verified.isoformat(),
            'sync_run_id':chain['sync']['id'],
            'note':'Readiness only; no message delivery confirmation'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--now', help='ISO timestamp; defaults to real clock')
    parser.add_argument('--cycle-id', help='Exact YYYY-MM-DD-1645')
    args = parser.parse_args()
    now = stamp(args.now) if args.now else datetime.now(TZ)
    if not now:
        parser.error('Invalid timezone-aware --now')
    cycle_id = args.cycle_id or now.strftime('%Y-%m-%d-1645')
    try:
        cert = json.loads((args.root/'report_ready.json').read_text(encoding='utf-8'))
        result = validate_certificate(cert,cycle_id=cycle_id,now=now)
    except (OSError,ValueError,TypeError) as exc:
        result = {'state':'not_ready','reason':str(exc)[:180]}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['state']=='eligible_for_report' else 2

if __name__=='__main__':
    raise SystemExit(main())
