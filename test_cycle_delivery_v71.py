"""Estado final del ciclo: cadena + web + notificación (funciones puras y main con red simulada)."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from garmin_recovery import cycle_delivery as cd

NOW = datetime.fromisoformat("2026-10-18T17:20:00+02:00")
READY = {"cycle_id": "2026-10-18-1645", "verified_at": "2026-10-18T17:05:00+02:00", "chain": {
    "sync": {"conclusion": "success"}, "heart": {"conclusion": "success"}, "advanced": {"conclusion": "success"},
    "crossfit": {"id": 7, "started_at": "2026-10-18T17:05:00+02:00", "conclusion": "publishing_in_same_job"}}}
SENT = 'x\n{"notify": "enviado", "http": 200}\n'


class Pure(unittest.TestCase):
    def test_complete(self):
        r = cd.assess(READY, {"status": "completed", "conclusion": "success", "id": 9}, SENT, NOW)
        self.assertEqual(r["state"], "complete")
        self.assertEqual(set(r["stages"]), {"sync", "heart", "advanced", "crossfit", "web", "notification"})
        self.assertIn("no prueba", r["scope"])

    def test_notification_variants(self):
        ok = {"status": "completed", "conclusion": "success"}
        self.assertEqual(cd.assess(READY, ok, '{"notify": "sin_informe_nuevo"}', NOW)["state"], "complete_without_notification")
        self.assertEqual(cd.assess(READY, ok, '{"notify": "error", "detail": "URLError"}', NOW)["state"], "failed")
        self.assertEqual(cd.assess(READY, ok, None, NOW)["state"], "unconfirmed")

    def test_web_states(self):
        self.assertEqual(cd.assess(READY, {"status": "in_progress"}, SENT, NOW)["state"], "pending")
        self.assertEqual(cd.assess(READY, {"status": "completed", "conclusion": "failure"}, SENT, NOW)["state"], "failed")
        self.assertEqual(cd.assess(READY, None, SENT, NOW)["state"], "unconfirmed")

    def test_failed_chain_stage_wins(self):
        bad = json.loads(json.dumps(READY))
        bad["chain"]["heart"]["conclusion"] = "failure"
        self.assertEqual(cd.assess(bad, {"status": "completed", "conclusion": "success"}, SENT, NOW)["state"], "failed")

    def test_find_pages_run_takes_first_after_cycle(self):
        after = datetime.fromisoformat("2026-10-18T17:05:00+02:00")
        runs = [{"id": 3, "created_at": "2026-10-18T15:30:00Z"}, {"id": 2, "created_at": "2026-10-18T15:06:00Z"},
                {"id": 1, "created_at": "2026-10-18T10:00:00Z"}]
        self.assertEqual(cd.find_pages_run(runs, after)["id"], 2)
        self.assertIsNone(cd.find_pages_run(runs[2:], after))


class Main(unittest.TestCase):
    def run_main(self, fetch_json, fetch_text):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "report_ready.json").write_text(json.dumps(READY))
        with mock.patch.dict("os.environ", {"GITHUB_REPOSITORY": "o/r", "GH_TOKEN": "t"}):
            rc = cd.main(str(tmp), fetch_json, fetch_text, sleep=lambda s: None, wait_s=30)
        out = tmp / "delivery_status.json"
        return rc, json.loads(out.read_text()) if out.exists() else None

    def test_happy_path(self):
        t0 = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

        def fj(url, token):
            if url.endswith("/jobs"):
                return {"jobs": [{"id": 5, "steps": [{"name": "V6.3 - Aviso al móvil (ntfy) del informe nuevo"}]}]}
            return {"workflow_runs": [{"id": 8, "created_at": "2026-10-18T15:06:00Z", "status": "completed",
                                       "conclusion": "success", "updated_at": t0}]}
        rc, st = self.run_main(fj, lambda url, token: SENT)
        self.assertEqual((rc, st["state"]), (0, "complete"))

    def test_network_failure_never_blocks(self):
        def boom(*a, **k):
            raise OSError("sin red")
        rc, st = self.run_main(boom, boom)
        self.assertEqual(rc, 0)
        self.assertEqual(st["state"], "unconfirmed")


if __name__ == "__main__":
    unittest.main()
