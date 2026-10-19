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
        self.assertEqual(keys, ["missed:2026-10-18T08:30"])

    def test_recovered_slot_is_not_a_problem(self):
        recent = (NOW - timedelta(minutes=30)).isoformat()
        ws = workspace(missed=[recent])
        (ws / "workflow_health.json").write_text(json.dumps({"alerts": [
            {"code": "cron_missed_dispatch_recovered", "slots": [recent]}]}))
        self.assertEqual(alerts.problems(ws, NOW), [])
        (ws / "workflow_health.json").write_text(json.dumps({"alerts": [
            {"code": "cron_missed_dispatch_recovered", "slots": [recent]},
            {"code": "sync_slot_not_recovered", "slots": [recent]}]}))
        self.assertEqual([p["key"] for p in alerts.problems(ws, NOW)], ["missed:2026-10-18T08:30"])


class FakeGitHub:
    """Simula issues y comentarios con estado (crear, comentar, cerrar)."""

    def __init__(self):
        self.issue, self.comments, self.calls = None, [], []

    def __call__(self, method, path, token, body=None):
        self.calls.append((method, path, body))
        if method == "GET" and "/comments" in path:
            return list(self.comments)
        if method == "GET":
            return [self.issue] if self.issue and self.issue["state"] == "open" else []
        if method == "POST" and path.endswith("/issues"):
            self.issue, self.comments = {"number": 7, "title": body["title"], "body": body["body"], "state": "open"}, []
        elif method == "POST":
            self.comments.append({"body": body["body"]})
        elif method == "PATCH":
            self.issue["state"] = body["state"]
        return {}


def run(gh, found, scope="chain"):
    return alerts.sync_issue(found, "o/r", "t", "CarpetoX", scope=scope, api=gh)


A, B = {"key": "validation", "text": "A"}, {"key": "stale", "text": "B"}


class IssueLifecycle(unittest.TestCase):
    def test_opens_once_and_mentions_owner(self):
        gh = FakeGitHub()
        self.assertEqual(run(gh, [B]), "opened")
        self.assertIn("@CarpetoX", gh.issue["body"])
        self.assertEqual(run(gh, [B]), "unchanged")

    def test_change_back_is_announced(self):  # A → A+B → A
        gh = FakeGitHub()
        run(gh, [A])
        self.assertEqual(run(gh, [A, B]), "commented")
        self.assertEqual(run(gh, [A]), "commented")
        self.assertEqual(run(gh, [A]), "unchanged")

    def test_watchdog_cannot_close_chain_failure(self):
        gh = FakeGitHub()
        run(gh, [{"key": "chain_failed", "text": "x"}], scope="chain")
        self.assertEqual(run(gh, [], scope="watchdog"), "unchanged")
        self.assertEqual(gh.issue["state"], "open")
        self.assertEqual(run(gh, [], scope="chain"), "closed")
        self.assertEqual(gh.issue["state"], "closed")
        self.assertIn("garmin-keys: -->", gh.comments[-1]["body"])

    def test_watchdog_and_chain_keys_merge(self):
        gh = FakeGitHub()
        run(gh, [A], scope="chain")
        self.assertEqual(run(gh, [B], scope="watchdog"), "commented")
        self.assertIn("Sigue pendiente: `validation`", gh.comments[-1]["body"])
        self.assertEqual(run(gh, [], scope="watchdog"), "commented")  # stale resuelto; validation sigue
        self.assertEqual(gh.issue["state"], "open")

    def test_network_errors_never_fail(self):
        import os
        from unittest import mock
        root = workspace(gen=NOW - timedelta(hours=30))
        with mock.patch.dict(os.environ, {"GH_TOKEN": "t", "GITHUB_REPOSITORY": "o/r"}), \
                mock.patch.object(alerts, "_api", side_effect=OSError("red caída")):
            self.assertEqual(alerts.main(str(root)), 0)


class ChainStatus(unittest.TestCase):
    def test_failed_job_reports_chain_failed_not_local_files(self):
        keys = [p["key"] for p in alerts.problems(workspace(validation="failed"), NOW, "chain", job_status="failure")]
        self.assertEqual(keys, ["chain_failed"])

    def test_watchdog_reads_workflow_health_and_madrid_time(self):
        root = workspace()
        slot = datetime(2026, 10, 18, 8, 30, tzinfo=TZ)
        (root / "workflow_health.json").write_text(json.dumps(
            {"alerts": [{"code": "sync_slot_not_recovered", "slots": [slot.isoformat()]}]}))
        p = alerts.problems(root, NOW.astimezone(ZoneInfo("UTC")), "watchdog")
        self.assertEqual(p[0]["key"], "missed:2026-10-18T08:30")
        self.assertIn("18/10 08:30", p[0]["text"])
        stale = alerts.problems(workspace(gen=NOW - timedelta(hours=12)), NOW.astimezone(ZoneInfo("UTC")), "watchdog")
        self.assertIn((NOW - timedelta(hours=12)).strftime("%d/%m %H:%M"), stale[0]["text"])


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
