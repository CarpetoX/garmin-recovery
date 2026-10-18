import unittest
from garmin_recovery.pipeline_lineage import create, parse_event


def event(name, run_id, conclusion='success'):
    return {'workflow_run': {'name': name, 'id': run_id, 'conclusion': conclusion}}


class LineageV29Tests(unittest.TestCase):
    def test_scheduled_root_is_not_report_delivery(self):
        root = create('sync', 100, 'schedule')
        self.assertEqual(root['root']['origin_certainty'], 'github_schedule')
        self.assertFalse(root['complete_chain_verified'])

    def test_manual_root_never_looks_like_schedule(self):
        x = create('sync', 100, 'workflow_dispatch')
        self.assertEqual(x['root']['origin_certainty'], 'dispatch_sender_unverified')

    def test_exact_three_links_and_four_runs(self):
        root = create('sync', 100, 'schedule')
        h = create('heart', 101, 'workflow_run', event('Garmin Recovery Sync', 100), root)
        a = create('advanced', 102, 'workflow_run', event('Garmin Heart Rate Enrichment', 101), h)
        c = create('crossfit', 103, 'workflow_run', event('Garmin Advanced Analytics', 102), a)
        self.assertTrue(c['complete_chain_verified'])
        self.assertEqual([c['stages'][s]['run_id'] for s in ('sync','heart','advanced','crossfit')], [100,101,102,103])
        self.assertEqual(c['exact_link_count'], 3)

    def test_missing_parent_does_not_fabricate_ancestry(self):
        c = create('crossfit', 103, 'workflow_run', event('Garmin Advanced Analytics', 102))
        self.assertEqual(c['status'], 'partial_unverified_parent_artifact')
        self.assertEqual(set(c['stages']), {'crossfit'})
        self.assertFalse(c['complete_chain_verified'])

    def test_incorrect_parent_fails_degraded(self):
        root = create('sync', 100, 'schedule')
        h = create('heart', 101, 'workflow_run', event('Garmin Recovery Sync', 999), root)
        self.assertEqual(h['status'], 'partial_parent_mismatch')
        self.assertFalse(h['complete_chain_verified'])

    def test_invalid_event_name_rejected(self):
        with self.assertRaises(ValueError):
            create('heart', 101, 'workflow_run', event('Wrong Pipeline', 100))

    def test_unsuccessful_parent_rejected(self):
        with self.assertRaises(ValueError):
            create('heart', 101, 'workflow_run', event('Garmin Recovery Sync', 100, 'failure'))

    def test_manual_child_is_independent(self):
        child = create('advanced', 101, 'workflow_dispatch')
        self.assertEqual(child['status'], 'independent_unverified')
        self.assertIsNone(child['parent_run_id'])

    def test_invalid_ids_and_malformed_json(self):
        for invalid in (0, -1, '', None, 'x'):
            with self.assertRaises(ValueError):
                create('sync', invalid, 'schedule')
        for invalid in ('[1]', '{bad'):
            with self.assertRaises(ValueError):
                parse_event(invalid)

    def test_stale_parent_full_chain_refused(self):
        root = create('sync', 100, 'schedule')
        h = create('heart', 101, 'workflow_run', event('Garmin Recovery Sync', 100), root)
        a = create('advanced', 102, 'workflow_run', event('Garmin Heart Rate Enrichment', 101), h)
        bad = create('crossfit', 103, 'workflow_run', event('Garmin Advanced Analytics', 999), a)
        self.assertNotEqual(bad['status'], 'exact_chain_verified')


if __name__ == '__main__':
    unittest.main()
