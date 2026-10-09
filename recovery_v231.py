#!/usr/bin/env python3
"""Recovery V2.3.1: measured-time provenance, private context and training guidance.

Compatibility layer: first executes installed V2.3, never increases readiness
or infers physiological fitness from subjective reports. No raw check-ins are
serialized to reports or committed to a public repository.
"""
from __future__ import annotations
import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from recovery_v23 import enhance_assessment as _enhance_v23

TZ = ZoneInfo('Europe/Madrid')


def _time(value, *, utc_if_naive=False):
    if value is None or value == '':
        return None
    try:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            d = datetime.fromtimestamp(value / 1000 if value > 1e11 else value, timezone.utc)
        else:
            d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc if utc_if_naive else TZ)
        return d.astimezone(TZ)
    except (ValueError, TypeError, OverflowError):
        return None


def _json(name):
    try:
        value = json.loads(Path(name).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _day(source, day):
    days = source.get('days') if isinstance(source, dict) else None
    row = days.get(day) if isinstance(days, dict) else None
    return row if isinstance(row, dict) else {}


def _number(v, low=0, high=1e9):
    try:
        if isinstance(v, bool) or v is None or str(v).strip() == '':
            return None
        value = float(v)
        return value if low <= value <= high else None
    except (ValueError, TypeError):
        return None


def _observed(ts, now, *, fresh_minutes=90, stale_minutes=180, source='measured'):
    if ts is None:
        return {'state': 'unverified_timestamp', 'measured_at': None, 'age_minutes': None, 'basis': source}
    age = round((now - ts).total_seconds() / 60, 1)
    if age < -15:
        state = 'future_timestamp'
    elif age <= fresh_minutes:
        state = 'recent'
    elif age <= stale_minutes:
        state = 'delayed'
    else:
        state = 'old_measurement'
    return {'state': state, 'measured_at': ts.isoformat(), 'age_minutes': age, 'basis': source}


def measurement_provenance(assessment, now, sources, daily):
    """Use sample/episode clocks; generated_at is explicitly NOT evidence of freshness."""
    current = assessment.get('current') or {}
    day = str(current.get('date') or '')
    start = _time(current.get('sleep_start_local'))
    end = _time(current.get('sleep_end_local'))
    sleep = _day(sources.get('sleep', {}), day)
    hrv = _day(sources.get('hrv', {}), day)
    heart = _day(sources.get('heart_timeline', {}), day)
    body = (daily.get('garmin_metrics') or {}).get('body_battery') or {}
    body_file = _day(sources.get('battery', {}), day)

    out = {}
    source_name = (current.get('sources') or {}).get('sleep_hours')
    verified_by_garmin = bool(source_name == 'garmin_sleep_history' and sleep.get('window_confirmed') is True)
    main_valid = bool(start and end and start < end)
    out['confirmed_sleep'] = _observed(end if main_valid else None, now,
                                      fresh_minutes=18*60, stale_minutes=24*60,
                                      source='confirmed_sleep_end')
    if end and not main_valid:
        out['confirmed_sleep']['state'] = 'invalid_sleep_window'
    elif main_valid and not verified_by_garmin:
        out['confirmed_sleep']['state'] = 'time_known_confirmation_unverified'
    out['confirmed_sleep']['garmin_episode_confirmed'] = verified_by_garmin

    last_hrv = _time(hrv.get('last_sample_local'))
    hrv_observed = _observed(last_hrv, now, fresh_minutes=18*60,
                             stale_minutes=24*60, source='actual_sleep_hrv_sample')
    if last_hrv and start and end and not (start-timedelta(minutes=20) <= last_hrv <= end+timedelta(minutes=20)):
        hrv_observed['state'] = 'sample_outside_sleep'
    out['sleep_hrv'] = hrv_observed

    out['heart_rate_live'] = _observed(_time(heart.get('last_sample_local')), now,
                                      source='actual_hr_sample')
    last_battery = _time(body.get('latest_sample_timestamp'))
    if last_battery is None:
        values = body_file.get('bodyBatteryValuesArray') or []
        if isinstance(values, list) and values:
            item = values[-1]
            if isinstance(item, (list, tuple)) and item:
                last_battery = _time(item[0])
    out['body_battery_live'] = _observed(last_battery, now,
                                         source='actual_body_battery_sample')
    # No per-reading timestamp for Garmin daily resting-HR summary.
    out['resting_hr_summary'] = {
        'state': 'daily_summary_not_instantaneous', 'measured_at': None,
        'age_minutes': None, 'basis': 'daily_resting_hr_summary',
    }
    invalid_core = out['confirmed_sleep']['state'] in ('old_measurement', 'future_timestamp', 'invalid_sleep_window') or out['sleep_hrv']['state'] in ('sample_outside_sleep', 'future_timestamp')
    live_delayed = [key for key in ('heart_rate_live', 'body_battery_live')
                    if out[key]['state'] in ('delayed', 'old_measurement', 'future_timestamp', 'unverified_timestamp')]
    return {'sources': out, 'invalid_core_episode': invalid_core,
            'live_data_limited': bool(live_delayed), 'limited_live_metrics': live_delayed,
            'note': 'Measurement timestamps are independent from file generation times. Nightly HRV is expected during sleep, not continuously.'}


def _private_checkin(date):
    """The env secret is not logged, persisted or exposed in public report JSON."""
    encoded = os.environ.get('RECOVERY_CHECKIN_B64', '')
    if not encoded:
        return None
    try:
        obj = json.loads(base64.b64decode(encoded, validate=True).decode('utf-8'))
        entry = obj.get(date) if isinstance(obj, dict) else None
        return entry if isinstance(entry, dict) else None
    except (ValueError, TypeError, UnicodeError):
        return None


def sleep_context(assessment, checkin):
    """User-reported naps stay separate; never inserted into confirmed Garmin sleep."""
    current = assessment.get('current') or {}
    main_start = _time(current.get('sleep_start_local'))
    main_end = _time(current.get('sleep_end_local'))
    nap_count = 0
    nap_intervals = []
    errors = 0
    naps = checkin.get('naps', []) if isinstance(checkin, dict) else []
    if isinstance(naps, list):
        for item in naps[:8]:
            if not isinstance(item, dict):
                errors += 1
                continue
            start = _time(item.get('start_local'))
            end = _time(item.get('end_local'))
            if (start is None or end is None or not start < end or end-start > timedelta(hours=6)):
                errors += 1
                continue
            # Exclude overlap with main sleep without distributing minutes to scores.
            if main_start and main_end and start < main_end and end > main_start:
                errors += 1
                continue
            if any(start < previous_end and end > previous_start for previous_start,previous_end in nap_intervals):
                errors += 1
                continue
            nap_intervals.append((start, end))
            nap_count += 1
    return {
        'main_sleep_is_score_source': True,
        'reported_naps_private': bool(nap_count),
        'reported_naps_excluded_from_core_score': True,
        'uncertain_events_remain_unconfirmed': True,
        # No nap times, exact durations, or symptoms leave the private input.
        'validation': 'accepted' if nap_count else 'not_supplied_or_not_verified',
        'note': 'User-confirmed extra naps may inform discussion but are not merged with Garmin HRV, stages or sleep-score baselines.',
    }


def _subjective_flags(checkin):
    if not isinstance(checkin, dict):
        return False, False
    sleepiness = _number(checkin.get('sleepiness'), 0, 3)
    fatigue = _number(checkin.get('physical_fatigue'), 0, 3)
    pain = _number(checkin.get('headache'), 0, 10)
    usual = checkin.get('headache_usual')
    meaningful = any(v is not None for v in (sleepiness, fatigue, pain))
    limit = bool((sleepiness is not None and sleepiness >= 2) or
                 (fatigue is not None and fatigue >= 3) or
                 (pain is not None and pain >= 5) or
                 (usual is False and pain is not None and pain >= 4))
    return meaningful, limit


def session_guidance(assessment, recent_rpe):
    """Conservative guidance by session class; no physiological or injury diagnosis."""
    v = assessment.get('v23') or {}
    reason = (assessment.get('state') == 'pending' or
              assessment.get('status') in ('red','unavailable') or
              v.get('intensity_guardrail') == 'avoid_maximum')
    confidence = assessment.get('confidence')
    no_green = confidence != 'high' or assessment.get('state') != 'assessed'
    if reason:
        choices = {
            'heavy_strength': 'postpone_heavy_sets',
            'olympic_lifting': 'avoid_heavy_or_complex_skill',
            'high_intensity_metcon': 'postpone_intense_metcon',
            'easy_aerobic': 'optional_easy_only_if_alert_and_symptoms_allow',
            'mobility': 'optional_light_mobility',
        }
        level = 'restrict'
    elif no_green or assessment.get('status') == 'yellow':
        choices = {
            'heavy_strength': 'submaximal_technique_no_maximum',
            'olympic_lifting': 'controlled_technique_only',
            'high_intensity_metcon': 'scale_and_verify_warmup',
            'easy_aerobic': 'light_to_moderate_by_perceived_effort',
            'mobility': 'usual_light_mobility',
        }
        level = 'conservative'
    else:
        choices = {
            'heavy_strength': 'consider_planned_work_after_symptom_and_warmup_check',
            'olympic_lifting': 'consider_planned_technique_after_warmup',
            'high_intensity_metcon': 'consider_planned_session_after_warmup',
            'easy_aerobic': 'usual_program_if_well',
            'mobility': 'usual_program_if_well',
        }
        level = 'individualize'
    return {
        'guidance_level': level, 'session_types': choices,
        'recent_sessions_with_declared_rpe': recent_rpe.get('count', 0),
        'recent_high_rpe_sessions': recent_rpe.get('high_count', 0),
        'note': 'Guidance only; no direct measure of neuromuscular readiness, and sleepiness can affect coordination independently of muscle fatigue.',
    }


def recent_rpe_summary(date, feedback):
    now = _time(date + 'T12:00:00+02:00')
    entries = (feedback or {}).get('activities') or {}
    found = []
    if not isinstance(entries, dict):
        return {'count':0,'high_count':0}
    for row in entries.values():
        if not isinstance(row, dict):
            continue
        day = row.get('date')
        measured = _time(str(day)+'T12:00:00+02:00') if isinstance(day,str) else None
        rpe = _number(row.get('rpe'), 0, 10)
        if measured and now and rpe is not None and timedelta(0) <= now-measured <= timedelta(days=2):
            found.append(rpe)
    return {'count':len(found),'high_count':sum(v>=8 for v in found)}


def enhance_assessment(assessment, extended, daily, now=None, *, sources=None, checkin_encoded=None):
    now = now or datetime.now(TZ)
    if now.tzinfo is None:
        now = now.replace(tzinfo=TZ)
    now = now.astimezone(TZ)
    # In tests a checkin_encoded value can be passed explicitly, never serialized.
    source_map = sources if isinstance(sources, dict) else {
        'sleep': _json('garmin_sleep_history.json'),
        'hrv': _json('garmin_hrv_timeline.json'),
        'heart_timeline': _json('garmin_hr_timeline.json'),
        'battery': _json('garmin_body_battery.json'),
        'feedback': _json('training_feedback.json'),
    }
    if checkin_encoded is not None:
        previous = os.environ.get('RECOVERY_CHECKIN_B64')
        os.environ['RECOVERY_CHECKIN_B64'] = checkin_encoded
        try:
            result = _enhance_v23(assessment, extended, daily, now, checkin_encoded=checkin_encoded)
            checkin = _private_checkin(str((result.get('current') or {}).get('date') or ''))
        finally:
            if previous is None: os.environ.pop('RECOVERY_CHECKIN_B64', None)
            else: os.environ['RECOVERY_CHECKIN_B64'] = previous
    else:
        result = _enhance_v23(assessment, extended, daily, now)
        checkin = _private_checkin(str((result.get('current') or {}).get('date') or ''))

    day = str((result.get('current') or {}).get('date') or '')
    provenance = measurement_provenance(result, now, source_map, daily if isinstance(daily, dict) else {})
    subjective_present, subjective_limit = _subjective_flags(checkin)
    sleep = sleep_context(result, checkin)
    if subjective_present:
        result['v23']['subjective_checkin'] = 'applied_privately'
        result['v23']['subjective_values_exported'] = False
    # Conservatively block *maximum* effort on serious private symptoms,
    # while maintaining the underlying score and transparent source provenance.
    if subjective_limit:
        result['v23']['intensity_guardrail'] = 'avoid_maximum'
        result['v23']['reason_codes'] = list(result['v23'].get('reason_codes') or []) + ['private_guardrail']
    if provenance['invalid_core_episode']:
        result['state'] = 'pending'
        result['status'] = 'unavailable'
        result['score'] = None
        result['confidence'] = 'low'
        result['reason'] = 'stale_or_inconsistent_sleep_measurement'
        result['recommendation'] = 'No evaluar recuperación hasta confirmar el episodio de sueño y sus marcas temporales.'
        result['v23']['intensity_guardrail'] = 'avoid_maximum'
    elif subjective_limit:
        if result.get('status') == 'green':
            result['v23']['raw_score_before_guardrail'] = result.get('score')
            if _number(result.get('score'),0,100) is not None:
                result['score'] = min(int(result['score']), 74)
            result['status'] = 'yellow'
        result['recommendation'] = 'Adaptar entrenamiento a síntomas, atención y descanso; no hacer cargas máximas.'
    if provenance['live_data_limited']:
        result['v23']['reason_codes'] = list(result['v23'].get('reason_codes') or []) + ['live_measurement_uncertain']
    result['methodology_version'] = 'recovery-reliability-v2.3.1'
    result['v23']['version'] = '2.3.1'
    result['v23']['measurement_provenance'] = provenance
    result['v23']['sleep_fragmentation'] = sleep
    result['v23']['training_guidance'] = session_guidance(result, recent_rpe_summary(day, source_map.get('feedback')))
    result['v23']['note'] = ('V2.3.1 reliability overlay; the V2.2 baseline score is retained '
                            'unless invalid measurements or a restrictive private guardrail block clearance.')
    return result


def install():
    """Idempotent patch: Python files only. Never edits GitHub workflow YAML."""
    base = Path('recovery_reliability.py')
    monitor_file = Path('monitor_monthly.py')
    if not base.is_file() or not monitor_file.is_file() or not Path('recovery_v23.py').is_file():
        raise SystemExit('Run from repo root containing V2.3; no changes performed.')
    old = base.read_text(encoding='utf-8')
    new = old
    origin = '    from recovery_v23 import enhance_assessment'
    new_import = '    from recovery_v231 import enhance_assessment'
    if new_import not in new:
        if new.count(origin) != 1 or new.count('assessment = enhance_assessment(assessment, extended, daily, now)') != 1:
            raise SystemExit('V2.3 integration anchor not found exactly once; no changes performed.')
        new = new.replace(origin, new_import, 1)
    monitor_old = monitor_file.read_text(encoding='utf-8')
    monitor_new = monitor_old
    needle = "if __name__ == '__main__':"
    if '__monitor_before_v231' not in monitor_new:
        if monitor_new.count(needle) != 1:
            raise SystemExit('Monitor integration anchor not found exactly once; no changes performed.')
        injection = (
            '# V2.3.1: verify real schedule slots, independent of manual runs.\n'
            'from monitor_v231 import enhance_monitor\n'
            '__monitor_before_v231 = monitor\n'
            'def monitor(now, repo, token, fetcher=fetch_runs):\n'
            '    base = __monitor_before_v231(now, repo, token, fetcher=fetcher)\n'
            '    return enhance_monitor(base, now, repo, token, fetcher=fetcher)\n\n'
        )
        monitor_new = monitor_new.replace(needle, injection + needle, 1)
    # Both anchors verified before writing either file.
    if new != old: base.write_text(new, encoding='utf-8')
    if monitor_new != monitor_old: monitor_file.write_text(monitor_new, encoding='utf-8')
    print('Installed V2.3.1 Python-only patch (idempotent).')


def self_test():
    import unittest
    class Tests(unittest.TestCase):
        def fixture(self):
            a={'current':{'date':'2026-10-09','sleep_hours':4.8,'sleep_score':56,
                          'sleep_start_local':'2026-10-09T08:00:00+02:00','sleep_end_local':'2026-10-09T12:50:00+02:00',
                          'sources':{'sleep_hours':'garmin_sleep_history'}},
               'status':'red','score':48,'state':'provisional','confidence':'medium',
               'work_shift_context':'post-TN','sleep_context':'day_sleep',
               'baseline_28d':{'hrv_ms':{'scope':'overall'}}}
            return a
        def sources(self,last='2026-10-09T12:50:00+02:00'):
            return {'sleep':{'days':{'2026-10-09':{'window_confirmed':True}}},
                    'hrv':{'days':{'2026-10-09':{'last_sample_local':'2026-10-09T12:21:11+02:00'}}},
                    'heart_timeline':{'days':{'2026-10-09':{'last_sample_local':last}}},
                    'battery':{},'feedback':{'activities':{'w1':{'date':'2026-10-08','rpe':8}}}}
        def run_case(self,assessment=None,sources=None,private=None,now='2026-10-09T13:20:00+02:00'):
            return enhance_assessment(assessment or self.fixture(), {'days':{}}, {}, _time(now),
                sources=sources if sources is not None else self.sources(), checkin_encoded=private)
        def test_real_hr_timestamp_and_not_generated_at(self):
            r=self.run_case(sources=self.sources('2026-10-09T08:10:00+02:00'))
            self.assertEqual(r['v23']['measurement_provenance']['sources']['heart_rate_live']['state'],'old_measurement')
            self.assertEqual(r['score'],48)
            self.assertTrue(r['v23']['measurement_provenance']['live_data_limited'])
        def test_actual_fresh_measurement(self):
            r=self.run_case()
            self.assertEqual(r['v23']['measurement_provenance']['sources']['heart_rate_live']['state'],'recent')
        def test_expired_sleep_requires_pending(self):
            r=self.run_case(now='2026-10-10T20:00:00+02:00')
            self.assertEqual((r['state'],r['score'],r['status']),('pending',None,'unavailable'))
        def test_hrv_outside_sleep_fails_closed(self):
            src=self.sources(); src['hrv']['days']['2026-10-09']['last_sample_local']='2026-10-09T03:00:00+02:00'
            self.assertEqual(self.run_case(sources=src)['state'],'pending')
        def test_unconfirmed_naps_not_added(self):
            raw={'2026-10-09':{'naps':[{'start_local':'2026-10-09T03:00:00+02:00',
                                      'end_local':'2026-10-09T04:00:00+02:00'}]}}
            b64=base64.b64encode(json.dumps(raw).encode()).decode()
            r=self.run_case(private=b64)
            self.assertTrue(r['v23']['sleep_fragmentation']['reported_naps_private'])
            self.assertEqual(r['current']['sleep_hours'],4.8)
            self.assertNotIn('03:00',json.dumps(r))
        def test_private_sleepiness_partial_no_raw(self):
            b64=base64.b64encode(json.dumps({'2026-10-09':{'sleepiness':3}}).encode()).decode()
            r=self.run_case(private=b64)
            self.assertEqual(r['v23']['subjective_checkin'],'applied_privately')
            self.assertEqual(r['v23']['intensity_guardrail'],'avoid_maximum')
            self.assertNotIn('\"sleepiness\": 3',json.dumps(r))
        def test_training_specific(self):
            r=self.run_case()
            self.assertEqual(r['v23']['training_guidance']['session_types']['heavy_strength'],'postpone_heavy_sets')
            self.assertEqual(r['v23']['training_guidance']['recent_high_rpe_sessions'],1)
        def test_installer_has_no_workflow_writer(self):
            import inspect
            self.assertNotIn('write_text(workflow',inspect.getsource(install))
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Tests)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful(): raise SystemExit(1)


if __name__=='__main__':
    if '--self-test' in sys.argv: self_test()
    elif '--install' in sys.argv: install()
    else: print('Usage: python recovery_v231.py --self-test | --install')
