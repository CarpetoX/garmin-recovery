import json
import tempfile
import unittest
from pathlib import Path

from garmin_recovery import ai_analysis as ai


def ws(analysis=None, current="2026-10-18-0830"):
    r = Path(tempfile.mkdtemp())
    (r / "app").mkdir()
    (r / "report_ready.json").write_text(json.dumps({"cycle_id": current}))
    (r / "app" / "informe_completo.md").write_text("HRV 46 ms, 45/100, 7 h 50 min, RPE máx. 4, 68,1 lpm")
    if analysis is not None:
        (r / "app" / "analisis_ia.md").write_text(analysis)
    return r


class Analysis(unittest.TestCase):
    def test_absent(self):
        self.assertEqual(ai.check(ws())["state"], "absent")
        self.assertEqual(ai.section(ws()), "")

    def test_ok_and_numbers(self):
        r = ai.check(ws("<!-- cycle_id: 2026-10-18-0830 -->\nHRV 46 ms y 45/100, RPE máx. 4, FC 68,1."))
        self.assertEqual((r["state"], r["unverified"]), ("ok", []))

    def test_unverified_number_flagged(self):
        r = ai.check(ws("<!-- cycle_id: 2026-10-18-0830 -->\nHRV 99 ms"))
        self.assertEqual(r["unverified"], ["99"])
        self.assertIn("99", ai.section(ws("<!-- cycle_id: 2026-10-18-0830 -->\nHRV 99 ms")))

    def test_stale_and_invalid(self):
        self.assertEqual(ai.check(ws("<!-- cycle_id: 2026-10-17-2245 -->\ntexto"))["state"], "stale")
        self.assertIn("ciclo vigente", ai.section(ws("<!-- cycle_id: 2026-10-17-2245 -->\ntexto")))
        self.assertEqual(ai.check(ws("sin marca"))["state"], "invalid")
        self.assertEqual(ai.check(ws("<!-- cycle_id: 2026-10-18-0830 -->\n"))["state"], "invalid")


if __name__ == "__main__":
    unittest.main()
