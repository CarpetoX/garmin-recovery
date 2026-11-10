"""V8.5: correcciones de la auditoría de la app (cifras y textos que confundían)."""
import json
import unittest
from pathlib import Path

from garmin_recovery.dashboard import _plan_html, render
from garmin_recovery.glance import _n
from garmin_recovery.records import build_sessions

ROOT = Path(__file__).resolve().parent


class Audit(unittest.TestCase):
    def test_minutes_not_truncated(self):
        self.assertEqual((_n(69.8, 0), _n(70, 0), _n(7.5), _n(8.0)), ("70", "70", "7,5", "8"))

    def test_unscored_session_keeps_sheet_name(self):
        fb = {"activities": {}, "source_rows_AH": [{"ID actividad": "i9", "Actividad": "Técnica - toes to bar", "RPE": "",
                                                    "Notas": "", "Detalle JSON": '{"type": "skill"}'}]}
        s = build_sessions({"activities": [{"id": "i9", "start_date_local": "2026-10-26T10:26:00", "moving_time": 2826}],
                            "feedback": fb})[0]
        self.assertEqual(s["label"], "Técnica - toes to bar")
        self.assertTrue(s["rpe_na"])

    def test_plan_shift_in_spanish(self):
        html = _plan_html([{"kind": "light", "dow": "lun", "date": "2026-10-26", "shift": "free", "why": "x"},
                           {"kind": "rest", "dow": "vie", "date": "2026-10-30", "shift": "post-TN", "why": "y"}])
        self.assertIn(">libre<", html)
        self.assertIn(">tras TN<", html)
        self.assertNotIn(">free<", html)

    def test_page_keeps_chart_readings_visible_and_shows_today(self):
        page = render(json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8")), {})
        fold = page[page.index("const CARD_FOLD"):page.index(";", page.index("const CARD_FOLD"))]
        self.assertNotIn(".read", fold)
        self.assertIn("rolling: 'hrv_rolling_ms'", page)
        self.assertIn("Hoy llevas", page)
        self.assertIn("Ya has hecho una sesión dura hoy", page)


if __name__ == "__main__":
    unittest.main()
