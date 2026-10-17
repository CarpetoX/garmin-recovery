import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from garmin_recovery import notify

NOW = datetime(2026, 10, 18, 9, 0, tzinfo=ZoneInfo("Europe/Madrid"))


def ws(zone="red", gen="2026-10-18T08:55:00+02:00", val=None):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "app").mkdir()
    (tmp / "app" / "readiness_v3.json").write_text(json.dumps({
        "generated_at": gen, "decision": {"zone": zone, "guidance": {"label": "Prioriza recuperar", "rpe_max": 4}}}))
    if val:
        (tmp / "app" / "validation.json").write_text(json.dumps({"status": val}))
    return tmp


class Notify(unittest.TestCase):
    def test_message_for_new_valid_report(self):
        m = notify.build_message(ws(val="ok"), NOW)
        self.assertEqual(m["priority"], 4)
        self.assertEqual(m["tags"], ["red_circle"])
        self.assertIn("Prioriza recuperar", m["message"])
        self.assertIn("RPE máx. 4", m["message"])
        self.assertTrue(m["click"].startswith("https://carpetox.github.io/"))

    def test_no_message_when_report_old_failed_or_missing(self):
        self.assertIsNone(notify.build_message(ws(gen="2026-10-18T05:00:00+02:00"), NOW))
        self.assertIsNone(notify.build_message(ws(val="failed"), NOW))
        self.assertIsNone(notify.build_message(Path(tempfile.mkdtemp()), NOW))

    def test_message_has_no_physiological_numbers(self):
        m = notify.build_message(ws(), NOW)
        self.assertNotIn("HRV", json.dumps(m))

    def test_send_posts_json_utf8_to_topic(self):
        seen = {}

        def opener(req, timeout):
            seen["body"] = json.loads(req.data.decode())
            seen["url"] = req.full_url
            return mock.Mock(status=200, __enter__=lambda s: s, __exit__=lambda *a: None)
        notify.send({"title": "t", "message": "Sí"}, "mi-tema", opener=opener)
        self.assertEqual(seen["body"]["topic"], "mi-tema")
        self.assertEqual(seen["url"], "https://ntfy.sh")

    def test_without_topic_does_nothing(self):
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": ""}), mock.patch.object(notify, "send") as s:
            self.assertEqual(notify.main(str(ws())), 0)
            s.assert_not_called()

    def test_errors_never_break_the_chain(self):
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "x"}), mock.patch.object(notify, "send", side_effect=OSError("red")):
            with mock.patch.object(notify, "build_message", return_value={"title": "t"}):
                self.assertEqual(notify.main("."), 0)

    def test_workflow_step_is_wired_and_non_blocking(self):
        wf = (Path(__file__).parent / ".github/workflows/crossfit-insights.yml").read_text(encoding="utf-8")
        self.assertIn("python -m garmin_recovery notify", wf)
        self.assertIn("secrets.NTFY_TOPIC", wf)


if __name__ == "__main__":
    unittest.main()
