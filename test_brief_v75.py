"""V7.5: «Hoy en breve» por reglas, solo con cifras de los datos."""
import unittest

from garmin_recovery import brief

RESULT = {"date": "2026-10-18",
          "decision": {"zone": "green", "guidance": {"label": "Listo para entrenar", "text": "Entrena según lo planificado."},
                       "registry": [{"id": "recovery_assessment_v2", "score": 88}], "divergence": []},
          "readiness": {"confidence": "media", "notes": ["Hoy turno de noche: entrena antes."],
                        "drivers": [{"z": -1.2, "text": "Sueño 6.0 h, deuda 4.0 h"}, {"z": 0.5, "text": "HRV bien"}]},
          "trend_28d": [{"date": "2026-10-17", "v2_score": 45}, {"date": "2026-10-18", "v2_score": 88}]}



class Brief(unittest.TestCase):
    def test_sentences_use_only_data(self):
        out = brief.compose(RESULT, {"need": {"need_tonight_h": 8.5}, "tip": "Duerme antes del turno."})
        txt = " ".join(out)
        for expected in ("Listo para entrenar", "88/100", "zona verde", "sueño 6.0 h", "8,5 h"):
            self.assertIn(expected, txt)

    def test_official_change(self):
        self.assertEqual(brief.official_change(RESULT["trend_28d"], "2026-10-18"), (45.0, 88.0))
        self.assertIsNone(brief.official_change(RESULT["trend_28d"], "2026-10-19"))

    def test_tip_not_repeated(self):
        out = brief.compose(RESULT, {"need": None, "tip": "Hoy turno de noche: entrena antes."})
        self.assertEqual(sum("turno de noche" in x for x in out), 1)

    def test_minimal_data_does_not_break(self):
        out = brief.compose({"decision": {}, "readiness": {}}, None)
        self.assertEqual(len(out), 1)
        self.assertIn("Sin decisión", out[0])


if __name__ == "__main__":
    unittest.main()
