import json
import re
import unittest
from pathlib import Path

from garmin_recovery import mdhtml
from garmin_recovery.fullreport import build_full_report, n, hm

ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "app" / "readiness_v3.json"


@unittest.skipUnless(RESULT.exists(), "sin app/readiness_v3.json")
class FullReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.md = build_full_report(ROOT, cls.result, "GR-TEST")
        cls.ra = json.loads((ROOT / "recovery_assessment.json").read_text(encoding="utf-8"))

    def test_structure(self):
        for h in ("## Resumen ejecutivo", "## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7.", "## Conclusión"):
            self.assertIn(h, self.md)
        self.assertIn("GR-TEST", self.md)
        for bad in ("None", "NaN", "nan", "{", "}"):
            self.assertNotIn(bad, self.md.replace("```", ""))

    def test_figures_come_from_data(self):
        cur, dec = self.ra["current"], self.result["decision"]
        self.assertIn(n(cur["hrv_ms"]) + " ms", self.md)
        self.assertIn(n(cur["resting_hr"]) + " lpm", self.md)
        self.assertIn(hm(cur["sleep_hours"] * 60), self.md)
        self.assertIn(dec["guidance"]["label"], self.md)
        self.assertIn(f"RPE máx. {n(dec['guidance']['rpe_max'])}", self.md)

    def test_no_invented_sleep_phases(self):
        self.assertNotIn("ligero", self.md.lower())
        self.assertNotIn("Vigilia", self.md)

    def test_deterministic(self):
        self.assertEqual(self.md, build_full_report(ROOT, self.result, "GR-TEST"))

    def test_missing_data_does_not_crash(self):
        import tempfile
        md = build_full_report(tempfile.mkdtemp(), {"generated_at": "2026-10-17T22:48:00+02:00", "date": "2026-10-17"}, "GR-X")
        self.assertIn("## 7.", md)
        self.assertIn("—", md)


class Render(unittest.TestCase):
    def test_render_escapes_and_formats(self):
        h = mdhtml.render("# T\n\n| a | b |\n|---|---|\n| <x> | **y** |\n\n- uno\n- dos\n\n```\nbar █\n```")
        self.assertIn("<h1>T</h1>", h)
        self.assertIn("&lt;x&gt;", h)
        self.assertIn("<strong>y</strong>", h)
        self.assertEqual(h.count("<li>"), 2)
        self.assertIn("<pre>bar █</pre>", h)
        self.assertIsNone(re.search(r"<script", mdhtml.page("<script>alert(1)</script>")))


if __name__ == "__main__":
    unittest.main()
