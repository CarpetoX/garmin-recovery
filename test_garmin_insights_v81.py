"""V8.1: respiración nocturna, equilibrio de carga, VO2max y efecto de entrenamiento desde garmin_extended.json."""
import json
import unittest
from pathlib import Path

from garmin_recovery import garmin_insights as gi
from garmin_recovery.dashboard import _load_balance_html, _respiration_html, _vo2_html, render

ROOT = Path(__file__).resolve().parent
DEV = "3639504748"


def day(resp=None, vo2=None, lb=None, acts=None):
    d = {"sleep_detail": {"avg_respiration": resp, "lowest_respiration": 10, "highest_respiration": 21}}
    ts = {}
    if vo2 is not None:
        ts["mostRecentVO2Max.generic.vo2MaxPreciseValue"] = vo2
    for k, v in (lb or {}).items():
        ts[f"mostRecentTrainingLoadBalance.metricsTrainingLoadBalanceDTOMap.{DEV}.{k}"] = v
    d["training_status"] = ts
    d["activity_metrics"] = {"activities": acts or []}
    return d


class Respiration(unittest.TestCase):
    def days(self, last):
        out = {f"2026-10-{i:02d}": day(16.0) for i in range(1, 11)}
        out["2026-10-11"] = day(last)
        return out

    def test_normal_high_and_combined(self):
        self.assertEqual(gi.respiration(self.days(16.5), "2026-10-11")["state"], "normal")
        r = gi.respiration(self.days(18.0), "2026-10-11", hrv_today=60, hrv_median=58)
        self.assertEqual((r["state"], r["delta"], r["median"]), ("alta", 2.0, 16.0))
        self.assertEqual(gi.respiration(self.days(18.5), "2026-10-11", hrv_today=40, hrv_median=58)["state"], "alta_y_hrv_baja")

    def test_needs_reference_and_ignores_future(self):
        few = {"2026-10-01": day(16), "2026-10-02": day(19)}
        self.assertEqual(gi.respiration(few, "2026-10-02")["state"], "sin_referencia")
        self.assertEqual(gi.respiration(self.days(25.0), "2026-10-10")["date"], "2026-10-10")

    def test_html_states(self):
        html = _respiration_html(gi.respiration(self.days(18.5), "2026-10-11", hrv_today=40, hrv_median=58))
        self.assertIn("alta y con HRV baja", html)
        self.assertIn("resfriado incipiente", html)
        self.assertEqual(_respiration_html({"available": False}), "")


class LoadAndVo2(unittest.TestCase):
    LB = {"monthlyLoadAerobicLow": 723.2, "monthlyLoadAerobicLowTargetMin": 485, "monthlyLoadAerobicLowTargetMax": 1138,
          "monthlyLoadAerobicHigh": 1500, "monthlyLoadAerobicHighTargetMin": 711, "monthlyLoadAerobicHighTargetMax": 1364,
          "monthlyLoadAnaerobic": 624, "monthlyLoadAnaerobicTargetMin": 0, "monthlyLoadAnaerobicTargetMax": 652,
          "trainingBalanceFeedbackPhrase": "AEROBIC_HIGH_FOCUS"}

    def test_load_balance_states(self):
        lb = gi.load_balance({"2026-10-26": day(lb=self.LB)}, "2026-10-26")
        st = {p["id"]: (p["value"], p["state"], p["near_top"]) for p in lb["parts"]}
        self.assertEqual(st["aerobic_low"], (723, "en rango", False))
        self.assertEqual(st["aerobic_high"], (1500, "alto", False))
        self.assertEqual(st["anaerobic"], (624, "en rango", True))
        self.assertEqual(lb["feedback"], "centrada en aeróbica alta")
        html = _load_balance_html(lb)
        self.assertIn("por encima", html)
        self.assertIn("cerca del techo", html)

    def test_vo2max_trend(self):
        v = gi.vo2max({"2026-10-01": day(vo2=50.9), "2026-10-20": day(vo2=51.4)}, "2026-10-26")
        self.assertEqual((v["value"], v["change"], v["since"]), (51.4, 0.5, "2026-10-01"))
        self.assertIn("sube 0,5", _vo2_html(v))


class TrainingEffect(unittest.TestCase):
    def test_matched_by_external_id_then_start(self):
        acts = [{"activity_id": 111, "start_time_local": "2026-10-26 09:59:58", "aerobic_training_effect": 2.6000001,
                 "anaerobic_training_effect": 2.4, "training_effect_label": "TEMPO"},
                {"activity_id": 222, "start_time_local": "2026-10-26 15:15:34", "aerobic_training_effect": 1.2,
                 "anaerobic_training_effect": 0.0}]
        ints = [{"id": "i1", "external_id": "111", "start_date_local": "2026-10-26T09:59:58"},
                {"id": "i2", "start_date_local": "2026-10-26T15:15:34"}, {"id": "i3", "start_date_local": "2026-10-27T10:00:00"}]
        te = gi.training_effect({"2026-10-26": day(acts=acts)}, ints)
        self.assertEqual(te["i1"], {"aerobic": 2.6, "anaerobic": 2.4, "label": "tempo"})
        self.assertEqual(te["i2"]["aerobic"], 1.2)
        self.assertNotIn("i3", te)


class RealDataAndPage(unittest.TestCase):
    def test_every_activity_gets_training_effect_and_page_has_cards(self):
        ext = json.loads((ROOT / "garmin_extended.json").read_text(encoding="utf-8"))
        acts = json.loads((ROOT / "activities.json").read_text(encoding="utf-8"))
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        ins = gi.build(ext, acts, result["date"], result.get("trend_28d"))
        self.assertTrue(ins["respiration"]["available"])
        page = render(result, {"garmin_insights": ins})
        for needle in ('id="respiracion"', 'id="equilibrio"', 'id="vo2max"', '"training_effect"', "Qué mide y cómo leerlo"):
            self.assertIn(needle, page)


if __name__ == "__main__":
    unittest.main()
