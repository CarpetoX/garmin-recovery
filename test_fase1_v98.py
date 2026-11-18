"""V9.8 (fase 1): catálogo de ejercicios, zonas con lado y series intradía antiguas recortadas."""
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from garmin_recovery import discomfort as dc
from garmin_recovery import exercise_catalog as ec
from garmin_recovery import garmin_metrics as gm
from garmin_recovery import progression as pg
from garmin_recovery import sensations as sn

CATALOG = {"unit_aliases": {"kg_lastre": "lastre_kg"},
           "exercises": [{"name": "press inclinado con mancuernas", "pattern": "empuje horizontal",
                          "aliases": ["press banca inclinado con mancuernas", "press de pecho inclinado con mancuernas"]},
                         {"name": "peso muerto", "aliases": []}]}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        Path(self.tmp.name, ec.FILE).write_text(json.dumps(CATALOG), encoding="utf-8")
        ec._load.cache_clear()

    def tearDown(self):
        self.tmp.cleanup()
        ec._load.cache_clear()

    def test_aliases_units_and_unknown(self):
        r = self.tmp.name
        self.assertEqual(ec.canonical("Press de pecho inclinado con mancuernas", r), "press inclinado con mancuernas")
        self.assertEqual(ec.canonical("Peso muerto", r), "Peso muerto")  # misma palabra: se respeta la grafía
        self.assertEqual(ec.canonical("sentadilla búlgara", r), "sentadilla búlgara")  # fuera del catálogo: tal cual
        self.assertEqual(ec.canonical_unit("kg_lastre", r), "lastre_kg")
        self.assertEqual(ec.pattern("press banca inclinado con mancuernas", r), "empuje horizontal")

    def test_history_is_recanonicalized(self):
        old = {"e1": {"date": "2026-10-10", "activity_id": "a", "exercise": "press banca inclinado con mancuernas",
                      "key": "x", "unit": "kg_total_dos_mancuernas", "top_load": 60, "top_reps": 8, "volume": 480,
                      "volume_complete": True, "work_sets": 1, "sets": [], "rpe": None, "activity": ""}}
        import os
        cwd = os.getcwd()
        os.chdir(self.tmp.name)
        try:
            e = pg.recanonical(old["e1"])
        finally:
            os.chdir(cwd)
        self.assertEqual((e["exercise"], e["exercise_raw"]), ("press inclinado con mancuernas", "press banca inclinado con mancuernas"))


class ZoneTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(sn.normalize_zone("rodilla dcha"), "Rodilla derecha")
        self.assertEqual(sn.normalize_zone("hombro izq"), "Hombro izquierdo")
        self.assertEqual(sn.normalize_zone("Rodilla"), "Rodilla")
        self.assertEqual(sn.normalize_zone("pie"), "pie")
        self.assertEqual(sn.side_of("Rodilla derecha"), "derecha")
        self.assertIsNone(sn.side_of("Espalda baja"))
        self.assertIn("Rodilla izquierda", sn.ZONE_OPTIONS)

    def test_history_by_side(self):
        mk = lambda d, z: {"date": d, "molestias": {"level": 1, "label": "Leves"}, "zonas": z}  # noqa: E731
        h = dc.zone_history([mk("2026-11-12", ["Rodilla derecha"]), mk("2026-11-18", ["Rodilla"]),
                             mk("2026-11-15", ["Espalda baja"]), mk("2026-11-16", ["Espalda alta"])], "2026-11-18")
        knee = next(g for g in h if g["joint"] == "rodilla")
        self.assertEqual((knee["label"], knee["sides"], knee["unsided_days"]), ("Rodilla derecha", ["derecha"], 1))
        self.assertEqual({g["label"] for g in h if g["joint"] != "rodilla"}, {"Espalda baja", "Espalda alta"})
        both = dc.zone_history([mk("2026-11-12", ["Rodilla derecha"]), mk("2026-11-13", ["Rodilla izquierda"])], "2026-11-18")
        self.assertEqual(both[0]["label"], "Rodilla (ambos lados)")


class IntradayTrimTests(unittest.TestCase):
    def test_trim_keeps_summary(self):
        store = {"days": {"2026-10-01": {"avgStressLevel": 30, "maxStressLevel": 90, "stressValuesArray": [[1, 2]],
                                         "bodyBatteryValuesArray": [[1, "x", 50]]},
                          "2026-11-18": {"avgStressLevel": 28, "stressValuesArray": [[1, 2]]}}}
        out = gm.trim_intraday(store, date(2026, 11, 19))
        old, new = out["days"]["2026-10-01"], out["days"]["2026-11-18"]
        self.assertNotIn("stressValuesArray", old)
        self.assertEqual((old["avgStressLevel"], old["maxStressLevel"], old["intraday_trimmed"]), (30, 90, True))
        self.assertIn("stressValuesArray", new)


if __name__ == "__main__":
    unittest.main()
