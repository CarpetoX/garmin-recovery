"""V7.27: una franja que el respaldo de Apps Script recuperó no se certifica como perdida."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from garmin_recovery.config import load_config
from garmin_recovery.quality import certificate

TZ = ZoneInfo("Europe/Madrid")
ROOT = Path(__file__).resolve().parent
NOW = datetime(2026, 10, 22, 9, 0, tzinfo=TZ)
REC = ["2026-10-21T16:45:00+02:00", "2026-10-21T22:45:00+02:00"]
LOST = ["2026-10-22T08:30:00+02:00"]


def cert(alerts):
    readiness = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))["readiness"]
    with tempfile.TemporaryDirectory() as d:
        return certificate(Path(d), {"workflow_health": {"status": "attention", "alerts": alerts}},
                           readiness, NOW, TZ, load_config(ROOT))


class MissedSlots(unittest.TestCase):
    def test_recovered_slots_are_not_missed(self):
        c = cert([{"code": "cron_missed_dispatch_recovered", "severity": "warning", "slots": REC}])
        eh = c["execution_health"]
        self.assertEqual(eh["missed_slots"], [])
        self.assertEqual(eh["recovered_slots"], REC)
        self.assertFalse(any("franja" in i for i in c.get("issues") or []))

    def test_unrecovered_slot_is_still_a_warning(self):
        c = cert([{"code": "cron_missed_dispatch_recovered", "slots": REC},
                  {"code": "sync_slot_not_recovered", "slots": LOST}])
        self.assertEqual(c["execution_health"]["missed_slots"], LOST)
        self.assertEqual(c["execution_health"]["recovered_slots"], REC)
        self.assertTrue(any("1 franja(s) de Sync sin ejecutar ni recuperar" in i for i in c["issues"]))


if __name__ == "__main__":
    unittest.main()
