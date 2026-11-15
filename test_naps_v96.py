"""V9.6: siestas de Garmin (extracción, recogida en el ciclo y línea en el panel)."""
import json
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from garmin_recovery import garmin_sleep_history as gsh
from garmin_recovery import panel_v9


class FakeApi:
    def __init__(self, naps=None, fail=False, has_get_naps=True):
        self.naps, self.fail, self.calls = naps or [], fail, []
        if has_get_naps:
            self.get_naps = self._get_naps

    def _get_naps(self, d):
        self.calls.append(("naps", d))
        if self.fail:
            raise RuntimeError("boom")
        return self.naps if d == "2026-11-15" else []

    def connectapi(self, path, params=None):
        self.calls.append(("connectapi", path))
        return self.naps

    def get_sleep_data(self, d):
        return {}

    def get_hrv_data(self, d):
        return {}


NAP = [{"napStartTimestampGMT": "2026-11-15T14:30:00.0", "napEndTimestampGMT": "2026-11-15T16:40:00.0"}]
NOW = datetime(2026, 11, 15, 22, 50, tzinfo=gsh.TZ)


class NapTests(unittest.TestCase):
    def test_extract_variants_and_rejects(self):
        n = gsh.extract_naps(NAP)
        self.assertEqual((n[0]["start_local"][11:16], n[0]["end_local"][11:16], n[0]["minutes"]), ("15:30", "17:40", 130))
        local = gsh.extract_naps([{"startLocal": "2026-11-15T15:30:00", "endLocal": "2026-11-15T16:00:00"}])
        self.assertEqual(local[0]["start_local"][11:16], "15:30")  # hora local sin zona: Madrid, no GMT
        self.assertEqual(gsh.extract_naps([{"startGMT": "2026-11-15T16:00:00", "endGMT": "2026-11-15T15:00:00"}]), [])
        self.assertEqual(gsh.extract_naps([{"startGMT": "2026-11-15T08:00:00", "endGMT": "2026-11-15T14:00:00"}]), [])  # > 4 h
        self.assertEqual(gsh.extract_naps(None), [])

    def test_collect_today_only_and_errors(self):
        api = FakeApi(NAP)
        res = gsh.collect(api, now=NOW, existing={})
        self.assertEqual(res["days"]["2026-11-15"]["nap_minutes"], 130)
        self.assertEqual(res["days"]["2026-11-14"]["naps"], [])
        self.assertEqual(sum(1 for c in api.calls if c[0] == "naps"), 2)  # solo hoy y ayer
        bad = gsh.collect(FakeApi(fail=True), now=NOW, existing={"days": {"2026-11-15": {"naps": [{"minutes": 30}], "nap_minutes": 30}}})
        self.assertEqual(bad["days"]["2026-11-15"]["nap_minutes"], 30)  # un fallo no borra lo que había
        self.assertIn("naps:2026-11-15", bad["fetch_errors"])

    def test_collect_without_get_naps_uses_endpoint(self):
        api = FakeApi(NAP, has_get_naps=False)
        res = gsh.collect(api, now=NOW, existing={})
        self.assertIn(("connectapi", "/sleep-service/sleep/naps/2026-11-15"), api.calls)
        self.assertEqual(res["days"]["2026-11-15"]["nap_minutes"], 130)

    def test_panel_line(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(panel_v9.naps_line(root, "2026-11-15"), "")
            (root / "garmin_sleep_history.json").write_text(json.dumps({"days": {"2026-11-15": {"naps": gsh.extract_naps(NAP)}}}))
            line = panel_v9.naps_line(root, "2026-11-15")
            self.assertIn("15:30 → 17:40 (2 h 10 min)", line)
            self.assertIn("no suma al sueño", line)


if __name__ == "__main__":
    unittest.main()
