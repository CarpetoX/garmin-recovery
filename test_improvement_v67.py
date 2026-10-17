import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from garmin_recovery import improvement, mdhtml

TODAY = "2026-10-18"


def trend(hrv_recent, hrv_prior, n=28):
    out = []
    for i in range(n):
        d = (date.fromisoformat(TODAY) - timedelta(days=n - 1 - i)).isoformat()
        hrv = hrv_recent if i >= n - 7 else hrv_prior
        out.append({"date": d, "hrv_ms": hrv, "resting_hr": 56, "sleep_hours": 7.5, "sleep_context": "night_sleep", "load": 0})
    return out


def result(tr, sessions=(), cov=100.0):
    return {"date": TODAY, "trend_28d": tr, "sessions_28d": list(sessions), "load": {"srpe_coverage_28d_pct": cov},
            "decision": {"guidance": {"label": "Prioriza recuperar", "rpe_max": 4}}}


def ws():
    r = Path(tempfile.mkdtemp())
    (r / "history").mkdir()
    (r / "history" / "daily.csv").write_text("date,sleep_context,sleep_start_local,shift,soreness,fatigue,stress_subjective,mood,motivation\n", encoding="utf-8")
    return r


class Improvement(unittest.TestCase):
    def find(self, res, key):
        return next(f for f in improvement.analyze(ws(), res)["findings"] if f["key"] == key)

    def test_hrv_drop_is_priority(self):
        f = self.find(result(trend(50, 60)), "hrv")
        self.assertEqual(f["severity"], 3)
        self.assertIn("-17 %", f["observed"])

    def test_hrv_stable_and_insufficient(self):
        self.assertEqual(self.find(result(trend(60, 60)), "hrv")["severity"], 0)
        self.assertIn("insuficientes", self.find(result(trend(None, None)), "hrv")["observed"])

    def test_intensity_flags_consecutive_hard_days(self):
        ss = [{"date": (date.fromisoformat(TODAY) - timedelta(days=k)).isoformat(), "rpe": 9, "removed": 0, "srpe": 100} for k in range(1, 7)]
        f = self.find(result(trend(60, 60), ss), "intensity")
        self.assertEqual(f["severity"], 2)

    def test_logging_gap_flagged_and_not_invented(self):
        a = improvement.analyze(ws(), result(trend(60, 60)))
        self.assertTrue(any(f["key"] == "logging" for f in a["findings"]))
        md = improvement.to_markdown(a)
        self.assertIn("## 8.", md)
        self.assertNotIn("None", md)
        self.assertNotIn("nan", md.lower().replace("financiero", ""))

    def test_empty_inputs_do_not_crash(self):
        md = improvement.run(ws(), {"date": TODAY})
        self.assertIn("## 8.", md)


class Render(unittest.TestCase):
    def test_images_only_from_charts_and_cards(self):
        h = mdhtml.render("```cards\nHRV|46 ms|-8 %|red\n```\n\n![g](charts/hrv.svg)\n\n![x](http://evil/x.svg)")
        self.assertIn('class="kpi red"', h)
        self.assertIn('<img src="charts/hrv.svg"', h)
        self.assertNotIn("evil/x.svg\"", h)


if __name__ == "__main__":
    unittest.main()
