"""Informes V5.9: resumen de tres líneas, decisión única, plegables y resumen semanal."""
import json
import unittest
from datetime import date, timedelta
from pathlib import Path

from garmin_recovery.report import build_report, models_details, summary_block
from garmin_recovery.readiness import GUIDANCE
from garmin_recovery.weekly import build_weekly, weekly_summary

ROOT = Path(__file__).resolve().parent


def fake_result(zone="red", today="2026-10-17"):
    d0 = date.fromisoformat(today)
    trend = [{"date": (d0 - timedelta(days=i)).isoformat(), "hrv_ms": 50 + i % 3, "resting_hr": 56, "sleep_hours": 7.0 + (i % 2),
              "decision_zone": zone if i < 3 else None, "hrv_rolling_ms": 51.0, "hrv_low_ms": 54.0, "hrv_high_ms": 60.0}
             for i in range(13, -1, -1)]
    sessions = [{"date": (d0 - timedelta(days=i)).isoformat(), "duration_min": 60, "load": 20, "srpe": 420, "rpe": 7 if i else 6}
                for i in range(0, 14, 2)]
    return {"date": today, "generated_at": today + "T22:50:00+02:00", "trend_28d": trend, "sessions_28d": sessions,
            "recent_sessions": sessions,
            "decision": {"zone": zone, "guidance": dict(GUIDANCE[zone]), "decided_by": ["recovery_assessment_v2"],
                         "missing_models": [], "rule": "Regla.",
                         "registry": [{"id": "recovery_assessment_v2", "label": "Recuperación v2 (oficial)", "score": 45,
                                       "zone": zone, "role": "oficial"},
                                      {"id": "readiness_v3", "label": "Disponibilidad v3", "score": 52, "zone": "yellow", "role": "sombra"}]},
            "readiness": {"components": {"sleep": {"need_hours": 7.5}},
                          "drivers": [{"z": -3.1, "text": "FC en reposo +5"}, {"z": -1.4, "text": "HRV −11 %"}, {"z": 0.5, "text": "bien"}]},
            "load": {"monotony": 0.8}, "certificate": {}, "model_validation": {"verdict": "Acumulando datos: 3/20."}}


class SummaryAndDecision(unittest.TestCase):
    def test_three_line_summary(self):
        r = fake_result()
        lines = [x for x in summary_block(r, r["decision"], r["decision"]["guidance"], "red") if x.startswith("> **")]
        self.assertEqual(len(lines), 3)
        self.assertIn("RPE ≤ 4", lines[0])
        self.assertIn("FC en reposo +5 · HRV −11 %", lines[1])
        self.assertNotIn("bien", lines[1])
        self.assertIn(GUIDANCE["red"]["text"], lines[2])

    def test_pending_summary_explains_missing(self):
        r = fake_result("unavailable")
        r["decision"]["missing_models"] = ["readiness_v3"]
        r["readiness"]["missing_today"] = ["sueño"]
        why = summary_block(r, r["decision"], r["decision"]["guidance"], "unavailable")[2]
        self.assertIn("faltan datos de hoy (sueño)", why)
        self.assertIn("Disponibilidad v3", why)

    def test_models_only_inside_details(self):
        md = "\n".join(models_details(fake_result()["decision"]))
        self.assertTrue(md.startswith("<details><summary>"))
        self.assertIn("</details>", md)
        self.assertIn("| Disponibilidad v3 | 52 | ámbar | sombra |", md)

    def test_full_report_single_decision_and_balanced_details(self):
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        md, _ = build_report(result, {}, None, "GR-2026-10-17-1705-8a9b0d")
        self.assertEqual(md.count("<details"), md.count("</details>"))
        self.assertEqual(md.count("## ") - md.count("### "), len([x for x in md.splitlines() if x.startswith("## ")]))
        self.assertNotIn("Puntuaciones (no equivalentes entre sí)", md)
        self.assertLess(md.index("> **Hoy:"), md.index("## "))
        self.assertIn("## Certificado", md)


class Weekly(unittest.TestCase):
    def test_week_vs_previous(self):
        w = weekly_summary(fake_result())
        self.assertEqual((w["start"], w["end"]), ("2026-10-11", "2026-10-17"))
        self.assertEqual(w["sessions"], 4)       # días 0, 2, 4, 6
        self.assertEqual(w["sessions_prev"], 3)  # días 8, 10, 12
        self.assertEqual(w["srpe"], 1680)
        self.assertEqual(w["days_with_decision"], 3)

    def test_over_cap_detected(self):
        w = weekly_summary(fake_result("red"))  # RPE 7 en días con decisión roja (máx. 4)
        self.assertEqual([o["date"] for o in w["over_cap"]], ["2026-10-15", "2026-10-17"])  # RPE 7 y 6 > 4

    def test_markdown_clean(self):
        md = build_weekly(fake_result(), [{"date": "2026-10-16", "exercise": "Sentadilla", "peak_declared_load_kg": 150,
                                           "known_sets": 5, "total_sets": 5}], "GR-2026-10-17-2250-abcdef")
        self.assertTrue(md.startswith("# Resumen semanal · 11/10–17/10"))
        self.assertIn("GR-2026-10-17-2250-abcdef", md)
        self.assertIn("| 16/10 | Sentadilla | 150,0 kg | 5/5 |", md)
        self.assertIn("2 de 2 días comprobados por encima del RPE máximo", md)
        self.assertNotIn("None", md)


class WeeklyReview(unittest.TestCase):
    def test_unchecked_days_not_reported_as_clean(self):
        r = fake_result()
        for row in r["trend_28d"]:
            row["decision_zone"] = None
            row["sleep_hours"] = None
        md = build_weekly(r, [], "GR-2026-10-17-2250-abcdef")
        self.assertIn("RPE máximo aún sin comprobar", md)
        self.assertIn("sin datos de sueño esta semana", md)
        self.assertNotIn("ningún día por encima", md)

    def test_weekly_failure_never_blocks_daily_report(self):
        import tempfile
        from unittest import mock
        from garmin_recovery import report as rep
        if not (ROOT / "app" / "readiness_v3.json").exists():
            self.skipTest("sin salida publicada")
        result = json.loads((ROOT / "app" / "readiness_v3.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp, mock.patch("garmin_recovery.weekly.build_weekly", side_effect=KeyError("x")):
            Path(tmp, "history").mkdir()
            rep.write_report(tmp, Path(tmp) / "app", result)
            weekly = (Path(tmp) / "app" / "informe_semanal.md").read_text(encoding="utf-8")
            self.assertTrue(weekly.startswith("# Resumen semanal"))
            self.assertIn("No se pudo generar", weekly)
            self.assertTrue((Path(tmp) / "app" / "informe.md").exists())


if __name__ == "__main__":
    unittest.main()
