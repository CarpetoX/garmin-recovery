import unittest

from garmin_recovery import strength_progress as sp


def row(d, ex="sentadilla trasera", kg=100.0, reps=5, e1=116.7, aid="a", unit="kg_total_barra", eq="barbell"):
    return {"date": d, "exercise": ex, "top_set_kg": kg, "top_set_reps": reps, "e1rm_min_kg": e1, "activity_id": aid,
            "load_unit": unit, "equipment": eq}


class Progress(unittest.TestCase):
    def test_weekly_best_and_dedup(self):
        rows = [row("2026-10-12", kg=100, e1=116.7), row("2026-10-12", kg=100, e1=116.7),
                row("2026-10-14", kg=110, reps=3, e1=121.0, aid="b"), row("2026-10-05", kg=90, e1=105.0, aid="c")]
        r = sp.compute(rows, "2026-10-18")["sentadilla trasera"]
        self.assertEqual([x["week"] for x in r], ["2026-S41", "2026-S42"])
        self.assertEqual((r[1]["best_kg"], r[1]["best_reps"], r[1]["e1rm"], r[1]["sessions"]), (110, 3, 121.0, 2))

    def test_only_barbell_total_load(self):
        rows = [row("2026-10-12", unit="kg_indicado_maquina"), row("2026-10-12", ex="prensa", eq="machine"),
                row("2026-10-12", kg=None)]
        self.assertEqual(sp.compute(rows, "2026-10-18"), {})
        self.assertIn("No hay series", sp.to_markdown({}))
        self.assertEqual(sp.compute(None, "2026-10-18"), {})

    def test_window_and_difference_text(self):
        rows = [row("2026-10-05", e1=100.0, aid="c"), row("2026-10-12", e1=110.0), row("2026-08-01", aid="old")]
        res = sp.compute(rows, "2026-10-18")
        self.assertEqual(len(res["sentadilla trasera"]), 2)
        md = sp.to_markdown(res)
        self.assertIn("+10 kg entre 2026-S41 y 2026-S42", md)
        self.assertIn("límite inferior", md)


if __name__ == "__main__":
    unittest.main()
