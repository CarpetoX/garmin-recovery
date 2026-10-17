"""V3.6.1 regression: freshness, independent optional report, rollback, and provenance."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from crossfit_report_v36 import validate
from crossfit_report_guard_v361 import (
    REPORT_NAMES, STATE_NAME, positive_id,
    previous_report, run_once,
)
from test_crossfit_report_v36 import fixture, NOW


class GuardV361Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.parts = fixture()
        self.write_inputs()

    def write(self, name, obj):
        (self.root / name).write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')

    def write_inputs(self):
        for name, obj in zip(('crossfit_insights.json', 'training_trends_v31.json',
                              'recovery_assessment.json', 'data_quality.json', 'report_ready.json'), self.parts):
            self.write(name, obj)

    def call(self, event='workflow_dispatch', run=123, now=NOW):
        return run_once(self.root, event_name=event, run_id=run, now=now)

    def test_report_success_and_all_files(self):
        s = self.call()
        self.assertEqual(s['state'], 'current_validated')
        self.assertTrue(s['report_current'])
        self.assertEqual(s['cycle_certificate'], 'not_linked_to_a_current_certificate')
        self.assertTrue(all((self.root / p).is_file() for p in REPORT_NAMES))
        validate(json.loads((self.root / REPORT_NAMES[0]).read_text()))
        self.assertEqual(json.loads((self.root / STATE_NAME).read_text())['state'], 'current_validated')

    def test_manual_run_does_not_infer_scheduled_certificate(self):
        s = self.call()
        self.assertNotEqual(s['cycle_certificate'], 'same_certified_cycle')
        self.assertEqual(s['github_event'], 'workflow_dispatch')

    def test_automatic_same_certificate_requires_both_lineage_and_run(self):
        ready = copy.deepcopy(self.parts[-1]); ready['chain'] = {'crossfit': {'id': 123}, 'sync': {'id': 77}}
        self.write('report_ready.json', ready)
        self.write('pipeline_lineage_v29.json', {'complete_chain_verified': True, 'run_id': 123,
                                                'root': {'run_id': 77}})
        self.assertEqual(self.call(event='workflow_run')['cycle_certificate'], 'same_certified_cycle')

    def test_stale_certificate_does_not_claim_binding(self):
        ready = copy.deepcopy(self.parts[-1]); ready['chain'] = {'crossfit': {'id': 999}, 'sync': {'id': 77}}
        self.write('report_ready.json', ready)
        self.write('pipeline_lineage_v29.json', {'complete_chain_verified': True, 'run_id': 123,
                                                'root': {'run_id': 77}})
        self.assertNotEqual(self.call(event='workflow_run')['cycle_certificate'], 'same_certified_cycle')

    def test_source_mismatch_preserves_prior_outputs(self):
        self.assertTrue(self.call()['report_current'])
        baseline = {x: (self.root / x).read_bytes() for x in REPORT_NAMES}
        bad = copy.deepcopy(self.parts[1]); bad['source_generated_at'] = '2026-10-11T09:00:21+02:00'
        self.write('training_trends_v31.json', bad)
        state = self.call()
        self.assertEqual(state['state'], 'generation_failed_previous_retained')
        self.assertEqual(state['failure_kind'], 'ReportError')
        self.assertEqual(state['previous_report']['state'], 'present_not_current')
        self.assertEqual(baseline, {x: (self.root / x).read_bytes() for x in REPORT_NAMES})

    def test_old_source_is_not_current(self):
        state = self.call(now=NOW+timedelta(minutes=21))
        self.assertFalse(state['report_current'])
        self.assertEqual(state['failure_kind'], 'ReportError')
        self.assertFalse(any((self.root / p).exists() for p in REPORT_NAMES))

    def test_future_source_is_not_current(self):
        self.parts[0]['generated_at'] = (NOW + timedelta(minutes=5)).isoformat()
        self.write_inputs()
        self.assertFalse(self.call()['report_current'])

    def test_missing_crossfit_reports_error_not_fake_success(self):
        (self.root / 'crossfit_insights.json').unlink()
        s = self.call()
        self.assertFalse(s['report_current'])
        self.assertTrue((self.root / STATE_NAME).exists())

    def test_invalid_json_reports_error(self):
        (self.root / 'training_trends_v31.json').write_text('{bad', encoding='utf-8')
        self.assertFalse(self.call()['report_current'])

    def test_unmatched_day_report_not_published(self):
        self.parts[1]['as_of_date'] = '2026-10-11'; self.write_inputs()
        self.assertFalse(self.call()['report_current'])

    def test_initial_prior_absent(self):
        self.assertEqual(previous_report(self.root)['state'], 'absent_or_invalid')

    def test_second_success_observes_old_report_but_updates(self):
        self.assertTrue(self.call()['report_current'])
        s = self.call()
        self.assertTrue(s['report_current'])
        self.assertEqual(s['previous_report']['state'], 'present_not_current')

    def test_missing_run_id_cannot_certify(self):
        self.assertEqual(self.call(run=None)['cycle_certificate'], 'not_verified_missing_run_id')
        self.assertIsNone(positive_id(True))
        self.assertIsNone(positive_id('0'))

    def test_no_message_delivery_claim(self):
        s = self.call()
        self.assertEqual(s['chatgpt_delivery'], 'unverified_no_receipt')
        self.assertEqual(json.loads((self.root / REPORT_NAMES[0]).read_text())['source_provenance']['chatgpt_delivery'],
                         'unverified_no_receipt')

    def test_invalid_v35_baseline_fails_closed(self):
        self.parts[1]['performance_report_v32']['performance_enhancements_v35']['version'] = '3.4'
        self.write_inputs()
        s = self.call()
        self.assertEqual(s['state'], 'generation_failed_previous_retained')

    def test_validate_candidate_not_publish_on_corrupt_output(self):
        with patch('crossfit_report_guard_v361.svg_chart', return_value='no svg'):
            s = self.call()
        self.assertFalse(s['report_current'])
        self.assertFalse((self.root / REPORT_NAMES[0]).exists())

    def test_publication_error_restores_files(self):
        self.assertTrue(self.call()['report_current'])
        saved = {x: (self.root / x).read_bytes() for x in REPORT_NAMES}
        import crossfit_report_guard_v361 as mod
        os_replace = mod.os.replace
        def fail_second(src, dst):
            if Path(dst).name == REPORT_NAMES[1] and '.diagnostics_current' in str(src):
                raise OSError('simulated filesystem failure')
            return os_replace(src, dst)
        with patch.object(mod.os, 'replace', side_effect=fail_second):
            result = self.call()
        self.assertFalse(result['report_current'])
        self.assertEqual({x: (self.root / x).read_bytes() for x in REPORT_NAMES}, saved)

    def test_wrong_lineage_root_not_certified(self):
        ready = copy.deepcopy(self.parts[-1]); ready['chain'] = {'crossfit': {'id': 123}, 'sync': {'id': 77}}
        self.write('report_ready.json', ready)
        self.write('pipeline_lineage_v29.json', {'complete_chain_verified': True, 'run_id': 123,
                                                'root': {'run_id': 88}})
        self.assertNotEqual(self.call(event='workflow_run')['cycle_certificate'], 'same_certified_cycle')

    def test_status_has_no_credentials(self):
        self.call()
        text = (self.root / STATE_NAME).read_text()
        self.assertNotIn('token', text.lower())
        self.assertNotIn('password', text.lower())

    def test_source_time_failure_does_not_mutate_sources(self):
        saved = [(self.root / p).read_bytes() for p in ('crossfit_insights.json','training_trends_v31.json')]
        self.call(now=NOW+timedelta(hours=2))
        self.assertEqual(saved, [(self.root / p).read_bytes() for p in ('crossfit_insights.json','training_trends_v31.json')])


if __name__ == '__main__':
    unittest.main()
