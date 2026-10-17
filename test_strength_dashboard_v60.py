"""V6.0: 1RM mínimo (Epley sin RIR) y panel con resumen, RPE y semana."""
import json
import unittest
from pathlib import Path

from muscle_load import epley_lower_bound

ROOT = Path(__file__).resolve().parent


class EpleyLowerBound(unittest.TestCase):
    def test_best_set_and_formula(self):
        sets = [{"reps": 8, "load_kg": 120}, {"reps": 2, "load_kg": 170}, {"reps": 12, "load_kg": 100}]
        self.assertEqual(epley_lower_bound(sets, "barbell"), (181.3, 170, 2))  # 170 × (1 + 2/30)

    def test_single_is_the_load(self):
        self.assertEqual(epley_lower_bound([{"reps": 1, "load_kg": 68}], "barbell"), (68.0, 68, 1))

    def test_excluded_cases(self):
        self.assertEqual(epley_lower_bound([{"reps": 5, "load_kg": 60}], "machine_stack"), (None, None, None))
        self.assertEqual(epley_lower_bound([{"reps": 15, "load_kg": 60}], "barbell"), (None, None, None))
        self.assertEqual(epley_lower_bound([{"reps": 5}], "barbell"), (None, None, None))

    def test_strength_table_and_chart_use_it(self):
        from garmin_recovery.report import chart_strength, strength_table
        rows = [{"date": "2026-10-09", "exercise": "sentadilla", "equipment": "barbell", "peak_declared_load_kg": 170,
                 "top_set_kg": 170, "top_set_reps": 2, "e1rm_min_kg": 181.3, "known_sets": 5, "total_sets": 5},
                {"date": "2026-10-11", "exercise": "sentadilla", "equipment": "barbell", "peak_declared_load_kg": 150,
                 "top_set_kg": 120, "top_set_reps": 8, "e1rm_min_kg": 152.0, "known_sets": 9, "total_sets": 9}]
        table = strength_table(rows)
        self.assertIn("170 × 2", table)
        self.assertIn("181,3 kg", table)
        self.assertIn("sentadilla (1RM mín.)", chart_strength(rows))


class Dashboard(unittest.TestCase):
    def test_dashboard_has_summary_rpe_and_week(self):
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        from garmin_recovery.dashboard import render
        html = render(json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8")))
        for txt in ("En tres líneas", "RPE frente al máximo del día", "Esta semana", "<svg"):
            self.assertIn(txt, html)
        self.assertNotIn("{{EXTRA}}", html)


if __name__ == "__main__":
    unittest.main()
