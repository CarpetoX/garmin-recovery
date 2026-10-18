"""Margen de tren inferior tras ejercicios de piernas muy duros y su efecto en el plan semanal."""
import unittest

from garmin_recovery import muscle_recovery as mr
from garmin_recovery import week_plan


def cf(rpe, name="sentadilla trasera", date="2026-10-18", pattern="squat"):
    return {"muscle_load": {"strength_exercises": [{"exercise": name, "movement_pattern": pattern}]},
            "activities": [{"date": date, "manual_blocks": [{"detail_json": {"exercises": [
                {"name": name, "rpe": rpe}, {"name": "press banca", "rpe": 9.5}]}}]}]}


class Compute(unittest.TestCase):
    def test_very_hard_squat_blocks_48h(self):
        r = mr.compute(cf(9.5), "2026-10-18")["legs"]
        self.assertEqual((r["until"], r["hours"], r["rpe"]), ("2026-10-20", 48, 9.5))
        self.assertIsNone(mr.compute(cf(9.5), "2026-10-20")["legs"])  # pasado el margen

    def test_hard_gives_24h_and_moderate_gives_none(self):
        self.assertEqual(mr.compute(cf(8), "2026-10-18")["legs"]["until"], "2026-10-19")
        self.assertIsNone(mr.compute(cf(7), "2026-10-18")["legs"])

    def test_upper_body_never_blocks_legs(self):
        data = cf(9.5)  # el press banca (RPE 9,5) no consta como patrón de piernas
        self.assertEqual(mr.compute(data, "2026-10-18")["legs"]["exercise"], "sentadilla trasera")
        self.assertIsNone(mr.compute(cf(9.5, "press de pecho", pattern="horizontal_push"), "2026-10-18")["legs"])

    def test_robust_to_missing_data(self):
        for bad in (None, {}, {"activities": [None, {"date": "x"}]}):
            self.assertIsNone(mr.compute(bad, "2026-10-18")["legs"])

    def test_note_text(self):
        txt = mr.note(mr.compute(cf(9.5), "2026-10-18")["legs"])
        self.assertIn("RPE 9,5", txt)
        self.assertIn("hasta el 20/10", txt)
        self.assertIn("sin validar", txt)
        self.assertIsNone(mr.note(None))


class Plan(unittest.TestCase):
    SHIFTS = {f"2026-10-{d}": {"shift": "free"} for d in range(18, 26)}

    def test_free_days_inside_margin_are_not_hard(self):
        legs = {"until": "2026-10-20", "date": "2026-10-18", "exercise": "sentadilla trasera", "rpe": 9.5, "hours": 48}
        without = week_plan.plan("2026-10-19", self.SHIFTS, [], "green", 9)
        withl = week_plan.plan("2026-10-19", self.SHIFTS, [], "green", 9, legs)
        self.assertEqual(without[0]["kind"], "hard")
        self.assertEqual(withl[0]["kind"], "moderate")
        self.assertIn("sin piernas pesadas hasta el 20/10", withl[0]["why"])
        self.assertEqual(withl[1]["kind"], "hard")  # el 20/10 ya vale
        self.assertNotIn("piernas pesadas hasta", withl[1]["why"])


if __name__ == "__main__":
    unittest.main()
