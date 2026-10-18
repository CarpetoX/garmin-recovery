import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from garmin_recovery import rpe_enrichment as rp


class Numbers(unittest.TestCase):
    def test_number_and_rpe(self):
        self.assertEqual(rp.number("8,5"), 8.5)
        self.assertIsNone(rp.number(True))
        self.assertIsNone(rp.number("x"))
        self.assertIsNone(rp.number(None))
        self.assertEqual(rp.valid_rpe("9.5"), 9.5)
        self.assertEqual(rp.valid_rpe(0), 0.0)
        self.assertIsNone(rp.valid_rpe(11))
        self.assertIsNone(rp.valid_rpe(-1))
        self.assertIsNone(rp.valid_rpe("sin dato"))

    def test_intervals_rpe_priority(self):
        self.assertEqual(rp.intervals_rpe({"session_rpe": 7, "icu_rpe": 5}), 7.0)
        self.assertEqual(rp.intervals_rpe({"session_rpe": None, "icu_rpe": "6"}), 6.0)
        self.assertEqual(rp.intervals_rpe({"perceived_exertion": 4}), 4.0)
        self.assertIsNone(rp.intervals_rpe({"session_rpe": 99}))
        self.assertIsNone(rp.intervals_rpe("x"))


class Normalize(unittest.TestCase):
    def test_sheet_columns_in_spanish(self):
        rows = [{"Fecha": "2026-10-18", "ID actividad": "i1", "Actividad": "Fuerza", "RPE": "9,5", "Sensaciones": "bien",
                 "Notas": "n", "Registrado": "2026-10-18", "Detalle JSON": "{}"},
                {"Fecha": "2026-10-18", "ID actividad": "", "RPE": "5"},          # sin ID: se ignora
                {"Fecha": "2026-10-18", "ID actividad": "i2", "RPE": ""}]          # sin RPE: se ignora
        out = rp.normalize_feedback({"activities": rows})
        self.assertEqual(list(out), ["i1"])
        self.assertEqual((out["i1"]["rpe"], out["i1"]["activity"], out["i1"]["detail_json"]), (9.5, "Fuerza", "{}"))

    def test_dict_and_list_shapes(self):
        as_dict = {"activities": {"i1": {"rpe": 6, "date": "2026-10-18"}, "i2": "x", "i3": {"rpe": 20}}}
        self.assertEqual(list(rp.normalize_feedback(as_dict)), ["i1"])
        as_list = {"activities": [{"activity_id": "i5", "rpe": 3}, {"id": "i6", "RPE": 4}, "x"]}
        self.assertEqual(sorted(rp.normalize_feedback(as_list)), ["i5", "i6"])
        self.assertEqual(rp.normalize_feedback([]), {})
        self.assertEqual(rp.normalize_feedback({"activities": 5}), {})


class Io(unittest.TestCase):
    def test_json_roundtrip_and_nan_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            self.assertEqual(rp.load_json(p, 7), 7)
            rp.save_json(p, {"a": "ñ"})
            self.assertEqual(rp.load_json(p, None), {"a": "ñ"})
            with self.assertRaises(ValueError):
                rp.save_json(p, {"a": float("nan")})
            p.write_text("{roto", encoding="utf-8")
            self.assertEqual(rp.load_json(p, "def"), "def")

    def test_fresh_url_adds_cache_buster(self):
        u = rp.fresh_url("https://example.com/export?format=csv#x")
        self.assertIn("format=csv", u)
        self.assertIn("_garmin_cache_bust=", u)
        self.assertTrue(u.endswith("#x"))
        self.assertNotEqual(u, rp.fresh_url("https://example.com/export?format=csv#x"))

    def test_feedback_from_csv(self):
        self.assertEqual(rp.feedback_from_csv(""), {})
        csv_text = "Fecha,ID actividad,Actividad,RPE\n2026-10-18,i1,Fuerza,9.5\n,,,\n"

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"\xef\xbb\xbf" + csv_text.encode()
        with mock.patch.object(rp, "validate_rows", lambda rows: None), mock.patch.object(rp.urllib.request, "urlopen", lambda req, timeout: Resp()):
            fb, rows = rp.feedback_from_csv("https://example.com/x.csv")
        self.assertEqual(list(fb), ["i1"])
        self.assertEqual(len(rows), 1)
        json.dumps(fb)


if __name__ == "__main__":
    unittest.main()
