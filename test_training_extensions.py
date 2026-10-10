"""Permanent regression tests for real performed CrossFit work (v2.4.11)."""
import unittest
from training_extensions import analyze


def activity(detail, date='2026-10-09', activity_id='a'):
    return {'date': date, 'activity_id': activity_id,
            'manual_blocks': [{'rpe': 8, 'detail_json': detail}]}


class TestPerformedMetconWork(unittest.TestCase):
    def test_amrap_completed_totals_only(self):
        detail = {
            'type': 'metcon', 'format': 'AMRAP', 'duration_minutes': 15,
            'prescribed_round': [
                {'name': 'carrera', 'distance_m': 400},
                {'name': 'thruster alterno con mancuerna', 'reps': 21},
                {'name': 'toes-to-bar', 'reps': 12},
                {'name': 'devil press alterno con mancuerna', 'reps': 9},
            ],
            'performed': {'rounds_complete': 2, 'totals': {
                'run_m': 1200, 'thruster_reps': 63,
                'toes_to_bar_reps': 33, 'devil_press_reps': 18,
            }}, 'recorded_garmin_minutes': 17.55,
        }
        entries = analyze([activity(detail)], {}, '2026-10-10')['metcon_exposure']['entries']
        by_name = {row['movement']: row for row in entries}
        self.assertEqual(by_name['carrera']['verified_distance_m'], 1200)
        self.assertEqual(by_name['thruster alterno con mancuerna']['verified_reps'], 63)
        self.assertEqual(by_name['toes-to-bar']['verified_reps'], 33)
        self.assertEqual(by_name['devil press alterno con mancuerna']['verified_reps'], 18)
        self.assertTrue(all(x['evidence'] == 'performed.totals' for x in entries))
        self.assertEqual(len(entries), 4)

    def test_21_15_9_completed(self):
        detail = {
            'type': 'metcon', 'format': '21-15-9', 'time_cap_minutes': 8,
            'exercises': [{'name': 'sentadilla frontal', 'load_kg': 60},
                          {'name': 'handstand push-up', 'load_kg': None}],
            'performed': {'completed': True, 'total_reps_each_exercise': 45,
                          'total_reps': 90},
        }
        out = analyze([activity(detail)], {}, '2026-10-10')['metcon_exposure']
        self.assertEqual(len(out['entries']), 2)
        self.assertEqual({e['movement']: e['verified_reps'] for e in out['entries']},
                         {'sentadilla frontal': 45, 'handstand push-up': 45})
        self.assertEqual(out['entries'][0]['declared_load_kg'], 60)
        self.assertEqual(out['movement_work']['7d']['sentadilla frontal']['reps'], 45)

    def test_unfinished_prescription_is_not_performed(self):
        planned = {'type': 'metcon', 'prescribed_round': [
            {'name': 'carrera', 'distance_m': 400}, {'name': 'thruster', 'reps': 21}],
            'performed': {'rounds_complete': 2}}
        unfinished = {'type': 'metcon', 'exercises': [{'name': 'sentadilla frontal'}],
                      'performed': {'completed': False, 'total_reps_each_exercise': 45}}
        entries = analyze([activity(planned), activity(unfinished)], {}, '2026-10-10')['metcon_exposure']['entries']
        self.assertEqual(entries, [])

    def test_no_double_count_when_multiple_schemas_coexist(self):
        detail = {'completed_movements': [{'name': 'carrera', 'distance_m': 400}],
                  'performed': {'totals': {'run_m': 1200}}}
        entries = analyze([activity(detail)], {}, '2026-10-10')['metcon_exposure']['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['verified_distance_m'], 400)

    def test_invalid_values_not_counted(self):
        detail = {'completed_movements': [
            {'name': 'Thruster', 'reps': -2},
            {'name': 'Burpee', 'reps': 2.5},
            {'name': 'Correr', 'distance_m': 'nan'},
            {'name': 'Remo', 'distance_m': 1000},
        ]}
        entries = analyze([activity(detail)], {}, '2026-10-10')['metcon_exposure']['entries']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['movement'], 'Remo')

    def test_preserve_existing_direct_schema(self):
        detail = {'completed_movements': [
            {'name': 'burpee', 'reps': 21, 'load_kg': None},
            {'name': 'carrera', 'distance_m': 500}], 'benchmark_id': ''}
        result = analyze([activity(detail)], {}, '2026-10-10')
        self.assertEqual(result['metcon_exposure']['movement_work']['7d']['burpee']['reps'], 21)
        self.assertEqual(result['metcon_exposure']['movement_work']['7d']['carrera']['distance_m'], 500)

    def test_benchmarks_still_require_exact_variant(self):
        records = [activity({'benchmark_id': 'Fran', 'benchmark_variant': 'RX',
                             'benchmark_result': {'metric': 'time_seconds', 'value': 320}},
                            '2026-10-06', 'a1'),
                   activity({'benchmark_id': 'Fran', 'benchmark_variant': 'Scaled',
                             'benchmark_result': {'metric': 'time_seconds', 'value': 280}},
                            '2026-10-09', 'a2')]
        self.assertEqual(analyze(records, {}, '2026-10-10')['performance_trends']['comparisons'], [])


if __name__ == '__main__':
    unittest.main()
