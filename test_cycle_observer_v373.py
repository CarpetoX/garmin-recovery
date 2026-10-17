import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch

from garmin_recovery import cycle_observer as m

NOW = datetime(2026, 10, 12, 18, 0, tzinfo=ZoneInfo('Europe/Madrid'))

class ObserverTests(unittest.TestCase):
    def test_missing_certificate_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = m.observe(Path(tmp), now=NOW, fetch_run=lambda _: {})
        self.assertEqual(r['state'], 'not_eligible')
        self.assertEqual(r['chatgpt_delivery'], 'unverified_no_receipt')

    def test_fetches_each_independent_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'report_ready.json').write_text(json.dumps({'chain': {s: {'id': i+1} for i, s in enumerate(m.STAGES)}}))
            (root / 'report_cycles.json').write_text('{}')
            called = []
            def fetch(i):
                called.append(i)
                return {'id': i, 'status': 'completed', 'conclusion': 'success'}
            with patch.object(m, 'evaluate', return_value={'state':'eligible_certified_snapshot', 'chatgpt_delivery':'unverified_no_receipt'}) as mocked:
                result = m.observe(root, now=NOW, fetch_run=fetch)
            self.assertEqual(called, [1,2,3,4])
            self.assertEqual(mocked.call_args.kwargs['actions']['crossfit']['id'], 4)
            self.assertEqual(result['state'], 'eligible_certified_snapshot')

    def test_failed_action_remains_not_eligible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'report_ready.json').write_text(json.dumps({'chain': {s: {'id': i+1} for i, s in enumerate(m.STAGES)}}))
            (root / 'report_cycles.json').write_text('{}')
            with patch.object(m, 'evaluate', return_value={'state': 'not_eligible', 'reason':'action failed'}):
                result = m.observe(root, now=NOW, fetch_run=lambda i: {'id':i,'status':'completed','conclusion':'failure'})
            self.assertEqual(result['state'], 'not_eligible')

    def test_api_error_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'report_ready.json').write_text(json.dumps({'chain': {s: {'id': i+1} for i, s in enumerate(m.STAGES)}}))
            (root / 'report_cycles.json').write_text('{}')
            def broken(_):
                raise OSError('unavailable')
            result = m.observe(root, now=NOW, fetch_run=broken)
            self.assertEqual(result['state'], 'not_eligible')

    def test_missing_credentials_rejected(self):
        with self.assertRaises(ValueError):
            m.github_fetcher('owner/repo', '')

if __name__ == '__main__':
    unittest.main()
