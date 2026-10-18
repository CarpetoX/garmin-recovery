import base64
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from garmin_recovery import alerts, token_health as th

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)


def b64(obj):
    return base64.b64encode(json.dumps(obj).encode()).decode()


def jwt(exp):
    enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    return f"{enc({'alg': 'none'})}.{enc({'exp': exp})}.firma"


def ts(days):
    return NOW.timestamp() + days * 86400


class Inspect(unittest.TestCase):
    def test_jwt_and_numeric_fields(self):
        r = th.inspect(b64({"a": {"token": jwt(ts(10))}, "expires_at": ts(2), "expires_in": 3600}), NOW)
        self.assertEqual((r["state"], r["days_left"]), ("ok", 10.0))
        self.assertEqual(th.inspect(b64({"refresh_token_expires_at": 1}), NOW)["state"], "no_expiry_found")
        self.assertEqual(th.inspect(b64({"expires_at": ts(30) * 1000}), NOW)["days_left"], 30.0)  # milisegundos
        self.assertEqual(th.inspect(b64({"x": [{"exp": ts(5)}]}), NOW)["days_left"], 5.0)

    def test_expired_unreadable_and_no_secret_in_output(self):
        r = th.inspect(b64({"tok": jwt(ts(-3))}), NOW)
        self.assertEqual(r["state"], "expired")
        self.assertEqual(th.inspect("%%%", NOW)["state"], "unreadable")
        self.assertEqual(th.inspect(b64([1, 2]), NOW)["state"], "no_expiry_found")
        self.assertNotIn("firma", json.dumps(th.inspect(b64({"tok": jwt(ts(4))}), NOW)))


class Alert(unittest.TestCase):
    def problems(self, expiry):
        d = Path(tempfile.mkdtemp())
        (d / "garmin_status.json").write_text(json.dumps({"latest_heart_rate_date": "2026-10-18", "token_expiry": expiry}))
        return [p["key"] for p in alerts.source_problems(d, datetime(2026, 10, 18, 12, 0, tzinfo=alerts.TZ))]

    def test_warns_only_when_close(self):
        self.assertIn("garmin_token", self.problems({"state": "ok", "latest_expiry": "2026-10-25", "days_left": 7}))
        self.assertNotIn("garmin_token", self.problems({"state": "ok", "latest_expiry": "2027-01-01", "days_left": 75}))
        self.assertNotIn("garmin_token", self.problems({"state": "expired", "latest_expiry": "2026-10-01", "days_left": -17}))
        self.assertNotIn("garmin_token", self.problems({"state": "no_expiry_found"}))
        self.assertTrue(alerts._in_scope("garmin_token", "chain") and alerts._in_scope("garmin_token", "watchdog"))


if __name__ == "__main__":
    unittest.main()
