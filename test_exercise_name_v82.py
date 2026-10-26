"""V8.2: un registro de un solo ejercicio se nombra por su campo «exercise», no por el título de la sesión."""
import unittest

from garmin_recovery.muscle_load import analyze


class SingleExerciseName(unittest.TestCase):
    def test_uses_exercise_field(self):
        acts = [{"date": "2026-10-13", "activity_id": "i1", "manual_blocks": [{
            "activity": "Fuerza - Squat snatch",
            "detail_json": {"type": "strength", "exercise": "squat snatch", "load_unit": "kg_total_barra",
                            "sets": [{"reps": 1, "load_kg": 68}]}}]},
                {"date": "2026-10-26", "activity_id": "i2", "manual_blocks": [{
                    "activity": "Fuerza - Squat snatch",
                    "detail_json": {"type": "strength", "exercises": [{"name": "squat snatch", "load_unit": "kg_total_barra",
                                                                       "sets": [{"reps": 1, "load_kg": 75}]}]}}]}]
        out = analyze(acts, "2026-10-26")
        names = {r["exercise"] for r in out["strength_exercises"]}
        self.assertEqual(names, {"squat snatch"})


if __name__ == "__main__":
    unittest.main()
