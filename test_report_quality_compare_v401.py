"""V4.0.1 offline regression tests; no GitHub writes, network, or live API calls."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from cycle_snapshot_report_v38 import SnapshotError
from garmin_report_v40 import render
from test_garmin_report_v40 import fixture
from report_quality_compare_v401 import compare_texts, evaluate

LEGACY = '''# V3.9
| HRV nocturna | 66 ms | 58 ms | n=17 |
| Sueño | 7.23 h | 7.27 h | n=17 |
| Puntuación sueño | 79/100 | 77/100 | n=17 |
| FC reposo | 53 lpm | 55.5 lpm | n=17 |
| FC nocturna | 58.3 lpm | 62.5 lpm | n=17 |
- Sesiones: 9; con RPE: 9.
- RPE medio registrado: 6.39; sesiones RPE alto: 4.
- sRPE calculado con duración grabada: 1457.7; minutos grabados: 262.3.
- Volumen externo mínimo cuantificado: 30465 kg; bloques de fuerza sin peso cuantificado: 5.
### Evolución diaria
| Fecha | Sesiones | RPE medio | sRPE |
| 2026-10-06 | 1 | 6 | 100 |
| 2026-10-07 | 2 | 6 | 100 |
| 2026-10-08 | 1 | 6 | 100 |
| 2026-10-09 | 0 | No disponible | 100 |
| 2026-10-10 | 1 | 6 | 100 |
| 2026-10-11 | 2 | 6 | 100 |
| 2026-10-12 | 0 | No disponible | 100 |
'''


def assess(ledger=None, legacy=LEGACY, text=None, meta=None, completeness='complete'):
    if ledger is None:
        ledger, cid = fixture()
    else:
        cid = ledger["cycles"][-1]["cycle_id"]
    if text is None or meta is None:
        text, meta = render(ledger, cid)
    return compare_texts(ledger, cid, legacy, text, meta, completeness)


class V401Tests(unittest.TestCase):
    def test_complete_legacy_v40_semantically_compatible(self):
        result = assess()
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['compared_metrics'], 9)
        self.assertIn('rounding_mean_rpe', result['notices'])
        self.assertEqual(result['errors'], [])

    def test_missing_v40_metric_is_regression(self):
        ledger, cid = fixture()
        content, meta = render(ledger, cid)
        content = content.replace('| Sesiones registradas | 9 |', '| Sesiones registradas | No disponible |')
        result = assess(ledger, text=content, meta=meta)
        self.assertEqual(result['status'], 'regression_detected')
        self.assertIn('v40_missing_sessions', result['errors'])

    def test_wrong_v40_value_is_regression(self):
        ledger, cid = fixture()
        content, meta = render(ledger, cid)
        content = content.replace('| RPE medio | 6.4 |', '| RPE medio | 8.4 |')
        self.assertIn('v40_value_mismatch_mean_rpe', assess(ledger, text=content, meta=meta)['errors'])

    def test_pending_sleep_not_used_or_comparison_penalized(self):
        ledger, _ = fixture(confirmed=False)
        result = assess(ledger)
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['compared_metrics'], 5)
        self.assertTrue(result['v40_sleep_confirmed'] is False)
        self.assertEqual(sum(x['status'] == 'not_comparable_sleep_pending' for x in result['metric_checks']), 4)

    def test_pending_sleep_exposure_blocks(self):
        ledger, cid = fixture(confirmed=False)
        content, meta = render(ledger, cid)
        content = content.replace('| HRV nocturna | Pendiente |', '| HRV nocturna | 66 ms |')
        self.assertIn('pending_sleep_exposed_hrv_ms', assess(ledger, text=content, meta=meta)['errors'])

    def test_bad_chart_missing_row_blocks(self):
        ledger, cid = fixture()
        content, meta = render(ledger, cid)
        content = content.replace('| 2026-10-10 |', '| missing-2026-10-10 |')
        self.assertIn('v40_chart_dates_missing', assess(ledger, text=content, meta=meta)['errors'])

    def test_incomplete_chart_explicit(self):
        ledger, cid = fixture(complete=False)
        result = assess(ledger, completeness='partial_missing_crossfit_chart')
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['errors'], [])

    def test_not_found_in_v39_is_not_falsely_counted(self):
        result = assess(legacy='legacy without metric fields')
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['compared_metrics'], 0)
        self.assertIn('v39_not_comparable_sessions', result['notices'])

    def test_hash_mismatch_is_rejected(self):
        ledger, cid = fixture()
        ledger['cycles'][0]['snapshot']['recovery_assessment']['score'] = 90
        with self.assertRaises(SnapshotError):
            assess(ledger)

    def test_metadata_wrong_snapshot_is_regression(self):
        ledger, cid = fixture()
        content, meta = render(ledger, cid)
        meta['snapshot_sha256'] = 'bad'
        self.assertIn('v40_snapshot_hash_mismatch', assess(ledger, text=content, meta=meta)['errors'])

    def test_delivery_not_claimed(self):
        ledger, cid = fixture()
        content, meta = render(ledger, cid)
        meta['delivery'] = 'delivered'
        self.assertIn('v40_delivery_claim_invalid', assess(ledger, text=content, meta=meta)['errors'])

    def test_deterministic_and_no_mutation(self):
        ledger, _ = fixture()
        before = copy.deepcopy(ledger)
        a, b = assess(ledger), assess(ledger)
        self.assertEqual(a, b)
        self.assertEqual(ledger, before)

    def test_integrated_v39_renderer_is_invoked(self):
        ledger, cid = fixture()
        with patch('report_quality_compare_v401.render_v39', return_value=(LEGACY, 'complete')):
            result = evaluate(ledger, cid)
        self.assertEqual(result['status'], 'pass')

    def test_real_ledger_when_available(self):
        path = Path('report_cycles.json')
        if not path.exists():
            self.skipTest('Real ledger not packaged in local test bundle')
        ledger = json.loads(path.read_text(encoding='utf-8'))
        from garmin_report_v40 import latest_id
        result = evaluate(ledger, latest_id(ledger))
        self.assertEqual(result['status'], 'pass', result['errors'])
        self.assertGreater(result['compared_metrics'], 0)


if __name__ == '__main__':
    unittest.main()
