"""V8.4: las cadenas repetidas sin cambios no lanzan monitor, web ni rutina; ante la duda se publica."""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_recovery import publish_gate as pg

NOW = datetime(2026, 10, 26, 10, 0, tzinfo=timezone.utc)


def setup(root: Path, score=66, sleep="post_night_shift_sleep_pending", verified=NOW - timedelta(hours=3)):
    (root / "app").mkdir(exist_ok=True)
    (root / "app" / "readiness_v3.json").write_text(json.dumps({
        "date": "2026-10-26", "readiness": {"state": "assessed", "score": score}, "decision": {"zone": "yellow"},
        "sessions_28d": [{"id": "i1", "date": "2026-10-26", "rpe": 7}, {"id": "i0", "date": "2026-10-20", "rpe": 8}]}))
    (root / "morning_sleep_status.json").write_text(json.dumps({"state": sleep, "is_definitive": False}))
    (root / "report_ready.json").write_text(json.dumps({"cycle_id": "2026-10-26-0830", "verified_at": verified.isoformat()}))


class Gate(unittest.TestCase):
    def test_first_publish_then_skip_then_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            setup(root)
            first = pg.decide(root, NOW)
            self.assertTrue(first["publish"])
            (root / pg.STATE).write_text(json.dumps(first))
            again = pg.decide(root, NOW + timedelta(minutes=65))
            self.assertFalse(again["publish"])
            self.assertEqual(again["reason"], "sin cambios desde la última publicación")
            self.assertEqual(again["published_digest"], first["digest"])
            (root / pg.STATE).write_text(json.dumps(again))
            setup(root, sleep="confirmed_ready")
            self.assertTrue(pg.decide(root, NOW + timedelta(minutes=130))["publish"])

    def test_new_certificate_always_publishes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            setup(root)
            (root / pg.STATE).write_text(json.dumps(pg.decide(root, NOW)))
            setup(root, verified=NOW + timedelta(minutes=60))
            out = pg.decide(root, NOW + timedelta(minutes=65))
            self.assertTrue(out["publish"])
            self.assertEqual(out["reason"], "certificado nuevo")

    def test_old_sessions_do_not_count_and_main_fails_open(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            setup(root)
            self.assertEqual([s[0] for s in pg.fingerprint(root)["sessions"]], ["i1"])
            (root / "app" / "readiness_v3.json").write_text("{roto")
            out_file = root / "out.txt"
            os.environ["GITHUB_OUTPUT"] = str(out_file)
            try:
                pg.main(root)
            finally:
                del os.environ["GITHUB_OUTPUT"]
            self.assertIn("publish=true", out_file.read_text())


class Workflow(unittest.TestCase):
    def test_dispatch_and_routine_are_gated(self):
        wf = (Path(__file__).resolve().parent / ".github" / "workflows" / "crossfit-insights.yml").read_text(encoding="utf-8")
        self.assertLess(wf.index("python -m garmin_recovery.publish_gate"), wf.index("- name: Commit CrossFit insights"))
        self.assertIn("git add publish_gate.json", wf)
        self.assertEqual(wf.count("steps.gate.outputs.publish != 'false'"), 2)


if __name__ == "__main__":
    unittest.main()
