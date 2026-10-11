import copy
import unittest
from datetime import datetime, timezone
from ops_metrics_v28 import report

NOW = datetime(2026, 10, 11, 13, 0, tzinfo=timezone.utc)

class OpsMetricsTests(unittest.TestCase):
    def base(self):
        return {'due': 3, 'matched': 0, 'recovered_count': 3,
                'recovered_by_unattributed': ['a', 'b', 'c']}
    def test_recovered_is_not_cron_success(self):
        r = report(NOW, self.base(), {}, {})
        self.assertEqual(r['cron_confirmed_pct'], 0)
        self.assertEqual(r['schedule_state'], 'recovered_without_automatic_cron_proof')
        self.assertIn('github_schedule_not_verified', r['blockers'])
    def test_all_cron_success(self):
        s = dict(self.base(), matched=3, recovered_count=0, recovered_by_unattributed=[])
        r = report(NOW, s, {}, {})
        self.assertEqual(r['cron_confirmed_pct'], 100)
        self.assertEqual(r['schedule_state'], 'cron_observed_all')
    def test_uncovered_slot(self):
        s = dict(self.base(), matched=1, recovered_count=0, recovered_by_unattributed=[])
        self.assertIn('sync_slot_uncovered', report(NOW, s, {}, {})['blockers'])
    def test_empty_due_never_fabricates_100_percent(self):
        s = dict(self.base(), due=0, matched=0, recovered_count=0)
        self.assertIsNone(report(NOW, s, {}, {})['cron_confirmed_pct'])
    def test_unverified_audit_does_not_infer_state(self):
        r = report(NOW, {'state':'unverified'}, {}, {})
        self.assertEqual(r['schedule_state'], 'unknown')
    def test_invalid_ambiguous_count(self):
        s = dict(self.base(), matched=2, recovered_count=3)
        self.assertEqual(report(NOW, s, {}, {})['schedule_state'], 'unknown')
    def test_manual_origin_is_unverified(self):
        rs = {'sync': [{'event':'workflow_dispatch','created_at':'2026-10-11T10:00:00Z'}]}
        self.assertEqual(report(NOW, self.base(), {}, rs)['last_sync_origin'],
                         'workflow_dispatch_caller_unverified')
    def test_repository_dispatch_not_apps_script_proof(self):
        rs = {'sync': [{'event':'repository_dispatch','created_at':'2026-10-11T10:00:00Z'}]}
        self.assertEqual(report(NOW, self.base(), {}, rs)['last_sync_origin'],
                         'repository_dispatch_sender_unverified')
    def test_pipeline_duration_only_if_completed(self):
        pipe = {'state':'completed_outside_report_slots','stages':{
            'sync':{'created_at':'2026-10-11T10:00:00Z'},
            'crossfit':{'updated_at':'2026-10-11T10:02:30Z'}}}
        self.assertEqual(report(NOW, self.base(), pipe, {})['latest_chain_duration_minutes'],2.5)
        pipe['state'] = 'in_progress'
        self.assertIsNone(report(NOW, self.base(), pipe, {})['latest_chain_duration_minutes'])
    def test_mismatched_timestamps_not_presented_as_latency(self):
        pipe = {'state':'ready','stages':{
            'sync':{'created_at':'2026-10-11T11:00:00Z'},
            'crossfit':{'updated_at':'2026-10-11T10:02:30Z'}}}
        self.assertIsNone(report(NOW,self.base(),pipe,{})['latest_chain_duration_minutes'])
    def test_no_claim_of_delivery(self):
        self.assertEqual(report(NOW,self.base(),{}, {})['report_delivery_receipt'],'unavailable')

if __name__ == '__main__':
    unittest.main()
