"""V6.0: avisos en GitHub y puntualidad de los informes."""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import alerts
from garmin_recovery.weekly import punctuality

TZ = ZoneInfo("Europe/Madrid")
NOW = datetime(2026, 10, 18, 9, 0, tzinfo=TZ)


def workspace(gen=None, validation="ok", missed=()):
    tmp = tempfile.mkdtemp()
    app = Path(tmp, "app")
    app.mkdir()
    (app / "validation.json").write_text(json.dumps({"status": validation, "errors": ["md: falta el certificado"]}))
    (app / "readiness_v3.json").write_text(json.dumps({
        "generated_at": (gen or NOW - timedelta(minutes=20)).isoformat(),
        "certificate": {"execution_health": {"missed_slots": list(missed)}}}))
    return Path(tmp)


class Problems(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(alerts.problems(workspace(), NOW), [])

    def test_validation_failed(self):
        p = alerts.problems(workspace(validation="failed"), NOW)
        self.assertEqual(p[0]["key"], "validation")
        self.assertIn("falta el certificado", p[0]["text"])

    def test_stale_report(self):
        keys = [p["key"] for p in alerts.problems(workspace(gen=NOW - timedelta(hours=12)), NOW)]
        self.assertIn("stale", keys)
        # El hueco normal de la noche (22:50 → 08:35) no avisa
        self.assertEqual(alerts.problems(workspace(gen=NOW - timedelta(hours=9, minutes=50)), NOW), [])

    def test_only_recent_missed_slots(self):
        old = (NOW - timedelta(hours=16)).isoformat()
        recent = (NOW - timedelta(minutes=30)).isoformat()
        keys = [p["key"] for p in alerts.problems(workspace(missed=[old, recent]), NOW)]
        self.assertEqual(keys, ["missed:18/10 08:30"])


class FakeGitHub:
    def __init__(self, issues=None, comments=None):
        self.issues, self.comments, self.calls = issues or [], comments or [], []

    def __call__(self, method, path, token, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and path.endswith("/comments?per_page=100"):
            return self.comments
        if method == "GET":
            return self.issues
        return {}


class IssueLifecycle(unittest.TestCase):
    P = [{"key": "stale", "text": "Sin informe"}]

    def test_opens_once_and_mentions_owner(self):
        gh = FakeGitHub()
        self.assertEqual(alerts.sync_issue(self.P, "o/r", "t", "CarpetoX", api=gh), "opened")
        method, path, body = gh.calls[-1]
        self.assertEqual((method, path), ("POST", "/repos/o/r/issues"))
        self.assertIn("@CarpetoX", body["body"])

    def test_no_repeat_for_same_problem(self):
        gh = FakeGitHub()
        alerts.sync_issue(self.P, "o/r", "t", "x", api=gh)
        body = gh.calls[-1][2]["body"]
        gh2 = FakeGitHub(issues=[{"number": 7, "title": alerts.TITLE, "body": body}])
        self.assertEqual(alerts.sync_issue(self.P, "o/r", "t", "x", api=gh2), "unchanged")
        self.assertEqual(alerts.sync_issue([{"key": "validation", "text": "x"}], "o/r", "t", "x", api=gh2), "commented")

    def test_closes_when_resolved(self):
        gh = FakeGitHub(issues=[{"number": 7, "title": alerts.TITLE, "body": "..."}])
        self.assertEqual(alerts.sync_issue([], "o/r", "t", "x", api=gh), "closed")
        self.assertEqual(gh.calls[-1][0:2], ("PATCH", "/repos/o/r/issues/7"))
        self.assertEqual(alerts.sync_issue([], "o/r", "t", "x", api=FakeGitHub()), "ok")

    def test_network_errors_never_fail(self):
        import os
        from unittest import mock
        root = workspace(gen=NOW - timedelta(hours=30))
        with mock.patch.dict(os.environ, {"GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}), \
                mock.patch.object(alerts, "_api", side_effect=OSError("red caída")):
            self.assertEqual(alerts.main(str(root)), 0)


class Punctuality(unittest.TestCase):
    def test_slots_on_time_late_and_missing(self):
        reports = [
            {"generated_at": "2026-10-17T08:35:00+02:00", "data_synced_at": "2026-10-17T08:33:00+02:00"},
            {"generated_at": "2026-10-17T17:15:00+02:00", "data_synced_at": "2026-10-17T17:12:00+02:00"},
            {"generated_at": "2026-10-17T13:56:00+02:00", "data_synced_at": "2026-10-17T13:55:00+02:00"},
        ]
        p = punctuality(reports, date(2026, 10, 17), datetime(2026, 10, 17, 23, 30, tzinfo=TZ))
        by = {x["slot"]: x for x in p["slots"]}
        self.assertTrue(by["08:30"]["on_time"])
        self.assertEqual(by["08:30"]["minutes_margin"], 30)
        self.assertFalse(by["16:45"]["on_time"])
        self.assertIsNone(by["22:45"]["ready"])
        self.assertEqual((p["on_time"], p["total"]), (1, 3))

    def test_ignores_future_and_pre_record_slots(self):
        reports = [{"generated_at": "2026-10-17T17:05:00+02:00", "data_synced_at": "2026-10-17T17:04:00+02:00"}]
        p = punctuality(reports, date(2026, 10, 17), datetime(2026, 10, 17, 18, 0, tzinfo=TZ))
        self.assertEqual([x["slot"] for x in p["slots"]], ["16:45"])


if __name__ == "__main__":
    unittest.main()
