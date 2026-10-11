import unittest
from copy import deepcopy
from origin_monitor_v292 import origin, report


def example(source='signed'):
    root = {'run_id': 301, 'event': 'workflow_dispatch'}
    if source == 'signed':
        root['origin_v291'] = dict(github_event='workflow_dispatch',
            source_verified=True, origin_source='apps_script_backup',
            auth_method='hmac_sha256_shared_secret_v291', cycle_id='2026-10-11-1645')
    if source == 'schedule':
        root['event'] = 'schedule'
    line = dict(root=root, stage='crossfit', run_id=304, complete_chain_verified=True,
                exact_link_count=3)
    cert = dict(cycle_id='2026-10-11-1645', slot_at='2026-10-11T16:45:00+02:00',
                verified_at='2026-10-11T17:00:00+02:00', status='ready',
                chain=dict(sync=dict(id=301,started_at='2026-10-11T16:59:00+02:00'),
                           crossfit=dict(id=304)))
    return line, cert


class OriginMonitorTests(unittest.TestCase):
    def test_signed(self):
        self.assertEqual(origin(example()[0])['source'], 'apps_script_backup')
    def test_schedule(self):
        self.assertEqual(origin(example('schedule')[0])['source'], 'github_schedule')
    def test_unsigned_not_manual(self):
        self.assertEqual(origin(example('unsigned')[0])['source'], 'dispatch_unattributed')
    def test_unsigned_repository_dispatch(self):
        line, _ = example('unsigned'); line['root']['event'] = 'repository_dispatch'
        self.assertFalse(origin(line)['verified'])
    def test_missing_hmac_auth_method(self):
        line, _ = example(); del line['root']['origin_v291']['auth_method']
        self.assertFalse(origin(line)['verified'])
    def test_mismatched_auth_event(self):
        line, _ = example(); line['root']['origin_v291']['github_event'] = 'repository_dispatch'
        self.assertFalse(origin(line)['verified'])
    def test_root_mismatch(self):
        line, cert = example(); cert['chain']['sync']['id'] = 302
        self.assertEqual(report(line, cert)['origin']['source'], 'unknown')
    def test_crossfit_mismatch(self):
        line, cert = example(); cert['chain']['crossfit']['id'] = 309
        self.assertFalse(report(line, cert)['lineage_complete_verified'])
    def test_incomplete_chain(self):
        line, cert = example(); line['complete_chain_verified'] = False
        self.assertFalse(report(line, cert)['data_ready'])
    def test_wrong_cycle(self):
        line, cert = example(); cert['cycle_id'] = '2026-10-11-2245'
        self.assertEqual(report(line, cert)['origin']['source'], 'unknown')
    def test_delay(self):
        result = report(*example())
        self.assertEqual(result['punctuality']['sync_delay_minutes'], 14.0)
        self.assertEqual(result['punctuality']['data_ready_delay_minutes'], 15.0)
    def test_no_delivery_claim(self):
        self.assertEqual(report(*example())['chatgpt_delivery'], 'unconfirmed_without_receipt')
    def test_no_history_claim(self):
        self.assertTrue(report(*example())['historical_7_28d_slo'].startswith('unavailable'))
    def test_inputs_unchanged(self):
        line, cert = example(); a,b = deepcopy(line),deepcopy(cert)
        report(line,cert); self.assertEqual((line,cert),(a,b))

if __name__ == '__main__':
    unittest.main()
