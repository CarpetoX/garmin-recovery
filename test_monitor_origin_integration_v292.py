import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from garmin_recovery.origin_integration import integrate, main

NOW = datetime(2026, 10, 11, 15, 2, tzinfo=timezone.utc)


def inputs(signed=False):
    health = {
        'checked_at': NOW.isoformat(), 'status': 'attention',
        'pipeline_progress': {'state': 'ready', 'sync_run_id': 10},
        'schedule_v231': {'recovered_count': 1,
                          'recovered_by_manual': ['2026-10-11T16:45:00+02:00'],
                          'recovered_by_unattributed': ['2026-10-11T16:45:00+02:00']},
        'operational_quality_v28': {'cron_confirmed_pct': 0, 'blockers': ['github_schedule_not_verified']},
        'alerts': [{'severity': 'warning', 'code': 'cron_missed_dispatch_recovered'}]
    }
    root = {'run_id': 10, 'event': 'workflow_dispatch'}
    if signed:
        root['origin_v291'] = {
            'github_event': 'workflow_dispatch', 'origin_source': 'apps_script_backup',
            'source_verified': True, 'auth_method': 'hmac_sha256_shared_secret_v291',
            'cycle_id': '2026-10-11-1645'}
    lineage = {'stage': 'crossfit', 'complete_chain_verified': True,
               'exact_link_count': 3, 'run_id': 40, 'root': root}
    ready = {'status': 'ready', 'cycle_id': '2026-10-11-1645',
             'slot_at': '2026-10-11T16:45:00+02:00',
             'verified_at': '2026-10-11T17:00:18+02:00',
             'chain': {'sync': {'id': 10, 'started_at': '2026-10-11T16:59:10+02:00'},
                       'crossfit': {'id': 40}}}
    return health, lineage, ready


class MonitorOriginIntegrationTests(unittest.TestCase):
    def test_authenticated_source_is_reported(self):
        health, lineage, ready = inputs(True)
        output, detail = integrate(health, lineage, ready, NOW)
        self.assertEqual(detail['status'], 'verified_current_cycle')
        self.assertEqual(detail['origin']['source'], 'apps_script_backup')
        self.assertTrue(detail['origin']['verified'])
        self.assertEqual(detail['punctuality']['sync_delay_minutes'], 14.17)
        self.assertEqual(detail['punctuality']['data_ready_delay_minutes'], 15.3)
        self.assertTrue(output['operational_quality_v28']['origin_monitor_v292']['source_verified'])

    def test_unsigned_is_never_called_manual(self):
        health, lineage, ready = inputs(False)
        output, detail = integrate(health, lineage, ready, NOW)
        self.assertEqual(detail['origin']['source'], 'dispatch_unattributed')
        self.assertFalse(detail['origin']['verified'])
        self.assertEqual(output['schedule_v231']['recovered_by_confirmed_manual'], [])
        self.assertIn('unattributed', output['schedule_v231']['legacy_recovered_by_manual_meaning'])

    def test_old_schedule_alert_remains_true(self):
        health, lineage, ready = inputs(True)
        output, _ = integrate(health, lineage, ready, NOW)
        self.assertEqual(output['status'], 'attention')
        self.assertEqual(output['operational_quality_v28']['cron_confirmed_pct'], 0)
        self.assertEqual(output['operational_quality_v28']['blockers'], ['github_schedule_not_verified'])
        self.assertEqual(output['alerts'][0]['severity'], 'warning')

    def test_copy_not_mutate_original(self):
        health, lineage, ready = inputs(True)
        original = copy.deepcopy((health, lineage, ready))
        integrate(health, lineage, ready, NOW)
        self.assertEqual((health, lineage, ready), original)

    def test_new_pipeline_cannot_inherit_old_certification(self):
        health, lineage, ready = inputs(True)
        health['pipeline_progress']['sync_run_id'] = 100
        _, detail = integrate(health, lineage, ready, NOW)
        self.assertEqual(detail['status'], 'previous_cycle_only')
        self.assertFalse(detail['latest_pipeline_matches_certificate'])

    def test_mismatched_crossfit_is_not_verified(self):
        health, lineage, ready = inputs(True)
        ready['chain']['crossfit']['id'] = 41
        _, detail = integrate(health, lineage, ready, NOW)
        self.assertEqual(detail['status'], 'lineage_or_certificate_unmatched')
        self.assertFalse(detail['origin']['verified'])

    def test_no_lineage_causes_advisory_not_loss(self):
        health, _, ready = inputs()
        output, detail = integrate(health, None, ready, NOW)
        self.assertEqual(detail['status'], 'missing_lineage_or_certificate')
        self.assertEqual(detail['origin']['source'], 'unknown')
        self.assertEqual(output['operational_quality_v28']['cron_confirmed_pct'], 0)

    def test_incomplete_metrics_still_works(self):
        health, lineage, ready = inputs()
        del health['operational_quality_v28']
        del health['schedule_v231']
        a, b = integrate(health, lineage, ready, NOW)
        self.assertIn('origin_monitor_v292', a)
        self.assertFalse(b['origin']['verified'])

    def test_delivery_is_not_certified(self):
        health, lineage, ready = inputs(True)
        _, detail = integrate(health, lineage, ready, NOW)
        self.assertEqual(detail['chatgpt_delivery'], 'unconfirmed_without_receipt')
        self.assertIn('unavailable', detail['historical_7_28d_slo'])

    def test_cli_writes_original_health_fields_and_separate_report(self):
        health, lineage, ready = inputs(True)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            for name, obj in [('workflow_health.json', health), ('pipeline_lineage_v29.json', lineage),
                              ('report_ready.json', ready)]:
                (p / name).write_text(json.dumps(obj), encoding='utf8')
            main(['--health', str(p / 'workflow_health.json'),
                  '--lineage', str(p / 'pipeline_lineage_v29.json'),
                  '--certificate', str(p / 'report_ready.json'),
                  '--origin-report', str(p / 'origin_monitor_v292.json')])
            output = json.loads((p / 'workflow_health.json').read_text(encoding='utf8'))
            detail = json.loads((p / 'origin_monitor_v292.json').read_text(encoding='utf8'))
            self.assertEqual(output['origin_monitor_v292'], detail)
            self.assertEqual(output['operational_quality_v28']['blockers'], health['operational_quality_v28']['blockers'])

    def test_cli_missing_snapshots_retains_current_monitor(self):
        health, _, _ = inputs()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'workflow_health.json').write_text(json.dumps(health),encoding='utf8')
            main(['--health',str(p/'workflow_health.json'),
                  '--lineage',str(p/'absent_lineage.json'),
                  '--certificate',str(p/'absent_ready.json'),
                  '--origin-report',str(p/'origin_monitor_v292.json')])
            output=json.loads((p/'workflow_health.json').read_text(encoding='utf8'))
            self.assertEqual(output['status'],'attention')
            self.assertEqual(output['origin_monitor_v292']['status'],'missing_lineage_or_certificate')
            self.assertEqual(output['origin_monitor_v292']['missing_inputs']['lineage'],'file_not_published')

    def test_bad_monitor_document_fails_without_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'workflow_health.json'
            p.write_text('garbled',encoding='utf8')
            with self.assertRaises(SystemExit):
                main(['--health',str(p)])
            self.assertEqual(p.read_text(encoding='utf8'),'garbled')


if __name__ == '__main__':
    unittest.main()
