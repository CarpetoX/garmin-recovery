"""V9.4: historial largo de Garmin (descarga de días que faltan, medianas mensuales y tarjeta en Progreso)."""
import csv
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from garmin_recovery import longterm_history as lh
from garmin_recovery import panel_v9


def _sleep(day: str, hours: float = 7.5, start_hour: int = 0, score: int = 80):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    start = datetime.fromisoformat(day).replace(hour=start_hour, tzinfo=ZoneInfo("Europe/Madrid"))
    end = start + timedelta(hours=hours + 0.25)
    return {"dailySleepDTO": {"sleepStartTimestampGMT": int(start.timestamp() * 1000), "sleepEndTimestampGMT": int(end.timestamp() * 1000),
                              "sleepTimeSeconds": int(hours * 3600), "sleepScores": {"overall": {"value": score}}}}


class FakeApi:
    def __init__(self, fail_day=None):
        self.calls, self.fail_day = [], fail_day

    def get_hrv_data(self, d):
        self.calls.append(("hrv", d))
        if d == self.fail_day:
            raise RuntimeError("boom")
        return {"hrvSummary": {"lastNightAvg": 50}}

    def get_stats(self, d):
        self.calls.append(("stats", d))
        return {"restingHeartRate": 56, "averageStressLevel": 30, "bodyBatteryHighestValue": 90, "bodyBatteryLowestValue": 20}

    def get_sleep_data(self, d):
        self.calls.append(("sleep", d))
        return _sleep(d)


class LongtermTests(unittest.TestCase):
    def test_extract_day_and_bounds(self):
        row = lh.extract_day("2026-03-05", {"hrvSummary": {"lastNightAvg": 47.6}},
                             {"restingHeartRate": 999, "averageStressLevel": 25}, _sleep("2026-03-05"), "2026-11-13T03:00:00+01:00")
        self.assertEqual(row["hrv_ms"], 48)
        self.assertIsNone(row["resting_hr"])  # fuera de rango: vacío, no se inventa
        self.assertEqual(row["stress_avg"], 25)
        self.assertEqual(row["sleep_hours"], 7.5)
        self.assertEqual(row["sleep_context"], "night_sleep")

    def test_backfill_only_missing_and_survives_errors(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            lh.write(root / lh.FILE, {"2026-03-01": {"date": "2026-03-01", "hrv_ms": 40}})
            api = FakeApi(fail_day="2026-03-02")
            res = lh.backfill(root, api, "2026-03-01", "2026-03-03", pause=0)
            self.assertEqual(res["requested"], 2)  # el 1 ya estaba
            self.assertNotIn(("hrv", "2026-03-01"), api.calls)
            rows = lh.read(root / lh.FILE)
            self.assertEqual(rows["2026-03-01"]["hrv_ms"], "40")  # no se reescribe lo que había
            self.assertEqual(rows["2026-03-02"]["hrv_ms"], "")  # falló la HRV, el resto se guarda
            self.assertEqual(rows["2026-03-02"]["resting_hr"], "56")
            self.assertEqual(res["errors"], 1)

    def test_monthly_medians_precedence_and_min_days(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = {}
            d = date(2026, 3, 1)
            while d <= date(2026, 4, 30):
                rows[d.isoformat()] = {"date": d.isoformat(), "hrv_ms": 40 if d.month == 3 else 50, "resting_hr": 60,
                                       "sleep_hours": 7, "sleep_context": "night_sleep"}
                d += timedelta(days=1)
            rows["2026-04-10"]["sleep_hours"], rows["2026-04-10"]["sleep_context"] = 3, "day_sleep"
            for k in ("2026-05-01", "2026-05-02"):
                rows[k] = {"date": k, "hrv_ms": 99}
            lh.write(root / lh.FILE, rows)
            (root / "history").mkdir(exist_ok=True)
            with (root / "history" / "daily.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["date", "hrv_ms", "resting_hr"])
                w.writeheader()
                for i in range(1, 31):
                    w.writerow({"date": f"2026-04-{i:02d}", "hrv_ms": 60, "resting_hr": ""})
            m = {r["month"]: r for r in lh.monthly(root)}
            self.assertEqual(m["2026-03"]["hrv_ms"], 40)
            self.assertEqual(m["2026-04"]["hrv_ms"], 60)  # manda daily.csv
            self.assertEqual(m["2026-04"]["resting_hr"], 60)  # vacío en daily.csv: se conserva el largo
            self.assertEqual(m["2026-04"]["sleep_hours_n"], 29)  # la siesta de día no cuenta
            self.assertIsNone(m["2026-05"]["hrv_ms"])  # 2 días: sin mediana

    def test_panel_card(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIn("Aparecerá cuando", panel_v9.longterm_card(root, "2026-11-13"))
            rows, d = {}, date(2026, 3, 1)
            while d <= date(2026, 5, 31):
                rows[d.isoformat()] = {"date": d.isoformat(), "hrv_ms": {3: 40, 4: 45, 5: 52}[d.month], "resting_hr": {3: 62, 4: 60, 5: 58}[d.month]}
                d += timedelta(days=1)
            lh.write(root / lh.FILE, rows)
            html = panel_v9.longterm_card(root, "2026-05-20")
            self.assertIn("¿Cómo he cambiado mes a mes?", html)
            self.assertIn("desde mar 2026", html)
            self.assertIn("+12 mejor", html)  # HRV 40 → 52
            self.assertIn("-4 mejor", html)  # FC en reposo baja: mejor
            self.assertIn("may (en curso)", html)


if __name__ == "__main__":
    unittest.main()
