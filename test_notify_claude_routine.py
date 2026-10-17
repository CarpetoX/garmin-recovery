import io
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

import notify_claude_routine as n

URL = "https://api.anthropic.com/v1/claude_code/routines/trig_TEST/fire"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class NotifyRoutineTests(unittest.TestCase):
    def test_without_secrets_is_noop(self):
        called = []
        self.assertEqual(n.main(env={}, opener=lambda *a, **k: called.append(1)), 0)
        self.assertEqual(called, [])

    def test_rejects_unexpected_url(self):
        env = {"CLAUDE_ROUTINE_URL": "https://example.com/fire", "CLAUDE_ROUTINE_TOKEN": "x"}
        self.assertEqual(n.main(env=env, opener=lambda *a, **k: None), 1)

    def test_posts_cycle_context(self):
        seen = {}

        def opener(req, timeout):
            seen["req"] = req
            return FakeResponse(b'{"claude_code_session_id": "session_1"}')

        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "report_ready.json").write_text(json.dumps({"cycle_id": "2026-10-17-1645", "status": "ready"}))
            env = {"CLAUDE_ROUTINE_URL": URL, "CLAUDE_ROUTINE_TOKEN": "tok", "GITHUB_SHA": "abc"}
            self.assertEqual(n.main(env=env, root=Path(tmp), opener=opener), 0)
        req = seen["req"]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers["Authorization"], "Bearer tok")
        self.assertEqual(req.headers["Anthropic-beta"], n.BETA_HEADER)
        text = json.loads(req.data)["text"]
        self.assertIn("2026-10-17-1645", text)
        self.assertIn("abc", text)

    def test_http_error_returns_1(self):
        def opener(req, timeout):
            raise urllib.error.HTTPError(URL, 401, "unauthorized", {}, None)
        env = {"CLAUDE_ROUTINE_URL": URL, "CLAUDE_ROUTINE_TOKEN": "tok"}
        self.assertEqual(n.main(env=env, opener=opener), 1)


if __name__ == "__main__":
    unittest.main()
