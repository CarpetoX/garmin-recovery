import unittest

from garmin_recovery import why_changed as w


def row(d, **k):
    base = {"date": d, "score": 50, "zone": "yellow", "state": "assessed", "sleep_context": "night_sleep"}
    base.update(k)
    return base


class Why(unittest.TestCase):
    def test_changes_and_direction(self):
        r = w.compute([row("2026-10-17", hrv_ms=46, resting_hr=60, sleep_score=62),
                       row("2026-10-18", hrv_ms=69, resting_hr=56, sleep_score=87, score=77, zone="green")], "2026-10-18")
        labels = {i["label"]: i["favorable"] for i in r["items"]}
        self.assertEqual(labels, {"HRV": True, "FC en reposo": True, "Puntuación de sueño": True})
        self.assertIn("favorable", w.to_markdown(r))

    def test_small_change_ignored_and_unfavorable(self):
        r = w.compute([row("2026-10-17", hrv_ms=60, stress_avg=20), row("2026-10-18", hrv_ms=61, stress_avg=40)], "2026-10-18")
        self.assertEqual([(i["label"], i["favorable"]) for i in r["items"]], [("Estrés medio", False)])

    def test_unavailable(self):
        self.assertFalse(w.compute([row("2026-10-18")], "2026-10-18")["available"])
        self.assertFalse(w.compute([row("2026-10-17", state="pending"), row("2026-10-18")], "2026-10-18")["available"])
        self.assertIn("sin datos", w.to_markdown({"available": False}))


if __name__ == "__main__":
    unittest.main()
