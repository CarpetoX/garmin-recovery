import unittest

from garmin_recovery import zone_calibration as z


def rows(n, zone_fn, hrv_fn):
    return [{"date": f"2026-09-{1 + i:02d}", "hrv_ms": str(hrv_fn(i)), "decision_zone": zone_fn(i)} for i in range(n)]


class Calibration(unittest.TestCase):
    def test_insufficient_history(self):
        r = z.compute(rows(5, lambda i: "green", lambda i: 50), "2026-09-05")
        self.assertFalse(r["available"])
        self.assertIn("al menos 10", z.to_markdown(r))

    def test_zone_means(self):
        # días pares: verde y HRV siguiente (impar) alto; impares: rojo y HRV siguiente (par) bajo
        data = rows(26, lambda i: "green" if i % 2 == 0 else "red", lambda i: 70 if i % 2 else 40)
        r = z.compute(data, "2026-09-26")
        self.assertTrue(r["available"])
        self.assertGreater(r["zones"]["green"]["mean_delta_ms"], 0)
        self.assertLess(r["zones"]["red"]["mean_delta_ms"], 0)
        self.assertFalse(r["zones"]["yellow"]["ok"])
        md = z.to_markdown(r)
        self.assertIn("🟢 Verde", md)
        self.assertIn("datos insuficientes", md)

    def test_ignores_unknown_zone_and_gaps(self):
        data = rows(14, lambda i: "purple", lambda i: 55)
        data[3]["hrv_ms"] = ""
        r = z.compute(data, "2026-09-14")
        self.assertTrue(all(v["n"] == 0 for v in r["zones"].values()))


if __name__ == "__main__":
    unittest.main()
