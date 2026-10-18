"""V7.0: tarjetas nuevas del panel web (qué ha cambiado, esta noche, próximos 7 días) y navegación."""
import unittest

from garmin_recovery import dashboard


class Cards(unittest.TestCase):
    def test_tonight(self):
        need = {"base_h": 7.5, "load_add_h": 0.3, "debt_add_h": 1.0, "nap_today_h": 0.0, "need_tonight_h": 8.8,
                "debt_7n_h": 6.3, "debt_3n_h": 3.1, "debt_3n_model_h": 4.0, "naps_known": False}
        html = dashboard._tonight_html({"need": need, "tip": "Duerme pronto <b>"})
        self.assertIn("8,8", html)
        self.assertIn("sin dato", html)
        self.assertIn("3 noches: 3,1 h", html)
        self.assertIn("v3) cuenta solo 3 noches y no descuenta siestas: 4,0 h", html)
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


class Days(unittest.TestCase):
    def test_days_card_and_snapshot_banner(self):
        html = dashboard._days_html([{"date": "2026-10-17", "zone": "red", "score": 52.4}])
        self.assertIn("dia/2026-10-17.html", html)
        self.assertIn("52", html)
        self.assertEqual(dashboard._days_html([]), "")

    def test_day_snapshots_from_git(self):
        import json
        from pathlib import Path

        from garmin_recovery import site

        class R:
            def __init__(self, out):
                self.stdout = out

        objs = {"a": {"date": "2026-10-17", "decision": {"zone": "red"}, "readiness": {}},
                "b": {"date": "2026-10-17", "decision": {"zone": "green"}, "readiness": {}},
                "c": {"date": "2026-10-16", "decision": {"zone": "green"}, "readiness": {}},
                "d": {"date": "2026-10-18", "decision": {"zone": "green"}, "readiness": {}}}

        def fake(cmd, **kw):
            if "log" in cmd:
                return R("d\na\nb\nc\nzz\n")
            sha = cmd[-1].split(":")[0]
            return R(json.dumps(objs[sha]) if sha in objs else "no json")
        out = site.day_snapshots(Path("."), "2026-10-18", run=fake)
        self.assertEqual([(o["date"], o["decision"]["zone"]) for o in out],
                         [("2026-10-17", "red"), ("2026-10-16", "green")])  # el más reciente de cada día, sin hoy


class ReportFigures(unittest.TestCase):
    def test_plain_figure_images_fit_the_column(self):
        from garmin_recovery import webreport
        self.assertIn("figure>img{display:block;width:100%", webreport.CSS)  # sessions.svg mide 640 px: no debe desbordar el móvil


class Delivery(unittest.TestCase):
    D = {"cycle_id": "2026-10-18-1645", "state": "complete", "scope": "Notificación enviada = aceptada por ntfy.",
         "stages": {"sync": {"state": "ok"}, "web": {"state": "pending", "note": "despliegue en curso"},
                    "notification": {"state": "failed"}}}

    def test_chips_and_title(self):
        html = dashboard._delivery_html(self.D)
        self.assertIn("Ciclo completo", html)
        self.assertIn("✓ Sync", html)
        self.assertIn("… Web", html)
        self.assertIn("✗ Aviso", html)
        self.assertIn("aceptada por ntfy", html)
        self.assertEqual(dashboard._delivery_html(None), "")
