import unittest
from report_interpretation_v391 import section, enrich


class InterpretationTests(unittest.TestCase):
    def test_comparison_and_coverage(self):
        data = {'recovery_assessment': {'current': {'hrv_ms': 55}, 'baseline_28d': {'hrv_ms': {'median': 50, 'n': 20}}}}
        result = section(data)
        self.assertIn('+5.0 ms', result)
        self.assertIn('1/5', result)

    def test_insufficient_coverage(self):
        data = {'recovery_assessment': {'current': {'hrv_ms': 55}, 'baseline_28d': {'hrv_ms': {'median': 50, 'n': 3}}}}
        self.assertIn('Cobertura insuficiente', section(data))
        self.assertIn('0/5', section(data))

    def test_missing_and_invalid_data(self):
        self.assertIn('0/5', section({}))
        data = {'recovery_assessment': {'current': {'hrv_ms': float('nan')}, 'baseline_28d': {'hrv_ms': {'median': 50, 'n': 28}}}}
        self.assertIn('No calculable', section(data))

    def test_deterministic_and_non_destructive(self):
        base = '# Informe\n\nDatos'
        a = enrich(base, {})
        self.assertTrue(a.startswith(base))
        self.assertEqual(a, enrich(base, {}))
        self.assertIn('Procedencia', a)


if __name__ == '__main__':
    unittest.main()
