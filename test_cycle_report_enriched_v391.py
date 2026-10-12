import copy
import unittest
from unittest.mock import patch
from cycle_snapshot_report_v38 import SnapshotError
from cycle_report_enriched_v391 import render


class EnrichedReportTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {'cycles': []}
        self.cid = '2026-10-12-1645'
        self.data = {'recovery_assessment': {'current': {'hrv_ms': 55},
            'baseline_28d': {'hrv_ms': {'median': 50, 'n': 20}}}}
        self.cert = {'data': self.data}

    @patch('cycle_report_enriched_v391.build')
    @patch('cycle_report_enriched_v391.render_legacy')
    def test_complete_preserves_chart(self, old, build):
        old.return_value = ('# Original\n\n### Gráfica textual — carga sRPE diaria\n\n```text\n7\n```', 'complete')
        build.return_value = self.cert
        report, state = render(self.ledger, self.cid)
        self.assertEqual(state, 'complete')
        self.assertIn('```text\n7\n```', report)
        self.assertIn('+5.0 ms', report)

    @patch('cycle_report_enriched_v391.build')
    @patch('cycle_report_enriched_v391.render_legacy')
    def test_partial_retains_classification(self, old, build):
        old.return_value = ('# Parcial\n\nGráfica diaria CrossFit: no disponible', 'partial_missing_crossfit_chart')
        build.return_value = self.cert
        report, state = render(self.ledger, self.cid)
        self.assertEqual(state, 'partial_missing_crossfit_chart')
        self.assertIn('Gráfica diaria CrossFit: no disponible', report)
        self.assertIn('Interpretación técnica', report)

    @patch('cycle_report_enriched_v391.build')
    @patch('cycle_report_enriched_v391.render_legacy')
    def test_deterministic(self, old, build):
        old.return_value = ('# Base', 'complete')
        build.return_value = self.cert
        self.assertEqual(render(self.ledger, self.cid), render(self.ledger, self.cid))

    @patch('cycle_report_enriched_v391.render_legacy', side_effect=SnapshotError('SHA mismatch'))
    def test_invalid_snapshot_rejected(self, old):
        with self.assertRaises(SnapshotError):
            render(self.ledger, self.cid)

    @patch('cycle_report_enriched_v391.build', side_effect=SnapshotError('SHA mismatch'))
    @patch('cycle_report_enriched_v391.render_legacy', return_value=('# Base', 'complete'))
    def test_secondary_integrity_failure_rejected(self, old, build):
        with self.assertRaises(SnapshotError):
            render(self.ledger, self.cid)


if __name__ == '__main__':
    unittest.main()
