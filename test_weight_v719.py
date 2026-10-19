import unittest

from garmin_recovery import weight, dashboard

REG = {"entries": [
    {"date": "2026-09-28", "weight_kg": 91.5, "source": "derivado"},
    {"date": "2026-10-10", "weight_kg": 89.6, "source": "registro de entreno"},
    {"date": "2026-10-19", "time": "13:34", "weight_kg": 88.3, "source": "Zepp Life"},
    {"date": "2026-10-25", "weight_kg": 80.0}]}


class Weight(unittest.TestCase):
    def test_build(self):
        w = weight.build(REG, "2026-10-19")
        self.assertEqual(w["current"], 88.3)
        self.assertEqual(len(w["points"]), 3)  # la fecha futura se ignora
        self.assertEqual(w["delta_prev"], -1.3)
        self.assertEqual(w["delta_first"], -3.2)
        self.assertTrue(w["has_derived"])
        self.assertIsNone(w["mean7"])  # una sola lectura directa en 7 días

    def test_mean_needs_two_direct_readings(self):
        reg = {"entries": [{"date": "2026-10-17", "weight_kg": 90}, {"date": "2026-10-19", "weight_kg": 88}]}
        self.assertEqual(weight.build(reg, "2026-10-19")["mean7"], 89.0)

    def test_invalid_and_empty(self):
        self.assertIsNone(weight.build(None, "2026-10-19"))
        self.assertIsNone(weight.build({"entries": [{"date": "2026-10-19", "weight_kg": 5}, {"date": "2026-10-19", "weight_kg": True}]}, "2026-10-19"))

    def test_html(self):
        h = dashboard._weight_html(weight.build(REG, "2026-10-19"))
        self.assertIn("88,3 kg", h)
        self.assertIn("calculado", h)
        self.assertEqual(dashboard._weight_html(None), "")

    def test_stale_flag(self):
        self.assertTrue(weight.build({"entries": [{"date": "2026-10-01", "weight_kg": 90}]}, "2026-10-19")["stale"])


if __name__ == "__main__":
    unittest.main()
