import json
import unittest
from pathlib import Path

from garmin_recovery import dashboard, glance

RES = {"date": "2026-10-19",
       "sessions_28d": [
           {"date": "2026-10-15", "name": "HIIT", "rpe": 8.0, "duration_min": 13.2, "start_local": "2026-10-15T10:03:12"},
           {"date": "2026-10-18", "name": "Fuerza", "rpe": 7.5, "duration_min": 65.5, "start_local": "2026-10-18T10:45:58"}],
       "load": {"week_sessions": 9, "week_load": 142.0, "week_change_pct": 17.4, "coverage_days": 14, "srpe_coverage_7d_pct": 100.0}}


def by_id(chips):
    return {c["id"]: c for c in chips}


class Compose(unittest.TestCase):
    def test_full(self):
        c = by_id(glance.compose(RES, {"today": "post-TN", "tomorrow": "free"},
                                 {"summary": {"available": True, "up": 3, "flat": 0, "down": 0, "comparable": 3}}))
        self.assertEqual(c["ultimo"]["value"], "Fuerza · RPE 7,5")
        self.assertIn("ayer", c["ultimo"]["sub"])
        self.assertEqual(c["registros"]["value"], "2 de 2 con RPE")
        self.assertEqual(c["registros"]["tone"], "good")
        self.assertEqual(c["semana"]["value"], "9 sesiones · carga 142")
        self.assertIn("+17 %", c["semana"]["sub"])
        self.assertEqual(c["turno"]["value"], "Hoy libre tras la noche")
        self.assertEqual(c["progresion"]["value"], "3 ▲ · 0 = · 0 ▼")

    def test_pending_rpe_warns(self):
        res = json.loads(json.dumps(RES))
        res["sessions_28d"].append({"date": "2026-10-19", "name": "WOD", "rpe": None, "start_local": "2026-10-19T09:00:00"})
        c = by_id(glance.compose(res))
        self.assertEqual(c["registros"]["tone"], "warning")
        self.assertIn("faltan 1", c["registros"]["sub"])
        self.assertEqual(c["ultimo"]["value"], "WOD · sin RPE")

    def test_no_weekly_percent_without_full_coverage(self):
        res = json.loads(json.dumps(RES))
        res["load"]["coverage_days"] = 9
        self.assertNotIn("%", by_id(glance.compose(res))["semana"]["sub"])

    def test_empty(self):
        self.assertEqual(glance.compose({"date": "2026-10-19"}), [])


class Html(unittest.TestCase):
    def test_in_dashboard(self):
        res = json.loads((Path(__file__).resolve().parent / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        html = dashboard.render(res, {"glance_shifts": {"today": "TN", "tomorrow": "free"}})
        self.assertIn('aria-label="De un vistazo"', html)
        self.assertIn("Hoy noche 15–08", html)


if __name__ == "__main__":
    unittest.main()
