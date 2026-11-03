"""V8.10: «Cambios recientes» compara sueño con sueño del mismo tipo (tras un TN, con el último sueño tras TN)."""
import unittest

from garmin_recovery import why_changed


def row(d, ctx="night_sleep", hrv=50, rhr=55, sleep=7.5, v2=80):
    return {"date": d, "sleep_context": ctx, "hrv_ms": hrv, "resting_hr": rhr, "sleep_hours": sleep, "v2_score": v2, "score": v2}


class LikeForLike(unittest.TestCase):
    def test_day_sleep_compares_with_last_day_sleep(self):
        t = [row("2026-10-30", "day_sleep", 34, 54, 4.18, 19), row("2026-11-01"), row("2026-11-02", hrv=49, rhr=57),
             row("2026-11-03", "day_sleep", 40, 61, 5.15, 31)]
        c = why_changed.compute(t, "2026-11-03")
        self.assertTrue(c["available"])
        self.assertEqual((c["prev_date"], c["basis"]), ("2026-10-30", "day_sleep"))
        self.assertIn("30/10", c["compare_label"])
        self.assertEqual((c["official_from"], c["official_to"]), (19, 31))
        hrv = next(i for i in c["items"] if i["label"] == "HRV")
        self.assertEqual((hrv["from"], hrv["to"], hrv["favorable"]), (34, 40, True))
        self.assertIn("frente a tu último sueño tras turno de noche (30/10)", why_changed.heading(c))
        self.assertIn("dormiste de día", why_changed.to_markdown(c))

    def test_night_after_day_sleep_compares_with_last_night(self):
        t = [row("2026-11-02", hrv=49), row("2026-11-03", "day_sleep", 40), row("2026-11-04", hrv=58)]
        c = why_changed.compute(t, "2026-11-04")
        self.assertEqual((c["prev_date"], c["basis"]), ("2026-11-02", "last_night"))
        self.assertIn("02/11", c["compare_label"])

    def test_normal_night_is_still_yesterday(self):
        c = why_changed.compute([row("2026-11-01"), row("2026-11-02", hrv=44)], "2026-11-02")
        self.assertEqual((c["basis"], c["compare_label"]), ("yesterday", "ayer"))
        self.assertEqual(why_changed.heading(c), "Qué ha cambiado desde ayer")

    def test_no_comparable_sleep_explains_why(self):
        c = why_changed.compute([row("2026-11-02"), row("2026-11-03", "day_sleep")], "2026-11-03")
        self.assertFalse(c["available"])
        self.assertIn("dormiste de día", c["reason"])

    def test_card_shows_the_note(self):
        from garmin_recovery.dashboard import _changes_html
        t = [row("2026-10-30", "day_sleep", 34, 54, 4.18, 19), row("2026-11-03", "day_sleep", 40, 61, 5.15, 31)]
        c = why_changed.compute(t, "2026-11-03")
        html = _changes_html(c, (19, 31), t)
        self.assertIn("chg-note", html)
        self.assertIn("frente a tu último sueño tras turno de noche (30/10)", html)
        self.assertIn("chg-card", html)


if __name__ == "__main__":
    unittest.main()
