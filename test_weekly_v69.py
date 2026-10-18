"""Comparación semana a semana (garmin_recovery/weekly_compare.py)."""
import unittest
from datetime import date, timedelta

from garmin_recovery import improvement, weekly_compare as wc

TODAY = "2026-10-18"  # domingo


def trend(n=28, **over):
    end = date.fromisoformat(TODAY)
    rows = []
    for i in range(n - 1, -1, -1):
        d = end - timedelta(days=i)
        row = {"date": d.isoformat(), "hrv_ms": 60.0, "resting_hr": 55.0, "sleep_hours": 7.0, "sleep_score": 75.0,
               "sessions": 1, "srpe": 200.0}
        for k, f in over.items():
            row[k] = f(d, row[k])
        rows.append(row)
    return rows


def sess(first="2026-09-21"):
    return [{"date": first, "rpe": 6, "removed": 0}]


class Weekly(unittest.TestCase):
    def test_complete_weeks_get_delta_and_percent(self):
        t = trend(hrv_ms=lambda d, v: 50.0 if "2026-09-28" <= d.isoformat() <= "2026-10-04" else v)
        c = wc.compare(t, sess(), TODAY, 100.0)
        hrv = next(r for r in c["physio"] if r["key"] == "hrv_ms")
        self.assertAlmostEqual(hrv["delta"], 10.0)
        self.assertAlmostEqual(hrv["pct"], 20.0)
        self.assertEqual(hrv["verdict"], "better")
        self.assertTrue(c["comparable"])

    def test_resting_hr_down_is_better(self):
        t = trend(resting_hr=lambda d, v: 60.0 if "2026-09-28" <= d.isoformat() <= "2026-10-04" else v)
        r = next(x for x in wc.compare(t, sess(), TODAY, 100.0)["physio"] if x["key"] == "resting_hr")
        self.assertEqual(r["verdict"], "better")

    def test_missing_days_block_percent_and_delta(self):
        # solo 4 noches con HRV en la semana anterior: no se compara
        t = trend(hrv_ms=lambda d, v: v if not ("2026-10-09" <= d.isoformat() <= "2026-10-11") else None)
        hrv = next(r for r in wc.compare(t, sess(), TODAY, 100.0)["physio"] if r["key"] == "hrv_ms")
        self.assertIsNone(hrv["delta"])
        self.assertIsNone(hrv["pct"])

    def test_six_of_seven_gives_delta_without_percent(self):
        t = trend(hrv_ms=lambda d, v: None if d.isoformat() == "2026-10-10" else (55.0 if d.isoformat() >= "2026-10-05" else v))
        hrv = next(r for r in wc.compare(t, sess(), TODAY, 100.0)["physio"] if r["key"] == "hrv_ms")
        self.assertIsNotNone(hrv["delta"])
        self.assertIsNone(hrv["pct"])

    def test_current_week_never_compared(self):
        c = wc.compare(trend(), sess(), TODAY, 100.0)
        self.assertEqual(c["weeks"][-1]["start"], "2026-10-12")
        self.assertEqual(c["weeks"][-2]["start"], "2026-10-05")

    def test_load_needs_coverage_and_history(self):
        low = wc.compare(trend(), sess(), TODAY, 40.0)
        self.assertIsNone(low["load"])
        self.assertIn("cobertura", low["load_reason"])
        young = wc.compare(trend(), sess("2026-10-05"), TODAY, 100.0)
        self.assertIsNone(young["load"])
        ok = wc.compare(trend(), sess(), TODAY, 100.0)
        self.assertEqual(ok["load"]["prev"]["sessions"], 7)
        self.assertEqual(ok["load"]["prev"]["srpe"], 1400)

    def test_markdown_in_section_8(self):
        a = improvement.analyze(".", {"date": TODAY, "trend_28d": trend(), "sessions_28d": sess(),
                                      "load": {"srpe_coverage_28d_pct": 100.0}, "decision": {}})
        md = improvement.to_markdown(a)
        self.assertIn("### Semana a semana", md)
        self.assertNotIn("None", md)
        self.assertNotIn("nan", md.lower())

    def test_no_data_does_not_crash(self):
        c = wc.compare([], [], TODAY, None)
        self.assertIn("Semana a semana", wc.to_markdown(c))


if __name__ == "__main__":
    unittest.main()
