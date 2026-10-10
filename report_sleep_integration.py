#!/usr/bin/env python3
"""V2.4.7: conservative report certification with freshness-aware sleep evidence."""
import hashlib
import json
from datetime import datetime, timedelta
import report_delivery_gate as gate

TARGETS = {'0830': '09:05', '1645': '17:10', '2245': '23:10'}
_original_build = gate.build_certificate
_original_snapshot = gate.compact_cycle_snapshot


def sleep_state():
    obj = gate._read_json('morning_sleep_status.json', {})
    return obj if isinstance(obj, dict) else {}


def _parse(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result if result.tzinfo is not None else None
    except ValueError:
        return None


def _validated_sleep(state, now):
    generated = _parse(state.get('generated_at'))
    end = _parse(state.get('sleep_end_local'))
    earliest = _parse(state.get('earliest_definitive_at'))
    # A certificate can only rely on fresh, internally consistent evidence.
    reasons = []
    if state.get('date') != now.date().isoformat():
        reasons.append('wrong_day')
    if state.get('state') != 'confirmed_ready' or state.get('is_definitive') is not True:
        reasons.append('not_confirmed_ready')
    if not generated or generated > now + timedelta(minutes=2) or now - generated > timedelta(minutes=120):
        reasons.append('stale_or_invalid_generation')
    if not end or end.date() != now.date() or end > now:
        reasons.append('invalid_sleep_end')
    if not earliest or not end or abs((earliest - end).total_seconds() - 1800) > 120 or earliest > now:
        reasons.append('margin_not_verified')
    if state.get('recovery_matches_sleep_episode') is not True or state.get('recovery_sleep_fresh') is not True:
        reasons.append('recovery_not_fresh')
    return not reasons, reasons


def build(chain, file_times, now):
    cert = _original_build(chain, file_times, now)
    cert['gate_version'] = '2.4.7'
    slot = chain['slot']['slot']
    cert['target_report_at'] = TARGETS.get(slot, cert['target_report_at'])
    state = sleep_state()
    valid, reasons = _validated_sleep(state, now)
    cert['morning_sleep'] = {
        'state': state.get('state', 'unavailable'),
        'is_definitive_source': state.get('is_definitive') is True,
        'evidence_valid': valid,
        'evidence_issues': reasons,
        'generated_at': state.get('generated_at'),
        'date': state.get('date'),
        'sleep_end_local': state.get('sleep_end_local'),
        'earliest_definitive_at': state.get('earliest_definitive_at'),
    }
    cert['physiological_report_status'] = (
        'definitive' if valid else 'provisional'
    ) if slot == '0830' else 'not_evaluated_for_this_slot'
    cert.setdefault('limitations', []).append(
        'Data-ready certificate does not prove completed sleep or ChatGPT delivery; '
        'morning sleep evidence must be fresh and validated.'
    )
    return cert


def snapshot(cert):
    data, _ = _original_snapshot(cert)
    data['morning_sleep'] = cert.get('morning_sleep', {})
    data['physiological_report_status'] = cert.get('physiological_report_status', 'unknown')
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return data, hashlib.sha256(raw).hexdigest()


gate.build_certificate = build
gate.compact_cycle_snapshot = snapshot
gate.SLOTS = tuple((h, m, code, TARGETS.get(code, target)) for h, m, code, target in gate.SLOTS)

if __name__ == '__main__':
    raise SystemExit(gate.main())
