import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery import delivery_gate as g
from garmin_recovery import monitor_v231 as m

TZ = ZoneInfo("Europe/Madrid")


def at(h, mi=0, day=18):
    return datetime(2026, 10, day, h, mi, tzinfo=TZ)


def run(created, minutes=5, event="workflow_run", conclusion="success", status="completed", **k):
    c = created if isinstance(created, datetime) else at(*created)
    r = {"status": status, "conclusion": conclusion, "event": event, "created_at": c.isoformat(),
         "updated_at": (c + timedelta(minutes=minutes)).isoformat(), "id": 1}
    r.update(k)
    return r


class Basics(unittest.TestCase):
    def test_stamp(self):
        self.assertIsNone(g.stamp(None))
        self.assertIsNone(g.stamp(""))
        self.assertIsNone(g.stamp("basura"))
        self.assertEqual(g.stamp("2026-10-18T10:00:00").hour, 10)
        self.assertEqual(g.stamp("2026-10-18T10:00:00Z").hour, 12)

    def test_slot_for_run(self):
        s = g.slot_for_run(at(8, 31))
        self.assertEqual((s["cycle_id"], s["report_target"]), ("2026-10-18-0830", "09:05"))
        self.assertEqual(g.slot_for_run(at(11, 0))["cycle_id"], "2026-10-18-0830")      # dentro de los 150 min
        self.assertIsNone(g.slot_for_run(at(12, 0)))
        self.assertEqual(g.slot_for_run(at(1, 0, day=19))["cycle_id"], "2026-10-18-2245")  # tras medianoche
        self.assertIsNone(g.slot_for_run(None))

    def test_successful(self):
        self.assertTrue(g.successful(run((8, 30)), {"workflow_run"}))
        self.assertFalse(g.successful(run((8, 30), conclusion="failure"), {"workflow_run"}))
        self.assertFalse(g.successful(run((8, 30), event="schedule"), {"workflow_run"}))
        self.assertFalse(g.successful(None, {"workflow_run"}))

    def test_parent_before(self):
        child = run((8, 40))
        old = run((8, 30), 5)       # termina 8:35, 5 min antes
        far = run((6, 0), 5)
        newer = run((8, 32), 6)     # termina 8:38
        self.assertIs(g.parent_before([far, old, newer], child, {"workflow_run"}), newer)
        self.assertIsNone(g.parent_before([far], child, {"workflow_run"}))
        self.assertIsNone(g.parent_before([old], {"created_at": None}, {"workflow_run"}))


def chain_runs(sync_at=(8, 31)):
    sync = run(sync_at, 4, event="schedule", id=10)
    heart = run(at(*sync_at) + timedelta(minutes=5), 4, id=11)
    adv = run(at(*sync_at) + timedelta(minutes=10), 4, id=12)
    cf = run(at(*sync_at) + timedelta(minutes=15), 3, status="in_progress", conclusion=None, id=13)
    return sync, heart, adv, cf


class Chain(unittest.TestCase):
    def test_valid_chain(self):
        sync, heart, adv, cf = chain_runs()
        chain, problems = g.validate_chain(cf, [adv], [heart], [sync])
        self.assertEqual(problems, [])
        self.assertEqual(chain["slot"]["cycle_id"], "2026-10-18-0830")
        self.assertEqual(set(chain["runs"]), {"sync", "heart", "advanced", "crossfit"})

    def test_chain_failures(self):
        sync, heart, adv, cf = chain_runs()
        self.assertEqual(g.validate_chain(None, [adv], [heart], [sync])[1], ["crossfit_not_workflow_run"])
        bad = dict(cf, conclusion="failure", status="completed")
        self.assertEqual(g.validate_chain(bad, [adv], [heart], [sync])[1], ["crossfit_not_active_or_successful"])
        self.assertEqual(g.validate_chain(cf, [], [heart], [sync])[1], ["advanced_missing_or_not_correlated"])
        self.assertEqual(g.validate_chain(cf, [adv], [], [sync])[1], ["heart_missing_or_not_correlated"])
        self.assertEqual(g.validate_chain(cf, [adv], [heart], [])[1], ["sync_missing_or_not_correlated"])

    def test_outside_slot(self):
        sync, heart, adv, cf = chain_runs((13, 0))
        with tempfile.TemporaryDirectory() as d, self.subTest("sin ledger"):
            import os
            old = os.getcwd()
            os.chdir(d)
            try:
                self.assertEqual(g.validate_chain(cf, [adv], [heart], [sync])[1], ["sync_outside_report_slot"])
            finally:
                os.chdir(old)


class Files(unittest.TestCase):
    def test_validate_files(self):
        sync, heart, adv, cf = chain_runs()
        chain = {"runs": {"sync": sync, "heart": heart, "advanced": adv, "crossfit": cf}}
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            _, problems = g.validate_files(chain, d)
            self.assertEqual(len(problems), len(g.REQUIRED))
            self.assertTrue(all(p.startswith("missing_or_invalid:") for p in problems))
            fresh = at(8, 50).isoformat()
            for name in g.REQUIRED:
                body = {"generated_at": fresh}
                if name == "garmin_status.json":
                    body["status"] = "success"
                if name == "recovery_assessment.json":
                    body.update(state="assessed", v23={"version": "2.3.1"})
                (d / name).write_text(json.dumps(body), encoding="utf-8")
            generated, problems = g.validate_files(chain, d)
            self.assertEqual(problems, [])
            self.assertEqual(len(generated), len(g.REQUIRED))
            (d / "garmin_status.json").write_text(json.dumps({"generated_at": fresh, "status": "error"}), encoding="utf-8")
            (d / "recovery_assessment.json").write_text(json.dumps({"generated_at": fresh, "state": "x", "v23": {}}), encoding="utf-8")
            (d / "daily_summary.json").write_text(json.dumps({"generated_at": at(7, 0).isoformat()}), encoding="utf-8")
            _, problems = g.validate_files(chain, d)
            for needle in ("garmin_status_not_success", "wrong_recovery_version", "invalid_recovery_state", "not_generated_in_cycle:daily_summary.json"):
                self.assertIn(needle, problems)


class Monitor(unittest.TestCase):
    def test_due_slots(self):
        now = at(12, 0)
        self.assertEqual([s.strftime("%d %H:%M") for s in m.due_slots(now)], ["17 08:30", "17 16:45", "17 22:45", "18 08:30"])
        self.assertEqual(m.due_slots(datetime(2026, 10, 9, 23, 0)), [])  # antes de SCHEDULE_START
        self.assertEqual(m.due_slots(now.replace(tzinfo=None))[0].tzinfo is not None, True)

    def test_audit_states(self):
        now = at(12, 0)
        self.assertEqual(m.audit_slots(now, None)["state"], "unverified")
        runs = [run(datetime(2026, 10, 17, 8, 31, tzinfo=TZ), event="schedule"),
                run(datetime(2026, 10, 17, 16, 46, tzinfo=TZ), event="schedule"),
                run(datetime(2026, 10, 17, 22, 50, tzinfo=TZ), event="repository_dispatch"),
                run(at(8, 40), event="schedule", conclusion="failure")]
        out = m.audit_slots(now, runs)
        self.assertEqual((out["state"], out["matched"], out["recovered_count"]), ("attention", 2, 1))
        self.assertEqual(out["uncovered"], [at(8, 30).isoformat()])
        ok = m.audit_slots(now, runs + [run(at(8, 35), event="workflow_dispatch")])
        self.assertEqual(ok["state"], "recovered")
        self.assertEqual(len(ok["recovered_by_manual"]), 1)
        self.assertEqual(m.audit_slots(datetime(2026, 10, 10, 5, 0, tzinfo=TZ), [])["state"], "awaiting_next_due_slot")

    def test_gate_status(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "report_ready.json"
            self.assertEqual(m.gate_status(at(12), str(p))["state"], "not_yet_published")
            p.write_text(json.dumps({"status": "pending"}), encoding="utf-8")
            self.assertEqual(m.gate_status(at(12), str(p))["state"], "invalid")
            p.write_text(json.dumps({"status": "ready", "cycle_id": "c", "verified_at": at(10).isoformat(),
                                     "chain": {"sync": {"id": 42}}}), encoding="utf-8")
            st = m.gate_status(at(12), str(p))
            self.assertEqual((st["state"], st["age_hours"], st["last_sync_run_id"]), ("ready", 2.0, 42))
        self.assertIsNone(m._utc_local("x"))
        self.assertIsNone(m._utc_local(None))


if __name__ == "__main__":
    unittest.main()
