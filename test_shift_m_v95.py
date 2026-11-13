"""V9.5: turno M (08–15) y calendario de diciembre y enero."""
import unittest

from garmin_recovery import panel_v9, shift_calendar


class ShiftMTests(unittest.TestCase):
    def test_m_shift_resolves_with_hours(self):
        r = shift_calendar.resolve_day("2026-12-25")
        self.assertEqual((r["shift"], r["start"], r["end"]), ("M", "08:00", "15:00"))
        self.assertEqual(panel_v9.context_of("2026-12-25", shift_calendar.load_calendar()), "M")

    def test_december_and_january_loaded(self):
        self.assertEqual(shift_calendar.resolve_day("2026-12-27")["shift"], "TN")
        self.assertEqual(shift_calendar.resolve_day("2026-12-28")["label"], "post-TN")
        self.assertEqual(shift_calendar.resolve_day("2026-12-30")["label"], "free")
        self.assertEqual(shift_calendar.resolve_day("2027-01-31")["shift"], "TN")


if __name__ == "__main__":
    unittest.main()
