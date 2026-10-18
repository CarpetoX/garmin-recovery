import unittest
from garmin_recovery.json_contracts import audit


def fixtures():
    return {
        'advanced_analytics.json': {'generated_at':'2026-10-11T13:00:00+02:00',
                                    'rpe_feedback': {'source_rows_sha256':'abc', 'advanced_run_id':'123'}},
        'training_feedback.json': {'source_rows_sha256':'abc','advanced_run_id':'123','remote_rows_loaded':9},
        'crossfit_insights.json': {'generated_at':'2026-10-11T13:01:00+02:00',
                                  'sheet_source':'cycle_snapshot','sheet_rows_loaded':9,
                                  'activities':[{'activity_id':'i-1','rpe_used':6}]},
    }


class V30ContractTests(unittest.TestCase):
    def test_valid_snapshot(self):
        self.assertEqual(audit(fixtures())['status'], 'ok')

    def test_mismatched_sha_rejected(self):
        data = fixtures()
        data['training_feedback.json']['source_rows_sha256'] = 'other'
        self.assertIn('cycle_fingerprint_mismatch', [e['code'] for e in audit(data)['issues']])

    def test_mismatched_run_id_rejected(self):
        data = fixtures()
        data['training_feedback.json']['advanced_run_id'] = 'other'
        self.assertIn('cycle_fingerprint_mismatch', [e['code'] for e in audit(data)['issues']])

    def test_mismatched_row_count_rejected(self):
        data=fixtures()
        data['crossfit_insights.json']['sheet_rows_loaded'] = 8
        self.assertIn('rpe_row_count_mismatch', [e['code'] for e in audit(data)['issues']])

    def test_no_source_not_assumed_good(self):
        result=audit({})
        self.assertEqual(result['status'], 'unavailable')

    def test_duplicate_id(self):
        data=fixtures()
        data['crossfit_insights.json']['activities'] *= 2
        self.assertIn('duplicate_activity_id',[e['code'] for e in audit(data)['issues']])

    def test_live_manual_source_is_not_forced_to_match_advanced(self):
        data=fixtures()
        data['crossfit_insights.json']['sheet_source']='live_csv'
        data['training_feedback.json']['source_rows_sha256']='other'
        self.assertEqual(audit(data)['status'],'ok')

    def test_missing_created_at(self):
        data=fixtures()
        del data['advanced_analytics.json']['generated_at']
        self.assertIn('missing_generated_at',[e['code'] for e in audit(data)['issues']])


if __name__=='__main__':
    unittest.main()
