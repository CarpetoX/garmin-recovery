import unittest

from garmin_recovery import week_plan as w


def shifts(start_day, labels, post=()):
    out = {}
    for i, lab in enumerate(labels):
        d = f"2026-10-{start_day + i:02d}"
        out[d] = {"shift": lab, "post_tn": d in post}
    return out


FREE7 = shifts(18, ["free"] * 8)


def kinds(rows):
    return [r["kind"] for r in rows]


class Plan(unittest.TestCase):
    def test_trained_today_and_restricted(self):
        sess = [{"date": "2026-10-18", "rpe": 5}]
        self.assertEqual(w.plan("2026-10-18", FREE7, sess, "green", 9)[0]["kind"], "light")
        self.assertEqual(w.plan("2026-10-18", FREE7, [], "red", 9)[0]["kind"], "light")
        self.assertEqual(w.plan("2026-10-18", FREE7, [], "green", 6)[0]["kind"], "light")
        self.assertEqual(w.plan("2026-10-18", FREE7, [], "green", 9)[0]["kind"], "hard")

    def test_hard_spacing_and_weekly_cap(self):
        k = kinds(w.plan("2026-10-18", FREE7, [], "green", 9))
        self.assertEqual(k[:3], ["hard", "moderate", "hard"])
        self.assertLessEqual(k.count("hard"), 3)
        sess = [{"date": f"2026-10-{d}", "rpe": 9} for d in (13, 15, 17)]
        r = w.plan("2026-10-18", FREE7, sess, "green", 9)
        self.assertEqual(r[0]["kind"], "moderate")      # hace 1 día hubo una dura
        self.assertIn("3 sesiones duras", r[1]["why"])  # cupo de la ventana móvil

    def test_shifts_limit_intensity(self):
        sh = shifts(18, ["free", "TN", "free", "MT", "unknown", "free", "free", "free"], post={"2026-10-20"})
        r = w.plan("2026-10-18", sh, [], "green", 9)
        by = {x["date"][8:]: x for x in r}
        self.assertEqual(by["19"]["kind"], "moderate")   # TN
        self.assertEqual(by["20"]["kind"], "rest")       # post-TN
        self.assertEqual(by["20"]["shift"], "post-TN")
        self.assertEqual(by["21"]["kind"], "light")      # MT
        self.assertEqual(by["22"]["kind"], "moderate")   # turno sin confirmar
        self.assertIn("mañana TN", w.plan("2026-10-18", shifts(18, ["free", "TN"] + ["free"] * 6), [], "green", 9)[0]["why"])

    def test_missing_shift_info_and_markdown(self):
        r = w.plan("2026-10-18", {}, [], "green", 9)
        self.assertTrue(all(x["kind"] == "moderate" for x in r) or r[0]["kind"] == "moderate")
        md = w.to_markdown(r)
        self.assertIn("| dom 18/10 |", md)
        self.assertIn("recalcula en cada informe", md)


if __name__ == "__main__":
    unittest.main()
