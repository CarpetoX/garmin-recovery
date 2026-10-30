"""V8.12: reintentos del certificador ante fallos transitorios de GitHub y aviso ntfy cuando falla la cadena."""
import os
import unittest
import urllib.error
from datetime import datetime
from unittest import mock

from garmin_recovery import delivery_gate as g
from garmin_recovery import notify
from test_gate_retry_v728 import ADV, CF, HEART, SYNC


class CertifierRetry(unittest.TestCase):
    def test_crossfit_status_glitch_is_retried(self):
        calls = {"cf": 0}

        def fetch(url, token):
            if url.endswith("/runs/4"):
                calls["cf"] += 1
                return dict(CF, status="queued") if calls["cf"] == 1 else dict(CF)
            if url.endswith("/runs/3"):
                return dict(ADV)
            if "garmin-heart-rate.yml" in url:
                return {"workflow_runs": [HEART]}
            return {"workflow_runs": [SYNC]}
        chain, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=lambda s: None)
        self.assertEqual(problems, [])
        self.assertEqual(calls["cf"], 2)

    def test_api_502_is_retried(self):
        calls = {"n": 0}

        def fetch(url, token):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(url, 502, "Bad Gateway", {}, None)
            if url.endswith("/runs/4"):
                return dict(CF)
            if url.endswith("/runs/3"):
                return dict(ADV)
            if "garmin-heart-rate.yml" in url:
                return {"workflow_runs": [HEART]}
            return {"workflow_runs": [SYNC]}
        chain, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=lambda s: None)
        self.assertEqual(problems, [])

    def test_persistent_api_error_reports_reason(self):
        def fetch(url, token):
            raise urllib.error.URLError("down")
        chain, problems = g.fetch_chain("o/r", "t", "4", "3", fetch=fetch, sleep=lambda s: None)
        self.assertIsNone(chain)
        self.assertEqual(problems, ["github_api_error"])


class FailureNotice(unittest.TestCase):
    def test_failure_message_has_no_physiology_and_links_run(self):
        m = notify.failure_message("https://x/run/1", datetime(2026, 10, 30, 19, 10, tzinfo=notify.TZ))
        self.assertIn("19:10", m["message"])
        self.assertEqual(m["click"], "https://x/run/1")
        self.assertNotRegex(m["message"], r"VFC|HRV|lpm|sueño")

    def test_main_sends_failure_when_chain_failed(self):
        sent = []
        env = {"NTFY_TOPIC": "t", "CHAIN_STATUS": "failure", "RUN_URL": "https://x/run/9"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(notify, "send", lambda msg, topic, server: sent.append(msg) or 200):
            self.assertEqual(notify.main("."), 0)
        self.assertEqual(sent[0]["title"], "Fallo en la actualización")

    def test_success_keeps_normal_path(self):
        env = {"NTFY_TOPIC": "t", "CHAIN_STATUS": "success"}
        with mock.patch.dict(os.environ, env, clear=False), \
                mock.patch.object(notify, "build_message", lambda root: None), \
                mock.patch.object(notify, "send", side_effect=AssertionError("no debe enviar")):
            self.assertEqual(notify.main("."), 0)


if __name__ == "__main__":
    unittest.main()
