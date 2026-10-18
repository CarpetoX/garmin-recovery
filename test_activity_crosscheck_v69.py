import unittest

from garmin_recovery import activity_crosscheck as c


def ext(*items):
    days = {}
    for day, start, name in items:
        days.setdefault(day, {"activity_metrics": {"activities": []}})["activity_metrics"]["activities"].append(
            {"activity_id": 1, "start_time_local": start, "activity_name": name, "duration_minutes": 30.0})
    days["2026-10-17"] = days.get("2026-10-17", 5)  # entrada no-dict
    return days


class Cross(unittest.TestCase):
    def test_all_matched_with_tolerance(self):
        e = ext(("2026-10-18", "2026-10-18 10:00:00", "HIIT"))
        r = c.compute(e, [{"start_date_local": "2026-10-18T10:01:30"}], "2026-10-18")
        self.assertEqual(r["missing_in_intervals"], [])
        self.assertIn("constan también", c.to_markdown(r))

    def test_missing_listed(self):
        e = ext(("2026-10-18", "2026-10-18 10:00:00", "HIIT"), ("2026-10-16", "2026-10-16 09:00:00", "Fuerza"))
        r = c.compute(e, [{"start_date_local": "2026-10-16T09:00:00"}, "x"], "2026-10-18")
        self.assertEqual(len(r["missing_in_intervals"]), 1)
        md = c.to_markdown(r)
        self.assertIn("1 de 2", md)
        self.assertIn("18/10 10:00 · HIIT, 30 min", md)

    def test_window_and_empty(self):
        e = ext(("2026-10-01", "2026-10-01 09:00:00", "Viejo"))
        r = c.compute(e, [], "2026-10-18")
        self.assertEqual(r["garmin_count"], 0)
        self.assertIn("no aporta actividades", c.to_markdown(r))
        self.assertEqual(c.compute(None, None or [], "2026-10-18")["garmin_count"], 0)
        self.assertIsNone(c._dt("basura"))


if __name__ == "__main__":
    unittest.main()
