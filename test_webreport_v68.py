import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from garmin_recovery import mdhtml, webreport

MD = """# Garmin Recovery · Cierre nocturno

Domingo, 18 de octubre de 2026 · 01:10

```cards
Decisión|Prioriza recuperar|RPE máx. 4|red
```

## Resumen ejecutivo

- uno

## 1. Certificación y calidad

| a | b |
|---|---|
| 1 | 2 |

## 2. Recuperación fisiológica

![HRV](charts/hrv.svg)

![Fuerza](charts/strength.svg)

## Conclusión

Fin </script><b>x</b>
"""
RESULT = {"trend_28d": [{"date": f"2026-10-{d:02d}", "hrv_ms": 50 + d % 5, "hrv_low_ms": 45, "hrv_high_ms": 62, "resting_hr": 56,
                         "sleep_hours": 7.5, "deep_min": 60, "rem_min": 90, "srpe": 100, "sessions": 1, "score": 60, "v2_score": 58}
                        for d in range(1, 19)],
          "sessions_28d": [{"date": "2026-10-05", "rpe": 9, "removed": 0}],
          "readiness": {"components": {"hrv": {"label": "HRV", "score": None, "weight": 0.3}, "sleep": {"label": "Sueño", "score": 72, "weight": 0.25}}}}


class WebReport(unittest.TestCase):
    def setUp(self):
        self.html = webreport.build(MD, RESULT)

    def test_sections_nav_and_cards(self):
        self.assertEqual(self.html.count('<details class="sec"'), 4)
        self.assertEqual(self.html.count('<a href="#s'), 4)
        self.assertIn('class="kpi red"', self.html)
        self.assertIn('data-n="7"', self.html)
        self.assertIn("Certificación y calidad", self.html)

    def test_priority_order_and_open(self):
        ids = re.findall(r'<details class="sec" id="(s\d)"( open)?>', self.html)
        self.assertEqual(ids, [("s2", ""), ("s0", ""), ("s1", ""), ("s3", "")])  # recuperación primero; resumen, calidad y conclusión al final
        md = MD.replace("## Conclusión", "## 7. Balance\n\nx\n\n## Análisis de Claude\n\n**En breve:** y\n\n## Conclusión")
        ids = re.findall(r'<details class="sec" id="(s\d)"( open)?>', webreport.build(md, RESULT))
        self.assertEqual([i[1] for i in ids[:2]], [" open", " open"])  # balance y análisis de Claude abiertos y primeros

    def test_section_icons(self):
        self.assertEqual(self.html.count('class="ico"'), 4)

    def test_interactive_chart_and_fallback(self):
        self.assertIn('data-chart="hrv"', self.html)
        self.assertIn('<noscript><img src="charts/hrv.svg"', self.html)
        self.assertIn('<img src="charts/strength.svg"', self.html)  # sin versión interactiva: imagen

    def test_weights_block(self):
        self.assertIn("sin datos hoy", self.html)
        self.assertIn("72", self.html)

    def test_data_embedded_and_safe(self):
        m = re.search(r'<script type="application/json" id="d">(.*?)</script>', self.html, re.S)
        data = json.loads(m.group(1))
        self.assertEqual(len(data["trend"]), 18)
        self.assertEqual(data["trend"][4]["rpe_max"], 9.0)
        self.assertNotIn("</script><b>", self.html)
        self.assertIn("&lt;/script&gt;", self.html)

    @unittest.skipUnless(shutil.which("node"), "sin node")
    def test_javascript_syntax(self):
        js = self.html[self.html.index("<script>") + 8:self.html.rindex("</script>")]
        p = Path(tempfile.mkdtemp()) / "app.js"
        p.write_text(js, encoding="utf-8")
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_plain_renderer_still_works(self):
        self.assertIn("<h2>", mdhtml.page(MD))


if __name__ == "__main__":
    unittest.main()
