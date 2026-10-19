import json
import unittest
from pathlib import Path

from garmin_recovery import dashboard, shiftstrip

CAL = {"days": {"2026-10-18": "TN", "2026-10-22": "MT", "2026-10-23": "TN"}, "confirmed_months": ["2026-10"]}
ROOT = Path(__file__).resolve().parent


class ShiftStrip(unittest.TestCase):
    def test_post_tn_morning_and_free_day(self):
        s = shiftstrip.compute(CAL, "2026-10-19", 6.5)
        r0, r1 = s["rows"]
        self.assertEqual(r0["blocks"], [{"code": "TN", "start": 0.0, "end": 8.0}])
        self.assertEqual(r0["now"], 6.5)
        self.assertEqual(r1["blocks"], [])
        self.assertTrue(s["available"])

    def test_mt_and_tn_tomorrow(self):
        s = shiftstrip.compute(CAL, "2026-10-22", 12)
        self.assertEqual(s["rows"][0]["blocks"], [{"code": "MT", "start": 8.0, "end": 22.0}])
        self.assertEqual(s["rows"][1]["blocks"], [{"code": "TN", "start": 15.0, "end": 24.0}])

    def test_unknown_outside_calendar(self):
        s = shiftstrip.compute(CAL, "2027-03-01", 9)
        self.assertFalse(s["available"])
        self.assertEqual(dashboard._shift_strip_html(s), "")

    def test_html_in_dashboard(self):
        res = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        html = dashboard.render(res, {"shifts": shiftstrip.compute(CAL, "2026-10-22", 12)})
        self.assertIn('aria-label="Turnos de hoy y mañana"', html)
        self.assertIn("turno de mañana y tarde 08:00–22:00", html)
        self.assertNotIn('aria-label="Turnos de hoy y mañana"', dashboard.render(res, {}))


if __name__ == "__main__":
    unittest.main()
