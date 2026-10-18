import unittest

from garmin_recovery import strength_patterns as sp


def row(d, pat="squat", sets=4, vol=400.0, eq="barbell", unit="kg_total_barra", complete=True, aid="a1", ex="x", **k):
    r = {"date": d, "activity_id": aid, "exercise": ex, "equipment": eq, "load_unit": unit, "movement_pattern": pat,
         "known_sets": sets, "verified_volume_kg": vol, "volume_complete": complete}
    r.update(k)
    return r


class Patterns(unittest.TestCase):
    def test_windows_dedup_and_volume(self):
        rows = [row("2026-10-17"), row("2026-10-17"), row("2026-10-01", aid="a2", ex="y", sets=3, vol=300.0)]
        r = sp.compute(rows, "2026-10-18")
        self.assertEqual(r["7d"]["squat"]["blocks"], 1)
        self.assertEqual((r["28d"]["squat"]["blocks"], r["28d"]["squat"]["sets"], r["28d"]["squat"]["bar_kg"]), (2, 7, 700.0))

    def test_incomplete_or_other_equipment_not_summed(self):
        rows = [row("2026-10-17", complete=False), row("2026-10-17", ex="m", eq="machine", unit="kg", vol=900.0),
                row("2026-10-16", ex="n", laterality_unconfirmed=True)]
        p = sp.compute(rows, "2026-10-18")["7d"]["squat"]
        self.assertEqual(p["bar_kg"], 0.0)
        self.assertTrue(p["bar_partial"])
        self.assertIn("(parcial)", sp.to_markdown(sp.compute(rows, "2026-10-18")))

    def test_unknown_sets_and_empty(self):
        r = sp.compute([row("2026-10-17", sets=None)], "2026-10-18")
        self.assertEqual(r["7d"]["squat"]["sets_unknown"], 1)
        self.assertIn("+", sp.to_markdown(r))
        self.assertIn("No hay series", sp.to_markdown(sp.compute([], "2026-10-18")))
        self.assertEqual(sp.compute(None, "2026-10-18"), {"7d": {}, "28d": {}})


if __name__ == "__main__":
    unittest.main()
