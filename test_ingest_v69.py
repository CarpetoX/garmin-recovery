"""Ingesta resistente de Intervals.icu y estado de fuentes."""
import io
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from garmin_recovery import alerts, ingest, source_health

TZ = ZoneInfo("Europe/Madrid")


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def http(code):
    return urllib.error.HTTPError("u", code, "x", {}, io.BytesIO(b""))


class Fetch(unittest.TestCase):
    def test_retries_transient_then_succeeds(self):
        calls = []

        def fake(req, timeout=None):
            calls.append(1)
            if len(calls) < 3:
                raise http(503)
            return Resp(b'[{"id": "2026-10-18"}]')
        with mock.patch.object(urllib.request, "urlopen", fake):
            self.assertEqual(ingest.fetch_json("https://example.test/x", "k", sleep=lambda s: None), [{"id": "2026-10-18"}])
        self.assertEqual(len(calls), 3)

    def test_auth_is_not_retried(self):
        calls = []

        def fake(req, timeout=None):
            calls.append(1)
            raise http(403)
        with mock.patch.object(urllib.request, "urlopen", fake), self.assertRaises(ingest.IngestError) as cm:
            ingest.fetch_json("https://example.test/x", "k", sleep=lambda s: None)
        self.assertEqual((cm.exception.kind, cm.exception.http, len(calls)), ("auth", 403, 1))

    def test_classification(self):
        self.assertEqual(ingest.classify(http(429)), ("rate_limit", 429))
        self.assertEqual(ingest.classify(http(502)), ("server", 502))
        self.assertEqual(ingest.classify(urllib.error.URLError("dns"))[0], "network")
        self.assertEqual(ingest.classify(ValueError("x"))[0], "schema")


class KeepPrevious(unittest.TestCase):
    def run_in_tmp(self, exc, previous=True):
        with tempfile.TemporaryDirectory() as tmp:
            if previous:
                (Path(tmp) / "wellness.json").write_text("[]")

            def fake(req, timeout=None):
                raise exc
            with mock.patch.object(urllib.request, "urlopen", fake), mock.patch.object(ingest.time, "sleep", lambda s: None):
                try:
                    out = ingest.fetch_or_keep("wellness", "https://example.test/x", "k", str(Path(tmp) / "wellness.json"), root=Path(tmp))
                    err = None
                except ingest.IngestError as e:
                    out, err = "raised", e
                status = json.loads((Path(tmp) / ingest.STATUS).read_text())
            return out, err, status

    def test_transient_failure_keeps_previous_data(self):
        out, err, status = self.run_in_tmp(http(503))
        self.assertIsNone(out)
        self.assertEqual(status["wellness"]["status"], "error")
        self.assertEqual(status["wellness"]["consecutive_failures"], 1)

    def test_transient_without_previous_data_raises(self):
        out, err, _ = self.run_in_tmp(http(503), previous=False)
        self.assertEqual(out, "raised")

    def test_auth_failure_always_raises(self):
        out, err, status = self.run_in_tmp(http(401))
        self.assertEqual(out, "raised")
        self.assertEqual(status["wellness"]["kind"], "auth")

    def test_consecutive_failures_accumulate_and_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            e = ingest.IngestError("server", "x", 500)
            for _ in range(3):
                ingest.write_status("wellness", False, e, root=Path(tmp))
            self.assertEqual(json.loads((Path(tmp) / ingest.STATUS).read_text())["wellness"]["consecutive_failures"], 3)
            ingest.write_status("wellness", True, newest="2026-10-18", root=Path(tmp))
            self.assertEqual(json.loads((Path(tmp) / ingest.STATUS).read_text())["wellness"]["consecutive_failures"], 0)


class Alerts(unittest.TestCase):
    def test_alert_after_three_consecutive_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
            (Path(tmp) / "wellness.json").write_text(json.dumps([{"id": "2026-10-18", "hrv": 60}]))
            for n, expect in ((2, False), (3, True)):
                (Path(tmp) / "intervals_status.json").write_text(json.dumps(
                    {"wellness": {"status": "error", "kind": "server", "http": 503, "consecutive_failures": n}}))
                keys = [p["key"] for p in alerts.source_problems(Path(tmp), now)]
                self.assertEqual("intervals" in keys, expect, n)


class Health(unittest.TestCase):
    def test_table_and_activity_row_does_not_depend_on_last_activity_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
            r = Path(tmp)
            (r / "wellness.json").write_text(json.dumps([{"id": "2026-10-18", "hrv": 60}]))
            (r / "activities.json").write_text(json.dumps([{"start_date_local": "2026-10-10T10:00:00"}]))
            (r / "intervals_status.json").write_text(json.dumps(
                {"activities": {"status": "ok", "last_ok_at": "2026-10-18T11:00:00+02:00", "consecutive_failures": 0}}))
            (r / "garmin_status.json").write_text(json.dumps({"latest_heart_rate_date": "2026-10-16"}))
            rows = {x["source"]: x for x in source_health.collect(r, now)}
            self.assertIn("🟢", rows["Intervals.icu · actividades"]["icon"])
            self.assertIn("🔴", rows["Garmin · FC diurna y nocturna"]["icon"])  # 2 días de retraso
            md = source_health.to_markdown(list(rows.values()))
            self.assertIn("### Fuentes de datos", md)
            self.assertNotIn("None", md)


if __name__ == "__main__":
    unittest.main()
