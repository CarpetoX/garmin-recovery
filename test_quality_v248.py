"""Quality and regression checks for Garmin Recovery V2.4.8."""
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from morning_sleep_gate import classify
from muscle_load import analyze, classify as classify_movement
import monitor_v231 as monitor
import report_sleep_integration as integration

TZ = ZoneInfo('Europe/Madrid')


class QualityTestsV248(unittest.TestCase):
    def test_sync_backup_event_and_cron(self):
        sync = (Path(__file__).parent / '.github/workflows/sync.yml').read_text(encoding='utf-8')
        self.assertIn('  repository_dispatch:\n    types: [garmin-sync]', sync)
        self.assertIn('  workflow_dispatch:', sync)
        self.assertIn('timezone: "Europe/Madrid"', sync)
        self.assertEqual(sync.count('    - cron:'), 3)

    def test_report_targets_aligned(self):
        self.assertEqual(
            [slot[3] for slot in integration.gate.SLOTS],
            ['09:05', '17:10', '23:10'],
        )
        self.assertEqual(integration.TARGETS,
                         {'0830': '09:05', '1645': '17:10', '2245': '23:10'})

    def test_sleep_after_night_shift_is_not_closed_early(self):
        now = datetime(2026, 10, 10, 6, 0, tzinfo=TZ)
        end = '2026-10-10T05:00:00+02:00'
        sleep = {'days': {'2026-10-10': {
            'window_confirmed': True,
            'sleep_start_local': '2026-10-10T03:00:00+02:00',
            'sleep_end_local': end,
        }}}
        rec = {'current': {'sleep_end_local': end},
               'input_freshness': {'sleep': True}}
        shifts = {'days': {'2026-10-09': 'TN'}}
        result = classify(now, sleep, rec, shifts)
        self.assertEqual(result['state'], 'post_night_shift_early_sleep_pending')
        self.assertFalse(result['is_definitive'])
        self.assertFalse(result['wake_confirmed'])
        self.assertTrue(result['episode_end_confirmed'])
        self.assertTrue(result['possible_sleep_in_progress'])
        self.assertEqual(classify(now, sleep, rec, {'days': {}})['state'], 'confirmed_ready')

    def test_strength_patterns(self):
        expected = {
            'press de pecho inclinado con mancuernas': 'horizontal_push',
            'press superinclinado iso lateral': 'horizontal_push',
            'press banca en máquina sentado': 'horizontal_push',
            'aperturas de pecho en máquina sentado': 'chest_isolation',
            'tríceps en polea': 'triceps_isolation',
            'sit-ups': 'core',
            'sentadilla frontal': 'squat',
        }
        for name, category in expected.items():
            with self.subTest(name=name):
                self.assertEqual(classify_movement(name), category)

    def test_external_load_by_equipment(self):
        activities = [{'date': '2026-10-10', 'activity_id': 'test', 'manual_blocks': [{
            'rpe': 6,
            'detail_json': {'exercises': [
                {'name': 'press de pecho inclinado', 'load_unit': 'kg_total_dos_mancuernas',
                 'sets': [{'reps': 8, 'load_kg': 60}]},
                {'name': 'press banca en máquina', 'load_unit': 'kg_indicado_maquina',
                 'sets': [{'reps': 8, 'load_kg': 70}]},
                {'name': 'fondos de pecho', 'load_unit': 'peso_corporal',
                 'sets': [{'count': 3, 'reps': 8}]},
            ]},
        }]}]
        out = analyze(activities, '2026-10-10')
        by_equipment = out['movement_pattern_load_by_equipment']['7d']
        self.assertEqual(
            by_equipment['horizontal_push:dumbbell_pair']['verified_volume_kg'], 480)
        self.assertEqual(
            by_equipment['horizontal_push:machine_stack']['verified_volume_kg'], 560)
        self.assertTrue(by_equipment['horizontal_push:bodyweight']['volume_complete'])
        self.assertEqual(out['strength_exercises'][2]['volume_status'],
                         'bodyweight_no_external_load')
        self.assertEqual(len(out['best_estimated_1rm_by_exercise']), 2)

    def test_sensor_age_uses_actual_measurement(self):
        now = datetime(2026, 10, 10, 17, 0, tzinfo=TZ)
        provenance = {
            'heart_rate_live': {
                'state': 'old_measurement',
                'measured_at': (now - timedelta(minutes=185)).isoformat(),
            },
            'body_battery_live': {
                'state': 'recent',
                'measured_at': (now - timedelta(minutes=10)).isoformat(),
            },
        }
        quality = integration.live_sensor_summary(provenance, now)
        self.assertIn('heart_rate_live', quality['not_confirmed_recent'])
        self.assertNotIn('body_battery_live', quality['not_confirmed_recent'])
        self.assertEqual(
            quality['live_measurements']['heart_rate_live']['age_minutes_at_report'], 185.0)

    def test_manual_dispatch_does_not_pass_as_schedule(self):
        now = datetime(2026, 10, 11, 11, 30, tzinfo=TZ)
        created_at = datetime(2026, 10, 11, 8, 35, tzinfo=TZ).isoformat()
        run = {'event': 'workflow_dispatch', 'created_at': created_at,
               'status': 'completed', 'conclusion': 'success'}
        result = monitor.audit_slots(now, [run], lookback_hours=12)
        self.assertEqual(result['matched'], 0)
        self.assertEqual(result['recovered_count'], 1)
        self.assertEqual(result['dispatch_origin_verified'], False)
        self.assertTrue(result['recovered_by_manual'])


if __name__ == '__main__':
    unittest.main()
