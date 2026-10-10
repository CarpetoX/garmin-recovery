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


def live_sensor_summary(provenance, now):
    """Audit age of actual HR/Body Battery samples; NEVER alter recovery scores."""
    details = {}
    for key in ('heart_rate_live', 'body_battery_live'):
        source = provenance.get(key) if isinstance(provenance, dict) else None
        source = source if isinstance(source, dict) else {}
        measured = _parse(source.get('measured_at'))
        minutes = round((now - measured).total_seconds() / 60, 1) if measured else None
        if minutes is None:
            state = 'unknown'
        elif minutes < -2:
            state = 'invalid_future_measurement'
        elif minutes > 90 or source.get('state') in ('delayed', 'old_measurement'):
            state = 'delayed'
        else:
            state = 'recent'
        details[key] = {
            'state': state,
            'measured_at': source.get('measured_at'),
            'age_minutes_at_report': minutes,
            'source_state': source.get('state'),
        }
    attention = [key for key, item in details.items()
                 if item['state'] in ('delayed', 'invalid_future_measurement', 'unknown')]
    return {
        'live_measurements': details,
        'not_confirmed_recent': attention,
        'interpretation': 'caution' if attention else 'available_recent',
        'note': ('Data generation time never proves a new sensor reading. '
                 'Sleep HRV is measured during sleep, not continuously.'),
    }


def build(chain, file_times, now):
    cert = _original_build(chain, file_times, now)
    cert['gate_version'] = '2.4.8'
    cert['live_sensor_quality'] = live_sensor_summary(
        cert.get('measurement_provenance', {}), now)
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
    data['live_sensor_quality'] = cert.get('live_sensor_quality', {})
    data['physiological_report_status'] = cert.get('physiological_report_status', 'unknown')
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return data, hashlib.sha256(raw).hexdigest()


gate.build_certificate = build
gate.compact_cycle_snapshot = snapshot
gate.SLOTS = tuple((h, m, code, TARGETS.get(code, target)) for h, m, code, target in gate.SLOTS)

if __name__ == '__main__':
    raise SystemExit(gate.main())
