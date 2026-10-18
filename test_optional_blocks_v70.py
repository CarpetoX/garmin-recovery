"""Los bloques opcionales que fallan ya no desaparecen en silencio."""
import contextlib
import io
import unittest

from garmin_recovery import optional_blocks as ob


class Blocks(unittest.TestCase):
    def setUp(self):
        ob.reset()

    def test_failure_is_recorded_annotated_and_reported(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            ob.failed("sleep_need", KeyError("x"))
            ob.failed("sleep_need", ValueError("y"))
            ob.failed("web:plan", OSError("z"))
        self.assertIn("::warning title=", err.getvalue())
        self.assertEqual(len(ob.failures()), 3)
        md = ob.to_markdown()
        self.assertIn("sleep_need, web:plan", md)  # sin repetir nombres
        ob.reset()
        self.assertEqual(ob.to_markdown(), "")

    def test_report_mentions_failed_block(self):
        import json
        from pathlib import Path
        from unittest import mock

        from garmin_recovery import fullreport, why_changed
        root = Path(__file__).resolve().parent
        result = json.loads((root / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        with mock.patch.object(why_changed, "compute", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stderr(io.StringIO()):
            text = fullreport.build_full_report(root, result)
        self.assertIn("Bloques opcionales no disponibles en este ciclo: why_changed", text)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertNotIn("Bloques opcionales no disponibles", fullreport.build_full_report(root, result))


if __name__ == "__main__":
    unittest.main()
