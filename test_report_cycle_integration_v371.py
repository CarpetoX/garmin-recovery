import copy
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from report_cycle_integration_v371 import evaluate, digest
from test_report_cycle_guard_v37 import fixture, NOW


def sample():
    cert = fixture()
    entry = {'cycle_id': cert['cycle_id'], 'state': 'data_ready',
             'sync_run_id': 1, 'crossfit_run_id': 4,
             'source_generated_at': copy.deepcopy(cert['source_generated_at']),
             'snapshot': {'date': '2026-10-12', 'value': 5}}
    entry['snapshot_sha256'] = digest(entry['snapshot'])
    actions = {name: {'id': i+1, 'status': 'completed', 'conclusion': 'success'}
               for i, name in enumerate(('sync','heart','advanced','crossfit'))}
    report = {'state': 'current_validated', 'report_current': True,
              'cycle_certificate': 'not_linked_to_a_current_certificate',
              'github_run_id': 99}
    return cert, {'cycles': [entry]}, report, actions


class IntegrationTests(unittest.TestCase):
    def check(self, parts, **kwargs):
        c, l, r, a = parts
        return evaluate(c, l, r, now=kwargs.get('now', NOW), actions=kwargs.get('actions', a))

    def test_valid_snapshot_with_independent_report(self):
        x = self.check(sample())
        self.assertEqual(x['state'], 'eligible_certified_snapshot')
        self.assertEqual(x['report_v36_link'], 'independent_not_certified')

    def test_report_can_be_same_cycle(self):
        parts = sample()
        parts[2].update(cycle_certificate='same_certified_cycle', github_run_id=4,
                        source_generated_at=parts[0]['source_generated_at']['crossfit_insights.json'])
        self.assertEqual(self.check(parts)['report_v36_link'], 'same_cycle')

    def test_missing_actions_blocks(self):
        self.assertEqual(self.check(sample(), actions=None)['state'], 'not_eligible')

    def test_crossfit_in_progress_blocks(self):
        parts = sample(); parts[3]['crossfit']['status'] = 'in_progress'
        self.assertEqual(self.check(parts)['state'], 'not_eligible')

    def test_wrong_run_blocks(self):
        parts = sample(); parts[3]['heart']['id'] = 200
        self.assertEqual(self.check(parts)['state'], 'not_eligible')

    def test_bad_snapshot_hash_blocks(self):
        parts = sample(); parts[1]['cycles'][0]['snapshot']['value'] = 6
        self.assertEqual(self.check(parts)['state'], 'not_eligible')

    def test_mixed_sources_block(self):
        parts = sample(); parts[1]['cycles'][0]['source_generated_at']['daily_summary.json'] = '2026-10-11T16:59:00+02:00'
        self.assertEqual(self.check(parts)['state'], 'not_eligible')

    def test_duplicate_cycle_blocks(self):
        parts = sample(); parts[1]['cycles'].append(copy.deepcopy(parts[1]['cycles'][0]))
        self.assertEqual(self.check(parts)['state'], 'not_eligible')

    def test_no_actions_no_delivery_claim(self):
        x = self.check(sample(), actions={})
        self.assertEqual(x['chatgpt_delivery'], 'unverified_no_receipt')
        self.assertEqual(x['state'], 'not_eligible')

    def test_future_certificate_blocks(self):
        parts = sample(); parts[0]['verified_at'] = '2026-10-12T17:11:00+02:00'
        self.assertEqual(self.check(parts)['state'], 'not_eligible')


if __name__ == '__main__':
    unittest.main()
