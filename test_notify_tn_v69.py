import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import notify

TZ = ZoneInfo("Europe/Madrid")


def ws(shift="TN", hours=(7.5,) * 6, last=7.8, ext=None):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "app").mkdir()
    trend = [{"date": f"2026-10-{12 + i:02d}", "sleep_hours": h, "sleep_context": "night_sleep", "srpe": None} for i, h in enumerate(hours)]
    trend.append({"date": "2026-10-18", "sleep_hours": last, "sleep_context": "night_sleep", "shift": shift, "srpe": None})
    (tmp / "app" / "readiness_v3.json").write_text(json.dumps({
        "generated_at": "2026-10-18T08:55:00+02:00", "date": "2026-10-18", "trend_28d": trend,
        "decision": {"zone": "green", "guidance": {"label": "Plan normal", "rpe_max": 9}}}))
    if ext is not None:
        (tmp / "garmin_extended.json").write_text(json.dumps({"days": ext}))
    return tmp


def msg(root, hour=9):
    return notify.build_message(root, datetime(2026, 10, 18, hour, 0, tzinfo=TZ), max_age_min=600)["message"]


class TnTip(unittest.TestCase):
    def test_no_tip_without_tn_or_after_start(self):
        self.assertNotIn("TN", msg(ws(shift="MT")))
        self.assertNotIn("TN", msg(ws(), hour=15))

    def test_short_night_suggests_nap(self):
        m = msg(ws(last=5.0))
        self.assertIn("siesta de 20–90 min", m)

    def test_debt_suggests_nap(self):
        self.assertIn("siesta", msg(ws(hours=(6.0,) * 6, last=7.0)))

    def test_rested_gets_light_tip_and_no_numbers(self):
        m = msg(ws())
        self.assertIn("Hoy TN", m)
        self.assertNotIn("siesta de 20", m)
        self.assertNotIn("7,5", m)
        self.assertNotIn("h de sueño", m)

    def test_tip_failure_does_not_break_message(self):
        root = ws()
        (root / "garmin_extended.json").write_text("{roto")
        self.assertIn("Plan normal", msg(root))


if __name__ == "__main__":
    unittest.main()


class RpePending(unittest.TestCase):
    def res(self, sessions):
        return {"date": "2026-10-18", "sessions_28d": sessions}

    def test_today_pending_after_noon(self):
        s = [{"date": "2026-10-18", "rpe": None}, {"date": "2026-10-18", "rpe": 7.5}, {"date": "2026-10-17", "rpe": None}]
        tip = notify.rpe_pending_tip(self.res(s), datetime(2026, 10, 18, 17, 10, tzinfo=TZ))
        self.assertEqual(tip, "1 sesión de hoy sin RPE: cuéntamelo antes del cierre de las 22:45.")

    def test_yesterday_pending_in_the_morning_and_plural(self):
        s = [{"date": "2026-10-17", "rpe": None}, {"date": "2026-10-17", "rpe": None}, {"date": "2026-10-18", "rpe": None}]
        tip = notify.rpe_pending_tip(self.res(s), datetime(2026, 10, 18, 9, 0, tzinfo=TZ))
        self.assertTrue(tip.startswith("2 sesiones de ayer sin RPE"))

    def test_none_when_all_logged_or_removed(self):
        s = [{"date": "2026-10-18", "rpe": 6.0}, {"date": "2026-10-18", "rpe": None, "removed": 1}]
        self.assertIsNone(notify.rpe_pending_tip(self.res(s), datetime(2026, 10, 18, 17, 10, tzinfo=TZ)))

    def test_appended_to_message(self):
        root = ws()
        data = json.loads((root / "app" / "readiness_v3.json").read_text())
        data["sessions_28d"] = [{"date": "2026-10-18", "rpe": None}]
        (root / "app" / "readiness_v3.json").write_text(json.dumps(data))
        self.assertIn("sin RPE", msg(root, hour=17))
