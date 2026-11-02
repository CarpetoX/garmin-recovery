"""V8.9: copias ligeras del registro de ciclos y salvaguarda del híbrido."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from garmin_recovery import ledger_light
from garmin_recovery.archive_report_cycles import digest
from garmin_recovery.reliability import patch_hybrid

NOW = datetime(2026, 11, 2, 18, 0, tzinfo=timezone(timedelta(hours=1)))


def _row(cid, hours_ago, size=10):
    snap = {"cycle_id": cid, "payload": "x" * size}
    at = (NOW - timedelta(hours=hours_ago)).isoformat()
    return {"cycle_id": cid, "slot_at": at, "ready_at": at, "state": "data_ready", "snapshot": snap,
            "snapshot_sha256": digest(snap), "chain": {"big": "y" * 50}}


class LightCopies(unittest.TestCase):
    def test_recent_and_index(self):
        ledger = {"cycles": [_row(f"c{i}", h) for i, h in enumerate((200, 100, 60, 10, 1))]}
        recent, index = ledger_light.build(ledger, NOW)
        self.assertEqual([c["cycle_id"] for c in recent["cycles"]], ["c2", "c3", "c4"])
        self.assertIn("snapshot", recent["cycles"][0])
        self.assertEqual(len(index["cycles"]), 5)
        self.assertNotIn("snapshot", index["cycles"][0])
        self.assertNotIn("chain", index["cycles"][0])
        self.assertEqual(index["cycles"][0]["snapshot_sha256"], ledger["cycles"][0]["snapshot_sha256"])
        self.assertEqual(recent["source"]["cycles_digest_sha256"], digest(ledger["cycles"]))

    def test_stays_under_one_megabyte(self):
        ledger = {"cycles": [_row(f"c{i}", 1 + i, size=300_000) for i in range(6)]}
        recent, _ = ledger_light.build(ledger, NOW)
        self.assertLessEqual(len(ledger_light._dump(recent)), ledger_light.MAX_BYTES)
        self.assertEqual(recent["cycles"][-1]["cycle_id"], "c0")  # el más reciente siempre está

    def test_bad_hash_writes_nothing_and_never_fails(self):
        row = _row("c0", 1)
        row["snapshot_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            ledger_light.build({"cycles": [row]}, NOW)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "report_cycles.json").write_text(json.dumps({"cycles": [row]}), encoding="utf-8")
            self.assertEqual(ledger_light.main(d, NOW), 0)
            self.assertFalse((Path(d) / "report_cycles_recent.json").exists())

    def test_original_is_never_touched(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "report_cycles.json"
            src.write_text(json.dumps({"cycles": [_row("c0", 1)]}), encoding="utf-8")
            before = src.read_bytes()
            ledger_light.main(d, NOW)
            self.assertEqual(src.read_bytes(), before)
            self.assertEqual(json.loads((Path(d) / "report_cycles_recent.json").read_text(encoding="utf-8"))["count"], 1)


class HybridGuardrail(unittest.TestCase):
    ASSESSED_YELLOW = {"state": "assessed", "confidence": "high", "status": "yellow"}

    def test_garmin_below_35_stays_red(self):
        h = {"score": 49, "raw_score_before_guardrails": 61, "status": "red",
             "guardrails_applied": ["garmin_score_below_35_forces_red", "recovery_time_24h_or_more_prevents_green"]}
        out = patch_hybrid(h, self.ASSESSED_YELLOW)
        self.assertEqual((out["score"], out["status"], out["recommendation"]), (49, "red", "recovery"))
        again = patch_hybrid(out, self.ASSESSED_YELLOW)  # aplicar dos veces no cambia nada
        self.assertEqual((again["score"], again["status"]), (49, "red"))

    def test_garmin_low_never_green(self):
        h = {"score": 74, "raw_score_before_guardrails": 88, "status": "yellow", "guardrails_applied": ["garmin_low_prevents_green"]}
        out = patch_hybrid(h, {"state": "assessed", "confidence": "high", "status": "green"})
        self.assertEqual((out["score"], out["status"]), (74, "yellow"))

    def test_without_garmin_caps_unchanged(self):
        h = {"score": 82, "raw_score_before_guardrails": 82, "status": "green", "guardrails_applied": []}
        out = patch_hybrid(h, {"state": "assessed", "confidence": "high", "status": "green"})
        self.assertEqual((out["score"], out["status"]), (82, "green"))


if __name__ == "__main__":
    unittest.main()
