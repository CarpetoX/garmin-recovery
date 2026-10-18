"""V7.0: tarjetas nuevas del panel web (qué ha cambiado, esta noche, próximos 7 días) y navegación."""
import unittest

from garmin_recovery import dashboard


class Cards(unittest.TestCase):
    def test_tonight(self):
        need = {"base_h": 7.5, "load_add_h": 0.3, "debt_add_h": 1.0, "nap_today_h": 0.0, "need_tonight_h": 8.8,
                "debt_7n_h": 6.3, "naps_known": False}
        html = dashboard._tonight_html({"need": need, "tip": "Duerme pronto <b>"})
        self.assertIn("8,8", html)
        self.assertIn("sin dato", html)
        self.assertIn("&lt;b&gt;", html)  # el texto se escapa
        self.assertEqual(dashboard._tonight_html({"need": None}), "")
        self.assertEqual(dashboard._tonight_html(None), "")

    def test_plan(self):
        rows = [{"date": "2026-10-20", "dow": "Mar", "shift": "free", "kind": "hard", "why": "libre"}]
        html = dashboard._plan_html(rows)
        self.assertIn("k-hard", html)
        self.assertIn("Exigente", html)
        self.assertEqual(dashboard._plan_html([]), "")

    def test_changes(self):
        c = {"available": True, "score_from": 70, "score_to": 77,
             "items": [{"label": "HRV", "from": 50, "to": 58, "dec": 0, "unit": " ms", "favorable": True}]}
        html = dashboard._changes_html(c)
        self.assertIn("70 → 77", html)
        self.assertIn("HRV", html)
        self.assertEqual(dashboard._changes_html({"available": False}), "")
        self.assertIn("Ningún indicador", dashboard._changes_html({"available": True, "items": []}))


if __name__ == "__main__":
    unittest.main()
