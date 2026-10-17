"""V6.1: avisos de Garmin/Intervals desconectados y fuentes de reserva visibles."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery.alerts import problems, source_problems
from garmin_recovery.report import fallback_notes

NOW = datetime(2026, 10, 18, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))


def ws(garmin=None, wellness_last=None):
    tmp = Path(tempfile.mkdtemp())
    if garmin is not None:
        (tmp / "garmin_status.json").write_text(json.dumps(garmin))
    if wellness_last is not None:
        (tmp / "wellness.json").write_text(json.dumps([{"id": "2026-10-01", "hrv": 60}, {"id": wellness_last, "hrv": 60}]))
    return tmp


class Sources(unittest.TestCase):
    def test_all_fresh(self):
        self.assertEqual(source_problems(ws({"status": "success", "latest_heart_rate_date": "2026-10-18"}, "2026-10-18"), NOW), [])
        self.assertEqual(source_problems(ws({"status": "success", "latest_heart_rate_date": "2026-10-17"}, "2026-10-17"), NOW), [])

    def test_garmin_token_error(self):
        p = source_problems(ws({"status": "error", "error": "RuntimeError: GARMIN_TOKENS_B64 no está disponible",
                                "latest_heart_rate_date": "2026-10-15"}, "2026-10-18"), NOW)
        self.assertEqual([x["key"] for x in p], ["garmin"])
        self.assertIn("GARMIN_TOKENS_B64", p[0]["text"])

    def test_garmin_stale_without_error(self):
        p = source_problems(ws({"status": "success", "latest_heart_rate_date": "2026-10-15"}, "2026-10-18"), NOW)
        self.assertEqual([x["key"] for x in p], ["garmin"])
        self.assertNotIn("renueva", p[0]["text"])

    def test_intervals_stale(self):
        p = source_problems(ws(None, "2026-10-14"), NOW)
        self.assertEqual([x["key"] for x in p], ["intervals"])
        self.assertIn("INTERVALS_API_KEY", p[0]["text"])

    def test_intervals_rows_with_only_load_do_not_count(self):
        root = ws(None, "2026-10-14")
        (root / "wellness.json").write_text(json.dumps([{"id": "2026-10-14", "hrv": 60}, {"id": "2026-10-18", "ctl": 40, "atl": 50}]))
        self.assertEqual([x["key"] for x in source_problems(root, NOW)], ["intervals"])

    def test_isolated_garmin_error_with_fresh_data_is_not_an_alert(self):
        root = ws({"status": "error", "error": "429", "latest_heart_rate_date": None}, "2026-10-18")
        self.assertEqual(source_problems(root, NOW), [])
        root = ws({"status": "error", "error": "429", "latest_heart_rate_date": "2026-10-17"}, "2026-10-18")
        self.assertEqual(source_problems(root, NOW), [])

    def test_watchdog_scope_reports_sources(self):
        root = ws({"status": "error", "error": "401", "latest_heart_rate_date": "2026-10-10"}, "2026-10-18")
        (root / "app").mkdir()
        (root / "app" / "readiness_v3.json").write_text(json.dumps({"generated_at": NOW.isoformat()}))
        self.assertIn("garmin", [x["key"] for x in problems(root, NOW, "watchdog")])


class Fallback(unittest.TestCase):
    def test_note_when_intervals_used(self):
        notes = fallback_notes({"today_sources": {"hrv_ms": "intervals_icu", "sleep_hours": "garmin_sleep_history"}})
        self.assertEqual(len(notes), 1)
        self.assertIn("HRV", notes[0])
        self.assertNotIn("sueño", notes[0])
        self.assertEqual(fallback_notes({"today_sources": {"hrv_ms": "garmin_hrv_timeline"}}), [])


if __name__ == "__main__":
    unittest.main()
