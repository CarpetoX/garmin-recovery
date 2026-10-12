"""CrossFit V3.6 isolated regression tests, requiring no Garmin or network access."""
import copy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from crossfit_report_v36 import ReportError, make_report, validate, markdown, svg_chart, main

DAY = date(2026, 10, 12)
CREATED = '2026-10-12T09:00:21+02:00'
TREND_TIME = '2026-10-12T07:00:23+00:00'
NOW = datetime(2026, 10, 12, 7, 1, tzinfo=timezone.utc)


def fixture():
    daily = []
    for lag in range(27, -1, -1):
        d = DAY - timedelta(days=lag)
        daily.append({'date': str(d), 'recorded_sessions': 1 if lag in (2, 1) else 0,
                      'mean_rpe': 6 if lag in (2, 1) else None,
                      'srpe_proxy': 180 if lag in (2, 1) else None,
                      'trimp': 25 if lag in (2, 1) else None,
                      'hrv': 53 if lag == 0 else None,
                      'resting_hr': 55 if lag == 0 else None,
                      'sleep_hours': 7.2 if lag == 0 else None,
                      'sleep_score': 79 if lag == 0 else None})
    crossfit = {'generated_at': CREATED, 'activities': [{'date': '2026-10-11', 'activity_id': '1'}]}
    v35 = {'version': '3.5', 'as_of_date': str(DAY),
           'charts': {'modality_rpe_7d': [{'category': 'Fuerza', 'sessions': 2}]},
           'benchmarks': {'status': 'no_verified_repeated_benchmarks', 'reported_comparison_count': 0},
           'recommendations': [{'priority': 2, 'category': 'benchmark', 'message': 'Registrar benchmark'}]}
    base = {'version': '3.2', 'as_of_date': str(DAY),
            'provenance': {'crossfit_generated_at': CREATED},
            'interpretation_quality': {'level': 'provisional'},
            'charts': {'daily_28d': daily},
            'window_comparison': {'current_vs_previous_7d': {'comparison_status': 'insufficient_sessions_in_either_week',
                                                             'srpe_proxy_delta_pct': 99}},
            'strength': {'exact_exercise_groups': [
                {'exercise': 'curl femoral unilateral', 'equipment': 'machine_stack',
                 'load_unit': 'kg_indicado_maquina', 'distinct_training_days': 1,
                 'last_day': '2026-10-11', 'observed_peak_change_kg': None},
                {'exercise': 'sentadilla', 'equipment': 'barbell', 'load_unit': 'kg_total_barra',
                 'distinct_training_days': 2, 'last_day': '2026-10-11',
                 'observed_peak_change_kg': 5}]},
            'recommendations': [{'priority': 1, 'kind': 'insufficient_history', 'text': 'Registrar otra semana'}],
            'performance_enhancements_v35': v35}
    trends = {'schema_version': 1, 'version': '3.1', 'as_of_date': str(DAY),
              'generated_at': TREND_TIME, 'source_generated_at': CREATED,
              'confidence': 'provisional',
              'windows': {'7d': {'recorded_sessions': 2, 'recorded_sessions_with_rpe': 2,
                                 'mean_session_rpe': 6, 'recorded_duration_minutes': 60,
                                 'srpe_recorded_duration_sum': 360},
                          '28d': {'recorded_sessions': 2}},
              'performance_report_v32': base}
    recovery = {'state': 'assessed', 'status': 'yellow', 'score': 88, 'confidence': 'medium',
                'current': {'date': str(DAY), 'hrv_ms': 66, 'resting_hr': 53,
                            'sleep_hours': 7.23, 'sleep_score': 79}}
    quality = {'generated_at': '2026-10-12T09:00:00+02:00', 'score': 74, 'issues': ['baseline_immature']}
    ready = {'status': 'ready', 'verified_at': '2026-10-12T09:00:30+02:00',
             'source_generated_at': {'crossfit_insights.json': CREATED},
             'measurement_provenance': {
                 'heart_rate_live': {'state': 'recent', 'measured_at': '2026-10-12T08:14:00+02:00'},
                 'body_battery_live': {'state': 'delayed', 'measured_at': '2026-10-12T07:18:00+02:00'}}}
    return crossfit, trends, recovery, quality, ready


def build(parts=None):
    return make_report(*(parts if parts is not None else fixture()), now=NOW)


class CrossFitV36Tests(unittest.TestCase):
    def test_report_valid(self):
        self.assertTrue(validate(build()))

    def test_is_pure(self):
        parts = fixture()
        original = copy.deepcopy(parts)
        build(parts)
        self.assertEqual(parts, original)

    def test_report_source_matches(self):
        r = build()
        self.assertTrue(r['source_provenance']['same_source_verified'])
        self.assertEqual(r['source_provenance']['certificate_state'], 'matched_data_ready_source')

    def test_rpe_coverage_uses_existing(self):
        r = build()
        self.assertEqual(r['training']['last_7d']['rpe_coverage'], {'with_rpe': 2, 'sessions': 2})
        self.assertEqual(r['training']['last_7d']['srpe_recorded_minutes_proxy'], 360)

    def test_rpe_not_rir(self):
        self.assertTrue(build()['training']['session_rpe_is_not_set_rir'])

    def test_no_missing_day_misclassified_as_rest(self):
        r = build()
        self.assertTrue(r['charts']['daily_28d'][0]['no_record_does_not_prove_rest'])
        self.assertEqual(r['charts']['daily_28d'][0]['recorded_sessions'], 0)

    def test_no_comparison_without_eligible_week(self):
        r = build()
        self.assertFalse(r['training']['week_comparison']['eligible'])
        self.assertIsNone(r['training']['week_comparison']['srpe_delta_pct'])

    def test_comparison_does_not_invent_value(self):
        parts = fixture()
        parts[1]['performance_report_v32']['window_comparison']['current_vs_previous_7d']['comparison_status'] = 'descriptive_only'
        self.assertEqual(build(parts)['training']['week_comparison']['srpe_delta_pct'], 99)

    def test_strength_keeps_units(self):
        s = build()['training']['strength_exact_equipment']
        self.assertEqual(s[0]['load_unit'], 'kg_indicado_maquina')
        self.assertEqual(s[1]['load_unit'], 'kg_total_barra')

    def test_strength_never_validates_1rm(self):
        self.assertTrue(all(r['verified_1rm'] is False for r in build()['training']['strength_exact_equipment']))

    def test_peak_delta_descriptive_only(self):
        r = build()['training']['strength_exact_equipment'][-1]
        self.assertEqual(r['observed_peak_change_kg'], 5)
        self.assertEqual(r['progression_state'], 'descriptive_only_not_rep_rpe_matched')

    def test_recovery_preserves_yellow(self):
        r = build()['recovery']
        self.assertEqual(r['score_heuristic'], 88)
        self.assertEqual(r['status_original'], 'yellow')

    def test_unmatched_recovery_hidden(self):
        parts = fixture()
        parts[2]['current']['date'] = '2026-10-11'
        self.assertIsNone(build(parts)['recovery']['score_heuristic'])

    def test_quality_not_software_score(self):
        r = build()['data_quality']
        self.assertEqual(r['data_score_not_software_quality'], 74)

    def test_stale_quality_not_displayed(self):
        parts = fixture()
        parts[3]['generated_at'] = '2026-10-11T09:00:00+02:00'
        self.assertIsNone(build(parts)['data_quality']['data_score_not_software_quality'])

    def test_cert_not_inferred_from_stale(self):
        parts = fixture()
        parts[4]['source_generated_at']['crossfit_insights.json'] = '2026-10-11T09:00:00+02:00'
        r = build(parts)
        self.assertEqual(r['source_provenance']['certificate_state'], 'not_linked_to_current_certificate')
        self.assertEqual(r['live_measures']['body_battery_live']['state'], 'unverified')

    def test_real_sample_timestamps(self):
        self.assertEqual(build()['live_measures']['body_battery_live']['measured_at'], '2026-10-12T07:18:00+02:00')

    def test_never_claims_message_delivered(self):
        self.assertEqual(build()['source_provenance']['chatgpt_delivery'], 'unverified_no_receipt')
        self.assertIn('Entrega en ChatGPT: **no verificada**', markdown(build()))

    def test_invalid_source_mismatch_fails_closed(self):
        parts = fixture()
        parts[1]['source_generated_at'] = '2026-10-11T09:00:00+02:00'
        with self.assertRaises(ReportError):
            build(parts)

    def test_invalid_version_fails_closed(self):
        parts = fixture()
        parts[1]['performance_report_v32']['performance_enhancements_v35']['version'] = '3.4'
        with self.assertRaises(ReportError):
            build(parts)

    def test_missing_daily_graph_fails_closed(self):
        parts = fixture()
        parts[1]['performance_report_v32']['charts']['daily_28d'].pop()
        with self.assertRaises(ReportError):
            build(parts)

    def test_duplicate_date_fails_closed(self):
        parts = fixture()
        parts[1]['performance_report_v32']['charts']['daily_28d'][2]['date'] = parts[1]['performance_report_v32']['charts']['daily_28d'][1]['date']
        with self.assertRaises(ReportError):
            build(parts)

    def test_invalid_session_count_fails_closed(self):
        parts = fixture()
        parts[1]['performance_report_v32']['charts']['daily_28d'][-1]['recorded_sessions'] = -1
        with self.assertRaises(ReportError):
            build(parts)

    def test_rpe_outside_range_not_displayed(self):
        parts = fixture()
        parts[1]['performance_report_v32']['charts']['daily_28d'][-1]['mean_rpe'] = 15
        self.assertIsNone(build(parts)['charts']['daily_28d'][-1]['mean_rpe'])

    def test_finite_numbers_only(self):
        parts = fixture()
        parts[1]['performance_report_v32']['charts']['daily_28d'][-1]['hrv'] = float('nan')
        self.assertIsNone(build(parts)['charts']['daily_28d'][-1]['hrv_ms'])
        json.dumps(build(parts), allow_nan=False)

    def test_markdown_has_no_impossible_1rm_claim(self):
        m = markdown(build())
        self.assertIn('progresión', m.lower()) if 'progresión' in m.lower() else self.assertIn('descriptive_only', m)
        self.assertIn('no demuestra', m)

    def test_recommendations_existing_only(self):
        r = build()
        self.assertEqual([x['kind'] for x in r['recommendations']], ['insufficient_history', 'benchmark'])
        self.assertTrue(all(x['source'] == 'existing_v32_v35_rule' for x in r['recommendations']))

    def test_validate_rejects_false_delivery(self):
        r = build()
        r['source_provenance']['chatgpt_delivery'] = 'delivered'
        with self.assertRaises(ReportError):
            validate(r)

    def test_svg_has_separate_axes_and_missing_gaps(self):
        import xml.etree.ElementTree as ET
        raw = svg_chart(build())
        root = ET.fromstring(raw)
        self.assertTrue(root.tag.endswith('svg'))
        self.assertIn('Dos escalas independientes', raw)
        self.assertIn('28 días', raw)

    def test_svg_missing_values_not_connected(self):
        raw = svg_chart(build())
        self.assertNotIn('nan', raw.lower())
        # A single recorded proxy point is not drawn as a falsely continuous line.
        self.assertIn('2 muestras observadas', raw)

    def test_write_cli_and_validate_cli(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            crossfit, trends, recovery, quality, ready = fixture()
            for name, obj in [('crossfit.json', crossfit), ('trends.json', trends),
                              ('recovery.json', recovery), ('quality.json', quality), ('ready.json', ready)]:
                (td/name).write_text(json.dumps(obj), encoding='utf-8')
            args = ['--crossfit', str(td/'crossfit.json'), '--trends', str(td/'trends.json'),
                    '--recovery', str(td/'recovery.json'), '--quality', str(td/'quality.json'),
                    '--ready', str(td/'ready.json'), '--out', str(td/'r.json'),
                    '--markdown', str(td/'r.md'), '--chart', str(td/'r.svg')]
            self.assertEqual(main(args), 0)
            self.assertTrue((td/'r.md').exists())
            self.assertTrue((td/'r.svg').exists())
            self.assertTrue(json.loads((td/'r.json').read_text())['training']['last_7d']['registered_sessions'] == 2)
            self.assertEqual(main(['--validate', str(td/'r.json')]), 0)

    def test_no_write_when_source_invalid(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td/'crossfit.json').write_text('{}')
            (td/'trends.json').write_text('{}')
            with self.assertRaises(ReportError):
                main(['--crossfit', str(td/'crossfit.json'), '--trends', str(td/'trends.json'),
                      '--out', str(td/'out.json'), '--markdown', str(td/'out.md'), '--chart', str(td/'out.svg')])
            self.assertFalse((td/'out.json').exists())
            self.assertFalse((td/'out.md').exists())
            self.assertFalse((td/'out.svg').exists())


if __name__ == '__main__':
    unittest.main()
