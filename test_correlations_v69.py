import unittest

from garmin_recovery import correlations as c


def days(n, hrv_fn, **fields):
    rows = []
    for i in range(n):
        d = f"2026-09-{1 + i:02d}"
        r = {"date": d, "hrv_ms": str(hrv_fn(i)), "sessions": "0", "sleep_hours": "7.5", "shift": "MT"}
        r.update({k: (v(i) if callable(v) else v) for k, v in fields.items()})
        rows.append(r)
    return rows


class Corr(unittest.TestCase):
    def test_notable_difference(self):
        # sesiones en días pares; HRV del día siguiente (impar) 10 ms menor
        rows = days(20, lambda i: 50 if i % 2 else 60, sessions=lambda i: "1" if i % 2 == 0 else "0")
        f = {x["key"]: x for x in c.compute(rows, "2026-09-20")["factors"]}
        self.assertTrue(f["trained"]["ok"])
        self.assertEqual(f["trained"]["diff_ms"], -10.0)
        self.assertTrue(f["trained"]["notable"])
        self.assertIn("**", c.to_markdown(c.compute(rows, "2026-09-20")))

    def test_insufficient_groups(self):
        rows = days(20, lambda i: 55, sessions=lambda i: "1" if i < 3 else "0")
        f = {x["key"]: x for x in c.compute(rows, "2026-09-20")["factors"]}
        self.assertFalse(f["trained"]["ok"])
        self.assertIn("insuficientes", c.to_markdown(c.compute(rows, "2026-09-20")))

    def test_missing_measurements_not_counted_as_without(self):
        rows = days(20, lambda i: 55, sleep_hours="")
        f = {x["key"]: x for x in c.compute(rows, "2026-09-20")["factors"]}
        self.assertEqual((f["short_sleep"]["n_with"], f["short_sleep"]["n_without"]), (0, 0))

    def test_load_missing_file(self):
        self.assertEqual(c.load("/nonexistent-dir-xyz"), [])


if __name__ == "__main__":
    unittest.main()
