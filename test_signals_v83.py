"""V8.3: señales a favor y en contra cuando los modelos discrepan; solo cifras de los datos y sin tocar la decisión."""
import unittest

from garmin_recovery.dashboard import _signals_html
from garmin_recovery.signals import compute

RESULT = {"decision": {"zone": "green", "registry": [{"id": "recovery_assessment_v2", "score": 88},
                                                     {"id": "readiness_hybrid", "score": 76}]}}
DAY = {"training_readiness": {"score": 39, "level": "LOW", "sleep_factor_feedback": "VERY_GOOD", "sleep_factor_percent": 95,
                              "recovery_time_feedback": "MODERATE", "recovery_time_factor_percent": 51, "recovery_time_hours": 30.1},
       "hrv_status": {"last_night_avg": 84, "weekly_avg": 46, "status": "UNBALANCED",
                      "baseline": {"balanced_low": 47, "balanced_upper": 81}},
       "sleep_detail": {"sleep_hours": 8.37}}


class Signals(unittest.TestCase):
    def test_mixed_day(self):
        s = compute(RESULT, DAY)
        self.assertTrue(s["show"])
        self.assertEqual((s["official"], s["hybrid"], s["garmin"], s["garmin_level"]), (88, 76, 39, "bajo"))
        self.assertIn("Sueño según Garmin: muy bueno (95 %)", s["favorable"])
        self.assertIn("HRV de anoche 84 ms, por encima de tu rango equilibrado (47–81)", s["favorable"])
        self.assertTrue(any("30 h pendientes" in x for x in s["restrictive"]))
        self.assertTrue(any("7 días 46 ms" in x for x in s["restrictive"]))
        self.assertIn("no entra en la decisión", s["why"])
        self.assertIsNotNone(s["advice"])
        html = _signals_html(s)
        self.assertIn('id="senales"', html)
        self.assertIn("En contra", html)

    def test_hidden_when_models_agree(self):
        day = {"training_readiness": {"score": 80, "level": "HIGH", "sleep_factor_feedback": "GOOD", "recovery_time_hours": 4},
               "hrv_status": {"last_night_avg": 60, "weekly_avg": 58, "status": "BALANCED",
                              "baseline": {"balanced_low": 47, "balanced_upper": 81}}}
        s = compute(RESULT, day)
        self.assertFalse(s["show"])
        self.assertEqual(_signals_html(s), "")
        self.assertFalse(compute(RESULT, None)["show"])


if __name__ == "__main__":
    unittest.main()
