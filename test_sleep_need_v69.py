import unittest

from garmin_recovery import sleep_need as sn


def trend(hours, srpe_last=None):
    rows = [{"date": f"2026-10-{10 + i:02d}", "sleep_hours": h, "sleep_context": "night_sleep", "srpe": None}
            for i, h in enumerate(hours)]
    if srpe_last:
        rows[-2]["srpe"] = srpe_last
    return rows


class SleepNeed(unittest.TestCase):
    def test_insufficient(self):
        self.assertFalse(sn.compute(trend([7, 7, 7]), {}, "2026-10-13")["available"])

    def test_debt_and_naps(self):
        t = trend([6.5, 6.5, 6.5, 6.5])
        no_nap = sn.compute(t, {}, "2026-10-13")
        self.assertEqual(no_nap["debt_7n_h"], 4.0)
        ext = {"2026-10-10": {"sleep_detail": {"nap_minutes": 60.0}}, "2026-10-11": 5}
        with_nap = sn.compute(t, ext, "2026-10-13")
        self.assertEqual(with_nap["debt_7n_h"], 3.0)

    def test_caps_and_today_nap(self):
        t = trend([4, 4, 4, 4, 4, 4, 4])
        r = sn.compute(t, {}, "2026-10-16")
        self.assertEqual(r["debt_add_h"], 1.0)
        self.assertLessEqual(r["need_tonight_h"], 7.5 + 0.5 + 1.0)
        r2 = sn.compute(t, {"2026-10-16": {"sleep_detail": {"nap_minutes": 60.0}}}, "2026-10-16")
        self.assertEqual(r2["need_tonight_h"], r["need_tonight_h"] - 1.0)

    def test_day_sleep_excluded_and_markdown(self):
        t = trend([7, 7, 7, 7, 7])
        t[2]["sleep_context"] = "day_sleep"
        r = sn.compute(t, {}, "2026-10-14")
        self.assertEqual(len(r["nights"]), 4)
        self.assertIn("heurística", sn.to_markdown(r))


if __name__ == "__main__":
    unittest.main()
