"""El tonelaje verificado solo suma barra con carga total; máquinas y otras unidades no se mezclan."""
import unittest

from garmin_recovery import crossfit


class BarbellVolume(unittest.TestCase):
    DETAIL = {"exercises": [
        {"name": "sentadilla trasera", "load_unit": "kg_total_barra", "sets": [{"reps": 10, "load_kg": 20}, {"count": 2, "reps": 5, "load_kg": 100}]},
        {"name": "péndulo", "load_unit": "kg_indicado_maquina", "sets": [{"count": 4, "reps": 8, "load_kg": 60}]},
        {"name": "curl", "load_unit": "kg_total_dos_lados", "sets": [{"count": 8, "reps": 10, "load_kg": 42.5}]},
        {"name": "mancuernas", "load_unit": "kg_total_dos_mancuernas", "sets": [{"reps": 10, "load_kg": 30}]},
    ]}

    def test_only_barbell_counts(self):
        vol, complete, known, total = crossfit.sets_volume(self.DETAIL)
        self.assertEqual(vol, 10 * 20 + 2 * 5 * 100)  # 1.200 kg: sin los 1.920 de máquina ni el resto
        self.assertTrue(complete)
        self.assertEqual((known, total), (3, 3))

    def test_legacy_exercise_without_unit_is_kept(self):
        vol, _, _, _ = crossfit.sets_volume({"exercises": [{"sets": [{"reps": 5, "load_kg": 100}]}]})
        self.assertEqual(vol, 500)

    def test_only_machines_gives_no_volume(self):
        vol, complete, _, total = crossfit.sets_volume({"exercises": [self.DETAIL["exercises"][1]]})
        self.assertEqual((vol, complete, total), (None, False, 0))


if __name__ == "__main__":
    unittest.main()
